# AgentPlatform · 团队 Agent 研发协作工作台

团队成员在项目中共同推进 Issue，在各自获准的本地 Agent 环境中完成研发工作。打开一个 Issue，接手者能找到目标、当前负责人、已交付的变更，以及接下来要谁作什么决定。仓库提供产品与架构设计、上游源码依据及研究原型。

## 核心架构

整体系统模块、中心与本地 Runtime 边界、五层映射及 Multica / TeamAI / LoopForge 融合关系见[整体系统架构与模块边界](docs/architecture/system-architecture.md)。

从[架构总览](docs/architecture/overview.md)进入正式设计；核心对象的权威定义见[核心对象模型](docs/architecture/core-object-model.md)，其状态转换和跨层事件见[统一生命周期、状态机与事件模型](docs/architecture/lifecycle-state-event-model.md)，并发与恢复规则见[核心协作一致性与并发控制模型](docs/architecture/core-consistency-concurrency.md)，跨层协作约定见[跨层业务契约与协作协议](docs/architecture/cross-layer-contracts.md)。它说明中心协作、成员本机和资料来源各自维护什么事实，五项核心职责怎样配合，以及一次工作从发起、执行到交付和后续改进的条件。[系统边界](docs/architecture/overview.md#1-系统边界) · [职责分层](docs/architecture/overview.md#3-核心职责分层) · [核心流程](docs/architecture/overview.md#4-一项工作的核心流程)

## 五个设计专题

LoopForge 的 SOP 形成、AI 编排、执行消费与评价演进源码研究见[LoopForge SOP 生命周期研究](docs/research/loopforge-sop-lifecycle.md)；从 Squad / Main Bot 动态协作中发现和提炼 SOP 的研究见[SOP 发现与提炼机制](docs/research/sop-discovery-extraction.md)，以及[Main Bot 跨 Runtime 持续协调机制](docs/research/mainbot-runtime-coordination.md)。这些文档记录源码依据与研究结论，不替代本项目正式架构决策。

| 要了解的问题 | 设计正文 |
|---|---|
| 谁负责、怎样分工、介入和完成？ | [工作生命周期](docs/architecture/01-unified-work-lifecycle.md) |
| 何时自主规划，何时让 SOP 处理依赖、核验和返工？ | [SOP 与项目工作流](docs/architecture/02-sop-workflow.md) |
| 成员本机怎样接工作，Agent 怎样取得工具和项目依据？ | [本地执行](docs/architecture/03a-execution-plane.md) · [能力与上下文](docs/architecture/03b-capability-governance.md) |
| 怎样计算已知用量、评价交付，并让有效的方法进入下次工作？ | [成本、质量与改进](docs/architecture/04-cost-quality-improvement.md) |
| 成员在哪里处理待办、查看交付、接手工作与选用方法？ | [统一工作台](docs/architecture/05-unified-workbench.md) |

项目可以直接使用现有文档和代码仓。需要长期查阅资料或理解实现时，可分别接入[团队 Wiki 与项目资料](docs/architecture/team-project-wiki.md)和[项目代码 Wiki](docs/architecture/code-wiki.md)。两者都沿原 Issue 引用团队获准使用的内容。

## 查设计与依据

对象含义见[统一术语](CONTEXT.md)。Multica 原生覆盖、项目配置与需要补充的能力见[底座能力与边界](docs/architecture/governance-baseline.md)，各宿主可观察的事实见[宿主能力矩阵](docs/architecture/execution-capabilities.md)。源码核对、场景假设和历史实验按版本收录在[源码与研究](docs/research)。
