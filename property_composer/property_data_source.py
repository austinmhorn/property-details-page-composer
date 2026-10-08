from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"

DEFAULT_VM_PDE_DIR = Path(
    "/home/birchstonereporting/Property-Data-Engine"
)
DEFAULT_LOCAL_PDE_DIR = (
    Path.home()
    / "PROJECTS"
    / "(Data Engines)"
    / "Property-Data-Engine"
)


def resolve_property_data_engine_dir() -> Path:
    configured = os.getenv(
        "PROPERTY_DATA_ENGINE_DIR",
        "",
    ).strip()

    candidates = []
    if configured:
        candidates.append(
            Path(configured).expanduser()
        )

    candidates.extend(
        [
            DEFAULT_VM_PDE_DIR,
            DEFAULT_LOCAL_PDE_DIR,
        ]
    )

    for candidate in candidates:
        if (
            candidate.is_dir()
            and (candidate / "start.sh").is_file()
        ):
            return candidate.resolve()

    checked = ", ".join(
        str(path)
        for path in candidates
    )

    raise FileNotFoundError(
        "Property Data Engine could not be located. "
        "Set PROPERTY_DATA_ENGINE_DIR in secrets/.env. "
        f"Checked: {checked}"
    )


def run_property_data_engine() -> Path:
    engine_dir = (
        resolve_property_data_engine_dir()
    )

    print(
        "Using Property Data Engine: "
        f"{engine_dir}"
    )

    subprocess.run(
        ["bash", str(engine_dir / "start.sh")],
        cwd=engine_dir,
        check=True,
        env={
            **os.environ,
            "RUN_SOURCE": "dependency",
        },
    )

    return engine_dir


def sync_property_data_artifacts(
    engine_dir: Path,
) -> tuple[Path, Path]:
    source_csv = (
        engine_dir / "notion_data.csv"
    )
    source_metadata = (
        engine_dir / "property_fields.json"
    )

    missing = [
        str(path)
        for path in (
            source_csv,
            source_metadata,
        )
        if not path.is_file()
    ]

    if missing:
        raise FileNotFoundError(
            "Property Data Engine completed but "
            "required artifact(s) are missing: "
            + ", ".join(missing)
        )

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    csv_target = (
        DATA_DIR / "notion_data.csv"
    )
    metadata_target = (
        DATA_DIR / "property_fields.json"
    )

    shutil.copy2(
        source_csv,
        csv_target,
    )
    shutil.copy2(
        source_metadata,
        metadata_target,
    )

    print(
        "Synced Property Data Engine artifacts:"
    )
    print(
        f"  {source_csv.name} -> {csv_target}"
    )
    print(
        "  "
        f"{source_metadata.name} -> "
        f"{metadata_target}"
    )

    return (
        csv_target,
        metadata_target,
    )


def refresh_property_data() -> tuple[Path, Path]:
    engine_dir = (
        run_property_data_engine()
    )

    return sync_property_data_artifacts(
        engine_dir
    )
