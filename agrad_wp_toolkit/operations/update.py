"""Update operations for plugins, themes, and WordPress core."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, List

from .. import config_loader, directadmin, paths, prompts, wp_cli, zip_repository
from . import zips

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
        selection = prompts.ask_multi_select("Select items to update", catalog.get_names())
        if not selection:
            logger.info("No items selected. Nothing to do.")
            return

    force_run = prompts.ask_yes_no("Force reinstall even if up-to-date?", default=False)
    zips.run_zip_normalization()
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
        for item in payload:
            try:
                _update_item(site.path, item, zip_repo, free_slugs)
            except Exception as exc:  # pylint: disable=broad-except
                logger.error("Failed to update %s on %s: %s", item.name, site.domain, exc)


def _update_item(
    site_path: Path,
    item: config_loader.UpdateItem,
    zip_repo: zip_repository.ZipRepository,
    free_slugs: Iterable[str],
) -> None:
    kind = _map_kind(item.type)
    if item.source == "zip":
        artifact = zip_repo.get(item.name)
        if not artifact:
            raise RuntimeError(f"No ZIP found for {item.name} inside {paths.ZIPS_DIR}")
        wp_cli.install_from_zip(site_path, artifact.path, kind, force=item.force)
        return
    if item.name.lower() in free_slugs or item.source == "wp.org":
        wp_cli.update_from_repo(site_path, item.name, kind, force=item.force)
        return
    raise RuntimeError(f"Unknown source for {item.name}; set source to 'zip' or 'wp.org'")


def _map_kind(item_type: str) -> str:
    if item_type == "themes":
        return "theme"
    if item_type == "wordpress":
        return "core"
    return "plugin"
