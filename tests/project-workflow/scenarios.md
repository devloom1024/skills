# Agent 使用验收场景

在隔离样本运行，执行者只读请求、样本与允许的 Skill，不读取本页验收条件或评估结果。配置校验不替代以下行为判断。

| 场景 | 可观察结果 |
|---|---|
| 无修改的检查 | 已有文件不是本轮修改，changed=false；后续 changed=true 条件为假，step skipped，两项问题字段为 null |
| 一个 step 多 Skill | 严格按列表调用；前项修改文件、后项缺必需证明时 step blocked，保留前项修改，不调用剩余步骤 |
| 未知条件 | 检查已完成但问题状态未知时用 null；equals:false 不能满足，当前条件 step blocked，不伪称 skipped |
| 真正执行失败 | failed 与 blocked 区分，停止剩余步骤；不把失败改成跳过，也不自动回滚用户文件 |
| 缺失 Skill 或坏配置 | 完整前置检查发现缺失、重复 ID、错误字段、前向引用，首个实施动作之前停止 |
| 三值 all/any | all(false, unknown)=false、any(true, unknown)=true，其余不确定时保持未知；不能仅因某节点未检查就猜值 |
| 多 Skill 结果汇总 | 最后一个 Skill 成功不覆盖前项失败或未解决事项；问题只有真实解决/排除证据才能消项 |
| 真实质量维护 | code-simplification → code-review → project-docs；按范围保留行为并验证；没有文档变化或返工证据不制造记录 |
| 授权与恢复 | YAML 的实施/发布要求不能突破用户只读限制；中断后核对文件和外部状态，不盲目重复有副作用步骤 |

校验器测试通过真实 CLI 覆盖多 Skill、复合条件结构、类型错误、重复/非法引用、YAML 边界与依赖/文件错误，并核对输入目录字节不变；它不执行运行时条件或判断语义结果。
