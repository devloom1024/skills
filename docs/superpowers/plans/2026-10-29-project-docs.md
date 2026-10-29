# project-docs 实施计划

> 执行方式：当前会话逐项完成；使用 writing-skills 要求的独立 agent 验证行为，不委派产品实现。

**目标：** 交付可独立分发、可验证的项目文档组织 Skill。

**架构：** 短入口按需加载职责、内容与维护规范，模板只负责起点，标准库脚本检查机械规则，agent 对照源码判断语义。

**技术：** Markdown、YAML 元数据、Python 3.10+ 标准库和 unittest。

**设计依据：** [中文设计](../specs/2026-10-29-project-docs-design.md)。

## 全局约束

- 保存于 `skills/project-docs/`，不修改全局 Skill 安装或创建 worktree。
- 文档默认中文，目标项目已有语言与用户指令优先。
- Skill 不依赖 `.cache`、上游项目或其他 Skill。
- 不编造事实，不批量创建空目录，不用模板覆盖现有用户规则。
- 检查器只读，Python 3.10+ 标准库，不联网、不执行文档命令。

## 任务一：独立基线与行为验收

文件：`skills/project-docs/tests/scenarios.md`、`tests/evaluation.md`；实际隔离样本位于忽略的 `.cache/project-docs-evaluation/`。

- [x] 创建含真实代码、已有约束和决策记录的隔离样本。
- [x] 无 Skill 执行文档整理请求，记录实际差异和缺漏，不预设一定失败。
- [x] 写出五个行为场景及可观察验收条件。
- [x] 有 Skill 后在新副本执行同类请求，核对产物、规则保留和内容归属。

## 任务二：规范、模板与入口

文件：`SKILL.md`、`references/*.md`、`assets/templates/*.md`、`agents/openai.yaml`。

- [x] 编写事实归属、每类文档内容契约、采用/迁移、维护、决策和经验规则。
- [x] 模板覆盖根/局部指令、架构、子系统、模块、开发、测试、教程、决策、复盘、经验和文档标准；按需复制并删除不适用内容。
- [x] 提供一致示例，展示跨文档链接和所有权，示例不作为真实项目事实复制。
- [x] 入口按请求选模式和参考，只触发必要范围。
- [x] 在仓库 README 添加 Skill 入口和运行方式。

## 任务三：检查器，先测后实现

文件：`scripts/check_docs.py`、`tests/test_check_docs.py`。

公开命令：`python skills/project-docs/scripts/check_docs.py <project-root> [--config <json>] [--json]`。

配置：相对根路径的 `required_files`、`exclude`、`note_roots`、`budgets`。预算项包含 `max` 和 `metric`，metric 为 `mixed` 或 `words`。

- [x] 用 subprocess 在临时目录执行 CLI；先断言脚本尚不存在，再实现可解析命令的最小程序。
- [x] 先写失败用例，再实现坏链接、引用式/图片链接、代码屏蔽、排除和读取错误处理。
- [x] 先写失败用例，再实现决策状态、归档提示、占位符、预算和配置校验。
- [x] 检查错误返回 1、配置或执行错误返回 2、只有提示返回 0；JSON 始终含 scope、findings、summary。
- [x] 执行 `python -m unittest discover -s skills/project-docs/tests -p test_*.py -v`，确认所有断言。

## 任务四：独立评估与交付核验

- [x] 独立 agent 使用完成的 Skill 执行场景，回传实际文件和验证结果。
- [x] 针对观察到的问题修改规范和用例，必要时重跑对应场景。
- [x] 执行系统 Skill 校验：`python C:/Users/huangkl/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/project-docs`。
- [x] 检查所有 Skill 资源链接；模板的占位符和占位链接由模板规则排除，不伪装成已填写产物。
- [x] 执行 `git diff --check` 和 `git status --short --branch`，报告通过项、未覆盖项和分发方式。
