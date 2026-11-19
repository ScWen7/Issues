# AgentPlatform · 核心业务对象与统一关系模型

## 1. 建模目标与结论

本模型统一团队知识、产研工作、Harness、执行、交付、评价与持续改进的业务对象和事实归属。它承接[产品定位与总体设计基线](product-foundation.md)及[团队知识管理与研发知识闭环](knowledge-management-lifecycle.md)，并作为各专题对象定义的统一依据。

建模的首要目标不是增加对象，而是明确：
- 哪些事实已经有权威来源，必须直接引用；
- 哪些事实需要平台独立维护；
- 哪些内容只是来源、证据或派生视图；
- 哪些对象有独立生命周期，哪些只是关联、版本或处理状态；
- 同一份研发事实如何同时服务交付、知识和 Harness，而不复制权威记录。

**核心结论：保留现有 Issue / Run / Artifact / Candidate / Evidence / Evaluation / Finding / Proposal / Benchmark / Release / Project Adoption 主线；为知识管理补齐来源、证据锚点、知识条目与修订等必要对象；Harness 与知识共享资产版本、发布和采用的公共机制，但保持不同内容模型、治理规则和责任人。**

本模型定义业务概念和关系，不定义数据库表、API、消息队列或部署结构。

## 2. 统一建模原则

1. **权威来源优先。** 飞书、Git、Issue、宿主和项目系统仍是各自原始事实的权威来源。平台保存来源身份、修订、可定位快照和处理结果，不冒充原文或代码的权威维护者。
2. **工作主线唯一。** Issue 是一项业务研发工作的唯一归属。知识整理、解析、评价和 Benchmark 不产生平行的研发 Issue；其处理记录挂靠原来源、批次或治理活动。
3. **事实与解释分开。** 原始资料、证据、知识结论、Harness 规则、Evaluation 判断和业务 Decision 是不同语义。模型生成的摘要或归因不能冒充来源证据。
4. **内容、版本、发布、采用、使用分开。** 稳定身份标识一个知识或 Harness 资产；不可变 Revision 固定内容；Release 使经治理的版本可供选用；Project Adoption 表达项目决定；Work / Run 记录本次选择、投递和可观察的实际使用。
5. **证据可复用，结论有边界。** 同一份证据可以被交付核验、知识提炼和 Harness 评价引用。不同结论分别记录自己的标准、推理和责任人，不重复复制证据，也不共享一个含糊的“通过”状态。
6. **按来源与用途区分权限。** 读取原文、处理内容、生成派生知识、向特定受众发布、向 Agent 投递是不同授权。来源可见不自动意味着派生和跨项目发布许可。
7. **生命周期局部自治。** 各对象维护自己的状态，通过明确关联和事件协作；不建立覆盖知识、Issue、Run 和发布的总状态机。
8. **普通研发低摩擦。** 知识和 Harness 按工作需要进入 Issue，不要求所有工作先创建知识任务、SOP 或 Evaluation。

## 3. 统一对象分类

| 对象域 | 核心对象 | 权威事实 |
|---|---|---|
| 组织与范围 | Team、Project、Member、Agent、Project Configuration / Adoption | 成员关系、项目范围、项目采用和配置 |
| 来源管理 | Source Connection、Source Item、Source Revision、Ingestion Batch | 外部来源身份、连接授权、发现 / 同步和取得修订 |
| 知识资产 | Knowledge Item、Knowledge Revision、Knowledge Release（复用 Release）、Knowledge Feedback | 可复用知识内容、修订、发布和质量反馈 |
| Harness 资产 | Harness Asset、Harness Revision、Harness Release（复用 Release） | 原则、规则、Skill、Playbook、Workflow、SOP、Script、Evaluation 定义及其发布版本 |
| 产研工作 | Issue、Work Agreement、Decision、Project Workflow | 目标、责任、当前业务上下文、项目阶段与决定 |
| 流程实例 | SOP Execution、Node Activation、Node Attempt | 明确受托流程的运行状态、节点进入和尝试 |
| 执行与观察 | Multica Task / Run、Runtime、Session、AgentObservation、Usage | 实际受管执行、宿主连续性、可观察活动和原生计量 |
| 交付与证据 | Artifact、Candidate、Evidence、Evidence Anchor、Evidence Applicability、Delivery Record | 不可变交付版本、证据事实及其适用关系 |
| 评价与改进 | Evaluation、Finding、Improvement Proposal、Benchmark、Budget Reservation | 独立评价、问题归因、候选变更、对照结果和治理预算 |
| 横向消费记录 | ContextReceipt、Work / Run Asset Pin、Asset Usage Observation | 某次工作选择、投递和可观察使用哪些知识 / Harness 版本；知识反馈仍归 Knowledge Feedback |

