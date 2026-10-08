import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent

if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from property_composer.property_data_source import refresh_property_data


def run_command(command: list[str], description: str) -> bool:
    """Run one workflow step and return True only when it succeeds."""
    print(f"===== {description.upper()} =====")

    try:
        subprocess.run(
            command,
            cwd=PROJECT_DIR,
            check=True,
        )
    except FileNotFoundError as error:
        print(
            f"Error: command not found: {error.filename}"
        )
        return False
    except subprocess.CalledProcessError as error:
        print(
            f"Error: {description} failed "
            f"with exit code {error.returncode}."
        )
        return False

    print(
        f"{description} completed successfully."
    )
    return True


def refresh_property_dataset() -> bool:
    print(
        "===== REFRESHING PROPERTY DATA DEPENDENCY ====="
    )

    try:
        refresh_property_data()
    except (
        FileNotFoundError,
        RuntimeError,
        OSError,
        subprocess.CalledProcessError,
    ) as error:
        print(
            "Error: Property Data Engine dependency "
            f"failed: {error}"
        )
        return False

    print(
        "Property Data Engine dependency completed successfully."
    )
    return True


def main() -> int:
    if not refresh_property_dataset():
        return 1

    if not run_command(
        [
            sys.executable,
            "scripts/publish_portfolio.py",
        ],
        "Publishing property details page",
    ):
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
