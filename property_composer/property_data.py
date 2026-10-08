from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path

from .config import DATA_FILE, FIELD_METADATA_FILE


SENSITIVE_FIELDS = {
    "Property #",
    "Prop No",
    "PMS ID",
    "Asset Status",
    "Payroll ID",
    "Maximum Allowed Employee Discount Units",
    "EIN",
    "Owning Entity",
    "Exec. Report Due Date",
    "Priority Group",
}

SECTION_FIELDS: dict[str, list[str]] = {
    "Quick Facts": [
        "Units", "Year Built",
        "Building Class", "Property Type", "Business Type",
        "Groups", "Submarket", "Metro", "County",
    ],
    "Leasing & Policies": [
        "Income Req.", "Late Fee Max", "Lease Terms", "Cares Act / Days to File",
        "Resident Referral Maximum", "Unit Hold Times", "Units Displayed",
        "Deposit Alt", "Get 100", "Housing Units / Max Limit Set",
        "Reno Status",
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
        "Acquisition Date", "Years Under Management", "Dispo Date",
    ],
}

@dataclass(slots=True)
class InteractField:
    csv_header: str
    category: str
    label: str
    order: int = 0


def load_interact_field_metadata(
    metadata_path: Path | str = FIELD_METADATA_FILE,
) -> tuple[dict[str, InteractField], set[str]]:
    path = Path(metadata_path)

    if not path.exists():
        return {}, set()

    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if payload.get("version") != 1:
        raise RuntimeError(
            f"Unsupported property field metadata version in {path}"
        )

    fields = payload.get("fields")
    if not isinstance(fields, list):
        raise RuntimeError(
            f"Property field metadata has no fields list: {path}"
        )

    visible: dict[str, InteractField] = {}
    managed_headers: set[str] = set()

    for item in fields:
        if not isinstance(item, dict):
            continue

        header = _clean(item.get("csv_header"))
        if not header:
            continue

        managed_headers.add(header)

        if item.get("display_in_interact") is not True:
            continue

        category = _clean(item.get("interact_category"))
        label = _clean(item.get("interact_label")) or header

        if not category:
            category = "Additional Details"

        try:
            order = int(item.get("interact_order") or 0)
        except (TypeError, ValueError):
            order = 0

        visible[header] = InteractField(
            csv_header=header,
            category=category,
            label=label,
            order=order,
        )

    return visible, managed_headers



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


def _external_url(value: str) -> str:
    value = _clean(value)
    if not value:
        return ""
    if value.lower().startswith(("http://", "https://")):
        return value
    return f"https://{value}"


def _include_property_name(name: str) -> bool:
    normalized = _clean(name).casefold()
    if not normalized:
        return False
    if normalized.startswith(("x_", "z_")):
        return False
    if normalized == "corporate office":
        return False
    return True


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
            {"label": display, "url": _external_url(self.get(column))}
            for display, column in labels
            if self.get(column)
        ]

    def sections(
        self,
        interact_fields: dict[str, InteractField] | None = None,
        managed_headers: set[str] | None = None,
    ) -> list[dict[str, object]]:
        interact_fields = interact_fields or {}
        managed_headers = managed_headers or set()

        used = {"Property Name"} | SENSITIVE_FIELDS | managed_headers
        section_details: dict[str, list[dict[str, object]]] = {}

        for section_name, labels in SECTION_FIELDS.items():
            details: list[dict[str, object]] = []

            for label in labels:
                used.add(label)
                value = self.get(label)

                if value:
                    details.append({
                        "label": label,
                        "value": value,
                        "kind": _kind(label, value),
                    })

            section_details[section_name] = details

        dynamic_by_category: dict[str, list[tuple[int, dict[str, object]]]] = {}

        for header, metadata in interact_fields.items():
            value = self.get(header)

            if not value:
                continue

            dynamic_by_category.setdefault(
                metadata.category,
                [],
            ).append(
                (
                    metadata.order,
                    {
                        "label": metadata.label,
                        "value": value,
                        "kind": _kind(metadata.label, value),
                    },
                )
            )

        for category, items in dynamic_by_category.items():
            items.sort(
                key=lambda item: (
                    item[0],
                    str(item[1]["label"]).casefold(),
                )
            )

            section_details.setdefault(
                category,
                [],
            ).extend(
                detail
                for _, detail in items
            )

        additional: list[dict[str, object]] = []

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
            section_details.setdefault(
                "Additional Details",
                [],
            ).extend(additional)

        ordered_names = list(SECTION_FIELDS)

        for category in section_details:
            if (
                category not in ordered_names
                and category != "Additional Details"
            ):
                ordered_names.append(category)

        if "Additional Details" in section_details:
            ordered_names.append("Additional Details")

        sections: list[dict[str, object]] = []

        seen_names: set[str] = set()
        for section_name in ordered_names:
            if section_name in seen_names:
                continue

            seen_names.add(section_name)
            details = section_details.get(
                section_name,
                [],
            )

            if details:
                sections.append({
                    "name": section_name,
                    "details": details,
                })

        return sections


def load_properties(csv_path: Path | str = DATA_FILE) -> list[Property]:
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Property dataset not found: {path}. Refresh Property Data Engine artifacts first."
        )

    properties: list[Property] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise RuntimeError(f"CSV has no header row: {path}")

        for row in reader:
            cleaned = {key: _clean(value) for key, value in row.items() if key}
            property_name = cleaned.get("Property Name", "")
            if _include_property_name(property_name):
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
