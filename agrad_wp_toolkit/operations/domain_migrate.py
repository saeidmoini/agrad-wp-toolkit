"""Domain migration helper."""
from __future__ import annotations

import logging
from pathlib import Path

from .. import wp_cli

logger = logging.getLogger(__name__)


def run_domain_migration() -> None:
    user = input("DirectAdmin user: ").strip()
    old_domain = input("Old domain (e.g. example.com): ").strip()
    new_domain = input("New domain (e.g. newsite.com): ").strip()
    if not all([user, old_domain, new_domain]):
        logger.error("User, old domain, and new domain are required.")
        return
    site_path = Path("/home") / user / "domains" / old_domain / "public_html"
    if not site_path.exists():
        logger.error("Path %s does not exist.", site_path)
        return
    if not wp_cli.ensure_wp_cli():
        return
    _run_migration(site_path, old_domain, new_domain)


def _run_migration(site_path: Path, old_domain: str, new_domain: str) -> None:
    replacements = [
        (f"https://{old_domain}", f"https://{new_domain}"),
        (f"http://{old_domain}", f"https://{new_domain}"),
        (f"https://www.{old_domain}", f"https://{new_domain}"),
        (f"http://www.{old_domain}", f"https://{new_domain}"),
    ]
    wp_cli._run_wp(["option", "update", "home", f"https://{new_domain}"], site_path)  # type: ignore[attr-defined]
    wp_cli._run_wp(["option", "update", "siteurl", f"https://{new_domain}"], site_path)  # type: ignore[attr-defined]
    for needle, replacement in replacements:
        wp_cli._run_wp(
            ["search-replace", needle, replacement, "--all-tables", "--precise", "--recurse-objects"],
            site_path,
        )  # type: ignore[attr-defined]
    wp_cli._run_wp(["cache", "flush"], site_path)  # type: ignore[attr-defined]
    wp_cli._run_wp(["rewrite", "flush", "--hard"], site_path)  # type: ignore[attr-defined]
    wp_cli._run_wp(["elementor", "flush-css"], site_path)  # type: ignore[attr-defined]
    logger.info("Completed domain migration for %s", site_path)