分类是业务概念边界，不要求一对象一表、一模块一服务。后文说明哪些名称是独立对象，哪些只是现有对象的属性或关联。

## 4. 来源与知识对象

### 4.1 Source Connection 与 Source Item / Revision

| 对象 | 职责 | 关键边界 |
|---|---|---|
| Source Connection | 表示对某个外部系统、仓库、目录或来源范围的持续连接与授权 | 管连接身份、授权状态、同步策略 / 游标和最近核对时间；不等于资料已取得、已解析或可检索 |
| Source Item | 表示来源中的一项稳定内容身份，如飞书文档、Git 仓库文件、网页或某个可引用业务记录 | 同一 Item 可有多个 Revision；来源原始身份由来源系统决定 |
| Source Revision | 固定某一时点取得的内容版本、元数据和可核对摘要 | 不可被新内容覆盖；可以是来源原生版本，也可以是标明抓取时间和内容摘要的平台快照 |
| Ingestion Batch | 将一次显式导入或一轮同步发现的多个 Source Item 组织为共同处理范围 | 仅用于处理批次和进度；不承担 Issue、Task 或 Run 的工作编排 |

资料 Inbox 是用户入口和处理视图，不是另一套任务对象。单次上传、URL 或灵感可直接形成 Source Item / Revision；持续同步来源通过 Connection 发现 Item / Revision。上传文件本身不是来源连接。

解析、OCR、同步和索引任务可沿现有受管执行能力运行，保存处理结果和失败回执；不因知识处理建立第二套 Task / Run / Runtime 控制平面。解析器版本、处理方式和覆盖范围属于处理记录的来源信息。

### 4.2 Evidence Anchor 与 Evidence

**Evidence Anchor** 是证据在来源修订中的稳定定位，例如文档块、标题路径、页码、表格范围、代码符号 / 行范围、Issue Comment、Run 回执或 Artifact 位置。它解决“在哪里”，不单独表达“证明什么”。

**Evidence** 是对某项可核验事实的不可变观察或证据记录，引用来源身份、Revision、Anchor、内容摘要、取得方式、时间、主体和可信等级。它解决“实际观察到了什么”。Evidence 可以来自：
- Source Revision 中的原文段落、表格、代码和页面；
- Issue 上有权成员确认的决定或反馈；
- Run / AgentObservation / Usage 的宿主回执；
- Artifact 的具体版本和文件回读；
- 测试、检查、独立审查和 Evaluation 的结果。

不需要为每个文本块都创建独立 Evidence 业务记录。解析块和 Anchor 是检索 / 定位结构；当某个片段被引用来支持结论、检查或评价时，建立可追溯的 Evidence 引用或记录。

Evidence 的生产来源、观察事实和后续解释分开。成员自述、来源原文、宿主原生回执、确定性测试、独立审查和模型判断具有不同证明强度，不能互相替代。

### 4.3 Knowledge Item 与 Knowledge Revision

| 对象 | 职责 | 关键边界 |
|---|---|---|
| Knowledge Item | 表示一个稳定的知识主题 / 结论身份，如一条技术经验、业务约定或踩坑经验 | 标识持续存在的知识概念；不直接承载可变正文 |
| Knowledge Revision | 固定该知识在某一修订下的完整正文、类型、适用范围、证据引用、维护者和有效性声明 | 不可变；修订不会覆盖旧版本 |
| Knowledge Release | 使特定 Knowledge Revision 经核验后成为可供指定范围消费的正式知识版本 | **复用既有 Release 语义**，不是另建一套通用发布系统；但使用知识专属核验和派生许可规则 |
| Knowledge Feedback | 记录使用者对具体知识修订的有帮助、无关、过期、错误、冲突或缺失反馈 | 反馈是质量信号，不自动改写正式知识或替代维护者决定 |

