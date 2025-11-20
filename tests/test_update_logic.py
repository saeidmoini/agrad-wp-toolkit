from pathlib import Path

from agrad_wp_toolkit import config_loader
from agrad_wp_toolkit.operations import update


class DummyRepo:
    def __init__(self, artifact=None):
        self._artifact = artifact

    def get(self, _name):
        return self._artifact


def test_update_item_falls_back_to_repo_when_zip_missing(monkeypatch, tmp_path: Path) -> None:
    item = config_loader.UpdateItem(name="contact-form-7", type="plugins", force=False, source="zip")
    called = {}

    def fake_update_from_repo(site_path, slug, kind, force=False):  # noqa: D401
        called["slug"] = slug

    monkeypatch.setattr(update.wp_cli, "update_from_repo", fake_update_from_repo)

    update._update_item(tmp_path, item, DummyRepo(), {"contact-form-7"})

    assert called["slug"] == "contact-form-7"


def test_update_item_errors_when_zip_missing_for_nonfree(monkeypatch, tmp_path: Path) -> None:
    item = config_loader.UpdateItem(name="premium-plugin", type="plugins", force=False, source="zip")

    def fake_update_from_repo(*_args, **_kwargs):
        raise AssertionError("should not reach repo")

    monkeypatch.setattr(update.wp_cli, "update_from_repo", fake_update_from_repo)

    try:
        update._update_item(tmp_path, item, DummyRepo(), set())
    except RuntimeError as exc:
        assert "premium-plugin" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError when ZIP is missing")


def test_update_item_uses_repo_for_wordpress(monkeypatch, tmp_path: Path) -> None:
    item = config_loader.UpdateItem(name="wordpress", type="wordpress", force=False, source="zip")
    called = {}

    def fake_update_from_repo(site_path, slug, kind, force=False):
        called["kind"] = kind

    monkeypatch.setattr(update.wp_cli, "update_from_repo", fake_update_from_repo)

    update._update_item(tmp_path, item, DummyRepo(), set())

    assert called["kind"] == "core"
