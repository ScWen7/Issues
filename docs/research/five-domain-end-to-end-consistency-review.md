# AgentPlatform · 五个核心能力域端到端协作一致性审查

> 状态：架构一致性审查完成  
> 分支：design/system-architecture-convergence  
> 审查范围：A Knowledge、B Work、C Harness、D Execution & Delivery、E Evaluation / Improvement 的职责交接、事实权威、生命周期和反馈闭环。  
> 基线：当前 system-architecture、core-business-object-model、cross-layer-contracts、knowledge-management-lifecycle 及 Topic 3B 证据。  
> 非目标：不修改冻结的产品定位、五域划分或 Multica 边界；不进入数据库、API、部署或工程切片。

## 1. 总体判断

当前五域架构的核心方向成立，五域之间没有必要再增加一个统筹控制域。真正需要解决的是**跨域交接时，谁提供事实、谁作业务决定、谁维护定义、谁执行、谁记录结果**。

五域不是固定流水线，也不是五个独立后台。它们围绕 Issue 形成按需协作：

- A 提供有证据、可授权、可版本化的知识；
- B 维护研发目标、责任、决定和工作推进；
- C 提供经过治理的研发方法与约束；
- D 连接真实执行并形成交付和执行证据；
- E 对执行和结果作独立评价，定位改进方向。

**Issue 是工作主线；Multica 是执行账本；Release 是资产发布事实；Project Adoption 是项目采用决定；Work / Run Pin 是本次实际选择；ContextReceipt / Observation 是投递与消费证据。** 任何一个能力域都不能替代其他域的权威决定。

本轮没有发现需要新增能力域或重建 Multica 的理由。发现的是几处需要统一表达的跨域契约，以及两处需要防止未来实现越界的高风险边界。

## 2. 五域责任矩阵

| 能力域 | 拥有的业务事实 / 决定 | 向其他域提供 | 接收什么 | 不得越界 |
|---|---|---|---|---|
| A · Knowledge | Source Connection / Item / Revision、Knowledge Item / Revision / Release、证据定位与知识治理、派生许可、知识消费资格 | 正式知识候选、准确修订、Evidence 引用 / 可访问性、来源修订与知识影响信息 | 来源变化、Issue / Run / Artifact / Finding 证据、消费反馈 | 不拥有 Issue 目标、Run 终态、Artifact / Candidate 交付权威或 Harness 强制规则 |
| B · Work | Issue、Work Agreement、Decision、Assignee / Accountable Member、Delegation、Project Workflow、SOP Execution | 工作意图、授权、责任交接、适用范围、采用决定的工作上下文 | A 的知识、C 的方法、D 的执行与交付结果、E 的 Finding | 不复制知识正文或索引；不改写 Harness 定义；不创建平行 Run；不把评价结果当业务验收 |
| C · Harness | Harness Asset / Revision / Release、Rule / Skill / Playbook / SOP Definition / Script / Scorer / Rubric 定义及验证 | 可用方法、强制规则、流程定义、执行工具契约和评价标准定义 | A 的事实与经验依据、E 的 Finding / Benchmark 证据、项目配置和采用反馈 | 不拥有 Issue 工作实例和总责；不拥有 Run 执行账本；不替代 E 执行独立 Evaluation |
| D · Execution & Delivery | Host / Runtime 观察、Artifact / Candidate 交付事实、Delivery Record、Evidence 事实及来源关联 | Run 结果、制品、候选、执行 / 工具 / 用量证据、投递与加载观察 | B 的执行授权和交付要求、C 的执行方法、A 的获准上下文 | 不重复 Multica Run / Usage；不作业务验收、知识发布或 Harness 发布决定；不扩大来源权限 |
| E · Evaluation & Improvement | Evaluation 实例 / 结果、Finding、Improvement Proposal、Benchmark 结果、度量与成本分析 | 评价结果、根因分类、改进候选和验证证据 | D 的 Run / Artifact / Candidate / Evidence，C 的 Scorer / Rubric / Evaluation Definition，B 的 Work Agreement / 验收目标，A 的知识与历史依据 | 不替代 Issue 验收；不发布知识或 Harness；不把 Finding 自动变成改进；不把模型判断伪装成事实 |

