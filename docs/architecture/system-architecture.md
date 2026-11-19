# AgentPlatform · 整体系统架构与能力边界

## 1. 架构目标与组织原则

AgentPlatform 面向研发团队建设一套持续积累和改进 AI 研发能力的平台。团队知识进入研发，产研工作沿 Issue 连续推进，Engineering Harness 提供可执行的方法与质量标准，真实执行和交付证据支撑评价，并将有效经验反馈给知识与 Harness。

产品围绕两个相互促进的飞轮：
- **团队知识飞轮**：已有知识 → 研发消费 → 新事实与经验 → 提炼治理 → 可复用知识。
- **Harness 进化飞轮**：Harness 指导研发 → 观察与评价 → Finding → 改进候选 → 对照验证 → 发布与采用 → 真实效果回收。

整体架构遵循以下原则：
1. **团队研发能力优先于 Agent 管理。** Agent 是执行载体，协作复杂度由真实研发需要驱动。
2. **Issue 是研发工作的唯一业务归属。** 目标、责任、讨论、决定、交付消费和完成状态沿 Issue 维护。
3. **知识与 Harness 是两个独立治理的基础能力。** 知识描述事实和经验；Harness 规定工作方法、约束和验证方式。
4. **复用 Multica，不复制控制平面。** Issue、Task / Run、Runtime、Daemon、Backend、Session、Usage 沿用 Multica 原生能力。
5. **定义与执行分离。** SOP Definition 是 Harness 方法资产；SOP Execution 是 Issue 下明确受托的流程实例。
6. **执行与交付共享一条结果链。** Run、Artifact、Candidate、Evidence 保持各自事实语义，但由同一能力域负责执行结果的形成、核验与交接。
7. **Evaluation 是反馈能力，不是生产流水线必经阶段。** 评价、改进和知识提炼按风险、证据与价值按需触发。
8. **证据共享、结论独立。** 同一 Evidence 可被交付、知识和 Evaluation 引用，不复制权威事实；业务验收、知识发布和 Harness 发布分别治理。
9. **能力域是业务责任边界，不是部署拆分。** 不要求一域一服务、一对象一表或五个独立团队。

## 2. 总体架构

~~~mermaid
flowchart TB
  People["团队成员 / 项目维护者 / Agent"]
  UI["统一工作台 · 查询、导航与操作入口"]
  Org["身份 / 权限 / 项目配置规则（横切约束）"]
  subgraph Core["五个核心业务能力域"]
    Knowledge["A · 团队知识管理"]
    Work["B · 产研工作与流程协作"]
    Harness["C · Engineering Harness 治理"]
    Delivery["D · 执行与交付证据"]
    Evolution["E · Evaluation / 度量 / 持续改进"]
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
  UI --> Delivery
  UI --> Evolution
  Org -.-> Knowledge
  Org -.-> Work
  Org -.-> Harness
  Org -.-> Delivery
  Org -.-> Evolution
  Sources --> Knowledge
  Knowledge --> Work
  Knowledge --> Harness
  Work --> Harness
  Work --> Delivery
  Harness --> Work
  Harness --> Delivery
  Work --> Delivery
  Multica <--> Delivery
  Hosts <--> Delivery
  Delivery --> Work
  Delivery --> Evolution
  Knowledge --> Evolution
  Harness --> Evolution
  Evolution --> Knowledge
  Evolution --> Harness
  Evolution --> Work
~~~

图中箭头表示业务依赖、事实引用或反馈，不表示同步事务，也不意味着每项研发都经过全部能力。

## 3. 五个核心业务能力域

### 3.1 A · 团队知识管理

**职责：把团队已有资料和研发中新产生的经验，转化为可追溯、可检索、在适用范围内可复用的知识。**

维护：
- Source Connection、Source Item、Source Revision、Ingestion Batch；
- 来源取得、结构解析、OCR、章节 / 块 / 页码 / 表格 / 代码位置锚点和处理回执；
- Knowledge Item、Knowledge Revision、知识核验、派生许可、发布申请和知识反馈；
- 知识有效性、冲突、替代、撤回、复核与面向 Team / Project / Issue 的检索消费；
- Knowledge Revision 对 Evidence 的引用、适用范围和来源可追溯关系。

