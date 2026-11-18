# AgentPlatform 核心架构总览

AgentPlatform 是面向研发团队的 AI 研发能力平台。它以团队知识为基础、以产研工作为主线、以 Engineering Harness 为质量保障，通过真实执行证据、Evaluation 和持续改进，让团队经验进入研发、研发结果反哺知识与工程方法。

产品目标、两个飞轮、范围边界见[产品定位与总体设计基线](product-foundation.md)。统一能力域、职责、事实权威、依赖和端到端数据流见[整体系统架构](system-architecture.md)。知识、Harness、工作、执行和证据的对象关系见[核心业务对象与统一关系模型](core-business-object-model.md)。

## 1. 核心能力域

| 能力域 | 主要职责 |
|---|---|
| 组织与项目治理 | 成员、项目、授权、项目配置和项目采用决定 |
| 团队知识管理 | 来源接入、证据处理、知识提炼、发布、检索、复用、更新与失效 |
| 产研工作协作 | Issue 目标、责任、上下文、协作决定、工作流交接和交付消费 |
| Engineering Harness 治理 | Principles、Rules、Skills、Playbooks、SOP、Scripts、Scorer / Rubric 及版本发布 |
| 研发流程与 SOP 执行 | 明确委托的流程实例、节点依赖、结果消费、门禁和返工 |
| 执行集成与 Runtime 观测 | 复用 Multica 执行链，连接成员本地 Agent 并记录实际回执 |
| 交付与证据 | Artifact、Candidate、Evidence、核验依据和交付消费 |
| Evaluation、度量与持续改进 | Finding 分诊、知识 / Harness 改进、Benchmark、发布采用和真实效果回收 |

统一工作台、来源连接器和宿主适配器是横向能力，不另立业务主线。详细边界见[整体系统架构](system-architecture.md)。

## 2. 核心业务对象与事实归属

**Issue 是研发工作的唯一业务归属。** 目标、责任、讨论、决定、业务状态和完成条件沿 Issue 维护。成员可以自行推进、一次性邀请 Agent 协助，或在明确授权后把持续协调交给现有 Agent 担任 Main Bot。

**知识和 Harness 是两类独立资产。** Knowledge 描述有证据的事实、经验和解释；Harness 定义研发方法、约束和验证方式。二者共享不可变修订、Release、Project Adoption 和工作实际使用引用的最小机制，但内容模型、核验标准和发布责任不同。

**Run 记录真实受管执行。** 沿用 Multica Task / Run / Runtime / Session / Usage，不另建执行控制平面。SOP 只管理明确委托的流程范围；项目阶段与负责人交接由 Project Workflow 管理。

**Evidence 可以被多个消费者引用。** 同一份事实可支持交付核验、知识提炼和 Harness Evaluation；不同消费者形成各自结论和决定，不复制权威事实。

详细定义见[统一对象目录](core-object-model.md)、[统一业务对象关系](core-business-object-model.md)、[生命周期与事件模型](lifecycle-state-event-model.md)和[一致性与并发控制](core-consistency-concurrency.md)。

## 3. 一项研发工作的核心链路

1. **确定工作**：在 Issue 明确目标、范围、责任和完成条件。
2. **准备上下文**：按项目、工作类型、阶段、代码基准和接收者权限检索团队知识、项目资料及必要的代码依据。
3. **选择 Harness**：取得项目采用或本项选用的规则、Skills、Playbooks、SOP 和验证标准。
4. **组织执行**：负责人决定自行推进、一次性协助、持续 Main Bot 委托或调用 SOP；实际受管执行沿 Multica Run / Runtime。
5. **形成交付**：固定 Artifact、Candidate 和 Evidence；按工作约定执行必要检查。
6. **作出业务决定**：有权负责人或验收人接受、退回或要求补充；Evaluation 不替代业务验收。
7. **反馈与沉淀**：从真实交付和执行中形成知识候选或 Harness Finding，按不同治理路径验证、发布和采用。

并非每项工作都需要 SOP、独立 Evaluation 或知识审批。按需启用，避免将研发变成仪式化流水线。

