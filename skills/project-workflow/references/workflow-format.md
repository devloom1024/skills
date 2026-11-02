# Workflow YAML 格式契约

格式版本 1。文档只声明编排，由 Agent 执行；[执行契约](execution.md) 定义结果和控制行为，校验器不运行流程。

## 文件与字段

默认建议项目内 `.agents/workflows/<name>.yml`，已有路径保留，也接受 `.yaml`。根 AGENTS 可链接具体文件并说明用途。支持 UTF-8（可含 BOM）单个 YAML 文档，使用标准映射、列表、文本、整数和 true/false；不使用锚点、别名、合并键、显式类型标签或多文档。重复键会被拒绝，避免不同解析器选择不同值。为可读性保持浅层；校验器限制文件不超过 1 MiB，条件最多 8 层。

| 位置 | 字段 | 要求 |
|---|---|---|
| 根 | version | 必须是整数 1，不是字符串或布尔值 |
| 根 | name | 必需，`[a-z][a-z0-9_-]*` 标识 |
| 根 | description | 可选，非空说明 |
| 根 | steps | 必需，非空有序列表 |
| step | id | 必需，遵守 name 的标识规则，全流程唯一 |
| step | name | 可选，非空显示名称，可用中文 |
| step | when | 可选，省略表示到达该步时执行 |
| step | skills | 必需，非空有序列表 |
| skills 项 | name | 必需，可用 Skill 的准确名称，不是文件路径；小写字母/数字/连字符，可带一个 `plugin:skill` 命名空间 |
| skills 项 | instruction | 必需，非空本阶段任务，可用 `\|` 多行文本 |

只接受上述字段；拼错、未知字段和不支持版本在修改项目之前报告。不要将 shell 命令或工具调用变成 YAML 扩展字段；instruction 可提及任务所需验证，但实际执行仍由 Skill、目标项目和本次授权决定。Skill 不被强制安装到项目内，用环境实际可用的 Skill 名称解析；名称不明确时报告，不按近似名称替换。

一个 step 的 instruction 分别属于 skills 中各项，后项接收前项产物。顺序始终以 YAML 列表为准，不能按名称重排、并行或自动补入 skill。可以多次列出同一个 Skill 完成不同的明确任务。

下面是一个 step 顺序使用多个 Skill 的完整示例；本次请求仍需明确实际评审范围：

```yaml
version: 1
name: review-code-and-docs
steps:
  - id: inspect
    name: 代码与文档检查
    skills:
      - name: code-review
        instruction: 只读评审本次指定改动，交付发现和验证范围。
      - name: project-docs
        instruction: 根据改动及评审结果只读核对受影响文档，不实施修改。
```

## 条件

单条件固定三个字段，只能引用列表中更早的 step：

```yaml
when:
  step: simplify
  field: changed
  equals: true
```

`field` 仅支持 status、changed、has_findings、has_unresolved。status 的 equals 为 completed/skipped/blocked/failed 之一；其他字段只接受字面量 true 或 false，不接受 `"true"`、yes、no、0、1 或 null。结果未知用 null 表示，但不能通过 equals:null 把未知当成可执行分支。

复合条件使用非空列表，可以嵌套：

```yaml
when:
  all:
    - {step: simplify, field: changed, equals: true}
    - any:
        - {step: review, field: has_unresolved, equals: false}
        - {step: review, field: status, equals: skipped}
```

一个节点只能是单条件、`{all: [...]}` 或 `{any: [...]}`，不混用。单条件的未知值比较结果仍为未知，不把 null 当作 false。

| 运算 | 真 | 假 | 未知 |
|---|---|---|---|
| all | 全部真 | 任一假 | 没有假且至少一个未知 |
| any | 任一真 | 全部假 | 没有真且至少一个未知 |

例如 all(false, unknown) 为 false，any(true, unknown) 为 true；其余不确定情况不能继续猜测。未检查的节点不自动产生确定值。条件是假时仅跳过当前 step，仍按列表继续；未知则当前 step blocked 并停止流程。failed/blocked 已停止流程，所以即便能写 status=failed 条件，也不会执行后续失败处理分支；首版没有失败恢复路由。

条件只在 step 开始时判断，后续步骤不能悄悄改写之前结果使其重跑。若需要针对新的产物再次评审，用后续明确 step；不支持循环或 goto。

## 校验方式

校验器要求 Python 3.10+ 和 PyYAML 6，依赖见 [requirements.txt](../requirements.txt)。使用已有兼容环境，或在用户选择的隔离环境安装 `python -m pip install -r <skill-dir>/requirements.txt`；不要默认向目标项目、全局环境或 CI 添加依赖。

```text
python <skill-dir>/scripts/check_workflow.py <workflow.yml>
python <skill-dir>/scripts/check_workflow.py <workflow.yml> --json
```

退出码：0 表示结构有效，1 表示 YAML/字段/引用无效，2 表示文件读取或依赖环境不可用。JSON 包含 valid、steps、skills、errors；只返回首个错误，修复配置后重新检查。校验不写入文件、不导入项目 Skill、不运行 instruction、不检查 Skill 是否存在、不评估运行时条件。

缺少可用 Python/PyYAML 时，可以人工按同一完整契约核对并报告「未运行自动校验」，不声称脚本通过；无法确认结构或 Skill 可用性时在实施前阻塞。自动或人工校验均不授予任何修改、网络或外部动作权限。
