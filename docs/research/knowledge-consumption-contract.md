# AgentPlatform · Knowledge Consumption Contract 产品定义

> 状态：产品语义收敛  
> 分支：design/system-architecture-convergence  
> 上游依据：[Knowledge Recall 的能力归属与调用承载审查](knowledge-recall-ownership-and-invocation.md)、[Recall 双项目隔离实验](context-recall-two-project-experiment.md)、[知识管理生命周期](../architecture/knowledge-management-lifecycle.md)、[跨层业务契约](../architecture/cross-layer-contracts.md)  
> 范围：定义正式 Team / Project Knowledge 如何被发现、读取、判断、引用、投递和反馈。  
> 非目标：不定义 API / MCP 工具 Schema、数据库 Schema、索引结构、搜索算法、部署拓扑或生产代码。

## 1. 产品目标与核心决定

Knowledge Consumption Contract 规定：**AgentPlatform 中的成员或 Agent，如何在当前授权和工作范围内发现正式知识，理解它适用于什么，读取准确版本，决定是否用于当前工作，并在真实消费链路中保留可核验依据。**

它不是另一个产品能力域，也不是 Recall 服务设计。它是 A · 团队知识管理向 B · 产研工作与流程协作提供知识消费能力时必须遵守的产品契约，并由 D · 执行与交付证据承接实际投递和消费观察。

### 1.1 职责归属

| 环节 | 权威责任 | 业务含义 |
|---|---|---|
| 知识可查询与可读取 | A · 团队知识管理 | 维护知识候选资格、范围过滤、修订读取、Evidence 引用和反馈 |
| 触发、适用判断与采用 | B · 产研工作与流程协作 | 以 Issue / Work Agreement 确定查询意图和工作范围，判断是否将知识用于本项工作 |
| 宿主投递与消费观察 | D · 执行与交付证据 | 通过现有授权通道将获准内容提供给 Agent，记录实际可观察阶段 |
| Harness 是否强制 / 已采用 | C · Engineering Harness 治理及 Project Adoption | 独立解析发布、采用、适用范围和执行资格 |

A 拥有知识权威，不意味着 A 决定每项工作必须查什么；B 决定本项采用，不意味着 B 可以改写知识；D 负责送达，不意味着 D 能扩大读取权限或证明 Agent 已理解。

### 1.2 两种调用入口，共用一套契约

1. **工作准备时发现**：B 根据 Issue 和 Work Agreement 判断有知识缺口，发起 Knowledge Recall，并将候选交给负责人 / Agent 判断。
2. **Agent 执行中发现**：Agent 在任务过程中遇到未知问题，使用当前受信任身份和工作上下文主动调用 Knowledge Recall。

两者调用同一 A 域能力，使用相同授权、候选格式、读取、反馈和状态规则。不是两个 Recall 产品，也不要求每个 Issue 必须 Recall。

## 2. 消费链路：从候选到实际使用

~~~mermaid
flowchart TD
  A[Issue / Agent 发现知识缺口] --> B[Knowledge Recall]
  B --> C{授权与范围过滤}
  C -->|不允许| D[不返回该知识及其元数据]
  C -->|允许| E[返回可核查候选摘要]
  E --> F{是否适用 / 值得展开}
  F -->|否| G[忽略或提交反馈]
  F -->|是| H[按 Item + Revision 读取正文]
  H --> I{是否需要查看 Evidence}
  I -->|需要| J[独立核验 Evidence 访问权并展开]
  I -->|不需要| K[依据已足够]
  J --> L[成员 / Agent 决定是否用于当前工作]
  K --> L
  L -->|不采用| M[保留未采用事实，可反馈]
  L -->|采用| N[引用准确版本到当前 Work / Run]
  N --> O[按接收者复核并投递到宿主]
  O --> P[记录 Loaded / Used 可观察证据]
  P --> Q[关联结果反馈]
~~~

