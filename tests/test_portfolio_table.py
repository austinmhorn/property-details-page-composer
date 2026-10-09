"""Phase 2: table generation respects the existing Field Manager contract."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from property_composer.property_data import Property, load_interact_field_metadata
from property_composer.renderer import render_portfolio


class PortfolioTableTests(unittest.TestCase):
    def render(self, fields):
        with tempfile.TemporaryDirectory() as directory:
            f = Path(directory) / "fields.json"
            f.write_text(json.dumps({"version": 1, "fields": fields}), encoding="utf-8")
            metadata = load_interact_field_metadata(f)
        properties = [
            Property({"Property Name": "Alpha", "Prop No": "1", "City": "Irving",
                      "State": "TX", "Metro": "DFW", "Units": "250",
                      "Regional Manager": "Jane Smith", "Website": "https://example.com"}),
            Property({"Property Name": "Beta", "Prop No": "2", "City": "Orlando",
                      "State": "FL", "Metro": "Orlando", "Units": "340"}),
        ]
        with patch("property_composer.renderer.load_interact_field_metadata", return_value=metadata):
            return render_portfolio(properties)

    def test_has_both_views_and_all_rows(self):
        html = self.render([])
        for marker in ('data-property-details-view', 'data-property-table-view',
                       'data-property-view-button="details"', 'data-property-view-button="table"',
                       'data-property-table-row="1"', 'data-property-table-row="2"',
                       'data-property-table-search', 'data-property-table-sort="0"',
                       'data-property-table-state', 'data-property-table-market'):
            self.assertIn(marker, html)
        self.assertIn('data-property-record="1"', html)
        self.assertIn('data-property-record="2"', html)

    def test_unpublished_registry_field_not_in_table(self):
        html = self.render([{"csv_header": "Regional Manager", "display_in_interact": False}])
        self.assertNotIn('Sort by Regional Manager', html)
        self.assertNotIn('Jane Smith', html)

    def test_registry_label_applied_to_table(self):
        html = self.render([{"csv_header": "Regional Manager", "display_in_interact": True,
                             "interact_category": "Property Team",
                             "interact_label": "RM Contact"}])
        self.assertIn('Sort by RM Contact', html)
        self.assertIn("Jane Smith", html)

    def test_table_hides_unapproved_csv_identifiers(self):
        html = self.render([])
        self.assertNotIn('Sort by Prop No', html)
        self.assertNotIn('Sort by PMS ID', html)

    def test_column_chooser_respects_registry_visibility(self):
        html = self.render([
            {"csv_header": "Regional Manager", "display_in_interact": False},
            {"csv_header": "Metro", "display_in_interact": True,
             "interact_category": "Quick Facts", "interact_label": "Portfolio Market"},
        ])
        self.assertIn('data-property-column-chooser', html)
        self.assertIn('data-property-columns-reset', html)
        self.assertNotIn('data-property-column-key="Regional Manager"', html)
        self.assertIn('data-property-column-key="Metro"', html)
        self.assertIn('Portfolio Market', html)
        self.assertIn('data-property-column-key="Property Name"', html)

    def test_curated_columns_available_but_not_default(self):
        html = self.render([])
        self.assertIn('data-property-column-key="Landline"', html)
        self.assertIn('data-property-column-key="Units"', html)
        self.assertIn('data-property-column-checkbox=', html)
        self.assertIn('data-property-column="Landline" hidden', html)

    def test_hidden_market_and_state_not_exposed_in_filter_attributes(self):
        html = self.render([
            {"csv_header": "State", "display_in_interact": False},
            {"csv_header": "Metro", "display_in_interact": False},
        ])
        self.assertNotIn('data-property-table-state="TX"', html)
        self.assertNotIn('data-property-table-market="DFW"', html)
        self.assertNotIn('data-property-column-key="State"', html)
        self.assertNotIn('data-property-column-key="Metro"', html)


if __name__ == "__main__":
    unittest.main()
