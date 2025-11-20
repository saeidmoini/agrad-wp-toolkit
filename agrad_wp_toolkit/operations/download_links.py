"""Download ZIPs from a URL list and keep only the latest versions."""
from __future__ import annotations

import logging
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List, Tuple

from .. import paths
from ..zip_repository import ZIP_PATTERN

logger = logging.getLogger(__name__)
LINKS_FILE = paths.CONFIG_DIR / "zip_links.txt"


def run_link_downloader() -> None:
    paths.ensure_dirs()
    if not LINKS_FILE.exists():
        logger.error("Links file not found: %s", LINKS_FILE)
        return
    links = _read_links(LINKS_FILE)
    if not links:
        logger.warning("No URLs found inside %s", LINKS_FILE)
        return
    paths.ZIPS_DIR.mkdir(exist_ok=True)
    for url in links:
        _download_url(url, paths.ZIPS_DIR)
    logger.info("Finished downloading custom ZIPs.")


def _read_links(file_path: Path) -> List[str]:
    results: List[str] = []
    with file_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            results.append(line)
    return results


def _download_url(url: str, dest_dir: Path) -> None:
    file_name = _filename_from_url(url)
    if not file_name:
        logger.warning("Unable to determine filename for %s", url)
        return
    dest_path = dest_dir / file_name
    try:
        with urllib.request.urlopen(url, timeout=60) as response, dest_path.open("wb") as target:
            target.write(response.read())
        logger.info("Saved %s", dest_path.name)
    except urllib.error.URLError as exc:
        logger.error("Download failed for %s: %s", url, exc)


def _filename_from_url(url: str) -> str | None:
    parts = url.split("?")[0].rstrip("/").split("/")
    if not parts:
        return None
    return parts[-1]


def prune_old_zip_versions() -> None:
    """Keep only the highest version for each slug after normalization."""
    candidates: Dict[str, List[Tuple[Tuple[int, ...], Path]]] = {}
    for entry in paths.ZIPS_DIR.glob("*.zip"):
        match = ZIP_PATTERN.match(entry.name)
        if not match:
            continue
        slug = match.group("slug").lower()
        version = match.group("version") or "0"
        candidates.setdefault(slug, []).append((_version_key(version), entry))
    removed = 0
    for slug, versions in candidates.items():
        if len(versions) <= 1:
            continue
        versions.sort()
        to_remove = versions[:-1]
        for _, path in to_remove:
            try:
                path.unlink()
                removed += 1
                logger.info("Removed older ZIP for %s: %s", slug, path.name)
            except OSError as exc:
                logger.warning("Could not remove %s: %s", path, exc)
    if removed:
        logger.info("Pruned %d outdated ZIP(s).", removed)


def _version_key(version: str) -> Tuple[int, ...]:
    parts = [int(part) for part in re.split(r"[^0-9]+", version) if part.isdigit()]
    return tuple(parts) if parts else (0,)


__all__ = [
    "run_link_downloader",
    "prune_old_zip_versions",
    "_version_key",
]
