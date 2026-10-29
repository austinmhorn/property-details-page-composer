import json
import hashlib
import uuid
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from property_composer.renderer import render_portfolio
from property_composer.related_fees import fee_source
from property_composer.artifact_manifest import verify_manifest, REQUIRED, MANIFEST
from property_composer import property_data_source as source

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


    def test_negative_current_fee_suppressed_and_security_deposits_distinguished(self):
        dataset = {"version": 3, "properties": {"p": {"property_name": "Avery", "fees": [
            {"fee_type": "Hold Deposit", "variant": "Setup", "current": {
                "amount": "-250", "category": "Deposit", "group": "Hold"
            }, "history": [{"id": "n", "amount": "-250", "status": "Active"}]},
            {"fee_type": "Security Deposit", "variant": "Standard Deposit",
             "current": {"amount": "500", "category": "Deposit", "group": "Security"},
             "history": [{"id": "s", "amount": "500", "status": "Active"}]},
            {"fee_type": "Security Deposit", "variant": "Conditional Approval",
             "current": {"amount": "1000", "category": "Deposit", "group": "Security"},
             "history": [{"id": "c", "amount": "1000", "status": "Active"},
                         {"id": "n", "amount": "-100", "status": "Inactive"}]}
        ]}}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fees.json"
            path.write_text(json.dumps(dataset))
            categories = load_fee_sections(path)["avery"]
        fees = [fee for cat in categories for group in cat["groups"] for fee in group["fees"]]
        by_label = {fee["label"]: fee for fee in fees}
        self.assertTrue(by_label["Hold Deposit"]["suppress"])
        self.assertEqual(by_label["Hold Deposit"]["history"], [])
        self.assertFalse(by_label["Security Deposit (Standard)"]["suppress"])
        self.assertFalse(by_label["Security Deposit (Conditional)"]["suppress"])
        self.assertEqual(len(by_label["Security Deposit (Conditional)"]["history"]), 1)

    def test_legacy_default_and_invalid_mode(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(fee_source(), "legacy")
        with patch.dict("os.environ", {"COMPOSER_FEE_SOURCE": "v3"}):
            self.assertEqual(fee_source(), "v3")
        with patch.dict("os.environ", {"COMPOSER_FEE_SOURCE": "unknown"}):
            with self.assertRaises(ValueError):
                fee_source()

    def test_v3_missing_artifact_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                load_fee_sections(Path(directory) / "absent.json")

    def test_v3_requires_explicit_engine(self):
        with patch.dict("os.environ", {"COMPOSER_FEE_SOURCE": "v3",
                                       "PROPERTY_DATA_ENGINE_DIR": ""}):
            with self.assertRaises(RuntimeError):
                source.resolve_property_data_engine_dir()

    def test_manifest_valid_and_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entries = {}
            for name in REQUIRED:
                payload = ("fixture:" + name).encode()
                (root / name).write_bytes(payload)
                entries[name] = {
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "size": len(payload),
                }
            manifest = {
                "schema_version": 1, "run_id": str(uuid.uuid4()),
                "created_at": "2026-10-29T14:00:00+00:00",
                "artifacts": entries,
            }
            (root / MANIFEST).write_text(json.dumps(manifest))
            self.assertEqual(verify_manifest(root)["run_id"], manifest["run_id"])
            (root / "property_fees.json").write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                verify_manifest(root)

    def test_unresolved_and_historical_fees_remain_visible(self):
        dataset = {
            "version": 3,
            "warnings": [{"type": "overlapping_active_fees",
                          "property_id": "p1", "fee_key": "overlap"}],
            "properties": {
                "p1": {"property_name": "Avery", "fees": [
                    {"fee_key": "overlap", "fee_type": "Reserved Parking",
                     "variant": "Monthly", "current": None,
                     "history": [{"id": "one", "name": "Reserved Parking",
                                  "amount": "50", "category": "Add On",
                                  "group": "Parking", "effective": "2025-01-01"},
                                 {"id": "two", "name": "Reserved Parking",
                                  "amount": "75", "category": "Add On",
                                  "group": "Parking", "effective": "2026-01-01"}]},
                    {"fee_key": "old", "fee_type": "Old Fee",
                     "variant": "", "current": None,
                     "history": [{"id": "old", "name": "Old Fee",
                                  "amount": "10", "category": "Add On",
                                  "group": "Other", "effective": "2024-01-01"}]}
                ]}
            }
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fees.json"
            path.write_text(json.dumps(dataset))
            categories = load_fee_sections(path)["avery"]
        fees = [fee for category in categories for group in category["groups"]
                for fee in group["fees"]]
        by_name = {fee["label"]: fee for fee in fees}
        self.assertEqual(by_name["Reserved Parking"]["state"], "unresolved")
        self.assertIsNone(by_name["Reserved Parking"]["amount"])
        self.assertEqual(by_name["Old Fee"]["state"], "noncurrent")
        self.assertEqual(len(by_name["Old Fee"]["history"]), 1)

    def test_v3_refresh_never_runs_pde(self):
        fake_engine = Path("/example/pde-v3")
        with patch.dict("os.environ", {"COMPOSER_FEE_SOURCE": "v3"}), \
             patch.object(source, "resolve_property_data_engine_dir", return_value=fake_engine), \
             patch.object(source, "sync_property_data_artifacts", return_value=("csv", "metadata")) as sync, \
             patch.object(source, "run_property_data_engine", side_effect=AssertionError("PDE must not execute")):
            self.assertEqual(source.refresh_property_data(), ("csv", "metadata"))
            sync.assert_called_once_with(fake_engine)

    def test_legacy_refresh_still_runs_pde(self):
        fake_engine = Path("/example/pde-v2")
        with patch.dict("os.environ", {"COMPOSER_FEE_SOURCE": "legacy"}), \
             patch.object(source, "run_property_data_engine", return_value=fake_engine) as run, \
             patch.object(source, "sync_property_data_artifacts", return_value=("csv", "metadata")) as sync:
            self.assertEqual(source.refresh_property_data(), ("csv", "metadata"))
            run.assert_called_once_with()
            sync.assert_called_once_with(fake_engine)

    def test_manifest_missing_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                verify_manifest(Path(directory))

    def test_missing_property_name_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fees.json"
            path.write_text(json.dumps({"version": 3, "properties": {
                "id": {"property_name": "", "fees": []}}}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_fee_sections(path)


if __name__ == "__main__":
    unittest.main()
