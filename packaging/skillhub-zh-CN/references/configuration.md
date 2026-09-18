# 本地配置

## 已登记主机

本 Skill 只识别 `~/.ssh/config` 或 OpenSSH `Include` 引入文件中明确声明的 `Host` 别名。
包含 `*`、`?` 或 `!` 的模式不是资源。

示例：

```sshconfig
Host home-nas
    HostName 192.0.2.10
    User operator
    IdentityFile ~/.ssh/id_ed25519

Host production-api
    HostName api.internal.example
    User deploy
    ProxyJump company-bastion
```

真实地址应保存在用户的 SSH 配置中，不要写进 Skill 目录。

只列出明确别名，不显示地址：

```bash
python3 scripts/ssh_hosts.py list
```

## 可选的机器上下文

用户可在 `~/.config/ssh-hosts/hosts.md` 中保存私有、跨 Agent 使用的机器说明。该文件不会随
Skill 打包。保持简洁即可：

```markdown
# 主机

## home-nas
- 用途：家庭存储
- 环境：个人
- 注意：修改数据集前先只读排查磁盘空间

## production-api
- 用途：客户 API
- 环境：生产
- 注意：只有用户明确要求后才重启
```

只有用户要求记住长期事实，或明确同意刷新清单时，才更新此文件。不要保存密码、令牌、私钥
或恢复材料。

## 可选的跨平台 sudo 密码

sudo 辅助工具会按明确 SSH 别名和远程生效账号，在系统原生保险库中各保存一条凭据：

- service：`dev.ssh-hosts.sudo/<别名>`
- account：由 `ssh -G` 报告的远程生效用户

录入只能在用户自己的可信本地终端中完成，并关闭输入回显。Skill 和 Agent 不会在对话中接收
密码。macOS 使用钥匙串，Linux 使用 Secret Service，Windows 使用凭据管理器。若系统保险库
缺失或被锁定，应改用 root 账号、受限的非交互 sudo 规则，或用户平时的交互式管理流程。

先运行 `python3 scripts/setup_ssh_hosts.py --host <别名>`。如果 root、`NOPASSWD` 或已有的
系统保险库条目已经满足需要，它会明确提示无需继续配置。
