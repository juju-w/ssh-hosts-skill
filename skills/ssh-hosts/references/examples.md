# Usage examples

Replace `<alias>` with an explicit `Host` alias from the user's OpenSSH configuration. Start with
read-only operations. Never place a host address, username, password, or private key in the Skill.

## Quick task map

- First use or connection failure: run the readiness check below.
- Host health: combine a few closely related read-only checks in one SSH call.
- Docker or logs: try the registered account first; use sudo only after a permission failure.
- File transfer: confirm the source, destination, and overwrite risk before copying.
- Password-backed sudo: let the user provision the native vault from a trusted terminal.

## First use

Run the read-only readiness check. It does not change configuration or read passwords:

```bash
python3 scripts/setup_ssh_hosts.py
```

Representative successful output:

```text
system: Darwin
openssh: available (/usr/bin/ssh)
registered_hosts: 2
aliases: home-nas, production-api
sudo_vault: available (macOS Keychain)
status: ready
next: Use --host <alias> to check SSH and sudo readiness.
```

List registered aliases without revealing endpoints:

```bash
python3 scripts/ssh_hosts.py list
```

Check whether OpenSSH can connect with public-key authentication:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=10 -- <alias> 'uname -a'
```

If authentication fails, the readiness check returns a stable error category and a concrete next
command:

```text
error: ssh.authentication_failed
host: home-nas
message: Public-key authentication was rejected.
next: ssh -v -- home-nas
hint: Check IdentityFile, ssh-agent, and the remote authorized_keys file. Password login is not used.
```

Use `ssh -G -- <alias>` to inspect effective configuration. Do not print private-key contents.

## Host health

Combine closely related read-only checks to reduce round trips:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=10 -- <alias> \
  'uptime; printf "\n-- filesystems --\n"; df -h; printf "\n-- memory --\n"; free -h 2>/dev/null || true'
```

## Docker status

Try the registered account first. Membership in the `docker` group may already provide access:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=10 -- <alias> \
  'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"'
```

Only consider sudo or a remote account change after a permission failure. Reading Docker service
status is non-destructive:

```bash
python3 scripts/ssh_sudo.py \
  --host <alias> --allow-high-privilege -- \
  systemctl status docker
```

Restarting a container or the Docker service can interrupt workloads and requires confirmation.

## Logs

First try logs available to the registered account and keep output bounded:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=10 -- <alias> \
  'journalctl -u docker --since "30 minutes ago" --no-pager -n 200'
```

If the same bounded query genuinely requires administrator access, run it through `ssh_sudo.py`.

## File transfer

Use OpenSSH `scp` so SSH configuration continues to handle jump hosts, agents, and keys:

```bash
scp -- ./local-file <alias>:/tmp/
scp -- <alias>:/tmp/remote-file ./
```

Confirm the destination and impact before overwriting a remote file, writing a system directory, or
transferring sensitive data.

## Password-backed sudo fallback

Root accounts and `NOPASSWD` sudo work without a stored password on every caller platform. Only
when password-backed sudo is actually required should the user run:

```bash
python3 scripts/setup_ssh_hosts.py --host <alias>
python3 scripts/sudo_credential.py set <alias>
```

macOS uses Keychain, Linux uses Secret Service, and Windows uses Credential Manager. Never request
the password in conversation or create a plaintext fallback when the native vault is unavailable.
