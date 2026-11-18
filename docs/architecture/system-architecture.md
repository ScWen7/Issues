# AgentPlatform · 整体系统架构与能力边界

## 1. 架构目标

AgentPlatform 是面向研发团队的 AI 研发能力平台。系统把团队知识、产研工作、Engineering Harness 和成员本地 Agent 执行连接起来，使团队经验能进入实际研发，研发过程受到适当管控，真实结果反过来改善知识与 Harness。

整体架构围绕两个相互促进的飞轮组织：

- **团队知识飞轮**：已有知识 → 研发消费 → 新事实与经验 → 提炼治理 → 可复用知识。
- **Harness 进化飞轮**：Harness 指导研发 → 观察与评价 → Finding → 改进候选 → 对照验证 → 发布与采用 → 真实效果回收。

Issue 是研发工作主线；知识和 Harness 是两个独立治理的基础能力域；Multica 是既有协作执行底座；交付证据和 Evaluation 让两个飞轮与实际研发相连。

本架构定义能力职责、事实归属、依赖关系和端到端数据流，不预设一模块一服务、一对象一数据表，也不决定数据库、API、消息队列或部署拓扑。

## 2. 总体架构视图

~~~mermaid
flowchart TB
  People["团队成员 / 项目维护者 / Agent"]
  UI["统一工作台 · 查询、导航与操作入口"]

  subgraph Core["AgentPlatform 核心能力域"]
    Org["组织与项目治理"]
    Knowledge["团队知识管理"]
    Work["产研工作协作"]
    Harness["Engineering Harness 治理"]
    Flow["研发流程与 SOP 执行"]
    Execution["执行集成与 Runtime 观测"]
    Evidence["交付与证据"]
    Evolution["Evaluation、度量与持续改进"]
  end

  subgraph External["权威来源与成员本地环境"]
    Sources["飞书 / 文档 / Git / 代码仓 / 外部资料"]
    Multica["Multica · Project / Issue / Task / Run / Runtime / Usage"]
    Hosts["Codex / Claude Code / Qoder / CodeBuddy 等本地宿主"]
  end

  People --> UI
  UI --> Org
  UI --> Knowledge
  UI --> Work
  UI --> Harness
  UI --> Evidence
  Org --> Knowledge
  Org --> Work
  Org --> Harness
  Org --> Execution
  Sources --> Knowledge
  Sources --> Evidence
  Knowledge --> Work
  Knowledge --> Harness
  Work --> Harness
  Harness --> Flow
  Work --> Flow
  Flow --> Execution
  Work --> Execution
  Multica <--> Execution
  Hosts <--> Execution
  Execution --> Evidence
  Work --> Evidence
  Evidence --> Evolution
  Execution --> Evolution
  Knowledge --> Evolution
  Harness --> Evolution
  Evolution --> Knowledge
  Evolution --> Harness
  Evolution --> Work
~~~

图中的箭头表示业务依赖、事实引用或反馈，不表示所有 Issue 都要经过全部模块，也不表示同步事务。

## 3. 核心能力域

### 3.1 组织与项目治理

**职责：确定谁在什么范围内工作，以及哪些资源和资产可以被采用。**

维护：
- Team、Project、Member、Agent 的组织关系；
- 项目成员、访问范围和资源授权；
- 项目级配置、Project Workflow 选择和 Evaluation Policy；
- Project Adoption：有权成员决定项目采用哪个已发布知识或 Harness Release，以及生效范围和在途工作处理。

不维护 Issue 的业务进展、知识正文、Harness 内容、Run 终态或评价结论。组织与项目治理提供身份、范围、权限和采用决定，其他能力域按需消费。

### 3.2 团队知识管理

**职责：把团队已有资料和研发中新产生的经验，转化为可追溯、可检索、在适用范围内可复用的知识。**

维护：
- Source Connection、Source Item、Source Revision 和 Ingestion Batch；
- 取得、解析、OCR、结构定位、索引和处理回执；
- Evidence Anchor 与知识处理所需的来源证据引用；
- Knowledge Item、Knowledge Revision、知识核验与发布申请；
- 来源许可、适用范围、知识有效性、冲突、替代、撤回和反馈；
- 面向 Team / Project / Issue 的检索与知识消费记录。

