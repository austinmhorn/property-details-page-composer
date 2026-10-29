"""Read the PDE v3 related-fee artifact for the Composer Details view.

Never infer a fee from a legacy CSV formula field. The artifact is joined
using the verified property name carried by PDE's Property ID/name lookup.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from .config import DATA_DIR
from .property_data import _currency


FEE_FILE = DATA_DIR / "property_fees.json"


def load_fee_sections(path: Path = FEE_FILE) -> dict[str, list[dict]]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != 3 or not isinstance(data.get("properties"), dict):
        raise ValueError("Unsupported PDE related fee artifact")
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
            if not current:
                continue  # Historical-only fees are not presented as current.
            category = (current.get("category") or "Other Fees").strip()
            family = (current.get("group") or group.get("fee_type") or "Other").strip()
            history = sorted(group.get("history", []),
                             key=lambda x: (x.get("effective") or "", x.get("id") or ""),
                             reverse=True)
            categories[category][family].append({
                "label": group.get("fee_type") or current.get("name") or "Fee",
                "variant": group.get("variant") or "",
                "amount": _currency(current.get("amount")),
                "effective": current.get("effective"),
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
