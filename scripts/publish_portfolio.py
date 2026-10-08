import argparse
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
import os

from property_composer.interact import InteractClient
from property_composer.property_data import find_property, load_properties
from property_composer.config import OUTPUT_DIR
from property_composer.renderer import (
    render_portfolio,
    write_preview,
    write_publish_fragment,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render and publish the full property portfolio to one Interact page."
    )
    parser.add_argument(
        "--page-id",
        default=os.getenv("INTERACT_PAGE_ID"),
        help="Interact page ID (defaults to INTERACT_PAGE_ID from secrets/.env)",
    )
    parser.add_argument("--selected", help="Property name or property number to show by default.")
    parser.add_argument(
        "--existing",
        action="store_true",
        help="Publish the most recent saved render without rendering again.",
    )
    args = parser.parse_args()

    if not args.page_id:
        raise SystemExit("❌ Provide --page-id or set INTERACT_PAGE_ID in secrets/.env")

    if args.existing:
        fragment_output = (
            OUTPUT_DIR
            / "portfolio_details.fragment.html"
        )

        if not fragment_output.is_file():
            raise SystemExit(
                "❌ No saved publishable render exists. Run Render first."
            )

        html = fragment_output.read_text(
            encoding="utf-8"
        )
        output = (
            OUTPUT_DIR
            / "portfolio_details.html"
        )
        publish_message = (
            "Published existing render from "
            "Property Details Page Composer"
        )
        published_label = "existing render"

    else:
        properties = load_properties()
        selected_key = (
            find_property(
                properties,
                args.selected,
            ).key
            if args.selected
            else None
        )

        html = render_portfolio(
            properties,
            selected_key=selected_key,
        )
        fragment_output = (
            write_publish_fragment(
                html
            )
        )
        output = write_preview(
            html
        )
        publish_message = (
            f"Published {len(properties)} properties "
            "from Property Details Page Composer"
        )
        published_label = (
            f"{len(properties)} properties"
        )

    client = InteractClient()
    result = client.update_html_page(
        args.page_id,
        html,
        message=publish_message,
    )

    print(
        f"✅ Published {published_label} "
        f"to Interact page {args.page_id}"
    )
    print(f"   Local render: {output}")
    print(f"   Publish fragment: {fragment_output}")
    print(f"   Interact response: {result}")


if __name__ == "__main__":
    main()
