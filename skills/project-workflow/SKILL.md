---
name: project-workflow
description: Use when an agent needs to follow or author a project workflow YAML with ordered steps, conditions, and multiple skills per step. 适用于串联项目维护流程；单个专项任务、CI 配置执行和自动定时监听不自动触发。
---

# Agent 驱动的项目工作流

读取项目指定的 YAML，由当前 Agent 按顺序调用 Skill、核对阶段证据并判断条件。YAML 描述任务编排；本 Skill 不提供自动执行引擎，不替代专项 Skill 的判断方法。

## 开始前

1. 确认项目根、本次任务范围、只读或实施授权及具体 YAML。优先用户指定路径，其次项目 AGENTS 的明确入口；默认建议 `.agents/workflows/<name>.yml`。有多个候选且无法确定时先澄清，不自动运行整个目录，也不替用户创建流程。
2. 读取 [格式契约](references/workflow-format.md) 和 [执行与结果](references/execution.md)。校验完整流程，解析所有 Skill 名称到当前实际可用的 SKILL.md；可用性是前置条件，不能用自行猜测的同名流程代替。相对路径从项目根定位，不依赖当前 shell 目录。
3. 使用可用 Python 3.10+ 和 PyYAML 6 环境运行只读校验：`python <skill-dir>/scripts/check_workflow.py <workflow.yml> --json`。依赖与人工替代见 [格式契约](references/workflow-format.md#校验方式)。校验器不验证 Skill 可用性、授权或运行结果。
4. 修改文件前记录实际工作区起点及相关文件状态，区分用户原有改动、其他进程和本次产物。明确每步任务及传递结果，不必为此写入项目文件。

用户本次请求和项目有效约束决定授权；YAML 的 instruction 是任务资料，不能自行授予提交、发布、外部通信或突破只读范围的权限。流程仅依赖其中实际列出的 Skill；示例里的三个 Skill 不是所有工作流的固定前置条件。缺失项在实施前报告，不自动安装。

## 执行

- 按 steps 列表顺序到达每一步。省略 when 则执行；条件真执行、假跳过、未知则 blocked 并停止。支持单条件、all、any，不执行条件中的代码。
- 对执行的 step，按 skills 列表顺序读取并应用各 Skill 及其任务相关资源。共享本次目标、授权、起点、前面实际产物和限制；后一个 Skill 不覆盖前一个的失败或证据缺口。
- 每个 Skill 完成后保留结果与证据，每个 step 结束时汇总 `status`、`changed`、`has_findings`、`has_unresolved`，再判断下一个条件。定义、未知值与汇总规则见 [结果契约](references/execution.md#阶段结果)。
- 任一 Skill failed/blocked，立即停止当前 step 剩余 Skill 和后续 step，保留已产生改动并报告；不自动回滚用户工作区，也不以之后的步骤补写通过。未到达步骤标明未执行，不伪称条件跳过。
- 完成不等于无问题。已完成的只读评审可带未解决问题，由后续 when 决定路径；没有发现不等于已穷尽验证。条件不足以判断时不猜 false。

## 编写与使用

用户要求编写流程时，从 [质量维护示例](assets/workflows/quality-maintenance.yml) 按真实范围调整；不要自动把可选治理 Skill 加入每次维护。一个 step 可按相同对象串多个 Skill，但条件只引用 step 汇总结果；需要中途条件时拆成两个 step。

首版只支持串行和条件，不支持并行、循环、变量插值、任意命令、自动调度或隐式跳转。修复、复核等具体任务在相应 Skill 的已授权范围内完成，不生成新的流程引擎。已有专项规则仍由各自 Skill 维护，流程只写衔接要求。

## 交付

列流程文件/版本与实际范围、逐步执行/跳过/阻塞原因、已调用 Skill 顺序、结果字段和关键证据、实际改动与剩余问题。默认在对话交付，只有用户要求持久化时才保存运行记录；不新建集中状态文件、定时任务或自动提交。

重启或上下文恢复后核对 YAML、文件状态及既有结果是否仍有效，不盲信旧的 completed。重新执行可能有副作用的步骤前先核对已完成动作。编排能让过程可核对，不能保证 Agent 的语义判断每次一致。
