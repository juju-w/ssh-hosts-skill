# 平台支持与安全边界

SSH Hosts 在 macOS、Linux 和 Windows 上遵循同一条路径：从 `~/.ssh/config` 解析明确别名，
先尝试普通权限；只有远程账号不是 root、非交互 sudo 不可用且任务确实需要提权时，才从调用端
系统原生保险库读取 sudo 密码。

## 支持矩阵

| 调用端平台 | SSH 客户端 | 可选 sudo 保险库 | 常见限制 |
| --- | --- | --- | --- |
| macOS | 系统 OpenSSH | macOS 钥匙串 | 钥匙串锁定时需要本机用户解锁 |
| Linux 桌面 | OpenSSH Client | Secret Service（`secret-tool`） | 可能缺少 libsecret 命令行工具或已解锁的登录钥匙环 |
| Linux 无桌面环境 | OpenSSH Client | 取决于用户 Secret Service | 通常缺少 D-Bus 和钥匙环，优先使用受限 `NOPASSWD` |
| Windows 10/11 | Windows OpenSSH Client | Windows 凭据管理器 | 可能需要启用 OpenSSH Client，且终端中必须能调用 Python |

远程账号是 root，或 `sudo -n -v` 成功时，不会使用系统保险库。

## 只读就绪检查

```bash
python3 scripts/setup_ssh_hosts.py
python3 scripts/setup_ssh_hosts.py --host <别名>
```

探针设置有限的 SSH 连接超时，并分类公钥认证、DNS、VPN 或网络可达性、主机密钥校验、连接
被拒绝、ProxyJump 转发和 OpenSSH 配置错误。每条诊断包含稳定错误码、通俗说明和最短可用的
下一步命令。

即使尚未提供 Python，Windows 用户也可以先运行只读 PowerShell 引导脚本：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup_ssh_hosts.ps1
```

它不会安装软件，只会报告 OpenSSH、SSH 配置或 Python 是否缺失。普通 `ssh.exe` 连接不依赖
Python；别名发现和系统保险库辅助工具需要 Python。

如果可信的便携版或嵌入式 Python 不在 PATH，可直接指定位置，无需安装第二份 Python 或修改
系统 PATH：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup_ssh_hosts.ps1 `
  -PythonPath "C:\path\to\python.exe"
```

## Linux

Linux 密码回退通过 `secret-tool` 使用 Freedesktop Secret Service。密码经 stdin 传递，不进入
进程参数。如果桌面钥匙环不可用、被锁定或未连接当前 D-Bus 会话，操作会明确失败，不会回退
到明文文件。

不同发行版的软件包名称不同；使用桌面钥匙环时，安装该发行版提供的 libsecret 命令行工具。
在无桌面服务器上，使用范围受限的 `NOPASSWD` 通常比专门为本 Skill 运行桌面钥匙环更合适。

## Windows

Windows 使用当前登录用户的凭据管理器。实现直接调用系统 Credential API，不需要第三方
PowerShell 模块，也不会把密码放入进程参数。缺少 Windows OpenSSH Client 时，可通过可选功能
或组织的系统策略启用。

发布前，`tests/windows_python_credential_smoke.py` 可在隔离的 Windows 机器上验证真实 Python
后端，`tests/windows_credential_smoke.ps1` 可直接检查系统 API。两者都会创建一条随机命名的
合成凭据，验证后立即删除，不读取或替换现有凭据。测试应在本地交互式用户会话中运行；OpenSSH
或 WinRM 会话可能不具备相同的凭据管理器登录上下文。

自动化实验室可通过一次性的、仅交互用户可运行的计划任务执行
`tests/windows_interactive_credential_smoke.ps1`。测试后删除任务、结果文件和临时目录；绝不在
生产用户会话中注册为持久任务。

## 凭据录入与删除

只有用户本人可以在可信本地终端中运行这些命令；Agent 不得代替用户输入密码：

```bash
python3 scripts/sudo_credential.py set <别名>
python3 scripts/sudo_credential.py status <别名>
python3 scripts/sudo_credential.py delete <别名>
```

旧的 `sudo_keychain.py` 继续作为 macOS 兼容入口；新配置统一使用 `sudo_credential.py`。

## 系统原生保险库能保护什么

系统保险库让密码不进入 Skill 文件、Shell 历史和进程参数，并把存储绑定到当前操作系统用户。
它不是独立的授权 Broker：以同一登录用户身份运行的恶意进程，仍可能滥用该用户已有的访问权。
如果需要每次操作都由系统认证、细粒度审批或更强的 Agent 隔离，应使用具备独立授权边界的运行时。
