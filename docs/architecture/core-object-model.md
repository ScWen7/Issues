# 核心对象模型

本文定义 AgentPlatform 的核心对象、对象关系及事实归属，是各架构专题共同遵循的对象定义。对象状态、转换条件和跨层事件由[统一生命周期、状态机与事件模型](lifecycle-state-event-model.md)定义；并发写入、跨层恢复和结果消费一致性由[核心协作一致性与并发控制模型](core-consistency-concurrency.md)定义；本文不定义数据库表、接口字段或页面结构。

## 1. 建模原则

1. **一项业务工作的唯一归属是 Issue。** 工作目标、范围、当前责任、业务决定和完成状态以 Issue 为准。
2. **组织协作、流程编排和实际执行是不同维度。** Issue、SOP Execution、Run 不是三种可互换的任务。
3. **工作责任与执行资源分别记录。** 成员承担业务责任，成员或 Agent 可接手具体工作。Run 记录实际执行者、Runtime 和宿主 Session。
4. **结果不等于证据，评价不等于验收。** 制品说明交付了什么；证据说明某项事实得到什么支持；评价给出分析结论；验收是有权主体对当前候选作出的业务决定。
5. **定义、实例、版本和使用记录分开。** SOP、Skill、Rule 等定义可发布多个版本；一次工作固定实际采用的版本，后续变更不改写历史。
6. **同一事实只由其权威来源维护。** 工作台汇集和呈现对象关系，不复制各来源的决定权。

## 2. 对象分组

| 对象组 | 核心对象 | 主要职责 |
|---|---|---|
| 组织与范围 | Team、Project、Member、Agent | 界定协作范围、参与主体及组织关系 |
| 工作与责任 | Issue、工作约定、Decision、Project Workflow | 承载业务目标、责任、决定和工作生命周期 |
| 方法与能力 | Skill、Rule、Playbook、SOP Definition、Role、Tool 配置、Knowledge | 定义可复用的方法、规则、能力和资料 |
| 流程实例 | SOP Execution、Node Activation、Node Attempt | 管理一次受托流程的依赖、节点推进、结果消费和出口 |
| 执行资源与记录 | Host、Runtime、Daemon、Backend、Session、Run | 提供本地执行能力并记录真实受管执行 |
| 交付与证据 | Artifact、Candidate、Evidence、Delivery Record | 表达交付内容、版本、检查依据和交接结果 |
| 评价与演进 | Evaluation、Finding、Improvement Proposal、Benchmark、Release | 评价实际结果，审核和发布可复用改进 |

这些分组是概念边界，不要求对应独立服务、数据库或部署单元。

## 3. 核心对象定义

### 3.1 组织与参与主体

| 对象或职责 | 定义 | 边界 |
|---|---|---|
| Team | 人员、Agent、共享能力和项目的组织范围 | 不直接承载某项工作的业务生命周期 |
| Project | 一组工作及其成员、工程资源、项目配置和工作约定的范围 | 不替代 Issue 成为单项工作的责任记录 |
| Member | 真实人员，可承担工作、作出业务决定、提供 Runtime 或维护资产 | 身份本身不自动授予所有资源和业务权限 |
| Agent | 可被指派或受邀参与工作的智能执行主体 | 不等于 Runtime，也不天然拥有业务决定权 |
| Main Bot / Coordinator | 现有 Agent 在一个 Issue 上受托持续协调的角色，可自行执行、委派 Worker、选择方法和汇总交付 | 权限来自本项工作约定与当前指派 |
| Worker | Agent 在某次委派中承担执行或核验的角色，按约定交回产物、证据或阻塞原因 | 其权限限于该次委派，业务验收权由工作约定确定 |

成员可自行组织工作。需要 Agent 持续协调时，有权成员在该 Issue 指派并授权一个 Agent 担任 Main Bot。Main Bot 按每份工作的需要选择获准的 Worker。同一 Agent 可以在一个 Issue 担任 Main Bot，在另一份委派中担任 Worker，权限分别取自相应工作约定。

### 3.2 工作与责任对象

| 对象 | 定义 | 事实归属 |
|---|---|---|
| Issue | 一项具有目标、范围、责任和完成要求的业务工作 | Issue 维护当前工作状态、负责人、讨论、决定及交付引用 |
| Sub-Issue | 具有独立负责人、范围和交付要求的 Issue，与父 Issue 建立分工关系 | 子项维护自身生命周期；父项维护整体目标及对其结果的消费 |
| Work Agreement | 某一时点有效的目标、范围、完成要求、责任与约束 | 由有权成员在所属 Issue 上确认或变更；历史版本可追溯 |
| Decision | 对工作范围、授权、例外、接管、门禁或验收作出的明确决定 | 由对应事项的有权主体作出，记录对象、适用版本、范围和后果 |
| Project Workflow | 项目层的 Issue 阶段、步骤指令和负责人交接规则 | 项目配置定义规则；具体 Issue 记录实际发生的阶段与交接 |

