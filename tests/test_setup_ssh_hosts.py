from __future__ import annotations

import contextlib
import io
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "ssh-hosts" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import setup_ssh_hosts  # noqa: E402


def result(returncode: int, stdout: bytes = b"", stderr: bytes = b"") -> subprocess.CompletedProcess[bytes]:
    return subprocess.CompletedProcess([], returncode, stdout=stdout, stderr=stderr)


class SetupTests(unittest.TestCase):
    def args(self, host: str | None = None) -> SimpleNamespace:
        return SimpleNamespace(config=Path("/tmp/ssh-config"), host=host)

    @mock.patch.object(setup_ssh_hosts, "backend_problem", return_value=None)
    @mock.patch.object(setup_ssh_hosts, "backend_name", return_value="test vault")
    @mock.patch.object(setup_ssh_hosts, "explicit_aliases", return_value=())
    @mock.patch.object(setup_ssh_hosts, "ssh_binary", return_value="/usr/bin/ssh")
    @mock.patch.object(setup_ssh_hosts, "parse_args")
    def test_no_aliases_prints_a_concrete_next_step(
        self,
        parse: mock.Mock,
        _ssh: mock.Mock,
        _aliases: mock.Mock,
        _backend_name: mock.Mock,
        _problem: mock.Mock,
    ) -> None:
        parse.return_value = self.args()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(setup_ssh_hosts.main(), 0)
        self.assertIn("Host <alias>", output.getvalue())

    @mock.patch.object(setup_ssh_hosts, "probe", return_value=result(0, b"0\n"))
    @mock.patch.object(setup_ssh_hosts, "require_alias", return_value="nas")
    @mock.patch.object(setup_ssh_hosts, "backend_problem", return_value=None)
    @mock.patch.object(setup_ssh_hosts, "backend_name", return_value="test vault")
    @mock.patch.object(setup_ssh_hosts, "explicit_aliases", return_value=("nas",))
    @mock.patch.object(setup_ssh_hosts, "ssh_binary", return_value="/usr/bin/ssh")
    @mock.patch.object(setup_ssh_hosts, "parse_args")
    def test_root_host_needs_no_credential(
        self,
        parse: mock.Mock,
        _ssh: mock.Mock,
        _aliases: mock.Mock,
        _backend_name: mock.Mock,
        _problem: mock.Mock,
        _require: mock.Mock,
        _probe: mock.Mock,
    ) -> None:
        parse.return_value = self.args("nas")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(setup_ssh_hosts.main(), 0)
        self.assertIn("root", output.getvalue())
        self.assertIn("无需保存 sudo 密码", output.getvalue())

    def test_permission_denied_has_key_diagnostics(self) -> None:
        message = setup_ssh_hosts.explain_ssh_failure(
            "nas", result(255, stderr=b"Permission denied (publickey).\n")
        )
        self.assertIn("IdentityFile", message)
        self.assertIn("authorized_keys", message)


if __name__ == "__main__":
    unittest.main()
