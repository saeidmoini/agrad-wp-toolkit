#!/usr/bin/env bash
set -euo pipefail

python3 -m agrad_wp_toolkit --action normalize-zips "$@"
