"""Manage allowed IPs and firewall rules for key services."""
from __future__ import annotations

import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

from .. import paths, prompts

logger = logging.getLogger(__name__)

DEFAULT_ALLOWED_IPS = [
    "2.180.12.195",
    "162.19.171.47",
    "104.28.205.246",
    "104.28.193.116",
    "127.0.0.1",
]

SERVICES = [
    ("SSH", 2244, ["tcp"]),
    ("DirectAdmin", 8956, ["tcp"]),
    ("MySQL", 3306, ["tcp"]),
    ("FTP", 21, ["tcp"]),
    ("LiteSpeed Admin", 7080, ["tcp"]),
]


def run_security_menu() -> None:
    options = [
        "Show allowed IPs",
        "Add allowed IP",
        "Remove allowed IP",
        "Apply firewall rules",
        "Restore last firewall backup",
        "Back",
    ]
    while True:
        choice = prompts.ask_from_list("Security options", options)
        if choice == "Show allowed IPs":
            _show_allowed_ips()
        elif choice == "Add allowed IP":
            _add_ip()
        elif choice == "Remove allowed IP":
            _remove_ip()
        elif choice == "Apply firewall rules":
            _apply_rules_with_backup()
        elif choice == "Restore last firewall backup":
            _restore_backup()
        elif choice == "Back":
            break


def load_allowed_ips() -> List[str]:
    path = paths.ALLOWED_IPS_PATH
    if not path.exists():
        save_allowed_ips(DEFAULT_ALLOWED_IPS)
        return list(DEFAULT_ALLOWED_IPS)
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, list):
            return [str(ip).strip() for ip in data if str(ip).strip()]
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Failed to read %s: %s", path, exc)
    return list(DEFAULT_ALLOWED_IPS)


def save_allowed_ips(ips: List[str]) -> None:
    path = paths.ALLOWED_IPS_PATH
    with path.open("w", encoding="utf-8") as fh:
        json.dump(sorted(set(ips)), fh, indent=2)
    logger.info("Saved allowed IPs to %s", path)


def _show_allowed_ips() -> None:
    ips = load_allowed_ips()
    print("Allowed IPs:")
    for ip in ips:
        print(f" - {ip}")


def _add_ip() -> None:
    ips = load_allowed_ips()
    new_ip = input("Enter IP to add: ").strip()
    if not new_ip:
        logger.warning("No IP provided.")
        return
    if new_ip in ips:
        logger.info("%s already allowed.", new_ip)
        return
    ips.append(new_ip)
    save_allowed_ips(ips)


def _remove_ip() -> None:
    ips = load_allowed_ips()
    if not ips:
        logger.info("Allowed IP list is empty.")
        return
    ip = prompts.ask_from_list("Select IP to remove", ips)
    ips = [entry for entry in ips if entry != ip]
    save_allowed_ips(ips)


def _apply_rules_with_backup() -> None:
    backup_path = backup_firewall()
    logger.info("Firewall backup saved to %s", backup_path)
    apply_rules()


def apply_rules() -> None:
    ips = load_allowed_ips()
    ipv4_allow = [ip for ip in ips if not _is_ipv6(ip)]
    ipv6_allow = [ip for ip in ips if _is_ipv6(ip)]
    allowed_mysql = set(ipv4_allow) | {"127.0.0.1"}
    allowed_ftp = set(ipv4_allow) | {"127.0.0.1"}

    _ensure_chain("AGRAD_ACCESS", ipv6=False)
    _flush_chain("AGRAD_ACCESS", ipv6=False)

    _ensure_chain("AGRAD_ACCESS6", ipv6=True)
    _flush_chain("AGRAD_ACCESS6", ipv6=True)

    for service, port, protocols in SERVICES:
        allowed_v4 = ipv4_allow
        if service == "MySQL":
            allowed_v4 = list(allowed_mysql)
        if service == "FTP":
            allowed_v4 = list(allowed_ftp)
        for proto in protocols:
            for ip in allowed_v4:
                _run(["iptables", "-A", "AGRAD_ACCESS", "-p", proto, "--dport", str(port), "-s", ip, "-j", "ACCEPT"])
            _run(["iptables", "-A", "AGRAD_ACCESS", "-p", proto, "--dport", str(port), "-j", "DROP"])
        logger.info("Applied IPv4 rules for %s (port %s)", service, port)

        # IPv6: if no IPv6 allowlist, drop everything for these ports
        for proto in protocols:
            for ip in ipv6_allow:
                _run(["ip6tables", "-A", "AGRAD_ACCESS6", "-p", proto, "--dport", str(port), "-s", ip, "-j", "ACCEPT"])
            _run(["ip6tables", "-A", "AGRAD_ACCESS6", "-p", proto, "--dport", str(port), "-j", "DROP"])
        if ipv6_allow:
            logger.info("Applied IPv6 rules for %s (port %s)", service, port)
        else:
            logger.info("Blocked IPv6 traffic for %s (port %s)", service, port)

    _ensure_input_jump("AGRAD_ACCESS", ipv6=False)
    _ensure_input_jump("AGRAD_ACCESS6", ipv6=True)
    logger.info("Firewall rules applied.")


def backup_firewall() -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = paths.ROOT_DIR / f"iptables_backup_{ts}.rules"
    result = subprocess.run(["iptables-save"], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to backup iptables: {result.stderr.strip()}")
    backup_path.write_text(result.stdout, encoding="utf-8")
    return backup_path


def _restore_backup() -> None:
    backup = _latest_backup()
    if not backup:
        logger.warning("No firewall backup found.")
        return
    logger.info("Restoring firewall from %s", backup)
    result = subprocess.run(["iptables-restore"], input=backup.read_text(encoding="utf-8"), text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to restore iptables: {result.stderr.strip()}")
    logger.info("Restore completed.")


def _latest_backup() -> Path | None:
    backups = sorted(paths.ROOT_DIR.glob("iptables_backup_*.rules"))
    return backups[-1] if backups else None


def _ensure_chain(chain: str, ipv6: bool = False) -> None:
    binary = "ip6tables" if ipv6 else "iptables"
    result = subprocess.run([binary, "-L", chain], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        _run([binary, "-N", chain])


def _flush_chain(chain: str, ipv6: bool = False) -> None:
    binary = "ip6tables" if ipv6 else "iptables"
    _run([binary, "-F", chain])


def _ensure_input_jump(chain: str, ipv6: bool = False) -> None:
    binary = "ip6tables" if ipv6 else "iptables"
    result = subprocess.run([binary, "-C", "INPUT", "-j", chain], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        _run([binary, "-I", "INPUT", "1", "-j", chain])


def _run(cmd: List[str]) -> Tuple[int, str, str]:
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        logger.error("Command failed (%s): %s", " ".join(cmd), result.stderr.strip())
    return result.returncode, result.stdout, result.stderr


def _is_ipv6(ip: str) -> bool:
    return ":" in ip
