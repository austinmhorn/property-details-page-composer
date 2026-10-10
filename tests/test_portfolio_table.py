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
                       'data-property-table-search', 'data-property-table-menu="0"'):
            self.assertIn(marker, html)
        self.assertNotIn('data-property-filter-options="state"', html)
        self.assertNotIn('data-property-filter-options="manager"', html)
        self.assertIn('data-property-record="1"', html)
        self.assertIn('data-property-record="2"', html)

    def test_unpublished_registry_field_not_in_table(self):
        html = self.render([{"csv_header": "Regional Manager", "display_in_interact": False}])
        self.assertNotIn('Sort or filter Regional Manager', html)
        self.assertNotIn('Jane Smith', html)

    def test_registry_label_applied_to_table(self):
        html = self.render([{"csv_header": "Regional Manager", "display_in_interact": True,
                             "interact_category": "Property Team",
                             "interact_label": "RM Contact"}])
        self.assertIn('Sort or filter RM Contact', html)
        self.assertIn("Jane Smith", html)

    def test_table_hides_unapproved_csv_identifiers(self):
        html = self.render([])
        self.assertNotIn('Sort or filter Prop No', html)
        self.assertNotIn('Sort or filter PMS ID', html)

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

    def test_column_actions_appear_before_checkboxes(self):
        html = self.render([])
        menu = html.split('class="property-column-chooser__menu"', 1)[1].split("</details>", 1)[0]
        self.assertLess(menu.index("data-property-columns-all"), menu.index("data-property-column-checkbox"))
        self.assertLess(menu.index("data-property-columns-reset"), menu.index("data-property-column-checkbox"))

    def test_curated_columns_available_but_not_default(self):
        html = self.render([])
        self.assertIn('data-property-column-key="Landline"', html)
        self.assertIn('data-property-column-key="Units"', html)
        self.assertIn('data-property-column-checkbox=', html)
        self.assertIn('data-property-column="Landline" hidden', html)

    def test_hidden_manager_and_state_not_exposed_in_filter_attributes(self):
        html = self.render([
            {"csv_header": "State", "display_in_interact": False},
            {"csv_header": "Regional Manager", "display_in_interact": False},
        ])
        self.assertNotIn('data-property-column-key="State"', html)
        self.assertNotIn('data-property-column-key="Regional Manager"', html)

    def test_filter_and_export_controls(self):
        html = self.render([])
        for marker in ('data-property-table-menu="0"',
                       'data-property-columns-all', 'data-property-columns-reset',
                       'data-property-table-export'):
            self.assertIn(marker, html)


    def test_table_website_normalizes_bare_domain(self):
        from property_composer.property_data import Property
        site = Property({"Property Name": "Example", "Website": "example.com"})
        self.assertEqual(site.website_url, "https://example.com")
        self.assertEqual(site.quick_links()[0]["url"], site.website_url)
        with patch("property_composer.renderer.load_interact_field_metadata", return_value=({}, set())):
            html = render_portfolio([site])
        self.assertIn('href="https://example.com"', html)
        self.assertIn('>https://example.com</a>', html)
        self.assertNotIn('Open website', html)

    def test_table_website_preserves_protocol_and_blank(self):
        from property_composer.property_data import Property
        self.assertEqual(Property({"Website": "https://example.org"}).website_url, "https://example.org")
        self.assertEqual(Property({"Website": ""}).website_url, "")


    def test_independent_table_order_and_approved_columns_visible(self):
        fields = [
            {"csv_header": "Metro", "display_in_interact": True,
             "interact_category": "Quick Facts", "interact_label": "Market",
             "interact_details_order": 1, "interact_table_order": 70},
            {"csv_header": "Regional Manager", "display_in_interact": True,
             "interact_category": "Property Team", "interact_label": "RM",
             "interact_details_order": 90, "interact_table_order": 5},
        ]
        html = self.render(fields)
        self.assertLess(
            html.index('data-property-column="Regional Manager"'),
            html.index('data-property-column="Metro"')
        )
        self.assertIn('data-property-column-key="Metro" checked', html)
        self.assertIn('data-property-column-key="Regional Manager" checked', html)

    def test_currency_fee_and_blank_values(self):
        from property_composer.renderer import render_portfolio
        with tempfile.TemporaryDirectory() as directory:
            metadata_path = Path(directory) / "fields.json"
            metadata_path.write_text(json.dumps({"version": 1, "fields": [
                {"csv_header": "Application Fee", "display_in_interact": True,
                 "interact_category": "Fees & Deposits",
                 "interact_label": "Application Fee", "extractor_type": "formula_number",
                 "interact_details_order": 8, "interact_table_order": 5}
            ]}), encoding="utf-8")
            metadata = load_interact_field_metadata(metadata_path)
        properties = [
            Property({"Property Name": "Alpha", "Application Fee": "125.50"}),
            Property({"Property Name": "Beta", "Application Fee": ""}),
            Property({"Property Name": "Gamma", "Application Fee": "0.00"}),
        ]
        with patch("property_composer.renderer.load_interact_field_metadata", return_value=metadata):
            html = render_portfolio(properties)
        self.assertIn("$125.50", html)
        self.assertIn("$0.00", html)
        self.assertIn("Fees &amp; Deposits", html)


if __name__ == "__main__":
    unittest.main()
