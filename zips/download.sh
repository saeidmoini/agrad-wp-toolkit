#!/usr/bin/env bash
set -euo pipefail

# CONFIG (EDIT IF NEEDED)
URL_FILE="${1:-links.txt}"   # default: plugins.txt or pass as first arg
DEST_DIR="${2:-.}"        # default: ./zips or pass as second arg
RETRIES=3
RETRY_DELAY=5   # seconds

# helper
log() { printf '%s\n' "$*"; }

# checks
if [ ! -f "$URL_FILE" ]; then
  log "❌ URL file not found: $URL_FILE"
  exit 2
fi

mkdir -p "$DEST_DIR"

# read file line-by-line, ignore empty lines and lines starting with #
while IFS= read -r url || [ -n "$url" ]; do
  # trim whitespace
  url="${url#"${url%%[![:space:]]*}"}"
  url="${url%"${url##*[![:space:]]}"}"
  [ -z "$url" ] && continue
  case "$url" in \#*) continue ;; esac

  # determine filename from URL
  filename="$(basename "${url%%\?*}")"
  if [ -z "$filename" ] || [ "$filename" = "/" ]; then
    log "⚠️  Could not determine filename from URL: $url"
    continue
  fi

  dest_path="$DEST_DIR/$filename"

  log "⬇️  Downloading: $url"
  # try curl with redirects and retries, overwrite existing file
  attempt=1
  success=0
  while [ $attempt -le $RETRIES ]; do
    if curl -L --fail --silent --show-error --max-time 120 --retry 0 -o "$dest_path" "$url"; then
      log "✅ Saved: $dest_path"
      success=1
      break
    else
      log "⚠️  Attempt $attempt failed for $url"
      attempt=$((attempt+1))
      sleep $RETRY_DELAY
    fi
  done

  if [ $success -ne 1 ]; then
    log "❌ Failed to download after $RETRIES attempts: $url"
  fi

done < "$URL_FILE"

log "🎉 All done. Files saved to: $DEST_DIR"