## 3. 高风险跨域边界：定义、执行、事实、决定分离

### 3.1 SOP：C 定义，B 委托与执行治理，D 运行

- C 维护 SOP Definition / Revision / Release：步骤、输入输出、依赖、门禁、重试、返工和交还条件。
- B 根据 Issue Work Agreement 决定是否采用 / 委托 SOP，创建并维护 SOP Execution、Node Activation、Node Attempt 的业务流程状态；业务目标和保留决定仍归 Issue。
- D 沿 Multica 原生 Task / Run / Runtime 实际执行节点，提供工具调用、产物和回执。
- E 可以评价 SOP 效果，但不决定当前 Issue 是否验收，也不修改 SOP 正文。

边界判定：**SOP 的定义与执行实例不能放在同一个域；节点执行状态不应再复制一套 Run 状态；SOP 不能成为第二个 Issue。**

### 3.2 Evaluation：C 定义标准，E 负责评价，B 负责业务验收

- C 维护 Scorer / Rubric / Evaluation Definition 的内容、版本、适用范围和发布。
- B / Project Configuration 中有权成员决定哪些评价是当前工作或项目的必需门禁、采用哪个版本。
- E 创建 Evaluation 实例，固定输入快照、标准版本、执行器和结果；形成 Finding / Benchmark / Improvement Proposal。
- D 提供被评价的 Run、Artifact、Candidate 和 Evidence。
- B 的有权成员依据 Work Agreement 和交付证据作业务接受 / 退回 / 例外决定。

边界判定：**评价通过不等于业务验收；Benchmark 通过不等于 Harness 发布；Harness 发布不等于 Project Adoption；Project Adoption 不等于本项实际使用。**

### 3.3 Evidence：D 提供执行事实，A 维护知识证据关系，E 维护评价判断

同一事实可以被多个域引用，但不能被复制成多个“权威事实”：
- 来源原文 / Source Revision 仍由原来源系统维护，A 负责连接、解析和定位；
- Run、工具调用、Artifact、Candidate、宿主输入等执行 / 交付事实由 D 记录或引用原生来源；
- A 的 Knowledge Revision 引用 Evidence，说明它支持、限定或反驳哪条知识 Claim；
- E 的 Evaluation / Finding 引用相同 Evidence，给出评价标准、观察和归因；
- B 的 Decision 引用相关证据，作当前业务决定。

边界判定：**D 不替 A 判断知识结论；A 不复制 D 的执行账本；E 的评分和归因不是原始 Evidence；B 的决定不改写来源事实。**

### 3.4 Release / Adoption / Pin / Receipt：四个不同阶段

| 概念 | 谁负责 | 回答什么 |
|---|---|---|
| Release | A 或 C 的资产治理者，复用公共 Release 语义 | 这个 Knowledge / Harness Revision 是否正式发布？ |
| Project Adoption | 项目有权成员 / 项目配置 | 项目是否采用这个已发布版本、适用范围是什么？ |
| Work / Run Asset Pin | B 的工作选择，附着既有 Work / Run | 本项工作实际固定采用了哪个版本？ |
| ContextReceipt / Observation | D 的投递和观察能力 | 哪些内容准备、投递、加载或被可观察地使用？ |

不得把四者合成一个“Active / Enabled”状态。撤回 Release 会阻止新消费；撤销 Adoption 影响该项目后续选择；Work Pin 保留历史选择身份但不授予永久访问权；Receipt 记录当时发生的投递事实。

### 3.5 知识与 Harness：共享证据，不共享治理

- A 的知识描述事实、经验、解释和适用条件。
- C 的 Harness 把被确认的方法转成可执行、可评估、可强制的资产。
- E 评价 Harness 的效果，并可提出知识或 Harness 两类不同候选。
- 同一 Finding 可以同时支持 Knowledge Revision 与 Harness Revision，但两者必须分别核验、分别发布。
- Knowledge Recall 命中 Skill / Rule 文档不意味着本项采用；Harness Resolution 不能靠语义 Recall 决定。

边界判定：**知识不自动晋升为 Harness；Harness 失败也不自动证明知识错误。**

## 4. 一条研发工作如何穿过五域

以“项目新增区域数据导出功能”为例。此例只用于检验域间交接，不引入新的顶层流程。

