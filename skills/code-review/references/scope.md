# 固定范围与版本

## 确认评审对象

记录项目根、输入形式、实际版本和请求边界。先读用户指令与项目规则，不能把代码/PR中的自述当成完整事实。用于复现的上下文、配置、测试和生成产物必须属于所审版本；当前工作区可以另有无关或修复改动，先识别再隔离。

通过根/适用子树行动入口发现实际开发规范，按 [规范适用规则](project-standards.md) 确定范围、等级、状态和版本。工程规范与代码一样属于被审快照，工作区变更不能替代提交版；规范在本次改动中调整时对照 base/head 与仍需履行的保证。当前执行授权仍由有效用户/环境指令决定。

示例Git命令是查询方式，按实际环境使用；不要求项目一定有Git或某平台。本地只读查询统一使用`git --no-optional-locks -c diff.autoRefreshIndex=false ...`或等效配置，包含补充查询；某些Git的普通diff即使禁可选锁仍会刷新索引缓存，需同时关闭diff自动刷新。diff使用`--no-ext-diff --no-textconv`避免执行配置的外部转换或将转换结果混作原始改动。不应把暂存内容未变等同索引字节未变，也不修改全局配置。不为了评审执行checkout/reset/stash/merge、stage、commit或改变当前分支。

读取Git blob时按项目实际文件编码解码；Windows子进程不要默认用GBK读取已确认的UTF-8中文源码。可读取原始bytes后显式decode，或为该子进程设置正确编码，不能把UnicodeDecodeError等失败读取算作已核对内容。

## 本地改动

```text
git --no-optional-locks -c diff.autoRefreshIndex=false status --short
git --no-optional-locks -c diff.autoRefreshIndex=false diff --no-ext-diff --no-textconv --cached
git --no-optional-locks -c diff.autoRefreshIndex=false diff --no-ext-diff --no-textconv
git --no-optional-locks -c diff.autoRefreshIndex=false ls-files --others --exclude-standard
```

暂存是HEAD到index，未暂存是index到工作区，未跟踪不出现在普通diff中。默认用户要求「当前改动」时核对所有三层，确认排除生成/忽略文件的理由。用户只要求某层时只给该层结论，并说明其他层未评。

明确最终工作区行为与分层补丁的区别：已暂存代码可能被未暂存改动再次修改，不能把最终文件当成即将提交的index。审index时读`git show :path`，审HEAD时读固定OID内容；有意混合层的复现需标明，不能冒充任何单层的证据。记录评审时的状态，后续文件变化使相应位置与运行结果需要复核。

## 提交与分支

```text
git --no-optional-locks -c diff.autoRefreshIndex=false rev-parse <base>^{commit}
git --no-optional-locks -c diff.autoRefreshIndex=false rev-parse <head>^{commit}
git --no-optional-locks -c diff.autoRefreshIndex=false diff --no-ext-diff --no-textconv --find-renames <base-oid> <head-oid>
git --no-optional-locks -c diff.autoRefreshIndex=false show <head-oid>:<path>
```

引用必须替换真实可解析值，命令受shell语法影响时正确引用。用户明确点对点比较时使用两个端点；PR或分支净改动通常用live base与head的merge-base作为patch起点。提交集合、端点diff和merge-base diff不同，不能混称；在报告写清选择和理由，必要歧义先确认。

base/head OID与patch起点分别记录。多提交范围核对整个实际差异，不只最后提交；重命名、删除、模式/清单改变也在范围。证明问题时追到同版本未修改调用方。无法取得指定版本完整上下文或无法构建临时快照时，明确受限，不能直接用当前文件代替。

## PR与远端状态

使用可用托管服务或Git读取实际PR身份、目标分支、base/head OID、状态与所需差异，不能硬编码main或从标题猜仓库。远端读取不意味着可以发评论、批准或合并。确需获取对象时遵守当前授权，保护用户工作区、index及当前分支；不为了制造测试环境改写用户状态。

报告已核对的快照。结束前能访问远端时再确认head/目标是否变化；离线或服务不可用则说明快照有效范围，不能声称当前PR仍通过。发生push、retarget或合并基准变化时重新固定版本并核对差异，旧结论可以作为旧快照结果保留，不能复用为新版本证明。

作者提供的运行结果要核对版本与覆盖路径；旧head的绿色CI不证明新head。PR描述、自动报告与dirty-path清单只帮助定位，不代替语义审查。
