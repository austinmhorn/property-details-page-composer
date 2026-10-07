import argparse
import sys
import webbrowser
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from property_composer.property_data import find_property, load_properties
from property_composer.renderer import render_portfolio, write_preview


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render all property records into one Interact-ready HTML page."
    )
    parser.add_argument("--selected", help="Property name or property number to show by default.")
    parser.add_argument("--open", action="store_true", help="Open the rendered portfolio in the default browser.")
    args = parser.parse_args()

    properties = load_properties()
    selected_key = find_property(properties, args.selected).key if args.selected else None

    html = render_portfolio(properties, selected_key=selected_key)
    output = write_preview(html)
    print(f"✅ Rendered {len(properties)} properties to {output}")
    if args.open:
        webbrowser.open(output.resolve().as_uri())


if __name__ == "__main__":
    main()
