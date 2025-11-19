"""Download free plugins from WordPress.org."""
from __future__ import annotations

import json
import logging
import urllib.request
from pathlib import Path

from .. import config_loader, paths, zip_repository

logger = logging.getLogger(__name__)


def run_free_downloads() -> None:
    slugs = config_loader.load_free_plugin_slugs()
    repo = zip_repository.ZipRepository()
    for slug in slugs:
        try:
            version = _fetch_version(slug)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Failed to fetch version for %s: %s", slug, exc)
            continue
        artifact = repo.get(slug)
        if artifact and artifact.version == version:
            logger.info("Latest version %s for %s already downloaded.", version, slug)
            continue
        logger.info("Downloading %s version %s", slug, version)
        if not _download_plugin(slug, version):
            logger.warning("Falling back to unversioned download for %s", slug)
            _download_plugin(slug, None)


def _fetch_version(slug: str) -> str:
    url = f"https://api.wordpress.org/plugins/info/1.2/?action=plugin_information&request[slug]={slug}"
    with urllib.request.urlopen(url, timeout=10) as resp:
        data = json.load(resp)
    version = data.get("version")
    if not version:
        raise RuntimeError(f"No version reported for {slug}")
    return version


def _download_plugin(slug: str, version: str | None) -> bool:
    if version:
        url = f"https://downloads.wordpress.org/plugin/{slug}.{version}.zip"
        target = paths.ZIPS_DIR / f"{slug}_v{version}.zip"
    else:
        url = f"https://downloads.wordpress.org/plugin/{slug}.zip"
        target = paths.ZIPS_DIR / f"{slug}.zip"
    try:
        with urllib.request.urlopen(url, timeout=30) as response, target.open("wb") as fh:
            fh.write(response.read())
        logger.info("Downloaded %s", target.name)
        return True
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Download failed for %s: %s", slug, exc)
        if target.exists():
            target.unlink()
        return False
