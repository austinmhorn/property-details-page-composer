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