权威来源仍由飞书、Git、代码仓和其他原系统维护。平台管理连接、取得快照、证据定位、知识派生和复用，不覆盖原始资料。团队知识、项目知识、项目代码知识有不同适用范围；Issue 工作上下文不复制成知识条目。

不维护：
- 原始 PRD、代码或外部文档的权威正文；
- 当前 Issue 的目标和决定；
- Harness 的强制规则正文；
- 第二套资料处理 Issue / Task / Run 控制面。

### 3.3 产研工作协作

**职责：承载研发目标、责任、上下文、协作决定和交付消费，是产研工作主线。**

维护或沿用：
- Project / Issue、Work Agreement、Assignee、Accountable Member 和 Decision；
- Issue 讨论、父子分工、一次性协助和持续委托；
- Project Workflow 的阶段与责任交接；
- 当前工作对知识、Harness、SOP、Run、Artifact、Candidate 和 Evidence 的引用；
- 当前候选的业务验收、退回、完成和取消决定。

Issue 是一项研发工作的唯一业务归属。成员可自行推进；一次性 @Agent 只请求本次协助；持续协调时，成员在原 Issue 上向现有 Agent 授权 Main Bot 职责。是否拆子 Issue、委派 Worker 或调用 SOP，由负责人按实际需要决定。

不把 Main Bot、Squad 或 Task 平铺提升为产品的顶层组织模型。成员保留业务总责；Agent 协调权来自本项有效授权。沿用 Multica 的 Issue 与指派机制，不复制工作控制平面。

### 3.4 Engineering Harness 治理

**职责：把团队认可的研发方法转化为可选用、可执行、可验证、可演进的工程资产。**

维护：
- Principles / Rules：必须满足的约束及适用范围；
- Skills：Agent 可调用的具体能力；
- Playbooks：指导某类工作的分析与推进方法；
- Workflow / SOP Definition：稳定阶段、依赖、输入输出、门禁、返工和交还契约；
- Scripts / Tools / Harness Configuration：确定性检查和执行工具约定；
- Scorer / Rubric / Evaluation Definition：质量评价标准与回归要求；
- 各类 Harness Revision、发布审核和 Harness Release。

Harness 可以引用团队知识作为依据，但知识正文与规则正文分别治理。经验只有在补齐适用范围、执行方式、例外和验证标准后，才适合转化为 Harness。Harness 资产发布不自动改变项目采用，也不证明某次工作已经加载或使用。

### 3.5 研发流程与 SOP 执行

**职责：运行明确委托的稳定流程范围，把 Harness 中定义的流程方法落实到具体工作。**

维护：
- SOP Execution、Node Activation、Node Attempt；
- 节点依赖、就绪条件、输入候选、输出契约、结果消费；
- 定向返工、人工门禁、等待、恢复和流程出口。

边界：
- Project Workflow 管 Issue 的项目阶段和负责人交接。
- Playbook 指导负责人或 Agent 如何判断和推进，不要求固定节点图。
- SOP 执行被明确委托的稳定流程范围，负责其内部节点和结果，不接管 Issue 的业务总责。
- 实际节点执行沿 Multica 原生派发链产生 Run；流程模块不创建第二套执行队列或 Runtime。

### 3.6 执行集成与 Runtime 观测

**职责：连接成员获准的本地 Agent 和工具，记录真实执行及宿主可观察事实。**

沿用 Multica 的 Project / Issue / Task / Run / Runtime / Daemon / Backend / Session / Usage 能力，AgentPlatform 补充跨层业务关联和确实缺失的宿主适配。

负责：
- 把 Issue 或 SOP 的有效授权安排交给原生执行入口；
- 将 Run 与 Issue、SOP Attempt、Evaluation 或 Benchmark 的业务来源关联；
- 适配 Codex、Claude Code、Qoder、CodeBuddy 等不同宿主；
- 采集宿主可提供的消息、工具调用、文件、终态和原生用量；
- 维护 Observation 的来源、身份、时间、覆盖范围和可信等级；
- 处理断连、迟到回执、撤权、取消和接管的执行事实。

