---
name: decision-records
description: Use when creating, reviewing, updating, completing, superseding, consolidating, rejecting, pruning, or archiving project decision records, ADRs, or Agent Notes. 适用于需要检查已有决定、实施证据、部分取代或冻结历史的任务；普通功能改动和一次性任务日志不自动触发全库治理。
---

# 决策记录治理

让当前决定、长期理由与冻结历史可以核对。先遵守目标项目自身规范，再按用户请求执行有限范围的治理；审查默认只读，不按年龄、篇幅或配额自动清理。

## 规则与范围

- 先读目标项目 AGENTS、决策 README/ADR 约定、受影响记录、源码、测试和入站引用。项目规范是实际权威，不依赖另一个 Skill 是否安装。
- 没有规范时按 [最小默认规范](references/standards.md) 建立项目内约定；已有 ADR 的路径、编号、状态和格式优先适配，不把 accepted 当作实现已验证。
- 只记录真实理由和考虑过的替代方案。证据不足明确留缺口，不凭字段、记录年代或名称猜测完成状态。
- 保存仍有指导价值的理由、负面保证、兼容约束和未完成范围。部分取代不能把整篇旧决定冻结或删除。
- 不自动提交、推送、建立定时任务或调整代码行为。没有用户授权的治理范围，不顺便清理全库。

## 按任务执行

先读 [治理流程](references/workflows.md)，再根据任务选择：

| 任务 | 关键判断与结果 |
|---|---|
| 新增或更新决定 | 搜索主题与替代方案，复用现有所有者；新决定说明补充/部分/全部取代关系 |
| 提案实施完成 | 对照代码与测试确认范围，路径、状态、当前正文和引用一起变更 |
| 审查或整理 | 逐条列当前价值、证据、处理理由；不默认修改 |
| 合并、拒绝或删除 | 先保存独特理由和未决缺口，修复活动引用；拒绝提案不进入归档 |
| 归档或冻结校验 | 再读 [归档流程与工具](references/archive.md)，先核对历史基准再封存 |

创建时可用 [记录模板](assets/templates/decision.md)，无项目规范时可用 [约定模板](assets/templates/notes-readme.md)。模板要按实际格式填写，不要求生成空状态目录。

## 归档命令

工具为 Python 3.10+ 标准库；Git 只用于可选的已提交清单基准。

```text
python <skill-dir>/scripts/archive_records.py verify <project-root> --json
python <skill-dir>/scripts/archive_records.py seal <project-root> --record .agents/notes/implemented/architecture/YYYY-MM-DD-topic.md --date YYYY-MM-DD --json
```

`verify` 只读；`seal` 只处理明确指定、符合格式且语义上已判定适合归档的记录，不自动判断取舍价值或修复引用。命令中的日期与路径必须替换为真实值。已有归档追加前需要覆盖当前清单的可信 Git 版本或显式快照。普通 hash 一致不能证明清单自身未被改写；报告 `protected_entries` 与基准来源。

工具写入只支持 Agent Note 的 implemented 头部。其他 ADR、附件、多语言配对或已有封存机制先遵守项目自己的格式和工具，不能强行改写来适配命令。无可信基准的历史档案不自动重新登记。

## 与项目文档协作

项目文档组织任务可由 project-docs 执行，但不要求它安装。记录的当前接口语义仍由项目参考文档拥有；本 Skill 处理理由与生命周期。两者都读同一份项目约定，专项操作完成后更新实际引用和必要导航，不在两个 Skill 各维护一套项目规则。

## 验收

报告处理范围、每项决定与证据、保留/新增/更新/拒绝/合并/归档/删除、修复的引用、运行的命令和未验证项。归档分别说明当前字节一致性、可信历史基准覆盖、语义判断和引用核查。失败后停止依赖工作，保留现场并报告实际文件状态，不把失败的重封存称为修复。
