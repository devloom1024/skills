# Devloom Skills

面向 AI 编程助手的可复用 Skill，支持项目文档管理、代码简化、代码评审和工作流编排。

## Skills

| Skill | 介绍 |
| --- | --- |
| [project-docs](skills/project-docs/SKILL.md) | 用 AGENTS 常驻规则、docs 与模块参考、Agent Notes 管理工程上下文，覆盖空项目初始化、旧项目迁移和后续开发维护。Notes 使用外部 write-notes-like-deepseek Skill。 |
| [code-simplification](skills/code-simplification/SKILL.md) | 依据实际调用与维护成本识别简化机会，在授权范围内实施并验证。 |
| [code-review](skills/code-review/SKILL.md) | 评审指定范围的改动，报告有证据的缺陷、验证缺口与建议。 |
| [project-workflow](skills/project-workflow/SKILL.md) | 按 YAML 工作流串联多个 Skill，控制执行条件并汇总结果。 |

## 安装

通过 `npx skills` 安装，在交互中选择所需 Skill、agent 和安装范围：

```sh
npx skills add devloom1024/skills
```