知识类型包括事实 / 约定、决策 / 理由、实践 / 方法、问题 / 踩坑经验、解释 / 导航和待确认认识。知识范围包括团队、项目；代码知识可作为项目知识中的专门类型或独立视图，必须绑定仓库和代码基准，不要求先建立独立代码知识产品。

Team Knowledge 与 Project Knowledge 使用相同的 Knowledge Item / Revision / Release 语义，但 Knowledge Item 的归属范围分别为 Team 或单一 Project，维护责任和默认可见范围随归属确定。适用范围是知识可用于哪些项目、系统、版本或工作条件，不等于成员访问权限；Evidence 原文权限和来源派生许可还须独立核验。

Project Sources（如 PRD、接口文档、项目决策原文）继续由 Source Item / Revision 指向原权威系统，工作可直接引用，不要求先创建 Project Knowledge。只有需要跨 Issue 长期复用、并由项目责任人维护的结论才形成 Project Knowledge。

Project Code Knowledge / Code Wiki 是可选的项目代码认知视图，绑定仓库与 Commit / Tree 基准；模块地图、调用关系和当前实现事实不自动成为 Knowledge Item。若从代码事实提炼出需要长期维护的业务不变量、架构决策或经验，再按其 Team / Project 作用域形成正式知识。

Team Knowledge 被 Project 引用时保留原 Knowledge Item / Revision / Release 身份，不复制正文或转移维护权。一般检索和引用不要求每条知识都创建 Project Adoption；只有项目需要将某一发布版本固定为持续采用基线时，才通过既有 Project Adoption / Project Configuration 采用。项目知识跨项目复用必须形成新的 Team Knowledge 候选并重新完成来源派生授权、去敏、适用性核验和团队发布，不得直接修改原 Project Knowledge 的作用域。

Knowledge Revision 必须引用支持结论的 Evidence，并声明适用范围、限制、反例、有效状态和最近核验依据。证据不足的内容只能保持待确认认识，不得以正式强制知识投递。

知识消费沿用上述对象，不新增 Recall Result 或 Knowledge Access Asset：Recall 发现 Knowledge Item / Revision / Release 候选；Read 按稳定 Revision 身份读取正文；Evidence Reference 与 Evidence 原文展开分别核验权限；本项实际采用的重要版本通过既有 Work / Run Asset Pin 固定；ContextReceipt 和 Asset Usage Observation 分别记录投递及可观察消费。命中、预览或读取本身不自动创建 Pin，也不代表实际使用。具体业务语义见[Knowledge Consumption Contract](../research/knowledge-consumption-contract.md)。

### 4.4 知识治理与来源许可

知识发布至少检查：
- 结论是否被引用证据支持，事实与推断是否分开；
- 来源是否当前可读、版本是否明确、证据位置是否稳定；
- 项目私有内容是否获得派生和目标受众许可；
- 适用范围、版本条件、例外和不适用场景是否明确；
- 是否重复、冲突或替代已有知识；
- 维护者和复核责任是否明确。

来源读权、处理许可、派生许可和受众发布许可分别核对。来源权限撤回时，受影响的派生知识停止新的投递并进入复核；历史工作仍保留当时的版本与共享事实，查看原文继续受当前权限控制。

## 5. Harness 资产对象与知识的边界

Harness Asset 是可治理方法资产的稳定身份；Harness Revision 固定某一版原则、Rule、Skill、Playbook、Workflow / SOP、Script、Scorer / Rubric 或其他工程方法内容。它们按类型使用不同的内容结构和验证方式。

Harness Release 复用既有 Release 机制，固定一份已审核发布的 Harness Revision 及依赖。资产维护者、审核标准和可用范围按资产类型配置。

知识与 Harness 共享：
- 稳定资产身份与不可变修订的版本原则；
- Release 的发布记录和撤回 / 退役语义；
- Project Adoption 对项目采用版本的决定机制；
- Work / Run 对实际选择、投递和使用版本的引用方式。

知识与 Harness 不共享：
- 内容模型：知识是可核查的事实、经验和解释；Harness 是可执行或可评估的方法、约束和规则。
- 核验标准：知识核验证据真实性、适用范围、时效和来源许可；Harness 核验行为效果、兼容性、质量门槛和回归。
- 治理责任：知识维护者不自动拥有 Skill / SOP 发布权；Harness 维护者也不能擅自确认业务事实。
- 评价方式：知识质量关注正确性、可检索性、时效和复用效果；Harness 质量关注执行效果、交付质量、安全、成本和回归。

