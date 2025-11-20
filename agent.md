# Agent Notes

This file tracks expectations for future contributors. Update it whenever you change core behaviour or add new workflows.

- Always route new functionality through the Python CLI (`agrad_wp_toolkit`). Keep single-purpose shell scripts as thin wrappers around `python3 -m agrad_wp_toolkit --action …`.
- Whenever you modify behaviour that affects operators (new prompt, new action, new config), update both this file and `README.md` in the same commit.
- Keep `catalog.json` authoritative; extend its schema if you need extra metadata for each plugin/theme/core entry.
  - `config/free_plugins.json` controls WordPress.org downloads.
  - `config/accessible_hosts.json` feeds `WP_ACCESSIBLE_HOSTS`.
  - `config/zip_links.txt` is the source of premium ZIP URLs for the custom downloader.
- Logging must continue to write to `logs/agrad_wp.log` plus stdout unless `--quiet` is set.
- Tests (`pytest`) must pass before delivering changes. Add coverage for new modules/helpers.
- When touching cron logic, consider both enabling and disabling flows (`ensure_cron_job` and `remove_cron_job`).
- The `audit-zips` action should always prompt for a specific WordPress site, run `wp plugin/theme/core` update checks as that site's user, and compare the reported updates with the ZIP catalog so operators know which archives are stale or missing.

- ZIP staging under `/tmp/agrad-wp-toolkit/<user>` is required so staged archives are readable by the DirectAdmin user that runs wp-cli. WordPress core reinstalls should either use the staged ZIP (to avoid re-downloading) or fall back to `wp core download --skip-content --force`. Always leave `wp-content`, `.htaccess`, and `wp-config.php` untouched during core reinstalls.
