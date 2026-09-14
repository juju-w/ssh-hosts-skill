#!/usr/bin/env python3
"""Discover concrete host aliases from OpenSSH user configuration."""

from __future__ import annotations

import argparse
import glob
import os
import re
import shlex
import shutil
import sys
from pathlib import Path


DEFAULT_CONFIG = Path.home() / ".ssh" / "config"
PATTERN_CHARS = set("*?![]")
ALIAS_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def ssh_binary() -> str:
    executable = shutil.which("ssh")
    if executable is None:
        raise RuntimeError("OpenSSH client is unavailable")
    return executable


def _words(line: str) -> list[str]:
    try:
        lexer = shlex.shlex(line, posix=True)
        lexer.whitespace_split = True
        lexer.commenters = "#"
        if os.name == "nt":
            # Windows OpenSSH config paths use backslashes. POSIX shlex treats them as
            # escape characters and would turn C:\\Users into C:Users.
            lexer.escape = ""
        return list(lexer)
    except ValueError:
        return []


def _include_paths(value: str) -> list[Path]:
    expanded = Path(os.path.expanduser(value))
    pattern = expanded if expanded.is_absolute() else Path.home() / ".ssh" / expanded
    return [Path(item) for item in sorted(glob.glob(str(pattern)))]


def explicit_aliases(config: Path = DEFAULT_CONFIG) -> tuple[str, ...]:
    pending = [config.expanduser()]
    visited: set[Path] = set()
    aliases: set[str] = set()

    while pending:
        path = pending.pop()
        try:
            resolved = path.resolve(strict=True)
        except OSError:
            continue
        if resolved in visited or not resolved.is_file():
            continue
        visited.add(resolved)

        try:
            lines = resolved.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError):
            continue
        for line in lines:
            words = _words(line)
            if len(words) < 2:
                continue
            keyword = words[0].lower()
            if keyword == "include":
                for value in words[1:]:
                    pending.extend(_include_paths(value))
            elif keyword == "host":
                for alias in words[1:]:
                    if (
                        ALIAS_PATTERN.fullmatch(alias)
                        and not any(char in PATTERN_CHARS for char in alias)
                    ):
                        aliases.add(alias)
    return tuple(sorted(aliases))


def require_alias(alias: str, config: Path = DEFAULT_CONFIG) -> str:
    if alias not in explicit_aliases(config):
        raise ValueError(
            f"unregistered SSH alias: {alias}. Add an explicit 'Host {alias}' block to "
            f"{config.expanduser()}, then run 'python3 scripts/ssh_hosts.py list'. "
            "Wildcard Host entries do not register a machine."
        )
    return alias


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    subparsers = parser.add_subparsers(dest="action", required=True)
    subparsers.add_parser("list", help="List concrete aliases without endpoints")
    resolve = subparsers.add_parser("resolve", help="Verify one alias is explicitly registered")
    resolve.add_argument("alias")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.action == "list":
        for alias in explicit_aliases(args.config):
            print(alias)
        return 0
    try:
        print(require_alias(args.alias, args.config))
        return 0
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
