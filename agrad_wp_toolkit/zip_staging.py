"""Stage ZIPs in a user-readable area before installation."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

STAGING_ROOT = Path("/tmp/agrad-wp-toolkit")


def stage_for_user(zip_path: Path, user: str) -> Path:
    dest_dir = STAGING_ROOT / user
    dest_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(dest_dir, 0o755)
    dest = dest_dir / zip_path.name
    shutil.copy2(zip_path, dest)
    os.chmod(dest, 0o644)
    return dest


def cleanup_staged(staged_path: Path) -> None:
    try:
        staged_path.unlink()
    except FileNotFoundError:
        pass
