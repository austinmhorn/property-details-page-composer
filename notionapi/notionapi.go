package notionapi

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"
)

// Runtime configuration is loaded from secrets/.env. Existing environment
// variables take precedence, which keeps deployment flexible.
var notionToken string
var databaseID string
var notionAPIURL string
var apiResponseFilePath string

var client = &http.Client{Timeout: 120 * time.Second}

// ProjectRoot finds the repository root by walking upward until go.mod exists.
func ProjectRoot() (string, error) {
	dir, err := os.Getwd()
	if err != nil {
		return "", err
	}

	for {
		if _, err := os.Stat(filepath.Join(dir, "go.mod")); err == nil {
			return dir, nil
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			break
		}
		dir = parent
	}
	return "", fmt.Errorf("could not locate project root (go.mod not found)")
}

func loadDotEnv(path string) error {
	data, err := os.ReadFile(path)
	if err != nil {
		return err
	}

	for _, line := range strings.Split(string(data), "\n") {
		line = strings.TrimSpace(line)
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}

		parts := strings.SplitN(line, "=", 2)
		if len(parts) != 2 {
			continue
		}

		key := strings.TrimSpace(parts[0])
		value := strings.Trim(strings.TrimSpace(parts[1]), "\"'")
		if key == "" {
			continue
		}

		if _, exists := os.LookupEnv(key); !exists {
			_ = os.Setenv(key, value)
		}
	}
	return nil
}

// LoadConfig loads Notion credentials from secrets/.env.
func LoadConfig() error {
	root, err := ProjectRoot()
	if err != nil {
		return err
	}

	envPath := filepath.Join(root, "secrets", ".env")
	if err := loadDotEnv(envPath); err != nil {
		return fmt.Errorf("failed to load %s: %w", envPath, err)
	}

	notionToken = strings.TrimSpace(os.Getenv("NOTION_TOKEN"))
	databaseID = strings.TrimSpace(os.Getenv("NOTION_DATABASE_ID"))
	if notionToken == "" {
		return fmt.Errorf("NOTION_TOKEN is missing from secrets/.env")
	}
	if databaseID == "" {
		return fmt.Errorf("NOTION_DATABASE_ID is missing from secrets/.env")
	}

	notionAPIURL = "https://api.notion.com/v1/databases/" + databaseID + "/query"
	apiResponseFilePath = filepath.Join(root, "json", "api_response.json")

	if err := os.MkdirAll(filepath.Dir(apiResponseFilePath), 0755); err != nil {
		return fmt.Errorf("failed to create json directory: %w", err)
	}

	fmt.Println("✅ Notion configuration loaded successfully")
	return nil
}

// Fetch Notion Data (Supports Pagination)
func FetchNotionData() ([]map[string]interface{}, error) {
	var allData []map[string]interface{}
	hasMore := true
	startCursor := ""

	for hasMore {
		payload := map[string]interface{}{"page_size": 100}
		if startCursor != "" {
			payload["start_cursor"] = startCursor
		}

		payloadBytes, err := json.Marshal(payload)
		if err != nil {
			return nil, fmt.Errorf("failed to encode Notion request: %w", err)
		}

		req, err := http.NewRequest("POST", notionAPIURL, bytes.NewReader(payloadBytes))
		if err != nil {
			return nil, err
		}
		req.Header.Set("Authorization", "Bearer "+notionToken)
		req.Header.Set("Notion-Version", "2022-06-28")
		req.Header.Set("Content-Type", "application/json")

		resp, err := client.Do(req)
		if err != nil {
			return nil, err
		}
		body, readErr := io.ReadAll(resp.Body)
		resp.Body.Close()
		if readErr != nil {
			return nil, readErr
		}

		if resp.StatusCode < 200 || resp.StatusCode >= 300 {
			return nil, fmt.Errorf("Notion API returned HTTP %d: %s", resp.StatusCode, strings.TrimSpace(string(body)))
		}

		var result map[string]interface{}
		if err := json.Unmarshal(body, &result); err != nil {
			return nil, err
		}

		if results, ok := result["results"].([]interface{}); ok {
			for _, r := range results {
				if page, ok := r.(map[string]interface{}); ok {
					allData = append(allData, page)
				}
			}
		}

		if hasMoreVal, ok := result["has_more"].(bool); ok {
			hasMore = hasMoreVal
		} else {
			hasMore = false
		}

		if nextCursor, ok := result["next_cursor"].(string); ok {
			startCursor = nextCursor
		} else {
			startCursor = ""
		}
	}

	debugPayload := map[string]interface{}{
		"count": len(allData),
		"results": allData,
	}
	formattedJSON, err := json.MarshalIndent(debugPayload, "", "    ")
	if err != nil {
		return nil, fmt.Errorf("failed to format combined Notion response: %w", err)
	}
	if err := os.WriteFile(apiResponseFilePath, formattedJSON, 0644); err != nil {
		return nil, fmt.Errorf("failed to write API response file: %w", err)
	}
	fmt.Printf("📁 Combined Notion API response saved to %s\n", apiResponseFilePath)

	return allData, nil
}

