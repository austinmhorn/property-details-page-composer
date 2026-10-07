import json
import os
import sys

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


def require_env(name, value):
    if not value:
        print(f"Missing required environment variable: {name}")
        sys.exit(1)


for name, value in {
    "INTERACT_API_DOMAIN": API_DOMAIN,
    "INTERACT_TENANT_GUID": TENANT_GUID,
    "INTERACT_API_KEY": API_KEY,
    "INTERACT_API_SECRET": API_SECRET,
    "INTERACT_PERSON_ID": PERSON_ID,
}.items():
    require_env(name, value)


def get_access_token():
    url = f"{API_DOMAIN}/token"

    headers = {
        "X-Tenant": TENANT_GUID,
        "Content-Type": "application/x-www-form-urlencoded",
    }

    data = {
        "grant_type": "authorization_code",
        "code": f"{API_KEY}__{API_SECRET}",
        "context": "KeySecret",
    }

    response = requests.post(
        url,
        params={"personid": PERSON_ID},
        headers=headers,
        data=data,
        timeout=30,
    )

    if not response.ok:
        print("Authentication failed")
        print("Status:", response.status_code)
        print(response.text)
        sys.exit(1)

    payload = response.json()

    token = payload.get("access_token")

    if not token:
        print("Token response did not contain access_token:")
        print(json.dumps(payload, indent=2))
        sys.exit(1)

    return token


def get_page(token):
    url = f"{API_DOMAIN}/api/page/{PAGE_ID}/composer/latest"

    headers = {
        "X-Tenant": TENANT_GUID,
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=30,
    )

    if not response.ok:
        print("Failed to retrieve page")
        print("Status:", response.status_code)
        print(response.text)
        sys.exit(1)

    return response.json()


def main():
    print("Authenticating with Interact...")
    token = get_access_token()
    print("Authentication successful.")

    print(f"Fetching Composer data for page {PAGE_ID}...")
    page = get_page(token)

    JSON_DIR = BASE_DIR / "json"
    JSON_DIR.mkdir(exist_ok=True)

    output_file = JSON_DIR / f"page_{PAGE_ID}.json"

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(page, file, indent=2)

    print(f"Success. Page data written to {output_file}")


if __name__ == "__main__":
    main()