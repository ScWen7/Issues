# AgentPlatform 仓库维护

`master` 是发布产品设计的默认分支。从 [README](README.md) 进入[架构总览](docs/architecture/overview.md)，按问题找到负责的专题。术语在 [CONTEXT.md](CONTEXT.md) 维护，Multica 固定版本的覆盖范围见[底座能力与边界](docs/architecture/governance-baseline.md)。

- 直接更新定义该行为的正文。写清谁在什么情形下可以采取什么行动、结果记录在哪里、谁能接着工作。总览只维护跨专题关系；其他文档引用原定义。
- 提出产品扩展时，先对照 Multica 的实际入口、配置、源码或测试，说明哪个成员的具体工作仍缺支持。已有机制直接沿用。团队资料与代码说明根据工作需要接入。
- 产品设计放在 `docs/architecture/`。带版本的源码观察、实验方法和结果放在 `docs/research/`，复跑工具和原始回执分别归 `prototypes/` 与 `artifacts/`。用例标明假设。能力覆盖按实际入口记录，缺少回执的字段标为未知。
- 工作从最新 `master` 开始。需要分支时围绕一项具体改动使用短期分支，合回后核对全部独有提交和打开的 PR，再清理分支。已经发布的方案就地维护，讨论和修订过程由 Git 或 PR 记录。
- 修改名称、路径或标题时同步检查引用。运行 `python3 .github/scripts/check_design_links.py` 检查仓库内的链接和设计入口。合入前核对专题间的对象含义，以及源码或实验引用的版本。
