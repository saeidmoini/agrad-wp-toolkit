# Agrad WP Toolkit

Interactive CLI that automates the recurring WordPress maintenance work across DirectAdmin servers.  
It consolidates the previous shell scripts (download, rename, update, clean, migrate, …) into a single Python entry point that asks the required questions at runtime so you do not need to edit JSON files before every run.

## Features
- Menu driven CLI or single-action mode (`--action …`).
- Update plugins, themes, or WordPress core across all users or a single DirectAdmin user.
- Force reinstall regardless of current version, while respecting per-item force flags defined in `catalog.json`.
- Automatically downloads free plugins from WordPress.org and custom premium ZIPs from `config/zip_links.txt`, keeping only the latest versions.
- Automatically normalises ZIP filenames during updates/installs and maintains `zips/zip_folders.json`.
- Remove a specific plugin everywhere (plugin is deactivated first), clean malicious `.htaccess` files (and auto-rewrite compromised root rules to stock WordPress variants), migrate domains, manage wp-config flags (cron, HTTP block, auto updates, file mods).
- Install and/or activate plugins (single, multi-select, or entire catalog) or install catalog themes across all sites, ensuring plugins are enabled after install.
- Ensure cron jobs exist whenever `DISABLE_WP_CRON` is enabled (detects PHP version from `/home/<user>/.php-version`).
- Collects a cross-site plugin inventory in JSON format (records the first site where each plugin is found).
- Audit a single WordPress site to see which plugins/themes/core builds report updates and match them against the ZIP catalog.
- Structured logging to `logs/agrad_wp.log` plus console output.
- Test suite (`pytest`) covering the config loader, wp-config editor, DirectAdmin discovery, and ZIP repository logic.

## Requirements
- Python 3.10+
- `wp` CLI available in `$PATH`
- DirectAdmin style layout (`/home/<user>/domains/<domain>/public_html`)

## Usage
Run the main script:

```bash
./wordpress_update.sh
```

You will see a menu with all supported tasks. Every task asks the required follow-up questions (scope, force update, etc.) and uses the existing JSON catalog automatically.  
To skip the menu and launch a single action:

```bash
python3 -m agrad_wp_toolkit --action update
python3 -m agrad_wp_toolkit --action download-free
python3 -m agrad_wp_toolkit --action inventory
python3 -m agrad_wp_toolkit --action install-plugin
```

### Available actions
`update`, `remove-plugin`, `clean-htaccess`, `migrate-domain`, `wp-config`, `download-free`, `download-links`, `inventory`, `install-plugin` (plugins/themes), `audit-zips`

### Configuration files
- `catalog.json`: master catalog of all plugins/themes/core entries; edit this file to add/remove items or tweak force flags.
- `config/free_plugins.json`: slugs that can be auto-downloaded or updated from WordPress.org.
- `config/accessible_hosts.json`: allow list injected into `WP_ACCESSIBLE_HOSTS`.
- `config/zip_links.txt`: list of premium ZIP URLs consumed by the “Download custom ZIPs” action.

### ZIP management
- Store custom update ZIPs inside the `zips/` folder named like `<slug>_v<version>.zip` (WordPress core ZIPs follow the same naming so version comparisons work).
- Update and install actions automatically normalize ZIP names (and prune duplicates) before running; ZIPs are staged into `/tmp/agrad-wp-toolkit/<user>` so wp-cli runs as the target DirectAdmin user and files retain the proper ownership.
- Free plugins are downloaded with the “Download free plugins” action (or `download_files.sh` wrapper).
- Premium ZIPs are pulled via the “Download custom ZIPs from link list” action, which reads `config/zip_links.txt`, saves them under `zips/`, normalizes names, and removes older versions automatically.

## Tests

Create a virtual environment once (kept out of git via `.gitignore`):

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

Tests run without touching real `/home` paths by using temporary directories and monkeypatching. Add more tests whenever you extend the CLI or touch the config manipulation code.
