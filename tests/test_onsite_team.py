"""Isolated onsite team tests. No Notion API or production artifacts required."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from property_composer.onsite_team import (
    load_onsite_team, onsite_team_enabled,
)
from property_composer.property_data import Property
from property_composer.renderer import render_portfolio
from property_composer import property_data_source as source


def artifact(people):
    return {
        "version": 1, "generated_at": "2026-11-09T12:00:00+00:00",
        "properties": {
            "notion-property-id": {"property_name": "Anthem Town East",
                                    "associates": people}
        }, "warnings": [],
    }


class OnsiteTeamTests(unittest.TestCase):
    def read(self, records):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "team.json"
            path.write_text(json.dumps(records), encoding="utf-8")
            return load_onsite_team(path)

    def test_group_same_titles_alphabetically_and_dedupe(self):
        data = self.read(artifact([
            {"page_id": "b", "title": "Leasing Consultant", "name": "Zoe"},
            {"page_id": "a", "title": "leasing consultant", "name": "Alice"},
            {"page_id": "a", "title": "Leasing Consultant", "name": "Alice"},
            {"page_id": "c", "title": "Maintenance Technician", "name": "Bill"},
            {"page_id": "d", "title": "Property Manager", "name": "Manager"},
        ]))
        self.assertEqual(data["anthem town east"], [
            {"label": "Leasing Consultant", "value": "Alice, Zoe", "kind": "text"},
            {"label": "Maintenance Technician", "value": "Bill", "kind": "text"},
        ])

    def test_render_places_onsite_after_existing_property_manager(self):
        team = self.read(artifact([
            {"page_id": "a", "title": "Leasing Consultant", "name": "Sam"},
            {"page_id": "b", "title": "Leasing Consultant", "name": "Alex"},
            {"page_id": "c", "title": "Property Manager", "name": "Not published"},
        ]))
        property_row = Property({
            "Property Name": "Anthem Town East", "Prop No": "123",
            "Property Manager": "Existing PM",
            "Regional Manager": "Existing RM",
        })
        with (
            patch("property_composer.renderer.onsite_team_enabled", return_value=True),
            patch("property_composer.renderer.load_onsite_team", return_value=team),
            patch("property_composer.renderer.load_interact_field_metadata",
                  return_value=({}, set())),
            patch("property_composer.renderer.fee_source", return_value="legacy"),
        ):
            html = render_portfolio([property_row])
        self.assertIn("<dt>Property Manager</dt>", html)
        self.assertIn("Existing PM", html)
        self.assertIn("Alex, Sam", html)
        self.assertEqual(html.count("<dt>Leasing Consultant</dt>"), 1)
        self.assertNotIn("Not published", html)
        self.assertLess(html.index("<dt>Property Manager</dt>"),
                        html.index("<dt>Leasing Consultant</dt>"))
        self.assertLess(html.index("<dt>Leasing Consultant</dt>"),
                        html.index("<dt>Regional Manager</dt>"))

    def test_disabled_by_default_keeps_existing_details(self):
        with patch.dict("os.environ", {"COMPOSER_ONSITE_TEAM_ENABLED": "0"}):
            self.assertFalse(onsite_team_enabled())
        with patch("property_composer.renderer.onsite_team_enabled", return_value=False), \\
             patch("property_composer.renderer.load_onsite_team") as roster_load:
            html = render_portfolio([
                Property({"Property Name": "Anthem Town East", "Prop No": "123"})
            ])
        roster_load.assert_not_called()
        self.assertIn("Anthem Town East", html)

    def test_rejects_duplicate_property_names_and_invalid_payload(self):
        data = artifact([])
        data["properties"]["other-id"] = {
            "property_name": "ANTHEM TOWN EAST", "associates": [],
        }
        with self.assertRaisesRegex(ValueError, "Duplicate Property"):
            self.read(data)
        with self.assertRaisesRegex(ValueError, "Unsupported onsite"):
            self.read({"version": 88, "properties": {}})

    def test_enabled_sync_rejects_missing_sidecar_before_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "notion_data.csv").write_text("Property Name\nExample\n")
            (path / "property_fields.json").write_text('{"version": 1}')
            with patch.object(source, "onsite_team_enabled", return_value=True), \\
                 patch.object(source, "fee_source", return_value="legacy"), \\
                 patch.object(source, "DATA_DIR", path / "composer_data"):
                with self.assertRaisesRegex(FileNotFoundError, "Onsite team"):
                    source.sync_property_data_artifacts(path)
                self.assertFalse((path / "composer_data" / "notion_data.csv").exists())


if __name__ == "__main__":
    unittest.main()
