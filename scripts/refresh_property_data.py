import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from property_composer.property_data_source import refresh_property_data


def main() -> None:
    csv_path, metadata_path = (
        refresh_property_data()
    )

    print(
        "✅ Property Data Engine artifacts are ready:"
    )
    print(f"   Dataset: {csv_path}")
    print(f"   Metadata: {metadata_path}")


if __name__ == "__main__":
    main()
