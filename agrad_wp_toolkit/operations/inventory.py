"""Collect plugin inventory across all sites."""
from __future__ import annotations

import logging
from typing import Dict, Set

from .. import config_loader, directadmin, paths, wp_cli

logger = logging.getLogger(__name__)


def run_inventory() -> None:
    catalog = config_loader.Catalog.load()
    known_plugins = _catalog_plugin_slugs(catalog)
    sites = directadmin.resolve_sites()
    if not sites:
        logger.warning("No WordPress sites discovered.")
        return
    if not wp_cli.ensure_wp_cli():
        return
    inventory: Dict[str, str] = {}
    for site in sites:
        logger.info("Listing plugins for %s", site.domain)
        try:
            result = wp_cli.list_plugins(site.path, run_as=site.user)
            for entry in result:
                name = entry.get("name")
                if not name:
                    continue
                slug = name.lower()
                if slug in known_plugins:
                    continue
                inventory.setdefault(name, site.domain)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Failed to list plugins for %s: %s", site.domain, exc)
    payload: Dict[str, list[dict]] = {
        "plugins": [
            {"name": name, "first_site": inventory[name]} for name in sorted(inventory)
        ]
    }
    config_loader.write_json(paths.PLUGIN_INVENTORY_PATH, payload)
    logger.info("Plugin inventory saved to %s", paths.PLUGIN_INVENTORY_PATH)


def _catalog_plugin_slugs(catalog: config_loader.Catalog) -> Set[str]:
    return {item.name.lower() for item in catalog.items if item.type == "plugins"}
