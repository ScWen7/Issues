# AgentPlatform · 团队 Agent 研发协作工作台

团队成员在项目中共同推进 Issue，在各自获准的本地 Agent 环境中完成研发工作。打开一个 Issue，接手者能找到目标、当前负责人、已交付的变更，以及接下来要谁作什么决定。仓库提供产品与架构设计、上游源码依据及研究原型。

## 团队怎样工作

成员可以从项目列表接下 Issue，也可以先在自己的工具中调查，再把选定的结论、变更或文件交回 Issue。自己负责时可在评论中请 Agent 协助。需要交出整项责任时使用原生指派。独立分工有自己的负责人和交付物，使用子 Issue。指派给 Squad 时，其 Leader 在获准的本地 Runtime 上组织协作。[工作生命周期](docs/architecture/01-unified-work-lifecycle.md)

一次受管执行记为 Run。稳定的重复环节可以调用 SOP。成员在 Issue 中决定业务范围和接受哪次交付，后续工作可选用团队已审核的方法。提供机器、执行检查、接受业务结果是不同职责。[架构总览](docs/architecture/overview.md) · [工作台](docs/architecture/05-unified-workbench.md)

## 五个设计专题

| 要了解的问题 | 设计正文 |
|---|---|
| 谁负责、怎样分工、介入和完成？ | [工作生命周期](docs/architecture/01-unified-work-lifecycle.md) |
| 何时自主规划，何时让 SOP 处理依赖、核验和返工？ | [SOP 与项目工作流](docs/architecture/02-sop-workflow.md) |
| 成员本机怎样接工作，Agent 怎样取得工具和项目依据？ | [本地执行](docs/architecture/03a-execution-plane.md) · [能力与上下文](docs/architecture/03b-capability-governance.md) |
| 怎样计算已知用量、评价交付，并让有效的方法进入下次工作？ | [成本、质量与改进](docs/architecture/04-cost-quality-improvement.md) |
| 成员在哪里处理待办、查看交付、接手工作与选用方法？ | [统一工作台](docs/architecture/05-unified-workbench.md) |

项目可以直接使用现有文档和代码仓。需要长期查阅资料或理解实现时，可分别接入[团队 Wiki 与项目资料](docs/architecture/team-project-wiki.md)和[项目代码 Wiki](docs/architecture/code-wiki.md)。两者都沿原 Issue 引用团队获准使用的内容。

## 查设计与依据

产品范围及跨专题关系见[架构总览](docs/architecture/overview.md)，对象含义见[统一术语](CONTEXT.md)。Multica 已提供的能力和需要适配的部分见[底座能力与边界](docs/architecture/governance-baseline.md)。研究记录按源码版本、宿主入口和观察范围区分事实与假设。[源码与研究](docs/research) · [宿主能力矩阵](docs/architecture/execution-capabilities.md) · [交互原型](prototypes/topic-05/workbench.html)
