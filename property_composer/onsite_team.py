"""Validated, opt-in PDE onsite team artifact for the Property Team section."""
from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path

from .config import DATA_DIR

ARTIFACT = DATA_DIR / "property_onsite_team.json"


def onsite_team_enabled() -> bool:
    return os.getenv("COMPOSER_ONSITE_TEAM_ENABLED", "").strip() == "1"


def _group_staff(associates: list[dict]) -> list[dict[str, str]]:
    grouped: dict[str, dict[str, object]] = {}
    for person in associates:
        if not isinstance(person, dict):
            raise ValueError("Invalid onsite team associate entry")
        title = str(person.get("title") or "").strip()
        name = str(person.get("name") or "").strip()
        if not title or not name:
            raise ValueError("Onsite team entries require a title and preferred name")
        if " ".join(title.casefold().split()) == "property manager":
            continue  # PM has a dedicated, authoritative Notion/registry field.
        key = " ".join(title.casefold().split())
        if key not in grouped:
            grouped[key] = {"title": title, "names": {}}
        names = grouped[key]["names"]
        names[name.casefold()] = name
    return [
        {"label": grouped[title]["title"],
         "value": ", ".join(
             grouped[title]["names"][key]
             for key in sorted(grouped[title]["names"])
         ),
         "kind": "text"}
        for title in sorted(grouped)
    ]


def load_onsite_team(path: Path = ARTIFACT) -> dict[str, list[dict[str, str]]]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing enabled onsite team artifact: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != 1 or not isinstance(data.get("properties"), dict):
        raise ValueError("Unsupported onsite team artifact version")
    result = {}
    for pid, record in data["properties"].items():
        if not isinstance(record, dict):
            raise ValueError(f"Invalid onsite roster for property {pid}")
        name = str(record.get("property_name") or "").strip()
        associates = record.get("associates")
        if not name or not isinstance(associates, list):
            raise ValueError(f"Incomplete onsite roster for property {pid}")
        key = name.casefold()
        if key in result:
            raise ValueError(f"Duplicate Property name in onsite roster artifact: {name}")
        result[key] = _group_staff(associates)
    return result
