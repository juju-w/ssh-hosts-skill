# Platform support and security boundaries

SSH Hosts follows the same path on macOS, Linux, and Windows: resolve an explicit alias from
`~/.ssh/config`, try ordinary permissions first, and read a sudo password from the caller's native
vault only when the remote account is not root, non-interactive sudo is unavailable, and the task
actually requires elevation.

## Support matrix

| Caller platform | SSH client | Optional sudo vault | Common limitation |
| --- | --- | --- | --- |
| macOS | System OpenSSH | macOS Keychain | A locked Keychain requires the local user to unlock it |
| Linux desktop | OpenSSH Client | Secret Service (`secret-tool`) | The libsecret CLI or an unlocked login keyring may be missing |
| Linux headless | OpenSSH Client | Depends on a user Secret Service | D-Bus and a keyring are often absent; scoped `NOPASSWD` is preferred |
| Windows 10/11 | Windows OpenSSH Client | Windows Credential Manager | OpenSSH Client may need enabling; Python must be callable from the terminal |

The native vault is not used when the remote account is root or `sudo -n -v` succeeds.

## Read-only readiness check

```bash
python3 scripts/setup_ssh_hosts.py
python3 scripts/setup_ssh_hosts.py --host <alias>
```

The probe sets a finite SSH connection timeout and classifies common failures such as public-key
authentication, DNS, VPN or network reachability, host-key verification, refused connections,
ProxyJump forwarding, and malformed OpenSSH configuration. Each diagnostic includes a stable error
code, a plain-language message, and the shortest useful next command.

Windows users can run the read-only PowerShell bootstrap even before Python is available:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup_ssh_hosts.ps1
```

It does not install software. It reports whether OpenSSH, SSH configuration, or Python is missing.
Ordinary `ssh.exe` connections do not require Python; alias discovery and native-vault helpers do.

If a trusted portable or embedded Python runtime is not on PATH, specify it without installing a
second copy or modifying the system PATH:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup_ssh_hosts.ps1 `
  -PythonPath "C:\path\to\python.exe"
```

## Linux

The Linux password fallback uses Freedesktop Secret Service through `secret-tool`. Passwords pass
through stdin and never enter process arguments. If the desktop keyring is unavailable, locked, or
not attached to the current D-Bus session, the operation fails explicitly and does not fall back to
a plaintext file.

Package names vary by distribution; install the distribution's libsecret command-line tools when
using a desktop keyring. On headless servers, narrowly scoped `NOPASSWD` rules are usually a better
fit than running a desktop keyring only for this Skill.

## Windows

Windows uses Credential Manager for the current signed-in user. The implementation calls the
system Credential API directly, requires no third-party PowerShell module, and does not place the
password in process arguments. Enable Windows OpenSSH Client through optional features or managed
system policy when it is missing.

Before a release, `tests/windows_python_credential_smoke.py` can verify the actual Python backend
on an isolated Windows machine, while `tests/windows_credential_smoke.ps1` checks the system API
directly. Both create one randomly named synthetic credential, verify it, and immediately delete
it without reading or replacing existing credentials. Run these tests in a local interactive user
session; OpenSSH and WinRM sessions may not have the same Credential Manager logon context.

An automated lab may run `tests/windows_interactive_credential_smoke.ps1` through a one-time,
interactive-user-only scheduled task. Delete the task, result files, and temporary directory after
the test. Never register it as a persistent task in a production user session.

## Credential enrollment and deletion

Only the user should run these commands in a trusted local terminal; the Agent must not enter the
password on the user's behalf:

```bash
python3 scripts/sudo_credential.py set <alias>
python3 scripts/sudo_credential.py status <alias>
python3 scripts/sudo_credential.py delete <alias>
```

The older `sudo_keychain.py` remains as a macOS compatibility entry point. New configuration uses
the unified `sudo_credential.py` command.

## What the native vault protects

The native vault keeps passwords out of Skill files, shell history, and process arguments, and
binds storage to the current operating-system user. It is not an isolated authorization broker: a
malicious process running as the same signed-in user may still abuse that user's existing access.
Use a runtime with a separate authorization boundary when per-operation system authentication,
fine-grained approval, or stronger Agent isolation is required.
