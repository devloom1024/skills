# Devloom Skills

可复用的 agent 工作技能。

| Skill | 用途 |
|---|---|
| [project-docs](skills/project-docs/SKILL.md) | 建立、迁入和持续维护工程上下文：AGENTS 常驻工程规则、docs 与模块当前参考、外部 Agent Notes 接入 |
| [code-simplification](skills/code-simplification/SKILL.md) | 基于消费证据和净维护成本发现、评估并实施授权的代码简化 |
| [code-review](skills/code-review/SKILL.md) | 固定范围与版本，追踪行为路径，区分已证实缺陷、验证缺口与建议 |
| [project-workflow](skills/project-workflow/SKILL.md) | 按 workflow YAML 串联多个 Skill，以实际证据汇总结果 |

## project-docs 重写稿

当前规范版本为 `2026.11.07-draft.1`，待用户审阅，尚未进行本版行为评估。已有评估记录仅代表旧版本，本次没有重新运行检查器测试或项目样本。

方法来源于 [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) 的工程上下文实践，参考 [项目维护方式介绍](https://linux.do/t/topic/2904342) 和 [Agent Notes Skill 介绍](https://linux.do/t/topic/2874256)。目标是让新会话找到当前系统事实、既有约束和设计取舍，在改动中同步维护。

总体布局与职责连接见 [项目结构总则](skills/project-docs/references/standards/README.md)，各部分详细规范如下。

| 职责域 | 标准入口 |
|---|---|
| 根与子树 AGENTS.md | [全仓与局部常驻工程规则](skills/project-docs/references/standards/agents.md) |
| docs 与模块参考 | [文档总则、布局与专项规范](skills/project-docs/references/standards/docs/README.md) |
| Agent Notes | [外部 Skill 接入与信息连接](skills/project-docs/references/standards/notes.md) |

规范和场景分开：[初始化](skills/project-docs/references/scenarios/initialize.md) 建立最小体系；[迁移](skills/project-docs/references/scenarios/migrate.md) 核对、迁入和清理已有材料；[维护](skills/project-docs/references/scenarios/maintain.md) 同步后续变化、检查漂移与升级规则。声明版本不代表迁移完成，未处置内容保持部分采用状态。

Notes 的具体协议和专用工具统一使用外部 [write-notes-like-deepseek](https://github.com/czm15053/write-notes-like-deepseek/tree/main/skills/write-notes-like-deepseek)。本仓库已移除高度重叠的 decision-records Skill 及其专用测试；已有使用者应读取外部实际版本，按 [接入规范](skills/project-docs/references/standards/notes.md) 迁移规则与命令，不能假设安装后项目脚本已自动生效。本次未安装外部 Skill，也未迁移任何下游项目。

## 安装与使用

将需要的 `skills/<skill-name>` 放入当前 agent 支持的 Skill 搜索位置。project-docs 会自行探测上述外部 Notes Skill；缺失时询问用户选择项目或全局安装，选择后通过 `npx skills add` 自动安装并读取，无需用户手工执行。已可用则复用；用户可以暂不安装，此时明确 Notes 接入未完成，不生成本地替代协议。具体命令与失败处理见 [Notes 接入规范](skills/project-docs/references/standards/notes.md#自动安装命令)。

```text
使用 $project-docs，为这个空项目建立最小工程上下文。
使用 $project-docs，分析旧项目，输出目标结构和逐份迁移映射，只给方案。
使用 $project-docs，按统一标准完成文档迁移，保留有效事实和理由，修复全部受影响消费者并清理旧位置。
使用 $project-docs，根据本次开发结果更新受影响参考、行动入口和相关决定。
使用 $project-docs，只检查文档漂移，报告证据，不修改。
```

长期规则保存在目标项目自身指令中，基本阅读与事实维护无需每次重新调用本 Skill；专用 Notes 操作按已接入的外部能力执行。不把作者本机路径写入目标项目。

code-simplification 与 code-review 分别学习了 DeepSeek Harness 的简化调查和证据评审方法，仍可独立使用。project-workflow 要求当前环境具备 YAML 中实际列出的 Skill。

```text
使用 $code-simplification，只读调查当前模块的简化机会。
使用 $code-review，只读评审当前改动，报告已证实问题和验证范围。
```

串联任务可复制 [quality-maintenance.yml](skills/project-workflow/assets/workflows/quality-maintenance.yml) 到项目工作流目录，明确范围和授权后调用 project-workflow。示例依次简化、评审、同步文档，条件和失败处理见 [workflow 格式](skills/project-workflow/references/workflow-format.md)。Notes 需要发生实际操作时再遵循其依赖和协议。

## 工具与历史记录

Skill 安装内容在 `skills/`，开发测试与历史记录在 [tests](tests/)，临时材料在忽略的 `.cache/`。安装不需要复制 tests 或 .cache。

**文档检查能力须落到目标仓库。** 优先复用已有等效工具；否则将自带脚本接入项目，配置逐文件预算，纳入版本管理并提供本地入口；已有 CI 同时接入。来源记录、升级和检查边界见 [文档检查器](skills/project-docs/references/tools/check-docs.md)。

自带脚本是 Python 3.10+ 标准库工具，只覆盖一般 Markdown、必要入口与显式预算，Notes 专用规则交由外部工具。旧 `note_roots` 配置已移除，现有使用者需显式处理决策目录的外部验证范围。workflow 校验器另需 PyYAML 6，仅检查配置，不执行任务。

以下为可用命令说明，本版草稿尚未运行这些测试或行为评估：

```text
python skills/project-docs/scripts/check_docs.py <目标项目根目录> --json
python skills/project-docs/scripts/check_docs.py skills/project-docs --config ../../tests/project-docs/skill-doc-rules.json
python -B -m unittest discover -s tests/project-docs -p test_*.py -v
python skills/project-workflow/scripts/check_workflow.py skills/project-workflow/assets/workflows/quality-maintenance.yml --json
python -B -m unittest discover -s tests/project-workflow -p test_*.py -v
```

其他 Skill 的检查配置在各自 tests 目录。实际执行和行为评估待用户审阅草稿后决定，历史通过记录不能为本版背书。
