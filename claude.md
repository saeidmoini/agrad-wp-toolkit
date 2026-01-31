# Claude's Project Reference - Agrad WP Toolkit

## Project Overview

**Agrad WP Toolkit** is an interactive Python CLI that automates WordPress maintenance tasks across DirectAdmin servers. It consolidates multiple shell scripts into a single menu-driven interface for managing WordPress installations at scale.

**Key Purpose**: Server administrator's assistant for managing multiple WordPress sites across DirectAdmin hosting environments.

## Architecture

### Technology Stack
- **Language**: Python 3.10+
- **CLI Framework**: Custom interactive menu using prompts module
- **WordPress Interface**: wp-cli (WordPress command-line tool)
- **Server Layout**: DirectAdmin structure (`/home/<user>/domains/<domain>/public_html`)
- **Testing**: pytest with monkeypatching for safe testing

### Project Structure

```
agrad-wp-toolkit/
├── agrad_wp_toolkit/          # Main Python package
│   ├── __main__.py            # Entry point (delegates to cli.py)
│   ├── cli.py                 # Interactive menu and action router
│   ├── config_loader.py       # JSON config handlers (Catalog, UpdateItem)
│   ├── directadmin.py         # DirectAdmin user/site discovery
│   ├── wp_cli.py              # wp-cli wrapper functions
│   ├── zip_repository.py      # ZIP file version management
│   ├── zip_staging.py         # Temporary ZIP staging for wp-cli
│   ├── prompts.py             # Interactive user input helpers
│   ├── logging_utils.py       # Logging setup
│   ├── paths.py               # Path constants and directory setup
│   └── operations/            # Feature modules
│       ├── update.py          # Update plugins/themes/core
│       ├── remove_plugin.py   # Remove plugins everywhere
│       ├── remove_htaccess.py # Clean malicious .htaccess files
│       ├── domain_migrate.py  # Domain migration
│       ├── wp_config.py       # wp-config.php editor
│       ├── free_downloads.py  # Download from WordPress.org
│       ├── download_links.py  # Download premium ZIPs from URLs
│       ├── inventory.py       # Cross-site plugin inventory
│       ├── install_activate_plugin.py  # Install/activate plugins
│       ├── update_audit.py    # Audit ZIP freshness vs site updates
│       ├── security.py        # Firewall & IP allowlist management
│       └── zips.py            # ZIP normalization
├── config/                    # Configuration files
│   ├── free_plugins.json      # WordPress.org plugin slugs
│   ├── accessible_hosts.json  # WP_ACCESSIBLE_HOSTS values
│   └── zip_links.txt          # Premium ZIP download URLs
├── zips/                      # ZIP archive storage
│   └── zip_folders.json       # Metadata for ZIPs
├── logs/                      # Log files
│   └── agrad_wp.log          # Application log
├── tests/                     # pytest test suite
├── catalog.json              # Master catalog of updateable items
├── allowed_ips.json          # Firewall IP allowlist
├── *.sh                      # Thin shell wrappers for actions
├── README.md                 # User documentation
└── agent.md                  # Developer guidelines
```

## Core Concepts

### 1. Catalog System
- **catalog.json**: Master list of all plugins/themes/WordPress core that should be managed
- Each item has: `name`, `type` (plugins/themes/wordpress), `force` flag, `source` (zip/wp.org)
- The `Catalog` class loads this and provides helper methods
- Force flag means "always reinstall even if same version"

### 2. DirectAdmin Site Discovery
- Scans `/home/*/domains/*/public_html` for WordPress installations
- Identifies WP roots by presence of `wp-config.php` and `wp-content/`
- Returns `Site` objects with `user`, `path`, and `domain` properties
- Can target all users or a specific DirectAdmin user

### 3. ZIP Management
- Custom/premium plugins stored in `zips/` folder
- Naming convention: `<slug>_v<version>.zip`
- Auto-normalizes filenames during operations
- Keeps only latest versions (prunes old ones)
- `zip_folders.json` maintains metadata
- Free plugins downloaded from WordPress.org API

### 4. ZIP Staging
- ZIPs staged to `/tmp/agrad-wp-toolkit/<user>/` before wp-cli operations
- Ensures proper file ownership (readable by DirectAdmin user running wp-cli)
- Staging directory cleaned up after operations

### 5. wp-cli Integration
- All WordPress operations run through wp-cli
- Commands run as DirectAdmin user: `sudo -u <user> wp --path=<site> ...`
- Supports: install, update, activate, list, version checks
- Always includes `--allow-root` flag

### 6. Security Features
- **IP Allowlist**: Stored in `allowed_ips.json`
- **Firewall Rules**: iptables management for:
  - SSH (port 2244)
  - DirectAdmin (port 8956)
  - MySQL (port 3306) + localhost exception
  - FTP (port 21) + localhost exception
  - LiteSpeed Admin (port 7080)
- **IPv6 Protection**: Drops IPv6 packets on protected ports
- Automatic backup before applying rules
- Can restore last backup

## Key Operations

