import json
import os
import sys
from datetime import datetime, timedelta, timezone

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


def create_page(token):
    now = datetime.now(timezone.utc)

    pub_start = now.isoformat()
    pub_end = (now + timedelta(days=3650)).isoformat()
    review_date = (now + timedelta(days=365)).isoformat()

    # Deliberately weird phrase so it is easy to search for.
    test_sentence = (
        "The sapphire armadillo checks property details every Tuesday."
    )

    payload = {
        "Transition": {
            "State": "Published",
            "Message": "Created by Property Details Page Composer",
            "SendNotifications": False,
            "ResendMentions": False,
        },

        "Page": {
            "AuthorId": int(PERSON_ID),
            "PublishAsId": int(PERSON_ID),
            "PublisherType": 0,

            # Same Sandbox category/section as page 2185.
            "CategoryIds": [3624],
            "TopSectionIds": [3573],

            "TagIds": [],
            "Keywords": [
                "property composer",
                "dynamic html test",
            ],

            "ContentType": "html",

            "Title": "Dynamic HTML Search Test",

            "Summary": (
                "Test page for validating search indexing of "
                "Page Composer HTML content."
            ),

            "Content": {
                "Html": f"""
<div class="property-details-page">
    <h1>Dynamic HTML Search Test</h1>

    <p>{test_sentence}</p>
</div>
""".strip()
            },

            "Features": {
                "DefaultToFullWidth": True,
                "AllowComments": False,
                "IsKeyPage": False,

                "Recommends": {
                    "Show": False,
                    "MaxContentAge": 7,
                },

                "IsMandatoryRead": False,
                "ShowTimeToRead": False,
                "ShowPublishedDate": False,
                "ShowUpdatedDate": False,
            },

            "Audience": {
                "RelatedContent": [],
                "NotificationRecipients": [],
            },

            "PubStartDate": pub_start,
            "PubEndDate": pub_end,
            "ReviewDate": review_date,

            "IsPublic": False,

            # This is the important search setting.
            "IsDiscoverable": True,

            # Explicitly tell Interact this is NOT a Block Editor page.
            "IsBlockEditorPage": False,
        },
    }

    print()
    print("Creating pure HTML Composer page...")
    print(json.dumps(payload, indent=2))
    print()

    response = requests.post(
        f"{API_DOMAIN}/api/page/composer",
        headers={
            "X-Tenant": TENANT_GUID,
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        json=payload,
        timeout=30,
    )

    print(f"HTTP {response.status_code}")

    if not response.ok:
        print("❌ Page creation failed.")
        print(response.text)
        sys.exit(1)

    print("✅ Page created successfully.")

    try:
        result = response.json()
        print(json.dumps(result, indent=2))
    except ValueError:
        print(response.text)


def main():
    token = get_access_token()
    create_page(token)


if __name__ == "__main__":
    main()