"""Phase 1 regression contract: preserve the published Details experience.

Runs without Notion, Interact credentials, or production PDE artifacts:
    python -m unittest discover -s tests -v
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from property_composer.property_data import Property, load_interact_field_metadata
from property_composer.renderer import render_portfolio


class DetailsRegressionTests(unittest.TestCase):
    def setUp(self):
        self.property = Property({
            "Property Name": "Baseline Community",
            "Prop No": "123",
            "City": "Irving",
            "State": "TX",
            "Units": "250",
            "Website": "https://example.org",
            "Custom Program": "Enabled",
            "Private Field": "do-not-publish",
        })

    def metadata(self, fields):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "property_fields.json"
            path.write_text(json.dumps({"version": 1, "fields": fields}), encoding="utf-8")
            return load_interact_field_metadata(path)

    def render(self, fields, properties=None):
        metadata = self.metadata(fields)
        with patch("property_composer.renderer.load_interact_field_metadata", return_value=metadata):
            return render_portfolio(properties or [self.property])

    def test_details_markup_and_selection_contract(self):
        html = self.render([])
        for marker in (
            'data-property-details-app', 'data-property-selector',
            'data-property-record="123"', 'data-property-active="true"',
            'class="property-record__hero"', 'class="property-sections"',
            'class="property-detail-grid"',
        ):
            self.assertIn(marker, html)
        self.assertIn("Baseline Community", html)
        self.assertIn("250", html)

    def test_registry_hidden_field_never_appears(self):
        html = self.render([
            {"csv_header": "Private Field", "display_in_interact": False,
             "interact_category": "Systems & Programs", "interact_label": "Private Label"},
            {"csv_header": "Custom Program", "display_in_interact": True,
             "interact_category": "Systems & Programs", "interact_label": "Program Label"},
        ])
        self.assertNotIn("do-not-publish", html)
        self.assertNotIn("Private Label", html)
        self.assertIn("Program Label", html)
        self.assertIn("Enabled", html)

    def test_label_and_category_follow_approved_metadata(self):
        old = self.render([{"csv_header": "Custom Program", "display_in_interact": True,
                            "interact_category": "Systems & Programs", "interact_label": "Old Label"}])
        new = self.render([{"csv_header": "Custom Program", "display_in_interact": True,
                            "interact_category": "Marketing & Reviews", "interact_label": "New Label"}])
        self.assertIn("Old Label", old)
        self.assertNotIn("Old Label", new)
        self.assertIn("New Label", new)
        self.assertIn("Marketing &amp; Reviews", new)

    def test_unsafe_property_data_is_html_escaped(self):
        prop = Property({"Property Name": '<script>alert("x")</script>',
                         "City": "<img src=x onerror=alert(1)>"})
        html = self.render([], [prop])
        self.assertNotIn("<script>", html)
        self.assertNotIn("<img", html)
        self.assertIn("&lt;script&gt;", html)

    def test_unknown_metadata_version_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text('{"version":2,"fields":[]}', encoding="utf-8")
            with self.assertRaises(RuntimeError):
                load_interact_field_metadata(path)

    def test_multiple_properties_stay_in_initial_html(self):
        second = Property({"Property Name": "Other Community", "Prop No": "456"})
        html = self.render([], [self.property, second])
        self.assertIn('data-property-record="123"', html)
        self.assertIn('data-property-record="456"', html)
        self.assertIn('data-property-active="false"', html)


if __name__ == "__main__":
    unittest.main()
