import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from property_composer.interact import InteractClient


def main() -> None:
    html = """
<div class="property-details-page">
  <h1>Dynamic HTML Search Test</h1>
  <p>The sapphire armadillo checks property details every Tuesday.</p>
</div>
""".strip()

    client = InteractClient()
    result = client.create_html_page(
        title="Dynamic HTML Search Test",
        summary="Test page for validating search indexing of Page Composer HTML content.",
        html=html,
        category_ids=[3624],
        top_section_ids=[3573],
        keywords=["property composer", "dynamic html test"],
    )

    print("✅ Test page created successfully.")
    print(result)


if __name__ == "__main__":
    main()
