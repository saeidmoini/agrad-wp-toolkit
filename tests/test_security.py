import json
from pathlib import Path

from agrad_wp_toolkit import paths
from agrad_wp_toolkit.operations import security


class DummyResult:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_load_allowed_ips_creates_default(tmp_path, monkeypatch) -> None:
    target = tmp_path / "allowed_ips.json"
    monkeypatch.setattr(paths, "ALLOWED_IPS_PATH", target)
    ips = security.load_allowed_ips()
    assert "127.0.0.1" in ips
    assert target.exists()
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data


def test_apply_rules_builds_commands(tmp_path, monkeypatch) -> None:
    target = tmp_path / "allowed_ips.json"
    monkeypatch.setattr(paths, "ALLOWED_IPS_PATH", target)
    security.save_allowed_ips(["10.0.0.1"])
    monkeypatch.setattr(paths, "ROOT_DIR", tmp_path)

    calls = []

    def fake_run(cmd, capture_output=True, text=True, check=False, input=None):  # type: ignore[override]
        calls.append(cmd)
        return DummyResult(0, stdout="")

    monkeypatch.setattr(security, "_run", lambda cmd: (calls.append(cmd) or (0, "", "")))  # type: ignore
    monkeypatch.setattr(security.subprocess, "run", fake_run)  # type: ignore

    security.apply_rules()

    # Ensure drop rules were added for SSH and a jump in INPUT exists
    flat_calls = [" ".join(cmd) if isinstance(cmd, list) else " ".join(cmd) for cmd in calls]
    assert any("--dport 2244" in cmd and "-j DROP" in cmd for cmd in flat_calls)
    assert any("INPUT" in cmd and "AGRAD_ACCESS" in cmd for cmd in flat_calls)
