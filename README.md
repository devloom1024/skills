# Devloom Skills

可复用的 agent 工作技能。

| Skill | 用途 |
|---|---|
| [project-docs](skills/project-docs/SKILL.md) | 建立和维护项目文档分层、内容契约、Agent 指令、决策记录及 LESSONS 晋升机制 |
| [decision-records](skills/decision-records/SKILL.md) | 创建与治理项目决策记录，核对实施、取代与合并，封存归档并验证冻结历史 |
| [code-simplification](skills/code-simplification/SKILL.md) | 基于生产消费证据和净维护成本发现、评估并实施明确授权的代码简化 |
| [code-review](skills/code-review/SKILL.md) | 固定评审范围与版本，追踪完整行为路径，区分已证实缺陷、验证缺口与设计建议 |

`project-docs` 是对 [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) 文档组织、内容要求和维护经验的学习与总结，并参考 [Magpie](https://github.com/yetone/magpie) 的 LESSONS 机制。Skill 本身独立定义规范和流程，不依赖这些项目。

`code-simplification` 学习并提炼了 DeepSeek Harness 的简化审查方法，采用独立规范与案例，不依赖参考仓库。

`code-review` 学习并提炼了该项目的代码评审方法，将范围固定、语义审查和验证证据组织为独立流程，不带其框架专有规则。

## 使用

将需要的 `skills/<skill-name>` 目录放入所用 agent 支持的 Skill 搜索目录，然后请求：

```text
使用 $project-docs，分析当前代码和已有文档，建立项目文档组织与内容规范，保留现有用户约束。
使用 $project-docs，只审查当前文档，报告事实归属、内容缺口与验证证据。
```

Skill 自包含，不需要此仓库的 `.cache`。目标项目的长期规则保存在其自身文档中，不依赖每次重新调用 Skill。

四项 Skill 可分别安装。code-review 判断指定改动的正确性与回归；code-simplification 调查简化收益与代价；project-docs 建立文档规范并完成基本维护；decision-records 执行专项记录治理。它们都以目标项目自身约定为准，不要求其他 Skill 同时安装。

project-docs 默认用 `docs/standards/` 组织正式开发规范，领域防错属于其 `defensive-patterns/`，已有规范路径保留并映射。根 AGENTS 提供开发/评审的阅读入口；code-review 按改动和所审版本读取实际适用规范，区分强制要求、建议与历史提案。

```text
使用 $decision-records，审查本次改动涉及的决定，区分部分取代与实施完成，并在授权范围处理记录和引用。
使用 $code-simplification，只读评估当前模块的简化机会，给出消费证据、维护收益和保留理由，不修改代码。
使用 $code-review，只读评审当前暂存、未暂存和未跟踪改动，报告已证实缺陷、验证缺口与实际检查范围。
```

## 验证

检查器需要 Python 3.10+，仅用标准库。检查说明和范围见 [checker](skills/project-docs/references/checker.md)。

```text
python -m unittest discover -s skills/project-docs/tests -p test_*.py -v
python skills/project-docs/scripts/check_docs.py skills/project-docs --config tests/skill-doc-rules.json
python skills/project-docs/scripts/check_docs.py <目标项目根目录>
python -m unittest discover -s skills/decision-records/tests -p test_*.py -v
python skills/project-docs/scripts/check_docs.py skills/decision-records --config tests/skill-doc-rules.json
python skills/decision-records/scripts/archive_records.py verify <目标项目根目录> --json
python skills/project-docs/scripts/check_docs.py skills/code-simplification --config tests/skill-doc-rules.json
python skills/project-docs/scripts/check_docs.py skills/code-review --config tests/skill-doc-rules.json
```