关键区别：
- Recall 命中不是选择；
- 读取正文不是采用；
- 采用不是投递；
- 投递不是加载；
- 加载不是实际使用；
- 实际使用也不等于最终结果正确。

## 3. Recall 请求：查询意图与授权上下文

### 3.1 请求表达什么

Recall 请求应表达“当前工作需要找什么知识”，而不是让 Agent 自行指定可访问哪些知识。

查询意图可以来自：
- Issue 标题、目标和 Work Agreement；
- 当前子任务、角色和工作阶段；
- Agent 在执行中提出的自然语言问题；
- 成员在工作台明确输入的查询；
- 相关领域、系统、模块、工作类型等辅助线索。

查询文本可以是自然语言。允许提供有助于缩小范围的主题和适用条件，但不允许调用者通过任意传入 Team / Project ID 扩大自己可见的范围。

### 3.2 授权上下文由谁提供

授权上下文必须来自现有可信身份 / 工作 / Runtime 链，而不是由 Agent 自述。至少能确定：
- 实际成员 / Agent / Runtime 主体；
- 当前 Team 成员资格；
- 当前 Project 成员关系和项目授权；
- 当前 Issue（存在时）及其 Work Agreement / Delegation；
- 当前工作角色和受托范围（用于适用性与最小必要原则，不代替来源授权）；
- 本次请求目的和允许共享范围。

Agent 可提交查询意图和任务线索；A 域根据可信身份和授权上下文计算有效可见范围。调用者传入的 Project、角色或代码基准只能作为待核验的工作上下文线索，不能作为授权凭据。

### 3.3 范围规则

- Team Knowledge：仅在调用者当前有权访问的 Team 范围内检索。
- Project Knowledge：仅在调用者有权访问且当前工作关联的 Project 范围内检索。
- 同时检索 Team 与 Project 时，返回结果保留分组和原始作用域，不把 Project Knowledge 当成 Team Knowledge。
- 不因 Issue 评论、父子关系、语义相似或曾经参与过项目，就推断调用者当前仍有权访问。
- 不允许通过查询参数请求其他项目私有知识；需要跨项目复用的知识必须已正式派生为 Team Knowledge。

## 4. 候选资格：先判断能不能返回，再判断相关不相关

**权限、作用域和正式可消费状态是返回资格，不是排序权重。** 不得把未授权或不可投递的知识先混入候选，再依赖低分或隐藏正文处理。

### 4.1 候选资格检查

在任何标题、摘要、Claim、Evidence ID、关系或错误信息向调用者暴露前，依次判断：

1. **调用主体有效**：身份和授权上下文可验证；不明确时拒绝或要求通过可信工作入口重试。
2. **知识作用域可见**：Team / Project 成员资格和范围满足要求。
3. **存在正式可消费版本**：Knowledge Revision 已核验并由有效 Knowledge Release 发布；候选、草稿、驳回版本不进入正式 Recall 默认结果。
4. **发布未暂停 / 撤回 / 退役**：暂停投递、撤回或退役的 Release 不作为可用候选返回。
5. **派生许可仍有效**：如果知识依赖受许可约束的派生来源，必须满足当前对目标受众的许可要求。
6. **当前接收者可读**：知识正文对该接收者可见。Evidence 原文权限仍独立判断。
7. **满足硬性适用边界**：明确的不适用项目、版本、环境或工作类型不能因语义相似被当作适用知识。

任何检查不通过，不向调用者泄漏该知识的存在或内部元数据；如需解释，只返回不含私有对象线索的通用权限 / 范围提示。

### 4.2 检索与排序

只有通过候选资格检查的知识才能参与相关性排序。排序应帮助发现，不负责决定知识真伪或项目规则优先级。

适用的判断维度包括：
- 与查询意图的语义和主题相关性；
- 与当前项目、工作类型、系统和版本的适用程度；
- 知识类型与当前问题的匹配程度；
- 核验状态、Evidence 完整性和来源可追溯性；
- 最近核验时间、来源变化和已知冲突；
- 是否有明确替代版本或限制条件。

