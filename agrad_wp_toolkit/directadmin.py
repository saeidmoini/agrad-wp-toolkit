"""Helpers to discover DirectAdmin users and WordPress installations."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

logger = logging.getLogger(__name__)


def iter_directadmin_users(explicit_user: str | None = None) -> Iterable[Path]:
    base = Path("/home")
    if explicit_user:
        candidate = base / explicit_user
        if candidate.is_dir():
            yield candidate
        else:
            logger.warning("User %s not found under /home", explicit_user)
        return
    for path in base.iterdir():
        if path.is_dir():
            yield path


def is_wp_root(path: Path) -> bool:
    return (path / "wp-config.php").is_file() and (path / "wp-content").is_dir()


def discover_wp_roots(user_root: Path) -> List[Path]:
    """Discover WordPress installations for a DirectAdmin user."""
    results: List[Path] = []
    domains_root = user_root / "domains"
    if not domains_root.is_dir():
        return results
    for domain_dir in domains_root.iterdir():
        if not domain_dir.is_dir():
            continue
        public_html = domain_dir / "public_html"
        if public_html.is_dir():
            results.extend(_discover_under(public_html))
    return results


def _discover_under(public_html: Path) -> List[Path]:
    found: List[Path] = []
    for root, dirs, files in os.walk(public_html):
        root_path = Path(root)
        if "wp-config.php" in files:
            found.append(root_path)
        # prune heavy directories to keep scan fast
        dirs[:] = [d for d in dirs if d not in {"wp-admin", "wp-content", "wp-includes"}]
    return found


@dataclass
class Site:
    user: str
    path: Path

    @property
    def domain(self) -> str:
        return self.path.parts[self.path.parts.index("domains") + 1]


def resolve_sites(target_user: str | None = None) -> List[Site]:
    sites: List[Site] = []
    for user_path in iter_directadmin_users(target_user):
        user = user_path.name
        for root in discover_wp_roots(user_path):
            sites.append(Site(user=user, path=root))
    return sites
