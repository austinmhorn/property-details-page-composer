import argparse
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
import os

from property_composer.interact import InteractClient
from property_composer.property_data import find_property, load_properties
from property_composer.renderer import render_portfolio, write_preview


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
    args = parser.parse_args()

    if not args.page_id:
        raise SystemExit("❌ Provide --page-id or set INTERACT_PAGE_ID in secrets/.env")

    properties = load_properties()
    selected_key = find_property(properties, args.selected).key if args.selected else None

    html = render_portfolio(properties, selected_key=selected_key)
    output = write_preview(html)

    client = InteractClient()
    result = client.update_html_page(
        args.page_id,
        html,
        message=f"Published {len(properties)} properties from Property Details Page Composer",
    )

    print(f"✅ Published {len(properties)} properties to Interact page {args.page_id}")
    print(f"   Local render: {output}")
    print(f"   Interact response: {result}")


if __name__ == "__main__":
    main()
