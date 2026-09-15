from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "ssh-hosts" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import ssh_hosts  # noqa: E402


class ExplicitAliasesTests(unittest.TestCase):
    @mock.patch.object(ssh_hosts.os, "name", "nt")
    def test_windows_config_keeps_backslashes_in_include_paths(self) -> None:
        self.assertEqual(
            ssh_hosts._words(r"Include C:\Users\operator\.ssh\conf.d\hosts.conf"),
            ["Include", r"C:\Users\operator\.ssh\conf.d\hosts.conf"],
        )

    def test_lists_only_concrete_host_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config"
            config.write_text(
                """
Host home-nas backup_1
    HostName 192.0.2.10
Host *
    ServerAliveInterval 30
Host *.internal !blocked.internal
    User operator
Host [legacy]
    User legacy
""".strip()
                + "\n",
                encoding="utf-8",
            )

            self.assertEqual(ssh_hosts.explicit_aliases(config), ("backup_1", "home-nas"))

    def test_follows_absolute_include_and_deduplicates_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            included = root / "included.conf"
            included.write_text("Host storage storage-backup\n", encoding="utf-8")
            config = root / "config"
            config.write_text(
                f"Include {included}\nHost storage\n",
                encoding="utf-8",
            )

            self.assertEqual(
                ssh_hosts.explicit_aliases(config),
                ("storage", "storage-backup"),
            )

    def test_require_alias_rejects_unregistered_host(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config"
            config.write_text("Host known-host\n", encoding="utf-8")

            self.assertEqual(ssh_hosts.require_alias("known-host", config), "known-host")
            with self.assertRaisesRegex(ValueError, "ssh.alias_not_registered"):
                ssh_hosts.require_alias("arbitrary.example", config)

    def test_rejects_invalid_alias_without_echoing_control_characters(self) -> None:
        with self.assertRaises(ValueError) as raised:
            ssh_hosts.require_alias("nas\nmisleading-output", Path("unused"))

        self.assertIn("ssh.alias_invalid", str(raised.exception))
        self.assertNotIn("misleading-output", str(raised.exception))


class InvocationTests(unittest.TestCase):
    @mock.patch.object(ssh_hosts.shutil, "which", return_value=None)
    def test_missing_openssh_has_stable_code_and_next_step(self, _which: mock.Mock) -> None:
        with self.assertRaises(RuntimeError) as raised:
            ssh_hosts.ssh_binary()

        self.assertIn("error: local.openssh_missing", str(raised.exception))
        self.assertIn("next: Install or enable OpenSSH Client", str(raised.exception))

    @mock.patch.object(ssh_hosts, "ssh_binary", return_value="/usr/bin/ssh")
    def test_connection_timeout_is_always_explicit(self, _binary: mock.Mock) -> None:
        command = ssh_hosts.ssh_invocation("nas", "true", 12)

        self.assertIn("BatchMode=yes", command)
        self.assertIn("ConnectTimeout=12", command)

    def test_invalid_connection_timeout_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least 1 second"):
            ssh_hosts.ssh_invocation("nas", "true", 0)


class DiagnosticTests(unittest.TestCase):
    def test_common_failures_have_distinct_stable_codes(self) -> None:
        cases = {
            b"connect to host nas port 22: Connection refused\n": "ssh.connection_refused",
            b"stdio forwarding failed\n": "ssh.proxy_jump_failed",
            b"Bad configuration option: madeup\n": "ssh.config_invalid",
            b"an unexpected OpenSSH failure\n": "ssh.connection_failed",
        }

        for stderr, expected_code in cases.items():
            with self.subTest(expected_code=expected_code):
                result = subprocess.CompletedProcess([], 255, stdout=b"", stderr=stderr)
                diagnostic = ssh_hosts.diagnose_ssh_failure("nas", result)
                self.assertEqual(diagnostic.code, expected_code)
                self.assertTrue(diagnostic.next_step.startswith("ssh "))


if __name__ == "__main__":
    unittest.main()