// Fetch Name (Page Title)
func GetName(props map[string]interface{}, key string) string {
	name := "No Name"
	if nameProp, exists := props[key]; exists {
		if titleList, ok := nameProp.(map[string]interface{})["title"].([]interface{}); ok && len(titleList) > 0 {
			if firstTitle, ok := titleList[0].(map[string]interface{}); ok {
				if text, exists := firstTitle["text"].(map[string]interface{}); exists {
					if content, exists := text["content"].(string); exists {
						name = content
					}
				}
			}
		}
	}
	return name
}

// Fetch Status
func GetStatus(props map[string]interface{}, key string) string {
	status := "No Status"

	// Check if "Asset Status" exists
	if assetStatus, exists := props[key]; exists {
		if assetStatusMap, ok := assetStatus.(map[string]interface{}); ok {
			// Check if "status" exists within "Asset Status"
			if statusMap, exists := assetStatusMap["status"]; exists {
				if statusDetails, ok := statusMap.(map[string]interface{}); ok {
					// Extract the "name" field from "status"
					if name, exists := statusDetails["name"].(string); exists {
						status = name
					}
				}
			}
		}
	}

	return status
}

// Fetch Float Value
func GetFloatValue(props map[string]interface{}, key string) string {
	if numProp, exists := props[key]; exists {
		if num, ok := numProp.(map[string]interface{})["number"].(float64); ok {
			return fmt.Sprintf("%.2f", num)
		}
	}
	return ""
}

// Fetch Integer Value
func GetIntValue(props map[string]interface{}, key string) string {
	if numProp, exists := props[key]; exists {
		if num, ok := numProp.(map[string]interface{})["number"].(float64); ok {
			return fmt.Sprintf("%d", int(num)) // Convert float64 to int and format as a string
		}
	}
	return ""
}

// Fetch Plain Text Value
func GetPlainTextValue(props map[string]interface{}, key string) string {
	if field, exists := props[key]; exists {
		if fieldMap, ok := field.(map[string]interface{}); ok {
			if richTextArray, exists := fieldMap["rich_text"]; exists {
				if texts, ok := richTextArray.([]interface{}); ok && len(texts) > 0 {
					if textMap, ok := texts[0].(map[string]interface{}); ok {
						if plainText, exists := textMap["plain_text"].(string); exists {
							return plainText
						}
					}
				}
			}
		}
	}
	return ""
}

// Extracts the "name" field from a Select property
func GetSelectValue(props map[string]interface{}, key string) string {
	if field, exists := props[key]; exists {
		if fieldMap, ok := field.(map[string]interface{}); ok {
			if selectField, exists := fieldMap["select"]; exists && selectField != nil {
				if selectMap, ok := selectField.(map[string]interface{}); ok {
					if name, exists := selectMap["name"].(string); exists {
						return name
					}
				}
			}
		}
	}
	return ""
}

