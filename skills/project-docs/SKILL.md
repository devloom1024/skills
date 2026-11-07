---
name: project-docs
description: Use when establishing engineering documentation for an empty project, migrating an existing documentation tree into a unified standard, or updating an adopted project's instructions and documentation after development. Covers root/subtree AGENTS.md, docs and module references, and integration with the external write-notes-like-deepseek Skill for Agent Notes. Also use for scoped documentation audits and maintenance. 不用于仅润色文字，也不因普通功能任务自动重组全仓。
---

# 项目工程上下文

规范版本：2026.11.07-draft.1。此版本是待用户审阅的重写稿，尚未进行行为评估。

让没有历史对话的人和 agent 能找到当前事实、理解既有约束与被否决方案，正确修改项目，并同步维护这些信息。目录、标题、版本声明或检查器通过都不足以证明采用完成。

## 规范入口

先读 [项目结构总则](references/standards/README.md)，理解 AGENTS、docs 与模块参考、Notes 的位置、职责和连接，再进入相关详细规范。

## 按项目状态选择场景

| 实际状态 | 执行流程 | 完成结果 |
|---|---|---|
| 没有成体系文档，或尚无实现 | [初始化](references/scenarios/initialize.md) | 最小行动入口、项目内规则与按需增长方式 |
| 已有文档尚未符合本规范，或采用中仍有旧材料 | [迁移](references/scenarios/migrate.md) | 有效信息迁入、消费者修复、旧位置完成处置 |
| 已完成采用，需要随开发更新或检查漂移 | [维护](references/scenarios/maintain.md) | 本次影响范围内的规则、事实、决定与实现一致 |

不能只因项目写了基线版本就选维护。核对实际归属与旧树处置；部分采用仍按迁移处理未完成范围。普通开发只维护受影响所有者，不自动重组全仓。

只要求分析时输出目标结构、迁移映射或维护建议；授权实施时完成对应流程。遵守用户本轮和此前有效授权，不另设强制审批、提交或发布流程。未解决且影响实施的真实选择集中提出，环境里查得到的事实先自行查明。

## 开始工作

1. 确认项目根目录、范围和用户限制。读取实际生效的 `AGENTS.md`、兼容指令、入口、相关实现、配置、测试与现有决定。
2. 读取项目结构总则、相关职责规范和选定场景。涉及 docs 时先读文档总则，再只读本次适用的专项规范。检查外部 Notes Skill 是否可用；缺失时按接入规范询问安装范围，并在用户选择后自动安装。
3. 确定信息所有者与读取路径。当前事实核对源码和实际消费者；旧文档提供线索，不自动代表现状。命令未运行、实现未完成与证据不足分别说明。
4. 执行场景流程，按 [检查器接入](references/tools/check-docs.md) 落实项目内工具、文件预算与本地/CI 入口。项目规则保留用户有效要求；语言沿用明确约定，无约定时沿用现有正文语言。Notes 的协议和语言按外部规范及用户要求处理。
5. 在授权范围内执行适用检查，报告未执行部分。用户只要求草稿或明确不评估时，交付草稿和未验证范围，不擅自开展行为评估。

## 外部 Notes 依赖

使用 [write-notes-like-deepseek](https://github.com/czm15053/write-notes-like-deepseek/tree/main/skills/write-notes-like-deepseek)。由本 Skill 负责探测依赖；已可用则复用，缺失则询问用户选择「项目安装」或「全局安装」，选择后自动通过 `npx skills add` 完成安装并确认可用，无需再询问是否执行同一次安装。用户也可以暂不安装；未回复不视为已选择安装范围。先读取实际可用版本的 `SKILL.md` 与相关参考；不在本 Skill 重建其格式、分类、生命周期、模板或校验器。

在 Notes 职责范围内与本地旧定义冲突时采用外部 Skill，并清除本地竞争定义；用户直接要求和实际生效的项目指令仍按其优先级处理，冲突未解决时不能悄悄改写。具体接入、版本记录和缺失处理见 [Notes 规范](references/standards/notes.md)。不默认启用外部的看板或额外审批流程。

## 交付与采用状态

交付说明：所选场景、实际范围、三个职责域的变更及连接、迁移处置与例外、Notes 来源和可用性、核对依据、实际命令结果、未验证项与遗留工作。

采用状态明确为未采用、部分采用或已采用；存在未处置旧材料、未接通的重要阅读路径、未落实的预算与检查入口或必要 Notes 操作无法完成时，**不标记全量采用完成**。基线记录在项目内，用于后续核对差异，不代替验收。

**检查能力交付到目标仓库，优先复用已有等效工具。** 使用本 Skill 脚本时，接入后从项目根运行：

```text
python3 scripts/check-docs.py . --config docs/doc-rules.json --json
```

项目使用实际接入路径；脚本、配置与入口纳入版本管理，临时检查可直接用 Skill 自带脚本。配置、接入和升级见 [文档检查器](references/tools/check-docs.md)，内容核对见 [文档总则](references/standards/docs/README.md#同步与核对)。Notes 专用检查由外部工具执行。**机械通过不代表语义、运行或整个体系已经验证。**
