#!/usr/bin/env python3
"""Execute one scoped command with the least available remote privilege."""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from ssh_hosts import DEFAULT_CONFIG, require_alias, ssh_binary
from sudo_credential import backend_name, read_password, ssh_user


def ssh(alias: str, remote_command: str, *, input_data: bytes | None = None) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [ssh_binary(), "-T", "-o", "BatchMode=yes", "--", alias, remote_command],
        input=input_data,
        stdout=None,
        stderr=None,
        check=False,
    )


def quiet_ssh(alias: str, remote_command: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [ssh_binary(), "-T", "-o", "BatchMode=yes", "--", alias, remote_command],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def command_text(command: list[str]) -> str:
    return "sh -c 'exec \"$@\" </dev/null' sh " + shlex.join(command)


def password_wrapper(command: list[str]) -> str:
    return (
        "IFS= read -r SSH_HOSTS_SUDO_PASSWORD || exit 90; "
        "printf '%s\\n' \"$SSH_HOSTS_SUDO_PASSWORD\" | "
        "sudo -S -p '' -- "
        + command_text(command)
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--host", required=True)
    parser.add_argument("--allow-high-privilege", action="store_true")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.allow_high_privilege:
        print("sudo execution requires --allow-high-privilege", file=sys.stderr)
        return 2
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        print("missing remote command after --", file=sys.stderr)
        return 2
    try:
        alias = require_alias(args.host, args.config)
        identity = quiet_ssh(alias, "id -u")
        if identity.returncode != 0:
            raise RuntimeError(f"SSH connection failed for {alias}")
        if identity.stdout.strip() == b"0":
            return ssh(alias, command_text(command)).returncode

        nopasswd = quiet_ssh(alias, "sudo -n -v")
        if nopasswd.returncode == 0:
            return ssh(alias, "sudo -n -- " + command_text(command)).returncode

        account = ssh_user(alias)
        password = read_password(alias, account)
        if password is None:
            raise RuntimeError(
                f"sudo credential unavailable for '{alias}' in {backend_name()}; "
                f"run 'python3 scripts/sudo_credential.py set {alias}' in a trusted local terminal, "
                "or configure root/scoped NOPASSWD sudo"
            )
        return ssh(alias, password_wrapper(command), input_data=password + b"\n").returncode
    except (RuntimeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
