"""Install/update/activate a plugin across WordPress sites."""
from __future__ import annotations

import logging
from pathlib import Path

from .. import config_loader, directadmin, prompts, wp_cli, zip_repository, zip_staging
from . import zips
from . import download_links

logger = logging.getLogger(__name__)


def run_install_activate_plugin() -> None:
    catalog = config_loader.Catalog.load()
    plugin_items = [item for item in catalog.items if item.type == "plugins"]
    slug: str
    source: str
    force = False
    selected_item = None
    if plugin_items and prompts.ask_yes_no("Select plugin from catalog?", True):
        name = prompts.ask_from_list("Choose plugin", [item.name for item in plugin_items])
        selected_item = next(item for item in plugin_items if item.name == name)
        slug = selected_item.name
        source = selected_item.source
        force = prompts.ask_yes_no(
            "Force reinstall/update for this plugin?",
            default=selected_item.force,
        )
    else:
        print("Enter the plugin slug (matches folder name inside wp-content/plugins).")
        print("If you have a custom ZIP, place it in the zips/ folder as <slug>_v<version>.zip before running this action.")
        slug = input("Enter plugin slug: ").strip()
        if not slug:
            logger.error("Plugin slug is required.")
            return
        source_choice = prompts.ask_from_list(
            "Plugin source",
            ["ZIP inside zips/", "WordPress.org"],
        )
        source = "zip" if source_choice.startswith("ZIP") else "wp.org"
        force = prompts.ask_yes_no("Force reinstall/update if already installed?", default=False)

    scope = prompts.ask_from_list("Target scope", ["All users", "Single user"])
    target_user = None
    if scope == "Single user":
        target_user = input("Enter DirectAdmin username: ").strip()

    if not wp_cli.ensure_wp_cli():
        return
    sites = directadmin.resolve_sites(target_user)
    if not sites:
        logger.warning("No WordPress sites found for the selected scope.")
        return

    zips.run_zip_normalization()
    download_links.prune_old_zip_versions()
    repo = zip_repository.ZipRepository()
    for site in sites:
        try:
            _ensure_plugin(site, slug, source, force, repo)
            logger.info("Ensured plugin %s active on %s", slug, site.domain)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Failed to ensure %s on %s: %s", slug, site.domain, exc)


def _ensure_plugin(
    site: directadmin.Site,
    slug: str,
    source: str,
    force: bool,
    repo: zip_repository.ZipRepository,
) -> None:
    site_path = site.path
    run_as = site.user
    if wp_cli.plugin_is_installed(site_path, slug, run_as=run_as):
        _update_plugin(site_path, slug, source, force, repo, run_as)
    else:
        _install_plugin(site_path, slug, source, force, repo, run_as)
    wp_cli.activate_plugin(site_path, slug, run_as=run_as)


def _install_plugin(
    site_path: Path,
    slug: str,
    source: str,
    force: bool,
    repo: zip_repository.ZipRepository,
    run_as: str,
) -> None:
    staged = None
    if source == "zip":
        artifact = repo.get(slug)
        if not artifact:
            raise RuntimeError(
                f"No ZIP found for {slug}. Place {slug}.zip or {slug}_v*.zip inside zips/."
            )
        staged = zip_staging.stage_for_user(artifact.path, run_as)
        args = ["plugin", "install", str(staged)]
    else:
        args = ["plugin", "install", slug]
    if force:
        args.append("--force")
    result = wp_cli._run_wp(args, site_path, run_as=run_as)  # type: ignore[attr-defined]
    if result.returncode != 0:
        if staged:
            zip_staging.cleanup_staged(staged)
        raise RuntimeError(result.stderr.strip())
    if staged:
        zip_staging.cleanup_staged(staged)


def _update_plugin(
    site_path: Path,
    slug: str,
    source: str,
    force: bool,
    repo: zip_repository.ZipRepository,
    run_as: str,
) -> None:
    staged = None
    if source == "zip":
        artifact = repo.get(slug)
        if not artifact:
            raise RuntimeError(
                f"No ZIP found for {slug}. Place {slug}.zip or {slug}_v*.zip inside zips/."
            )
        staged = zip_staging.stage_for_user(artifact.path, run_as)
        args = ["plugin", "install", str(staged), "--force"]
    else:
        args = ["plugin", "update", slug]
        if force:
            args.append("--force")
    result = wp_cli._run_wp(args, site_path, run_as=run_as)  # type: ignore[attr-defined]
    if result.returncode != 0:
        if staged:
            zip_staging.cleanup_staged(staged)
        raise RuntimeError(result.stderr.strip())
    if staged:
        zip_staging.cleanup_staged(staged)