不建立一个把 Knowledge、Skill、SOP、Evaluation、Project Configuration 混为一类的通用内容对象。共享的是最小发布与采用机制，不是内容本身。

## 6. 工作、上下文与执行对象

现有工作对象保持不变：

- **Issue**：业务目标、责任、讨论、决定、工作状态和完成要求的唯一权威归属。
- **Work Agreement**：Issue 在某一时点有效的目标、范围、完成条件、责任和约束版本。
- **Decision**：有权主体对业务范围、例外、接管、门禁或验收作出的决定。
- **Project Workflow**：项目级阶段、步骤和负责人交接规则；具体发生记录附着原 Issue。
- **SOP Definition / Release**：可复用流程方法定义及发布版本；不等于某次工作实例。
- **SOP Execution / Node Activation / Node Attempt**：一次明确委托的流程范围、节点进入和履行尝试；不成为平行 Issue。
- **Task / Run**：沿 Multica 原生执行链记录实际受管执行；Run 可以服务生产、SOP、Evaluation 或 Benchmark，Purpose 与来源业务身份区分用途。
- **Runtime / Session**：Runtime 是本地执行资源，Session 是宿主连续性；都不拥有 Issue 业务责任。

知识和 Harness 如何进入工作：
1. Issue / Project 给出范围、目标、工作类型、当前阶段和责任。
2. Work Context Preparation 根据接收者权限检索适用知识、资料和 Harness Release。
3. Work / Run Asset Pin 固定本次选择的 Knowledge Revision / Release 与 Harness Release / 配置版本。
4. ContextReceipt 记录材料准备和投递回执；宿主可观察证据再证明加载或实际使用，不能从投递推断使用。
5. Run、交付和人工反馈继续沿原工作主线记录。

Work / Run Asset Pin 是附着现有工作或执行的版本引用，不是独立知识任务，也不是新的业务工作对象。无需为每次知识命中都创建 Pin；只有被明确选用并参与工作约定或执行上下文的版本才需要固定引用。

## 7. 交付、证据、评价与改进对象

保留现有对象定义：
- **Artifact**：可引用的具体交付或输入制品版本。
- **Candidate**：固定一项 Issue 送审的 Artifact 组合及适用工作约定。
- **Evidence**：针对具体对象、要求或执行事实的可核验观察。
- **Evidence Applicability**：说明原 Evidence 是否仍适用于另一个 Candidate / 标准版本。
- **Delivery Record**：从原权威事实重建交付过程的视图，不是第二权威记录。
- **Evaluation**：使用固定目标、评价器、标准和输入证据形成的独立评价。
- **Finding**：Evaluation 或其他有依据观察中定位明确的问题、机会或缺陷。
- **Improvement Proposal**：对知识、Harness、流程、Runtime / Tool 或项目配置提出的可审查变更。
- **Benchmark**：对候选与基线进行固定样本、环境和标准下的可比对照。
- **Budget Reservation**：评价和实验等治理活动的资源预留；实际消耗仍来自原生 Task / Usage。
- **Release**：资产维护者发布的不可变版本；按资产类型固定 Knowledge Revision 或 Harness Revision。
- **Project Adoption**：有权项目成员决定在项目范围采用哪个 Release 或项目配置版本。

同一 Finding 可以引用同一组 Evidence，并产生不同改进路径：
- Knowledge Proposal：核验、修订或新建 Knowledge Revision，按知识规则发布。
- Harness Proposal：修改 Harness Revision，以回归和 Benchmark 验证后发布。
- Runtime / Tool Proposal：修复适配、观察或工具能力。
- Project / Work Decision：回到原 Project Configuration 或 Issue，由有权成员决定。
这些路径是 Improvement Proposal 的目标类型和独立候选修订，不是新增平行工作系统。若同一提案跨越多种资产，发布和采用仍按各自权威维护者分别完成。

## 8. 统一对象关系

### 8.1 关系总览

