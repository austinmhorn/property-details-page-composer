import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from property_composer.property_data import load_properties
from property_composer.property_data_source import refresh_property_data
from property_composer.renderer import (
    render_portfolio,
    write_preview,
    write_publish_fragment,
)


def main() -> None:
    print(
        "===== REFRESHING PROPERTY DATA DEPENDENCY ====="
    )
    refresh_property_data()

    print(
        "===== RENDERING PROPERTY DETAILS PAGE ====="
    )
    properties = load_properties()
    html = render_portfolio(
        properties
    )

    fragment_output = (
        write_publish_fragment(
            html
        )
    )
    preview_output = write_preview(
        html
    )

    print(
        f"✅ Rendered {len(properties)} properties."
    )
    print(
        f"   Preview: {preview_output}"
    )
    print(
        f"   Publish fragment: {fragment_output}"
    )


if __name__ == "__main__":
    main()
