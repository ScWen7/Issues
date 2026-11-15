# 专题三 A：Multica 执行底座能力审计与最小扩展

版本：V1.0 · Multica 基座治理修订 · 2026-11-15

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

以下是审计基线。具体版本覆盖和边界以 [源码研究](../research/03a-source-evidence.md)、[宿主能力矩阵](execution-capabilities.md)及目标版本复测为准。

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
| 基础用量 | Task Usage、Provider / Model、Token / cost / Credits 扩展点 | 沿用 Usage 写入和汇总，不建第二账本 |
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
- **CodeBuddy**：复用 Multica 已有适配器和 Stream-JSON 事件处理；对真实 Stage / Credits 覆盖做版本化验证。
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

## 7. 只有真实缺口才允许扩展

| 候选扩展 | 允许条件 | 优先方式 |
|---|---|---|
| 新宿主 Backend | Multica 没有目标宿主适配，或已有适配无法覆盖必需能力 | 实现现有 Backend 接口，复用统一进程和 Run 生命周期 |
| AgentObservation 补充 | Multica Trace / ContextReceipt 无法表达所需来源、请求身份或共享覆盖 | 扩展现有事件 / 回执，或保存可回溯的附属观察 |
| 本地 IDE 接入 | 目标宿主没有可用原生接入，且用户明确需要原会话观测 / 控制 | Hook / OTel / 原生 API 最小接入；不复制 Session 管理 |
| 进程清理增强 | 目标宿主真实复测证明现有进程组 / Job Object 机制无法清理其派生进程 | 修正 Multica 统一进程管理和 Provider 清理协商，不建 TeamAI Supervisor |
| 新用量来源 | Multica Usage 未覆盖该 Provider 的真实原生计量 | 扩展既有 Usage Entry 与来源证据，不另建账本 |
| 新工作区能力 | 现有 Workspace / Artifact 不能支持目标文件类型或接续场景 | 扩展现有工作区或附件通道 |

任何核心修改必须提供最小复现、目标版本、原生行为、当前 Multica 行为、失败证据和回归测试。

## 8. 与其他专题的交接

- 专题二：提供 SOP 节点需要的现有 Run、Runtime、结果和制品引用方式；不接受第二派发链。
- 专题三 B：提供实际材料投递、ContextReceipt、宿主调用和加载证据；不替其决定资产版本治理。
- 专题四：提供 Run、Trace、Tool Activity、Result 和 Task Usage 原始事实；计量与评价消费这些事实。
- 专题五：展示 Multica 现有工作与执行对象，以及融合后的能力治理和评测信息；不新增状态权威。

## 9. 验收标准

1. 一个 Issue 通过 Multica 既有入口发起 Agent 执行，只有一个 Run、一个真实宿主执行单元。
2. SOP / Skill Driver 能驱动节点执行，但实际派发和进程生命周期仍由 Multica 管理。
3. 取消、超时、Daemon 重启和迟到回报沿用 Multica 原有机制，目标宿主的缺失回执明确呈现。
4. 同一 Session 服务多个 Run 时能正确归属；不能证明时不强行归属。
5. Hook、ACP、OTel、转录等多路观察不会造成重复 Run 或重复 Usage。
6. TeamAI 资产实际投递能关联 Multica ContextReceipt 和宿主调用。
7. 任一新增 Backend 或扩展均有源码、测试及目标版本真实回执证明其必要性。
