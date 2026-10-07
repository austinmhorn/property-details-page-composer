package main

import (
	"encoding/csv"
	"fmt"
	"os"
	"path/filepath"
	"property-details-page-composer/notionapi"
	"time"
)


func writeLastUpdated() {
	// Get current timestamp
	timestamp := time.Now().Format("01/02/2006 - 15:04:05")

	// Write timestamp to a second CSV file
	lastUpdatedFile := "last_updated.csv"
	csvFile, err := os.Create(lastUpdatedFile)
	if err != nil {
		fmt.Println("❌ ERROR: Creating Last Updated CSV file:", err)
		return
	}
	defer csvFile.Close()

	writer := csv.NewWriter(csvFile)
	defer writer.Flush()

	writer.Write([]string{"Last Updated", timestamp})

	fmt.Printf("✅ Timestamp successfully written to %s!\n", lastUpdatedFile)
}

// Main function
func main() {
	projectRoot, err := notionapi.ProjectRoot()
	if err != nil {
		fmt.Println("❌ Error locating project root:", err)
		return
	}

	outputFile := filepath.Join(projectRoot, "data", "notion_data_unsorted.csv")
	if err := os.MkdirAll(filepath.Dir(outputFile), 0755); err != nil {
		fmt.Println("❌ Error creating data directory:", err)
		return
	}

	// Load configuration first.
	err = notionapi.LoadConfig()
	if err != nil {
		fmt.Println("❌ Error loading config:", err)
		return
	}

	fmt.Println("🚀 Fetching Notion Data...")
	data, err := notionapi.FetchNotionData()
	if err != nil {
		fmt.Println("❌ Error fetching data from Notion:", err)
		return
	}

	totalEntries := len(data)
	if totalEntries == 0 {
		fmt.Println("❌ No data found in Notion.")
		return
	}

	fmt.Printf("✅ Successfully retrieved %d entries from Notion.\n", totalEntries)

	// Save data to CSV
	csvFileName := outputFile
	csvFile, err := os.Create(csvFileName)
	if err != nil {
		fmt.Println("❌ ERROR: Creating CSV file:", err)
		return
	}
	defer csvFile.Close()

	writer := csv.NewWriter(csvFile)
	defer writer.Flush()

	headers := []string{"Property Name",
		"Asset Status",
		"Prop No",
		"Payroll ID",
		"PMS ID",
		"Year Built",
		"Units",
		"Priority Group",
		"Groups",
		"Website",
		"Address",
		"City",
		"State",
		"Zip",
		"Submarket",
		"Metro",
		"County",
		"Regional Vice President",
		"Regional Manager",
		"Area Manager",
		"UBS",
		"Regional Maintenance",
		"Asset Manager",
		"EIN",
		"Owning Entity",
		"Business Type",
		"Acquisition Date",
		"Years Under Management",
		"Formerly Known As",
		"Landline",
		"ApartmentRatings.com",
		"ApartmentGuide Review",
		"Apartments.com Review",
		"JTurner",
		"AptLife",
		"Flex",
		"Spruce",
		"BlueMoon Exp.",
		"BlueMoon License ID",
		"Cares Act / Days to File",
		"Community Rewards",
		"Company Device",
		"Facebook Review",
		"Facebook",
		"Instagram",
		"Google Review",
		"Income Req.",
		"Late Fee Max",
		"Lease Terms",
		"MSA",
		"Possesion Partners",
		"Prospect Portal Link",
		"Resident Portal Link",
		"Rental Criteria Link",
		"Community Information | Fee Sheet",
		"Reno Status",
		"Renovation Strategy & Online Leasing Display",
		"RentPlus",
		"Resident Referral Maximum",
		"Package Locker",
		"Towing Company",
		"Unit Hold Times",
		"Units Displayed",
		"Zumper GBP",
		"Deposit Alt",
		"Get 100",
		"Rev Management",
		"PM Email",
		"APM Email",
		"Leasing Email",
		"Service Manager Email",
		"Website Tracking Email",
		"Website Tracking Number",
		"Customer Service Email",
		"Property Manager",
		"PetScreening",
		"Link to Summary",
		"Property Type",
		"Special Note",
		"Building Class",
		"CoStar Building Rating",
		"Gross Leasable SF",
		"Acres",
		"Units per Acre",
		"Buildings Count",
		"Stories",
		"Parking Spaces",
		"Exec. Report Due Date",
		"Amenify",
		"Housing Units / Max Limit Set",
		"Bulk WiFi",
		"Voucher Program",
		"Website Host",
		"Webex",
		"LeaseLock",
		"LeaseLock Cost",
		"Onsite Team Size",
		"Dispo Date",
		"Housing Connector",
		"Maximum Allowed Employee Discount Units",
		"PEP Page",
		"Website Design Template",
	}
	writer.Write(headers)

	// Process each entry
	for i, entry := range data {
		props, ok := entry["properties"].(map[string]interface{})
		if !ok {
			fmt.Printf("⚠️ Skipping entry %d: Invalid properties format.\n", i+1)
			continue
		}

		nameStr := notionapi.GetName(props, "Name")
		statusStr := notionapi.GetStatus(props, "Asset Status")
		propNoStr := notionapi.GetIntValue(props, "Prop No")
		payrollIDStr := notionapi.GetIntValue(props, "Payroll ID")
		pmsIDStr := notionapi.GetIntValue(props, "PMS ID")
		yearBuiltStr := notionapi.GetPlainTextValue(props, "Year Built")
		unitsStr := notionapi.GetIntValue(props, "Units")
		priorityGroupStr := notionapi.GetStatus(props, "Priority Group")
		groupsStr := notionapi.GetSelectValue(props, "Groups")
		websiteStr := notionapi.GetURLValue(props, "Website")
		addressStr := notionapi.GetPlainTextValue(props, "Address")
		cityStr := notionapi.GetFormulaTextValue(props, "City (As Text)")
		stateStr := notionapi.GetFormulaTextValue(props, "State (As Text)")
		zipStr := notionapi.GetIntValue(props, "Zip")
		submarketStr := notionapi.GetPlainTextValue(props, "Submarket")
		metroStr := notionapi.GetRollupPlainText(props, "Metro")
		countyStr := notionapi.GetRollupPlainText(props, "County")
		regionalVicePresidentStr := notionapi.GetRollupFormulaString(props, "Regional Vice President (As Text)")
		regonalManagerStr := notionapi.GetRollupFormulaString(props, "Regional Manager (As Text)")
		areaManagerStr := notionapi.GetRollupFormulaString(props, "Area Manager (As Text)")
		ubsStr := notionapi.GetSelectValue(props, "UBS")
		regionalMaintenanceStr := notionapi.GetRollupFormulaString(props, "Regional Maintenance (As Text)")
		assetManagerStr := notionapi.GetRollupFormulaString(props, "Asset Manager (As Text)")
		einStr := notionapi.GetPlainTextValue(props, "EIN")
		owningEntityStr := notionapi.GetPlainTextValue(props, "Owning Entity")
		businessTypeStr := notionapi.GetSelectValue(props, "Business Type")
		acquisitionDateStr := notionapi.GetDateValue(props, "Acquisition Date")
		yearsUnderManagementStr := fmt.Sprintf("%.2f", notionapi.GetFormulaNumberValue(props, "Years Under Management"))
		formerlyKnownAsStr := notionapi.GetPlainTextValue(props, "Formerly Known As")
		landlineStr := notionapi.GetPhoneNumberValue(props, "Landline")
		apartmentRatingsStr := notionapi.GetCleanURL(props, "ApartmentRatings.com")
		apartmentGuideStr := notionapi.GetCleanURL(props, "ApartmentGuide Review")
		apartmentsDotComReviewStr := notionapi.GetCleanURL(props, "Apartments.com Review")
		jTurnerStr := notionapi.GetDateValue(props, "JTurner")
		aptLifeStr := notionapi.GetPlainTextValue(props, "AptLife")
		flexStr := notionapi.GetDateValue(props, "Flex")
		spruceStr := notionapi.GetPlainTextValue(props, "Spruce")
		blueMoonExpStr := notionapi.GetDateValue(props, "BlueMoon Exp.")
		blueMoonLicenseIDStr := notionapi.GetPlainTextValue(props, "BlueMoon License ID")
		caresActDaysToFileStr := notionapi.GetIntValue(props, "Cares Act / Days to File")
		communityRewardsStr := notionapi.GetDateValue(props, "Community Rewards")
		companyDeviceStr := notionapi.GetIntValue(props, "Company Device")
		facebookReviewStr := notionapi.GetCleanURL(props, "Facebook Review")
		facebookStr := notionapi.GetCleanURL(props, "Facebook")
		instagramStr := notionapi.GetCleanURL(props, "Instagram")
		googleReviewStr := notionapi.GetCleanURL(props, "Google Review")
		incomeReqStr := notionapi.GetSelectValue(props, "Income Req.")
		lateFeeMaxStr := notionapi.GetSelectValue(props, "Late Fee Max")
		leaseTermsStr := notionapi.GetSelectValue(props, "Lease Terms")
		msaStr := notionapi.GetPlainTextValue(props, "MSA")
		possesionsPartnersStr := notionapi.GetSelectValue(props, "Possesion Partners")
		prospectPortalLinkStr := notionapi.GetCleanURL(props, "Prospect Portal Link")
		residentPortalLinkStr := notionapi.GetCleanURL(props, "Resident Portal Link")
		rentalCriteriaLinkStr := notionapi.GetCleanURL(props, "Rental Criteria Link")
		communityInfoFeeSheetStr := notionapi.GetCleanURL(props, "Community Information | Fee Sheet")
		renoStatusStr := notionapi.GetSelectValue(props, "Reno Status")
		renovationStrategyAndOnlineLeasingDisplayStr := notionapi.GetPlainTextValue(props, "Renovation Strategy & Online Leasing Display")
		rentPlusStr := notionapi.GetSelectValue(props, "RentPlus")
		residentReferralMaximumStr := notionapi.GetSelectValue(props, "Resident Referral Maximum")
		packageLockerStr := notionapi.GetPlainTextValue(props, "Package Locker")
		towingCompanyStr := notionapi.GetPlainTextValue(props, "Towing Company")
		unitHoldTimesStr := notionapi.GetSelectValue(props, "Unit Hold Times")
		unitsDisplayed := notionapi.GetIntValue(props, "Units Displayed")
		zumperGBPStr := notionapi.GetDateValue(props, "Zumper GBP")
		depositAltStr := notionapi.GetSelectValue(props, "Deposit Alt")
		get100Str := notionapi.GetSelectValue(props, "Get 100")
		revManagementStr := notionapi.GetPlainTextValue(props, "Rev Management")
		pmEmailStr := notionapi.GetCleanEmailValue(props, "PM Email")
		apmEmailStr := notionapi.GetCleanEmailValue(props, "APM Email")
		leasingEmailStr := notionapi.GetCleanEmailValue(props, "Leasing Email")
		serviceManagerEmailStr := notionapi.GetCleanEmailValue(props, "Service Manager Email")
		websiteTrackingEmailStr := notionapi.GetCleanEmailValue(props, "Website Tracking Email")
		websiteTrackingNumberStr := notionapi.GetPhoneNumberValue(props, "Website Tracking Number")
		customerServiceEmailStr := notionapi.GetCleanEmailValue(props, "Customer Service Email")
		propertyManagerStr := notionapi.GetFormulaTextValue(props, "Property Manager (As Text)")
		petScreeningStr := notionapi.GetPlainTextValue(props, "PetScreening")
		linkToSummaryStr := notionapi.GetCleanURL(props, "Link to Summary")
		propertyTypeStr := notionapi.GetSelectValue(props, "Property Type")
		specialNoteStr := notionapi.GetPlainTextValue(props, "Special Note")
		buildingClassStr := notionapi.GetSelectValue(props, "Building Class")
		costarBuildingRating := notionapi.GetSelectValue(props, "CoStar Building Rating")
		grossLeasableSFStr := notionapi.GetIntValue(props, "Gross Leasable SF")
		acresStr := notionapi.GetFloatValue(props, "Acres")
		unitsPerAcreStr := notionapi.GetFloatValue(props, "Units per Acre")
		buildingsCountStr := notionapi.GetIntValue(props, "Buildings Count")
		storiesStr := notionapi.GetIntValue(props, "Stories")
		parkingSpacesStr := notionapi.GetIntValue(props, "Parking Spaces")
		execReportDueDate := notionapi.GetPlainTextValue(props, "Exec. Report Due Date")
		amenifyStr := notionapi.GetDateValue(props, "Amenify")
		housingUnitsMaxLimitSetStr := notionapi.GetPlainTextValue(props, "Housing Units / Max Limit Set")
		bulkStr := notionapi.GetPlainTextValue(props, "Bulk WiFi")
		voucherProgramStr := notionapi.GetDateValue(props, "Voucher Program")
		websiteHostStr := notionapi.GetSelectValue(props, "Website Host")
		webexStr := notionapi.GetPhoneNumberValue(props, "Webex")
		leaselockStr := notionapi.GetDateValue(props, "LeaseLock")
		leaselockCostStr := notionapi.GetFloatValue(props, "LeaseLock Cost")
		onsiteTeamSizeStr := fmt.Sprintf("%.0f", notionapi.GetFormulaNumberValue(props, "Onsite Team Size"))
		dispoDateStr := notionapi.GetDateValue(props, "Dispo Date")
		housingConnectorStr := notionapi.GetDateValue(props, "Housing Connector")
		maximumAllowedEmployeeDiscountUnitsStr := fmt.Sprintf("%.1f", notionapi.GetFormulaNumberValue(props, "Maximum Allowed Employee Discount Units"))
		pepPageStr := notionapi.GetCleanURL(props, "PEP Page")
		websiteDesignTemplateStr := notionapi.GetSelectValue(props, "Website Design Template")

		row := []string{
			nameStr,
			statusStr,
			propNoStr,
			payrollIDStr,
			pmsIDStr,
			yearBuiltStr,
			unitsStr,
			priorityGroupStr,
			groupsStr,
			websiteStr,
			addressStr,
			cityStr,
			stateStr,
			zipStr,
			submarketStr,
			metroStr[0],  // Assuming metroStr is a slice, take the first element
			countyStr[0], // Assuming countyStr is a slice, take the first element
			regionalVicePresidentStr,
			regonalManagerStr,
			areaManagerStr,
			ubsStr,
			regionalMaintenanceStr,
			assetManagerStr,
			einStr,
			owningEntityStr,
			businessTypeStr,
			acquisitionDateStr,
			yearsUnderManagementStr,
			formerlyKnownAsStr,
			landlineStr,
			apartmentRatingsStr,
			apartmentGuideStr,
			apartmentsDotComReviewStr,
			jTurnerStr,
			aptLifeStr,
			flexStr,
			spruceStr,
			blueMoonExpStr,
			blueMoonLicenseIDStr,
			caresActDaysToFileStr,
			communityRewardsStr,
			companyDeviceStr,
			facebookReviewStr,
			facebookStr,
			instagramStr,
			googleReviewStr,
			incomeReqStr,
			lateFeeMaxStr,
			leaseTermsStr,
			msaStr,
			possesionsPartnersStr,
			prospectPortalLinkStr,
			residentPortalLinkStr,
			rentalCriteriaLinkStr,
			communityInfoFeeSheetStr,
			renoStatusStr,
			renovationStrategyAndOnlineLeasingDisplayStr,
			rentPlusStr,
			residentReferralMaximumStr,
			packageLockerStr,
			towingCompanyStr,
			unitHoldTimesStr,
			unitsDisplayed,
			zumperGBPStr,
			depositAltStr,
			get100Str,
			revManagementStr,
			pmEmailStr,
			apmEmailStr,
			leasingEmailStr,
			serviceManagerEmailStr,
			websiteTrackingEmailStr,
			websiteTrackingNumberStr,
			customerServiceEmailStr,
			propertyManagerStr,
			petScreeningStr,
			linkToSummaryStr,
			propertyTypeStr,
			specialNoteStr,
			buildingClassStr,
			costarBuildingRating,
			grossLeasableSFStr,
			acresStr,
			unitsPerAcreStr,
			buildingsCountStr,
			storiesStr,
			parkingSpacesStr,
			execReportDueDate,
			amenifyStr,
			housingUnitsMaxLimitSetStr,
			bulkStr,
			voucherProgramStr,
			websiteHostStr,
			webexStr,
			leaselockStr,
			leaselockCostStr,
			onsiteTeamSizeStr,
			dispoDateStr,
			housingConnectorStr,
			maximumAllowedEmployeeDiscountUnitsStr,
			pepPageStr,
			websiteDesignTemplateStr,
		}
		writer.Write(row)

		// Print progress
		fmt.Printf("📊 Progress: %d/%d (%.2f%%)\n", i+1, totalEntries, float64(i+1)/float64(totalEntries)*100)
	}

	writer.Flush()
	if err := writer.Error(); err != nil {
		fmt.Println("❌ ERROR: Writing CSV:", err)
		return
	}

	fmt.Printf("✅ Data successfully written to %s!\n", csvFileName)

	// Write last updated timestamp
	//writeLastUpdated()
}
