"""Remove plugin zips from all sites."""
from __future__ import annotations

import logging
from pathlib import Path

from .. import directadmin, prompts, wp_cli

logger = logging.getLogger(__name__)


def run_remove_plugin() -> None:
    plugin_slug = input("Enter plugin slug to remove: ").strip()
    if not plugin_slug:
        logger.error("Plugin slug is required.")
        return
    scope = prompts.ask_from_list("Remove from", ["All users", "Single user"])
    target_user = None
    if scope == "Single user":
        target_user = input("Enter DirectAdmin username: ").strip()

    sites = directadmin.resolve_sites(target_user)
    if not sites:
        logger.warning("No WordPress sites discovered.")
        return
    if not wp_cli.ensure_wp_cli():
        return
    for site in sites:
        try:
            _remove_plugin_from_site(site.path, plugin_slug)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Failed to remove %s from %s: %s", plugin_slug, site.domain, exc)


def _remove_plugin_from_site(site_path: Path, slug: str) -> None:
    deactivate = wp_cli._run_wp(["plugin", "deactivate", slug], site_path)  # type: ignore[attr-defined]
    if deactivate.returncode != 0:
        logger.warning(
            "Could not deactivate %s at %s: %s",
            slug,
            site_path,
            deactivate.stderr.strip(),
        )
    result = wp_cli._run_wp(["plugin", "delete", slug], site_path)  # type: ignore[attr-defined]
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    logger.info("Removed %s from %s", slug, site_path)