边界：
- 飞书、Git、代码仓和其他来源系统仍然维护原始正文；知识管理不覆盖外部权威原文。
- Evidence 的可核验事实由执行与交付证据能力统一维护或引用来源原生事实；知识管理维护 Evidence Anchor 和 Knowledge Revision 对 Evidence 的引用，不复制第二份证据正文。
- 不维护 Issue 当前目标、Run 终态、Artifact / Candidate 的交付权威事实或 Harness 强制规则正文。
- 不建立知识处理专用的第二套 Issue / Task / Run / Runtime 控制面。

团队知识、项目知识和项目代码知识按适用范围、权限与代码基准区分。项目代码知识可独立扩展，但不作为当前主线成立的前置条件。

### 3.2 B · 产研工作与流程协作

**职责：承载研发目标、责任、业务决定、工作流交接和明确受托流程，是产研工作主线。**

维护或沿用：
- Project / Issue、Work Agreement、Assignee、Accountable Member、Decision；
- Issue 讨论、父子分工、一次性 Agent 协助和持续 Main Bot 委托；
- Project Workflow 的阶段语义、Issue 步骤推进和负责人交接；
- SOP Execution、Node Activation、Node Attempt、节点依赖、等待、人工门禁、返工和流程出口；
- 当前工作对知识、Harness、Run、Artifact、Candidate 和 Evidence 的引用与消费。

边界：
- Issue 是业务工作唯一归属。短时协助留在原 Issue；只有独立负责人、独立交付或独立生命周期才拆 Sub-Issue。
- 一次 @Agent 只请求本次协助；持续协调由有权成员在原 Issue 上明确授权现有 Agent 担任 Main Bot。成员保留业务总责。
- Project Workflow 管 Issue 阶段和责任交接；SOP Execution 管明确委托范围内的节点与结果。二者不能互相替代。
- SOP Execution 不拥有 SOP 方法定义、Issue 总责或业务验收权；实际节点执行沿 Multica 原生 Run。
- 不将 Main Bot、Squad 或 Task 平铺提升为产品顶层组织模型。

### 3.3 C · Engineering Harness 治理

**职责：把团队认可的研发方法转化为可选用、可执行、可验证、可演进的工程资产。**

维护：
- Principles / Rules：必须满足的工程要求及适用范围；
- Skills：Agent 可调用的专业能力；
- Playbooks：指导某类工作的分析和推进方法；
- SOP Definition：稳定流程的输入、依赖、节点、输出、门禁、返工和交还定义；
- Scripts / Tools / Harness Configuration：确定性检查和执行工具约定；
- Scorer / Rubric / Evaluation Definition：评价标准、评分器定义和回归要求；
- Harness Asset / Revision、核验、发布审核与 Harness Release。

边界：
- Harness 可以引用 Knowledge 作为事实和经验依据，但不复制维护知识正文。
- 知识经验只有在补齐适用范围、执行方式、例外和验证标准后，才适合转化为 Harness。
- SOP Definition 在 Harness 治理；SOP Execution 在产研工作与流程协作。
- Evaluation Policy 的 Team / Project 配置归平台基础治理；Scorer / Rubric 归 Harness 维护；Evaluation 执行与结论归 Evaluation 能力。
- Harness Release 不自动改变 Project Adoption，也不证明某项工作已加载或使用。

### 3.4 D · 执行与交付证据

**职责：连接成员获准的本地 Agent，记录真实执行，形成可取得、可核验、可交接的交付结果。**

沿用 Multica 的 Project / Issue / Task / Run / Runtime / Daemon / Backend / Session / Usage；AgentPlatform 只补足必要的业务来源关联、宿主适配和证据契约。

