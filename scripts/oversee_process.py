import shutil
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
GO_BIN = Path("/usr/local/go/bin/go")


def resolve_go_binary() -> str:
    """Return the production Go binary when available, otherwise use PATH."""
    if GO_BIN.exists():
        return str(GO_BIN)

    fallback = shutil.which("go")
    if fallback:
        return fallback

    raise FileNotFoundError("go")


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
        print(f"Error: command not found: {error.filename}")
        return False
    except subprocess.CalledProcessError as error:
        print(
            f"Error: {description} failed "
            f"with exit code {error.returncode}."
        )
        return False

    print(f"{description} completed successfully.")
    return True


def main() -> int:
    try:
        go_binary = resolve_go_binary()
    except FileNotFoundError:
        print("Error: command not found: go")
        return 1

    steps = [
        (
            [go_binary, "run", "."],
            "Fetching property data",
        ),
        (
            [sys.executable, "scripts/publish_portfolio.py"],
            "Publishing property details page",
        ),
    ]

    for command, description in steps:
        if not run_command(command, description):
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
