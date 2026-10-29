"""Verify that PDE v3 artifacts belong to one published extraction."""
from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path

REQUIRED = ("notion_data.csv", "property_fees.json", "property_fields.json")
MANIFEST = "pde_v3_manifest.json"


def verify_manifest(directory: Path) -> dict:
    path = directory / MANIFEST
    if not path.is_file():
        raise FileNotFoundError(f"Missing coordinated PDE v3 manifest: {path}")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1:
        raise ValueError("Unsupported PDE v3 manifest version")
    try:
        uuid.UUID(manifest["run_id"])
    except (KeyError, ValueError, TypeError) as exc:
        raise ValueError("Invalid PDE v3 extraction run ID") from exc
    if not manifest.get("created_at"):
        raise ValueError("Missing extraction timestamp")
    entries = manifest.get("artifacts")
    if not isinstance(entries, dict):
        raise ValueError("Missing artifact checksums")
    for name in REQUIRED:
        entry = entries.get(name)
        if not isinstance(entry, dict) or not isinstance(entry.get("sha256"), str):
            raise ValueError(f"Missing expected hash for {name}")
        source = directory / name
        if not source.is_file():
            raise FileNotFoundError(f"Missing PDE v3 artifact: {source}")
        data = source.read_bytes()
        if hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise ValueError(f"PDE v3 checksum mismatch: {name}")
        if len(data) != entry.get("size"):
            raise ValueError(f"PDE v3 artifact size mismatch: {name}")
    return manifest