## 4. 双飞轮如何连接

**团队知识飞轮**：来源 → 证据 → 候选知识 → 核验发布 → 检索复用 → 使用反馈 → 更新 / 失效。

**Harness 进化飞轮**：执行 → 观察与评价 → Finding → Harness 候选 → 回归 / Benchmark → 审核发布 → 项目采用 → 生产效果回收。

两个飞轮共享 Issue、Run、Artifact、Evidence 和 Finding 等可追溯事实；知识候选和 Harness 候选分别治理。Finding 也可能指向项目约定、Runtime / Tool 或评价器问题，不应强行归因到知识或 Harness。

- [团队知识管理与研发知识闭环](knowledge-management-lifecycle.md)
- [D7 持续改进内循环](d7-continuous-improvement-loop.md)
- [成本、质量与改进](04-cost-quality-improvement.md)

## 5. 中心协作与成员本地执行边界

中心维护共享的组织、项目、Issue、授权、资产版本、交付引用、评价和改进事实。成员本地环境维护宿主进程、Session、工具、凭据、工作副本和未共享内容。

中心派发不等于本地实际启动；上下文选择、准备、投递、宿主加载和实际使用是不同证据阶段。宿主未提供的工具活动、模型用量和 Credits 保持 unknown。成员 Runtime 断联不应使共享 Issue 和其他成员的协作不可用。

具体规则见[本地执行](03a-execution-plane.md)、[工作生命周期](01-unified-work-lifecycle.md)和[统一工作台](05-unified-workbench.md)。


## 首期协作范围

首期以一项真实研发工作能顺畅接续为核心：成员从 Issue 取得目标和责任，按需检索团队 / 项目知识，选择适用 Harness，使用本地 Agent 或人工推进，交回可核验交付，并把有复用价值的经验反馈给知识和 Harness 维护者。普通工作不要求启用完整 SOP、独立 Evaluation 或全部知识扩展能力。

## 共享业务契约

| 契约 | 谁提供，谁使用 | 变化时如何处理 |
|---|---|---|
| Work Contract | Issue 提供目标、责任、范围和决定；成员、Agent 与流程按授权执行 | 目标或授权变化时由有权成员修订，后续执行核对有效版本 |
| Context Contract | 知识、项目资料、代码与 Issue 提供有来源的上下文；执行者按读权取得 | 来源修订或权限变化时重算受影响输入，保留历史引用 |
| Capability Contract | 团队 / 项目维护者发布 Harness；项目或工作按权限选用 | 新版本发布不自动改变项目采用或在途工作 |
| Delegation / Execution Contract | Issue 负责人或授权 SOP 明确受托范围、动作、输入与产出 | 撤权、改派或接管时停止新的受影响动作并核对在途副作用 |
| Delivery Contract | 生产者提供 Artifact / Candidate / Evidence；接收方按工作约定核验 | 候选或标准换版时重新判断证据适用性 |
| Feedback Contract | 交付、执行、Evaluation 和人工反馈提供证据；知识 / Harness 维护者分别治理 | 同一 Finding 可产生独立知识与 Harness 候选，不合并发布权责 |

## 6. 跨层业务契约

| 契约 | 主要回答的问题 |
|---|---|
| Work Contract | 目标、责任、范围和业务决定由谁维护？ |
| Context Contract | 当前执行者按什么权限取得哪些知识、资料和历史版本？ |
| Capability Contract | 本项工作采用哪些 Harness 资产、工具和规则？ |
| Delegation / Execution Contract | Agent 或 SOP 获得什么授权，实际执行允许做什么？ |
| Delivery Contract | 交付哪些版本、如何核验、谁有权接受？ |
| Feedback Contract | 证据如何进入知识提炼、Evaluation 和持续改进？ |

具体契约、状态转换、事件因果和恢复规则分别由专题维护；工作台只读取并调用相应权威入口，不复制业务规则。

[跨层业务契约与协作协议](cross-layer-contracts.md) · [研究与架构推进规则](../governance/research-and-architecture-rules.md)