中心协作不依赖某一成员 Runtime 在线。成员本机保留宿主 Session、凭据、工作副本、私有历史和未共享内容。Runtime 未上报的 Credits、Token 或费用保持 unknown，不推测补齐。

### 3.7 交付与证据

**职责：让工作结果可取得、可核验、可交接，并允许不同消费者引用同一事实。**

维护：
- Artifact 的来源、不可变版本、Locator / Digest 和可取得性；
- Candidate 固定的一组交付制品和适用 Work Agreement；
- Evidence 对要求、交付、执行或来源事实的可核验观察；
- Evidence Anchor 与 Evidence Applicability；
- Delivery Record 的可重建视图及交付消费关系。

Evidence 可以来自来源文档、Issue 决定、Run 回执、工具观察、文件回读、确定性测试、独立审查或业务验收。来源强度不可混用。成员自述不能伪装成宿主事实；模型评价不能伪装成测试结果。

交付域不决定业务验收，不拥有原始 Run，也不复制原始来源。Issue 上的有权成员决定是否接受当前 Candidate。

### 3.8 Evaluation、度量与持续改进

**职责：判断研发过程和交付效果，发现问题根因，并推动知识与 Harness 的可验证改进。**

维护：
- 原生 Usage 的归集视图、成本覆盖与质量指标；
- Evaluation Policy、Evaluation、Finding；
- Improvement Proposal、改进候选修订和 Benchmark；
- 评价器与实验版本、资源预算、审核证据；
- 改进发布后的采用观察、真实生产效果和回退建议。

Finding 按根因分诊，可进入：
- 当前 Issue 修正；
- Knowledge Revision 的新增、修订或失效；
- Harness Revision 的改进；
- Project Configuration / Workflow 决定；
- Runtime / Tool / Adapter 修复；
- Evaluation / Measurement 自身校准；
- 证据不足时继续观察或调查。

知识与 Harness 的候选、审核和发布分别由各自维护者负责。Evaluation 不替代 Issue 验收；Benchmark 通过不等于发布；Release 不等于 Project Adoption；Adoption 不等于实际使用或生产效果。

## 4. 横向能力：不另立业务主线

### 4.1 统一工作台

工作台是成员理解状态、寻找下一步和发起操作的共同入口，不是独立业务权威域。

它按成员任务组织视图：
- 项目与 Issue：当前目标、责任、阶段、阻塞、候选交付和待决事项；
- 知识：团队 / 项目知识、来源状态、证据、有效性和贡献入口；
- Harness：可用方法、适用范围、版本、项目采用和改进候选；
- 执行：Run、Runtime、宿主回执和真实可观察的用量；
- 质量与改进：评价结论、Finding、待处理改进和效果观察。

页面不按内部八个能力域机械铺设。成员从项目、Issue 或当前问题进入，需要时再展开知识、Harness、执行和评价细节。所有写操作回到拥有该事实决定权的能力域或 Multica 原生入口。

### 4.2 来源连接器与宿主适配器

连接器和适配器是横向集成能力，不拥有业务对象：
- 来源连接器把飞书、Git、文档、PDF、HTML、表格和外部系统接入知识管理，保留来源身份、权限、修订和定位。
- 宿主适配器把不同 Agent 工具协议接入执行集成，保留宿主版本、原生身份、能力覆盖和观察证据。
- 代码分析器可为项目代码知识提供解析和图谱能力，但不替代工程仓作为代码事实权威。

同一连接器可服务多个知识类型；同一宿主适配器可支持不同工作方式。适配层只标准化来源与能力，不替业务域作知识发布、Issue 验收或 Harness 采用决定。

## 5. 关键端到端数据流

### 5.1 知识进入研发

1. 来源连接器发现资料，或成员向收件区提交一次性资料。
2. 知识管理取得来源修订，按资料类型解析结构、位置和内容，记录处理状态。
3. 形成可定位 Evidence；基于证据整理 Knowledge Revision 候选。
4. 知识维护者按证据、范围、时效、许可和冲突核验并发布。
5. Project Adoption 或当前工作按权限选用知识版本。
6. Issue 开工时按项目、目标、阶段、代码基准和接收者权限检索相关知识。
7. 选择、投递、加载、实际使用分别留证；无法观察的阶段保持 unknown。