~~~mermaid
flowchart TD
  Team[Team / Project]
  Conn[Source Connection]
  Item[Source Item]
  Rev[Source Revision]
  Anchor[Evidence Anchor]
  Ev[Evidence]
  KI[Knowledge Item]
  KR[Knowledge Revision]
  HR[Harness Asset / Revision]
  Rel[Release]
  Adopt[Project Adoption]
  Issue[Issue / Work Agreement]
  Pin[Work / Run Asset Pin]
  Receipt[ContextReceipt]
  Run[Multica Task / Run]
  Art[Artifact]
  Cand[Candidate]
  Eval[Evaluation]
  Finding[Finding]
  Proposal[Improvement Proposal]
  Bench[Benchmark]
  Team --> Issue
  Team --> Conn
  Conn --> Item
  Item --> Rev
  Rev --> Anchor --> Ev
  Run --> Ev
  Art --> Ev
  Issue --> Ev
  Ev --> KR
  KI --> KR
  KR --> Rel
  HR --> Rel
  Rel --> Adopt
  Issue --> Pin
  Adopt --> Pin
  KR --> Pin
  HR --> Pin
  Pin --> Receipt
  Receipt --> Run
  Run --> Art --> Cand
  Cand --> Eval
  Run --> Eval
  Ev --> Eval
  Eval --> Finding
  Finding --> Proposal
  Proposal --> KR
  Proposal --> HR
  Proposal --> Bench
  Bench --> Rel
  Rel --> Adopt
~~~

图表达业务引用，不表示所有关系都要同步创建或所有研发都必须经过每个节点。Project Adoption 可以选择知识或 Harness Release；Work Pin 记录本项实际选用的版本。Evidence 可以由不同来源产生，并被多个消费者引用。

### 8.2 关键关系表

| 起点 | 关系 | 终点 | 语义 |
|---|---|---|---|
| Source Connection | discovers | Source Item | 连接发现来源内容 |
| Source Item | has revisions | Source Revision | 一个来源内容有多个不可变修订 / 快照 |
| Source Revision | locates | Evidence Anchor | 解析结构保留原文位置 |
| Evidence Anchor | supports | Evidence | 证据引用可定位的来源内容 |
| Knowledge Item | has revisions | Knowledge Revision | 稳定知识身份对应多个修订 |
| Knowledge Revision | supported by | Evidence | 知识结论由一份或多份证据支持 |
| Knowledge Revision | published as | Release | 经知识治理的修订成为正式可用版本 |
| Harness Asset | has revisions | Harness Revision | 稳定方法资产对应多个修订 |
| Harness Revision | published as | Release | 经方法验证与审核的版本可供选用 |
| Release | adopted by | Project Adoption | 项目有权成员决定采用的版本与范围 |
| Issue / Project | selects | Work / Run Asset Pin | 当前工作固定实际选用的知识和 Harness 版本 |
| Work / Run Asset Pin | delivered through | ContextReceipt | 记录材料准备与投递事实 |
| Run / Issue / Artifact / Source | produces or anchors | Evidence | 执行、决定、制品或来源提供可核验事实 |
| Run / Candidate / Asset | evaluated by | Evaluation | 评价固定目标、标准和输入快照 |
| Evaluation | identifies | Finding | 形成可行动的观察 |
| Finding | motivates | Improvement Proposal | 提出知识、Harness 或其他改进 |
| Improvement Proposal | tested by | Benchmark | 对候选修订进行可比验证 |
| Benchmark | supports release | Release | 实验结果为发布审核提供证据，不自动发布 |
| Release | used in | Work / Run | 由工作选择、投递和可观察使用回执证明 |

### 8.3 不创建的重复对象

| 不单独创建 | 沿用什么 | 原因 |
|---|---|---|
| 知识处理 Issue / Task 队列 | Source Item、Ingestion Batch 与现有受管 Run / 处理回执 | 资料处理不是团队业务工作，不需要第二套工作队列 |
| Wiki Page 作为新的权威来源 | Knowledge Item / Revision，原文继续由 Source Item / Revision 指向 | 避免 Wiki 复制飞书、Git 或项目系统的权威正文 |
| 每个 Chunk 一个知识对象 | 解析结构、Evidence Anchor 与按需 Evidence | 分块是检索和定位结构，不是知识资产身份 |
| Knowledge Release 专属发布系统 | 通用 Release + Knowledge Revision 类型与知识治理规则 | 复用发布版本能力，保留知识特有审核 |
| Harness Release 专属发布系统 | 通用 Release + Harness Revision 类型与 Harness 验证规则 | 同上 |
| 第二套 Project Adoption | 现有 Project Adoption，引用 Knowledge / Harness Release | 项目采用机制相同，内容和权限策略按资产类型校验 |
| 第二套 Knowledge Run / Runtime | Multica 原生 Task / Run / Runtime | 同一执行事实和计量入口 |
| 通用知识使用 Task | Work / Run Asset Pin、ContextReceipt、宿主 Observation 和 Knowledge Feedback | 使用记录附着工作，不创建额外工作 |
| 通用全局 Candidate | Issue 交付 Candidate 与 Proposal 内的改进候选修订各自保留 | 交付内容与拟发布资产变更语义不同 |
| 独立 Evidence 仓库复制原始材料 | 来源修订与可定位 Evidence 引用 | 避免证据与原文脱离或重复存储权威内容 |

