# SSH Hosts

[English](README.md) | [简体中文](README.zh-CN.md)

[![skills.sh](https://skills.sh/b/juju-w/ssh-hosts-skill)](https://skills.sh/juju-w/ssh-hosts-skill)

安全、可审计、跨平台的 SSH 主机管理 Agent Skill。它只接受用户 OpenSSH 配置中明确声明的
`Host` 别名，优先使用普通权限，并且只在确有需要时使用 sudo。

## 为什么使用

- 只允许明确配置的 SSH 别名，拒绝任意主机名和 IP 地址。
- 强制使用 `BatchMode=yes`，不会悄悄退回到 SSH 密码登录。
- root 账户和限定范围的 `NOPASSWD` 无需保存凭据。
- 可选的 sudo 凭据存入 macOS 钥匙串、Linux Secret Service 或 Windows 凭据管理器，绝不写入明文文件。
- 密码只通过标准输入传递，不进入命令参数或 Shell 历史。
- 默认先做只读诊断，中断服务或修改系统前必须确认。

## 安装

使用开源的 `skills` CLI 安装：

```bash
npx skills add juju-w/ssh-hosts-skill
```

也可以克隆仓库，再把 `skills/ssh-hosts` 复制到 Agent 使用的 Skill 目录。

## 首次使用

确认 `~/.ssh/config` 中至少存在一个明确的别名：

```sshconfig
Host home-nas
    HostName 192.0.2.10
    User operator
    IdentityFile ~/.ssh/id_ed25519
```

在仓库工作副本中运行只读自检：

```bash
python3 skills/ssh-hosts/scripts/setup_ssh_hosts.py
python3 skills/ssh-hosts/scripts/setup_ssh_hosts.py --host home-nas
```

Windows 用户可以使用 PowerShell 启动脚本。使用内嵌或便携 Python 时，可以显式指定可信的
Python 路径：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File skills/ssh-hosts/scripts/setup_ssh_hosts.ps1

powershell -NoProfile -ExecutionPolicy Bypass -File skills/ssh-hosts/scripts/setup_ssh_hosts.ps1 `
  -PythonPath "C:\path\to\python.exe"
```

自检不会修改 SSH 配置、安装软件或读取密码。

## 可选的 sudo 凭据

先让辅助脚本判断远端账户是否为 root 或已经支持 `NOPASSWD`。只有确实需要密码 sudo 时，才在
用户自己的可信终端中执行：

```bash
python3 skills/ssh-hosts/scripts/sudo_credential.py set home-nas
```

不要通过 Agent 对话发送 sudo 密码。

## 平台支持

| 调用端平台 | SSH | 可选 sudo 保险柜 |
| --- | --- | --- |
| macOS | 系统 OpenSSH | macOS 钥匙串 |
| Linux 桌面 | OpenSSH Client | Secret Service（`secret-tool`） |
| Linux 无桌面服务器 | OpenSSH Client | 推荐 root 或限定范围的 `NOPASSWD` |
| Windows 10/11 | Windows OpenSSH Client | Windows 凭据管理器 |

参阅[平台说明](skills/ssh-hosts/references/platforms.md)和
[使用示例](skills/ssh-hosts/references/examples.md)。

## 故障诊断

自检和 sudo 辅助脚本设置了有限的 SSH 连接超时，并使用 `error`、`message`、`next`、`hint`
等稳定字段输出结果。它能区分密钥认证、DNS、网络不可达、主机指纹、连接被拒绝、ProxyJump
以及 OpenSSH 配置错误。实际输出参阅[使用示例](skills/ssh-hosts/references/examples.md#first-use)。

遇到问题时先运行 `setup_ssh_hosts.py --host <alias>`，不要猜测 SSH 参数。`next` 字段给出可在
本地终端执行的最短排查命令，`hint` 字段解释应检查什么以及哪些安全校验不能绕过。

## 测试

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q skills/ssh-hosts/scripts tests
```

测试套件会在 macOS、Linux 和 Windows 上运行。凭据保险柜冒烟测试只使用随机生成的合成数据，
并在测试结束后立即删除。

## 安全

报告安全问题前请阅读 [SECURITY.md](SECURITY.md)。Issue 中不要包含真实主机、用户名、密钥、
密码、Token 或命令输出。

## 许可证

[MIT-0](LICENSE)
