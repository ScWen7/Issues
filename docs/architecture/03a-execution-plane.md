# 专题三 A：Multica 执行底座能力审计与最小扩展

版本：V1.1 · 底座缺口与订单执行交叉审查 · 2026-11-15

本专题不再定义或建设 TeamAI 自己的统一执行平面。**Multica 是执行底座；本专题负责理解、验证、配置和扩展 Multica 已有执行能力。**

既有宿主研究、跨机实验、真实回执和原型全部保留，作为底座审计证据。设计方向遵循[架构治理基线](governance-baseline.md)。

## 1. 目标与非目标

### 目标

- 明确 Multica 当前 Daemon、Runtime、Run、Backend、Session、Process、Workspace、Trace、ContextReceipt 的真实能力。
- 验证目标宿主与版本在 Multica 现有 Backend 中的覆盖范围。
- 找出成员已有 IDE / CLI 主动工作与中心派发之间的观测和关联缺口。
- 明确 TeamAI Skill Driver、AgentObservation、能力治理如何使用现有执行链。
- 对真实缺口提出最小扩展，并给出版本、源码和测试证据。

### 非目标

- 不新建 Host / Daemon / Runtime 管理系统。
- 不新建 Run、执行队列、Process Supervisor 或 Provider Adapter 框架。
- 不重新实现工作副本、附件、Session 恢复、进程树清理和结果回报。
- 不要求所有宿主统一使用 ACP、SDK 或同一种协议。
- 不把专题研究中发现的复杂问题自动转化为 TeamAI 自研模块。

## 2. Multica 执行底座能力地图

本轮底座源码固定为 Multica `fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc`。下表描述原生基础，已证实的扩展列在第 7 节。具体版本覆盖和边界以 [源码研究](../research/03a-source-evidence.md)、[宿主能力矩阵](execution-capabilities.md)及目标版本复测为准。

| Multica 已有能力 | 典型模块 / 机制 | TeamAI 融合时的使用方式 |
|---|---|---|
| 工作派发与领取 | Issue / Task Run 队列、Daemon claim / Start | SOP / Skill Driver 请求现有派发，不旁建队列 |
| 本地执行管理 | Daemon、Runtime 注册、心跳、容量、共享授权 | 复用成员机器和 Runtime 的在线、授权与资源信息 |
| Agent 执行 | Provider Backend、Agent Session、各宿主适配 | 直接复用目标 Provider Backend |
| 宿主协议 | ACP、Codex / Claude 等原生接口或 CLI 流 | 只在现有入口不足时补充对应 Backend 能力 |
| 进程生命周期 | launch.go、Unix Process Group、Windows Job Object、取消与 Wait | 沿用统一启动和回收路径，不再建 Process Supervisor |
| Session 连续性 | 原生 Session ID、resume / load、恢复拒绝处理 | 关联 Run 和宿主 Session，不假定一对一 |
| 工作区与制品 | 工作目录、工作副本、附件上传下载、摘要校验 | SOP 输入输出引用已有工作区与 Artifact 通道 |
| 上下文投递 | Agent brief、Skill / MCP 准备、ContextReceipt | TeamAI 资产治理提供选择，Multica 负责实际投递并回执 |
| 执行观察 | Message、Tool Activity、Result、Trace / terminal 事实 | AgentObservation 补充缺失身份、来源、覆盖和共享边界 |
| 基础用量 | Task Usage 与 Provider / Model、Token / cost；服务端支持 Credits，当前本地上报链缺字段 | 补齐 Backend → Daemon → Usage 的原生 Credits 与请求 / Stage 身份 |
| 结果接收与恢复 | 结果队列、重试、迟到回报、清理与 GC | TeamAI / SOP 以原 Run 和结果身份消费 |

## 3. 现有研究成果如何重新定位

