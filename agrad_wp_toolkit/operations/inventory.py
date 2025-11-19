"""Collect plugin inventory across all sites."""
from __future__ import annotations

import logging
from typing import Dict, Set

from .. import config_loader, directadmin, paths, wp_cli

logger = logging.getLogger(__name__)


def run_inventory() -> None:
    sites = directadmin.resolve_sites()
    if not sites:
        logger.warning("No WordPress sites discovered.")
        return
    if not wp_cli.ensure_wp_cli():
        return
    inventory: Set[str] = set()
    for site in sites:
        try:
            result = wp_cli.list_plugins(site.path)
            for entry in result:
                inventory.add(entry["name"])
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Failed to list plugins for %s: %s", site.domain, exc)
    payload: Dict[str, list[dict]] = {"plugins": [{"name": name} for name in sorted(inventory)]}
    config_loader.write_json(paths.PLUGIN_INVENTORY_PATH, payload)
    logger.info("Plugin inventory saved to %s", paths.PLUGIN_INVENTORY_PATH)
