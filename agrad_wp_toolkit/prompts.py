"""Simple input helpers for the interactive CLI."""
from __future__ import annotations

from typing import Iterable, List


def ask_yes_no(question: str, default: bool = True) -> bool:
    suffix = " [Y/n]: " if default else " [y/N]: "
    while True:
        resp = input(question + suffix).strip().lower()
        if not resp:
            return default
        if resp in {"y", "yes"}:
            return True
        if resp in {"n", "no"}:
            return False
        print("Please enter y or n.")


def ask_from_list(question: str, items: Iterable[str]) -> str:
    options = list(items)
    if not options:
        raise ValueError("No options to choose from.")
    for idx, option in enumerate(options, start=1):
        print(f"{idx}) {option}")
    while True:
        resp = input(f"{question} (1-{len(options)}): ").strip()
        if not resp.isdigit():
            print("Enter the number of the option you want.")
            continue
        idx = int(resp)
        if 1 <= idx <= len(options):
            return options[idx - 1]
        print("Out of range. Try again.")


def ask_multi_select(question: str, items: Iterable[str]) -> List[str]:
    options = list(items)
    if not options:
        return []
    for idx, option in enumerate(options, start=1):
        print(f"{idx}) {option}")
    print("Enter comma-separated numbers (e.g., 1,3,4) or press Enter for none.")
    while True:
        resp = input(f"{question}: ").strip()
        if not resp:
            return []
        parts = [part.strip() for part in resp.split(",")]
        selections: List[str] = []
        invalid = False
        for part in parts:
            if not part.isdigit():
                invalid = True
                break
            idx = int(part)
            if not 1 <= idx <= len(options):
                invalid = True
                break
            selections.append(options[idx - 1])
        if invalid:
            print("Invalid selection. Try again.")
            continue
        # remove duplicates while preserving order
        seen = set()
        deduped: List[str] = []
        for item in selections:
            if item not in seen:
                seen.add(item)
                deduped.append(item)
        return deduped