| 既有研究 | 保留价值 | 正确架构用途 |
|---|---|---|
| Codex App Server / CLI、Claude Hooks / SDK / OTel | 真实宿主事件、请求身份、会话和用量覆盖 | 验证 Multica Backend 或既有会话接入能力；只补明确缺口 |
| Qoder ACP 与 SDK 对照 | 证明不同入口的生命周期、事件和用量差异 | 优先复用 Multica Qoder ACP Backend；SDK 探针仅用于协议能力对照，不作为默认生产执行路径 |
| CodeBuddy Stream-JSON | 真实 Stage、requestId、Credits 与快照语义 | 对照 Multica CodeBuddy Backend；补充其尚未暴露的计量证据 |
| Process Group / 清理实验 | 揭示 CLI 主进程退出与派生进程退出的差别 | 检查 Multica 统一进程管理在目标宿主上的覆盖，不另写进程管理器 |
| 跨机工作副本与迟到回报 | 验证 Run、候选、制品和回报接续 | 沿用 Multica 现有工作区、附件和结果交接机制 |
| Skill Driver / AgentObservation | 发现步骤驱动和多源观察需求 | 适配现有 Run / Session / Trace，不能形成第二套执行账本 |

## 4. 宿主适配原则

按宿主实际能力选择协议，不为统一而统一。

- **Codex**：优先使用 Multica 已有 App Server / CLI Backend 和已验证的原会话接入方式。
- **Claude Code**：复用 Multica 已有 Backend；Hooks、OTel 和转录用于补充已有会话的观察，不另启一个平行执行系统。
- **Qoder**：优先复用 Multica qoder.go 的 ACP Backend。当前 Qoder SDK 1.0.59 的 query() / Daemon 实验只说明 SDK 入口的生命周期行为，不能推翻 Multica ACP 路径，也不能证明 ACP 已提供 Credits。
- **CodeBuddy**：复用 Multica 已有适配器；固定版本的 `system` 分支只处理 Session / 状态，未解析 `usage_update` Stage / Credits。扩展已有 Backend 和本地上报链，再用 2.181.0 的真实 Stage 回执验收；该通路缺项已有源码证据。
- **其他宿主**：先检查 Multica Backend 是否已有支持；没有时按现有 Backend 抽象新增一个最小适配，不新建适配框架。

每种入口必须声明并验证：启动方式、原生 Session / Turn / Request 身份、消息和工具活动、Usage 覆盖、终态、取消、进程退出、清理、恢复及权限边界。未支持的能力明确标记 unknown / unsupported，不用时间、文本相似度或累计快照伪造事实。

## 5. 本地主动会话与 AgentObservation

中心派发之外，成员可能在自己的 CLI / IDE 中主动工作。TeamAI 需要补充的是“观察和关联”，而不是重新启动或接管所有本地进程。

建议的证据分层：

1. **宿主原生事实**：原生 Session / Thread / Turn / Request / Tool Call / Usage ID 和原始终态。
2. **Multica 事实**：Run、Runtime、Daemon、派发回执、Backend Trace、ContextReceipt、Result。
3. **TeamAI Observation**：Hook、转录、OTel、文件观察等来源补充的事件和配置证据。
4. **成员自述**：成员选择共享的文本、文件和归属说明。

关联规则：

- 已有 Run 的宿主事件只有在原生身份或可验证映射吻合时才并入。
- 一个 Session 可跨多个 Run；不得把 Session 当成 Run 的唯一键。
- 同一原生请求被 Hook、Daemon、OTel 和转录多路观察时保留多份来源，底层计量只结算一次。
- 无法证明归属时，保留 Session 级或外部来源 Observation，不强行归入某个 Run / Issue。
- 共享范围由成员明确选择，观察到不等于获准上传。

### 已有会话的控制与授权

成员交出本次输入控制、可核对宿主将携带的历史、模型、工具与 Hook，才可在原 Session 开执行段。允许历史用于模型输入与允许内容共享到 Issue 分别取得授权；中心只接收成员选区。已开放的端点访问权、工作执行权与全部历史可用性分别核对。

