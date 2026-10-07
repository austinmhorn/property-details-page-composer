package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"property-details-page-composer/notionapi"
)

type FieldDefinition struct {
	Header    string `json:"header"`
	NotionKey string `json:"notion_key"`
	Type      string `json:"type"`
}

type FieldRegistry struct {
	Version int               `json:"version"`
	Fields  []FieldDefinition `json:"fields"`
}

func loadFieldRegistry(projectRoot string) (FieldRegistry, error) {
	path := filepath.Join(projectRoot, "config", "property_fields.json")
	data, err := os.ReadFile(path)
	if err != nil {
		return FieldRegistry{}, fmt.Errorf("read property field registry: %w", err)
	}

	var registry FieldRegistry
	if err := json.Unmarshal(data, &registry); err != nil {
		return FieldRegistry{}, fmt.Errorf("parse property field registry: %w", err)
	}

	if registry.Version != 1 {
		return FieldRegistry{}, fmt.Errorf("unsupported property field registry version %d", registry.Version)
	}

	seen := map[string]bool{}
	for i, field := range registry.Fields {
		field.Header = strings.TrimSpace(field.Header)
		field.NotionKey = strings.TrimSpace(field.NotionKey)
		field.Type = strings.TrimSpace(field.Type)

		if field.Header == "" || field.NotionKey == "" || field.Type == "" {
			return FieldRegistry{}, fmt.Errorf("field registry entry %d is incomplete", i+1)
		}
		if seen[field.Header] {
			return FieldRegistry{}, fmt.Errorf("duplicate registry header %q", field.Header)
		}
		seen[field.Header] = true
		registry.Fields[i] = field
	}

	return registry, nil
}

func registryHeaders(registry FieldRegistry) []string {
	headers := make([]string, 0, len(registry.Fields))
	for _, field := range registry.Fields {
		headers = append(headers, field.Header)
	}
	return headers
}

func registryValues(
	registry FieldRegistry,
	props map[string]interface{},
) ([]string, error) {
	values := make([]string, 0, len(registry.Fields))

	for _, field := range registry.Fields {
		value, err := notionapi.GetValueByType(
			props,
			field.NotionKey,
			field.Type,
		)
		if err != nil {
			return nil, fmt.Errorf(
				"extract %q (%s): %w",
				field.NotionKey,
				field.Type,
				err,
			)
		}
		values = append(values, value)
	}

	return values, nil
}
