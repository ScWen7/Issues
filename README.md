# AgentPlatform · 团队 AI 研发能力平台

AgentPlatform 面向使用不同本地 Agent 工具共同开展研发的团队。平台以团队知识为基础、以产研工作为主线、以 Engineering Harness 为质量保障，通过真实执行证据、Evaluation 和持续改进，让团队经验进入研发、研发结果反哺知识与工程方法。

**核心目标：让团队知识在研发中被复用，让 Harness 使研发过程可控、交付质量可验证，并让每一轮研发都为下一轮积累有效知识和更好的工程方法。**

## 产品设计基线

[产品定位与总体设计基线](docs/architecture/product-foundation.md)是产品目标、核心能力域、双飞轮、关键边界和架构完成标准的权威入口。现有设计与该目标的差距、可继承机制和融合工作见[产品定位与现有架构审计](docs/research/product-architecture-audit.md)。

## 核心业务能力

| 能力域 | 职责 |
|---|---|
| 团队知识管理 | 来源接入、证据处理、知识提炼、发布、检索、复用和失效治理 |
| 产研工作与流程协作 | Issue 目标、责任、业务决定、Project Workflow 和受托 SOP 执行 |
| Engineering Harness 治理 | Principles、Rules、Skills、Playbooks、SOP 定义、Scripts 与评价标准 |
| 执行与交付证据 | Multica 本地执行接入、Runtime 观察、Artifact、Candidate 和 Evidence |
| Evaluation、度量与持续改进 | 质量评价、Finding 分诊、知识 / Harness 改进、Benchmark 和真实效果回收 |

身份、权限、项目配置、工作台、来源连接器和宿主适配器属于实施时的横切设计事项，不构成额外产品能力域。完整职责和事实归属见[整体系统架构](docs/architecture/system-architecture.md)。

知识管理与 Harness 演进形成两个相互促进的飞轮。知识不是对话和日志的堆积；Harness 也不只是提示词集合。
## 架构专题

现有对象、生命周期、跨层契约和模块设计仍是架构融合的基础材料：

| 主题 | 设计与依据 |
|---|---|
| 工作责任与交接 | [工作生命周期](docs/architecture/01-unified-work-lifecycle.md) |
| SOP 与项目工作流 | [SOP 与研发工作流](docs/architecture/02-sop-workflow.md) |
| 本地执行与能力上下文 | [本地执行](docs/architecture/03a-execution-plane.md) · [Harness 选用与上下文投递](docs/architecture/03b-capability-governance.md) |
| 成本、质量与持续改进 | [成本、质量与改进](docs/architecture/04-cost-quality-improvement.md) · [D7 持续改进内循环](docs/architecture/d7-continuous-improvement-loop.md) |
| 团队知识生命周期 | [知识管理与研发知识闭环](docs/architecture/knowledge-management-lifecycle.md) |
| 核心业务对象关系 | [核心业务对象与统一关系模型](docs/architecture/core-business-object-model.md) · [详细对象目录](docs/architecture/core-object-model.md) |
| 团队 Wiki 与项目资料 | [团队 Wiki 与项目资料](docs/architecture/team-project-wiki.md) |
| 项目代码知识 | [项目代码 Wiki](docs/architecture/code-wiki.md) |
| 统一工作入口 | [统一工作台](docs/architecture/05-unified-workbench.md) |
| 整体系统架构 | [整体系统架构与能力边界](docs/architecture/system-architecture.md) |

## 研究与治理

- [产品定位与现有架构审计](docs/research/product-architecture-audit.md)：当前阶段的架构审计与融合议题。
- [整体架构一致性审查](docs/research/architecture-consistency-audit.md)：五个核心业务域、对象权威归属、专题冲突与端到端验证。
- [双飞轮端到端场景验收](docs/research/scenario-acceptance.md)：完整研发交付链与知识 / Harness 自进化链的架构级验收。
- [整体架构一致性审查](docs/research/architecture-consistency-review.md)：现有对象、职责与 D5 / D6 / D7 契约的交叉核对。
- [研究与架构推进规则](docs/governance/research-and-architecture-rules.md)：研究、来源核验和远端文档治理要求。
- [统一术语](CONTEXT.md)：项目正式术语。
- [底座能力与边界](docs/architecture/governance-baseline.md)：Multica 原生能力及扩展边界。
- [源码与研究](docs/research)：上游源码观察、实验和证据。

当前阶段聚焦产品定位、知识生命周期、业务对象与整体架构融合。产品和业务关系收敛前，不进入数据库 Schema、API、部署拓扑、原型或工程实现设计。
