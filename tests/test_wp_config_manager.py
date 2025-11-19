import shutil
from pathlib import Path

from agrad_wp_toolkit.operations import wp_config
from agrad_wp_toolkit.operations.wp_config import WPConfigManager, detect_php_binary


def test_set_and_remove_constant(tmp_path: Path) -> None:
    fixture = Path("tests/fixtures/wp-config.php")
    target = tmp_path / "wp-config.php"
    shutil.copy(fixture, target)
    manager = WPConfigManager(target)
    manager.set_constant("DISABLE_WP_CRON", "true")
    content = target.read_text()
    assert "define('DISABLE_WP_CRON', true);" in content
    manager.remove_constant("DISABLE_WP_CRON")
    content = target.read_text()
    assert "DISABLE_WP_CRON" not in content


def test_detect_php_binary_reads_user_file(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    user_dir = home / "demo"
    user_dir.mkdir(parents=True)
    (user_dir / ".php-version").write_text("8.2")

    def _mock_path(path_str: str = ".") -> Path:
        if path_str == "/home":
            return home
        return Path(path_str)

    monkeypatch.setattr(wp_config, "Path", _mock_path)
    result = detect_php_binary("demo")
    assert result == "/usr/local/lsws/fcgi-bin/lsphp-8.2"
