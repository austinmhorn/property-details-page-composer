import json
import os
import sys
from datetime import datetime

import requests
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / "secrets" / ".env"

load_dotenv(ENV_FILE)

API_DOMAIN = os.getenv("INTERACT_API_DOMAIN", "").rstrip("/")
TENANT_GUID = os.getenv("INTERACT_TENANT_GUID")
API_KEY = os.getenv("INTERACT_API_KEY")
API_SECRET = os.getenv("INTERACT_API_SECRET")
PERSON_ID = os.getenv("INTERACT_PERSON_ID")
PAGE_ID = os.getenv("INTERACT_PAGE_ID", "2185")


def require(name, value):
    if not value:
        print(f"❌ Missing environment variable: {name}")
        sys.exit(1)


for name, value in {
    "INTERACT_API_DOMAIN": API_DOMAIN,
    "INTERACT_TENANT_GUID": TENANT_GUID,
    "INTERACT_API_KEY": API_KEY,
    "INTERACT_API_SECRET": API_SECRET,
    "INTERACT_PERSON_ID": PERSON_ID,
}.items():
    require(name, value)


def get_access_token():
    print("🔐 Authenticating with Interact...")

    response = requests.post(
        f"{API_DOMAIN}/token",
        params={"personid": PERSON_ID},
        headers={
            "X-Tenant": TENANT_GUID,
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "authorization_code",
            "code": f"{API_KEY}__{API_SECRET}",
            "context": "KeySecret",
        },
        timeout=30,
    )

    print(f"   HTTP {response.status_code}")

    if not response.ok:
        print("❌ Authentication failed.")
        print(response.text)
        sys.exit(1)

    token = response.json().get("access_token")

    if not token:
        print("❌ No access_token returned.")
        sys.exit(1)

    print("✅ Authentication successful.")
    return token


def get_current_page(token):
    print(f"📄 Reading current page {PAGE_ID}...")

    response = requests.get(
        f"{API_DOMAIN}/api/page/{PAGE_ID}/composer/latest",
        headers={
            "X-Tenant": TENANT_GUID,
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
        timeout=30,
    )

    print(f"   HTTP {response.status_code}")

    if not response.ok:
        print("❌ Failed to retrieve current page.")
        print(response.text)
        sys.exit(1)

    print("✅ Current page retrieved.")
    return response.json()


def build_test_html():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return f"""
<style>
    .property-composer-test {{
        max-width: 900px;
        margin: 40px auto;
        padding: 32px;
        border-radius: 16px;
        background: #ffffff;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.08);
        font-family: Arial, sans-serif;
    }}

    .property-composer-test h2 {{
        margin-top: 0;
        font-size: 28px;
    }}

    .property-composer-test .status {{
        display: inline-block;
        margin-top: 12px;
        padding: 8px 12px;
        border-radius: 999px;
        background: #e8f5e9;
        font-weight: 600;
    }}

    .property-composer-test .timestamp {{
        margin-top: 20px;
        opacity: 0.65;
        font-size: 14px;
    }}
</style>

<div class="property-composer-test">
    <h2>Property Details Page Composer</h2>

    <p>
        This content was published dynamically through the
        Interact Page Composer API using Python.
    </p>

    <div class="status">
        ✓ API Write Successful
    </div>

    <div class="timestamp">
        Generated: {timestamp}
    </div>
</div>
""".strip()


def update_page(token, current_page):
    html = build_test_html()

    payload = {
        "Transition": {
            "State": "Published",
            "Message": "Python Page Composer test",
            "SendNotifications": False,
            "ResendMentions": False,
        },

        "Page": {
            "AuthorId": current_page["Author"]["Id"],
            "PublishAsId": current_page["PublishedAs"]["Id"],
            "PublisherType": current_page["PublishedAs"].get("PublisherType", 0),

            "CategoryIds": [
                category["Id"]
                for category in current_page.get("Categories", [])
            ],

            "TagIds": [
                tag.get("TagId", tag.get("Id"))
                for tag in current_page.get("Tags", [])
            ],

            "Keywords": [
                keyword.get("Value", "")
                for keyword in current_page.get("Keywords", [])
            ],

            "TopSectionIds": current_page["TopSectionIds"],
            "AssetId": current_page["AssetId"],

            "ContentType": current_page["ContentType"],
            "Title": current_page["Title"],
            "Summary": current_page["Summary"],

            "Content": {
                "Html": html
            },

            # Important for Block Editor pages
            "JsonData": current_page["JsonData"],
            "IsBlockEditorPage": current_page["IsBlockEditorPage"],
            "Blocks": current_page["Blocks"],
            "BlockEditorContentType": current_page.get("BlockEditorContentType"),

            "Features": current_page["Features"],
            "Audience": current_page.get("Audience"),

            "PubStartDate": current_page["PubStartDate"],
            "PubEndDate": current_page["PubEndDate"],
            "ReviewDate": current_page["ReviewDate"],

            "ConfidentialityId": current_page.get("ConfidentialityId"),
            "ClassificationId": current_page.get("ClassificationId"),
            "BestBets": current_page.get("BestBets", []),

            "IsPublic": current_page.get("IsPublic", False),
            "IsDiscoverable": current_page.get("IsDiscoverable", True),
            "HasPublicationDateBeenSet":
                current_page.get("HasPublicationDateBeenSet", False),
        },
    }

    print()
    print("Payload:")
    print(json.dumps(payload, indent=2))
    print()

    url = f"{API_DOMAIN}/api/page/{PAGE_ID}/composer"

    print(f"🚀 Updating page {PAGE_ID}...")

    response = requests.put(
        url,
        headers={
            "X-Tenant": TENANT_GUID,
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        json=payload,
        timeout=30,
    )

    print(f"   HTTP {response.status_code}")

    if not response.ok:
        print("❌ Page update failed.")
        print(response.text)
        sys.exit(1)

    print("✅ Page updated successfully.")

    try:
        print(json.dumps(response.json(), indent=2))
    except ValueError:
        print(response.text)


def main():
    token = get_access_token()

    current_page = get_current_page(token)

    print()
    print("Current page:")
    print(f"   Title:       {current_page['Title']}")
    print(f"   Version:     {current_page['VersionNumber']}")
    print(f"   Author:      {current_page['Author']['Name']}")
    print(f"   Author ID:   {current_page['Author']['Id']}")
    print(f"   Asset ID:    {current_page['AssetId']}")
    print(f"   Sections:    {current_page['TopSectionIds']}")

    update_page(token, current_page)


if __name__ == "__main__":
    main()