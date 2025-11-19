"""Remove malicious .htaccess files."""
from __future__ import annotations

import logging
from pathlib import Path

from .. import directadmin, prompts

logger = logging.getLogger(__name__)


def run_htaccess_cleanup() -> None:
    scope = prompts.ask_from_list("Clean .htaccess for", ["All users", "Single user"])
    target_user = None
    if scope == "Single user":
        target_user = input("Enter DirectAdmin username: ").strip()
    users = directadmin.iter_directadmin_users(target_user)
    for user_dir in users:
        _cleanup_user_htaccess(user_dir)


def _cleanup_user_htaccess(user_dir: Path) -> None:
    for htaccess in user_dir.rglob(".htaccess"):
        parent = htaccess.parent
        if parent.name == "public_html" or "public_html" in parent.parts:
            logger.debug("Skipping %s (inside public_html)", htaccess)
            continue
        try:
            htaccess.unlink()
            logger.info("Removed %s", htaccess)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Failed to remove %s: %s", htaccess, exc)
