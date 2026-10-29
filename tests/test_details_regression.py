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

    def test_eight_sections_follow_requested_grid_order(self):
        from property_composer.property_data import SECTION_FIELDS
        expected = [
            "Quick Facts", "Property & Building Details",
            "Property Team", "Contacts", "Leasing & Policies",
            "Systems & Programs", "Portals & Resources", "Fees & Deposits",
        ]
        self.assertEqual(list(SECTION_FIELDS), expected)
        values = {"Property Name": "Baseline Community", "Prop No": "123"}
        fields = []
        for index, category in enumerate(expected):
            header = f"Example Section Field {index}"
            values[header] = f"Section value {index}"
            fields.append({
                "csv_header": header, "display_in_interact": True,
                "interact_category": category, "interact_label": header,
                "interact_details_order": 10,
            })
        html = self.render(fields, [Property(values)])
        section_html = html.split('class="property-sections"', 1)[1]
        last = -1
        for category in expected:
            current = section_html.index(category.replace("&", "&amp;"))
            self.assertGreater(current, last)
            last = current

    def test_unmanaged_properties_do_not_create_ninth_section(self):
        html = self.render([], [Property({
            "Property Name": "Baseline Community", "Prop No": "123",
            "Unmanaged Other Column": "Unreviewed value",
        })])
        self.assertNotIn("Additional Details", html)
        self.assertNotIn("Unreviewed value", html)

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

    def test_correction_link_is_shared_across_views(self):
        html = self.render([])
        self.assertEqual(html.count('class="property-details-correction-link"'), 1)
        self.assertIn('Request a Correction', html)
        self.assertIn('https://birchstoneres.notion.site/3f982f879539807296d5ef0dc0363ca1?pvs=105', html)
        self.assertIn('target="_blank" rel="noopener noreferrer"', html)
        self.assertLess(html.index('property-details-selector-wrap'), html.index('property-details-correction-link'))
        self.assertLess(html.index('property-details-correction-link'), html.index('id="property-details-selector"'))
        self.assertLess(html.index('property-details-correction-link'), html.index('data-property-view-switch'))

    def test_renamed_cares_act_header_uses_registry_metadata(self):
        properties = [Property({
            "Property Name": "Baseline Community",
            "Prop No": "123",
            "Cares Act": "30",
        })]
        html = self.render([{
            "csv_header": "Cares Act",
            "display_in_interact": True,
            "interact_category": "Leasing & Policies",
            "interact_label": "Cares Act",
            "interact_details_order": 40,
            "interact_table_order": 890,
        }], properties)
        self.assertIn("Cares Act", html)
        self.assertIn("30", html)
        self.assertNotIn("Cares Act / Days to File", html)

    def test_owning_entity_follows_registry_visibility(self):
        property_row = Property({
            "Property Name": "Baseline Community",
            "Prop No": "123",
            "Owning Entity": "Example Holding Company",
        })
        field = {
            "csv_header": "Owning Entity",
            "interact_category": "Quick Facts",
            "interact_label": "Owning Entity",
            "interact_details_order": 35,
            "interact_table_order": 270,
        }
        visible_html = self.render(
            [{**field, "display_in_interact": True}],
            [property_row],
        )
        self.assertIn("Example Holding Company", visible_html)
        self.assertIn("Quick Facts", visible_html)
        self.assertIn("Owning Entity", visible_html)
        self.assertIn('data-property-column="Owning Entity"', visible_html)

        hidden_html = self.render(
            [{**field, "display_in_interact": False}],
            [property_row],
        )
        self.assertNotIn("Example Holding Company", hidden_html)
        self.assertNotIn('data-property-column="Owning Entity"', hidden_html)

    def test_other_protected_fields_remain_excluded(self):
        prop = Property({
            "Property Name": "Baseline Community",
            "Prop No": "123",
            "EIN": "private-ein-sentinel",
        })
        html = self.render([{
            "csv_header": "EIN",
            "display_in_interact": True,
            "interact_category": "Quick Facts",
            "interact_label": "EIN",
        }], [prop])
        self.assertNotIn("private-ein-sentinel", html)

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
                            "interact_category": "Portals & Resources", "interact_label": "New Label"}])
        self.assertIn("Old Label", old)
        self.assertNotIn("Old Label", new)
        self.assertIn("New Label", new)
        self.assertIn("Portals &amp; Resources", new)

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
            path.write_text('{"version":3,"fields":[]}', encoding="utf-8")
            with self.assertRaises(RuntimeError):
                load_interact_field_metadata(path)

    def test_canonical_registry_v2_is_supported(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fields.json"
            path.write_text(json.dumps({"version": 2, "fields": [{
                "csv_header": "Custom Program",
                "display_in_interact": True,
                "interact_category": "Systems & Programs",
                "interact_label": "Program Label",
                "interact_details_order": 11,
                "interact_table_order": 21
            }]}), encoding="utf-8")
            visible, managed = load_interact_field_metadata(path)
        self.assertIn("Custom Program", visible)
        self.assertIn("Custom Program", managed)
        self.assertEqual(visible["Custom Program"].table_order, 21)

    def test_multiple_properties_stay_in_initial_html(self):
        second = Property({"Property Name": "Other Community", "Prop No": "456"})
        html = self.render([], [self.property, second])
        self.assertIn('data-property-record="123"', html)
        self.assertIn('data-property-record="456"', html)
        self.assertIn('data-property-active="false"', html)


if __name__ == "__main__":
    unittest.main()