**不使用单一 Confidence 分数表达知识质量。** 各维度以明确状态、证据和限制表达。相关性分数只用于候选排序，不得覆盖适用性、来源权威、有效性或权限门槛。

### 4.3 结果分组

当同时查询 Team 与 Project Knowledge 时，产品结果必须保留作用域：
- Team Knowledge 分组；
- 当前 Project Knowledge 分组。

不能因为 Team 结果更通用就默认排在 Project 事实之前，也不能因为 Project 结果更贴近项目就自动覆盖团队通用经验。适用条件和事实类型由使用者判断；冲突按已有事实权威规则处理。

### 4.4 Recall 覆盖状态不是知识状态

Recall 必须同时说明本次查询是否完整，而不能只返回命中列表：
- Complete + Hits：声明的可见范围已完整检索并返回候选；
- Complete + No Match：声明范围检索完整，没有匹配的正式知识；
- Partial / Stale：部分作用域或检索投影未追平，未命中不代表知识不存在；
- Unavailable / Failed：当前不能可靠完成查询，应明确失败或降级；
- Partial Success：多个 Team / Project 范围分别报告覆盖状态。

无命中只表示正式 Knowledge Recall 未找到，不代表 Project Sources、Code Retrieval 或 Issue 上下文不存在。投影不可用时，可按稳定身份直接读取已知 Revision；不能把旧投影静默当成最新，也不能把不可用伪装成 Complete + No Match。

Recall Projection 是可重建的派生视图，不是 Knowledge Release 或权限的权威。命中候选后、返回任何标题 / 摘要 / Claim / Evidence 元数据前，必须回查权威知识身份和当前资格。投影预过滤不构成安全边界。

## 5. Recall 响应：候选摘要应包含什么

Recall 默认返回轻量、可核查的候选，而不是直接把整篇 Topic 或 Evidence 原文塞入 Agent 上下文。

每个可见候选至少表达：

| 信息 | 用途 |
|---|---|
| Knowledge Item 身份 | 后续可稳定展开和引用 |
| Knowledge Revision 身份 | 明确当前命中的是哪次内容修订 |
| Knowledge Release 身份 / 状态 | 证明它是哪个正式发布版本及当前是否可消费 |
| 作用域 | Team 或具体 Project |
| 主题与 Claim 摘要 | 快速理解结论是什么 |
| 知识类型 | 事实、决策、实践、故障经验、解释等 |
| 适用条件 | 判断在哪些项目、版本、环境和工作类型可用 |
| 限制 / 反例 | 防止把局部经验泛化 |
| 有效性与复核状态 | 区分已核验、待复核、受影响和暂停投递 |
| Evidence 概览 | 说明支持依据的类型、数量 / 覆盖和可访问状态 |
| 维护责任与最近核验信息 | 知道有问题时由谁处理 |

Evidence 概览不应自动暴露私有来源名称、文档标题、Issue 编号或可反推项目身份的元数据。对当前接收者不可见的证据，可显示“存在受限依据”或等价的安全提示，但不能泄漏其身份和内容。

## 6. Read：按稳定身份读取准确版本

### 6.1 读取规则

- 从 Recall 结果展开时，按返回的 Knowledge Item + Revision / Release 身份读取，不以“latest”替代命中的版本。
- 完整正文读取返回该修订的全部结论、适用范围、限制、反例、维护责任、有效性声明和证据引用。
- 若当前版本已经变化，读取调用必须明确告知原候选是否仍有效、是否被替代或暂停；不能悄悄返回新正文并沿用旧身份。
- 如果 Agent 需要最新版本，应重新发现 / 查询当前可消费版本，再明确选择。
- 读取失败不得退化成无来源摘要而不告知。

### 6.2 Revision 与 Release 的区别

