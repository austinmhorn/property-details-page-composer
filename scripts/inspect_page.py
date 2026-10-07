import json
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from property_composer.config import JSON_DIR, ensure_runtime_dirs
from property_composer.interact import InteractClient


def main() -> None:
    page_id = os.getenv("INTERACT_PAGE_ID", "2185")

    print("🔐 Authenticating with Interact...")
    client = InteractClient()
    client.authenticate()
    print("✅ Authentication successful.")

    print(f"📄 Fetching Composer data for page {page_id}...")
    page = client.get_page(page_id)

    ensure_runtime_dirs()
    output_file = JSON_DIR / f"page_{page_id}.json"
    output_file.write_text(json.dumps(page, indent=2), encoding="utf-8")

    print(f"✅ Page data written to {output_file}")


if __name__ == "__main__":
    main()
