import os
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from property_composer.interact import InteractClient


def main() -> None:
    page_id = os.getenv("INTERACT_PAGE_ID")
    if not page_id:
        raise SystemExit("❌ Set INTERACT_PAGE_ID in secrets/.env before running this test.")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    html = f"""
<div class="property-composer-test">
  <h1>Property Details Page Composer</h1>
  <p>This content was published dynamically through the Interact Page Composer API using Python.</p>
  <p>API write test generated at {timestamp}.</p>
</div>
""".strip()

    client = InteractClient()
    result = client.update_html_page(
        page_id,
        html,
        message="Python Page Composer update test",
    )

    print(f"✅ Interact page {page_id} updated successfully.")
    print(result)


if __name__ == "__main__":
    main()