继续或恢复前，历史含已失权材料时，使用 Multica 现有新会话入口按当前权限重建 Work Context；必需项仍缺则相关节点等待。历史回执保留原发生时间与摘要。成员还能同时输入、未知 Hook 能接触输入或个人工具仍开放时，本次受限工作改走可控的新会话。在尚未开工、相同成员与原派发有效的条件下可沿用原 Run；宿主已经结束后重验则建立后继 Run。[真实历史重带](../research/topic-03b/project-knowledge.md) · [双客户端与 Hook 实验](../research/topic-03b/existing-session.md)

## 6. 执行生命周期：沿用底座，补充观察而非重建

Multica 已负责领取、准备、Start、执行、Result、取消、恢复和本地资源清理。本项目需要做的是确认这些状态在不同 Provider 上分别能观察到什么，并把缺失回执明确暴露出来。

同一次执行至少区分：

- 派发 / 领取事实；
- 本地准备和开工事实；
- 宿主消息、工具和模型调用事实；
- 宿主终态；
- 直接进程退出；
- 派生进程 / 资源清理确认；
- 中心收到并接受结果。

这些是对 Multica 现有生命周期的观测补充，不是新增一套 Run 状态机。某个 Provider 没有清理确认能力时，记录该能力缺失和后继保护策略，不假设成功。

### ContextReceipt 与逐调用证据

