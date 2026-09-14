# SSH Hosts

[中文](README.md) | [English](README.en.md)

[![skills.sh](https://skills.sh/b/juju-w/ssh-hosts-skill)](https://skills.sh/juju-w/ssh-hosts-skill)

A secure, auditable, cross-platform SSH host management Agent Skill. It accepts only explicit
`Host` aliases from the user's OpenSSH configuration, tries ordinary permissions first, and uses
sudo only when the task actually requires it.

## Why use it

- Accepts only explicit SSH aliases; arbitrary hostnames and IP addresses are rejected.
- Enforces `BatchMode=yes` and never silently falls back to SSH password login.
- Root accounts and scoped `NOPASSWD` work without stored credentials.
- Optional sudo credentials use macOS Keychain, Linux Secret Service, or Windows Credential
  Manager—never plaintext files.
- Passwords travel through stdin, not process arguments or shell history.
- Read-only diagnostics come first, with confirmation required before disruptive changes.

## Install

Install with the open-source `skills` CLI:

```bash
npx skills add juju-w/ssh-hosts-skill
```

Alternatively, clone the repository and copy `skills/ssh-hosts` into the Skill directory used by
your Agent.

## First run

Make sure at least one concrete alias exists in `~/.ssh/config`:

```sshconfig
Host home-nas
    HostName 192.0.2.10
    User operator
    IdentityFile ~/.ssh/id_ed25519
```

Run the read-only setup check from a repository checkout:

```bash
python3 skills/ssh-hosts/scripts/setup_ssh_hosts.py
python3 skills/ssh-hosts/scripts/setup_ssh_hosts.py --host home-nas
```

Windows users can use the PowerShell bootstrap. An explicit trusted Python path can be supplied
when using an embedded or portable runtime:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File skills/ssh-hosts/scripts/setup_ssh_hosts.ps1

powershell -NoProfile -ExecutionPolicy Bypass -File skills/ssh-hosts/scripts/setup_ssh_hosts.ps1 `
  -PythonPath "C:\path\to\python.exe"
```

The setup check does not modify SSH configuration, install software, or read passwords.

## Optional sudo credential

First let the helper detect whether the remote account is root or already has `NOPASSWD`. Only when
password-backed sudo is actually necessary, run this yourself in a trusted local terminal:

```bash
python3 skills/ssh-hosts/scripts/sudo_credential.py set home-nas
```

Never send a sudo password through an Agent conversation.

## Platform support

| Caller platform | SSH | Optional sudo vault |
| --- | --- | --- |
| macOS | System OpenSSH | macOS Keychain |
| Linux desktop | OpenSSH Client | Secret Service (`secret-tool`) |
| Linux headless | OpenSSH Client | Root or scoped `NOPASSWD` recommended |
| Windows 10/11 | Windows OpenSSH Client | Windows Credential Manager |

See [platform details](skills/ssh-hosts/references/platforms.md) and
[usage examples](skills/ssh-hosts/references/examples.md).

## Test

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q skills/ssh-hosts/scripts tests
```

The test suite runs on macOS, Linux, and Windows. Credential-vault smoke tests use only random
synthetic values and delete them immediately.

## Security

Read [SECURITY.md](SECURITY.md) before reporting a vulnerability. Do not include real hosts,
usernames, keys, passwords, tokens, or command output in an issue.

## License

[MIT-0](LICENSE)
