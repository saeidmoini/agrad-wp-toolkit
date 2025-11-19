"""Central logging configuration."""
from __future__ import annotations

import logging

from . import paths


def setup_logging(verbose: bool = True) -> None:
    paths.ensure_dirs()
    log_path = paths.LOG_DIR / "agrad_wp.log"
    handlers = [
        logging.FileHandler(log_path, encoding="utf-8"),
    ]
    if verbose:
        handlers.append(logging.StreamHandler())
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
        force=True,
    )
