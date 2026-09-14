# 常用示例

以下命令中的 `<alias>` 必须替换为用户 OpenSSH 配置里明确声明的 `Host` 别名。先从只读
操作开始；不要把主机地址、用户名、密码或私钥写入 Skill。

## 第一次使用

先运行一键自检。它不会修改配置，也不会读取密码：

```bash
python3 scripts/setup_ssh_hosts.py
```

列出已经登记的主机别名，不展示 IP 或其他连接细节：

```bash
python3 scripts/ssh_hosts.py list
```

检查 OpenSSH 能否以密钥方式连接：

```bash
ssh -o BatchMode=yes -- <alias> 'uname -a'
```

如果连接失败，检查 `ssh -G -- <alias>` 的有效配置，但不要输出私钥内容。

## 主机健康巡检

把紧密相关的只读检查放在一次 SSH 调用中，减少往返：

```bash
ssh -o BatchMode=yes -- <alias> \
  'uptime; printf "\n-- filesystems --\n"; df -h; printf "\n-- memory --\n"; free -h 2>/dev/null || true'
```

## Docker 状态

先直接使用当前远程账号；它可能已经属于 `docker` 组，不需要 sudo：

```bash
ssh -o BatchMode=yes -- <alias> \
  'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"'
```

只有返回权限不足时，才考虑 sudo 或调整远程账号权限。查看 Docker 服务状态属于只读操作：

```bash
python3 scripts/ssh_sudo.py \
  --host <alias> --allow-high-privilege -- \
  systemctl status docker
```

重启容器或 Docker 服务会中断业务，必须先获得用户确认。

## 查询日志

先尝试当前账号可读取的日志，并限制输出量：

```bash
ssh -o BatchMode=yes -- <alias> \
  'journalctl -u docker --since "30 minutes ago" --no-pager -n 200'
```

如果系统日志确实要求管理员权限，再通过 `ssh_sudo.py` 执行同一条限定范围的查询。

## 文件传输

使用 OpenSSH 自带的 `scp`，让 SSH 配置处理跳板机、Agent 和密钥：

```bash
scp -- ./local-file <alias>:/tmp/
scp -- <alias>:/tmp/remote-file ./
```

覆盖远程文件、写入系统目录或传输敏感数据前，先确认目标路径和影响。

## sudo 密码兜底

root 账号和 `NOPASSWD` sudo 在 macOS、Linux、Windows 调用端都可直接使用。只有确实必须
保存 sudo 密码时，才让用户在自己的可信终端执行统一入口：

```bash
python3 scripts/setup_ssh_hosts.py --host <alias>
python3 scripts/sudo_credential.py set <alias>
```

macOS 会使用钥匙串，Linux 会使用 Secret Service，Windows 会使用凭据管理器。不要在对话中
索要密码，也不要在原生保险柜不可用时创建明文密码文件。
