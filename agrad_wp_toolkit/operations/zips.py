"""Normalize zip filenames and build manifest."""
from __future__ import annotations

import json
import logging
import re
import zipfile
from pathlib import Path
from typing import List

from .. import paths

logger = logging.getLogger(__name__)

VERSION_PATTERN = re.compile(r"([0-9]+\.[0-9]+(\.[0-9]+)?)")


def run_zip_normalization() -> None:
    manifest: List[dict] = []
    for entry in paths.ZIPS_DIR.glob("*.zip"):
        folder = _detect_folder(entry)
        if not folder:
            logger.warning("Could not detect top-level folder for %s", entry)
            continue
        version = _detect_version(entry.name)
        new_name = f"{folder}_v{version}.zip" if version else f"{folder}.zip"
        target = entry.with_name(new_name)
        if entry.name != new_name:
            logger.info("Renaming %s -> %s", entry.name, new_name)
            entry.rename(target)
            entry = target
        manifest.append({
            "zip": entry.name,
            "folder": folder,
            "version": version,
        })
    manifest_path = paths.ZIPS_DIR / "zip_folders.json"
    with manifest_path.open("w", encoding="utf-8") as fh:
        json.dump({"archives": manifest}, fh, indent=2)
    logger.info("Updated %s", manifest_path)


def _detect_folder(zip_path: Path) -> str | None:
    with zipfile.ZipFile(zip_path, "r") as archive:
        for member in archive.namelist():
            if "/" in member:
                folder = member.split("/", 1)[0]
                if folder:
                    return folder
    return None


def _detect_version(filename: str) -> str | None:
    match = VERSION_PATTERN.search(filename)
    if match:
        return match.group(1)
    return None
