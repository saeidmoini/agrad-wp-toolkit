"""Manage wp-config.php constants (cron, HTTP block list, etc.)."""
from __future__ import annotations

import logging
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from .. import config_loader, directadmin, prompts

logger = logging.getLogger(__name__)

CRON_CONSTANT = "DISABLE_WP_CRON"
HTTP_BLOCK_CONSTANT = "WP_HTTP_BLOCK_EXTERNAL"
HTTP_HOSTS_CONSTANT = "WP_ACCESSIBLE_HOSTS"
AUTO_UPDATER_CONSTANT = "AUTOMATIC_UPDATER_DISABLED"
CORE_AUTO_UPDATE_CONSTANT = "WP_AUTO_UPDATE_CORE"
FILE_MODS_CONSTANT = "DISALLOW_FILE_MODS"
DEBUG_CONSTANT = "WP_DEBUG"
DEBUG_LOG_CONSTANT = "WP_DEBUG_LOG"
DEBUG_DISPLAY_CONSTANT = "WP_DEBUG_DISPLAY"


@dataclass
class WPConfigManager:
    path: Path

    def read(self) -> str:
        return self.path.read_text(encoding="utf-8")

    def write(self, content: str) -> None:
        self.path.write_text(content, encoding="utf-8")

    def set_constant(self, name: str, value: str) -> None:
        content = self.read()
        pattern = re.compile(
            rf"^\s*define\(\s*['\"]{re.escape(name)}['\"],\s*.+?\);\s*$",
            re.MULTILINE,
        )
        line = f"define('{name}', {value});"
        replacement = f"\n{line}\n"
        if pattern.search(content):
            content = pattern.sub(f"{line}\n", content)
        else:
            anchor = "/* That's all, stop editing! Happy publishing. */"
            if anchor in content:
                content = content.replace(anchor, f"{replacement}{anchor}")
            else:
                if not content.endswith("\n"):
                    content += "\n"
                content += f"{line}\n"
        self.write(content)
        logger.debug("Updated %s in %s", name, self.path)

    def remove_constant(self, name: str) -> None:
        content = self.read()
        pattern = re.compile(rf"\s*define\(\s*['\"]{re.escape(name)}['\"].+?\);\s*\n?", re.MULTILINE)
        content, count = pattern.subn("", content)
        if count:
            self.write(content)
            logger.debug("Removed %s from %s", name, self.path)


def run_wp_config_menu() -> None:
    action = prompts.ask_from_list(
        "Select config management task",
        [
            "Toggle DISABLE_WP_CRON and cron job",
            "Update HTTP block settings",
            "Toggle automatic updates",
            "Toggle DISALLOW_FILE_MODS",
            "Toggle WP_DEBUG (enforce log/display flags)",
        ],
    )
    scope = prompts.ask_from_list("Apply to", ["All users", "Single user"])
    target_user = None
    if scope == "Single user":
        target_user = input("Enter DirectAdmin username: ").strip()
    sites = directadmin.resolve_sites(target_user)
    if not sites:
        logger.warning("No WordPress sites detected for scope %s", scope)
        return
    if action == "Toggle DISABLE_WP_CRON and cron job":
        _handle_wp_cron(sites)
    elif action == "Update HTTP block settings":
        _handle_http_block(sites)
    elif action == "Toggle automatic updates":
        _handle_auto_updates(sites)
    elif action == "Toggle DISALLOW_FILE_MODS":
        _handle_file_mods(sites)
    elif action == "Toggle WP_DEBUG (enforce log/display flags)":
        _handle_debug(sites)


def _handle_wp_cron(sites: list[directadmin.Site]) -> None:
    enable = prompts.ask_yes_no("Disable WP internal cron and add system cron?", default=True)
    for site in sites:
        manager = WPConfigManager(site.path / "wp-config.php")
        if enable:
            manager.set_constant(CRON_CONSTANT, "true")
            ensure_cron_job(site)
        else:
            manager.remove_constant(CRON_CONSTANT)
            remove_cron_job(site)