### 阶段 1：工作建立与准备

1. B 的 Issue / Work Agreement 确认目标、范围、责任、完成条件和决定权。
2. B 按本项任务决定是否需要知识补充；A 提供适用的 Team Knowledge / Project Knowledge 候选。
3. Project PRD 由 A 的 Source Connection / Source Item 指向原始权威，按接收者权限直接读取，不要求先转成 Knowledge。
4. 代码实现通过 Project Code Wiki / 当前代码工具按仓库 Commit 基准读取。
5. C 提供已发布且项目已采用的 Harness 能力；B 按本项工作选择必要版本。
6. B 固定实际采用的 Knowledge / Harness 版本及来源 / 代码基准。D 通过现有宿主通道投递，记录 Prepared / Delivered；可观察 Loaded / Used 分别记录。

### 阶段 2：执行与交付

1. B 决定负责人自主推进、一次性协助、持续 Main Bot 委托、子 Issue 分工或 SOP 委托。
2. C 提供所选 Skill / Playbook / SOP 定义；B 负责本次 SOP Execution 的业务范围与交还。
3. D 沿 Multica Task / Run / Runtime 执行，记录真实宿主活动和原生 Usage。
4. D 形成 Artifact / Candidate / Evidence；Candidate 固定交付组合及适用 Work Agreement。
5. B 的有权负责人 / Acceptor 按工作约定消费 Candidate，作接受、退回、待决定或例外决定。

### 阶段 3：评价与改进

1. 只有在项目门禁、风险或改进价值要求时，E 才运行 Evaluation；使用 C 发布的标准，引用 D 的执行和交付证据。
2. E 形成 Finding，区分当前工作问题、知识问题、Harness 问题、Project / Policy 问题、Runtime / Tool 问题、Measurement 问题或未知根因。
3. 当前 Issue 的修复由 B 继续组织；跨工作知识改进由 A 的维护者核验发布；Harness 改进由 C 的维护者验证和发布；项目例外回到有权成员。
4. 后续工作分别消费新 Knowledge Release / Harness Release，并通过 D 的实际投递和观察、E 的结果评价判断改进是否有效。

## 5. 关键跨域交接契约

| 交接 | 提供方 → 接收方 | 必须携带的事实 | 接收方必须确认 | 失败 / 不完整处理 |
|---|---|---|---|---|
| 知识供给 | A → B / Agent | Item、Revision、Release、Claim、适用范围、限制、Evidence 可访问性、检索覆盖状态 | 当前接收者权限、适用性、是否采用 | 无命中与检索不完整分开；权限不足不泄漏元数据 |
| 工作授权 | B → D / Agent / SOP | Issue、Work Agreement 版本、授权代际、目标、允许动作、交付和停止条件 | 当前授权仍有效、输入和资源齐备 | 变更 / 撤权阻止新动作；核对已发生副作用 |
| 方法供给 | C → B / D / Agent | Asset、Revision、Release、依赖、适用范围、执行 / 输出契约 | 项目采用、本项选择、版本和能力可用性 | 未发布 / 未采用 / 不兼容不得静默当成强制生效 |
| 执行与交付 | D → B | Run 原生身份、执行段、Artifact / Candidate、Evidence、覆盖范围、Unknown | 结果对应当前 Work Agreement、交付完整、证据可核验 | Run 结束不等于交付接受；缺证据进入补充 / 退回 |
| 评价与 Finding | E → B / A / C / D | Evaluation 输入快照、标准版本、结果、Finding、证据、归因状态 | 有权接收方确认归属和处理路径 | 根因未知继续调查，不强行创建知识 / Harness 候选 |
| 知识 / Harness 发布 | A / C → B / Project | 新 Revision、Release、差异、适用范围、影响引用 | 项目是否采用，哪些在途工作需重新确认 | 发布不自动改写 Adoption / Pin |
| 改进效果 | D / E → A / C | 后续使用版本、真实交付结果、评价样本、覆盖范围 | 改进是否有效、是否回滚或继续迭代 | 使用频次不能代替效果；无法归因保持 Unknown |

## 6. 跨域状态不能混成一个状态机

