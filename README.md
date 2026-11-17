# AgentPlatform · 团队 Agent 研发协作工作台

团队成员在项目中共同推进 Issue，在各自获准的本地 Agent 环境中完成研发工作。打开一个 Issue，接手者能找到目标、当前负责人、已交付的变更，以及接下来要谁作什么决定。仓库提供产品与架构设计、上游源码依据及研究原型。

## 核心架构

从[一项工作的核心流程](docs/architecture/overview.md#4-一项工作的核心流程)看成员怎样发起或接回工作、取用项目方法、提交成果，以及下一位负责人怎样检查和接手。成员可以亲自推进，也可以将持续协调委托给一个 Agent，由它在授权内选择执行、分工或使用 SOP。工作台贯穿这些环节。

[架构总览](docs/architecture/overview.md)说明中心、成员本机和资料来源各自维护哪些事实。[整体系统架构与模块边界](docs/architecture/system-architecture.md)说明五项职责如何结合 Multica、TeamAI 和 LoopForge 的机制。对象、状态、并发和交接分别见[核心对象模型](docs/architecture/core-object-model.md)、[统一生命周期](docs/architecture/lifecycle-state-event-model.md)、[协作一致性与并发控制](docs/architecture/core-consistency-concurrency.md)和[跨层业务契约](docs/architecture/cross-layer-contracts.md)。

## 五个设计专题

| 要了解的问题 | 设计正文 |
|---|---|
| 谁负责、怎样分工、介入和完成？ | [工作生命周期](docs/architecture/01-unified-work-lifecycle.md) |
| 何时自主规划，何时让 SOP 处理依赖、核验和返工？ | [SOP 与项目工作流](docs/architecture/02-sop-workflow.md) |
| 成员本机怎样接工作，Agent 怎样取得工具和项目依据？ | [本地执行](docs/architecture/03a-execution-plane.md) · [能力与上下文](docs/architecture/03b-capability-governance.md) |
| 怎样计算已知用量、评价交付，并让有效的方法进入下次工作？ | [成本、质量与改进](docs/architecture/04-cost-quality-improvement.md) |
| 评价什么时候触发、如何抽样和控制资源？ | [D11 · 评价触发与资源预算治理](docs/architecture/d11-evaluation-trigger-budget-policy.md) |
| 如何从整体架构进入技术方案并选择最小纵向切片？ | [技术方案准备与最小纵向切片](docs/architecture/technical-solution-readiness.md) |
| Issue / Comment 的业务意图怎样可靠绑定原生 Task？ | [VS-0 / VS-1 派发绑定与恢复契约](docs/architecture/vs0-vs1-dispatch-binding-contract.md) |
| Artifact、Candidate、Evidence 和 Acceptance 如何技术承载？ | [VS-2 · Candidate 与验收技术契约](docs/architecture/vs2-candidate-acceptance-technical-contract.md) |
| 成员在哪里处理待办、查看交付、接手工作与选用方法？ | [统一工作台](docs/architecture/05-unified-workbench.md) |

项目可以直接使用现有文档和代码仓。需要长期查阅资料或理解实现时，可分别接入[团队 Wiki 与项目资料](docs/architecture/team-project-wiki.md)和[项目代码 Wiki](docs/architecture/code-wiki.md)。两者都沿原 Issue 引用团队获准使用的内容。

## 研究与架构治理

后续研究和架构推进遵循[研究与架构治理规则](docs/governance/research-and-architecture-rules.md)，确保所有专题围绕完整产品主线推进，优先复用 Multica，不重复建设协作控制平面。 整体对象、职责、生命周期及 D5 / D6 / D7 闭环的交叉核验见[整体架构一致性审查](docs/research/architecture-consistency-review.md)。

## 查设计与依据

对象含义见[统一术语](CONTEXT.md)。Multica 原生覆盖、项目配置与需要补充的能力见[底座能力与边界](docs/architecture/governance-baseline.md)，各宿主可观察的事实见[宿主能力矩阵](docs/architecture/execution-capabilities.md)。源码核对、场景假设和历史实验按版本收录在[源码与研究](docs/research)。

流程研究涵盖 [SOP 的发现与提炼](docs/research/sop-discovery-extraction.md)及 [LoopForge SOP 生命周期](docs/research/loopforge-sop-lifecycle.md)。持续委托的研究涵盖 [Issue 内的分工](docs/research/mainbot-issue-operating-model.md)、[跨 Runtime 协调](docs/research/mainbot-runtime-coordination.md)及[等待与回唤](docs/research/mainbot-lifecycle-and-progress.md)。
