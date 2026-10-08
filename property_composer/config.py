import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
JSON_DIR = BASE_DIR / "json"
OUTPUT_DIR = BASE_DIR / "output"
TEMPLATE_DIR = BASE_DIR / "templates"
ENV_FILE = BASE_DIR / "secrets" / ".env"
DATA_FILE = DATA_DIR / "notion_data.csv"
FIELD_METADATA_FILE = DATA_DIR / "property_fields.json"

load_dotenv(ENV_FILE)


def ensure_runtime_dirs() -> None:
    for directory in (DATA_DIR, JSON_DIR, OUTPUT_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def interact_settings() -> dict[str, str]:
    return {
        "api_domain": require_env("INTERACT_API_DOMAIN").rstrip("/"),
        "tenant_guid": require_env("INTERACT_TENANT_GUID"),
        "api_key": require_env("INTERACT_API_KEY"),
        "api_secret": require_env("INTERACT_API_SECRET"),
        "person_id": require_env("INTERACT_PERSON_ID"),
    }
