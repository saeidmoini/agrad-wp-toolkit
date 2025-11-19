"""Helpers for loading/saving JSON configuration files."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from . import paths


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=4, ensure_ascii=False)


@dataclass
class UpdateItem:
    name: str
    type: str
    force: bool = False
    source: str = "zip"  # zip | wp.org

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UpdateItem":
        return cls(
            name=data["name"],
            type=data.get("type", "plugins"),
            force=bool(data.get("force", False)),
            source=data.get("source", data.get("src", "zip")),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "force": self.force,
            "source": self.source,
        }


class Catalog:
    """Represents the master list of updateable items (plugins, themes, etc)."""

    def __init__(self, items: List[UpdateItem]):
        self.items = items

    @classmethod
    def load(cls) -> "Catalog":
        data = read_json(paths.CATALOG_PATH, {"updates": []})
        items = [UpdateItem.from_dict(entry) for entry in data.get("updates", [])]
        return cls(items)

    def get_names(self) -> List[str]:
        return [item.name for item in self.items]

    def find(self, name: str) -> UpdateItem | None:
        lowered = name.lower()
        for item in self.items:
            if item.name.lower() == lowered:
                return item
        return None

    def to_update_payload(self, names: List[str], force_all: bool) -> List[UpdateItem]:
        payload: List[UpdateItem] = []
        for name in names:
            item = self.find(name)
            if not item:
                item = UpdateItem(name=name, type="plugins", force=force_all)
            payload.append(
                UpdateItem(
                    name=item.name,
                    type=item.type,
                    force=force_all or item.force,
                    source=item.source,
                )
            )
        return payload


def load_free_plugin_slugs() -> List[str]:
    data = read_json(paths.FREE_PLUGINS_PATH, {"plugins": []})
    return data.get("plugins", [])


def load_accessible_hosts() -> Dict[str, Any]:
    data = read_json(
        paths.WP_ACCESSIBLE_HOSTS_PATH,
        {
            "hosts": [
                "*.google.com",
                "*.gstatic.com",
                "*.torob.com",
                "torob.com",
                "*.payamak-panel.com",
                "*.melipayamak.com",
                "*.wordpress.org",
                "arvancloud.ir",
                "*.arvancloud.ir",
            ]
        },
    )
    return data


def save_accessible_hosts(hosts: List[str]) -> None:
    write_json(paths.WP_ACCESSIBLE_HOSTS_PATH, {"hosts": hosts})
