from pathlib import Path

from agrad_wp_toolkit.operations import remove_htaccess


def test_has_malicious_rules_detects_markers() -> None:
    contents = '<FilesMatch ".(py|exe|php)$">Deny from all</FilesMatch> wp-l0gin.php'
    assert remove_htaccess._has_malicious_rules(contents)  # type: ignore[attr-defined]


def test_select_safe_rules_single_site(tmp_path: Path) -> None:
    rules = remove_htaccess._select_safe_rules(tmp_path)  # type: ignore[attr-defined]
    assert "# BEGIN WordPress" in rules
    assert "Multisite" not in rules


def test_select_safe_rules_multisite_subdomain(tmp_path: Path) -> None:
    config = tmp_path / "wp-config.php"
    config.write_text(
        "define('MULTISITE', true);\ndefine('SUBDOMAIN_INSTALL', true);",
        encoding="utf-8",
    )
    rules = remove_htaccess._select_safe_rules(tmp_path)  # type: ignore[attr-defined]
    assert "Multisite" in rules
    assert "subdomain network" in rules


def test_inspect_wp_root_htaccess_rewrites_malicious(tmp_path: Path) -> None:
    site = tmp_path
    (site / "wp-config.php").write_text("<?php // single site ?>", encoding="utf-8")
    htaccess = site / ".htaccess"
    htaccess.write_text("wp-l0gin.php\n<FilesMatch \".(py|exe|php)$\">", encoding="utf-8")

    remove_htaccess._inspect_wp_root_htaccess(htaccess)  # type: ignore[attr-defined]

    data = htaccess.read_text(encoding="utf-8")
    assert "# BEGIN WordPress" in data
    assert "wp-l0gin.php" not in data
