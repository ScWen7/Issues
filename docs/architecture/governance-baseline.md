# 架构治理基线：以 Multica 为基座的融合式产品

版本：V1.1 · 交叉审查修订 · 2026-11-15

本文件统一当前架构设计的所有权和扩展规则，遵循用户指令与 `AGENTS.md`。各专题与本文件冲突时，应按本文件修订；不得在专题内部自行恢复被本文件取消的平行系统。架构推导、用户确认与待决事项分别记录在[设计基线表](overview.md#设计基线与决策效力)，文档换版本身不产生用户确认。

## 1. 总体方向

本项目建设的是**以 Multica 为平台基座，融合 TeamAI 团队能力治理与 LoopForge SOP / 工程级 RSI 能力的研发协作产品**。这不是三个系统并列集成，也不是重新设计一套协作平台后再接入 Multica。

- **Multica 是产品底座**：承载工作组织、协作控制、任务派发、本地 Runtime 执行和基础执行记录。
- **TeamAI 是能力来源**：提供团队 / 项目资源治理、Role / Skill / Rule / Playbook、知识检索、上下文选择与投递、AgentObservation、Scorers 和团队能力改进机制。
- **LoopForge 是流程与工程进化来源**：提供可组合 SOP、DAG、Agent / Script / Human Gate、Trace 评测、结构化 Findings、改进处方、Benchmark 和 RSI 闭环。

本项目的产品价值来自三者的融合，而不是复制三者各自已有的基础设施。

## 2. 架构所有权：谁是事实权威

| 领域 | 唯一权威 / 基座 | 融合扩展 | 明确禁止 |
|---|---|---|---|
| 工作事项、负责人、协作讨论 | Multica Issue / Sub-Issue、Assignee、Comment、Squad | 必要的研发工作约定、验收引用 | 第二套 Issue、业务 Task、负责人或评论系统 |
| 工作状态与交接 | Multica status / Project Workflow / 既有权限写入路径 | 研发交付所需的最小校验与决定引用 | 平行工作状态机、第二套 Issue 完成权威 |
| 执行与调度 | Multica Run、Daemon、Runtime、队列、Backend | TeamAI Skill Driver 以适配方式驱动既有执行；SOP 决定节点就绪 | 第二套 Run、Daemon、Runtime、Process Supervisor、派发队列 |
| 宿主会话与进程 | Multica Provider Backend、Session、取消 / 恢复 / 进程管理 | 仅补充 Multica 缺失的宿主能力或证据 | 为同一宿主再建并行执行适配器，除非有明确兼容性缺口 |
| 执行事实与基础用量 | Multica Run / Trace / Task Usage / ContextReceipt / 结果回执 | 原生回执之上的调用级加载证据、TeamAI Observation、来源身份、覆盖范围和计量扩展 | 与 Multica Usage 并行的第二套成本账本 |
| 团队能力与知识 | 复用 Multica Agent / Skill / Plugin / Context 基础能力 | TeamAI 的作用域、版本、检索、发布、投递与加载核验 | 不经底座盘点就重建资产仓库、Agent 注册和分发系统 |
| SOP 与工程流程 | Multica Issue / Project Workflow / Run 是承载面 | LoopForge SOP 定义、DAG、节点执行逻辑、Sub-SOP、门禁与返工 | SOP 另建 Issue 状态、Run、Runtime 或独立派发权威 |
| 质量评价与 RSI | Multica 提供被评价的真实 Run / Trace / Usage | LoopForge Evaluator、TeamAI Scorers、Benchmark、Findings、改进处方 | 让评价器改写执行事实或绕过资产发布治理自动生效 |

## 3. 扩展原则：先复用，再补缺口

任何新增对象、服务、适配器或状态机制，在设计前必须完成以下判断：

1. **底座盘点**：指出 Multica 对应的源码模块、接口、数据对象、事件或测试。
2. **覆盖判定**：说明原生能力能否满足目标场景；区分“已有”“配置可达”“需要扩展”“确实缺失”。
3. **最小扩展**：优先使用配置、现有 API / 事件 / Hook / Backend 扩展点；只有无法通过扩展点满足时才修改 Multica 核心。
4. **权威归属**：新增数据必须声明归属哪个既有 Issue / Run / Session / Asset，并说明是否只是派生视图。
5. **失败与恢复**：说明与本次变更相关的撤权、重试、重复上报、进程退出、迟到回报和恢复如何沿用 Multica 原有生命周期；已证实的缺口须列出补齐规则。
6. **验证证据**：用真实源码、测试或目标宿主实测证明缺口和修复，不以概念推演替代。

新增能力必须回答“为什么 Multica 现有机制不够”。回答不了，不新增。

**保留业务约束，再选择实现载体。** 单一事实权威约束对象归属，具体的节点前置、执行轮次、报告消费、验收和权限规则仍须满足。撤回独立 Grant / Binding 服务的预设，不撤回已观察到的控制缺口。已有研究可直接作为缺口证据；升级源码后复核受影响结论，无须把每项既有发现重新降为未知。

### 固定版本的底座盘点

以下以 Multica [`fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc`](https://github.com/multica-ai/multica/tree/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc) 为本轮源码基准。早期研究使用的其他提交保留原版本标记；产品扩展尚待真实 Multica 集成验收。

| 能力 | 已有事实与缺口 | 最小融合方向 |
|---|---|---|
| Script 托管 | [Backend 工厂](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/agent.go#L502-L564)提供编码 Agent 协议；当前订单脚本实测走 TeamAI 命令驱动，见[能力矩阵](execution-capabilities.md)。任意确定性脚本经 Multica Run 执行尚缺对应承载 | 在现有 Run / Daemon 链中适配受管命令，复用 Runtime、工作目录、取消与结果通道；具体扩展点由 3A 核对 |
| 本地 Credits 与请求去重 | 服务端 Task Usage 已支持 `credits_micros`；[Daemon 用量结构](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/types.go#L309-L322)尚无 Credits；[当前写入](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/task_usage.sql#L1-L20)按 task / provider / model 覆盖，尚缺请求 / Stage 身份和多源合并规则 | 补齐 Backend → Daemon → Usage 的计量身份、分指标合并与更正。Run 明细已有 Credits，[Issue 摘要与每日看板](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/task_usage.sql#L84-L165)仍需按原生单位汇总并展示覆盖。云端 `qoder_cloud` 支持与本地 Qoder 分开记录 |
| ContextReceipt | 原生准备与投递回执存在；恢复会话还会携带[回执列表之外的历史](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/context_receipt.go#L61-L77)。准备证据和每次模型调用的实际输入分别核验 | 沿原 Run 关联调用、材料版本及原生证据；保留换版前后记录，缺实际观察时标缺项 |
| 验收资产固定版本 | 普通 Skill 缓存缺失时可接受服务端新版，原生删除会清除版本历史，见[固定源码与原生实验](../research/topic-03b/native-assets.md#multica) | 验收 Rule / Script 固定不可变内容引用并核对实际摘要；退役保留获准的历史内容或不变引用 |
| 工作流重入与 SOP 前置 | [步骤守卫](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/issue_workflow_entry.go#L118-L123)仅比较步骤名；早期[派发与 child_done 研究](../research/topic-02/multica.md)已记录多入口、阶段关闭和业务结果的差异 | 在 Multica 既有写入 / 派发链落实本轮激活、前置条件和结果消费检查；验证 A→B→A、取消子项及旧候选晚到 |
| Run 谱系 | [AgentTaskQueue](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/generated/models.go#L124-L185)已有父执行、委托、重试、重跑及触发证据等关联 | 逐字段核对现有写入方、含义和读取方，再映射 SOP / 评价关系；业务含义不同的轮次保留最小附属关联 |

源码已证明的数据通路缺项与宿主尚未暴露的字段分别登记。例如本地 Credits 上报链需要扩展已确定；目标 Qoder ACP 是否提供请求 Credits，仍由该入口的版本化实测回答。

## 4. SOP 与 Multica 的关系

SOP 是可被 Issue / Project Workflow 调用的研发执行方法，不是另一个协作平台。

- Issue 决定目标、责任、范围和最终业务接受。
- Project Workflow 负责 Issue 层状态推进及负责人交接。
- SOP DAG 负责被调用范围内的专业步骤依赖、输入输出、门禁和返工路径。
- DAG 节点需要实际执行时，必须通过 Multica 现有 Run / Runtime / Backend 执行；不得绕过底座另行启动一套平台执行队列。
- 节点、尝试、产物和 Findings 是 SOP 运行所需的流程数据，可作为附属记录或引用；它们不拥有 Issue 状态、Run 生命周期、成员权限或最终验收权。
- Agent 节点复用 Multica 现有 Backend；Script 节点沿现有 Run / Daemon 补齐受管命令承载。Human Gate 引用 Issue 上有权成员对具体候选和问题的决定，复用评论与权限，并补齐默认等待、版本匹配和结果消费校验。
- 是否需要 Node Attempt、Delegation Round、额外幂等键等扩展，必须由 LoopForge 原生语义与 Multica 现有能力的差异证明；不得先验地全部建成新控制平面。

SOP 托管范围内，各派发入口采用相同的节点前置与当前执行轮次检查；普通自由协作继续沿用原工作机制。`child_done` 是协调信号，成功交付由本轮候选、必需制品和核验决定证明。消费结果时核对当前有效尝试与接收节点。出口交接提交后，须能按持久记录恢复仍有效的下一项执行或成员通知。Issue 写入权限与 SOP 接收某份报告的资格分别核对，详见[专题二](02-sop-workflow.md)。

## 5. TeamAI 能力治理与 Multica 的关系

TeamAI 的能力不应被简化为“建一个 Skill 文件仓库”。应吸收其资源作用域、版本、来源、检索、选择、分发、驱动和实际加载核验机制，并尽可能复用 Multica 已有 Agent / Skill / Plugin / Context 设施。

- Agent / Role：优先沿用 Multica Agent 及其配置；补充团队角色组合与治理元数据。
- Skill / Plugin：优先沿用 Multica 已有加载与分发；补充作用域、版本、审核和实际加载证据。
- Rule / Principles / Playbook：作为可治理能力资产增量接入，不另建执行主体。
- Knowledge：补充来源、适用范围、版本有效性、检索与引用；不复制 Issue 和 Run 的工作事实。
- Skill Driver：驱动现有 Run / Session 或宿主子代理，不创建第二套 Run / Agent 执行生命周期。
- AgentObservation：对 Multica 已有事件、Trace、ContextReceipt 做补充关联与来源分级，不复制一份平行执行事实库。

版本固定、当前授权和实际输入分别核对。继续或恢复 Session 前，若其历史含已失权材料，使用现有新会话入口按当前权限重建上下文；必需材料缺失时相关工作等待。保留历史引用，当前读取和再次投递仍按当前授权检查。已验证的会话历史重带与派生知识撤权规则见[项目知识实验](../research/topic-03b/project-knowledge.md)。

## 6. 成本、质量与 RSI 的关系

- Multica Task Usage 是成本计量的基础写入和汇总链路。新增来源与计量单位应扩展既有 Usage，而不是建立独立 Cost Service。
- 原始观察可以多源并存，但结算必须回到 Multica 的实际 Run / Task 和原生计量单元，避免 Hook、ACP、OTel、转录和终态快照重复计费。
- Qoder Credits、CodeBuddy Credits、Token、USD 估价、账单实付是不同指标。未知值必须保留为 unknown；Session 累计快照不能伪装成请求增量。
- Issue、父子工作、SOP、Agent、Squad、项目与团队从同一计量事实去重汇总。业务执行、评价、Benchmark、知识抽取等活动分别分类；后台活动按实际项目 / 团队归属，历史制品复用成本与本次新增消耗分别展示。
- LoopForge Evaluator 与 TeamAI Scorers 对 Multica Run / Trace 进行评价，产出独立 Evaluation / Findings；不得覆盖 Run 终态或 Issue 验收。
- RSI 改进采用“Findings → 候选变更 → 固定输入 Benchmark → 审核 → 正式发布 → 后续真实工作观察”。Benchmark 在明确的实验范围使用候选版本，正式工作选择已发布版本；回归失败的版本保持候选并保留失败证据。不得自动修改在途 Run 或静默改变已发布版本。
- 单次工作内的修正遵循当前目标、授权、版本与预算。跨次改进按实际采用的版本及依赖组合验证。知识、能力与 SOP 资产通过审核后发布。Project Workflow 配置和人员分工由有权成员在 Multica 原项目或 Issue 上采用并记录生效范围。验收规则变更还需对应 Issue 的工作约定确认。

## 7. 设计与实现的强制审查表

每个专题设计，以及改变对象、权威归属或执行机制的实现 PR / 集成方案，必须附以下简表；可引用已有盘点和证据。验证场景按本次变更适用性选择，并说明已有证据与待执行验收。

| 问题 | 必须提供的答案 |
|---|---|
| Multica 已有什么？ | 源码路径、数据对象 / 接口 / 事件、测试 |
| 我们缺什么？ | 明确的场景缺口及失败证据 |
| 选择哪种扩展方式？ | 配置、插件 / Hook、API / Event、Backend 扩展或核心修改 |
| 谁拥有事实？ | Issue、Run、Session、Usage、Asset 或 SOP 附属数据 |
| 是否形成第二权威？ | 明确说明如何避免状态、身份、权限、计量双写 |
| 如何验证？ | 适用的正常、失败、重放、撤权、恢复、迟到事件用例；区分已执行证据与集成验收计划 |

若答案表明存在重复权威，设计不得进入实现。

## 8. 既有设计的治理处理

- 专题一：保留 Issue First 和 Multica 工作组织语义；将“底座工作假设”改为架构方向，移除允许各专题自行推翻底座的条件。
- 专题二：保留 LoopForge SOP / DAG 机制、订单双路径和控制反例；将 SOP 限定为附着于 Issue 的流程能力，重新审查 Delegation Grant、Dispatch Control Binding 的实现载体，保留已证实的前置、轮次与消费校验需求。
- 专题三 A：保留所有 Multica 源码和真实宿主研究；设计定位从“建设统一执行平面”改为“Multica 执行底座能力审计、配置与最小扩展”。
- 专题三 B：保留 TeamAI 资产治理研究；改为复用 Multica Agent / Skill / Plugin / Context 基础设施并补充治理能力。
- 专题四：沿用 Multica Usage / Run / Trace，补充异构计量、可信评价、Benchmark 和 LoopForge RSI。
- 专题五：只整合现有工作、执行、资产和评测视图，不创造新的状态权威。

历史研究、原始回执和测试不删除；它们是事实证据，不再自动等同于当前架构决策。

各专题继续引用同一份 Work Context、Execution Contract 和 Evidence & Feedback，详见[共享业务契约](overview.md#共享业务契约)。贯穿案例采用订单批量导出，案例角色、数字和决定标记为推演假设。每篇专题保留正常路径、失败处置与交叉审查反例；规则可集中维护，专题通过引用说明如何消费。
