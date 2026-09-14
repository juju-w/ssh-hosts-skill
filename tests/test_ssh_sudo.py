from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import ssh_sudo  # noqa: E402
import sudo_credential  # noqa: E402
import sudo_keychain  # noqa: E402


def result(returncode: int, stdout: bytes = b"") -> subprocess.CompletedProcess[bytes]:
    return subprocess.CompletedProcess([], returncode, stdout=stdout, stderr=b"")


class SshSudoTests(unittest.TestCase):
    def args(self) -> SimpleNamespace:
        return SimpleNamespace(
            allow_high_privilege=True,
            command=["--", "systemctl", "status", "docker"],
            config=Path("unused"),
            host="nas",
        )

    @mock.patch.object(ssh_sudo, "parse_args")
    @mock.patch.object(ssh_sudo, "require_alias", return_value="nas")
    @mock.patch.object(ssh_sudo, "quiet_ssh")
    @mock.patch.object(ssh_sudo, "ssh")
    def test_root_account_runs_without_sudo(
        self, run_ssh: mock.Mock, quiet: mock.Mock, _require: mock.Mock, parse: mock.Mock
    ) -> None:
        parse.return_value = self.args()
        quiet.return_value = result(0, b"0\n")
        run_ssh.return_value = result(0)

        self.assertEqual(ssh_sudo.main(), 0)
        remote_command = run_ssh.call_args.args[1]
        self.assertNotIn("sudo", remote_command)
        quiet.assert_called_once_with("nas", "id -u")

    @mock.patch.object(ssh_sudo, "parse_args")
    @mock.patch.object(ssh_sudo, "require_alias", return_value="nas")
    @mock.patch.object(ssh_sudo, "quiet_ssh")
    @mock.patch.object(ssh_sudo, "ssh")
    def test_nopasswd_sudo_is_cross_platform(
        self, run_ssh: mock.Mock, quiet: mock.Mock, _require: mock.Mock, parse: mock.Mock
    ) -> None:
        parse.return_value = self.args()
        quiet.side_effect = [result(0, b"1000\n"), result(0)]
        run_ssh.return_value = result(0)

        self.assertEqual(ssh_sudo.main(), 0)
        self.assertTrue(run_ssh.call_args.args[1].startswith("sudo -n -- "))

    @mock.patch.object(ssh_sudo, "read_password", return_value=None)
    @mock.patch.object(ssh_sudo, "ssh_user", return_value="operator")
    @mock.patch.object(ssh_sudo, "parse_args")
    @mock.patch.object(ssh_sudo, "require_alias", return_value="nas")
    @mock.patch.object(ssh_sudo, "quiet_ssh")
    @mock.patch.object(ssh_sudo, "ssh")
    def test_missing_native_vault_credential_stops_without_running_command(
        self,
        run_ssh: mock.Mock,
        quiet: mock.Mock,
        _require: mock.Mock,
        parse: mock.Mock,
        _user: mock.Mock,
        _password: mock.Mock,
    ) -> None:
        parse.return_value = self.args()
        quiet.side_effect = [result(0, b"1000\n"), result(1)]

        self.assertEqual(ssh_sudo.main(), 1)
        run_ssh.assert_not_called()

    @mock.patch.object(ssh_sudo, "read_password", return_value=b"not-a-real-password")
    @mock.patch.object(ssh_sudo, "ssh_user", return_value="operator")
    @mock.patch.object(ssh_sudo, "parse_args")
    @mock.patch.object(ssh_sudo, "require_alias", return_value="nas")
    @mock.patch.object(ssh_sudo, "quiet_ssh")
    @mock.patch.object(ssh_sudo, "ssh")
    def test_keychain_password_uses_stdin_not_command_arguments(
        self,
        run_ssh: mock.Mock,
        quiet: mock.Mock,
        _require: mock.Mock,
        parse: mock.Mock,
        _user: mock.Mock,
        _password: mock.Mock,
    ) -> None:
        parse.return_value = self.args()
        quiet.side_effect = [result(0, b"1000\n"), result(1)]
        run_ssh.return_value = result(0)

        self.assertEqual(ssh_sudo.main(), 0)
        call = run_ssh.call_args
        self.assertNotIn("not-a-real-password", call.args[1])
        self.assertEqual(call.kwargs["input_data"], b"not-a-real-password\n")


class KeychainTests(unittest.TestCase):
    def test_service_is_scoped_to_alias(self) -> None:
        self.assertEqual(sudo_keychain.service("nas"), "dev.ssh-hosts.sudo/nas")

    @mock.patch.object(sudo_credential.subprocess, "run")
    def test_store_passes_password_on_stdin_only(self, run: mock.Mock) -> None:
        run.return_value = result(0)

        sudo_credential.store("nas", "operator", "not-a-real-password", "Darwin")

        call = run.call_args
        self.assertNotIn("not-a-real-password", call.args[0])
        self.assertEqual(call.kwargs["input"], "not-a-real-password\nnot-a-real-password\n")


class CrossPlatformCredentialTests(unittest.TestCase):
    def test_backend_names_are_explicit(self) -> None:
        self.assertEqual(sudo_credential.backend_name("Darwin"), "macOS Keychain")
        self.assertEqual(sudo_credential.backend_name("Linux"), "Secret Service")
        self.assertEqual(sudo_credential.backend_name("Windows"), "Windows Credential Manager")

    def test_windows_target_is_scoped_to_alias_and_account(self) -> None:
        self.assertEqual(
            sudo_credential.windows_target("nas", "operator"),
            "dev.ssh-hosts.sudo/nas/operator",
        )

    @mock.patch.object(sudo_credential, "_secret_tool", return_value="/usr/bin/secret-tool")
    @mock.patch.object(sudo_credential.subprocess, "run")
    def test_linux_store_passes_password_on_stdin_only(
        self, run: mock.Mock, _tool: mock.Mock
    ) -> None:
        run.return_value = result(0)

        sudo_credential.store("nas", "operator", "not-a-real-password", "Linux")

        call = run.call_args
        self.assertNotIn("not-a-real-password", call.args[0])
        self.assertEqual(call.kwargs["input"], b"not-a-real-password\n")

    @mock.patch.object(sudo_credential, "_secret_tool", return_value="/usr/bin/secret-tool")
    @mock.patch.object(sudo_credential.subprocess, "run")
    def test_linux_lookup_returns_bytes(self, run: mock.Mock, _tool: mock.Mock) -> None:
        run.return_value = result(0, b"not-a-real-password\n")

        password = sudo_credential.read_password("nas", "operator", "Linux")

        self.assertEqual(password, b"not-a-real-password")
        self.assertEqual(run.call_args.args[0][1], "lookup")

    @mock.patch.object(sudo_credential.shutil, "which", return_value=None)
    def test_linux_reports_missing_secret_tool(self, _which: mock.Mock) -> None:
        self.assertIn("secret-tool is missing", sudo_credential.backend_problem("Linux") or "")


if __name__ == "__main__":
    unittest.main()
