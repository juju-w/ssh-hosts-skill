# 使用示例

把 `<别名>` 替换为用户 OpenSSH 配置中明确的 `Host` 别名。从只读操作开始。不要把主机地址、
用户名、密码或私钥写入 Skill。

## 快速任务导航

- 首次使用或连接失败：运行下方就绪检查。
- 主机健康巡检：把少量紧密相关的只读检查合并到一次 SSH 调用。
- Docker 或日志：先尝试登记账号；只有权限不足时才考虑 sudo。
- 文件传输：复制前确认来源、目标和覆盖风险。
- 需要密码的 sudo：让用户在可信终端中录入系统原生保险库。

## 首次使用

运行只读就绪检查。它不会修改配置，也不会读取密码：

```bash
python3 scripts/setup_ssh_hosts.py
```

成功时的典型输出：

```text
system: Darwin
openssh: available (/usr/bin/ssh)
registered_hosts: 2
aliases: home-nas, production-api
sudo_vault: available (macOS Keychain)
status: ready
next: Use --host <alias> to check SSH and sudo readiness.
```

只列出登记别名，不暴露地址：

```bash
python3 scripts/ssh_hosts.py list
```

检查 OpenSSH 能否使用公钥认证连接：

```bash
ssh -o BatchMode=yes -o ConnectTimeout=10 -- <别名> 'uname -a'
```

认证失败时，就绪检查会返回稳定的错误分类和可直接执行的下一步：

```text
error: ssh.authentication_failed
host: home-nas
message: Public-key authentication was rejected.
next: ssh -v -- home-nas
hint: Check IdentityFile, ssh-agent, and the remote authorized_keys file. Password login is not used.
```

使用 `ssh -G -- <别名>` 检查生效配置。不要输出私钥内容。

## 主机健康巡检

合并紧密相关的只读检查以减少网络往返：

```bash
ssh -o BatchMode=yes -o ConnectTimeout=10 -- <别名> \
  'uptime; printf "\n-- filesystems --\n"; df -h; printf "\n-- memory --\n"; free -h 2>/dev/null || true'
```

## Docker 状态

先用登记账号尝试；该账号可能已经属于 `docker` 用户组：

```bash
ssh -o BatchMode=yes -o ConnectTimeout=10 -- <别名> \
  'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"'
```

只有出现权限错误后，才考虑 sudo 或更换远程账号。读取 Docker 服务状态不会修改系统：

```bash
python3 scripts/ssh_sudo.py \
  --host <别名> --allow-high-privilege -- \
  systemctl status docker
```

重启容器或 Docker 服务可能中断业务，必须先确认。

## 日志

先读取登记账号有权访问的日志，并限制输出量：

```bash
ssh -o BatchMode=yes -o ConnectTimeout=10 -- <别名> \
  'journalctl -u docker --since "30 minutes ago" --no-pager -n 200'
```

只有同一条有限日志查询确实需要管理员权限时，才通过 `ssh_sudo.py` 执行。

## 文件传输

使用 OpenSSH `scp`，让跳板机、Agent 和密钥继续由 SSH 配置处理：

```bash
scp -- ./local-file <别名>:/tmp/
scp -- <别名>:/tmp/remote-file ./
```

覆盖远程文件、写入系统目录或传输敏感数据前，确认目标位置和影响。

## sudo 密码回退

root 账号和 `NOPASSWD` sudo 在所有调用端平台都无需保存密码。只有确实需要密码 sudo 时，
才让用户运行：

```bash
python3 scripts/setup_ssh_hosts.py --host <别名>
python3 scripts/sudo_credential.py set <别名>
```

macOS 使用钥匙串，Linux 使用 Secret Service，Windows 使用凭据管理器。绝不在对话中索要
密码；系统保险库不可用时也不要创建明文回退。