以下状态必须分别保留权威：
- Issue：当前工作目标、责任、工作状态和业务决定；
- SOP Execution：受托流程节点和交接状态；
- Harness / Knowledge：Revision、Release、Adoption；
- Recall Projection：索引当前、陈旧、失败或不可用；
- Multica：Task / Run / Runtime / Usage；
- Delivery：Artifact / Candidate / Evidence / 接收回执；
- Evaluation：Evaluation / Finding / Proposal / Benchmark；
- Host Observation：Prepared、Delivered、Loaded、Used 的实际可观察阶段。

一个状态变化可以影响其他对象，但不能静默改写它们。例如：
- Knowledge Release 暂停会影响新 Recall / 投递资格，不会把 Issue 自动标成 Blocked；
- Run 失败可以触发 SOP 重试或 Issue 处理，但不自动决定业务失败；
- Evaluation 失败可形成 Finding，不自动退回 Candidate；
- Candidate 退回由 B 按 Work Agreement 消费，不能由 E 直接改写 Issue；
- Harness 新版本发布不自动改变项目 Adoption 或在途 Work Pin。

## 7. 对现有架构文档的收敛建议

### 7.1 已一致、应保持

- 五个核心能力域及其职责边界；
- Issue 是研发工作的唯一业务归属；
- Multica 继续拥有 Project / Issue / Task / Run / Runtime / Session / Usage 原生执行事实；
- A / C 分别治理 Knowledge 与 Harness；
- B 负责 SOP Execution 和业务决定；
- D 负责真实执行、交付和证据关联；
- E 负责 Evaluation / Finding / Improvement / Benchmark；
- Release、Project Adoption、Work Pin、ContextReceipt、Observation 分离；
- Evaluation 不是每项生产工作的必经阶段；
- 同一 Evidence 可被多个域引用，结论独立。

### 7.2 需要补充到架构基线的规则

1. **Evaluation 定义与执行分离**：Scorer / Rubric / Evaluation Definition 归 C；Evaluation 实例和 Finding 归 E；门禁是否必需、采用哪个版本由项目配置 / B 工作约定确定。
2. **SOP 定义与执行分离**：SOP Definition 归 C；SOP Execution / Node Activation / Node Attempt 归 B；实际 Task / Run 归 Multica / D。
3. **Evidence 三方边界**：D 提供或引用执行 / 交付事实；A 维护 Knowledge Revision 的证据关系；E 维护 Evaluation / Finding 的判断；三者引用同一事实，不复制权威记录。
4. **跨域交接的最小回执**：提供方声明对象身份、版本、授权和覆盖；接收方确认适用、采用、消费或拒绝；缺项与 Unknown 显式保留。
5. **状态影响而非状态合并**：Release、Adoption、Pin、Receipt、Run、Candidate、Evaluation、Finding 分别维护自身生命周期，跨域只产生受影响范围和后续处理。

### 7.3 不应新增

- 全局 Coordinator / Orchestrator 能力域；
- 第二套 Issue、Task、Run、Runtime 或 Usage；
- 统一资产内容系统取代 Knowledge 与 Harness 的分别治理；
- 第二套 Evidence / Artifact / Candidate 权威仓；
- 统一总状态机；
- 每个 Issue 必须运行的 Evaluation 或 Recall 流程；
- 新的通用 Context Compiler 或 Recall Runtime。

## 8. 当前未解决的问题与验证优先级

### P0：必须在进入技术承载前回答

1. **跨域采用与在途工作**：项目撤销 Knowledge / Harness Adoption、Release 暂停、Work Agreement 修改同时发生时，当前工作如何确定继续、重取材、暂停或由谁决定？
2. **Evidence 权威与来源撤权**：同一执行证据被 Knowledge 和 Evaluation 引用，来源 / 证据访问权变化时，如何分别影响知识发布、评价复现和历史工作审计？
3. **Evaluation 门禁闭环**：项目把某个 Evaluation 作为必需门禁时，E 的结果如何回到 B 的交付消费，而不让 E 越权验收 Issue？
4. **D 的本地宿主断联**：执行者 Runtime / Host 不在线时，B 的 Issue 责任、SOP Execution 和跨成员接手如何继续；不引入 Coordinator Pool。
5. **Finding 分诊**：如何保证 E 不把同一 Finding 同时复制成多个相互冲突的知识 / Harness / Issue 结论。

