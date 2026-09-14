# Security policy

## Reporting

Please use GitHub's private vulnerability reporting for security issues. Do not open a public issue
containing a real hostname, endpoint, username, SSH configuration, private key, password, token,
Credential Manager target, Keychain label, Secret Service attribute, or remote command output.

## Security boundary

SSH Hosts is a lightweight Agent Skill, not an isolated credential broker. Native OS vaults keep
passwords out of files, command arguments, and chat, but another malicious process running as the
same operating-system user may still abuse that user's existing access.

The Skill deliberately refuses arbitrary hosts, SSH password fallback, disabled host-key checking,
plaintext sudo-password storage, and unscoped privileged execution.

## Supported versions

Security fixes are applied to the latest published version.
