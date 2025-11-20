from pathlib import Path

from agrad_wp_toolkit.operations import update_audit
from agrad_wp_toolkit.zip_repository import ZipArtifact


class DummyRepo:
    def __init__(self, artifacts: dict[str, ZipArtifact]):
        self._artifacts = artifacts

    def get(self, slug: str):
        return self._artifacts.get(slug)


def test_build_findings_enriches_with_zip_metadata() -> None:
    repo = DummyRepo(
        {
            "elementor": ZipArtifact(
                slug="elementor",
                version="3.0.0",
                path=Path("/tmp/elementor_v3.0.0.zip"),
            )
        }
    )
    candidates = [
        update_audit.UpdateCandidate(
            kind="plugin",
            slug="elementor",
            installed_version="2.9.0",
            available_version="3.0.0",
        ),
        update_audit.UpdateCandidate(
            kind="theme",
            slug="hello-elementor",
            installed_version="2.5.0",
            available_version=None,
        ),
    ]
    findings = update_audit.build_findings(candidates, repo)  # type: ignore[arg-type]
    assert len(findings) == 2
    elementor = findings[0]
    assert elementor.zip_name == "elementor_v3.0.0.zip"
    assert elementor.zip_version == "3.0.0"
    assert elementor.zip_missing is False
    theme = findings[1]
    assert theme.zip_name is None
    assert theme.zip_missing is True


def test_build_findings_preserves_available_version() -> None:
    repo = DummyRepo({})
    candidates = [
        update_audit.UpdateCandidate(
            kind="core",
            slug="wordpress",
            installed_version="6.4.3",
            available_version="6.5",
        )
    ]
    findings = update_audit.build_findings(candidates, repo)  # type: ignore[arg-type]
    assert findings[0].available_version == "6.5"
    assert findings[0].zip_missing is True


def test_zip_status_marker_flags_missing_zip() -> None:
    finding = update_audit.UpdateFinding(
        kind="plugin",
        slug="sonicctc",
        installed_version="3.3.2",
        available_version="4.0.0.2",
        zip_missing=True,
    )
    marker, status = update_audit._zip_status_marker(finding)
    assert marker == "[!!]"
    assert status == "zip missing"


def test_zip_status_marker_marks_outdated_zip_version() -> None:
    finding = update_audit.UpdateFinding(
        kind="plugin",
        slug="elementor-pro",
        installed_version="3.32.2",
        available_version="3.33.1",
        zip_version="3.32.2",
        zip_name="elementor-pro_v3.32.2.zip",
        zip_missing=False,
    )
    marker, status = update_audit._zip_status_marker(finding)
    assert marker == "[!!]"
    assert "zip outdated" in status


def test_zip_status_marker_marks_zip_ready() -> None:
    finding = update_audit.UpdateFinding(
        kind="plugin",
        slug="query-monitor",
        installed_version="3.19.0",
        available_version="3.20.0",
        zip_version="3.20.0",
        zip_name="query-monitor_v3.20.0.zip",
        zip_missing=False,
    )
    marker, status = update_audit._zip_status_marker(finding)
    assert marker == "[OK]"
    assert status == "zip ready"
