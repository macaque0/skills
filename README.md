# Team Codex Skills

团队共享 Codex skills 仓库。

## Skills

- `prompt-optimizer`：优化、结构化和修复提示词。
- `git-work-report`：根据 Git 提交记录生成工作报告。

## 安装

```bash
npx skills add https://github.com/macaque0/skills.git --skill prompt-optimizer
npx skills add https://github.com/macaque0/skills.git --skill git-work-report
```

## 目录结构

```text
skills/
  prompt-optimizer/
    SKILL.md
  git-work-report/
    SKILL.md
    references/
    scripts/
```

## 维护规则

- 不提交密钥、Token、账号口令或个人本机配置。
- 不提交 `__pycache__`、`.pyc`、临时输出和测试报告。
- 每个 skill 的核心说明写在自己的 `SKILL.md`。