- Revision 是内容版本，说明知识正文和依据在该次修订下是什么。
- Release 是正式发布决定，说明哪个修订被批准在何种目标范围内消费。
- 同一 Revision 的正式可消费资格由 Release 状态和当前授权共同决定。
- 旧 Revision / Release 可以继续用于历史 Work / Run 引用；是否允许新的工作继续使用，取决于其当前发布 / 撤回状态和适用政策。
- 新 Revision 发布不自动改写历史引用；新 Release 发布也不自动改变 Project Adoption 或在途工作固定版本。

## 7. Evidence：引用可见与原文可读必须分开

Evidence 是知识结论的支持依据，不意味着知识消费者自动获得来源原文权限。

### 7.1 两层读取

**第一层：Evidence Reference**
- Evidence / Evidence Anchor 身份（仅在可披露时）；
- 来源类型；
- 支持 / 反驳 / 限定 / 背景关系；
- 对应 Source Revision 和位置（按可见性披露）；
- 当前可访问、受限、已撤回或待复核状态。

**第二层：Evidence Content**
- 只有当前接收者对原始来源具有读权，且派生 / 展开用途被允许时才返回原文片段；
- 若只有团队派生知识的消费权，允许阅读已发布 Knowledge Revision 的正文和安全的证据概览，但不自动展开项目 A 的原始 C1 / C2 报告；
- 来源撤权或许可撤回后，停止新展开和新投递；历史已发生的读取 / 投递记录保留。

### 7.2 Evidence 不可访问时怎么办

Evidence 原文不可访问不自动意味着正式知识一定不可用。A 域应根据发布规则、撤回范围和知识当前状态决定：
- 若该证据只是可选背景，知识仍可在明确限制下消费；
- 若它是结论成立的必要依据，来源撤回或许可失效可能导致 Release 暂停投递，需责任人复核；
- 若当前只是调用者没有原文读权，但团队派生文案仍被授权，则可以消费派生结论，不暴露原文。

不能用一个全局 Confidence 分数决定上述情况。

## 8. 选择与采用：Recall 不自动形成工作约束

### 8.1 三种结果

- **未采用**：候选不相关、不适用或当前工作不需要。可以忽略，也可以提交“无关 / 不适用”反馈。
- **参考使用**：Agent 阅读后用于理解或辅助推理，但没有成为必须遵循的正式工作约束。是否有实际使用证据按宿主能力观察。
- **本项正式采用**：有权负责人或获授权的 Agent 在工作约定范围内，明确将具体 Knowledge Revision / Release 作为本项工作依据。需要时通过既有 Work / Run Asset Pin 固定引用。

### 8.2 何时固定版本

- Recall 命中、展示或预览不创建 Work / Run Asset Pin。
- 单纯读取候选不自动固定。
- 当知识被明确选用并作为重要工作依据、验收依据或交付约束时，才固定准确版本。
- 小型探索或非关键参考可以保留引用记录，但不强制创建 Pin。
- 一旦固定，历史工作保留该版本身份；在途工作遇到知识暂停、来源撤回、权限变化或重大适用性变化时，重新核验是否可继续，而不是静默替换版本。

### 8.3 知识不等于 Harness 规则

Knowledge Recall 返回的知识不自动成为强制规则。若某项内容必须被执行、检查或阻断，需要经过 Harness 独立定义、验证、发布和 Project Adoption。Recall 不能替代 Capability Resolution。

## 9. 投递：同一知识契约适用于两种宿主路径

### 9.1 B 准备后投递

B 可以在工作准备阶段选择候选，按版本读取后将已选内容纳入 Context Contract。D 通过现有宿主适配能力准备和投递。ContextReceipt 记录本次准备 / 投递事实；实际加载和使用由宿主观察证据分别记录。

### 9.2 Agent 自主调用