// Extracts all "name" fields from a Multi-Select property
func GetMultiSelectStrings(props map[string]interface{}, key string) []string {
	var values []string

	// Check if key exists in properties
	if field, exists := props[key]; exists {
		if fieldMap, ok := field.(map[string]interface{}); ok {
			if multiSelectField, exists := fieldMap["multi_select"]; exists {
				if multiSelectList, ok := multiSelectField.([]interface{}); ok {
					for _, item := range multiSelectList {
						if itemMap, ok := item.(map[string]interface{}); ok {
							if name, exists := itemMap["name"].(string); exists {
								values = append(values, name)
							}
						}
					}
				}
			}
		}
	}

	return values
}

// Fetch Date Value (Formatted MM/DD/YYYY)
func GetDateValue(props map[string]interface{}, key string) string {
	if dateProp, exists := props[key]; exists {
		if dateObj, ok := dateProp.(map[string]interface{})["date"].(map[string]interface{}); ok {
			if dateStr, ok := dateObj["start"].(string); ok && dateStr != "" {
				parsedDate, err := time.Parse("2006-01-02", dateStr)
				if err == nil {
					return parsedDate.Format("01/02/2006")
				}
				return dateStr // fallback if parsing fails
			}
		}
	}
	return ""
}

// Fetch URL Value
func GetURLValue(props map[string]interface{}, key string) string {
	if field, exists := props[key]; exists {
		if fieldMap, ok := field.(map[string]interface{}); ok {
			if url, exists := fieldMap["url"].(string); exists {
				return url
			}
		}
	}
	return ""
}

// Fetch Clean Plain Text Value (Removes Leading/Trailing Newlines and Spaces)
func GetCleanPlainTextValue(props map[string]interface{}, key string) string {
	// Check if the key exists
	if field, exists := props[key]; exists {
		if fieldMap, ok := field.(map[string]interface{}); ok {
			// Extract "rich_text" field
			if richTextArray, exists := fieldMap["rich_text"]; exists {
				if texts, ok := richTextArray.([]interface{}); ok && len(texts) > 0 {
					// Extract "plain_text" field from the first rich_text item
					if textMap, ok := texts[0].(map[string]interface{}); ok {
						if plainText, exists := textMap["plain_text"].(string); exists {
							// Trim whitespace and newlines, then return the cleaned plain text
							return strings.TrimSpace(plainText)
						}
					}
				}
			}
		}
	}
	return ""
}

// Fetch URL Value (Removes Leading/Trailing Newlines and Spaces)
func GetCleanURL(props map[string]interface{}, key string) string {
	// Check if the key exists
	if field, exists := props[key]; exists {
		if fieldMap, ok := field.(map[string]interface{}); ok {
			// Extract "url" field
			if url, exists := fieldMap["url"].(string); exists {
				// Trim whitespace and newlines, then return the cleaned URL
				return strings.TrimSpace(url)
			}
		}
	}
	return ""
}

// Fetch Email Value (Removes Leading/Trailing Newlines and Spaces)
func GetCleanEmailValue(props map[string]interface{}, key string) string {
	// Check if the key exists
	if field, exists := props[key]; exists {
		if fieldMap, ok := field.(map[string]interface{}); ok {
			// Extract "email" field
			if email, exists := fieldMap["email"].(string); exists {
				// Trim whitespace and newlines, then return the cleaned email
				return strings.TrimSpace(email)
			}
		}
	}
	return ""
}

// Fetch Phone Number Value (Removes Leading/Trailing Whitespace)
func GetPhoneNumberValue(props map[string]interface{}, key string) string {
	// Check if the key exists
	if field, exists := props[key]; exists {
		if fieldMap, ok := field.(map[string]interface{}); ok {
			// Extract "phone_number" field
			if phoneNumber, exists := fieldMap["phone_number"].(string); exists {
				// Trim whitespace and return the cleaned phone number
				return strings.TrimSpace(phoneNumber)
			}
		}
	}
	return ""
}

