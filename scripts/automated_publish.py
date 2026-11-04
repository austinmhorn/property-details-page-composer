"""Dedicated unattended publisher. The render and publish share one in-memory artifact.

Unlike --existing, this workflow can never publish a previously saved fragment.
"""
import os
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from property_composer.property_data_source import refresh_property_data
from property_composer.property_data import load_properties
from property_composer.renderer import (
    render_portfolio, write_publish_fragment, write_preview,
)
from property_composer.interact import InteractClient


def generate_current_html():
    # Must complete successfully before touching the live Interact page.
    refresh_property_data()
    properties = load_properties()
    if not properties:
        raise RuntimeError("Refusing to publish an empty property portfolio.")
    html = render_portfolio(properties)
    if not html or 'data-property-record=' not in html:
        raise RuntimeError("Rendered portfolio lacks property records.")
    # Verify that each property in the current dataset is represented before publishing.
    if html.count('data-property-record=') != len(properties):
        raise RuntimeError("Rendered property count does not match source records.")
    return html, len(properties)


def main():
    page_id = str(os.environ.get("INTERACT_PAGE_ID") or "2186")
    # Initial automation is purpose-built for 2186, not arbitrary Interact pages.
    if page_id != "2186":
        raise RuntimeError("Automated Property Details publishing only supports page 2186.")

    html, count = generate_current_html()
    # Write review artifacts only after a verified render.
    write_publish_fragment(html)
    write_preview(html)
    # Publish exactly the validated in-memory HTML from this run, never --existing.
    InteractClient().update_html_page(
        page_id, html,
        message=f"Automated Property Details refresh: {count} properties",
    )
    print(f"Published same-run render with {count} properties to Interact page {page_id}.")


if __name__ == "__main__":
    main()
