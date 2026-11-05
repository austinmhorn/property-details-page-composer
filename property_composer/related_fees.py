"""Read the PDE v3 related-fee artifact for the Composer Details view.

Never infer a fee from a legacy CSV formula field. The artifact is joined
using the verified property name carried by PDE's Property ID/name lookup.
"""
from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path
from datetime import date
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


def _hold_method(record: dict, variant: str = "") -> str | None:
    """Translate only the two approved Hold Deposit billing methods."""
    value = (record.get("billing_method") or variant or "").strip().casefold()
    if value.replace("-", " ") == "move in":
        return "At Move-In"
    if value.startswith("lease approval"):
        return "At Lease Approval"
    return None


def _active_as_of(record: dict, as_of: date) -> bool:
    """Use PDE's same inclusive active/effective/end semantics."""
    if (record.get("status") or "").casefold() != "active":
        return False
    start = record.get("effective")
    end = record.get("end")
    return (not start or date.fromisoformat(start[:10]) <= as_of) and (
        not end or date.fromisoformat(end[:10]) >= as_of
    )


def _signed_currency(value: str | None) -> str:
    formatted = _currency(value)
    # Currency symbols precede digits, but the minus sign precedes the symbol.
    return "-$" + formatted[2:] if formatted.startswith("$-") else formatted


def _hold_deposit_card(groups: list[dict], as_of: date) -> dict | None:
    """Make one Hold Deposit card without hiding approved refund entries.

    Multiple active entries for one billing method are intentionally unresolved
    rather than silently choosing an amount. All other negative fees remain
    governed by the existing suppression rules.
    """
    rows: dict[str, list[dict]] = {
        "At Move-In": [],
        "At Lease Approval": [],
    }
    history = []
    unresolved = False
    for group in groups:
        current = group.get("current")
        entries = group.get("history") or []
        variant = group.get("variant") or ""
        if group.get("_unresolved"):
            unresolved = True
        # Historical refunds are excluded from the normal current projection
        # by PDE because they are offsets, not charges.
        for entry in entries:
            method = _hold_method(entry, variant)
            if method and entry.get("amount") is not None:
                history.append({
                    "amount": _signed_currency(entry["amount"]),
                    "effective": entry.get("effective"),
                    "end": entry.get("end"),
                    "status": entry.get("status"),
                    "billing_method": method,
                })
            if entry.get("is_refund") is True and _active_as_of(entry, as_of):
                if method is None or entry.get("amount") is None:
                    unresolved = True
                else:
                    rows[method].append(entry)
        if current is not None:
            method = _hold_method(current, variant)
            if method is None or current.get("amount") is None:
                unresolved = True
            else:
                rows[method].append(current)
    if not any(rows.values()) and not unresolved:
        return None
    if any(len(values) > 1 for values in rows.values()):
        unresolved = True
    ordered = []
    if not unresolved:
        for method in ("At Move-In", "At Lease Approval"):
            if rows[method]:
                ordered.append({
                    "method": method,
                    "amount": _signed_currency(rows[method][0]["amount"]),
                })
    return {
        "label": "Hold Deposit",
        "state": "unresolved" if unresolved else "current",
        "suppress": False,
        "variant": "",
        "amount": None,
        "amount_rows": ordered,
        "effective": None,
        "history": sorted(history, key=lambda x: x.get("effective") or "", reverse=True),
        "hold_deposit": True,
    }


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
    as_of = date.fromisoformat(data["as_of"])
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
        hold_groups = []
        hold_category = "Deposit"
        for group in record.get("fees", []):
            current = group.get("current")
            entries = group.get("history", [])
            exemplar = current or (entries[-1] if entries else {})
            category = (exemplar.get("category") or "Other Fees").strip()
            family = (exemplar.get("group") or group.get("fee_type") or "Other").strip()
            unresolved = (property_id, group.get("fee_key")) in overlaps
            # Hold Deposit has one presentation card with two billing-method
            # amounts. PDE's distinct fee keys and refund records remain intact.
            if (group.get("fee_type") or exemplar.get("name") or "").strip().casefold() == "hold deposit":
                hold_category = category
                hold_groups.append({**group, "_unresolved": unresolved})
                continue
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
        if hold_groups:
            hold_card = _hold_deposit_card(hold_groups, as_of)
            if hold_card is not None:
                categories[hold_category]["Hold Deposit"].append(hold_card)
        names[key] = [
            {"name": category,
             "groups": [{"name": family,
                         "fees": sorted(fees, key=lambda x: (x["label"].casefold(), x["variant"].casefold()))}
                        for family, fees in sorted(families.items(), key=lambda x: x[0].casefold())]}
            for category, families in sorted(categories.items(), key=lambda x: x[0].casefold())
        ]
    return names
