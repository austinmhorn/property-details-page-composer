"""Read the PDE v3 related-fee artifact for the Composer Details view.

Never infer a fee from a legacy CSV formula field. The artifact is joined
using the verified property name carried by PDE's Property ID/name lookup.
"""
from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path
from decimal import Decimal, InvalidOperation

from .config import DATA_DIR
from .property_data import _currency


FEE_FILE = DATA_DIR / "property_fees.json"


def _negative_amount(value: object) -> bool:
    if value is None or str(value).strip() == "":
        return False
    try:
        return Decimal(str(value).replace("$", "").replace(",", "").strip()) < 0
    except (InvalidOperation, ValueError):
        return False


def _security_deposit_label(name: str, variant: str) -> str:
    if name.strip().casefold() != "security deposit":
        return name
    method = variant.casefold()
    if "conditional" in method:
        return f"{name} (Conditional)"
    if "standard" in method:
        return f"{name} (Standard)"
    return name

def fee_source() -> str:
    """Explicit opt-in. An artifact alone never activates v3."""
    source = os.getenv("COMPOSER_FEE_SOURCE", "legacy").strip().lower()
    if source not in ("legacy", "v3"):
        raise ValueError("COMPOSER_FEE_SOURCE must be 'legacy' or 'v3'")
    return source



def load_fee_sections(path: Path = FEE_FILE) -> dict[str, list[dict]]:
    if not path.is_file():
        raise FileNotFoundError(f"V3 fee artifact required: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != 3 or not isinstance(data.get("properties"), dict):
        raise ValueError("Unsupported PDE related fee artifact")
    overlaps = {
        (w.get("property_id"), w.get("fee_key"))
        for w in data.get("warnings", [])
        if w.get("type") == "overlapping_active_fees"
    }
    names = {}
    for property_id, record in data["properties"].items():
        name = (record.get("property_name") or "").strip()
        if not name:
            raise ValueError(f"Missing verified Property name for {property_id}")
        key = name.casefold()
        if key in names:
            raise ValueError(f"Duplicate Property name in PDE fee artifact: {name}")
        categories = defaultdict(lambda: defaultdict(list))
        for group in record.get("fees", []):
            current = group.get("current")
            entries = group.get("history", [])
            exemplar = current or (entries[-1] if entries else {})
            category = (exemplar.get("category") or "Other Fees").strip()
            family = (exemplar.get("group") or group.get("fee_type") or "Other").strip()
            unresolved = (property_id, group.get("fee_key")) in overlaps
            state = "current" if current else ("unresolved" if unresolved else "noncurrent")
            history = sorted((item for item in entries if not _negative_amount(item.get("amount"))),
                             key=lambda x: (x.get("effective") or "", x.get("id") or ""),
                             reverse=True)
            categories[category][family].append({
                "label": _security_deposit_label(group.get("fee_type") or exemplar.get("name") or "Fee", group.get("variant") or ""),
                "suppress": bool(current and _negative_amount(current.get("amount"))),
                "variant": group.get("variant") or "",
                "state": state,
                "amount": _currency(current.get("amount")) if current else None,
                "effective": current.get("effective") if current else None,
                "history": [{
                    "amount": _currency(item.get("amount")),
                    "effective": item.get("effective"),
                    "end": item.get("end"),
                    "status": item.get("status"),
                } for item in history],
            })
        names[key] = [
            {"name": category,
             "groups": [{"name": family,
                         "fees": sorted(fees, key=lambda x: (x["label"].casefold(), x["variant"].casefold()))}
                        for family, fees in sorted(families.items(), key=lambda x: x[0].casefold())]}
            for category, families in sorted(categories.items(), key=lambda x: x[0].casefold())
        ]
    return names