维护或关联：
- Issue / SOP / Evaluation / Benchmark 与 Multica 原生 Task / Run 的业务来源身份；
- Host、Runtime、Daemon、Backend / Adapter、Session 的能力覆盖与执行观察；
- 宿主可提供的消息、工具调用、文件、终态、原生用量及其来源、时间、可信度和覆盖范围；
- Artifact 的来源、不可变版本、Locator / Digest 和可取得性；
- Candidate 固定的 Artifact 组合与适用 Work Agreement；
- Evidence、Evidence Anchor 引用、Evidence Applicability 和 Delivery Record 可重建视图；
- 结果交回 Issue / SOP 的消费依据。

边界：
- Multica 是 Run / Runtime / Usage 的权威执行账本；观察器不得重复创建 Run 或重复计量。
- 成员本地保留宿主 Session、凭据、工作副本、私有历史和未共享内容；中心协作不依赖某一成员 Runtime 在线。
- 中心派发成功不代表本地已启动；上下文选择、准备、投递、宿主加载和实际使用是不同证据阶段。
- 交付与证据能力不决定业务验收；Issue 上有权主体依据当前 Work Agreement 和 Candidate 作决定。
- 宿主未上报的 Credits、Token、费用和工具活动保持 Unknown，不推测补齐。

### 3.5 E · Evaluation、度量与持续改进

**职责：评价研发过程和交付效果，发现问题根因，并推动知识与 Harness 的可验证改进。**

维护：
- 原生 Usage 的归集视图、成本覆盖、质量和效率指标；
- Evaluation、Finding、Improvement Proposal、Benchmark、Budget Reservation；
- 评价器执行记录、实验版本、候选比较、审核证据、发布后观察与回退建议；
- Finding 分诊及知识、Harness、项目、Runtime / Tool、Measurement 等改进路径。

Finding 按根因分流：
- 当前 Issue 修正：由当前负责人处理，不必建立跨工作提案；
- 知识缺失、错误、过期或经验未沉淀：形成 Knowledge Revision 候选，由知识维护者核验和发布；
- Harness 方法、规则、流程或验证器缺陷：形成 Harness Revision 候选，经回归 / Benchmark 和审核后发布；
- 项目工作流、授权或验收口径问题：回到有权成员的 Project Configuration / Issue Decision；
- Runtime、Tool、Adapter 或观察覆盖问题：交对应集成维护者处理；
- Evaluation / Measurement 问题：校准评价器、样本或计量口径；
- 证据不足或根因未知：继续调查，不强行归因。

边界：
- Evaluation 不替代 Issue 验收；Benchmark 通过不等于发布；Release 不等于 Project Adoption；Adoption 不等于实际使用或生产效果。
- 知识与 Harness 候选分别治理、发布和观察。相同 Finding 可以被两个候选引用，但不能合并发布权责。
- Evaluation、Benchmark、知识整理和改进自身的执行消耗单独归集，不污染生产成本。
- 评价不是每项生产工作的必经阶段；按风险、门禁和实际改进价值触发。

## 4. 实施时需要处理的横切设计事项

本节列出五个业务能力落地时必然遇到的实现问题，**不代表新增能力域、产品层级或独立子系统**。它们应按实际业务流程分散落实到相应能力与交互中。

### 4.1 身份、权限、项目配置与采用决定

身份、权限和项目配置是所有业务能力必须遵守的横切规则，不单独构成产品业务域。实施时需要明确：
- 成员、Agent、Runtime 和外部来源访问身份如何识别；
- Team / Project / Issue 的范围如何继承、收窄和校验；
- 谁能创建、修改、审核、发布知识与 Harness；
- 谁能修改 Issue 目标、责任、委托和验收决定；
- 项目如何分别采用知识与 Harness 版本，以及新工作和在途工作的生效策略；
- 来源读取、处理、派生、发布、投递等不同权限如何落实。

Project Adoption 是项目对已发布资产作出的业务决定，其写入权随项目管理规则落实；这不意味着要建设一个独立的“组织与项目治理产品”。

### 4.2 工作台与交互入口

工作台是五个业务能力的统一交互方式，不拥有业务事实。页面和操作应围绕成员当前任务组织，读写分别调用相应权威能力或 Multica 原生入口。不得因为有五个能力域就机械建设五套后台页面，也不得把工作台本身当成业务主线。

