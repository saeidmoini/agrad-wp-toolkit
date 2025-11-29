"""Interactive CLI entry point for the toolkit."""
from __future__ import annotations

import argparse
import logging

from . import logging_utils, paths, prompts
from .operations import (
    domain_migrate,
    download_links,
    free_downloads,
    install_activate_plugin,
    inventory,
    remove_htaccess,
    remove_plugin,
    security,
    update,
    update_audit,
    wp_config,
)

ACTIONS = {
    "update": ("Update plugins/themes/core", update.run_interactive_update),
    "remove-plugin": ("Remove a plugin everywhere", remove_plugin.run_remove_plugin),
    "clean-htaccess": ("Clean malicious .htaccess files", remove_htaccess.run_htaccess_cleanup),
    "migrate-domain": ("Migrate domain", domain_migrate.run_domain_migration),
    "wp-config": ("Manage wp-config flags", wp_config.run_wp_config_menu),
    "download-free": ("Download free plugins", free_downloads.run_free_downloads),
    "inventory": ("Collect plugin inventory", inventory.run_inventory),
    "install-plugin": (
        "Install/activate plugins or install themes everywhere",
        install_activate_plugin.run_install_activate_plugin,
    ),
    "download-links": (
        "Download custom ZIPs from link list",
        download_links.run_link_downloader,
    ),
    "audit-zips": (
        "Check a site's update list to see which ZIPs are outdated",
        update_audit.run_update_audit,
    ),
    "manage-addons": (
        "Manage plugins/themes (submenu)",
        lambda: manage_plugins_and_themes(),
    ),
    "security": ("Security tools (firewall/IP allowlist)", security.run_security_menu),
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Agrad WP Toolkit interactive CLI")
    parser.add_argument("--quiet", action="store_true", help="Only log to file")
    parser.add_argument(
        "--action",
        choices=list(ACTIONS.keys()),
        help="Run a specific action non-interactively",
    )
    args = parser.parse_args()
    logging_utils.setup_logging(verbose=not args.quiet)
    paths.ensure_dirs()
    if args.action:
        _, handler = ACTIONS[args.action]
        handler()
        return
    options = {
        "Manage plugins/themes": manage_plugins_and_themes,
        "Security": security.run_security_menu,
        "Clean .htaccess files": remove_htaccess.run_htaccess_cleanup,
        "Migrate domain": domain_migrate.run_domain_migration,
        "Manage wp-config flags": wp_config.run_wp_config_menu,
        "Exit": None,
    }
    while True:
        choice = prompts.ask_from_list("Select an action", list(options))
        if choice == "Exit":
            logging.getLogger(__name__).info("Goodbye!")
            break
        action = options.get(choice)
        if action:
            action()


def manage_plugins_and_themes() -> None:
    options = [
        "Update plugins/themes/core",
        "Remove a plugin everywhere",
        "Download free plugins",
        "Collect plugin inventory (non-catalog only)",
        "Install/activate plugins or install themes",
        "Download custom ZIPs from link list",
        "Audit ZIP freshness vs site updates",
        "Back",
    ]
    mapping = {
        "Update plugins/themes/core": update.run_interactive_update,
        "Remove a plugin everywhere": remove_plugin.run_remove_plugin,
        "Download free plugins": free_downloads.run_free_downloads,
        "Collect plugin inventory (non-catalog only)": inventory.run_inventory,
        "Install/activate plugins or install themes": install_activate_plugin.run_install_activate_plugin,
        "Download custom ZIPs from link list": download_links.run_link_downloader,
        "Audit ZIP freshness vs site updates": update_audit.run_update_audit,
    }
    while True:
        choice = prompts.ask_from_list("Manage plugins/themes", options)
        if choice == "Back":
            break
        handler = mapping.get(choice)
        if handler:
            handler()
