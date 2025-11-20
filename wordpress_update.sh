#!/usr/bin/env bash

set -euo pipefail

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required to run the toolkit."
  exit 1
fi

python3 -m agrad_wp_toolkit "$@"