### 4.3 来源接入实现

飞书、Git、PDF、HTML、Office、表格和其他来源需要不同的连接、授权、增量同步、内容取得和解析实现。连接器是这些实现的适配方式；来源身份、修订、证据定位、知识处理和知识治理语义仍归团队知识管理。不能因采用某种连接器就改变原始来源的权威归属。

### 4.4 本地宿主接入实现

Codex、Claude Code、Qoder、CodeBuddy 等宿主需要不同的协议、事件、工具、Session、取消和用量适配。适配器是执行接入实现，不拥有 Run、Issue 或交付的业务决定权。Run / Runtime / Usage 沿用 Multica 原生执行事实；观察覆盖不足和宿主未提供的用量保持 Unknown。

这些实现事项在后续落地设计中按优先级逐项处理，不应提前膨胀为新的产品能力域或服务拆分依据。

## 5. 关键端到端数据流

### 5.1 知识进入研发

1. 来源连接器发现资料，或成员提交一次性资料。
2. 知识管理取得来源修订，按资料类型解析结构、位置和内容，记录处理状态。
3. 形成可定位 Evidence Anchor / Evidence 引用，基于证据整理 Knowledge Revision 候选。
4. 知识维护者核对证据、范围、时效、许可和冲突后发布。
5. 项目采用或当前工作按权限选用知识版本。
6. Issue 开工时按项目、目标、阶段、代码基准和接收者权限检索相关知识。
7. 选择、投递、加载、实际使用分别留证；无法观察的阶段保持 Unknown。

### 5.2 Harness 进入研发

1. 团队 / 项目维护者定义 Principles、Skills、Playbooks、SOP、Scripts 和 Evaluation 标准。
2. Harness 候选经过适当的静态检查、回归或 Benchmark 后发布不可变 Release。
3. 项目有权成员决定采用的版本和适用范围。
4. Issue 根据工作类型和阶段选择必要方法，固定本项使用版本。
5. Agent 按方法执行；确定性检查、流程门禁和 Evaluation 分别产生可核验证据。
6. 实际效果回到 Evaluation 与改进能力，不因加载过某个 Skill 就视为质量达标。

### 5.3 研发工作端到端贯通

1. Issue 建立目标、范围、责任和完成条件。
2. 从团队知识、项目资料和代码知识中准备适用上下文。
3. 选择适用 Harness；负责人决定自主推进、一次性协助、持续 Main Bot 委托或调用 SOP。
4. 受管执行沿 Multica Run / Runtime；成员本地执行按授权共享必要活动和成果。
5. 执行与交付证据能力固定 Artifact、Candidate 和 Evidence。
6. Issue 负责人或验收人按工作约定作出接受、退回或待决定的业务处理。
7. 交付和执行证据供知识提炼与 Evaluation 引用。

### 5.4 双飞轮反馈

同一份 Finding 可以产生不同路径，但不能混为同一候选：
- 知识问题 → Knowledge Revision 候选 → 知识核验与发布 → 后续研发消费；
- Harness 问题 → Harness Revision 候选 → 回归 / Benchmark → 审核发布 → 项目采用；
- 项目流程问题 → 回到 Project Configuration / Issue Decision；
- Runtime / Tool 问题 → 对应适配或集成维护；
- 原因未知 → 补充证据，不强行归因。

后续生产工作分别记录实际使用的知识和 Harness 版本，观察质量、返工、人工介入、时长和可获得的原生计量。成本降低不能抵消质量、安全或交付完整性退化。

## 6. 能力依赖关系

~~~mermaid
flowchart LR
  Foundation["组织 / 项目 / 权限基础治理"]
  Knowledge["A · 团队知识"]
  Work["B · 产研工作与流程"]
  Harness["C · Harness 治理"]
  Delivery["D · 执行与交付证据"]
  Evolution["E · Evaluation 与改进"]
  Foundation --> Knowledge
  Foundation --> Work
  Foundation --> Harness
  Foundation --> Delivery
  Foundation --> Evolution
  Knowledge --> Work
  Knowledge --> Harness
  Work --> Harness
  Harness --> Work
  Work --> Delivery
  Harness --> Delivery
  Delivery --> Work
  Delivery --> Evolution
  Knowledge --> Evolution
  Harness --> Evolution
  Evolution --> Knowledge
  Evolution --> Harness
  Evolution --> Work