**Issue 是业务工作与责任的权威归属。** 评论、通知、Run、SOP 和交付记录都可以关联 Issue，但不能自行改变 Issue 的业务事实，除非通过 Issue 的有效授权入口完成相应写入。

持续委托由 Issue 上的有效指派和工作约定共同表达。约定标明人工总责人、可委派的工作与资源，以及哪些决定由谁保留。对某个 Agent 的一次提及只发出本次协助请求。改派、撤权或 Issue 结束后，原委托停止产生新的协调动作。后来再次委托同一 Agent 时，按新的授权判断历史结果能否采用。

子 Issue 不是 SOP 节点的默认实现。只有当一段工作需要独立负责人、独立交付或独立生命周期时，才建立子 Issue。短时协助和同一责任下的步骤可以留在原 Issue。

### 3.3 方法与能力对象

| 对象 | 定义 | 与工作实例的关系 |
|---|---|---|
| Skill | 可被 Agent 使用的具体能力或指令资产 | 工作选择并投递某个版本 |
| Rule / Principle | 约束行为、质量或决策的规则资产 | 按团队或项目适用范围生效，必要时进入工作约定 |
| Playbook | 帮助负责人或 Agent 分析和推进某类工作的指导方法 | 可按情境选择，不必具有固定节点图 |
| SOP Definition | 具有明确输入、依赖、节点、输出、门禁、返工和交还规则的流程定义 | 发布不可变版本，由 Issue 明确调用 |
| Role | 定义 Agent 在某项工作中的职责边界和预期行为 | 被工作或流程选用，不是独立执行实例 |
| Tool / Harness Configuration | 定义可用工具、宿主能力和执行环境配置 | 受项目、成员、Runtime 和本次授权共同约束 |
| Knowledge | 有来源、适用范围和有效版本的可复用知识 | 按读权和工作上下文需要被检索、引用和使用 |

团队或项目可以维护、发布和采用这些资产。**资产定义不等于一次工作已经使用它。** 必须区分已发布、已采用、已选择、已投递、宿主实际使用等不同事实，并保留各自证据。

### 3.4 流程实例对象

| 对象 | 定义 | 与其他对象的边界 |
|---|---|---|
| SOP Execution | 某个 Issue 调用某个 SOP 发布版本后产生的一次流程实例 | 归属于调用 Issue，不是新的业务工作 |
| Node Activation | 某个流程节点在特定输入、候选和授权下的一次有效进入 | 区分同一节点的不同轮次，防止旧结果推进新一轮 |
| Node Attempt | 节点在一次激活中的具体履行、修正或检查尝试 | 可关联一个或多个 Run，并保留各自结果 |
| Human Gate | 流程请求有权成员针对具体问题和候选作决定的等待点 | 等待与决定归属原 Issue；不是需要伪造 Agent Run 的执行任务 |
| Sub-SOP | 被父流程引用的独立 SOP Execution 及其固定定义版本 | 保留自己的节点状态，结果由父节点按消费契约接收 |

SOP 管理的是**被明确委托的流程范围**。它可以安排节点、判断依赖、消费结果、在授权内返工并交还结果；不能越过授权改变 Issue 的目标、业务责任或完成决定。

Project Workflow 与 SOP 不同：

- Project Workflow 管 Issue 的项目阶段和负责人交接。
- SOP Execution 管一次受托范围内的节点、依赖和结果。
- 两者通过 Issue 上的工作约定、指派和交付结果衔接，不互相嵌套成对方的替代品。

### 3.5 执行资源与记录对象

| 对象 | 定义 | 不代表什么 |
|---|---|---|
| Host | 承载本地进程、账号、代码副本和工具的机器或虚拟机 | 不是工作负责人 |
| Runtime | 成员提供并授权使用的本地执行资源 | 可用不等于当前已领取或已启动工作 |
| Daemon | 连接平台，注册 Runtime、领取工作、准备环境、启停宿主进程并回报结果的本地执行管理进程 | 不拥有 Issue 的业务决定权 |
| Backend / Adapter | 将具体 Agent 宿主协议接入执行链的适配层 | 不等于 Agent 身份或业务角色 |
| Session | 宿主维护的连续会话或线程，可被多个 Run 或 Issue 先后使用 | 不拥有工作归属，不是 Run 的同义词 |
| Run | 沿 Multica 受管派发链实际发生的一次执行记录 | 不等于 Issue、SOP Execution 或节点尝试 |
| AgentObservation | 对宿主活动、消息或工具调用的有来源观察 | 缺乏身份和工作归属依据时，不能自动认定为某个 Run |
| ContextReceipt | 某次执行上下文材料准备与投递的回执 | 证明材料被准备或投递，不自动证明模型逐项读取或实际采用 |

