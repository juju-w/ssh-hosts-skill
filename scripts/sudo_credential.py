#!/usr/bin/env python3
"""Store sudo credentials in the current platform's native credential vault."""

from __future__ import annotations

import argparse
import ctypes
import getpass
import platform
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from ssh_hosts import DEFAULT_CONFIG, explicit_aliases, require_alias, ssh_binary


SERVICE_PREFIX = "dev.ssh-hosts.sudo"


def ssh_user(alias: str) -> str:
    result = subprocess.run(
        [ssh_binary(), "-G", "--", alias],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip().splitlines()
        suffix = f": {detail[-1]}" if detail else ""
        raise RuntimeError(
            f"OpenSSH could not resolve alias '{alias}'{suffix}. "
            "Check the matching Host block with: ssh -G -- " + alias
        )
    for line in result.stdout.splitlines():
        key, _, value = line.partition(" ")
        if key.lower() == "user" and value.strip():
            return value.strip()
    raise RuntimeError(
        f"OpenSSH returned no remote user for alias '{alias}'. "
        "Add User to the matching Host block or fix the included SSH config."
    )


def service(alias: str) -> str:
    return f"{SERVICE_PREFIX}/{alias}"


def windows_target(alias: str, account: str) -> str:
    return f"{service(alias)}/{account}"


def backend_name(system: str | None = None) -> str:
    current = system or platform.system()
    return {
        "Darwin": "macOS Keychain",
        "Linux": "Secret Service",
        "Windows": "Windows Credential Manager",
    }.get(current, "unsupported platform")


def backend_problem(system: str | None = None) -> str | None:
    current = system or platform.system()
    if current == "Darwin":
        return None if Path("/usr/bin/security").is_file() else "the macOS security tool is missing"
    if current == "Linux":
        if shutil.which("secret-tool") is None:
            return "secret-tool is missing; install the libsecret command-line tools"
        return None
    if current == "Windows":
        return None
    return f"{current or 'this operating system'} has no supported native credential backend"


def _mac_exists(alias: str, account: str) -> bool:
    result = subprocess.run(
        ["/usr/bin/security", "find-generic-password", "-s", service(alias), "-a", account],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def _mac_store(alias: str, account: str, password: str) -> None:
    result = subprocess.run(
        [
            "/usr/bin/security",
            "add-generic-password",
            "-s",
            service(alias),
            "-a",
            account,
            "-U",
            "-w",
        ],
        input=f"{password}\n{password}\n",
        text=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"macOS Keychain write failed for '{alias}'")


def _mac_read(alias: str, account: str) -> bytes | None:
    result = subprocess.run(
        ["/usr/bin/security", "find-generic-password", "-s", service(alias), "-a", account, "-w"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.stdout.rstrip(b"\r\n") if result.returncode == 0 else None


def _mac_delete(alias: str, account: str) -> bool:
    result = subprocess.run(
        ["/usr/bin/security", "delete-generic-password", "-s", service(alias), "-a", account],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def _linux_attributes(alias: str, account: str) -> list[str]:
    return ["service", SERVICE_PREFIX, "alias", alias, "account", account]


def _secret_tool() -> str:
    executable = shutil.which("secret-tool")
    if executable is None:
        raise RuntimeError(
            "Secret Service support is unavailable because secret-tool is missing. "
            "Install the libsecret command-line tools, or use root/NOPASSWD sudo."
        )
    return executable


def _linux_read(alias: str, account: str) -> bytes | None:
    result = subprocess.run(
        [_secret_tool(), "lookup", *_linux_attributes(alias, account)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.decode(errors="replace").strip()
        if detail:
            raise RuntimeError(
                "Secret Service could not be opened. Ensure a desktop keyring is running and unlocked: "
                + detail
            )
        return None
    value = result.stdout.rstrip(b"\r\n")
    return value or None


def _linux_store(alias: str, account: str, password: str) -> None:
    result = subprocess.run(
        [
            _secret_tool(),
            "store",
            "--label=SSH Hosts sudo credential",
            *_linux_attributes(alias, account),
        ],
        input=password.encode() + b"\n",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.decode(errors="replace").strip()
        raise RuntimeError(
            "Secret Service write failed. Ensure a desktop keyring is running and unlocked"
            + (f": {detail}" if detail else "")
        )


def _linux_delete(alias: str, account: str) -> bool:
    result = subprocess.run(
        [_secret_tool(), "clear", *_linux_attributes(alias, account)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode not in (0, 1):
        detail = result.stderr.decode(errors="replace").strip()
        raise RuntimeError("Secret Service delete failed" + (f": {detail}" if detail else ""))
    return result.returncode == 0


def _windows_api() -> tuple[object, type[ctypes.Structure]]:
    from ctypes import wintypes

    class Credential(ctypes.Structure):
        _fields_ = [
            ("Flags", wintypes.DWORD),
            ("Type", wintypes.DWORD),
            ("TargetName", wintypes.LPWSTR),
            ("Comment", wintypes.LPWSTR),
            ("LastWritten", wintypes.FILETIME),
            ("CredentialBlobSize", wintypes.DWORD),
            ("CredentialBlob", ctypes.POINTER(wintypes.BYTE)),
            ("Persist", wintypes.DWORD),
            ("AttributeCount", wintypes.DWORD),
            ("Attributes", ctypes.c_void_p),
            ("TargetAlias", wintypes.LPWSTR),
            ("UserName", wintypes.LPWSTR),
        ]

    advapi32 = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
    pointer = ctypes.POINTER(Credential)
    advapi32.CredWriteW.argtypes = [pointer, wintypes.DWORD]
    advapi32.CredWriteW.restype = wintypes.BOOL
    advapi32.CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(pointer)]
    advapi32.CredReadW.restype = wintypes.BOOL
    advapi32.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
    advapi32.CredDeleteW.restype = wintypes.BOOL
    advapi32.CredFree.argtypes = [ctypes.c_void_p]
    advapi32.CredFree.restype = None
    return advapi32, Credential


def _windows_read(alias: str, account: str) -> bytes | None:
    advapi32, credential_type = _windows_api()
    pointer_type = ctypes.POINTER(credential_type)
    credential_pointer = pointer_type()
    if not advapi32.CredReadW(windows_target(alias, account), 1, 0, ctypes.byref(credential_pointer)):
        if ctypes.get_last_error() == 1168:
            return None
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        credential = credential_pointer.contents
        return ctypes.string_at(credential.CredentialBlob, credential.CredentialBlobSize)
    finally:
        advapi32.CredFree(credential_pointer)


def _windows_store(alias: str, account: str, password: str) -> None:
    from ctypes import wintypes

    advapi32, credential_type = _windows_api()
    blob = password.encode()
    blob_buffer = (wintypes.BYTE * len(blob)).from_buffer_copy(blob)
    credential = credential_type()
    credential.Type = 1
    credential.TargetName = windows_target(alias, account)
    credential.CredentialBlobSize = len(blob)
    credential.CredentialBlob = ctypes.cast(blob_buffer, ctypes.POINTER(wintypes.BYTE))
    credential.Persist = 2
    credential.UserName = account
    if not advapi32.CredWriteW(ctypes.byref(credential), 0):
        raise ctypes.WinError(ctypes.get_last_error())


def _windows_delete(alias: str, account: str) -> bool:
    advapi32, _credential_type = _windows_api()
    if advapi32.CredDeleteW(windows_target(alias, account), 1, 0):
        return True
    if ctypes.get_last_error() == 1168:
        return False
    raise ctypes.WinError(ctypes.get_last_error())


def read_password(alias: str, account: str, system: str | None = None) -> bytes | None:
    current = system or platform.system()
    if current == "Darwin":
        return _mac_read(alias, account)
    if current == "Linux":
        return _linux_read(alias, account)
    if current == "Windows":
        return _windows_read(alias, account)
    raise RuntimeError(f"no supported credential backend for {current}")


def exists(alias: str, account: str, system: str | None = None) -> bool:
    current = system or platform.system()
    if current == "Darwin":
        return _mac_exists(alias, account)
    return read_password(alias, account, current) is not None


def store(alias: str, account: str, password: str, system: str | None = None) -> None:
    current = system or platform.system()
    if current == "Darwin":
        _mac_store(alias, account, password)
    elif current == "Linux":
        _linux_store(alias, account, password)
    elif current == "Windows":
        _windows_store(alias, account, password)
    else:
        raise RuntimeError(f"no supported credential backend for {current}")


def delete(alias: str, account: str, system: str | None = None) -> bool:
    current = system or platform.system()
    if current == "Darwin":
        return _mac_delete(alias, account)
    if current == "Linux":
        return _linux_delete(alias, account)
    if current == "Windows":
        return _windows_delete(alias, account)
    raise RuntimeError(f"no supported credential backend for {current}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manage sudo credentials in the native OS vault")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    subparsers = parser.add_subparsers(dest="action", required=True)
    status = subparsers.add_parser("status", help="Check whether credentials exist")
    status.add_argument("hosts", nargs="*")
    set_command = subparsers.add_parser("set", help="Store credentials from a trusted local terminal")
    set_command.add_argument("hosts", nargs="+")
    delete_command = subparsers.add_parser("delete", help="Delete stored credentials")
    delete_command.add_argument("hosts", nargs="+")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        problem = backend_problem()
        if problem:
            raise RuntimeError(f"{backend_name()} unavailable: {problem}")
        requested = args.hosts or list(explicit_aliases(args.config))
        hosts = list(dict.fromkeys(require_alias(host, args.config) for host in requested))
        if args.action == "status":
            missing = False
            for host in hosts:
                available = exists(host, ssh_user(host))
                print(f"{host}: {'available' if available else 'missing'} ({backend_name()})")
                missing = missing or not available
            return 1 if missing else 0

        if args.action == "delete":
            for host in hosts:
                removed = delete(host, ssh_user(host))
                print(f"{host}: {'deleted' if removed else 'not found'}")
            return 0

        if not sys.stdin.isatty():
            raise RuntimeError(
                "credential setup requires a trusted local terminal; do not enter sudo passwords in an Agent chat"
            )
        for host in hosts:
            account = ssh_user(host)
            first = getpass.getpass(f"sudo password for {account}@{host}: ")
            second = getpass.getpass("Retype sudo password: ")
            if not first:
                raise ValueError("empty password is not allowed")
            if "\n" in first or "\r" in first:
                raise ValueError("sudo passwords containing newlines are unsupported")
            if first != second:
                raise ValueError("passwords do not match")
            store(host, account, first)
            print(f"stored: {host} ({backend_name()})")
        return 0
    except (OSError, RuntimeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
