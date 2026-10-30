# 一致示例：本地任务执行器

这是虚构的教学示例，不是目标项目事实。假设源码已确认 `run(task)` 同步调用 work、成功写 done/result、捕获 Exception 写 failed/error、原地返回字典，没有队列或持久化。

## 根指令只负责行动和导航

```markdown
# 项目开发规则

修改任务执行前读 docs/architecture.md 和 docs/subsystems/tasks.md，再核对 worker.py。
行为变化时同步所属参考，运行 Python 示例和受影响的行为检查。
开发和评审前读 docs/standards/README.md，按改动选择规范。
配置读写修改前读 docs/standards/defensive-patterns/configuration.md；文档更新遵守 docs/AGENTS.md。
```

这里不展开状态机，不复制配置失败的完整防错规则。

## 架构负责组成与协作

```markdown
# 架构

调用方在当前线程向 worker.run 传入任务和 work，worker 执行回调并修改该字典。数据只活在当前进程，当前没有调度器、队列或存储提供方。

执行语义和失败结果由子系统参考拥有，入口实现是 worker.py。新增后台调度需要重新定义所有权与生命周期，不能当作现有架构中的隐藏能力。
```

实际文档在对应名称处添加真实相对链接。架构没有复制每个字段的全部语义。

## 子系统参考回答契约问题

```markdown
# 任务执行

run 接收可变字典，进入时无条件写 state=running，不检查初态。调用 work 成功后写 result 和 done；捕获 Exception 时写错误字符串和 failed。返回原对象，不创建副本。

调用者拥有字典，不应并发修改它。重用字典不会清除旧 result/error，调用方不能仅依据这些字段是否存在判断本次结果；state 决定本次完成状态。BaseException 不在捕获范围内。

当前没有取消、重试或崩溃恢复。修改时核对 worker.py，验证成功、异常、旧字段、对象身份和重复调用。
```

比「支持执行任务并处理异常」多出的信息，正是 agent 会据此改变代码和测试选择的语义。

## Cookbook 给出可观察操作

在真实实现与示例存在的前提下，教程可以让读者运行 `python worker.py`，检查输出的 done 与结果 7；失败时区分 Python 环境问题与 work 回调错误。具体任务构造和清理步骤由该教程拥有，长期理由链接决策记录，不插入历史故事。

## Agent Note 保留取舍

若团队真实比较过同步执行与后台队列，记录问题、选择同步的理由、为何当前不采用队列以及「不能跨进程恢复」的后果。将来异步化要建立新决定并引用旧决定，不能把原记录改成「从一开始就是异步」。若未讨论替代方案，不编造比较过程。

## LESSONS 晋升示范

三个不同日期的事故证明配置读取失败被误当空值并写回。当前完整防错规则由 `docs/standards/defensive-patterns/configuration.md` 维护：读取失败中止写入、保留旧文件、区分有效空配置，并用故障输入核对文件字节未变化。LESSONS 仅保留主题、三个事件链接、已晋升状态和正式规则链接；根 AGENTS 只有阅读条件。

这比在三个文件反复维护相同长段落更容易保持一致，也让事故证据与现行要求都能找到。

## 同一项目的目录布局

假设这个已有项目原本就用 cookbook 保存管理员操作教程，user/index 是稳定网站入口；项目已明确保留这一读者与路径映射。随后确实增加配置子系统和两篇管理员教程，可以沿用下列布局。新项目没有此约定时，管理员产品任务默认放入 user，Cookbook 用于贡献者操作。仅展示已经有实际内容的路径，不能据此在目标项目预建目录。

```text
docs/
  AGENTS.md
  architecture.md
  subsystems/
    README.md
    tasks.md
    configuration.md
  cookbook/
    README.md
    install-plugin.md
    configure-proxy.md
    assets/
      install-plugin/
        settings.svg
  standards/
    README.md
    defensive-patterns/
      configuration.md
  user/
    index.md
```

约定写入 docs/AGENTS：子系统按契约平铺，每页拥有一个子系统；教程一篇一个管理员操作，动作加对象命名；资源归所属教程；user/index 是已有网站入口，保持路径，由它链接当前教程。standards 入口按修改对象指向正式规范，领域防错只有一篇时由该入口直接链接，不额外建 defensive-patterns 索引。

subsystems/README 用「页面 → 拥有的语义」表导航 tasks 和 configuration，不重述状态机。cookbook/README 按任务选择并说明真实前提，例如安装签名插件与配置代理；用户指南通过原 index 到达相应教程，不复制安装步骤。教程的图片链接按所在文件位置为 `assets/install-plugin/settings.svg`。

若旧 system.md 同时描述两个独立子系统，可以拆分并把所有入站引用指向实际语义所有者；旧页仅在仍需概览或兼容导航时保留。已有 guide.md 被公开链接引用时，先核对路由/别名能否保留，再决定是否重命名为 install-plugin.md。命名统一的收益不能自动覆盖稳定链接约定。

## 开发规范的归属与等级

若团队另已采纳 UTF-8 文件读写要求，其完整条款可由 standards/coding.md 拥有：适用于本项目文本读写，必须显式使用 UTF-8；目的是避免默认编码随环境变化；外部协议明确指定其他编码时保留来源和转换理由；用隔离的中文输入核对结果，不能写真实用户配置。同页若建议提前返回，应明确只是建议，不把等价控制流判错。规范入口链接此页，根指令只导航，不复制正文，也不虚构本项目曾发生编码事故。

已有项目若把这些要求放在 docs/conventions/index.md、docs/conventions/python.md 和 docs/defensive-patterns/file-io.md，则保持这些路径，用文档标准声明它们分别承担规范入口、编码规范和领域防错角色，不生成竞争的 standards 树。原政策草稿移出完整规则后可保留导航；任何规则只维护一个正文。testing 拥有测试隔离与结果判断，规范页链接它，避免两处更新。

## 决策规范与专项操作

project-docs为该项目建立记录约定：何时创建、目录/状态/正文、当前参考与理由区别、部分取代保留保证、冻结归档的工具和可信基准要求。没有集成冻结工具时如实记录缺口，单条提案维护仍可按代码与证据完成。

若后续使用独立decision-records，它先读同一个项目约定，再执行受影响决定的取代分析与封存，不重新生成另一套标准。第一次空库封存只建立当前字节清单；没有Git已提交基准或可信快照时，不能声称旧清单自身防重写。现有格式/链接检查与冻结校验分别报告。

## 从任务提炼教程

真实生成器写入显式输出路径时，教程先说明环境、工作目录和输出副作用，再在临时目录运行实际命令并检查产物内容。恢复步骤依据真实失败条件，不能靠猜测添加重试。步骤变动更新现有教程与样例，长期设计理由链接记录，不把每次执行日志写成教程正文。
