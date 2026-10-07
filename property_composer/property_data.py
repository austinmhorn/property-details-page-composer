from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from .config import DATA_FILE


SECTION_FIELDS: dict[str, list[str]] = {
    "Quick Facts": [
        "Asset Status", "Prop No", "PMS ID", "Payroll ID", "Units", "Year Built",
        "Building Class", "Property Type", "Business Type", "Priority Group",
        "Groups", "Submarket", "Metro", "County",
    ],
    "Leasing & Policies": [
        "Income Req.", "Late Fee Max", "Lease Terms", "Cares Act / Days to File",
        "Resident Referral Maximum", "Unit Hold Times", "Units Displayed",
        "Deposit Alt", "Get 100", "Housing Units / Max Limit Set",
        "Maximum Allowed Employee Discount Units", "Reno Status",
        "Renovation Strategy & Online Leasing Display", "Special Note",
    ],
    "Property Team": [
        "Property Manager", "Regional Manager", "Area Manager",
        "Regional Vice President", "Regional Maintenance", "Asset Manager", "UBS",
        "Onsite Team Size",
    ],
    "Contacts": [
        "Landline", "PM Email", "APM Email", "Leasing Email",
        "Service Manager Email", "Customer Service Email", "Collateral Email",
        "Website Tracking Email", "Website Tracking Number", "Webex",
    ],
    "Portals & Resources": [
        "Website", "Prospect Portal Link", "Resident Portal Link",
        "Rental Criteria Link", "Community Information | Fee Sheet",
        "Link to Summary", "PEP Page",
    ],
    "Systems & Programs": [
        "AptLife", "Flex", "Spruce", "BlueMoon Exp.", "BlueMoon License ID",
        "Community Rewards", "Company Device", "MSA", "Possesion Partners",
        "RentPlus", "Package Locker", "Towing Company", "Rev Management",
        "PetScreening", "Amenify", "Bulk WiFi", "Voucher Program",
        "Website Host", "LeaseLock", "LeaseLock Cost", "Housing Connector",
        "Zumper GBP",
    ],
    "Marketing & Reviews": [
        "ApartmentRatings.com", "ApartmentGuide Review", "Apartments.com Review",
        "Facebook Review", "Google Review", "Facebook", "Instagram", "JTurner",
        "Website Design Template",
    ],
    "Property & Building Details": [
        "Address", "City", "State", "Zip", "Formerly Known As",
        "Gross Leasable SF", "Acres", "Units per Acre", "Buildings Count",
        "Stories", "Parking Spaces",
    ],
    "Administrative Details": [
        "EIN", "Owning Entity", "Acquisition Date", "Years Under Management",
        "Exec. Report Due Date", "Dispo Date",
    ],
}


def _clean(value: str | None) -> str:
    if value is None:
        return ""
    value = str(value).strip()
    if value.lower() in {"nan", "none", "null"}:
        return ""
    return value


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "property"


def _kind(label: str, value: str) -> str:
    lowered = value.lower()
    if lowered.startswith(("http://", "https://")):
        return "url"
    if "@" in value and " " not in value:
        return "email"
    if any(token in label.lower() for token in ("phone", "landline", "webex", "tracking number")):
        return "phone"
    return "text"


@dataclass(slots=True)
class Property:
    raw: dict[str, str]

    @property
    def name(self) -> str:
        return self.get("Property Name") or "Unnamed Property"

    @property
    def key(self) -> str:
        prop_no = self.get("Prop No")
        return prop_no or _slugify(self.name)

    @property
    def full_address(self) -> str:
        city_state = ", ".join(part for part in (self.get("City"), self.get("State")) if part)
        tail = " ".join(part for part in (city_state, self.get("Zip")) if part)
        return ", ".join(part for part in (self.get("Address"), tail) if part)

    def get(self, label: str) -> str:
        return _clean(self.raw.get(label))

    def quick_links(self) -> list[dict[str, str]]:
        labels = [
            ("Website", "Website"),
            ("Prospect Portal", "Prospect Portal Link"),
            ("Resident Portal", "Resident Portal Link"),
            ("Rental Criteria", "Rental Criteria Link"),
            ("Fee Sheet", "Community Information | Fee Sheet"),
            ("Property Summary", "Link to Summary"),
            ("PEP", "PEP Page"),
        ]
        return [
            {"label": display, "url": self.get(column)}
            for display, column in labels
            if self.get(column)
        ]

    def sections(self) -> list[dict[str, object]]:
        used = {"Property Name"}
        sections: list[dict[str, object]] = []

        for section_name, labels in SECTION_FIELDS.items():
            details = []
            for label in labels:
                used.add(label)
                value = self.get(label)
                if value:
                    details.append({
                        "label": label,
                        "value": value,
                        "kind": _kind(label, value),
                    })
            if details:
                sections.append({"name": section_name, "details": details})

        additional = []
        for label, raw_value in self.raw.items():
            if label in used:
                continue
            value = _clean(raw_value)
            if value:
                additional.append({
                    "label": label,
                    "value": value,
                    "kind": _kind(label, value),
                })
        if additional:
            sections.append({"name": "Additional Details", "details": additional})

        return sections


def load_properties(csv_path: Path | str = DATA_FILE) -> list[Property]:
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Property dataset not found: {path}. Run the Go fetch first."
        )

    properties: list[Property] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise RuntimeError(f"CSV has no header row: {path}")

        for row in reader:
            cleaned = {key: _clean(value) for key, value in row.items() if key}
            if cleaned.get("Property Name"):
                properties.append(Property(cleaned))

    properties.sort(key=lambda item: item.name.casefold())
    return properties


def find_property(properties: list[Property], query: str) -> Property:
    normalized = query.strip().casefold()

    exact = [
        prop for prop in properties
        if prop.name.casefold() == normalized or prop.key.casefold() == normalized
    ]
    if len(exact) == 1:
        return exact[0]

    partial = [prop for prop in properties if normalized in prop.name.casefold()]
    if len(partial) == 1:
        return partial[0]
    if not partial:
        raise LookupError(f"No property matched {query!r}")

    names = ", ".join(prop.name for prop in partial[:8])
    raise LookupError(f"Property query {query!r} is ambiguous: {names}")