### Update Flow
1. Load catalog.json
2. Ask scope (all users vs single user)
3. Select items to update (all or multi-select)
4. Ask force reinstall preference
5. Normalize ZIPs and prune old versions
6. Discover all WordPress sites
7. For each site:
   - Check what's installed
   - Update from ZIP (local) or wp.org based on source
   - Respect per-item force flags

### Install/Activate Flow
1. Choose: plugins or themes
2. Multi-select from catalog or enter manual slugs
3. For each site:
   - Install from ZIP if available, else from wp.org
   - Activate plugins (themes just installed)

### Remove Plugin Flow
1. Enter plugin slug
2. Confirm action
3. For each site:
   - Deactivate plugin first
   - Delete plugin

### .htaccess Cleanup Flow
1. Scan all `/home/*/domains/*/public_html/**/.htaccess`
2. Delete non-root .htaccess files
3. Inspect root .htaccess for malicious markers
4. If compromised: rewrite with stock WordPress rules
5. Detect multisite (subdomain/subfolder) from wp-config.php
6. Use appropriate WordPress .htaccess template

### Domain Migration Flow
1. Ask for site, old domain, new domain
2. Update wp-config.php constants
3. Run wp search-replace on database
4. Update .htaccess if present

### wp-config Management
- Toggle WP_DISABLE_CRON (ensure/remove cron jobs)
- Toggle HTTP requests blocking
- Manage auto-updates (core/plugins/themes)
- Toggle file modifications
- Toggle debug mode (enforces WP_DEBUG_LOG=true, WP_DEBUG_DISPLAY=false)
- Manage WP_ACCESSIBLE_HOSTS

### Inventory Collection
1. Scan all sites for installed plugins
2. Exclude catalog plugins
3. Build JSON: `{"plugin-slug": {"version": "X.Y", "site": "/path/..."}}`
4. Records first site where each plugin found

### Audit ZIP Freshness
1. Ask for specific site
2. Run `wp plugin/theme/core check-update`
3. Compare reported updates with ZIP catalog
4. Show which ZIPs are outdated or missing

### Firewall Disable Flow (Safety Feature)
1. Ask for confirmation
2. Remove jump rules from INPUT chain (traffic bypasses custom chains)
3. Flush AGRAD_ACCESS and AGRAD_ACCESS6 chains (remove all rules)
4. Delete custom chains completely
5. Restores unrestricted access to all services

**Critical Safety Feature**: Prevents permanent lockout if firewall rules are applied without current IP in allowed list.

### Download Operations
- **Free Plugins**: Query WordPress.org API, download latest
- **Premium ZIPs**: Read URLs from `config/zip_links.txt`, download, normalize names

## Configuration Files

### catalog.json
```json
{
  "updates": [
    {
      "type": "plugins",
      "name": "elementor-pro",
      "force": false,
      "source": "zip"
    },
    {
      "type": "themes",
      "name": "hello-elementor"
    },
    {
      "type": "wordpress",
      "name": "wordpress"
    }
  ]
}
```

### config/free_plugins.json
```json
{
  "plugins": ["contact-form-7", "redis-cache", "query-monitor"]
}
```

### config/accessible_hosts.json
```json
{
  "hosts": [
    "*.google.com",
    "*.wordpress.org",
    "arvancloud.ir"
  ]
}
```

### config/zip_links.txt
```
https://example.com/elementor-pro-v3.24.0.zip
https://example.com/wp-rocket-v3.17.zip
```

### allowed_ips.json
```json
[
  "127.0.0.1",
  "2.180.12.195",
  "162.19.171.47"
]
```

## Menu Structure

### Main Menu
1. **Manage plugins/themes** → Submenu
2. **Security** → Security submenu
3. **Clean .htaccess files**
4. **Migrate domain**
5. **Manage wp-config flags**
6. **Exit**

### Plugins/Themes Submenu
1. Update plugins/themes/core
2. Remove a plugin everywhere
3. Download free plugins
4. Collect plugin inventory
5. Install/activate plugins or install themes
6. Download custom ZIPs from link list
7. Audit ZIP freshness vs site updates
8. Back

### Security Submenu
1. Show allowed IPs
2. Add allowed IP
3. Remove allowed IP
4. Apply firewall rules (with backup)
5. Disable firewall rules (removes all restrictions)
6. Restore last firewall backup
7. Back

## Command Line Usage

### Interactive Mode
```bash
./wordpress_update.sh
# OR
python3 -m agrad_wp_toolkit
```

### Single Action Mode
```bash
python3 -m agrad_wp_toolkit --action update
python3 -m agrad_wp_toolkit --action download-free
python3 -m agrad_wp_toolkit --action inventory
python3 -m agrad_wp_toolkit --action security
python3 -m agrad_wp_toolkit --quiet --action update  # Logs to file only
```