每轮协调（Coordinator Turn）和每次受管的 Worker 执行都沿 Multica 原生 Task / Run 派发链，分别记录执行者、来源、所属 Issue 和实际回执。协调轮次结束后，其他成员 Runtime 上的 Worker 可继续执行。下一轮通过原 Issue 的工作约定、在途 Run 及其谱系、交付与消费记录恢复。Session 可以接续上下文，同一 Session 中的各次执行仍按各自来源归属和计量。

Run 也可服务 SOP 节点、评价或实验。一次 SOP 节点尝试可引用多个 Run。回唤登记将指定事件或时间条件关联到需恢复的 Agent。后续 Task 的排队回执说明协调已安排。Worker 的交付以实际制品和证据为准，Issue 完成时按工作约定核对当前候选及所需决定。

### 3.6 交付与证据对象

| 对象 | 定义 | 关键关系 |
|---|---|---|
| Artifact | 可引用的输入或输出，如代码修订、补丁、报告、文档、样例或附件 | 标识生产者、来源、版本或摘要及可访问位置 |
| Candidate | 一份待检查、接受或退回的具体交付组合 | 绑定一个工作约定版本和一组确定的 Artifact 版本 |
| Evidence | 对某项要求、对象或执行事实的可核查观察 | 记录来源、主体、时间、环境、方法、适用版本和结论 |
| Delivery Record | 一次可追溯的交付记录，组合引用 Candidate、适用要求、制品、检查结论、缺项和决定 | 回答交付了什么、依据什么、由谁生产、当前是否被接受 |

Artifact 可以被多个工作引用，但每次消费都要保留原生产归属和版本。Candidate 不是某个文件名或最新附件，而是明确版本的交付组合。Candidate 变化后，原 Evidence 和检查报告仍指向旧对象；是否适用于新候选必须重新判断。

Evidence 的来源强度不能混为一谈。成员自述、宿主原生记录、文件回读、确定性检查、独立审查和业务决定分别标明来源，不得互相冒充。

### 3.7 评价与改进对象

| 对象 | 定义 | 与业务完成的关系 |
|---|---|---|
| Evaluation | 使用明确评价器和输入证据，对 Run、Candidate、资产或流程作出的评价记录 | 为负责人、维护者或质量门禁提供依据；本身不等于业务验收 |
| Finding | Evaluation 中一条有定位、有依据的问题或观察 | 可被当前 Issue 修正，也可成为改进提案的来源 |
| Improvement Proposal | 对方法、能力、知识或流程提出的可审查变更 | 引用源工作、Finding、拟改资产、预期效果和验证方式 |
| Benchmark | 在固定输入、环境、评价标准和候选版本下进行的可比对照 | 证明候选在声明范围内的实验结果，不替代真实业务效果 |
| Release | 经审核发布的不可变资产版本 | 可供项目采用；发布不等于项目已采用或后续工作已使用 |

Evaluation 的结论、Issue 的验收决定、资产 Release 和 Project Adoption 是不同事实。一个评分通过不自动完成 Issue；一个 Issue 验收通过也不自动发布新方法。

## 4. 对象关系

核心关系可概括为：

- Team 组织 Project 和参与主体；Project 组织 Issue、项目配置和资源。
- Issue 的当前委托确定谁组织工作。Main Bot 的轮次归该 Issue，同项 Worker 的 Run 也归该 Issue；独立子项的 Run 归子项，父项按约定接收子项交付。SOP 受托范围内的节点结果先由该 SOP 消费。
- Issue 可以有 Sub-Issue、Project Workflow 交接和 SOP Execution；这些关系不改变 Issue 作为业务工作归属的地位。
- SOP Execution 固定引用 SOP Definition 版本，包含节点激活和尝试；就绪的执行节点沿 Multica 原派发链产生 Run。
- Run 由 Agent 在获准 Runtime 上执行；Session 提供宿主连续性，但不拥有工作归属。
- Run 或成员工作可产生 Artifact；Artifact 的具体版本组成 Candidate。
- Evidence 针对 Candidate、要求或执行事实；Delivery Record 汇总交付、证据、缺项和决定。
- Evaluation 引用 Run、Candidate 或资产；Finding 可产生 Improvement Proposal，经 Benchmark 和审核形成 Release，再由 Project 采用。