~~~

依赖表示职责协作而非严格流水线。知识与 Harness 为工作提供输入；工作授权执行；执行与交付提供共享证据；Evaluation 读取证据并提出改进；正式发布与采用仍回到知识、Harness 或项目的权威入口。

## 7. 事实权威与禁止越界

| 事实 | 权威能力 / 来源 | 禁止越界 |
|---|---|---|
| 原始文档、代码和外部业务资料 | 飞书、Git、代码仓及原来源系统 | 知识管理不得静默覆盖原文 |
| 来源连接、取得修订和知识正文 | 团队知识管理及来源连接器 | 解析成功不得冒充知识发布 |
| Knowledge Item / Revision / Release | 团队知识管理及知识维护者 | Harness 维护者不得擅自确认业务事实 |
| Harness Asset / Revision / Release | Harness 治理及资产维护者 | 知识维护者不得直接修改团队强制规则 |
| Project Adoption / 项目配置 / Policy | 项目有权成员按项目权限规则作出的配置与采用决定 | Release 不得自动改变项目配置 |
| Issue / Work Agreement / Decision | 产研工作与流程协作，Issue 沿用 Multica 权威记录 | Run、SOP、Evaluation 不得自行完成 Issue |
| SOP Definition | Harness 治理 | 工作流程不得私自改写已发布定义 |
| SOP Execution / Node Activation | 产研工作与流程协作 | SOP 不得改变 Issue 目标、总责和保留决定 |
| Run / Runtime / Session / Usage | Multica 原生执行链与宿主回执 | 观察器不得重复创建生产 Run 或伪造缺失用量 |
| Artifact / Candidate / Evidence | 执行与交付证据；原制品仍由生产来源维护 | Delivery Record 不得成为第二权威写入 |
| Evaluation / Finding / Proposal / Benchmark | Evaluation、度量与持续改进 | 评价分数不得代替业务验收或资产发布 |
| 工作台视图和通知 | 可重建查询投影 | UI 不得成为状态和决定的权威来源 |

跨域操作采用各自权威对象写入、稳定来源身份、幂等消费和对账恢复；不假设全局事务。撤权、来源更新、候选换版和迟到回执只影响受影响范围，保留历史事实。

## 7.1 五域协作中的关键责任交接

五个能力域围绕 Issue 按需协作，不构成固定流水线。跨域时统一遵守以下责任边界：

| 交接 | 权威提供方 | 接收方责任 | 不得推导 |
|---|---|---|---|
| Knowledge → Work | A 提供正式知识候选、准确 Revision / Release、适用条件和 Evidence 可访问性 | B / 当前 Agent 判断是否适用于本项工作，决定是否采用 | Recall 命中不等于采用、强制规则或实际使用 |
| Harness → Work / Execution | C 提供已发布方法、规则、SOP Definition 和评价标准定义 | 项目配置 / B 决定采用范围，B 组织本项执行 | Release 不等于 Project Adoption；SOP Definition 不等于 SOP Execution |
| Work → Execution | B 提供 Issue、Work Agreement、授权代际、目标、允许动作和交付要求 | D / Multica 按当前授权执行并返回原生事实 | Issue 委托不转移业务总责；派发不等于启动 |
| Execution → Work / Evaluation | D 提供 Run、Artifact、Candidate、Evidence 和观察覆盖 | B 独立消费交付并作业务决定；E 按固定标准评价 | Run 终态不等于交付接受；Observation 不补造缺失事实 |
| Evaluation → Improvement | E 提供评价结果、Finding、根因状态和验证证据 | B 处理当前工作；A / C 分别治理知识或 Harness 候选 | Evaluation 不替代 Issue 验收，也不自动发布资产 |

