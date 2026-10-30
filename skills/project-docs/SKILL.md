---
name: project-docs
description: Use when a project needs agent-facing documentation organization, AGENTS.md guidance, document content standards, documentation migration or audit, decision-record lifecycle maintenance, or an evidence-based LESSONS.md process. 不用于仅润色文字、普通功能开发或与项目文档组织无关的文件操作。
---

# 项目文档组织与内容规范

建立清晰的文档职责、内容契约和维护流程，通过有证据的 LESSONS 持续改进项目规范。成功是 agent 能找到当前事实、正确修改项目并验证结果；目录齐全或标题齐全不足以证明完成。

## 范围与不可省略的约束

- 保留用户约束、已有事实、文档语言、工具链和有效引用。先读目标项目实际生效的指令，不能用模板覆盖。
- 先查源码、构建配置、测试和已有文档，再写项目事实。命令未运行、实现不存在、证据不足，分别如实报告，不能补成已验证能力。
- 按实际信息创建文档。空项目只建立最小入口、文档标准和必要的经验记录；不生成虚构架构、假替代方案或空目录。
- 一项事实只有一个维护位置。跨文档只保留导航和必要摘要；上层解释直接子层职责，不复制其细节。
- Skill 自包含；不要求目标项目安装另一个 Skill、克隆额外仓库、连接特定服务或自动提交。

## 选择流程

所有模式先读 [组织规则](references/document-ownership.md)；初始化、迁移、目录审查、新增页面或改变分组时读 [目录内部组织](references/directory-layout.md)；准备写哪类文档，再读 [对应内容契约](references/content-contracts.md)。

| 用户任务 | 再读 | 输出范围 |
|---|---|---|
| 新项目建立规范 | [采用与迁移](references/adoption.md) | 最小入口、可持续执行的项目规则、当前有依据的文档 |
| 整理现有文档 | [采用与迁移](references/adoption.md) | 归属映射、迁移、引用修复；保留用户规则 |
| 同步变更、处理设计或教训 | [维护](references/maintenance.md)，涉及时读 [决策](references/decision-records.md) / [LESSONS](references/lessons.md) | 仅更新受影响的所有者和引用 |
| 检查文档质量 | [维护](references/maintenance.md) | 默认只读，逐项给证据、影响和修复建议 |
| 提炼或维护开发教程 | [Cookbook 编写流程](references/cookbook-authoring.md) | 从真实任务核对前提、步骤、验证和持续维护 |

普通功能开发不触发全仓文档重组。需要示范深度时读 [一致示例](references/examples.md)，仅复制适用的 [模板](assets/templates/)，填写事实并删除不适用部分。

整理项目开发规范时，默认由 `docs/standards/` 拥有已采纳的工程要求，领域防错要求放其 `defensive-patterns/` 子目录；已有 conventions、独立防错目录等保留并映射。按 [目录契约](references/directory-layout.md) 和 [规范内容契约](references/content-contracts.md#项目开发规范) 建立任务导航、规则等级和判断依据，不凭模板创造标准。

## 与决策专项治理协作

本 Skill 定义文档体系、决策内容与格式要求，并把实际规则写入目标项目。创建前查重、维护单条决定、确认实施范围等基本操作见 [决策规范](references/decision-records.md)，不依赖另一个 Skill 安装。

独立的 decision-records 可在可用时执行取代分析、合并清理和冻结归档等专项流程。两者先读同一份目标项目决策约定，不各自覆盖项目规则。缺少专项工具时仍可完成规范初始化和基本维护；复杂冻结操作若没有可验证机制，报告缺口而不声称已完成。

## 执行

1. 确认目标根目录、请求模式和授权范围。盘点入口、文档、代码归属、真实命令和既有决策格式。
2. 按事实归属和目录契约确定必要文件、名称、层级、入口与资源位置。迁移前列出旧路径到新所有者的映射；保留已有 ADR 和稳定网站入口，明确适配。
3. 对照内容契约写入或审查：明确条件、默认值、失败、所有权、生命周期、兼容性和限制中适用的内容。未知信息写入交付缺口，不留下假装完成的占位内容。
4. 实施初始化/整理时，把长期文档维护规则、实际采用的命名/分组/导航/资源约定写入目标 `AGENTS.md` / `docs/AGENTS.md` 或其项目内所有者，使后续会话无需再次调用本 Skill 也能遵守。根 AGENTS 按开发/评审任务指向工程与领域规范；docs/AGENTS 负责文档编写，不将其子树约束自动扩张到源码。全仓根指令只保存常驻要求；领域细则放所属文档。
5. 修复实际受影响的引用。决策移到 implemented 时改成当前决定；LESSONS 晋升后完整规则只保留在正式规范。
6. 运行机械检查，再按源码和实际操作核对语义。未运行的命令、未检查的外链/锚点、无法确认的实现分别说明。

## 验收与机械检查

运行 Skill 自带脚本，使用可用的 Python 3.10+ 启动器；`<skill-dir>` 是此 Skill 所在目录，`<project-root>` 是目标项目，不要写入产物中的本机路径。

```text
python <skill-dir>/scripts/check_docs.py <project-root>
python <skill-dir>/scripts/check_docs.py <project-root> --config docs/doc-rules.json --json
```

配置与覆盖范围见 [检查器说明](references/checker.md)。脚本只读，不联网、不执行文档命令；通过只表示被覆盖的机械规则合格。检查前声明排除范围，不能通过排除出错文档隐藏问题。

交付说明：变更文件及归属、保留的项目约定、事实核对依据、执行的命令和结果、未验证项及下一步。审查给出具体文件位置；发现无源码可核对时明确标为缺口。再次执行应复用已有所有者，不反复生成相同文档。

## 常见误用

- 只生成目录和标题：按内容契约检查读者能否做出所需决定。
- 把所有规范和教训堆进根 AGENTS：领域规则放所属规范，只留下必读导航。
- 将已实施记录当作未完成计划：更新路径、状态和正文，保留真实取舍。
- 为满足模板编造内容：删掉不适用项，报告未知事实。
- 把脚本通过说成文档与代码一致：单独提供源码核对和执行证据。