## 5. 工作归属、执行归属与决定权

| 需要回答的问题 | 权威对象或主体 | 规则 |
|---|---|---|
| 这项业务工作是什么、当前到哪里 | Issue | 工作目标、责任、业务状态和完成条件以 Issue 为准 |
| 谁推进当前工作 | Issue Assignee | 同一时点至多一个，可为 Member 或 Agent，按有效指派交接 |
| 谁对业务目标、范围和授权负责 | Accountable Member（Issue Owner） | Agent 受托时，由项目分工或 Issue 上单列的成员关系确定人工总责人 |
| 谁协调这项委托 | 受托持续协调的 Main Bot | 在当前 Issue 的授权范围内组织、接收和汇总，保留事项按工作约定交给有权成员 |
| 哪段流程被委托、走到哪里 | SOP Execution / Node Activation | 只控制明确受托的流程范围；节点进展不替代 Issue 状态 |
| 谁实际执行、执行发生了什么 | Run 及其宿主来源 | 执行 Agent、Runtime 和宿主回执描述该次执行。Run 的 `accountable_user_id` 用于追溯该次执行的人员归因，Issue 总责人及验收人分别从工作约定读取 |
| 哪个会话延续了上下文 | Session | 仅提供宿主连续性，不决定工作或成本归属 |
| 实际交付了什么版本 | Artifact / Candidate / Delivery Record | 固定具体修订或附件版本，不以“最新”代替历史引用 |
| 某项要求是否得到支持 | Evidence / Evaluation | Evidence 保留事实来源；Evaluation 给出有边界的判断 |
| 是否接受本项交付 | Issue 上有权的接受主体及 Decision | 按当前 Candidate 和有效工作约定作决定 |
| 哪个方法可以供后续使用 | 资产维护者发布的 Release、项目采用记录 | 发布、采用和实际使用分别记录 |

## 6. 必须保持的对象不变量

1. 一个 Issue 在同一时点至多有一个当前 Assignee；可以有独立的 Accountable Member、Acceptor 和多个协作者。
2. 一个业务工作只有一个权威 Issue 归属。子 Issue 是独立分工，不因父子关系复制同一份责任。
3. SOP Execution 必须引用调用 Issue、SOP Definition 的固定版本和明确受托范围。
4. Node Activation 必须能区分节点重入、候选变化和新一轮授权；迟到结果只能归属其原激活。
5. Run 是实际执行记录。没有受管执行的人工工作可以有交付记录而没有 Run。
6. Session 可以关联多个 Run；Session 相同不能证明 Run 相同，也不能证明工作归属相同。
7. Artifact 的引用必须能定位具体来源版本；Candidate 必须固定其组成制品版本和适用工作约定。
8. Evidence 和 Evaluation 必须指向明确对象及版本；候选或标准变化后重新判断适用性。
9. Evaluation 不等于 Decision；Release 不等于 Project Adoption；Project Adoption 不等于一次工作实际使用。
10. 任何对象的状态变化只能由其权威主体或已授权机制写入，其他层通过引用和事件消费结果。
11. 同一次委派使用一个有效派发入口。对同一结果的重复回唤可合并协调安排，各个 Worker 的结果仍按原委派和版本分别消费。旧委托产生的回唤仅供核对其原始事实。

## 7. 与其他架构专题的边界

| 专题 | 维护的内容 |
|---|---|
| [工作生命周期](01-unified-work-lifecycle.md) | Issue、责任、分工、业务状态、验收与完成 |
| [SOP 与工作流](02-sop-workflow.md) | SOP Definition、Execution、节点激活、尝试、依赖、返工和出口 |
| [本地执行](03a-execution-plane.md) | Runtime、Daemon、Backend、Session、Run、观察与回报 |
| [能力与上下文](03b-capability-governance.md) | 资产定义、发布、适用范围、项目采用、选择与投递 |
| [成本、质量与改进](04-cost-quality-improvement.md) | Usage、Evaluation、Finding、Proposal、Benchmark 与 Release |
| [统一工作台](05-unified-workbench.md) | 从各权威来源读取对象，呈现判断并调用拥有决定权的入口 |

如果专题需要引入新对象，必须说明它属于哪一组、由谁维护事实、与现有对象的关系，以及为什么不能沿用现有对象。不得仅为页面、按钮或某个案例增加新的领域对象。
