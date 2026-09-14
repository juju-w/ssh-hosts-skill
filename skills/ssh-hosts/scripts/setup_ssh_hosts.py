#!/usr/bin/env python3
"""Run a read-only readiness check and print the shortest safe next step."""

from __future__ import annotations

import argparse
import platform
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from ssh_hosts import DEFAULT_CONFIG, explicit_aliases, require_alias, ssh_binary
from sudo_credential import backend_name, backend_problem, exists, ssh_user


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SSH Hosts 一键环境自检（不会修改系统或读取密码）")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--host", help="可选：同时检查一个已登记主机的连接与 sudo 路径")
    return parser.parse_args()


def probe(alias: str, command: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [ssh_binary(), "-T", "-o", "BatchMode=yes", "--", alias, command],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def explain_ssh_failure(alias: str, result: subprocess.CompletedProcess[bytes]) -> str:
    stderr = result.stderr.decode(errors="replace").lower()
    if "permission denied" in stderr:
        return (
            f"{alias}: 密钥认证失败。先在本机运行 'ssh -v -- {alias}' 检查 IdentityFile、"
            "ssh-agent 和远端 authorized_keys；本 Skill 不会回退到密码登录。"
        )
    if "could not resolve hostname" in stderr:
        return f"{alias}: 无法解析主机。检查 HostName、VPN、DNS 或 ProxyJump 配置。"
    if "host key verification failed" in stderr:
        return f"{alias}: 主机指纹校验失败。请人工核对主机指纹，不要关闭 StrictHostKeyChecking。"
    if "connection refused" in stderr or "operation timed out" in stderr:
        return f"{alias}: SSH 服务不可达。检查网络/VPN、端口和远端 sshd 状态。"
    detail = result.stderr.decode(errors="replace").strip().splitlines()
    suffix = f" OpenSSH: {detail[-1]}" if detail else ""
    return f"{alias}: SSH 连接失败。可运行 'ssh -v -- {alias}' 查看握手过程。{suffix}"


def main() -> int:
    args = parse_args()
    try:
        executable = ssh_binary()
        aliases = explicit_aliases(args.config)
        print(f"系统: {platform.system() or 'unknown'}")
        print(f"OpenSSH: 可用 ({executable})")
        print(f"已登记主机: {len(aliases)} 个")
        if aliases:
            print("别名: " + ", ".join(aliases))
        else:
            print(
                f"下一步: 在 {args.config.expanduser()} 添加明确的 'Host <alias>' 配置，"
                "然后重新运行本命令。"
            )

        problem = backend_problem()
        if problem:
            print(f"sudo 密码保险柜: 暂不可用 ({backend_name()}: {problem})")
        else:
            print(f"sudo 密码保险柜: 可用 ({backend_name()})")

        if not args.host:
            if aliases:
                print("下一步: 使用 --host <alias> 检查连接与 sudo 是否已经就绪。")
            return 0

        alias = require_alias(args.host, args.config)
        identity = probe(alias, "id -u")
        if identity.returncode != 0:
            print(explain_ssh_failure(alias, identity), file=sys.stderr)
            return 1
        if identity.stdout.strip() == b"0":
            print(f"{alias}: 连接成功；远端账号是 root，无需保存 sudo 密码。")
            return 0

        nopasswd = probe(alias, "sudo -n -v")
        if nopasswd.returncode == 0:
            print(f"{alias}: 连接成功；已具备非交互 sudo，无需保存密码。")
            return 0

        account = ssh_user(alias)
        if problem:
            print(
                f"{alias}: 连接成功，但 sudo 需要密码且本机保险柜不可用。"
                "可配置范围受限的 NOPASSWD，或在可信终端中交互管理。"
            )
            return 1
        if exists(alias, account):
            print(f"{alias}: 连接成功；sudo 凭据已就绪 ({backend_name()})。")
            return 0
        print(f"{alias}: 连接成功；普通权限可用，sudo 密码尚未配置。")
        print(
            "如确实需要密码型 sudo，请只在你自己的可信终端运行: "
            f"python3 scripts/sudo_credential.py set {alias}"
        )
        return 1
    except (OSError, RuntimeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
