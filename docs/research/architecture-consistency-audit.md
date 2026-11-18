# AgentPlatform · 整体架构一致性审查

## 1. 审查范围与结论

本次以产品定位、统一业务对象模型和整体系统架构为基准，交叉检查核心对象、生命周期与事件、一致性与并发、跨层契约、03B 能力治理、D7、D11、知识管理生命周期及工作台。

**结论：核心业务事实和两个飞轮可以成立，现有 Issue / Run / Artifact / Candidate / Evidence / Evaluation / Finding / Proposal / Benchmark / Release / Project Adoption 机制无需推翻。但八个并列能力域仍有过度拆分，且 03B 与知识管理存在职责重叠。需要将八个并列域收敛为五个核心业务能力域。组织权限、项目配置、工作台、来源连接器和宿主适配器属于实施时的横切设计事项，不构成产品能力域、产品层级或独立子系统。**

本次审查不要求另起产品，不新增平行控制面，不进入技术实现。

## 2. 主要审查发现

### 2.1 八个并列能力域不是八个同级业务模块

当前八域中存在明显的父子能力关系：
- 研发流程与 SOP 执行是产研工作组织的内部能力，不应与 Issue 工作协作并列为一个完整业务主线。
- SOP Definition 是 Harness 方法资产；SOP Execution 是工作中受托流程的运行实例。定义与执行分属不同职责，不能因为名称相同而放进同一模块。
- 执行集成与交付证据属于同一条“执行 → 产物 → 核验 → 交回”链。两者事实模型仍然不同，但无需因此成为两个相互独立的一级产品域。
- Evaluation、度量与持续改进是横跨知识、Harness、工作和执行的反馈能力，不能变成研发工作必须经过的串行阶段。
- 组织与项目治理提供身份、权限、项目范围和采用决定，是全平台基础治理，不是与知识、工作、Harness 同级的研发业务能力。

### 2.2 收敛后的五个核心业务能力域

| 核心能力域 | 纳入的现有职责 | 权威事实与边界 |
|---|---|---|
| **A. 团队知识管理** | 来源连接、资料取得与解析、证据锚点、知识提炼、核验、发布、检索、有效性和反馈 | 维护 Source Connection / Item / Revision、Ingestion Batch、Knowledge Item / Revision、知识治理和使用反馈；不维护 Issue、Run、交付 Evidence 的权威事实 |
| **B. 产研工作与流程协作** | Issue 工作、Project Workflow、责任交接、Main Bot 委托、SOP Execution | Issue 仍是工作唯一归属；维护工作约定、业务决定、流程实例与节点推进；不拥有 Harness 方法定义、Run 终态或交付验收事实 |
| **C. Engineering Harness 治理** | Principles、Rules、Skills、Playbooks、SOP Definition、Scripts、工具约定、Scorer / Rubric / Evaluation Definition | 维护方法资产、不可变修订、核验和发布；SOP Definition 在此，SOP Execution 不在此；不拥有知识正文和项目采用决定 |
| **D. 执行与交付证据** | Multica 原生执行接入、Runtime / Host 观察、Artifact、Candidate、Evidence、交付核验 | 复用 Multica Task / Run / Runtime / Session / Usage；维护平台侧执行关联、Artifact / Candidate / Evidence 及适用性；不决定 Issue 业务验收 |
| **E. Evaluation、度量与持续改进** | Evaluation、Finding、Proposal、Benchmark、预算、效果观察、成本质量分析 | 维护独立评价与改进治理事实；Finding 分流到知识、Harness、工作配置、Runtime / Tool 或当前工作；不直接发布知识 / Harness，也不替代业务验收 |

五个域是业务责任归属，不要求五个独立服务、数据库或团队。一个工程模块可以承载多个域；一个域也可以由多个组件实现。

### 2.3 实施时的横切设计事项（不构成产品能力域）

**平台基础治理：组织与项目治理**

维护 Team、Project、Member、Agent、访问控制、资源授权、Project Configuration、Project Adoption 和 Evaluation Policy 的项目级配置。它为五个业务域提供身份、范围和决定权，不承接研发工作、知识正文或 Harness 正文。

Project Workflow 的配置归项目范围治理，但其业务语义、Issue 阶段推进和责任交接归产研工作与流程协作。Project Adoption 的决定记录归组织与项目治理；被采用资产的正文、版本和发布仍归对应知识 / Harness 维护者。

