# Local configuration

## Registered hosts

The Skill recognizes only concrete `Host` aliases declared in `~/.ssh/config` or files reached by
OpenSSH `Include` directives. Patterns containing `*`, `?`, or `!` are not resources.

Example:

```sshconfig
Host home-nas
    HostName 192.0.2.10
    User operator
    IdentityFile ~/.ssh/id_ed25519

Host production-api
    HostName api.internal.example
    User deploy
    ProxyJump company-bastion
```

Keep real endpoints in the user's SSH config, not in the Skill directory.

List the explicit aliases without printing endpoints:

```bash
python3 scripts/ssh_hosts.py list
```

## Optional machine context

Users may keep private cross-Agent context at `~/.config/ssh-hosts/hosts.md`. This file is never
packaged with the Skill. A compact format is enough:

```markdown
# Hosts

## home-nas
- Purpose: household storage
- Environment: personal
- Caution: diagnose storage read-only before changing datasets

## production-api
- Purpose: customer API
- Environment: production
- Caution: restart only after an explicit request
```

Update this file only when the user asks to remember durable facts or approves an inventory
refresh. Do not store passwords, tokens, private keys, or recovery material in it.

## Optional cross-platform sudo password

The sudo helpers use one native-vault item per concrete SSH alias and effective remote account:

- service: `dev.ssh-hosts.sudo/<alias>`
- account: the effective remote user reported by `ssh -G`

Provisioning happens in a trusted local terminal with echo disabled. The Skill and Agent never
receive the password in conversation. macOS uses Keychain, Linux uses Secret Service, and Windows
uses Credential Manager. If the native vault is missing or locked, use a root account, scoped
non-interactive sudo policy, or the user's normal interactive administration workflow instead.

Run `python3 scripts/setup_ssh_hosts.py --host <alias>` first. It reports whether root,
`NOPASSWD`, or an existing native-vault item already makes setup unnecessary.
