"""Update operations for plugins, themes, and WordPress core."""
from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .. import config_loader, directadmin, paths, prompts, wp_cli, zip_repository
from .. import zip_staging
from . import zips
from . import download_links

logger = logging.getLogger(__name__)


def run_interactive_update() -> None:
    catalog = config_loader.Catalog.load()
    if not catalog.items:
        logger.error("Catalog (catalog.json) is empty.")
        return
    scope = prompts.ask_from_list(
        "Which scope do you want to update?",
        ["All users", "Single user"],
    )
    target_user = None
    if scope == "Single user":
        target_user = input("Enter DirectAdmin username: ").strip()
    include_all = prompts.ask_yes_no("Apply updates to every catalog entry?", default=True)
    if include_all:
        selection = catalog.get_names()
    else:
        display = [f"[{item.type}] {item.name}" for item in catalog.items]
        chosen = prompts.ask_multi_select("Select items to update", display)
        mapping = {label: item.name for label, item in zip(display, catalog.items)}
        selection = [mapping[label] for label in chosen]
        if not selection:
            logger.info("No items selected. Nothing to do.")
            return

    force_run = prompts.ask_yes_no("Force reinstall even if up-to-date?", default=False)
    zips.run_zip_normalization()
    download_links.prune_old_zip_versions()
    payload = catalog.to_update_payload(selection, force_run)
    zip_repo = zip_repository.ZipRepository()

    if not wp_cli.ensure_wp_cli():
        return
    sites = directadmin.resolve_sites(target_user)
    if not sites:
        logger.warning("No WordPress sites found for the selected scope.")
        return

    free_slugs = {slug.lower() for slug in config_loader.load_free_plugin_slugs()}
    for site in sites:
        logger.info("Processing %s (%s)", site.domain, site.path)
        installed_versions = _collect_installed_versions(site.path, site.user)
        for item in payload:
            try:
                _update_item(site.path, item, zip_repo, free_slugs, installed_versions, site.user)
            except Exception as exc:  # pylint: disable=broad-except
                logger.error("Failed to update %s on %s: %s", item.name, site.domain, exc)


def _update_item(
    site_path: Path,
    item: config_loader.UpdateItem,
    zip_repo: zip_repository.ZipRepository,
    free_slugs: Iterable[str],
    installed_versions: Dict[str, Dict[str, Optional[str]]],
    run_as: str,
) -> None:
    kind = _map_kind(item.type)
    installed_version = _lookup_installed_version(kind, item.name, installed_versions)
    if kind in {"plugin", "theme"} and installed_version is None:
        logger.info("Skipping %s on %s (not installed)", item.name, site_path)
        return
    if kind == "core":
        _update_wordpress_core(site_path, item, installed_version, run_as, zip_repo)
        return
    if item.source == "zip":
        artifact = zip_repo.get(item.name)
        if not artifact:
            raise RuntimeError(f"No ZIP found for {item.name} inside {paths.ZIPS_DIR}")
        if (
            not item.force
            and installed_version
            and artifact.version
            and not _version_changed(artifact.version, installed_version)
        ):
            logger.info("Skipping %s on %s (already at version %s)", item.name, site_path, installed_version)
            return
        staged = zip_staging.stage_for_user(artifact.path, run_as)
        try:
            wp_cli.install_from_zip(site_path, staged, kind, force=True, run_as=run_as)
        finally:
            zip_staging.cleanup_staged(staged)
        return
    if item.name.lower() in free_slugs or item.source == "wp.org":
        wp_cli.update_from_repo(site_path, item.name, kind, force=item.force, run_as=run_as)
        return
    raise RuntimeError(f"Unknown source for {item.name}; set source to 'zip' or 'wp.org'")


def _map_kind(item_type: str) -> str:
    if item_type == "themes":
        return "theme"
    if item_type == "wordpress":
        return "core"
    return "plugin"


def _collect_installed_versions(site_path: Path, run_as: str) -> Dict[str, Dict[str, Optional[str]]]:
    data: Dict[str, Dict[str, Optional[str]]] = {
        "plugins": {},
        "themes": {},
        "core": {"wordpress": None},
    }
    try:
        for entry in wp_cli.list_plugins(site_path, run_as=run_as):
            data["plugins"][entry["name"].lower()] = entry.get("version")
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("Could not list plugins for %s: %s", site_path, exc)
    try:
        for entry in wp_cli.list_themes(site_path, run_as=run_as):
            data["themes"][entry["name"].lower()] = entry.get("version")
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("Could not list themes for %s: %s", site_path, exc)
    try:
        data["core"]["wordpress"] = wp_cli.core_version(site_path, run_as=run_as)
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("Could not determine WordPress version for %s: %s", site_path, exc)
    return data


def _lookup_installed_version(
    kind: str,
    slug: str,
    installed_versions: Dict[str, Dict[str, Optional[str]]],
) -> Optional[str]:
    if kind == "plugin":
        return installed_versions["plugins"].get(slug.lower())
    if kind == "theme":
        return installed_versions["themes"].get(slug.lower())
    if kind == "core":
        return installed_versions["core"].get("wordpress")
    return None


def _version_changed(zip_version: str, installed_version: str) -> bool:
    return _normalize_version(zip_version) != _normalize_version(installed_version)


def _normalize_version(version: str) -> str:
    return version.strip().lower().lstrip("v")


def _update_wordpress_core(
    site_path: Path,
    item: config_loader.UpdateItem,
    installed_version: Optional[str],
    run_as: str,
    zip_repo: zip_repository.ZipRepository,
) -> None:
    if not item.force and installed_version:
        logger.info("Skipping WordPress core (already at %s)", installed_version)
        return
    logger.info("Reinstalling WordPress core at %s", site_path)
    _clean_core_directories(site_path)
    artifact = zip_repo.get(item.name) if item.source == "zip" else None
    version_hint = artifact.version if artifact and artifact.version else None
    if version_hint:
        wp_cli.core_download(site_path, run_as=run_as, version=version_hint)
    else:
        wp_cli.core_download(site_path, run_as=run_as)
    wp_cli.update_from_repo(site_path, "wordpress", "core", force=True, run_as=run_as)


CORE_DIRS = ["wp-admin", "wp-includes"]
CORE_FILES = [
    'index.php', 'wp-activate.php', 'wp-blog-header.php', 'wp-comments-post.php',
    'wp-config-sample.php', 'wp-cron.php', 'wp-links-opml.php', 'wp-load.php',
    'wp-login.php', 'wp-mail.php', 'wp-settings.php', 'wp-signup.php',
    'wp-trackback.php', 'xmlrpc.php', 'readme.html', 'license.txt'
]


def _clean_core_directories(site_path: Path) -> None:
    for rel in CORE_DIRS:
        target = site_path / rel
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
    for filename in CORE_FILES:
        target = site_path / filename
        if target.exists():
            target.unlink()

