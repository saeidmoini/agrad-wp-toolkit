"""Wrapper utilities for wp-cli interactions."""
from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, Sequence

logger = logging.getLogger(__name__)


class WPCLIError(RuntimeError):
    pass


def _run_wp(args: Sequence[str], site_path: Path, run_as: str | None = None) -> subprocess.CompletedProcess:
    cmd = ["wp", f"--path={site_path}", "--allow-root", *args]
    if run_as:
        cmd = ["sudo", "-u", run_as, *cmd]
    logger.debug("Running wp command: %s", " ".join(cmd))
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def ensure_wp_cli() -> bool:
    result = subprocess.run(["which", "wp"], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        logger.error("wp-cli binary not found in PATH")
        return False
    return True


def install_from_zip(site_path: Path, zip_path: Path, kind: str, force: bool = False, run_as: str | None = None) -> None:
    args = [kind, "install", str(zip_path)]
    if force:
        args.append("--force")
    result = _run_wp(args, site_path, run_as=run_as)
    if result.returncode != 0:
        raise WPCLIError(result.stderr.strip())
    logger.info("Installed %s from %s under %s", kind, zip_path.name, site_path)


def update_from_repo(site_path: Path, slug: str, kind: str, force: bool = False, run_as: str | None = None) -> None:
    if kind == "core":
        args = ["core", "update"]
    else:
        args = [kind, "update", slug]
    if force and kind != "core":
        args.append("--force")
    result = _run_wp(args, site_path, run_as=run_as)
    if result.returncode != 0:
        raise WPCLIError(result.stderr.strip())
    logger.info("Updated %s %s at %s", kind, slug, site_path)


def list_plugins(site_path: Path, run_as: str | None = None) -> Dict[str, Any]:
    result = _run_wp(["plugin", "list", "--format=json"], site_path, run_as=run_as)
    if result.returncode != 0:
        raise WPCLIError(result.stderr.strip())
    return json.loads(result.stdout)


def list_themes(site_path: Path, run_as: str | None = None) -> Dict[str, Any]:
    result = _run_wp(["theme", "list", "--format=json"], site_path, run_as=run_as)
    if result.returncode != 0:
        raise WPCLIError(result.stderr.strip())
    return json.loads(result.stdout)


def plugin_is_installed(site_path: Path, slug: str, run_as: str | None = None) -> bool:
    result = _run_wp(["plugin", "is-installed", slug], site_path, run_as=run_as)
    return result.returncode == 0


def activate_plugin(site_path: Path, slug: str, run_as: str | None = None) -> None:
    result = _run_wp(["plugin", "activate", slug], site_path, run_as=run_as)
    if result.returncode != 0:
        raise WPCLIError(result.stderr.strip())


def core_version(site_path: Path, run_as: str | None = None) -> str:
    result = _run_wp(["core", "version"], site_path, run_as=run_as)
    if result.returncode != 0:
        raise WPCLIError(result.stderr.strip())
    return result.stdout.strip()


def core_download(site_path: Path, run_as: str | None = None, version: str | None = None) -> None:
    args = ["core", "download", "--skip-content", "--force"]
    if version:
        args.extend(["--version", version])
    result = _run_wp(args, site_path, run_as=run_as)
    if result.returncode != 0:
        raise WPCLIError(result.stderr.strip())
    logger.info("Downloaded WordPress core into %s", site_path)