**横向能力：**
- **来源连接器**：适配飞书、Git、PDF、HTML、表格和其他来源协议；知识管理拥有连接、来源身份、修订、证据和知识处理语义。
- **宿主适配器**：适配 Codex、Claude Code、Qoder、CodeBuddy 等宿主协议；执行与交付证据能力拥有 Run 关联、Observation 来源和覆盖语义。
- **统一工作台**：跨域查询、导航和有权操作入口；不拥有业务事实，不按内部模块机械拆页面。

适配器是技术接入方式，不是新的业务权威域。工作台是用户入口，不是第六个业务域。

## 3. 对象与事实权威审查

| 对象 / 事实 | 唯一权威归属 | 其他能力的使用方式 | 审查结论 |
|---|---|---|---|
| Team / Project / Member / 权限 / Project Adoption | 各业务操作按项目授权规则写入；身份与权限按实际底座落实 | 其他域读取授权与项目范围 | 横切约束，不新增能力域 |
| 原始文档、代码、外部记录正文 | 飞书、Git、项目系统等原来源 | 知识管理保存身份、修订快照、定位与派生许可 | 不复制原文权威 |
| Source Connection / Item / Revision / Ingestion Batch | 团队知识管理 | 连接器负责协议适配 | 保留为知识域对象 |
| Evidence Anchor | 来源解析与知识管理 | 作为 Evidence 的精确位置引用 | 保留，但不把每个 Chunk 建成业务对象 |
| Evidence | 执行与交付证据 | 知识与 Evaluation 引用同一 Evidence；必要时补充 Evidence Applicability | 明确唯一证据事实，不建知识证据仓与交付证据仓两套系统 |
| Knowledge Item / Revision / Release | 团队知识管理及知识维护者 | Harness、Issue 和检索消费引用固定版本 | 保留独立知识生命周期 |
| Harness Asset / Revision / Release | Harness 治理及资产维护者 | 项目采用和工作执行引用固定版本 | 保留独立 Harness 生命周期 |
| Project Adoption / Evaluation Policy | 项目有权成员按配置规则作出的决定；Scorer / Rubric 归 Harness | 知识、Harness、工作和评价按范围读取 | 决定权明确，不新增组织产品 |
| Issue / Work Agreement / Decision | 产研工作与流程协作；Issue 沿用 Multica 权威记录 | Run、SOP、交付、知识提炼和评价引用 | 保留唯一工作主线 |
| SOP Definition | Harness 治理 | Issue 按需调用已发布版本 | 从流程执行域移至 Harness 定义域 |
| SOP Execution / Node Activation / Attempt | 产研工作与流程协作 | 调用原生 Run 并消费结果 | 从 Harness 定义域分离，保留受托流程实例 |
| Run / Runtime / Session / Usage | Multica 原生执行链 | 评价与交付引用，不复制执行账本 | 保留单一执行控制面 |
| Artifact / Candidate / Delivery Record | 执行与交付证据；原始制品仍归生产来源 | Issue 决定消费 / 验收，Evaluation 评价 | 保留 |
| Evaluation / Finding / Proposal / Benchmark | Evaluation、度量与持续改进 | 将候选交给知识 / Harness / 项目权威入口治理 | 保留独立评价和改进生命周期 |
| ContextReceipt / Work Asset Pin | 附着 Issue / Run 的选择、投递记录 | 工作台和评价读取 | 是关联与回执，不提升为独立业务工作对象 |

### 3.1 Evidence 的唯一事实与多方引用

必须区分三件事：
1. **Evidence Anchor**：某个来源修订中的位置，例如飞书 Block、PDF 页码、代码符号、Issue Comment 或 Run 回执位置。
2. **Evidence**：对明确事实的可核验观察，记录来源身份、版本、主体、时间、环境、方法、内容摘要和可信等级。
3. **Knowledge Claim / Evaluation Conclusion / Acceptance Decision**：分别是知识结论、评价结论和业务决定，引用 Evidence，但不等同于 Evidence。

