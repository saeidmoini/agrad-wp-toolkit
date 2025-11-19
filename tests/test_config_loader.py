from pathlib import Path

from agrad_wp_toolkit import config_loader, paths


def test_catalog_selection_respects_force(monkeypatch, tmp_path: Path) -> None:
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(
        """
        {
            "updates": [
                {"type": "plugins", "name": "alpha", "force": false, "source": "zip"},
                {"type": "themes", "name": "beta", "force": true, "source": "wp.org"}
            ]
        }
        """,
        encoding="utf-8",
    )
    monkeypatch.setattr(paths, "CATALOG_PATH", catalog_path)
    catalog = config_loader.Catalog.load()
    payload = catalog.to_update_payload(["alpha", "beta"], force_all=False)
    assert payload[0].force is False
    assert payload[1].force is True
    payload_force = catalog.to_update_payload(["alpha"], force_all=True)
    assert payload_force[0].force is True
