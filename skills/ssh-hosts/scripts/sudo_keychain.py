#!/usr/bin/env python3
"""Backward-compatible macOS wrapper for sudo_credential.py."""

from __future__ import annotations

import platform
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from sudo_credential import (  # noqa: E402, F401
    exists,
    main as credential_main,
    service,
    ssh_user,
    store,
)


def main() -> int:
    if platform.system() != "Darwin":
        print(
            "sudo_keychain.py is macOS-only; use sudo_credential.py for this platform",
            file=sys.stderr,
        )
        return 2
    return credential_main()


if __name__ == "__main__":
    raise SystemExit(main())