// Fetch Formula Text Value
func GetFormulaTextValue(props map[string]interface{}, key string) string {
	// Check if the property exists
	if field, exists := props[key]; exists {
		if fieldMap, ok := field.(map[string]interface{}); ok {
			// Ensure it has a "formula" field
			if formulaField, exists := fieldMap["formula"]; exists {
				if formulaMap, ok := formulaField.(map[string]interface{}); ok {
					// Extract the "string" value from the formula field
					if textValue, exists := formulaMap["string"].(string); exists {
						return textValue
					}
				}
			}
		}
	}
	return ""
}

// Fetch Formula Number Value
func GetFormulaNumberValue(props map[string]interface{}, key string) float64 {
	// Ensure the key exists in properties
	if field, exists := props[key]; exists {
		if fieldMap, ok := field.(map[string]interface{}); ok {
			// Ensure the field contains a "formula"
			if formulaField, exists := fieldMap["formula"]; exists {
				if formulaMap, ok := formulaField.(map[string]interface{}); ok {
					// Extract the "number" field
					if numberValue, exists := formulaMap["number"].(float64); exists {
						return numberValue
					}
				}
			}
		}
	}

	// If no valid number was found, return 0.0
	return 0.0
}

// Fetch Rollup Plain Text Value
func GetRollupPlainText(props map[string]interface{}, key string) []string {
	var values []string

	// Check if the key exists
	if field, exists := props[key]; exists {
		if fieldMap, ok := field.(map[string]interface{}); ok {
			// Check if it contains a "rollup" field
			if rollupField, exists := fieldMap["rollup"]; exists {
				if rollupMap, ok := rollupField.(map[string]interface{}); ok {
					// Check if "array" exists inside the rollup
					if arrayField, exists := rollupMap["array"]; exists {
						if arrayItems, ok := arrayField.([]interface{}); ok {
							// If the array is empty, append an empty string
							if len(arrayItems) == 0 {
								return []string{""}
							}

							// Iterate over array items
							for _, item := range arrayItems {
								if itemMap, ok := item.(map[string]interface{}); ok {
									// Check if "rich_text" exists
									if richTextArray, exists := itemMap["rich_text"]; exists {
										if richTextItems, ok := richTextArray.([]interface{}); ok && len(richTextItems) > 0 {
											// Extract the "plain_text" field from the first rich_text item
											if richTextMap, ok := richTextItems[0].(map[string]interface{}); ok {
												if plainText, exists := richTextMap["plain_text"].(string); exists {
													values = append(values, plainText)
												}
											}
										}
									}
								}
							}
						}
					}
				}
			}
		}
	}

	// If no values were extracted, return a slice containing an empty string
	if len(values) == 0 {
		return []string{""}
	}

	return values
}

// GetRollupFormulaString attempts to retrieve a string from either a rollup-formula or plain formula property
func GetRollupFormulaString(props map[string]interface{}, key string) string {
	// Try rollup → array → formula → string
	if field, exists := props[key]; exists {
		if fieldMap, ok := field.(map[string]interface{}); ok {
			if rollupField, exists := fieldMap["rollup"]; exists {
				if rollupMap, ok := rollupField.(map[string]interface{}); ok {
					if arrayField, exists := rollupMap["array"]; exists {
						if arrayItems, ok := arrayField.([]interface{}); ok && len(arrayItems) > 0 {
							for _, item := range arrayItems {
								if itemMap, ok := item.(map[string]interface{}); ok {
									if formulaField, exists := itemMap["formula"]; exists {
										if formulaMap, ok := formulaField.(map[string]interface{}); ok {
											if textValue, exists := formulaMap["string"].(string); exists {
												return textValue
											}
										}
									}
								}
							}
						}
					}
				}
			}

			// Fallback: try plain formula → string
			if formulaField, exists := fieldMap["formula"]; exists {
				if formulaMap, ok := formulaField.(map[string]interface{}); ok {
					if textValue, exists := formulaMap["string"].(string); exists {
						return textValue
					}
				}
			}
		}
	}
	return ""
}

