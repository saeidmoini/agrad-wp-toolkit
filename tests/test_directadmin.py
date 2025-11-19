from pathlib import Path

from agrad_wp_toolkit import directadmin


def _create_wp_site(base: Path) -> None:
    (base / "wp-config.php").write_text("<?php")
    (base / "wp-content").mkdir()


def test_discover_wp_roots(tmp_path: Path) -> None:
    user_root = tmp_path / "user"
    public_html = user_root / "domains" / "example.com" / "public_html"
    public_html.mkdir(parents=True)
    _create_wp_site(public_html)
    subfolder = public_html / "en"
    subfolder.mkdir()
    _create_wp_site(subfolder)
    results = directadmin.discover_wp_roots(user_root)
    assert len(results) == 2
