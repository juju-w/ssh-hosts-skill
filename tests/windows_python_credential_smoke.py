#!/usr/bin/env python3
"""Round-trip one synthetic Credential Manager item through the Python backend."""

from __future__ import annotations

import platform
import secrets
import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "ssh-hosts" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import sudo_credential  # noqa: E402


def main() -> int:
    if platform.system() != "Windows":
        print("skipped: Windows only")
        return 0
    alias = "smoke-" + secrets.token_hex(8)
    account = "ssh-hosts-smoke"
    password = secrets.token_urlsafe(24)
    created = False
    try:
        sudo_credential.store(alias, account, password, "Windows")
        created = True
        actual = sudo_credential.read_password(alias, account, "Windows")
        if actual != password.encode():
            raise RuntimeError("Credential Manager returned different synthetic data")
        if not sudo_credential.delete(alias, account, "Windows"):
            raise RuntimeError("Credential Manager did not delete the synthetic item")
        created = False
        print("windows_python_credential_roundtrip=ok")
        print("synthetic_credential_removed=true")
        return 0
    finally:
        if created:
            sudo_credential.delete(alias, account, "Windows")


if __name__ == "__main__":
    raise SystemExit(main())
