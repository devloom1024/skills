# 验证记录

2026-11-02，使用忽略目录内的独立样本，没有网络、提交、发布或用户真实配置修改。基线与使用者分开，不读取预期判定与其他评估结果。

## 基线与实际使用

三个原始样本均提供同样的 YAML 与本地小型 Skill：只读检查无改动；同一步先写入再核验缺失的外部证明；检查已完成但远端问题状态无法确定。已有 legacy.txt 不属于本轮修改。基线没有 project-workflow，只知道步骤和 Skill 顺序与条件形式。

基线已正确识别无改动和未知问题，不将原有文件计成本轮变化。缺少停止契约时，它将「先写后缺证据」标成自定 partial 状态，然后继续执行了无 when 的下一步；未知条件被记为 skipped。没有把基线已有的谨慎判断记作新增收益。

使用新 Skill 的独立执行者先运行校验并解析全部 Skill：无改动 inspect completed/changed=false，后续 skipped；缺证明样本 write 后 verify blocked，整个 step blocked/changed=true/has_findings=true/has_unresolved=true，后续未到达；未知样本 inspect completed，问题字段 null，后续 when 未知使当前 step blocked。三个后续 annotated.txt 都未创建，没有补造 external-proof.json。前后摘要显示只有允许的 seed.txt 改为 updated，legacy.txt 保持不变；主执行者再次核对产物符合这些结论。

## 真实专项 Skill 串联

另一独立执行者使用质量维护示例和真实 code-simplification、code-review、project-docs，在无 Git 的小型任务执行器中串联三个阶段。只删除一个有证据支持的未使用私有函数；公开 run 的 AST 保持相同，修改前后 3 项测试通过。评审 completed、无发现/无待解决事项，文档阶段核对现有 README/AGENTS 后确认无需修改，没有创建 LESSONS 或新决策。

主执行者核对实际差异仅删除该私有函数，并复跑最终 3 项行为测试。各阶段结果与分支证据一致；既有文档和测试未修改，没有初始化 Git 或引入依赖。该样本只证明一个有限场景，不证明任意项目可无人监督执行。

## 校验器与复核

CLI 测试先观察到脚本不存在导致失败，编写后覆盖结构、字段、布尔类型、重复 ID/YAML 键、非法引用、嵌套条件结构、锚点/别名/标签、多文档、BOM、读失败和缺 PyYAML。独立复核发现 PyYAML 隐式日期/超长整数可抛 ValueError、深层 YAML 的 RecursionError 被误归环境错误；增加失败用例后修正异常分类。当前 10 个测试方法（包含多组无效配置子用例）通过，每个输入样本目录保持原字节。

元数据、正文链接/结构和质量维护 YAML 已运行校验；独立内容/脚本复核未发现剩余具体问题。运行时 all/any 三值组合、失败而非阻塞、恢复后的外部副作用、所有汇总组合和真实平台差异未穷尽执行；仅完成契约复核并列入验收场景。脚本只校验格式，不检查 Skill 可用性、授权、运行语义或 Agent 判断质量。校验通过不等于端到端流程保证。
