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

from ssh_hosts import (  # noqa: E402
    DEFAULT_CONFIG,
    DEFAULT_CONNECT_TIMEOUT,
    diagnose_ssh_failure,
    require_alias,
    ssh_invocation,
)
from sudo_credential import backend_name, read_password, ssh_user  # noqa: E402


def ssh(
    alias: str,
    remote_command: str,
    connect_timeout: int,
    *,
    input_data: bytes | None = None,
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ssh_invocation(alias, remote_command, connect_timeout),
        input=input_data,
        stdout=None,
        stderr=None,
        check=False,
    )


def quiet_ssh(alias: str, remote_command: str, connect_timeout: int) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ssh_invocation(alias, remote_command, connect_timeout),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
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
    parser.add_argument(
        "--connect-timeout",
        type=int,
        default=DEFAULT_CONNECT_TIMEOUT,
        help=f"SSH connection timeout in seconds (default: {DEFAULT_CONNECT_TIMEOUT})",
    )
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
        identity = quiet_ssh(alias, "id -u", args.connect_timeout)
        if identity.returncode != 0:
            raise RuntimeError(diagnose_ssh_failure(alias, identity).render())
        if identity.stdout.strip() == b"0":
            return ssh(alias, command_text(command), args.connect_timeout).returncode

        nopasswd = quiet_ssh(alias, "sudo -n -v", args.connect_timeout)
        if nopasswd.returncode == 0:
            return ssh(alias, "sudo -n -- " + command_text(command), args.connect_timeout).returncode

        account = ssh_user(alias)
        password = read_password(alias, account)
        if password is None:
            raise RuntimeError(
                "error: sudo.credential_missing\n"
                f"host: {alias}\n"
                "message: Password-backed sudo is required, but no credential is available in "
                f"{backend_name()}.\n"
                f"next: Run 'python3 scripts/sudo_credential.py set {alias}' in a trusted local terminal.\n"
                "hint: A root account or narrowly scoped NOPASSWD rule needs no stored password."
            )
        return ssh(
            alias,
            password_wrapper(command),
            args.connect_timeout,
            input_data=password + b"\n",
        ).returncode
    except (RuntimeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
