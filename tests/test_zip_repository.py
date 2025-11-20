import zipfile
from pathlib import Path

from agrad_wp_toolkit import paths
from agrad_wp_toolkit.zip_repository import ZipRepository


def test_zip_repository_reads_artifacts(tmp_path: Path, monkeypatch) -> None:
    zip_dir = tmp_path / "zips"
    zip_dir.mkdir()
    archive_path = zip_dir / "plugin_v1.2.3.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("plugin/readme.txt", "data")
    monkeypatch.setattr(paths, "ZIPS_DIR", zip_dir)
    repo = ZipRepository()
    artifact = repo.get("plugin")
    assert artifact is not None
    assert artifact.version == "1.2.3"


def test_zip_repository_handles_slug_without_version(tmp_path: Path, monkeypatch) -> None:
    zip_dir = tmp_path / "zips"
    zip_dir.mkdir()
    archive_path = zip_dir / "agrad-toolkit-plugin.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("agrad-toolkit-plugin/readme.txt", "data")
    monkeypatch.setattr(paths, "ZIPS_DIR", zip_dir)
    repo = ZipRepository()
    artifact = repo.get("agrad-toolkit-plugin")
    assert artifact is not None
    assert artifact.version is None
