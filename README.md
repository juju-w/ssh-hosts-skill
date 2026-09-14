# SSH Hosts

[![skills.sh](https://skills.sh/b/juju-w/ssh-hosts-skill)](https://skills.sh/juju-w/ssh-hosts-skill)

安全、可审计、跨平台的 SSH 主机管理 Agent Skill。它只接受用户 OpenSSH 配置中明确声明的
`Host` 别名，优先使用普通权限，并且只在确有需要时使用 sudo。

Secure, auditable, cross-platform SSH host management for AI agents. The Skill accepts only
explicit `Host` aliases from the user's OpenSSH config, tries ordinary permissions first, and uses
sudo only when the task actually requires it.

## Why

- Explicit alias allowlist; no arbitrary hostname or IP execution.
- `BatchMode=yes`; no silent fallback to SSH password login.
- Root and scoped `NOPASSWD` work without stored credentials.
- Optional sudo credentials use macOS Keychain, Linux Secret Service, or Windows Credential
  Manager—never plaintext files.
- Passwords travel through stdin, not process arguments or shell history.
- Read-only diagnostics first, with confirmation required for disruptive operations.

## Install

Install with the open-source `skills` CLI:

```bash
npx skills add juju-w/ssh-hosts-skill
```

Or clone the repository and copy it into the skill directory used by your Agent.

## First run

Make sure at least one concrete alias exists in `~/.ssh/config`:

```sshconfig
Host home-nas
    HostName 192.0.2.10
    User operator
    IdentityFile ~/.ssh/id_ed25519
```

Then run the read-only setup check:

```bash
python3 scripts/setup_ssh_hosts.py
python3 scripts/setup_ssh_hosts.py --host home-nas
```

Windows users can start with the PowerShell bootstrap, including an explicit trusted Python path
when using an embedded or portable runtime:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup_ssh_hosts.ps1

powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup_ssh_hosts.ps1 `
  -PythonPath "C:\path\to\python.exe"
```

The setup check does not modify SSH configuration, install software, or read passwords.

## Optional sudo credential

First let the helper detect root or `NOPASSWD`. Only when password-backed sudo is really necessary,
run this yourself in a trusted local terminal:

```bash
python3 scripts/sudo_credential.py set home-nas
```

Never send a sudo password through an Agent conversation.

## Platform support

| Caller platform | SSH | Optional sudo vault |
| --- | --- | --- |
| macOS | System OpenSSH | macOS Keychain |
| Linux desktop | OpenSSH Client | Secret Service via `secret-tool` |
| Linux headless | OpenSSH Client | Root/scoped `NOPASSWD` recommended |
| Windows 10/11 | Windows OpenSSH Client | Windows Credential Manager |

See [platform details](references/platforms.md) and [usage examples](references/examples.md).

## Test

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q scripts tests
```

The test suite is exercised on macOS, Linux, and Windows. Credential-store smoke tests use only
random synthetic values and delete them immediately.

## Security

Please read [SECURITY.md](SECURITY.md) before reporting a vulnerability. Do not include real hosts,
usernames, keys, passwords, tokens, or command output in an issue.

## License

[MIT-0](LICENSE)
