# Agent Notes

This file tracks expectations for future contributors. Update it whenever you change core behaviour or add new workflows.

- Always route new functionality through the Python CLI (`agrad_wp_toolkit`). Keep single-purpose shell scripts as thin wrappers around `python3 -m agrad_wp_toolkit --action …`.
- Whenever you modify behaviour that affects operators (new prompt, new action, new config), update both this file and `README.md` in the same commit.
- Keep `catalog.json` authoritative; extend its schema if you need extra metadata for each plugin/theme/core entry.
  - `config/free_plugins.json` controls WordPress.org downloads.
  - `config/accessible_hosts.json` feeds `WP_ACCESSIBLE_HOSTS`.
  - `config/zip_links.txt` is the source of premium ZIP URLs for the custom downloader.
  - `allowed_ips.json` stores firewall allowlists; auto-create with defaults if missing.
- Logging must continue to write to `logs/agrad_wp.log` plus stdout unless `--quiet` is set.
- Tests (`pytest`) must pass before delivering changes. Add coverage for new modules/helpers.
- When touching cron logic, consider both enabling and disabling flows (`ensure_cron_job` and `remove_cron_job`).
- The `audit-zips` action should always prompt for a specific WordPress site, run `wp plugin/theme/core` update checks as that site's user, and compare the reported updates with the ZIP catalog so operators know which archives are stale or missing.
- The `install-plugin` action installs/activates plugins or installs themes; it must support selecting all catalog entries or a subset (and fall back to manual slugs) so operators can batch-deploy assets before enabling them on test sites.
- The `.htaccess` cleanup skips WordPress roots but must inspect root `.htaccess` files for known malicious markers; if found, it rewrites them to stock WordPress rules, picking multisite subdomain/subfolder variants when `wp-config.php` declares them.
- Interactive menu is grouped: plugins/themes submenu holds update/remove/download inventory/install/audit actions; security submenu manages IP allowlist plus firewall apply/restore.
- Security submenu must backup iptables before applying rules that restrict SSH 2244, DirectAdmin 8956, MySQL 3306 (plus localhost), FTP 21 (plus localhost), and LiteSpeed admin 7080 to allowed IPs; provide add/remove/list/restore helpers.
- wp-config manager should allow toggling WP_DEBUG while enforcing WP_DEBUG_LOG=true and WP_DEBUG_DISPLAY=false across sites.

- ZIP staging under `/tmp/agrad-wp-toolkit/<user>` is required so staged archives are readable by the DirectAdmin user that runs wp-cli. WordPress core reinstalls should either use the staged ZIP (to avoid re-downloading) or fall back to `wp core download --skip-content --force`. Always leave `wp-content`, `.htaccess`, and `wp-config.php` untouched during core reinstalls.
