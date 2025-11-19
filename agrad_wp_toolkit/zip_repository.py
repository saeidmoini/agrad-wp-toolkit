"""Utility class that understands files available under the zips/ directory."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from . import paths

logger = logging.getLogger(__name__)

ZIP_PATTERN = re.compile(r"(?P<slug>[a-zA-Z0-9\-_\.]+)_v(?P<version>[0-9][0-9a-zA-Z\.\-_]*)\.zip")


@dataclass
class ZipArtifact:
    slug: str
    version: str
    path: Path


class ZipRepository:
    def __init__(self) -> None:
        self.artifacts = self._scan()

    def _scan(self) -> Dict[str, ZipArtifact]:
        artifacts: Dict[str, ZipArtifact] = {}
        if not paths.ZIPS_DIR.exists():
            return artifacts
        for entry in paths.ZIPS_DIR.glob("*.zip"):
            match = ZIP_PATTERN.match(entry.name)
            if not match:
                logger.debug("Skipping %s (unable to parse slug/version)", entry.name)
                continue
            slug = match.group("slug")
            version = match.group("version")
            artifacts[slug] = ZipArtifact(slug=slug, version=version, path=entry)
        return artifacts

    def get(self, slug: str) -> Optional[ZipArtifact]:
        slug_key = slug.lower()
        for key, artifact in self.artifacts.items():
            if key.lower() == slug_key:
                return artifact
        return None

    def list_slugs(self) -> List[str]:
        return list(self.artifacts.keys())