来源解析和知识管理可以产生 Anchor；证据事实由执行与交付证据能力统一维护或引用原来源事实。Knowledge Revision 只保存支持结论的 Evidence 引用和适用范围，不复制一份证据正文。Evaluation 引用同一 Evidence 并形成独立评价。这样既不把所有资料 Chunk 都变成 Evidence 对象，也不让知识、交付和 Evaluation 各建一套证据仓。

## 4. 现有专题冲突与处理

| 文件 / 专题 | 当前问题 | 处理决定 |
|---|---|---|
| system-architecture.md | 八个同级能力域混入基础治理和子能力 | 收敛为五个核心业务域；身份权限、工作台和外部接入作为实施横切事项 |
| core-object-model.md | “方法与能力”对象组仍把 Knowledge 与 Skill / SOP 放在一起 | 将知识对象单独归入来源与知识；方法与能力只保留 Harness 资产 |
| core-business-object-model.md | 对象分类把 Knowledge Feedback 同时列在知识域和横向消费记录；SOP 定义 / 执行分属未充分映射 | Knowledge Feedback 只归知识治理；SOP Definition 归 Harness，Execution 归工作流程 |
| 03b-capability-governance.md | 同时承担能力选择、上下文投递和知识来源 / 知识贡献，和知识生命周期重复 | 保留为 Harness 选版、工作上下文组装与投递的详细专题；知识来源、提炼、许可、撤回与发布统一引用知识管理生命周期 |
| cross-layer-contracts.md | Context Contract 已经把团队 / 项目知识列为输入，但尚未明确知识治理是唯一权威来源 | 保留 Context Contract 为跨域消费契约，增加知识修订、当前读权、适用范围和 Evidence 引用要求；不重复知识处理流程 |
| lifecycle-state-event-model.md | 已有知识状态和事件，但需与五域归属对齐 | 保留各对象独立生命周期，明确知识状态由知识域维护，Run 状态沿 Multica，SOP 实例由工作流程维护 |
| core-consistency-concurrency.md | 已覆盖 Issue、Run、Candidate、Evaluation、Release、Adoption；知识写入边界不够显式 | 增加 Source Revision / Knowledge Revision / Release 的条件写入、来源撤权与投递隔离要求 |
| d7-continuous-improvement-loop.md | Finding 已分流知识 / Harness，但需明确各目标的唯一维护者 | 保留 D7；提案只提出候选，知识 / Harness / 项目各自的权威入口完成发布或采用 |
| d11-evaluation-trigger-budget-policy.md | Team / Project Policy、Scorer / Rubric 的职责已分开 | 继续由项目治理维护 Policy，Harness 维护 Scorer / Rubric，Evaluation 域执行策略并记录评价 |
| 05-unified-workbench.md | 页面容易按内部模块组织 | 继续按成员工作任务组织，知识与 Harness 作为按需上下文和反馈入口 |

## 5. 端到端一致性验证

| 场景 | 正确的事实流 | 不允许的结果 |
|---|---|---|
| 新 PRD 进入团队知识 | Source Connection → Source Revision → Anchor / Evidence → Knowledge Revision → Knowledge Release → Issue 检索与引用 | 上传成功就成为正式知识；知识正文覆盖飞书原文 |
| 新 Issue 开始研发 | Issue / Work Agreement → 权限过滤的知识检索 → Harness 选版 → ContextReceipt → Run | 每次工作强制建立知识任务、SOP 或模型 Evaluation |
| 本地 Agent 完成开发 | Multica Run / 宿主回执 → Artifact → Candidate → Evidence → Issue 有权主体验收 | Run 成功自动完成 Issue；Observation 复制成第二个 Run |
| 一次测试发现知识错误 | Evidence → Finding → 当前 Issue 修正 + Knowledge Revision 候选 → 知识维护者核验发布 | Evaluation 直接改写知识；一次失败自动成为团队规范 |
| 一次复盘发现 Harness 缺陷 | Finding → Harness Proposal → Candidate Revision → Benchmark → Harness Release → Project Adoption → 后续真实效果 | 知识维护者越权发布 Skill；Benchmark Passed 直接代表生产效果 |
| 同一问题同时涉及知识与 Harness | 同一 Finding / Evidence 形成两个独立候选，分别核验、发布、采用和观察 | 把知识发布与 Harness 发布合并成一个状态 |
| 来源权限撤回 | Source Connection / 权限事实变化 → 影响分析 → 暂停相关知识投递 → 复核派生知识和在途上下文 | 仅删除检索索引，却继续向失权 Agent 投递历史摘要 |
| Runtime 断联 | Issue / Project / 已共享知识与交付仍可访问；原 Run 保留 Unknown / Lost，其他获准成员可接手 | 因某成员 Runtime 离线导致整个 Issue 或知识服务不可用 |
| 评价预算耗尽 | D11 停止新增治理 Run；强制门禁等待或使用预先批准的等价检查 | 将未评价视为通过，或把治理成本混入生产成本 |