### Available Actions
- `update` - Update plugins/themes/core
- `remove-plugin` - Remove a plugin everywhere
- `clean-htaccess` - Clean malicious .htaccess
- `migrate-domain` - Migrate domain
- `wp-config` - Manage wp-config flags
- `download-free` - Download free plugins
- `download-links` - Download custom ZIPs
- `inventory` - Collect plugin inventory
- `install-plugin` - Install/activate plugins or themes
- `audit-zips` - Audit ZIP freshness
- `manage-addons` - Plugins/themes submenu
- `security` - Security submenu

## Important Patterns & Conventions

### 1. Logging
- Logs to both `logs/agrad_wp.log` and stdout
- Use `--quiet` flag to suppress stdout
- Always log user actions and errors

### 2. Error Handling
- Operations catch exceptions per-site to continue processing
- wp-cli errors raise `WPCLIError` with stderr output
- Log errors but don't stop batch operations

### 3. User Prompts
- `ask_from_list()` - Single choice from list
- `ask_multi_select()` - Multiple selections
- `ask_yes_no()` - Boolean confirmation
- All in `prompts.py`

### 4. Cron Management
- When enabling `DISABLE_WP_CRON`, ensure cron job exists
- Detect PHP version from `/home/<user>/.php-version`
- Use detected PHP binary in crontab entry
- When disabling, remove cron job

### 5. File Ownership
- wp-cli runs as DirectAdmin user (`sudo -u <user>`)
- ZIP staging ensures proper permissions
- Never run wp commands as root directly

### 6. WordPress Core Updates
- Can install from staged ZIP or use `wp core download --skip-content --force`
- Always preserve `wp-content/`, `.htaccess`, `wp-config.php`

### 7. Testing Strategy
- Use temporary directories for tests
- Monkeypatch file system operations
- Mock subprocess calls to wp-cli
- Test config loading, wp-config editing, discovery logic
- Run: `pytest` in virtualenv

### 8. Shell Script Wrappers
- `wordpress_update.sh` - Main entry point
- `download_files.sh` - Wrapper for download-free
- `remove-plugin.sh` - Wrapper for remove-plugin
- All are thin wrappers calling Python CLI

## Security Considerations

### .htaccess Malware Detection
- Scans for known malicious patterns in root .htaccess
- Markers indicate compromised files
- Auto-rewrites to stock WordPress rules
- Supports multisite variants (subdomain/subfolder)

### Firewall IPv6 Protection
- Checks if IP is IPv6 before adding to iptables
- Drops IPv6 packets on protected ports
- Prevents firewall bypass via IPv6

### Backup Strategy
- Backs up iptables before applying rules
- Timestamped backup files
- Can restore last backup
- Located in project directory

## Recent Git Commits Context

1. **Firewall IPv6 Protection** - Added guards against IPv6 addresses bypassing iptables rules
2. **LiteSpeed Admin Port Protection** - Added port 7080 to firewall rules
3. **Menu Reorganization** - Grouped menu, added security submenu, WP debug toggle
4. **Non-root .htaccess Deletion** - Deletes all .htaccess except WordPress roots
5. **Malicious .htaccess Rewrite** - Detects compromised root .htaccess and rewrites with safe WordPress rules

## Development Guidelines

### Adding New Features
1. Create operation module in `agrad_wp_toolkit/operations/`
2. Add handler function to `cli.py` ACTIONS dict
3. Update menu in `cli.py` if needed
4. Add tests in `tests/`
5. Update both `README.md` and `agent.md`
6. Keep `catalog.json` authoritative for updateable items

### Modifying Existing Operations
1. Update operation module
2. Add/update tests
3. Update documentation
4. Test with `pytest`
5. Verify logging output

### Configuration Changes
1. New config files go in `config/`
2. Add loader function in `config_loader.py`
3. Define default values
4. Auto-create if missing

### Testing Requirements
- All tests must pass before merging
- Add coverage for new modules
- Use monkeypatching for file operations
- Mock subprocess calls
- Use temp directories

## Key Dependencies

### External Tools
- `wp` CLI (WordPress command-line tool)
- `sudo` (for running commands as DirectAdmin users)
- `iptables` (for firewall management)
- DirectAdmin hosting environment

### Python Requirements
- Python 3.10+ (uses modern type hints)
- Standard library only for main package
- `pytest` for testing (dev dependency)

## Troubleshooting

### Common Issues
1. **wp-cli not found**: Ensure `wp` is in PATH
2. **Permission errors**: Commands must run as correct DirectAdmin user
3. **Site discovery fails**: Check DirectAdmin directory structure
4. **ZIP not found**: Normalize ZIPs and check `zips/` folder
5. **Cron jobs not created**: Verify `/home/<user>/.php-version` exists

### Debug Tips
- Check `logs/agrad_wp.log` for detailed output
- Run without `--quiet` to see stdout
- Test wp-cli manually: `sudo -u <user> wp --path=<site> plugin list`
- Verify DirectAdmin structure: `ls /home/<user>/domains/`

## Future Considerations

- Consider adding dry-run mode for updates
- Add rollback capability for failed updates
- Implement parallel site processing for speed
- Add email notifications for errors
- Create web dashboard for monitoring
- Add support for non-DirectAdmin hosting structures
