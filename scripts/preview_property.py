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
    parser = argparse.ArgumentParser(description="Render a single property for layout development.")
    parser.add_argument("property", help="Property name or property number")
    args = parser.parse_args()

    properties = load_properties()
    prop = find_property(properties, args.property)
    html = render_portfolio([prop], selected_key=prop.key, page_title="Property Details Preview")
    output = write_preview(html, f"preview-{prop.key}.html")

    print(f"✅ Previewed {prop.name}")
    print(f"   {output}")
    webbrowser.open(output.resolve().as_uri())


if __name__ == "__main__":
    main()
