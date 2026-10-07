#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path

import requests
from dotenv import load_dotenv


PROJECT_DIR = Path(__file__).resolve().parent.parent
REGISTRY_PATH = PROJECT_DIR / "config" / "property_fields.json"
ENV_PATH = PROJECT_DIR / "secrets" / ".env"

SUPPORTED_TYPES = {
    "rich_text": {"notion_types": {"rich_text"}, "label": "Text"},
    "number": {"notion_types": {"number"}, "label": "Number / Decimal"},
    "integer": {"notion_types": {"number"}, "label": "Whole Number"},
    "select": {"notion_types": {"select"}, "label": "Select"},
    "multi_select": {"notion_types": {"multi_select"}, "label": "Multi-select"},
    "status": {"notion_types": {"status"}, "label": "Status"},
    "date": {"notion_types": {"date"}, "label": "Date"},
    "url": {"notion_types": {"url"}, "label": "URL"},
    "email": {"notion_types": {"email"}, "label": "Email"},
    "phone_number": {"notion_types": {"phone_number"}, "label": "Phone Number"},
    "formula_string": {"notion_types": {"formula"}, "label": "Formula → Text"},
    "formula_number": {"notion_types": {"formula"}, "label": "Formula → Number"},
    "rollup_text": {"notion_types": {"rollup"}, "label": "Rollup → Text"},
    "rollup_formula_string": {"notion_types": {"rollup"}, "label": "Rollup → Formula Text"},
}


def load_registry() -> dict:
    with REGISTRY_PATH.open("r", encoding="utf-8") as handle:
        registry = json.load(handle)

    if registry.get("version") != 1:
        raise ValueError("Unsupported property field registry version.")

    fields = registry.get("fields")
    if not isinstance(fields, list):
        raise ValueError("Registry fields must be a list.")

    return registry


def save_registry(registry: dict) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=REGISTRY_PATH.parent,
        delete=False,
    ) as handle:
        json.dump(registry, handle, indent=2)
        handle.write("\n")
        temporary_path = Path(handle.name)

    temporary_path.replace(REGISTRY_PATH)


def notion_credentials() -> tuple[str, str]:
    load_dotenv(ENV_PATH)

    token = os.getenv("NOTION_TOKEN", "").strip()
    database_id = os.getenv("NOTION_DATABASE_ID", "").strip()

    if not token or not database_id:
        raise RuntimeError(
            "NOTION_TOKEN and NOTION_DATABASE_ID are required in secrets/.env."
        )

    return token, database_id


def fetch_schema() -> dict:
    token, database_id = notion_credentials()

    response = requests.get(
        f"https://api.notion.com/v1/databases/{database_id}",
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2022-06-28",
        },
        timeout=30,
    )
    response.raise_for_status()

    payload = response.json()
    properties = payload.get("properties")
    if not isinstance(properties, dict):
        raise RuntimeError("Notion database schema did not include properties.")

    return properties


def validate_field(name: str, registry_type: str, schema: dict | None = None) -> dict:
    name = name.strip()
    registry_type = registry_type.strip()

    if not name:
        raise ValueError("Notion property name is required.")

    if registry_type not in SUPPORTED_TYPES:
        raise ValueError(f"Unsupported property type: {registry_type}")

    if schema is None:
        schema = fetch_schema()

    definition = schema.get(name)
    if not isinstance(definition, dict):
        raise ValueError(f'Notion property "{name}" was not found in the database schema.')

    notion_type = str(definition.get("type") or "").strip()
    allowed_types = SUPPORTED_TYPES[registry_type]["notion_types"]

    if notion_type not in allowed_types:
        expected = ", ".join(sorted(allowed_types))
        raise ValueError(
            f'Notion property "{name}" is type "{notion_type}", '
            f'but "{registry_type}" expects: {expected}.'
        )

    return {
        "name": name,
        "registry_type": registry_type,
        "label": SUPPORTED_TYPES[registry_type]["label"],
        "notion_type": notion_type,
    }


def core_headers() -> set[str]:
    source = (PROJECT_DIR / "main.go").read_text(encoding="utf-8")
    marker = "headers := []string{"
    start = source.find(marker)

    if start < 0:
        raise RuntimeError("Unable to locate the core CSV header definition in main.go.")

    block = source[start + len(marker):]
    end = block.find("\n\t}")
    if end < 0:
        raise RuntimeError("Unable to parse the core CSV header definition in main.go.")

    return {
        value.casefold()
        for value in re.findall(r'"([^"]+)"', block[:end])
    }


def add_field(name: str, registry_type: str) -> dict:
    registry = load_registry()
    normalized_name = name.strip().casefold()

    if normalized_name in core_headers():
        raise ValueError(
            f'"{name.strip()}" is already part of the core Property Details export.'
        )

    for field in registry["fields"]:
        if str(field.get("header", "")).casefold() == normalized_name:
            raise ValueError(f'"{name.strip()}" is already registered.')

    validation = validate_field(name, registry_type)

    field = {
        "header": validation["name"],
        "notion_key": validation["name"],
        "type": validation["registry_type"],
    }
    registry["fields"].append(field)
    save_registry(registry)

    return field


def remove_field(name: str) -> bool:
    registry = load_registry()
    target = name.strip().casefold()

    original = len(registry["fields"])
    registry["fields"] = [
        field
        for field in registry["fields"]
        if str(field.get("header", "")).casefold() != target
    ]

    if len(registry["fields"]) == original:
        return False

    save_registry(registry)
    return True


def print_json(value) -> None:
    print(json.dumps(value, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate and manage self-service Property Details fields."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list")
    subparsers.add_parser("types")
    subparsers.add_parser("schema")

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--name", required=True)
    validate_parser.add_argument("--type", required=True, dest="registry_type")

    add_parser = subparsers.add_parser("add")
    add_parser.add_argument("--name", required=True)
    add_parser.add_argument("--type", required=True, dest="registry_type")

    remove_parser = subparsers.add_parser("remove")
    remove_parser.add_argument("--name", required=True)

    args = parser.parse_args()

    try:
        if args.command == "list":
            print_json(load_registry())
        elif args.command == "types":
            print_json(
                [
                    {"value": key, "label": value["label"]}
                    for key, value in SUPPORTED_TYPES.items()
                ]
            )
        elif args.command == "schema":
            schema = fetch_schema()
            print_json(
                [
                    {
                        "name": name,
                        "notion_type": definition.get("type"),
                    }
                    for name, definition in sorted(schema.items())
                ]
            )
        elif args.command == "validate":
            print_json(validate_field(args.name, args.registry_type))
        elif args.command == "add":
            field = add_field(args.name, args.registry_type)
            print_json({"ok": True, "field": field})
        elif args.command == "remove":
            removed = remove_field(args.name)
            if not removed:
                raise ValueError(f'"{args.name}" is not registered.')
            print_json({"ok": True, "removed": args.name.strip()})
    except (ValueError, RuntimeError, OSError, requests.RequestException) as error:
        print_json({"ok": False, "error": str(error)})
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