### 5.2 Harness 进入研发

1. 团队 / 项目维护者定义 Principles、Skills、Playbooks、SOP、Scripts 和 Evaluation。
2. Harness 候选经过相应的静态检查、回归或 Benchmark 后发布不可变 Release。
3. 项目有权成员决定采用的版本和适用范围。
4. Issue 根据工作类型和阶段选择必要方法，固定本项使用版本。
5. Agent 按方法执行；确定性检查、流程门禁和 Evaluation 分别产生可核验证据。
6. 实际效果回到 Evaluation 与改进能力，不因加载过某个 Skill 就视为质量达标。

### 5.3 研发工作端到端贯通

1. Issue 建立目标、范围、责任和完成条件。
2. 从团队知识、项目资料和代码知识中准备适用上下文。
3. 选择适用 Harness；由负责人决定自主推进、一次性协助、持续 Main Bot 委托或 SOP。
4. 受管执行沿 Multica Run / Runtime；成员本地执行按授权共享必要活动和成果。
5. 交付域固定 Artifact、Candidate 和 Evidence。
6. Issue 负责人或验收人按工作约定作出接受、退回或待决定的业务处理。
7. 交付和执行证据供知识提炼与 Evaluation 引用。

### 5.4 双飞轮反馈

同一份 Finding 可以产生不同路径，但不能混为同一候选：
- 知识问题 → 知识候选 → 知识核验与发布 → 后续研发消费；
- Harness 问题 → Harness 候选 → 回归 / Benchmark → 审核发布 → 项目采用；
- 项目流程问题 → 回原 Project Configuration / Issue Decision；
- Runtime / Tool 问题 → 对应适配或集成维护；
- 原因未知 → 补充证据，不强行归因。

后续生产工作分别记录实际使用的知识和 Harness 版本，观察质量、返工、人工介入、时长和可获得的原生计量。成本降低不能抵消质量、安全或交付完整性退化。

## 6. 能力依赖关系

~~~mermaid
flowchart LR
  Org["组织与项目治理"]
  Knowledge["团队知识管理"]
  Work["产研工作协作"]
  Harness["Harness 治理"]
  Flow["流程与 SOP"]
  Exec["执行集成"]
  Evidence["交付与证据"]
  Evolution["Evaluation 与持续改进"]

  Org --> Knowledge
  Org --> Work
  Org --> Harness
  Org --> Exec
  Knowledge --> Work
  Knowledge --> Harness
  Work --> Harness
  Work --> Flow
  Harness --> Flow
  Work --> Exec
  Flow --> Exec
  Exec --> Evidence
  Work --> Evidence
  Evidence --> Evolution
  Exec --> Evolution
  Knowledge --> Evolution
  Harness --> Evolution
  Evolution --> Knowledge
  Evolution --> Harness
  Evolution --> Work
~~~

依赖解释：
- 组织与项目治理提供身份、授权和范围，不拥有其他域的业务内容。
- 知识管理向工作和 Harness 提供有证据的知识，不决定工作目标或强制规则。
- 工作协作组织目标和责任，引用知识与 Harness，不直接控制宿主内部进程。
- Harness 定义方法与质量标准，流程域执行明确委托的 SOP。
- 流程和工作通过原生执行入口请求 Run；执行域只记录事实，不验收业务结果。
- 交付与证据被 Issue、SOP、知识和 Evaluation 多方消费。
- Evaluation 与持续改进读取证据并提出建议；发布和采用仍回到知识、Harness 或项目的权威入口。

## 7. 事实权威与禁止越界

