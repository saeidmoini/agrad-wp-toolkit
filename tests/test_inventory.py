import json
from pathlib import Path

from agrad_wp_toolkit import config_loader, directadmin, paths, wp_cli
from agrad_wp_toolkit.operations import inventory


def test_inventory_skips_catalog_plugins(tmp_path, monkeypatch) -> None:
    output_path = tmp_path / "inventory_plugins.json"
    monkeypatch.setattr(paths, "PLUGIN_INVENTORY_PATH", output_path)

    catalog = config_loader.Catalog(
        [
            config_loader.UpdateItem(name="known-plugin", type="plugins"),
            config_loader.UpdateItem(name="catalog-theme", type="themes"),
        ]
    )

    def fake_load(cls):  # pylint: disable=unused-argument
        return catalog

    monkeypatch.setattr(config_loader.Catalog, "load", classmethod(fake_load))

    site = directadmin.Site(
        user="demo",
        path=Path("/home/demo/domains/example.com/public_html"),
    )
    monkeypatch.setattr(directadmin, "resolve_sites", lambda target_user=None: [site])
    monkeypatch.setattr(wp_cli, "ensure_wp_cli", lambda: True)
    monkeypatch.setattr(
        wp_cli,
        "list_plugins",
        lambda path, run_as=None: [  # pylint: disable=unused-argument
            {"name": "known-plugin"},
            {"name": "new-plugin"},
            {"name": "Another"},
        ],
    )

    inventory.run_inventory()

    assert output_path.exists()
    data = json.loads(output_path.read_text(encoding="utf-8"))
    names = [entry["name"] for entry in data["plugins"]]
    assert "known-plugin" not in names
    assert names == ["Another", "new-plugin"]
    assert all(entry["first_site"] == "example.com" for entry in data["plugins"])