## 9. 生命周期与状态归属

生命周期属于各自权威对象，不建立统一总状态机。

| 对象 | 核心生命周期 / 状态 | 状态权威 |
|---|---|---|
| Source Connection | 已授权、同步中、部分失败、失效、断开 | 来源连接与授权管理 |
| Source Item / Revision | 已发现、待取得、已取得、修订变化、撤回 / 删除 | 来源系统及取得快照 |
| Ingestion Batch / Processing | 待处理、取得中、解析中、部分完成、完成、失败 | 对应批次和处理回执 |
| Evidence | 已记录、可用、待复核、失效 / 不可访问 | 来源修订、权限和证据核验事实 |
| Knowledge Item | 活跃、合并、替代、退役 | 知识维护者决定 |
| Knowledge Revision | 草拟、待核验、已核验、驳回、待复核、失效 | 修订治理记录 |
| Knowledge Release | 已发布、暂停投递、撤回、退役 | 知识发布者与来源授权 |
| Recall Projection（派生处理状态，不是业务对象） | Pending、Building、Current、Stale、Unavailable、Failed | 由检索投影处理回执表达；不改变 Knowledge Release，不拥有知识内容、权限或发布资格 |
| Harness Asset / Revision | 沿既有能力资产生命周期 | 对应资产维护者 |
| Release / Project Adoption | 沿既有发布和项目采用生命周期 | 资产维护者 / 项目有权成员 |
| Issue / SOP / Run / Candidate / Evaluation / Proposal / Benchmark | 沿现有生命周期专题 | 对应原权威对象 |

“可检索”是知识修订 / 发布在特定索引和权限范围内的处理可用状态，不等于正式发布；“证据可用”也不等于结论正确。来源修订变化时可以暂时标记旧知识待复核，但是否停止投递取决于风险、权威来源变化和适用策略。



Knowledge Release 与 Recall Projection 必须分离：Release 是正式发布决定；Projection 是从正式知识派生的可重建检索视图。投影更新失败不撤销 Release，Release 暂停 / 撤回时则立即阻止旧投影命中被返回，投影清理可异步。Recall 返回前必须按权威 Knowledge Item / Revision / Release 和当前 Membership / Policy 回查候选，不能直接向调用者暴露投影中的标题、摘要、Claim 或 Evidence 元数据。

Recall 覆盖状态（Complete + Hits / Complete + No Match / Partial or Stale / Unavailable or Failed）属于本次查询的运行结果，不新增业务对象。只有 Complete + No Match 才能表达“当前声明范围检索完整但没有找到知识”；部分覆盖和检索失败不得伪装成空结果。

## 10. 共享事实的权威归属与写入权

| 事实 | 权威来源 / 对象 | 其他能力如何引用 |
|---|---|---|
| 原始文档、代码和外部记录正文 | 原来源系统 | Source Item / Revision 固定身份与快照 |
| 来源连接与同步授权 | Source Connection 及来源授权主体 | 处理流程读取当前连接状态和授权 |
| 解析位置和证据 | Source Revision / Evidence Anchor / Evidence | 知识、交付和 Evaluation 通过引用使用 |
| 知识正文和适用范围 | Knowledge Revision | 检索和 Work Pin 引用固定修订 |
| 知识正式发布 | Knowledge Release（通用 Release 的知识类型） | Project Adoption / Work Pin 引用 |
| Harness 方法正文和版本 | Harness Revision | 执行上下文固定所用版本 |
| Harness 正式发布 | Harness Release（通用 Release 的 Harness 类型） | Project Adoption / Work Pin 引用 |
| 项目采用哪个版本 | Project Adoption / Project Configuration | 新工作按有效范围选择；在途工作保留固定版本 |
| 当前工作目标、决定和责任 | Issue / Work Agreement / Decision | SOP、Run、知识提炼和交付引用 |
| 实际执行与原生计量 | Multica Task / Run / Usage | 评价和分析引用，不复制执行账本 |
| 实际交付版本 | Artifact / Candidate | 知识和评价引用证据，不改变交付事实 |
| 评价结论与 Finding | Evaluation / Finding | Issue、知识维护者和 Harness 维护者分别消费 |
| 改进候选与 Benchmark | Improvement Proposal / Benchmark | 对应维护者决定发布或调整 |
| 业务验收 | Issue 上有权主体的 Decision | 不被 Evaluation 或 Release 替代 |