### P1：进入真实项目场景验证

- 一次 Issue 同时引用 Team Knowledge、Project Knowledge、Project Source 和代码基准；
- 一个 SOP 节点使用 C 发布的方法，经 D 执行后由 B 消费；
- 一个 Evaluation 门禁读取 Candidate，E 给出 Finding，B 作业务决定；
- 同一 Evidence 同时支持交付验收、知识提炼和 Evaluation；
- 一项 Knowledge / Harness 发布更新如何影响不同状态的在途 Work。

### P2：后续演进观察

- 多宿主对 Loaded / Used 的可观察能力差异；
- 评价与成本数据的覆盖率和归因边界；
- 高频 Finding 的聚类、去重和责任路由；
- 跨项目采用经验后的效果回收与反例发现。

## 9. 最终判断

五域架构已经具备清晰的核心责任，不需要新增统筹域或把它们合并成一个大系统。下一步应优先补齐 P0 的跨域一致性规则，并通过一条同时涉及知识、Harness、Issue、Run、交付和 Evaluation 的真实工作场景验证。

**五域真正融合的标准不是它们共享一个入口，而是每次跨域交接都有明确的权威来源、责任人、版本、授权、接收确认和失败出口；任何域都不能替另一个域作出它不拥有的决定。**

本轮不进入数据库、API、部署和工程实现；先完成 P0 决策与场景验收。


## 10. 与 Topic 3B 真实案例的对照

本轮不是重新发明场景，使用 Topic 3B 已有订单导出样本回归五域边界：

| 域 | 真实案例中的事实 / 机制 | 能证明什么 | 不能证明什么 |
|---|---|---|---|
| B · Work | 原订单导出 Issue 的 D2 决定、开发 / 核验分工和 C1 → C2 返工 | 同一 Issue 决定、责任和验收依据是工作主线 | 不证明知识或 Harness 自动拥有 Issue 决定权 |
| A · Knowledge | C1 / C2 两份报告形成团队测试经验；含项目订单号草稿被退回，逐来源许可、目标受众授权、独立团队发布、单来源撤回和复审均有检查 | 项目证据经授权与复审可以派生为团队知识，原始项目报告和团队派生文案分权 | 不证明生产 Knowledge Recall Provider 已接入 |
| C · Harness | D1 / D2、R1 / R2、S1 / S2 的发布、采用、版本固定和替代关系；Role / Skill / Playbook 的选用与冲突对照 | 规则版本、项目采用、本项选用和实际输入是不同事实 | 不证明所有 SOP 定义与执行实例已在同一真实场景完整联动 |
| D · Execution & Delivery | Codex / Claude Code 真实工具调用、模型请求输入观察、Run 绑定、XLSX Artifact、Candidate 和跨机接续回执 | 宿主调用、输入、结果、交付制品和消费可以逐层核验 | 不证明所有宿主都有同等 Loaded / Used 观察能力 |
| E · Evaluation / Improvement | 上游 TeamAI / LoopForge 的源码和测试机制被对照；AgentPlatform 的 C1 / C2 报告与知识贡献复审有确定性验证 | 有可用于改进分析的交付与验证事实，外部系统的 Evaluation 机制可作设计参照 | 本次 AgentPlatform 订单案例尚未形成一个由 E 正式创建、固定评价输入并回流 Finding 的完整 Evaluation 实例 |

### 10.1 订单案例对五域融合的真实判断

现有 Topic 3B 对 A、B、C、D 的局部交接已有实证，尤其是：
- D2 作为 Issue 业务决定，不被 R2 或 S2 替代；
- R2 / S2 的发布和采用不等于宿主已收到，Codex 实际请求探针证明旧规则仍可能留在历史输入；
- C1 / C2 的 Run、核验报告和工作簿为知识提炼提供证据；
- A 的团队经验发布不开放 Project A 原始报告；
- D 的跨宿主回执和制品由接收方独立核验，不由生产者自称通过。

但 E 域在本项目的完整闭环仍是主要缺口：当前案例有核验脚本和独立结果，但尚未将其完整组织为 AgentPlatform Evaluation 实例，明确固定 Evaluation Definition、输入快照、结果和 Finding，并由 B 消费该 Finding、由 A / C 分别决定是否形成改进候选。

