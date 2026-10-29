# 归档封存、基准与验证

## 操作前提

只归档语义上已判定完成且不再指导当前工作的 implemented 决定。先读取项目格式、归档机制与活动引用；工具不能替代这项判断。默认根为 `.agents/notes`，可用 `--notes-root docs/decisions` 指定实际根。路径必须规范项目相对路径，不接受 `./`、父级跳转或链接路径。

## 清单与可信程度

`archived/manifest.json` 是完整性元数据，version=1、archive_root 为项目相对路径，entries 按封存顺序追加。每项保存归档根相对 path、archived_on 和归档后全文原始字节 sha256。条目不能重排、修改、删除；文件改动、删除、移位或未登记都报错。

校验默认尝试读取 Git HEAD 中已提交清单；也可用 `--baseline-manifest <可信快照>`。已有条目必须与可信基准保持相同前缀。显式基准是调用方保存并信任的先前快照，不能使用当前清单自身；脚本不能鉴别快照是否真的可信，也不能防止调用方同时重写 Git 历史和所有快照。

没有历史基准时 verify 仍可检查当前文件与清单一致，但会提示 untrusted-history，history_verified=false，不能宣称清单未被重写。追加前必须有覆盖完整当前清单的基准；基准只保护部分条目时可验证前缀，不能继续封存。首次空库允许封存，但历史库中已有未登记记录时拒绝自动建立新基准。

全文哈希按原始字节计算。Git换行转换、clean/smudge过滤器和编辑器自动格式化都可能改变封存字节；采用前核对仓库策略。需要跨平台检出保持字节时，在项目自己的.gitattributes对实际归档路径设置适用的`-text`规则（默认路径示例：`.agents/notes/archived/** -text`），同时检查其他过滤器。不要修改用户全局Git配置，也不要用重新计算哈希掩盖检出后不一致；应从可信原件恢复或按项目既有归档机制处理。

## 使用

```text
python <skill-dir>/scripts/archive_records.py verify <project-root> --json
python <skill-dir>/scripts/archive_records.py verify <project-root> --baseline-manifest <trusted-snapshot.json> --json
python <skill-dir>/scripts/archive_records.py seal <project-root> --record .agents/notes/implemented/architecture/2026-10-20-topic.md --date 2026-10-29 --json
```

日期和路径为示例，替换真实值。verify 只读；seal 修改指定记录和清单，不改其他正文或自动修复引用。退出码 0 是所覆盖检查无错误（可能有提示）；1 为记录/完整性/基准覆盖错误；2 为配置、读写或清单格式错误。JSON 的 scope 明示基准来源、protected_entries、records_checked 和语义未验证。

## 单条封存流程

1. 读取项目规范、确认归档理由与当前替代权威，搜索受影响引用。
2. 先运行 verify。发现改坏、缺失、未登记或基准异常时停止，不重算哈希掩盖异常。
3. 已有归档时，确认 Git HEAD 或可信快照覆盖完整当前清单。保存快照必须在核对完整性后完成，不能从已知异常状态取样。
4. 用 seal 指定一个 implemented 记录。工具只在 Status 下插入 Archived 日期，其他原始字节（含 BOM、CRLF）保持不变，然后移到 archived 同分类/文件名并追加清单。
5. 在授权范围修复活动引用：当前规则指向当前所有者；确需历史依据的链接指向归档并说明历史性质。不修归档正文的出站链接。
6. 再 verify，并执行项目现有链接/格式检查和人工语义核对。提交或更新可信快照遵守用户任务，脚本不自动提交；第二条封存前需要新的完整基准。

## 格式与覆盖限制

写入仅支持 implemented/class/YYYY-MM-DD-topic.md 的 Agent Note 头部，class 使用最小规范分类。其他 ADR 不为适配脚本改成另一种格式；沿用项目已有工具，或明确提供格式适配后再执行。verify 检查 Agent Note 归档头部与清单日期，不证明章节内容、替代方案真实性或实施完成。活动记录的结构和链接可用项目已有文档检查；它与冻结校验是两类证据。

归档扫描不跟随 symlink/junction，不接受普通附件、翻译 sidecar 或未知格式文件，避免静默漏封。README.md、AGENTS.md、CLAUDE.md 是格式说明/入口元数据，明确不进入记录哈希清单；它们不能被当作冻结记录来绕过检查。需要多文件记录时先使用项目自己的整组封存机制，本版不自动处理。

目录链接、脚注、外链、当前权威关系和入站引用不由该工具验证。Git 可选且只读；没有 Git 时提供独立可信快照即可，不要求项目采用另一项 Skill。

## 失败与并发

封存使用排他锁、独占创建目标和同目录清单临时文件，单个清单替换原子。能捕获的写入失败会尝试回滚。多文件过程不具备跨文件崩溃原子性：异常终止可能留下锁或未完成文件，verify 将拒绝当正常结果。

存在 `.archive-records.lock` 时不要直接删除重跑。先确认没有进行中的进程，检查源、目标、清单、临时文件与可信基准，按实际状态恢复；恢复前保留证据。锁只协调使用此工具的操作，其他编辑器仍可修改文件，封存期间应停止同一记录与清单的并发编辑。