跨对象流程按各权威对象本地写入、稳定来源身份、可重试消费和对账恢复。不假设全局事务。来源变化、权限撤回或候选换版时，只重算受影响的引用和消费关系，不覆盖历史事实。

## 11. 用一条研发链检验模型

以一次新项目需求为例：

1. 项目连接已有飞书需求来源。平台发现 Source Item，取得 Source Revision，解析标题、块和表格，形成可定位 Evidence。
2. 需求事实和项目既有决策被整理为 Knowledge Revision。项目知识维护者核对来源、范围和冲突后发布 Knowledge Release。
3. 新 Issue 建立后，按项目、目标和研发阶段检索相关团队知识、项目知识和 Harness Release。负责人确认适用约束，工作记录固定被选用的版本；ContextReceipt 证明材料是否成功投递。
4. Agent 在成员获准 Runtime 上执行。Multica Run 记录真实执行；Run、测试和交付产生 Artifact 与 Evidence；Candidate 固定送审版本。
5. 验收者依据当前 Work Agreement、Candidate 和 Evidence 作业务 Decision。Evaluation 可以独立检查质量，但不能替代验收。
6. 研发中发现一项历史资料未说明边界条件。Finding 引用当前 Issue、Run、测试结果和旧 Knowledge Revision；当前 Issue 先完成修正。
7. 知识维护者形成 Knowledge Revision 新版本，补入边界条件并核验发布。若该问题还暴露 Harness 缺少强制边界检查，则另形成 Harness Revision 候选，用回归样本和 Benchmark 验证后独立发布。
8. 项目有权成员分别决定是否采用新 Knowledge Release 和 Harness Release。下一项研发工作固定引用新版本，之后的使用反馈和生产结果用于判断两个改进是否有效。

同一份测试结果和执行证据可被交付验收、知识提炼和 Harness Evaluation 共同引用；它们各自形成自己的结论和决定，不复制 Run、Artifact 或 Evidence 权威记录。

## 12. 架构验收条件与后续顺序

本模型只有在以下问题都能被一致回答时才算收敛：

- 原始资料的权威在哪里，平台取得了哪一版，权限和同步状态是什么？
- 证据能否回到来源修订和精确位置，哪些只是解析结果或模型推断？
- 一条知识由什么证据支持，谁维护、谁发布、适用于谁、何时失效？
- Harness 与知识共享什么机制、分别由谁治理，如何避免重复维护同一规则？
- Issue 如何按工作意图和权限消费知识与 Harness，如何固定本次实际版本？
- Run、Artifact 和 Evidence 如何被交付、知识和 Evaluation 多方引用？
- Finding 如何路由到知识、Harness、项目配置、Runtime / Tool 或当前工作修正？
- 发布、项目采用、实际投递、宿主加载、实际使用和效果观察是否各自有清晰证据？
- 是否避免新增平行 Issue、Task、Run、Runtime、Candidate、Release 和 Project Adoption 系统？

后续设计顺序：
1. 将本模型与现有核心对象、生命周期和一致性文档逐项对照，消除重复定义和冲突。
2. 按统一对象关系重新映射整体能力域和模块边界，决定现有 A–I 与五层如何合并 / 调整。
3. 补齐知识相关生命周期、事件和权限变化对引用的影响。
4. 用不同来源类型、不同研发任务和不同失败路径验证模型。
5. 完成整体架构一致性审查后，才进入技术承载和工程切片。

本阶段不决定具体存储、索引、检索引擎、Schema、API 或部署形态。