## 6. 需要统一的横向契约

五个业务域之间只保留六类必要契约：
1. **Identity / Scope / Authorization**：主体是谁、属于哪个 Team / Project、当前读写和派发权限是什么。
2. **Work Contract**：Issue 目标、责任、范围、决定和完成条件。
3. **Knowledge / Context Contract**：知识修订、来源证据、适用范围、当前读权和投递回执。
4. **Harness / Capability Contract**：本项工作采用哪些 Harness Release、强制规则、建议方法和评价标准。
5. **Execution / Delivery Contract**：执行授权、Run 来源、Artifact / Candidate、Evidence 与消费 / 验收。
6. **Evaluation / Improvement Contract**：评价输入、Finding、改进目标、候选验证、发布 / 采用和效果回收。

这些是跨域交接契约，不是六个额外模块，也不要求每个 Issue 都经过全部契约。按工作需要触发。

## 7. 复杂度控制结论

- 五个核心业务域是职责边界，不是五套独立系统。
- 组织与项目治理是基础能力；不必为它单独建设一套新的组织产品。
- 工作流执行并入产研工作协作；Harness 只维护 SOP 定义与发布。
- 执行与交付证据合并为一条业务能力链，但保留 Run、Artifact、Candidate、Evidence 的不同权威事实。
- 评价与持续改进是跨域反馈能力；不得成为生产工作必经的串行阶段。
- 连接器、宿主适配器和工作台保持横向能力。
- Knowledge、Harness、Issue、Run 和 Evidence 各自保留独立事实和必要生命周期；不为视觉上的模块整齐强行合并对象。

## 8. 本轮已完成的收敛修改

本次审查提出的结构性修正已写入对应正式文档：

1. [整体系统架构](../architecture/system-architecture.md)：从八个并列能力域收敛为五个核心业务域，并明确实施横切事项不构成额外产品能力域。
2. [03B Harness 选用与工作上下文投递](../architecture/03b-capability-governance.md)：知识来源、证据、提炼、许可、撤回和发布不再由 03B 维护；03B 只定义知识与 Harness 如何进入本次工作。
3. [核心对象模型](../architecture/core-object-model.md)：将 Knowledge 从 Harness 方法资产组分离；Project Adoption 归平台基础治理。
4. [核心业务对象与统一关系模型](../architecture/core-business-object-model.md)：Knowledge Feedback 只归知识治理，工作资产使用记录作为引用 / 回执，不重复维护知识反馈。
5. [一致性与并发控制模型](../architecture/core-consistency-concurrency.md)：增加 Source Revision、Knowledge Revision、Knowledge Release 的权威写入、条件更新、撤权和投递隔离要求。
6. [跨层业务契约](../architecture/cross-layer-contracts.md)：Context Contract 明确只消费经知识治理的修订，不重复定义知识生命周期。
7. [D7 持续改进](../architecture/d7-continuous-improvement-loop.md)：明确 Knowledge Release 与 Harness Release 的不同维护者和发布责任。
8. README、产品基线与架构总览同步为五域架构。

## 9. 最终审查结论与后续顺序

当前五域架构与核心对象、生命周期、权限、证据、跨层消费和持续改进机制已形成一致的业务结构。Markdown 内部链接检查已通过。

仍需在下一阶段用更具体的工作场景验证边界，但不再需要为本轮发现的结构性问题新增并列能力域或重复对象。

下一步建议：
1. 冻结整体产品与业务架构基线，明确哪些文档是权威定义、哪些是专题契约、哪些是研究证据。
2. 选择一条通用研发工作链和一条知识更新 / Harness 改进链，完成架构级验收。
3. 在验收通过后，才进行渐进落地切片和技术承载设计。

本审查不批准数据库 Schema、API、服务拆分、存储选型或部署方案。
