import unittest
from unittest.mock import patch, MagicMock

from scripts import automated_publish as workflow


class AutomatedPublishSafetyTests(unittest.TestCase):
    @patch.object(workflow, "InteractClient")
    @patch.object(workflow, "render_portfolio")
    @patch.object(workflow, "load_properties")
    @patch.object(workflow, "refresh_property_data")
    def test_refresh_failure_never_publishes(self, refresh, load, render, client):
        refresh.side_effect = RuntimeError("PDE unavailable")
        with self.assertRaisesRegex(RuntimeError, "PDE unavailable"):
            workflow.generate_current_html()
        load.assert_not_called()
        render.assert_not_called()
        client.assert_not_called()

    @patch.object(workflow, "render_portfolio")
    @patch.object(workflow, "load_properties")
    @patch.object(workflow, "refresh_property_data")
    def test_empty_portfolio_is_rejected(self, refresh, load, render):
        load.return_value = []
        with self.assertRaisesRegex(RuntimeError, "empty"):
            workflow.generate_current_html()
        render.assert_not_called()

    @patch.object(workflow, "render_portfolio")
    @patch.object(workflow, "load_properties")
    @patch.object(workflow, "refresh_property_data")
    def test_render_mismatch_prevents_publish(self, refresh, load, render):
        load.return_value = [object(), object()]
        render.return_value = '<article data-property-record="1"></article>'
        with self.assertRaisesRegex(RuntimeError, "count"):
            workflow.generate_current_html()

    @patch.dict("os.environ", {"INTERACT_PAGE_ID":"2186"})
    @patch.object(workflow, "InteractClient")
    @patch.object(workflow, "write_preview")
    @patch.object(workflow, "write_publish_fragment")
    @patch.object(workflow, "render_portfolio")
    @patch.object(workflow, "load_properties")
    @patch.object(workflow, "refresh_property_data")
    def test_publish_uses_exact_current_render(self, refresh, load, render, fragment, preview, client):
        load.return_value = [object()]
        html = '<main><article data-property-record="123">Current run</article></main>'
        render.return_value = html
        workflow.main()
        refresh.assert_called_once()
        fragment.assert_called_once_with(html)
        preview.assert_called_once_with(html)
        client.return_value.update_html_page.assert_called_once()
        args, kwargs = client.return_value.update_html_page.call_args
        self.assertEqual(args[:2], ("2186", html))
        self.assertNotIn("--existing", str(args))

    @patch.dict("os.environ", {"INTERACT_PAGE_ID":"9999"})
    @patch.object(workflow, "InteractClient")
    @patch.object(workflow, "refresh_property_data")
    def test_unapproved_target_is_rejected(self, refresh, client):
        with self.assertRaisesRegex(RuntimeError, "2186"):
            workflow.main()
        refresh.assert_not_called()
        client.assert_not_called()


if __name__ == "__main__":
    unittest.main()