原生 ContextReceipt 在准备执行环境时汇总 brief、Skill、MCP、摘要和版本化加载判断。恢复 Session 的历史在清单之外；服务端按 task 保留一份回执，fresh retry 的重报会覆盖该份。这些是原生投递证据，逐次模型实际输入、D1→D2 换版与工具返回是否被 Hook 改写，需要在同一 Run 下关联宿主调用、原生身份和附属证据，保留各次观察。[准备回执](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/context_receipt.go#L62-L89) · [准备内容](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/context_receipt.go#L151-L169) · [按 task 覆盖](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/task_context_receipt.sql#L1-L8)

材料分别记录期望版本、实际取得字节、投递通道、宿主版本、模型调用和核验方法。摘要注明对象与算法：发布正文、分发包、适配文件、实际请求各有自己的摘要。文件写入、目录可发现、正文进入当前输入、正文只在历史出现、工具调用与内容通过分别留据。必需材料缺项阻止受影响工作；普通可选参考材料缺使用回执时保留缺项，继续其余已授权动作。具体 D1/D2 通道差异见[能力矩阵](execution-capabilities.md)。

### 回报、消费与接续

原报告 / 服务返回、模型收到的 Hook 处理后结果、SOP 节点实际消费的报告分别引用。节点消费同时核对 Run、当前节点尝试、候选、规则 / 核验器版本、具名制品及当前授权；重复投递只消费一次，旧候选晚到仍回原 Run。控制平面接受上传与节点接受业务结果分别留据，沿专题二的本轮前置和结果消费规则执行。

Hook 改写结果时保留原生调用 ID、服务与模型所见摘要及拒收依据。本案例要求两者一致，改写后的回合留下拒收证据。宿主已返回并退出后重新核验签发后继 Run，关联原 Run 与拒收原因；只读核验的目标、候选和标准仍适用时保留原节点尝试，分别记录两次执行及成本。换成员使用其自己的 Runtime、凭证和新 Run。可能已有写入的接续先查原副作用，再决定如何重试。[结果接收](../research/topic-03a/result-handoff.md) · [Hook 复验归属](../research/topic-03b/existing-session.md#hook-复验的-run-归属修订)

## 7. 只有真实缺口才允许扩展

| 候选扩展 | 允许条件 | 优先方式 |
|---|---|---|
| Script 受管命令 | Backend 工厂只提供编码 Agent 协议；订单脚本现有实测使用 TeamAI 命令驱动 | 在现有 Run / Daemon 链适配确定性命令，复用 Runtime、工作目录、启动 / 取消和结果制品通道 |
| 新宿主 Backend | Multica 没有目标宿主适配，或已有适配无法覆盖必需能力 | 实现现有 Backend 接口，复用统一进程和 Run 生命周期 |
| AgentObservation 补充 | Multica Trace / ContextReceipt 无法表达所需来源、请求身份或共享覆盖 | 扩展现有事件 / 回执，或保存可回溯的附属观察 |
| 本地 IDE 接入 | 目标宿主没有可用原生接入，且用户明确需要原会话观测 / 控制 | Hook / OTel / 原生 API 最小接入；不复制 Session 管理 |
| 进程清理增强 | 目标宿主真实复测证明现有进程组 / Job Object 机制无法清理其派生进程 | 修正 Multica 统一进程管理和 Provider 清理协商，不建 TeamAI Supervisor |
| 新用量来源 | Multica Usage 未覆盖该 Provider 的真实原生计量 | 扩展既有 Usage Entry 与来源证据，不另建账本 |
| 新工作区能力 | 现有 Workspace / Artifact 不能支持目标文件类型或接续场景 | 扩展现有工作区或附件通道 |

**已证实的本地计量缺口。** 原生 [TokenUsage](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/agent.go#L273-L293) 与 [TaskUsageEntry](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/types.go#L309-L322) 没有 Credits；[CodeBuddy system 分支](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/codebuddy.go#L243-L277)没有 Stage / Credits 解析。服务端已有 `credits_micros`，本地采集到现有 Usage 的通路仍须补齐。请求 / Stage 身份、单位、覆盖及更正沿同一计量事实维护。Qoder ACP 在目标版本是否暴露请求 Credits 则保留目标宿主待测；SDK 的 Session 快照按原口径保留。

**Script 的证据与扩展。** [Backend 工厂](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/agent.go#L502-L564)尚无任意确定性脚本入口。[订单实验](../research/topic-03a/order-export-workspace.md)证明 TeamAI / LoopForge 的命令与制品语义，附件实验证明 Multica 的传输能力。融合设计将受管命令放回 Multica Run / Daemon，由 SOP 固定脚本、输入、候选及输出要求；具体承载需通过真实 Multica 领取、Start、命令运行、取消和结果回报验收。

任何核心修改必须提供最小复现、目标版本、原生行为、当前 Multica 行为、失败证据和回归测试。

## 8. 与其他专题的交接

- 专题二：提供 SOP 节点需要的现有 Run、Runtime、结果和制品引用方式；不接受第二派发链。
- 专题三 B：提供实际材料投递、ContextReceipt、宿主调用和加载证据；不替其决定资产版本治理。
- 专题四：提供 Run、Trace、Tool Activity、Result 和 Task Usage 原始事实；计量与评价消费这些事实。
- 专题五：展示 Multica 现有工作与执行对象，以及融合后的能力治理和评测信息；不新增状态权威。

## 9. 验收标准

1. 每次受管执行使用 Multica 既有 Run 与派发链；同一 Issue 可有多次 Run，同一 Session 可服务多次 Run。
2. SOP / Skill Driver 能驱动节点执行，但实际派发和进程生命周期仍由 Multica 管理。
3. 取消、超时、Daemon 重启和迟到回报沿用 Multica 原有机制，目标宿主的缺失回执明确呈现。
4. 同一 Session 服务多个 Run 时能正确归属；不能证明时不强行归属。
5. Hook、ACP、OTel、转录等多路观察不会造成重复 Run 或重复 Usage。
6. TeamAI 资产实际投递能关联 Multica ContextReceipt 和宿主调用。
7. 任一新增 Backend 或扩展均有源码、测试及目标版本真实回执证明其必要性。

## 10. 订单贯穿案例与反例

以下沿用[订单案例](overview.md#订单贯穿案例)的推演假设：当前筛选可见订单、XLSX、最多 5,000 条，D2 新增付款时间列。D1 四列对照与 D2 五列要求分别留存；C1、C2 都在 D2 下核验，C1 的 A2 区域权限失败，C2 的 A2、A3 通过。案例角色和数字用于设计验证。

正常路径：Issue 确认 D2 → 3B 选择发布的规则与核验 Script → 现有 Multica 派发 Run → 3A 回报准备材料与实际调用证据 → 固定候选执行核验 → 回传报告、XLSX 原件及摘要 → 节点按本轮候选消费 → Issue 记录验收决定。C1 失败后针对权限返工为 C2，新核验保留新 Run / 候选关系，旧报告继续属于 C1。Script 的直接 Multica 托管仍按第 7 节集成验收。

| 观察到的失败或变化 | 本次工作如何处理 | 已有证据与集成验收 |
|---|---|---|
| 写了 D2 文件，当前模型仍只带 D1 | 按通道显式补发或核对副作用后新会话加载，取得本轮输入证据 | Codex / Claude 固定版宿主换版已实测；逐调用证据接入现有回执待验 |
| 撤权后空材料指令仍带旧历史 | 新线程按当前权限重建；必需材料缺失则等待 | Codex 四回合对照已实测；产品继续 / 恢复入口守卫待验 |
| Script 退出 0，但 C1 的 A2 不通过 | 保留技术退出和业务核验结论，阻止依赖该报告的后继 | TeamAI 命令驱动与独立订单核验已实测；Multica 托管命令待验 |
| 服务返回正确，Hook 改写模型所得结果 | 保存两份结果与摘要，当前契约拒收；结束后复验建后继 Run | Claude Hook 与后继 Run 回执已归档；统一节点消费接入待验 |
| 原机 C1 迟到、接替成员重传 C2 | 旧报告回原 Run / 候选，当前有效报告消费一次 | 原生结果重传、双身份与消费原型已有记录；整链路集成待验 |
| Qoder Result 到达、主进程退出、派生进程仍活着 | 分别展示终态、退出和清理证据，按已知持有资源决定复用 | SDK 探针已有真实反例；现有 ACP Backend 目标版本清理覆盖单独验收 |

实验入口及原始回执见[3A 研究](../research/03a-source-evidence.md)、[能力矩阵](execution-capabilities.md)、[成员会话](../research/topic-03b/existing-session.md)与[Runtime 验证](../research/topic-04/runtime-validation-1.1.88-2.181.0.md)。上述既有实验沿用原版本和结果，本轮文档修订未重跑宿主。

## 11. 六问审查表

| 问题 | 本专题答案 |
|---|---|
| Multica 已有什么？ | 固定 `fdfbfcd` 的 Daemon 领取 / Start、Backend / Session、工作区、附件、结果队列、ContextReceipt 与 Usage；源码和定向测试见第 2、6、7 节及能力矩阵 |
| 我们缺什么？ | 确定性 Script 托管、本地 Credits 字段及 CodeBuddy Stage 解析、逐调用输入历史和结果消费附属证据；Qoder ACP 请求字段属目标宿主待测 |
| 选择哪种扩展方式？ | 现有 Backend / Daemon / 回执与结果通道最小扩展；复用会话启动 / 恢复与 Runtime 授权，SOP 只提供范围和消费条件 |
| 谁拥有事实？ | Issue / Run / Session / Usage 归 Multica；输入、原生调用与接收观察附着原 Run；节点消费决定归专题二 |
| 是否形成第二权威？ | 单一派发、Run 与进程管理；附属证据描述实际发生情况，恢复 / 后继 Run 均走底座生命周期 |
| 如何验证？ | 第 10 节分别标注已测与待验；集成覆盖 D1→D2、撤权历史、Script 退出与核验分离、Hook 拒收后继 Run、重复及迟到结果、取消与清理 |
