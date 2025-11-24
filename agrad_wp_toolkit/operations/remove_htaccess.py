"""Remove malicious .htaccess files."""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Tuple

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
        if directadmin.is_wp_root(parent):
            _inspect_wp_root_htaccess(htaccess)
            continue
        if parent.name == "public_html" or "public_html" in parent.parts:
            logger.debug("Skipping %s (inside public_html)", htaccess)
            continue
        try:
            htaccess.unlink()
            logger.info("Removed %s", htaccess)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Failed to remove %s: %s", htaccess, exc)


MALICIOUS_MARKERS = [
    "wp-l0gin.php",
    "wp-the1me.php",
    "wp-scr1pts.php",
    "lock360.php",
    "radio.php",
    "content.php",
    "mah.php",
    "jp.php",
    "ext.php",
]

SINGLE_SITE_RULES = """# BEGIN WordPress

RewriteEngine On
RewriteRule .* - [E=HTTP_AUTHORIZATION:%{HTTP:Authorization}]
RewriteBase /
RewriteRule ^index\\.php$ - [L]
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule . /index.php [L]

# END WordPress
"""

MULTISITE_SUBFOLDER_RULES = """# BEGIN WordPress Multisite
# Using subfolder network type: https://wordpress.org/documentation/article/htaccess/#multisite

RewriteEngine On
RewriteRule .* - [E=HTTP_AUTHORIZATION:%{HTTP:Authorization}]
RewriteBase /
RewriteRule ^index\\.php$ - [L]

# add a trailing slash to /wp-admin
RewriteRule ^([_0-9a-zA-Z-]+/)?wp-admin$ $1wp-admin/ [R=301,L]

RewriteCond %{REQUEST_FILENAME} -f [OR]
RewriteCond %{REQUEST_FILENAME} -d
RewriteRule ^ - [L]
RewriteRule ^([_0-9a-zA-Z-]+/)?(wp-(content|admin|includes).*) $2 [L]
RewriteRule ^([_0-9a-zA-Z-]+/)?(.*\\.php)$ $2 [L]
RewriteRule . index.php [L]

# END WordPress Multisite
"""

MULTISITE_SUBDOMAIN_RULES = """# BEGIN WordPress Multisite
# Using subdomain network type: https://wordpress.org/documentation/article/htaccess/#multisite

RewriteEngine On
RewriteRule .* - [E=HTTP_AUTHORIZATION:%{HTTP:Authorization}]
RewriteBase /
RewriteRule ^index\\.php$ - [L]

# add a trailing slash to /wp-admin
RewriteRule ^wp-admin$ wp-admin/ [R=301,L]

RewriteCond %{REQUEST_FILENAME} -f [OR]
RewriteCond %{REQUEST_FILENAME} -d
RewriteRule ^ - [L]
RewriteRule ^(wp-(content|admin|includes).*) $1 [L]
RewriteRule ^(.*\\.php)$ $1 [L]
RewriteRule . index.php [L]

# END WordPress Multisite
"""


def _inspect_wp_root_htaccess(htaccess: Path) -> None:
    try:
        contents = htaccess.read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("Could not read %s: %s", htaccess, exc)
        return
    if not _has_malicious_rules(contents):
        logger.debug("Skipping %s (no malicious markers)", htaccess)
        return
    safe_rules = _select_safe_rules(htaccess.parent)
    try:
        htaccess.write_text(safe_rules, encoding="utf-8")
        logger.info("Replaced malicious .htaccess at %s", htaccess)
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Failed to rewrite %s: %s", htaccess, exc)


def _has_malicious_rules(contents: str) -> bool:
    if '<FilesMatch ".(py|exe|php)$">' in contents:
        return True
    for marker in MALICIOUS_MARKERS:
        if marker in contents:
            return True
    return False


def _select_safe_rules(site_root: Path) -> str:
    is_multisite, is_subdomain = _detect_multisite(site_root)
    if is_multisite:
        return MULTISITE_SUBDOMAIN_RULES if is_subdomain else MULTISITE_SUBFOLDER_RULES
    return SINGLE_SITE_RULES


def _detect_multisite(site_root: Path) -> Tuple[bool, bool]:
    """Return (is_multisite, is_subdomain). Defaults to (False, False) if unknown."""
    config = site_root / "wp-config.php"
    if not config.exists():
        return False, False
    try:
        data = config.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False, False
    lowered = data.lower()
    is_multisite = bool(re.search(r"define\(\s*['\"]multisite['\"]\s*,\s*true", lowered))
    is_subdomain = bool(re.search(r"define\(\s*['\"]subdomain_install['\"]\s*,\s*true", lowered))
    return is_multisite, is_subdomain
