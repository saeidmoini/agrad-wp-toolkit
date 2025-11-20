from pathlib import Path

from agrad_wp_toolkit.operations import download_links
from agrad_wp_toolkit import paths


def test_version_key_orders_versions():
    assert download_links._version_key("1.2.3") > download_links._version_key("1.2.0")
    assert download_links._version_key("2") > download_links._version_key("1.9.9")


def test_prune_old_zip_versions(tmp_path, monkeypatch):
    zips_dir = tmp_path / "zips"
    zips_dir.mkdir()
    old_zip = zips_dir / "plugin_v1.0.0.zip"
    new_zip = zips_dir / "plugin_v1.2.0.zip"
    old_zip.write_bytes(b"old")
    new_zip.write_bytes(b"new")
    monkeypatch.setattr(download_links.paths, "ZIPS_DIR", zips_dir)
    download_links.prune_old_zip_versions()
    assert not old_zip.exists()
    assert new_zip.exists()
