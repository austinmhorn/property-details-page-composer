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


    def test_details_fees_are_alphabetical_across_groups(self):
        from property_composer.property_data import Property
        from unittest.mock import patch

        # Category and group order intentionally contradict fee label order.
        fees = [{
            "name": "Add On",
            "groups": [
                {"name": "Garage", "fees": [
                    {"label": "Zebra Garage", "state": "current", "suppress": False,
                     "amount": "$95.00", "variant": "", "history": []},
                    {"label": "Dormant Garage", "state": "noncurrent", "suppress": False,
                     "amount": None, "variant": "", "history": []},
                ]},
                {"name": "Parking", "fees": [
                    {"label": "Alpha Parking", "state": "current", "suppress": False,
                     "amount": "$50.00", "variant": "", "history": [{
                         "amount": "$45.00", "effective": "2025-01-01",
                         "end": None, "status": "Inactive"
                     }]},
                ]},
            ],
        }, {
            "name": "Deposits", "groups": [
                {"name": "Deposits", "fees": [
                    {"label": "Middle Deposit", "state": "unresolved",
                     "suppress": False, "amount": None, "variant": "",
                     "history": []},
                    {"label": "Excluded Deposit", "state": "current",
                     "suppress": True, "amount": "$10.00", "variant": "",
                     "history": []},
                ]}
            ],
        }]
        prop = Property({"Property Name": "Northern Cross", "Prop No": "123"})
        with patch("property_composer.renderer.fee_source", return_value="v3"), \
             patch("property_composer.renderer.verify_manifest"), \
             patch("property_composer.renderer.load_fee_sections",
                   return_value={"northern cross": fees}), \
             patch("property_composer.renderer.load_interact_field_metadata",
                   return_value=({}, set())):
            html = render_portfolio([prop])
        marker = 'class="property-fee-item__name">'
        labels = [
            "Alpha Parking", "Middle Deposit", "Zebra Garage"
        ]
        positions = [html.index(marker + label) for label in labels]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn(marker + "Dormant Garage", html)
        self.assertNotIn(marker + "Excluded Deposit", html)
        self.assertIn("View fee details (1)", html)
        self.assertIn("Requires review", html)
        self.assertIn("$95.00", html)

    def test_negative_current_fee_suppressed_and_security_deposits_distinguished(self):
        dataset = {"version": 3, "properties": {"p": {"property_name": "Avery", "fees": [
            {"fee_type": "Hold Deposit", "variant": "Move-In", "current": None,
             "history": [{"id": "n", "amount": "-250", "status": "Active",
                          "is_refund": True, "billing_method": "Move-In",
                          "category": "Deposit", "group": "Hold"}]},
            {"fee_type": "Hold Deposit", "variant": "Lease Approval [Primary (Responsible)]",
             "current": {"id": "h", "amount": "250", "status": "Active",
                         "is_refund": False,
                         "billing_method": "Lease Approval [Primary (Responsible)]",
                         "category": "Deposit", "group": "Hold"},
             "history": [{"id": "h", "amount": "250", "status": "Active",
                          "billing_method": "Lease Approval [Primary (Responsible)]"}]},
            {"fee_type": "Parking Refund", "variant": "", "current": {
                "amount": "-25", "category": "Deposit", "group": "Parking"
            }, "history": [{"id": "p", "amount": "-25", "status": "Active"}]},
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
        self.assertFalse(by_label["Hold Deposit"]["suppress"])
        self.assertEqual(by_label["Hold Deposit"]["amount_rows"], [
            {"method": "At Lease Approval", "amount": "$250.00"},
            {"method": "At Move-In", "amount": "-$250.00"},
        ])
        self.assertEqual(len(by_label["Hold Deposit"]["history"]), 2)
        self.assertTrue(by_label["Parking Refund"]["suppress"])
        self.assertEqual(by_label["Parking Refund"]["history"], [])
        self.assertFalse(by_label["Security Deposit (Standard)"]["suppress"])
        self.assertFalse(by_label["Security Deposit (Conditional)"]["suppress"])
        self.assertEqual(len(by_label["Security Deposit (Conditional)"]["history"]), 1)

    def test_hold_deposit_is_one_card_with_both_billing_methods_in_html(self):
        from property_composer.property_data import Property
        data = {
            "version": 3,
            "as_of": "2026-11-05",
            "properties": {"property-id": {
                "property_name": "Avery",
                "fees": [
                    {"fee_key": "move", "fee_type": "Hold Deposit", "variant": "Move-In",
                     "current": None, "history": [
                         {"id": "refund", "is_refund": True, "amount": "-200",
                          "status": "Active", "effective": "2026-07-09",
                          "billing_method": "Move-In", "category": "Deposit",
                          "group": "Hold Deposit"}]},
                    {"fee_key": "lease", "fee_type": "Hold Deposit",
                     "variant": "Lease Approval [Primary (Responsible)]",
                     "current": {"id": "charge", "is_refund": False, "amount": "200",
                                 "status": "Active", "effective": "2026-07-09",
                                 "billing_method": "Lease Approval [Primary (Responsible)]",
                                 "category": "Deposit", "group": "Hold Deposit"},
                     "history": [
                         {"id": "charge", "is_refund": False, "amount": "200",
                          "status": "Active", "effective": "2026-07-09",
                          "billing_method": "Lease Approval [Primary (Responsible)]"}]},
                    {"fee_key": "other", "fee_type": "Amenity Charge", "variant": "",
                     "current": {"amount": "20", "category": "Deposit", "group": "Other"},
                     "history": []}
                ]
            }}
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fees.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            sections = load_fee_sections(path)
        cards = [fee for section in sections["avery"]
                 for group in section["groups"] for fee in group["fees"]]
        self.assertEqual([fee["label"] for fee in cards].count("Hold Deposit"), 1)
        with patch("property_composer.renderer.fee_source", return_value="v3"), \
             patch("property_composer.renderer.verify_manifest"), \
             patch("property_composer.renderer.load_fee_sections",
                   return_value=sections), \
             patch("property_composer.renderer.load_interact_field_metadata",
                   return_value=({}, set())):
            html = render_portfolio([
                Property({"Property Name": "Avery", "Prop No": "123"})
            ])
        self.assertEqual(
            html.count('class="property-fee-item__name">Hold Deposit'), 1)
        self.assertIn("At Move-In", html)
        self.assertIn("At Lease Approval", html)
        self.assertLess(html.index("At Lease Approval"), html.index("At Move-In"))
        self.assertIn("-$200.00", html)
        self.assertIn("$200.00", html)
        self.assertIn("View fee details (2)", html)
        self.assertLess(html.index("Amenity Charge"), html.index(
            'class="property-fee-item__name">Hold Deposit'))

    def test_expired_refund_not_shown_and_ambiguous_hold_is_unresolved(self):
        from property_composer.related_fees import _hold_deposit_card
        from datetime import date
        expired = {"fee_type": "Hold Deposit", "variant": "Move-In",
                   "current": None, "history": [
                       {"is_refund": True, "status": "Active", "amount": "-200",
                        "end": "2026-10-31", "billing_method": "Move-In"}]}
        card = _hold_deposit_card([expired], date(2026, 11, 5))
        self.assertIsNone(card)
        charge = {"fee_type": "Hold Deposit", "variant": "Lease Approval",
                  "current": {"amount": "200", "billing_method": "Lease Approval"},
                  "history": []}
        another_charge = {**charge, "current": {
            "amount": "250", "billing_method": "Lease Approval"}}
        card = _hold_deposit_card([charge, another_charge], date(2026, 11, 5))
        self.assertEqual(card["state"], "unresolved")
        self.assertEqual(card["amount_rows"], [])

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
