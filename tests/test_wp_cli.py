from pathlib import Path

from agrad_wp_toolkit import wp_cli


class DummyResult:
    def __init__(self, returncode: int):
        self.returncode = returncode


def test_theme_is_installed_true(monkeypatch, tmp_path: Path) -> None:
    recorded = {}

    def fake_run(args, site_path, run_as=None):
        recorded["args"] = args
        recorded["path"] = site_path
        recorded["user"] = run_as
        return DummyResult(0)

    monkeypatch.setattr(wp_cli, "_run_wp", fake_run)
    assert wp_cli.theme_is_installed(tmp_path, "hello-elementor", run_as="agrad")
    assert recorded["args"] == ["theme", "is-installed", "hello-elementor"]
    assert recorded["path"] == tmp_path
    assert recorded["user"] == "agrad"


def test_theme_is_installed_false(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(wp_cli, "_run_wp", lambda *_, **__: DummyResult(1))
    assert wp_cli.theme_is_installed(tmp_path, "missing") is False
