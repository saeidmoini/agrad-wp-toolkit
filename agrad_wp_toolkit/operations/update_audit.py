"""Audit a chosen WordPress site and flag ZIPs that require updates."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Sequence, Tuple

from .. import directadmin, prompts, wp_cli, zip_repository

logger = logging.getLogger(__name__)


@dataclass
class UpdateCandidate:
    kind: str  # plugin | theme | core
    slug: str
    installed_version: str | None
    available_version: str | None = None


@dataclass
class UpdateFinding(UpdateCandidate):
    zip_version: str | None = None
    zip_name: str | None = None
    zip_missing: bool = True


def build_findings(
    candidates: Sequence[UpdateCandidate],
    repo: zip_repository.ZipRepository,
) -> List[UpdateFinding]:
    """Attach ZIP metadata to the given update candidates."""
    findings: List[UpdateFinding] = []
    for candidate in candidates:
        artifact = repo.get(candidate.slug)
        findings.append(
            UpdateFinding(
                kind=candidate.kind,
                slug=candidate.slug,
                installed_version=candidate.installed_version,
                available_version=candidate.available_version,
                zip_version=artifact.version if artifact else None,
                zip_name=artifact.path.name if artifact else None,
                zip_missing=artifact is None,
            )
        )
    return findings


def run_update_audit() -> None:
    """Interactive entry point for the update audit action."""
    if not wp_cli.ensure_wp_cli():
        return
    sites = directadmin.resolve_sites()
    if not sites:
        logger.warning("No WordPress sites discovered.")
        return
    site = _select_site(sites)
    if not site:
        logger.info("No site selected; aborting audit.")
        return
    logger.info("Checking update status reported by WordPress on %s", site.domain)
    candidates: List[UpdateCandidate] = []
    candidates.extend(_collect_plugin_updates(site))
    candidates.extend(_collect_theme_updates(site))
    core_candidate = _collect_core_update(site)
    if core_candidate:
        candidates.append(core_candidate)
    if not candidates:
        logger.info("Everything on %s is already up-to-date.", site.domain)
        return
    repo = zip_repository.ZipRepository()
    findings = build_findings(candidates, repo)
    _log_findings(site.domain, findings)


def _select_site(sites: Sequence[directadmin.Site]) -> directadmin.Site | None:
    labels = [
        f"{site.domain} ({site.user}) - {site.path}"
        for site in sites
    ]
    choice = prompts.ask_from_list("Select the site to audit", labels + ["Cancel"])
    if choice == "Cancel":
        return None
    mapping = dict(zip(labels, sites))
    return mapping[choice]


def _collect_plugin_updates(site: directadmin.Site) -> List[UpdateCandidate]:
    try:
        entries = wp_cli.list_plugins(
            site.path,
            run_as=site.user,
            fields=["name", "version", "update", "update_version"],
        )
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Failed to list plugins on %s: %s", site.domain, exc)
        return []
    updates: List[UpdateCandidate] = []
    for entry in entries:
        if entry.get("update") != "available":
            continue
        slug = entry.get("name")
        if not slug:
            continue
        slug = slug.lower()
        updates.append(
            UpdateCandidate(
                kind="plugin",
                slug=slug,
                installed_version=entry.get("version"),
                available_version=entry.get("update_version"),
            )
        )
    return updates


def _collect_theme_updates(site: directadmin.Site) -> List[UpdateCandidate]:
    try:
        entries = wp_cli.list_themes(
            site.path,
            run_as=site.user,
            fields=["name", "version", "update", "update_version"],
        )
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Failed to list themes on %s: %s", site.domain, exc)
        return []
    updates: List[UpdateCandidate] = []
    for entry in entries:
        if entry.get("update") != "available":
            continue
        slug = entry.get("name")
        if not slug:
            continue
        slug = slug.lower()
        updates.append(
            UpdateCandidate(
                kind="theme",
                slug=slug,
                installed_version=entry.get("version"),
                available_version=entry.get("update_version"),
            )
        )
    return updates


def _collect_core_update(site: directadmin.Site) -> UpdateCandidate | None:
    try:
        updates = wp_cli.core_check_updates(site.path, run_as=site.user)
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Failed to check WordPress core updates on %s: %s", site.domain, exc)
        return None
    if not updates:
        return None
    available = updates[0].get("version") or updates[0].get("update_version")
    installed = None
    try:
        installed = wp_cli.core_version(site.path, run_as=site.user)
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("Could not determine installed WordPress version on %s: %s", site.domain, exc)
    return UpdateCandidate(
        kind="core",
        slug="wordpress",
        installed_version=installed,
        available_version=available,
    )


def _log_findings(domain: str, findings: Sequence[UpdateFinding]) -> None:
    kinds = ("plugin", "theme", "core")
    for kind in kinds:
        items = [finding for finding in findings if finding.kind == kind]
        if not items:
            continue
        logger.info("%s update(s) reported on %s:", kind.capitalize(), domain)
        for finding in items:
            marker, status_text = _zip_status_marker(finding)
            details: List[str] = []
            details.append(status_text)
            if finding.installed_version:
                details.append(f"installed={finding.installed_version}")
            if finding.available_version:
                details.append(f"available={finding.available_version}")
            if finding.zip_name:
                details.append(f"zip={finding.zip_name}")
            elif finding.zip_version:
                details.append(f"zip_version={finding.zip_version}")
            if finding.zip_missing and "zip missing" not in details:
                details.append("zip missing")
            payload = ", ".join(details) if details else ""
            if payload:
                logger.info(" - %s %s (%s)", marker, finding.slug, payload)
            else:
                logger.info(" - %s %s", marker, finding.slug)


def _zip_status_marker(finding: UpdateFinding) -> Tuple[str, str]:
    if finding.zip_missing:
        return "[!!]", "zip missing"
    if not finding.zip_name:
        return "[!!]", "zip missing"
    if not finding.zip_version:
        return "[??]", "zip version unknown"
    if finding.available_version:
        available = _normalize_version(finding.available_version)
        zipped = _normalize_version(finding.zip_version)
        if available and zipped and available != zipped:
            return "[!!]", f"zip outdated (have {finding.zip_version})"
    return "[OK]", "zip ready"


def _normalize_version(version: str | None) -> str | None:
    if not version:
        return None
    return version.strip().lower().lstrip("v")
