# Devloom Skills

可复用的 agent 工作技能。

| Skill | 用途 |
|---|---|
| [project-docs](skills/project-docs/SKILL.md) | 建立和维护项目文档分层、内容契约、Agent 指令、决策记录及 LESSONS 晋升机制 |
| [decision-records](skills/decision-records/SKILL.md) | 创建与治理项目决策记录，核对实施、取代与合并，封存归档并验证冻结历史 |

`project-docs` 是对 [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) 文档组织、内容要求和维护经验的学习与总结，并参考 [Magpie](https://github.com/yetone/magpie) 的 LESSONS 机制。Skill 本身独立定义规范和流程，不依赖这些项目。

## 使用

将 `skills/project-docs` 目录放入所用 agent 支持的 Skill 搜索目录，然后请求：

```text
使用 $project-docs，分析当前代码和已有文档，建立项目文档组织与内容规范，保留现有用户约束。
使用 $project-docs，只审查当前文档，报告事实归属、内容缺口与验证证据。
```

Skill 自包含，不需要此仓库的 `.cache`。目标项目的长期规则保存在其自身文档中，不依赖每次重新调用 Skill。

两项 Skill 可分别安装。project-docs 建立文档与决策规范并完成基本维护，decision-records 执行专项治理；两者都以目标项目自己的决策约定为准。

```text
使用 $decision-records，审查本次改动涉及的决定，区分部分取代与实施完成，并在授权范围处理记录和引用。
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
```
