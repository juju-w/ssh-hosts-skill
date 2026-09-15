#!/usr/bin/env python3
"""Discover concrete host aliases from OpenSSH user configuration."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import glob
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


DEFAULT_CONFIG = Path.home() / ".ssh" / "config"
DEFAULT_CONNECT_TIMEOUT = 10
PATTERN_CHARS = set("*?![]")
ALIAS_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


@dataclass(frozen=True)
class SshDiagnostic:
    code: str
    alias: str
    message: str
    next_step: str
    hint: str
    detail: str | None = None

    def render(self) -> str:
        lines = [
            f"error: {self.code}",
            f"host: {self.alias}",
            f"message: {self.message}",
            f"next: {self.next_step}",
            f"hint: {self.hint}",
        ]
        if self.detail:
            lines.append(f"detail: {self.detail}")
        return "\n".join(lines)


def ssh_binary() -> str:
    executable = shutil.which("ssh")
    if executable is None:
        raise RuntimeError(
            "error: local.openssh_missing\n"
            "message: No OpenSSH client was found on PATH.\n"
            "next: Install or enable OpenSSH Client, reopen the terminal, and rerun the readiness check.\n"
            "hint: On Windows, OpenSSH Client is an optional system feature."
        )
    return executable


def ssh_invocation(alias: str, remote_command: str, connect_timeout: int) -> list[str]:
    if connect_timeout < 1:
        raise ValueError("connect timeout must be at least 1 second")
    return [
        ssh_binary(),
        "-T",
        "-o",
        "BatchMode=yes",
        "-o",
        f"ConnectTimeout={connect_timeout}",
        "--",
        alias,
        remote_command,
    ]


def diagnose_ssh_failure(
    alias: str, result: subprocess.CompletedProcess[bytes]
) -> SshDiagnostic:
    raw = result.stderr.decode(errors="replace").strip()
    stderr = raw.lower()
    verbose = f"ssh -v -- {alias}"

    if "permission denied" in stderr:
        return SshDiagnostic(
            "ssh.authentication_failed",
            alias,
            "Public-key authentication was rejected.",
            verbose,
            "Check IdentityFile, ssh-agent, and the remote authorized_keys file. Password login is not used.",
        )
    if any(
        marker in stderr
        for marker in (
            "could not resolve hostname",
            "name or service not known",
            "temporary failure in name resolution",
        )
    ):
        return SshDiagnostic(
            "ssh.hostname_resolution_failed",
            alias,
            "The SSH hostname could not be resolved.",
            f"ssh -G -- {alias}",
            "Check HostName, DNS, VPN, and ProxyJump in the effective SSH configuration.",
        )
    if "host key verification failed" in stderr or "remote host identification has changed" in stderr:
        return SshDiagnostic(
            "ssh.host_key_verification_failed",
            alias,
            "The server identity could not be verified.",
            verbose,
            "Verify the host fingerprint with its administrator. Do not disable StrictHostKeyChecking.",
        )
    if "connection refused" in stderr:
        return SshDiagnostic(
            "ssh.connection_refused",
            alias,
            "The host was reached, but its SSH service refused the connection.",
            verbose,
            "Check the configured port and whether sshd is running on the remote host.",
        )
    if any(
        marker in stderr
        for marker in (
            "connection timed out",
            "operation timed out",
            "no route to host",
            "network is unreachable",
        )
    ):
        return SshDiagnostic(
            "ssh.network_unreachable",
            alias,
            "The SSH host could not be reached before the connection timeout.",
            verbose,
            "Check the network, VPN, firewall, configured port, and whether the host is online.",
        )
    if "stdio forwarding failed" in stderr or "jumphost loop" in stderr:
        return SshDiagnostic(
            "ssh.proxy_jump_failed",
            alias,
            "The configured SSH jump host could not forward the connection.",
            verbose,
            "Check ProxyJump connectivity and authentication before retrying the target host.",
        )
    if "bad configuration option" in stderr or "no argument after keyword" in stderr:
        return SshDiagnostic(
            "ssh.config_invalid",
            alias,
            "OpenSSH rejected the effective configuration.",
            f"ssh -G -- {alias}",
            "Fix the reported SSH configuration option, then rerun the readiness check.",
        )

    detail_lines = [CONTROL_CHARS.sub("", line).strip() for line in raw.splitlines() if line.strip()]
    detail = detail_lines[-1][:300] if detail_lines else None
    return SshDiagnostic(
        "ssh.connection_failed",
        alias,
        "The SSH connection failed for an unclassified reason.",
        verbose,
        "Review the final OpenSSH detail below and the effective configuration before retrying.",
        detail,
    )


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
    if not ALIAS_PATTERN.fullmatch(alias) or any(char in PATTERN_CHARS for char in alias):
        raise ValueError(
            "error: ssh.alias_invalid\n"
            "message: The requested SSH alias has an invalid format.\n"
            "next: Use 'python3 scripts/ssh_hosts.py list' to select a registered alias.\n"
            "hint: Aliases may contain letters, digits, dots, underscores, and hyphens; patterns are not allowed."
        )
    if alias not in explicit_aliases(config):
        raise ValueError(
            "error: ssh.alias_not_registered\n"
            f"host: {alias}\n"
            "message: The requested SSH alias is not explicitly registered.\n"
            f"next: Add a 'Host {alias}' block to {config.expanduser()}, then run "
            "'python3 scripts/ssh_hosts.py list'.\n"
            "hint: Wildcard Host entries do not register a machine."
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