特别明确：
- **SOP 定义与执行分离**：SOP Definition 归 C；SOP Execution / Node Activation / Node Attempt 归 B；实际 Task / Run 沿 Multica / D。
- **Evaluation 定义与执行分离**：Scorer / Rubric / Evaluation Definition 归 C；Evaluation 实例、Finding、Benchmark 和改进提案归 E；门禁是否必需、采用哪个版本由项目配置与 B 的工作约定确定。
- **Evidence 共享但权威不复制**：D 提供或引用执行 / 交付事实；A 将 Evidence 关联到 Knowledge Revision；E 将 Evidence 关联到 Evaluation / Finding；B 在 Decision 中引用。各域形成自己的结论，不复制同一事实。
- **Release、Project Adoption、Work / Run Asset Pin、ContextReceipt / Observation 分别记录发布、项目采用、本项选择和实际投递 / 消费**，不能合并为一个启用状态。
- **状态只跨域影响，不跨域覆盖**：Release 暂停不自动修改 Issue 状态；Run 失败不自动判定业务失败；Evaluation 不自动退回 Candidate；Candidate 接受与否由 B 按 Work Agreement 决定。

更完整的交接矩阵、端到端研发场景和待验证问题见[五域端到端协作一致性审查](../research/five-domain-end-to-end-consistency-review.md)。

## 8. 与现有设计的承接和收敛

| 现有设计 | 新架构中的归属 | 处理 |
|---|---|---|
| Multica Issue / Project Workflow | 产研工作协作及项目范围规则 | 继承原生事实与入口，不复制控制平面 |
| Main Bot / Worker / Squad | 产研工作协作中的授权执行组织方式 | 保留机制，非所有 Issue 必需，不作为顶层产品模块 |
| Team Wiki / Project Knowledge | 团队知识管理 | 从可选资料入口提升为完整知识能力域 |
| Project Code Wiki | 团队知识管理中的代码知识专门能力 | 独立可扩展，不作为当前主线前置 |
| TeamAI Skills / Rules / Principles / Driver | Harness 治理与上下文消费 | 继承能力资产、作用域、版本和投递机制 |
| LoopForge SOP / Run Evaluation | Harness 定义、工作流程执行、Evaluation | SOP 定义归 Harness；执行实例归工作流程；评价进入 E 域 |
| D5 / D6 | 工作连续性、执行与交付证据 | 作为跨域业务契约继续有效 |
| D7 / D11 / VS3–VS4 | Evaluation、度量与持续改进 | 扩展知识改进路径，保留独立评价、Benchmark、发布与采用边界 |
| 原八个并列能力域 | 五个核心业务域；身份权限、交互入口和外部接入在实施中横切落实 | 合并子能力边界，不按旧域继续扩展 |
| 原五层职责 | 不再作为产品模块或严格流程层级 | 仅可用于描述职责视角，不用于决定模块边界 |

## 9. 当前范围与架构验收标准

当前主线建设：
1. 团队知识管理的来源、证据、提炼、发布、检索和失效治理；
2. Issue 驱动的产研工作贯通与低摩擦协作；
3. Harness 资产的定义、选择、执行约束和质量验证；
4. 本地 Agent Runtime 接入、执行事实和交付证据；
5. Evaluation、知识反馈与 Harness 持续改进。

按需扩展，不作为主线前置：完整项目代码图谱产品、通用企业知识管理平台、通用低代码流程引擎、全自动多 Agent 编排平台、自动训练模型或无审核修改团队默认 Harness、多组织复杂治理与跨团队权限产品。

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

## 10. 架构审查与后续基线

本架构的跨专题审查结论见[整体架构一致性审查](../research/architecture-consistency-audit.md)。五个核心能力域之间的责任交接、对象边界和端到端协作回归见[五域端到端协作一致性审查](../research/five-domain-end-to-end-consistency-review.md)。审查提出的五域收敛、03B 边界、对象分类和跨层契约修正，以相关审查及本文件的更新版本为准。当前冻结的产品与业务架构、权威文档层级、首期范围和渐进落地路线见[架构基线冻结与渐进落地规划](implementation-roadmap.md)。