Agent 在执行中直接调用 A 域 Recall / Read 时：
- 使用当前成员 / Runtime 的真实授权上下文；
- A 域对每次 Recall、Read 和 Evidence 展开分别校验；
- Agent 读取的内容如果要成为正式工作依据，仍需按 Work Contract / Work Pin 规则引用；
- 工具调用、返回内容和后续产物可按现有 AgentObservation / Usage / Evidence 关联；
- 不因为工具调用成功就自动认定知识已被理解或实际采用。

### 9.3 投递前最后核验

无论由 B 准备投递还是 Agent 自主读取，**从平台向某个具体宿主 / 接收者提供知识正文前，都必须重新检查**：
- 当前接收者身份和成员资格；
- 知识 Release 是否仍可投递；
- 派生许可是否仍有效；
- 该接收者是否有权查看本次要投递的 Evidence 内容；
- 当前 Issue / Delegation 是否仍授权该用途；
- 被固定的 Revision / Release 是否仍适用。

检索时有权不代表投递时仍有权。历史线程中已送达的正文不声称可远程删除；新投递按当前状态重新核验。

## 10. 变化、失败与重试语义

| 情况 | 消费行为 |
|---|---|
| 无相关知识命中 | 明确返回“当前正式知识未找到”；允许继续走 Project Sources / Code Retrieval / Issue 资料，不推断其他来源不存在 |
| 只有不适用知识 | 不把它作为正向结果；必要时返回安全的“不存在适用知识”说明 |
| 存在相互冲突的正式知识 | 并列呈现各自作用域、前提和依据；无法判断时交对应责任人，不做全局优先级覆盖 |
| 知识待复核 | 按风险和发布状态限制投递；不伪装成正常有效知识 |
| Release 暂停 / 撤回 / 退役 | 不进入新 Recall 可用候选；历史引用仍可审计 |
| Team 成员资格撤销 | 停止该成员新的 Team Knowledge Recall / Read / 投递；Project 权限按自身成员资格独立判断 |
| Project 成员资格撤销 | 停止该成员新的 Project Knowledge Recall / Read / 投递；不影响其仍有权访问的 Team Knowledge |
| 来源派生许可撤回 | 对依赖该来源的派生知识按撤回范围暂停新投递 / 展开并触发复核；不影响无关证据 |
| Recall 过程中权限 / 版本变化 | 返回前或读取 / 投递前复核；不满足时拒绝或要求重新 Recall |
| 宿主不支持加载观察 | 记录可证明的 Delivered，Loaded / Used 保持 Unknown |
| Agent 未使用返回知识 | 不自动生成错误或低质量结论；可记录未采用或无关反馈 |
| 工具超时 / 临时失败 | 可安全重试查询；重试时重新核验授权和当前 Release，不复用未经复核的旧授权结果 |

历史工作记录的是当时实际发生的命中、读取、选择、投递和使用；撤权影响未来的访问与投递，不伪造历史，也不声称已清除宿主历史。

## 11. Feedback：反馈指向具体知识修订

可反馈：
- 有帮助；
- 不相关；
- 不适用于当前项目 / 版本 / 环境；
- 结论错误；
- 证据不足或不可访问；
- 与另一条知识或项目事实冲突；
- 已过期 / 被替代；
- 需要补充例外或适用条件。

反馈必须关联具体 Knowledge Item / Revision / Release 和当前工作（如有），但不直接改写知识正文。Agent 可以提出反馈或修订候选；有权维护者按知识生命周期核验和处理。Recall 频次、点击量和被选择次数只是消费信号，不能自动晋升知识或转成 Harness。

## 12. 与现有业务对象的关系

