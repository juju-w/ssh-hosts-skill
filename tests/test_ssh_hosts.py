from __future__ import annotations

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
            with self.assertRaisesRegex(ValueError, "unregistered SSH alias"):
                ssh_hosts.require_alias("arbitrary.example", config)


if __name__ == "__main__":
    unittest.main()
