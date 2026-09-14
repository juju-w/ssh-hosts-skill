# 平台适配与安全边界

SSH Hosts 在三个桌面平台上保持同一条使用路径：先读取 `~/.ssh/config` 中明确登记的别名，
优先用普通权限；只有远端既不是 root、也没有非交互 sudo，而且任务确实需要提权时，才读取
本机原生保险柜里的 sudo 密码。

## 支持矩阵

| 调用端系统 | SSH 客户端 | 可选 sudo 密码保险柜 | 常见缺口 |
| --- | --- | --- | --- |
| macOS | 系统 OpenSSH | macOS Keychain | 通常开箱即用；钥匙串锁定时需要本机用户解锁 |
| Linux 桌面 | OpenSSH Client | Secret Service（`secret-tool`） | 发行版可能没装 libsecret 工具，或登录钥匙环未解锁 |
| Linux 服务器/无桌面 | OpenSSH Client | 取决于是否部署用户 Secret Service | 常常没有 D-Bus 会话和钥匙环；建议范围受限的 `NOPASSWD` |
| Windows 10/11 | Windows OpenSSH Client | Windows Credential Manager | OpenSSH Client 可能尚未启用；Python 需可从终端调用 |

如果远端账号是 root，或 `sudo -n -v` 已成功，以上保险柜都不会被使用。

## 一键自检

```bash
python3 scripts/setup_ssh_hosts.py
python3 scripts/setup_ssh_hosts.py --host <alias>
```

Windows 用户即使尚未安装 Python，也可以先运行只读 PowerShell 引导：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup_ssh_hosts.ps1
```

它不会自动安装软件，只会明确说明 OpenSSH、SSH 配置或 Python 缺少哪一项。普通 `ssh.exe`
连接不依赖 Python；别名解析和 sudo 保险柜辅助脚本需要 Python 3。

如果 Python 来自便携环境或其他受信任工具、没有加入 PATH，可以显式指定解释器，不必安装
第二份 Python 或修改系统 PATH：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup_ssh_hosts.ps1 `
  -PythonPath "C:\path\to\python.exe"
```

自检只读取本机环境和远端权限状态，不会保存密码、修改 SSH 配置或执行管理操作。它会给出
最短的下一步，例如添加明确的 `Host` 别名、修复密钥认证、启用 OpenSSH Client、安装
`secret-tool`，或在可信终端登记 sudo 凭据。

## Linux

Linux 密码兜底使用 Freedesktop Secret Service，通过 `secret-tool` 查找、保存和删除条目。
密码只通过标准输入传给工具，不进入命令参数。桌面钥匙环不可用、未解锁或当前会话没有
D-Bus 时，操作会明确失败，不会降级为明文文件。

不同发行版的软件包名称不同，请使用发行版提供的 libsecret 命令行工具包。无桌面服务器
更适合为确实需要的命令配置范围受限的 `NOPASSWD`，而不是为了本 Skill 额外运行一套桌面
钥匙环。

## Windows

Windows 使用当前登录用户的 Credential Manager。实现直接调用系统 Credential API，不需要
安装第三方 PowerShell 模块，也不会把密码放进命令参数。OpenSSH Client 若不可用，请先通过
Windows 的可选功能或系统管理策略启用。

发布前可在一台隔离的 Windows 测试机运行 `tests/windows_python_credential_smoke.py` 验证实际
Python 后端，或运行 `tests/windows_credential_smoke.ps1` 单独验证系统 API。两者都只写入一个
随机命名、随机内容的合成条目，完成读回校验后立即删除，不读取或覆盖任何现有凭据。测试必须
由目标用户在 Windows 本地交互登录会话中运行；OpenSSH 或 WinRM 远程会话可能没有可用的用户
Credential Manager 登录上下文，因此远程写入失败不能证明本地实现不可用。

自动化实验室可以在一个已登录的隔离 Windows 用户会话中，通过一次性“仅交互用户”计划任务
调用 `tests/windows_interactive_credential_smoke.ps1`。测试后必须删除计划任务、结果文件和
临时目录；不要在生产用户会话中把该测试注册为常驻任务。

## 凭据登记与删除

这些命令只能由用户在自己的可信本地终端运行；Agent 不应代替用户输入密码：

```bash
python3 scripts/sudo_credential.py set <alias>
python3 scripts/sudo_credential.py status <alias>
python3 scripts/sudo_credential.py delete <alias>
```

原来的 `sudo_keychain.py` 在 macOS 上继续保留为兼容入口，新配置统一使用
`sudo_credential.py`。

## 保险柜能保护什么

原生保险柜避免密码出现在 Skill 文件、Shell 历史和进程参数中，也把存储绑定到当前操作系统
用户。但它不是隔离 Broker：同一登录用户下的恶意进程仍可能滥用用户已有的访问能力。需要
逐次系统认证、细粒度审批或更强 Agent 隔离时，应使用具备独立授权边界的运行时，而不是在
这个轻量 Skill 里保存长期管理员密码。
