"""Shared filesystem paths used by the toolkit."""
from __future__ import annotations

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT_DIR / "config"
LOG_DIR = ROOT_DIR / "logs"
ZIPS_DIR = ROOT_DIR / "zips"
CATALOG_PATH = ROOT_DIR / "catalog.json"
WP_ACCESSIBLE_HOSTS_PATH = CONFIG_DIR / "accessible_hosts.json"
FREE_PLUGINS_PATH = CONFIG_DIR / "free_plugins.json"
PLUGIN_INVENTORY_PATH = ROOT_DIR / "inventory_plugins.json"


def ensure_dirs() -> None:
    """Create runtime directories required by the toolkit."""
    LOG_DIR.mkdir(exist_ok=True)
    ZIPS_DIR.mkdir(exist_ok=True)
    CONFIG_DIR.mkdir(exist_ok=True)
