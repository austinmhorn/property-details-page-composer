import json
import tempfile
import unittest
from pathlib import Path

from property_composer.related_fees import load_fee_sections


class RelatedFeesTests(unittest.TestCase):
    def test_grouped_fees_and_history(self):
        page = {"version": 3, "properties": {"property-id": {
            "property_name": "Northern Cross",
            "fees": [
                {"fee_type": "Detached Garage Parking Charges", "variant": "Monthly",
                 "current": {"amount": "95", "category": "Add On",
                             "group": "Garage Parking Charges", "effective": "2026-01-01"},
                 "history": [
                     {"id": "old", "amount": "75", "effective": "2025-01-01",
                      "end": "2025-12-31", "status": "Inactive"},
                     {"id": "new", "amount": "95", "effective": "2026-01-01",
                      "end": None, "status": "Active"}]},
                {"fee_type": "Breezeway Garage Parking Charges", "variant": "Monthly",
                 "current": {"amount": "125", "category": "Add On",
                             "group": "Garage Parking Charges", "effective": "2026-01-01"},
                 "history": []},
            ],
        }}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fees.json"
            path.write_text(json.dumps(page), encoding="utf-8")
            result = load_fee_sections(path)
        groups = result["northern cross"][0]["groups"]
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]["fees"]), 2)
        self.assertEqual({f["amount"] for f in groups[0]["fees"]},
                         {"$95.00", "$125.00"})
        detached = next(f for f in groups[0]["fees"] if f["label"].startswith("Detached"))
        self.assertEqual(len(detached["history"]), 2)

    def test_missing_property_name_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fees.json"
            path.write_text(json.dumps({"version": 3, "properties": {
                "id": {"property_name": "", "fees": []}}}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_fee_sections(path)


if __name__ == "__main__":
    unittest.main()
