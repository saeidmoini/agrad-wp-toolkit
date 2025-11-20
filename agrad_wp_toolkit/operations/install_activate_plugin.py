"""Install/update/activate plugins or themes across WordPress sites."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from .. import config_loader, directadmin, prompts, wp_cli, zip_repository, zip_staging
from . import zips
from . import download_links

logger = logging.getLogger(__name__)


def run_install_activate_plugin() -> None:
    catalog = config_loader.Catalog.load()
    item_type = prompts.ask_from_list(
        "What do you want to install?",
        ["Plugin", "Theme"],
    )
    type_key = "plugins" if item_type == "Plugin" else "themes"
    item_label = "plugin" if type_key == "plugins" else "theme"
    catalog_items = [item for item in catalog.items if item.type == type_key]

    install_items = _select_items(catalog_items, type_key, item_label)
    if not install_items:
        fallback = _prompt_manual_item(type_key, item_label)
        if not fallback:
            return
        install_items = [fallback]
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
        for item in install_items:
            try:
                _ensure_item(site, item, repo)
            except Exception as exc:  # pylint: disable=broad-except
                logger.error("Failed to ensure %s on %s: %s", item.name, site.domain, exc)


def _ensure_item(
    site: directadmin.Site,
    item: config_loader.UpdateItem,
    repo: zip_repository.ZipRepository,
) -> None:
    if item.type == "themes":
        _ensure_theme(site, item.name, item.source, item.force, repo)
        logger.info("Ensured theme %s installed on %s", item.name, site.domain)
        return
    _ensure_plugin(site, item.name, item.source, item.force, repo)
    logger.info("Ensured plugin %s active on %s", item.name, site.domain)


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


def _ensure_theme(
    site: directadmin.Site,
    slug: str,
    source: str,
    force: bool,
    repo: zip_repository.ZipRepository,
) -> None:
    site_path = site.path
    run_as = site.user
    if wp_cli.theme_is_installed(site_path, slug, run_as=run_as):
        _update_theme(site_path, slug, source, force, repo, run_as)
    else:
        _install_theme(site_path, slug, source, force, repo, run_as)


def _install_theme(
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
        args = ["theme", "install", str(staged)]
    else:
        args = ["theme", "install", slug]
    if force:
        args.append("--force")
    result = wp_cli._run_wp(args, site_path, run_as=run_as)  # type: ignore[attr-defined]
    if result.returncode != 0:
        if staged:
            zip_staging.cleanup_staged(staged)
        raise RuntimeError(result.stderr.strip())
    if staged:
        zip_staging.cleanup_staged(staged)


def _update_theme(
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
        args = ["theme", "install", str(staged), "--force"]
    else:
        args = ["theme", "update", slug]
        if force:
            args.append("--force")
    result = wp_cli._run_wp(args, site_path, run_as=run_as)  # type: ignore[attr-defined]
    if result.returncode != 0:
        if staged:
            zip_staging.cleanup_staged(staged)
        raise RuntimeError(result.stderr.strip())
    if staged:
        zip_staging.cleanup_staged(staged)


def _select_items(
    catalog_items: List[config_loader.UpdateItem],
    type_key: str,
    label: str,
) -> List[config_loader.UpdateItem]:
    if not catalog_items:
        return []
    if not prompts.ask_yes_no(f"Select {label}s from catalog?", True):
        return []
    if prompts.ask_yes_no(f"Install every catalog {label}?", False):
        selected = catalog_items
    else:
        chosen = prompts.ask_multi_select(
            f"Select {label}s to install",
            [item.name for item in catalog_items],
        )
        if not chosen:
            logger.info("No catalog %ss selected.", label)
            return []
        mapping = {item.name: item for item in catalog_items}
        selected = [mapping[name] for name in chosen]
    force_all = prompts.ask_yes_no("Force reinstall/update for selected items?", False)
    return [
        config_loader.UpdateItem(
            name=item.name,
            type=type_key,
            source=item.source,
            force=force_all or item.force,
        )
        for item in selected
    ]


def _prompt_manual_item(type_key: str, label: str) -> config_loader.UpdateItem | None:
    print(f"Enter the {label} slug (matches folder name inside wp-content/{label}s).")
    print(
        "If you have a custom ZIP, place it in zips/ as <slug>_v<version>.zip before running this action."
    )
    slug = input(f"Enter {label} slug: ").strip()
    if not slug:
        logger.error("%s slug is required.", label.capitalize())
        return None
    source_choice = prompts.ask_from_list(
        f"{label.capitalize()} source",
        ["ZIP inside zips/", "WordPress.org"],
    )
    source = "zip" if source_choice.startswith("ZIP") else "wp.org"
    force = prompts.ask_yes_no("Force reinstall/update if already installed?", default=False)
    return config_loader.UpdateItem(
        name=slug,
        type=type_key,
        source=source,
        force=force,
    )