| 事实 | 权威能力 / 来源 | 禁止越界 |
|---|---|---|
| 原始文档、代码、外部业务资料 | 飞书、Git、代码仓及原来源系统 | 知识管理不得静默覆盖原文 |
| 来源连接、取得修订和解析状态 | 知识管理与来源连接器 | 解析成功不得冒充知识发布 |
| Knowledge Item / Revision / Release | 知识管理及知识维护者 | Harness 维护者不得擅自确认业务事实 |
| Harness Asset / Revision / Release | Harness 治理及资产维护者 | 知识维护者不得直接修改团队强制规则 |
| Project Adoption / 项目配置 | 组织与项目治理中的有权成员 | Release 不得自动改变项目配置 |
| Issue / Work Agreement / Decision | 产研工作协作及有权成员 | Run、SOP、Evaluation 不得自行完成 Issue |
| SOP Execution / Node Activation | 流程与 SOP 执行 | SOP 不得改变 Issue 的目标、总责和保留决定 |
| Run / Runtime / Session / Usage | Multica 原生执行链与宿主回执 | 观察器不得重复创建生产 Run 或伪造缺失用量 |
| Artifact / Candidate / Evidence | 交付与证据；原制品仍由生产来源维护 | Delivery Record 不得成为第二权威写入 |
| Evaluation / Finding / Proposal / Benchmark | Evaluation 与持续改进 | 评价分数不得代替业务验收或资产发布 |
| 工作台视图和通知 | 可重建查询投影 | UI 不得成为状态和决定的权威来源 |

跨域操作采用各自权威对象写入、稳定来源身份、幂等消费和对账恢复；不假设全局事务。撤权、来源更新、候选换版和迟到回执只影响受影响范围，保留历史事实。

## 8. 与现有设计的承接和收敛

| 现有设计 | 新架构中的归属 | 处理 |
|---|---|---|
| Multica Issue / Project Workflow | 产研工作协作、组织与项目治理 | 继承原生事实与入口，不复制控制平面 |
| Main Bot / Worker / Squad | 产研工作协作中的授权执行组织方式 | 保留机制，非所有 Issue 必需，不作为顶层产品模块 |
| Team Wiki / Project Knowledge | 团队知识管理 | 从可选资料入口提升为完整知识能力域 |
| Project Code Wiki | 团队知识管理中的代码知识专门能力 | 独立可扩展，不作为当前主线前置 |
| TeamAI Skills / Rules / Principles / Driver | Harness 治理与上下文消费 | 继承能力资产、作用域、版本和投递机制 |
| LoopForge SOP / Run Evaluation | Harness 治理、流程与 SOP、Evaluation | 继承节点依赖、返工、评价和改进机制 |
| D5 / D6 | 工作连续性、交付与证据 | 作为跨域业务契约继续有效 |
| D7 / D11 / VS3–VS4 | Evaluation 与持续改进 | 扩展知识改进路径，保留独立评价、Benchmark、发布与采用边界 |
| 原 A–I 模块 | 不再作为新架构的一级划分 | 按本架构的能力域重新映射；原文档中的 A–I 表不再作为后续扩展依据 |
| 原五层职责 | 不再作为产品模块或严格流程层级 | 仅可用于描述职责视角，不用于决定模块边界 |

## 9. 当前范围与架构验收标准

当前主线建设：
1. 团队知识管理的来源、证据、提炼、发布、检索和失效治理；
2. Issue 驱动的产研工作贯通与低摩擦协作；
3. Harness 资产的定义、选择、执行约束和质量验证；
4. 本地 Agent Runtime 接入、执行事实和交付证据；
5. Evaluation、知识反馈与 Harness 持续改进。

按需扩展，不作为主线前置：
- 完整项目代码图谱产品；
- 通用企业知识管理平台；
- 通用低代码流程引擎；
- 全自动多 Agent 编排平台；
- 自动训练模型或无审核修改团队默认 Harness；
- 多组织复杂治理与跨团队权限产品。

整体架构收敛必须证明：
- 知识可从权威来源形成可核查内容，并在正确权限和适用范围内进入研发；
- Issue 能贯通需求、设计、实施、验证和交付，Agent 协作不破坏业务责任；
- Harness 能指导和约束执行，并以真实证据验证结果；
- 一份 Evidence 可被多个消费者引用而不复制权威事实；
- Finding 能正确分流到知识、Harness、项目、工具或当前工作；
- 发布、项目采用、实际投递、宿主使用和真实效果各自有独立证据；
- 普通研发不必启用全部知识、SOP 和 Evaluation 扩展能力；
- 不新增平行 Issue、Task、Run、Runtime、Candidate、Release 或 Project Adoption 控制系统。

本架构明确业务能力和事实边界。后续先完成专题映射和整体一致性审查，再决定技术承载与工程切片。
