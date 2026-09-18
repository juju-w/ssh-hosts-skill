# SkillHub 简体中文分发包

本目录保存 SkillHub/WorkBuddy 中文版本的可维护源文件。默认安装入口
`skills/ssh-hosts` 继续使用英文，方便 GitHub 和国际 Skill 市场收录；构建时复制默认 Skill，
再用本目录中的中文入口与参考文档覆盖对应文件。

## 构建

```bash
python3 packaging/skillhub-zh-CN/build.py /tmp/ssh-hosts-skillhub-zh-CN
```

输出目录是可直接交给 SkillHub CLI 的完整 Skill 包。构建过程会移除 PNG 图标，因为 SkillHub
目前不接受二进制附件；平台上已有的商店图标不受影响。

## 校验与发布

```bash
skillhub publish /tmp/ssh-hosts-skillhub-zh-CN --dry-run \
  --changelog "中文化 SkillHub/WorkBuddy 使用体验。"

skillhub publish /tmp/ssh-hosts-skillhub-zh-CN \
  --changelog "中文化 SkillHub/WorkBuddy 使用体验。"
```

发布新版本时，同时更新 `SKILL.md` 顶层和 `metadata.version` 中的版本号。不要在本目录保存
真实主机、用户名、密码、密钥、令牌或命令输出。