def ensure_cron_job(site: directadmin.Site) -> None:
    php_binary = detect_php_binary(site.user)
    cron_line = f"*/5\t*\t*\t*\t*\t{php_binary} {site.path / 'wp-cron.php'} >/dev/null 2>&1"
    current = read_user_crontab(site.user)
    if cron_line in current:
        return
    new_content = current + ("\n" if current and not current.endswith("\n") else "") + cron_line + "\n"
    write_user_crontab(site.user, new_content)
    logger.info("Added cron job for %s", site.user)


def remove_cron_job(site: directadmin.Site) -> None:
    php_binary = detect_php_binary(site.user)
    cron_line = f"*/5\t*\t*\t*\t*\t{php_binary} {site.path / 'wp-cron.php'} >/dev/null 2>&1"
    current = read_user_crontab(site.user)
    if cron_line not in current:
        return
    new_content = current.replace(cron_line + "\n", "")
    write_user_crontab(site.user, new_content)


def detect_php_binary(user: str) -> str:
    version_file = Path("/home") / user / ".php-version"
    if version_file.exists():
        version = version_file.read_text(encoding="utf-8").strip()
    else:
        version = "8.1"
    return f"/usr/local/lsws/fcgi-bin/lsphp-{version}"


def read_user_crontab(user: str) -> str:
    result = subprocess.run(["crontab", "-l", "-u", user], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return ""
    return result.stdout


def write_user_crontab(user: str, content: str) -> None:
    subprocess.run(["crontab", "-", "-u", user], input=content, text=True, check=True)


def _handle_http_block(sites: list[directadmin.Site]) -> None:
    data = config_loader.load_accessible_hosts()
    print("Current allow list:")
    for host in data["hosts"]:
        print(f" - {host}")
    if prompts.ask_yes_no("Would you like to edit the list?", default=False):
        hosts = _collect_host_inputs(data["hosts"])
        if hosts:
            config_loader.save_accessible_hosts(hosts)
            data["hosts"] = hosts
    enable = prompts.ask_yes_no("Enable WP_HTTP_BLOCK_EXTERNAL?", default=True)
    joined_hosts = ",".join(data["hosts"])
    for site in sites:
        manager = WPConfigManager(site.path / "wp-config.php")
        if enable:
            manager.set_constant(HTTP_BLOCK_CONSTANT, "true")
            manager.set_constant(HTTP_HOSTS_CONSTANT, f"'{joined_hosts}'")
        else:
            manager.remove_constant(HTTP_BLOCK_CONSTANT)
            manager.remove_constant(HTTP_HOSTS_CONSTANT)


def _handle_auto_updates(sites: list[directadmin.Site]) -> None:
    disable = prompts.ask_yes_no("Disable all automatic updates?", default=True)
    for site in sites:
        manager = WPConfigManager(site.path / "wp-config.php")
        if disable:
            manager.set_constant(AUTO_UPDATER_CONSTANT, "true")
            manager.set_constant(CORE_AUTO_UPDATE_CONSTANT, "false")
        else:
            manager.remove_constant(AUTO_UPDATER_CONSTANT)
            manager.remove_constant(CORE_AUTO_UPDATE_CONSTANT)


def _handle_file_mods(sites: list[directadmin.Site]) -> None:
    disable = prompts.ask_yes_no("Disallow file modifications?", default=True)
    for site in sites:
        manager = WPConfigManager(site.path / "wp-config.php")
        if disable:
            manager.set_constant(FILE_MODS_CONSTANT, "true")
        else:
            manager.remove_constant(FILE_MODS_CONSTANT)


def _handle_debug(sites: list[directadmin.Site]) -> None:
    enable_debug = prompts.ask_yes_no("Enable WP_DEBUG?", default=False)
    for site in sites:
        manager = WPConfigManager(site.path / "wp-config.php")
        # Always enforce logging to file and hide display
        manager.set_constant(DEBUG_LOG_CONSTANT, "true")
        manager.set_constant(DEBUG_DISPLAY_CONSTANT, "false")
        manager.set_constant(DEBUG_CONSTANT, "true" if enable_debug else "false")


def _collect_host_inputs(current_hosts: list[str]) -> list[str]:
    print("Enter host patterns (one per line or comma-separated). Leave empty to keep the current list.")
    entries: list[str] = []
    while True:
        line = input("Host (blank to finish): ").strip()
        if not line:
            break
        entries.extend(part.strip() for part in line.split(",") if part.strip())
    return entries if entries else current_hosts