| 现有对象 | 消费契约中的作用 | 不新增 |
|---|---|---|
| Knowledge Item / Revision / Release | 稳定身份、内容修订和正式消费资格 | 不新增 Recall Result 资产 |
| Evidence / Evidence Anchor | 支持结论的证据引用与位置 | 不要求每个 Chunk 成为 Evidence |
| Team / Project / Membership / Policy | 作用域和可信授权来源 | 不由 Agent 自行声明 Scope |
| Issue / Work Agreement / Decision | 当前工作意图、责任、目标和决定 | 不另建 Knowledge Task |
| Work / Run Asset Pin | 固定本项实际采用的知识版本 | 不为每次命中创建 Pin |
| ContextReceipt | 记录准备和投递 | 不用它证明模型已理解 |
| AgentObservation / Asset Usage Observation | 记录宿主实际加载、工具调用和可观察使用 | 不把工具命中直接标记为 Used |
| Knowledge Feedback | 对具体知识修订的质量反馈 | 不新增平行审核流程 |
| Multica Task / Run / Runtime / Session | 受管执行与宿主连续性 | 不为 Recall 创建新 Run |

## 13. 验收标准

Knowledge Consumption Contract 只有在以下行为都能通过真实 Provider 和宿主验证时，才算真实产品验收通过：

1. A / B / 非成员三类主体的 Team / Project Recall 结果符合授权范围；
2. 任何未授权知识的标题、摘要、Claim、Evidence ID、关系和错误信息都不泄漏；
3. Project B 能找到适用 Team Knowledge 和自己的 Project Knowledge，但不能看到 Project A 私有知识；
4. Recall 候选能按 Item / Revision / Release 稳定展开，不能静默换版；
5. Evidence 引用可见与 Evidence 原文读取权限分离；
6. Team 成员撤权、Project 成员撤权、派生许可撤回、Release 暂停分别产生正确结果；
7. 无命中不会阻止 Agent 使用 Project Sources、Code Retrieval 和 Issue 上下文；
8. 未采用 Harness 不会因 Recall 命中而生效；
9. B 准备投递和 Agent 自主调用两条路径使用相同权限与版本规则；
10. 只有实际采用的重要知识版本才固定 Work / Run Asset Pin；
11. 真实宿主能区分 Delivered、Loaded 和 Used；无法证明的状态保持 Unknown；
12. 反馈关联具体修订，不自动改写正式知识或晋升 Harness。

本轮已有双项目契约模拟覆盖其中部分授权、隔离和分流断言；它不是上述真实产品验收的替代品。

## 14. 仍待确认的问题

这些问题需要在真实 Provider / 宿主联测中回答，不应提前变成实现假设：
- 同一知识同时有 Team 与 Project 两个候选时，如何呈现共同点、差异和适用边界；
- Evidence 原文不可见但派生知识仍可见时，摘要应显示到什么程度才既可解释又不泄漏；
- 结果过多时，是否按知识类型 / 作用域分组展开比统一 Top-K 更有效；
- 长任务中知识 Release 暂停时，哪些在途工作必须停止，哪些可在负责人确认后继续；
- Agent 自主 Recall 的工具返回如何与 Work / Run Asset Pin 和 Usage Observation 关联，且不夸大实际使用。

这些属于消费体验和风险策略验证，不影响本轮确定的权威职责边界。

## 15. 最终产品定义

AgentPlatform 的 Knowledge Consumption 应表现为：

**A 域提供有权且可核查的正式知识候选与准确版本读取；B 域围绕 Issue 决定何时查、是否适用和是否采用；D 域按当前授权将已选知识提供给具体 Agent 宿主，并记录实际可观察的消费证据。**

Agent 不必理解 Team / Project 知识内部目录或资产维护细节，但必须能够知道自己读到的是什么版本、适用于什么条件、依据是什么、哪些证据不可访问，以及它是否真的被投递 / 加载。统一的是消费契约，不是所有来源的检索方式或权威归属。


## 16. 生命周期与检索可用性补充

本契约的 Release / Projection 双轨、检索覆盖状态、来源变化影响分析和在途引用处理，详见[Knowledge 生命周期与 Recall 可用性融合审查](knowledge-lifecycle-recall-availability.md)。本契约负责单次消费行为；该研究补充其依赖的知识发布、检索投影和权限变化权威。
