#!/usr/bin/env python3
"""Run a read-only readiness check and print the shortest safe next step."""

from __future__ import annotations

import argparse
import platform
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
    explicit_aliases,
    require_alias,
    ssh_binary,
    ssh_invocation,
)
from sudo_credential import backend_name, backend_problem, exists, ssh_user  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only SSH Hosts readiness check; does not change the system or read passwords"
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--host", help="Also check connectivity and sudo readiness for one registered alias")
    parser.add_argument(
        "--connect-timeout",
        type=int,
        default=DEFAULT_CONNECT_TIMEOUT,
        help=f"SSH connection timeout in seconds (default: {DEFAULT_CONNECT_TIMEOUT})",
    )
    return parser.parse_args()


def probe(alias: str, command: str, connect_timeout: int) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ssh_invocation(alias, command, connect_timeout),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def explain_ssh_failure(alias: str, result: subprocess.CompletedProcess[bytes]) -> str:
    return diagnose_ssh_failure(alias, result).render()


def main() -> int:
    args = parse_args()
    try:
        executable = ssh_binary()
        aliases = explicit_aliases(args.config)
        print(f"system: {platform.system() or 'unknown'}")
        print(f"openssh: available ({executable})")
        print(f"registered_hosts: {len(aliases)}")
        if aliases:
            print("aliases: " + ", ".join(aliases))

        problem = backend_problem()
        if problem:
            print(f"sudo_vault: unavailable ({backend_name()}: {problem})")
        else:
            print(f"sudo_vault: available ({backend_name()})")

        if not args.host:
            if aliases:
                print("status: ready")
                print("next: Use --host <alias> to check SSH and sudo readiness.")
                return 0
            print("status: needs_setup")
            print(
                f"next: Add an explicit 'Host <alias>' block to {args.config.expanduser()}, "
                "then rerun this check."
            )
            return 1

        alias = require_alias(args.host, args.config)
        identity = probe(alias, "id -u", args.connect_timeout)
        if identity.returncode != 0:
            print(explain_ssh_failure(alias, identity), file=sys.stderr)
            return 1
        if identity.stdout.strip() == b"0":
            print(f"status: ready\nhost: {alias}\nssh: connected\nprivilege: root\ncredential: not needed")
            return 0

        nopasswd = probe(alias, "sudo -n -v", args.connect_timeout)
        if nopasswd.returncode == 0:
            print(
                f"status: ready\nhost: {alias}\nssh: connected\nprivilege: sudo_nopasswd"
                "\ncredential: not needed"
            )
            return 0

        account = ssh_user(alias)
        if problem:
            print(
                f"status: limited\nhost: {alias}\nssh: connected\nprivilege: ordinary_user"
                f"\nsudo_vault: unavailable ({backend_name()}: {problem})"
                "\nnext: Use scoped NOPASSWD or the user's trusted interactive administration workflow."
            )
            return 1
        if exists(alias, account):
            print(
                f"status: ready\nhost: {alias}\nssh: connected\nprivilege: sudo_password"
                f"\ncredential: available ({backend_name()})"
            )
            return 0
        print(f"status: limited\nhost: {alias}\nssh: connected\nprivilege: ordinary_user")
        print(f"credential: missing ({backend_name()})")
        print(
            "next: If password-backed sudo is actually required, run this only in your trusted terminal: "
            f"python3 scripts/sudo_credential.py set {alias}"
        )
        return 1
    except (OSError, RuntimeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