因此下一阶段最有价值的实证不是重做订单开发，而是**在已有 C1 / C2 证据上补一条最小 E → B / A / C 闭环**：E 依据 C 发布的评价标准，对 D 提供的 Candidate / Evidence 建立独立 Evaluation；结果形成 Finding；B 决定当前 Issue 如何处理；A 或 C 只在对应维护者确认后形成各自候选。该实验不得让 E 代替业务验收或自动发布。


## 11. E → B → A / C 闭环的契约级验证结果

随后使用原有 C1 / C2 固定报告补充了[Evaluation → Issue → Knowledge / Harness 闭环验证](five-domain-evaluation-closure.md)，没有重新执行订单开发或伪造新的业务样本。

**实际完成的验证：**
- E 以 C1 / C2 报告摘要、Candidate、源 Run、核验器版本和 Artifact 摘要构造独立评价记录；逻辑 Evaluation Run 与源 Run 分离。
- C1 的 A2 失败形成高严重度 Finding，精确引用 C1 报告和东区工作簿摘要；根因仍为 unknown。A3 通过不能抵消 A2 权限硬要求。
- C2 的 A2 / A3 均通过，不制造 Finding。
- 事后评价默认 advisory-only。只有显式门禁声明且源 Run / Scorer 版本精确匹配时，才可能形成门禁结果。
- B 的模拟消费要求 Issue Accountable Member 身份。C1 显式返工；C2 仅提交业务验收，不由 Evaluation 自动接受 Candidate 或完成 Issue。
- E 按精确 C1 / C2 报告摘要关联 Topic 3B 已有知识贡献；该贡献当前最终状态为 retired，故只请求 A 维护者复核，不自动创建新 Release 或恢复旧版本。
- 真实 C1 / C2 使用同一核验器，且核验器正确检出 C1 的 A2 失败。因此本案例没有证据支持 Harness 缺陷，不创建 C 候选。
- 另用合成路由用例验证：若同一 Finding 的独立证据分别支持 Knowledge 与 Harness 两种根因，可以向 A、C 建立两个独立待分诊路径，但不会合并发布或自动改变 Adoption。

GitHub Actions 实际执行 **23 / 23 项回归通过**：[运行记录](https://github.com/ScWen7/Issues/actions/runs/44466281176)。

### 11.1 对五域融合成熟度的修正

E → B → A / C 的**产品责任和决策边界已通过确定性契约验证**，但生产集成仍未完成：
- 原型中的 Evaluation Run 身份是逻辑测试身份，没有真正创建 Multica Task / Run；
- B 的返工 / 交验收决定是契约测试显式输入，不是对历史 Issue 决定的伪造；
- A 的知识贡献状态来自既有实验账本，未在本轮重新执行发布或复审；
- C 的双路由仅为合成用例，C1 / C2 真实样本未证明 Harness 缺陷；
- 尚未在真实工作台完成 Evaluation 持久化、真实成员决策和后续生产效果回收。

因此，原审查中“E 域缺少完整闭环”的判断收敛为：**产品契约与分流规则已有确定性验证；真实 Evaluation Run、Issue 决策持久化和后续生产效果联测仍是下一项实证缺口。**
## 12. VS-3 真实 Evaluation 前置条件的源码复核

在 E → B → A / C 的契约实验之后，继续对固定 Multica 源码 `71683141a764ed3b1620db4bc26a2d0a098f135c` 做了 Task 生命周期隔离审查。发现原生 Task 来源证据不等于 Execution Purpose；当前 pending 唯一性、Comment Coalescing、Session 恢复、Issue Wakeup 和 Usage 视图均未提供统一 Governance Purpose 隔离。

该结论已形成[VS-3 · Multica Evaluation / Governance Task 隔离源码取证](vs3-evaluation-multica-runtime-evidence.md)，并回写[VS-3 技术承载契约](../architecture/vs3-evaluation-technical-contract.md)。在 Purpose 适配及 G1–G12 回归完成前，不应启动真实 Evaluation Task。

这不是增加新能力域或第二套执行系统，而是保护现有 Multica 生产协作语义所必需的执行用途边界。