// GetRollupPageTitle fetches the title of the first page in a rollup relation
func GetRollupPageTitle(props map[string]interface{}, key string) string {
	if field, exists := props[key]; exists {
		if fieldMap, ok := field.(map[string]interface{}); ok {
			if rollup, exists := fieldMap["rollup"]; exists {
				if rollupMap, ok := rollup.(map[string]interface{}); ok {
					if array, exists := rollupMap["array"]; exists {
						if arrayItems, ok := array.([]interface{}); ok && len(arrayItems) > 0 {
							// We're expecting a relation inside the rollup
							if relMap, ok := arrayItems[0].(map[string]interface{}); ok {
								if relations, exists := relMap["relation"]; exists {
									if relArray, ok := relations.([]interface{}); ok && len(relArray) > 0 {
										if relItem, ok := relArray[0].(map[string]interface{}); ok {
											if id, exists := relItem["id"].(string); exists {
												// Now fetch the page using this ID
												return FetchTitleFromPageID(id)
											}
										}
									}
								}
							}
						}
					}
				}
			}
		}
	}
	return ""
}

// Extracts the first "name" from a Rollup -> Select property
func GetRollupSelectValue(props map[string]interface{}, key string) string {
	if field, exists := props[key]; exists {
		if fieldMap, ok := field.(map[string]interface{}); ok {
			if rollup, exists := fieldMap["rollup"].(map[string]interface{}); exists {
				if array, exists := rollup["array"].([]interface{}); exists && len(array) > 0 {
					if item, ok := array[0].(map[string]interface{}); ok {
						if selectField, exists := item["select"]; exists && selectField != nil {
							if selectMap, ok := selectField.(map[string]interface{}); ok {
								if name, exists := selectMap["name"].(string); exists {
									return name
								}
							}
						}
					}
				}
			}
		}
	}
	return ""
}

// FetchTitleFromPageID hits the Notion API to get the page title
func FetchTitleFromPageID(pageID string) string {
	url := fmt.Sprintf("https://api.notion.com/v1/pages/%s", pageID)
	req, _ := http.NewRequest("GET", url, nil)
	req.Header.Set("Authorization", "Bearer "+notionToken)
	req.Header.Set("Notion-Version", "2022-06-28")

	resp, err := client.Do(req)
	if err != nil {
		fmt.Println("❌ Error fetching related page:", err)
		return ""
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)

	var result map[string]interface{}
	if err := json.Unmarshal(body, &result); err != nil {
		fmt.Println("❌ Failed to parse page JSON:", err)
		return ""
	}

	// Get the title from the "Name" property
	if props, ok := result["properties"].(map[string]interface{}); ok {
		return GetName(props, "Name") // Reuse your existing helper
	}

	return ""
}


// GetValueByType extracts a property value using a registry-safe type name.
func GetValueByType(props map[string]interface{}, key string, valueType string) (string, error) {
	switch strings.TrimSpace(valueType) {
	case "rich_text":
		return GetPlainTextValue(props, key), nil
	case "number":
		return GetFloatValue(props, key), nil
	case "integer":
		return GetIntValue(props, key), nil
	case "select":
		return GetSelectValue(props, key), nil
	case "multi_select":
		return strings.Join(GetMultiSelectStrings(props, key), ", "), nil
	case "status":
		return GetStatus(props, key), nil
	case "date":
		return GetDateValue(props, key), nil
	case "url":
		return GetCleanURL(props, key), nil
	case "email":
		return GetCleanEmailValue(props, key), nil
	case "phone_number":
		return GetPhoneNumberValue(props, key), nil
	case "formula_string":
		return GetFormulaTextValue(props, key), nil
	case "formula_number":
		return fmt.Sprintf("%.2f", GetFormulaNumberValue(props, key)), nil
	case "rollup_text":
		return strings.Join(GetRollupPlainText(props, key), ", "), nil
	case "rollup_formula_string":
		return GetRollupFormulaString(props, key), nil
	default:
		return "", fmt.Errorf("unsupported registry field type %q", valueType)
	}
}
