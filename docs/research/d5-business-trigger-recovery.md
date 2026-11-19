# D5-2 · 业务触发与恢复闭环

> 研究范围：Main Bot 首次激活、评论 / Worker 委派、SOP 节点派发与结果消费。
> Multica 仓库基线：`fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc`；本文补充核对快照为 `0f3e15f1d9dca781155e2fe475161f8c5e499b44`，源码链接固定到该快照。逐文件差异和结论沿用关系见[取证版本对照](d5-write-recovery-evidence.md#取证版本对照)。
> 研究目标：确定业务动作已经生效、后续 Run 未创建或回执丢失时，如何恢复原意图而不创建重复执行。
> 边界：产品和跨层契约研究，不决定数据库表、API 或部署实现。

## 1. 本阶段结论

三个场景不能用同一个“重试 Run”解决，因为它们的权威业务来源不同：

| 场景 | 业务意图的权威来源 | 执行身份 | 可复用的原生机制 | 平台仍需补齐 |
|---|---|---|---|---|
| Main Bot 首次激活 | Issue 当前指派 + 有效 Work Agreement / 授权代际 | 首次协调 Turn 对应的 Multica Task / Run | Task 持久化、同 Issue / Agent 待派唯一约束、Claim reclaim | Issue 写入与首次 Task 入队分离；入队错误被忽略；没有已确认的首次激活派发待办 |
| 评论 / Worker 委派 | 已保存的具体 Comment + 本次目标 Agent / 授权 | Task 的 trigger_comment_id / coalesced_comment_ids，及后续 Run | 评论与附件原子提交、同 Issue / Agent 待派归并、planned comment、完成时评论 reconcile、Wakeup 事务捕获 | 评论写入与显式 @Agent 入队分离；Handler 在触发前退出时，不能保证每个 Worker 目标都被创建或记录为阻塞 |
| SOP 节点 | SOP Execution + Node Activation + Node Attempt + 固定输入 / 契约 | 明确绑定的 Multica Task / Run ID | 原生 Task 队列、Claim generation、Start replay、终态记录 | Node Attempt 到 Task 的稳定绑定、派发意图查回、结果消费回执及节点恢复由平台负责 |

统一原则：**先保存业务意图，再把它绑定到一个实际 Task；执行通知与回执丢失时，查回原 Task；只有明确的新业务履行才产生新 Run。** 这里不新增第二套任务队列，也不把 Wakeup 当作业务委派记录。

## 2. Main Bot 首次激活：Issue 已指派，不等于协调 Turn 已建立

### 2.1 固定版 Multica 的真实路径

Issue 更新 Handler 在权威写入成功后，计算 `assigneeChanged`、`statusChanged` 和 Project Workflow handoff，调用统一的 `WillEnqueueRun` 判断。若需要启动 Agent，之后调用 `dispatchIssueRun`。

- [Issue 更新后的触发判断和派发调用](https://github.com/multica-ai/multica/blob/0f3e15f1d9dca781155e2fe475161f8c5e499b44/server/internal/handler/issue.go#L4338-L4440)
- [dispatchIssueRun](https://github.com/multica-ai/multica/blob/0f3e15f1d9dca781155e2fe475161f8c5e499b44/server/internal/handler/issue_trigger.go#L65-L105)
- [EnqueueTaskForIssue / enqueueIssueTask](https://github.com/multica-ai/multica/blob/0f3e15f1d9dca781155e2fe475161f8c5e499b44/server/internal/service/task.go#L1281-L1390)

关键事实：
- Issue 写入完成后才进行 Run 入队，两者不是同一事务。
- `dispatchIssueRun` 的 Agent 分支忽略 `EnqueueTaskForIssueWithHandoff` 的返回错误。
- Issue 的第二次普通更新如果没有再次改变 Assignee / Status，不会自然重放首次触发条件。
- 同 Issue / Agent 的待派 Task 唯一约束可以避免并发重复待派，但它不保证 Issue 写入后一定成功创建 Task。
- 已创建的 Task 是持久化队列事实；Daemon Claim 响应丢失可通过 reclaim 重新投递同一 Task。这个恢复只覆盖 Task 已创建之后。

因此存在一个明确断点：**Issue 指派已经生效，服务进程或入队调用在 Task 持久化之前失败，Issue 仍指向 Main Bot，但没有首次协调 Run。** 不能把 UI 显示“已指派”或 Issue 更新事件当作 Main Bot 已开工。

### 2.2 AgentPlatform 应如何表达

- Issue 当前 Assignee 和 Work Agreement / Delegation Contract 是持续协调授权的唯一业务权威；Main Bot 不拥有独立的 Issue 副本。
- 指派生效时，必须有一个可恢复的“首次协调激活意图”，与本次有效指派 / 授权代际绑定。它是派发待办，不是新 Task、Run 或第二个协调者。
- 激活意图至少能识别 Issue、目标 Agent、授权 / 工作约定版本、发起来源，以及该次首次协调请求是否已关联实际 Task。
- 入队成功后保存实际 Task ID；若 Task 已存在且确实覆盖同一首次激活，绑定已有 Task，不再创建第二个。
- 若服务在 Task 创建后、绑定 Task ID 前中断，恢复者必须按稳定激活身份查回原 Task。若无法证明哪一个 Task 对应本次激活，状态保持 unknown 并对账，不能通过再 enqueue 一个 Task 来掩盖不确定性。
- 若 Runtime 离线但 Task 已创建，沿 Multica 的持久化队列和 reclaim 等待原 Task；若 Runtime 尚未可用、授权失败或 Agent 不可执行，保留明确 blocked 原因，不伪装成 running。
- 改派、撤权、Issue 关闭或 Work Agreement 变化后，旧激活不能再创建新的协调 Turn。旧 Run 的终态和交付仍归原激活，是否消费由当前负责人判断。

### 2.3 首次激活的恢复矩阵

| 故障点 | 权威事实 | 恢复动作 |
|---|---|---|
| Issue 指派写入未提交 | 原 Assignee / 授权仍有效 | 原命令可按版本重试 |
| Issue 已提交，Task 尚未创建 | 新 Assignee 已生效，首次激活待派 | 扫描 / 查回该激活待办，按当前授权补派 |
| Task 已创建，绑定回执丢失 | Task 已存在，激活关联未知 | 按稳定激活身份查回并绑定原 Task |
| Task 已创建，Runtime 离线 | Run 已排队，未启动 | 等待原 Runtime 或有权改绑；不创建新 Run |
| 旧激活派发时已被撤权 / 改派 | 原意图已失效 | 标记 superseded / cancelled，不再派发 |
| Run 已启动，Main Bot Runtime 断联 | 原 Run 仍可能执行 | 其他协作继续；恢复后读取原 Issue、Worker 和结果，不依赖旧 Session 内存计划 |

## 3. 评论 / Worker 委派：评论是来源，不等于每个目标都已接单

### 3.1 固定版 Multica 的真实路径

评论及其附件在同一事务内创建和关联。事务提交后 Handler 发布评论事件，再调用 `triggerTasksForComment`，逐个解析并派发目标 Agent。

- [评论事务提交后的触发路径](https://github.com/multica-ai/multica/blob/0f3e15f1d9dca781155e2fe475161f8c5e499b44/server/internal/handler/comment.go#L1845-L1955)
- [triggerTasksForComment / enqueueCommentAgentTriggers](https://github.com/multica-ai/multica/blob/0f3e15f1d9dca781155e2fe475161f8c5e499b44/server/internal/handler/comment.go#L1991-L2099)
- [评论与 Agent 触发归并逻辑](https://github.com/multica-ai/multica/blob/0f3e15f1d9dca781155e2fe475161f8c5e499b44/server/internal/handler/comment.go#L2102-L2195)

已经具备的能力比简单的“评论后 enqueue”更完整：
- 评论 ID 是稳定来源身份；Task 使用 `trigger_comment_id` 和 `coalesced_comment_ids` 引用其触发输入。
- 同 Issue / Agent 的 queued Task 可按 review HEAD 合并评论；并发插入输掉唯一约束时会重新查找并归并。
- 对已领取 / 运行中的 Task，可以登记 planned comment；Task 完成时再 reconcile 未交付评论。
- 仅当评论已被持久化合并、登记为 planned input 或新建 Task 时，才返回 queued / coalesced / deferred 等成功形态。
- 不同 HEAD 的 queued blocker 既不能合并也不能接收旧 HEAD 评论；源码明确说明这一种情况仍缺 durable obligation record，当前只报告真实非成功，不虚报 deferred。
- Wakeup 的数据库触发器可在评论创建事务内捕获 `comment.created`，但前提是当时已有匹配且有效的订阅。它能可靠唤醒订阅者重新读取评论，不会自动为评论中每个 @Worker 创建委派 Task。

### 3.2 仍存在的故障窗口

评论已保存，但 Handler 在 `triggerTasksForComment` 之前退出：
- 评论及附件存在；
- 每个显式目标的 TriggerOutcome 还未计算或返回；
- 不能保证 Worker Task 已创建、planned comment 已登记或阻塞原因已持久化；
- 如果 Main Bot 有有效的 comment Wakeup 订阅，它可以被唤醒并重新读取评论，但 Wakeup 不保存每个 Worker 目标的委派完成状态；
- 如果没有有效订阅，也没有仍在运行的 Task 能在完成时 reconcile 这条评论，则不能声称原生机制必然补齐该次触发。

### 3.3 AgentPlatform 应如何表达

一次 @Worker 是一项具体委派，不是持续 Main Bot 授权。它的业务来源是原 Comment；目标是解析出的 Agent；实际执行仍是 Multica Task / Run。

- 同一 Comment 对同一目标 Agent 的委派必须有稳定身份，可用 Comment ID + Target Agent ID + 触发类型 / 目标解析版本识别。
- 委派状态要能区分：待处理、已关联新 Task、已由既有 Task 覆盖、已登记为计划输入、被阻塞、已撤销、结果待消费、已消费。
- 已关联 Task 后记录实际 Task ID；若归并到现有 Task，记录覆盖依据（同一 Issue、Agent、review HEAD、输入与授权范围兼容），不能伪造一个新 Run。
- Handler 响应丢失或触发处理进程退出时，恢复者从 Comment 重新解析当前有效目标和权限，再查回该委派身份；只补尚未解决的目标。
- 权限撤销、Agent 归档、Runtime 变化或 Issue 改派后，必须按当前授权重新判断；不能把历史评论视为永久授权。
- 不同 HEAD blocker 的未覆盖委派必须保留为待处理或明确阻塞，并在 blocker 变化时可恢复；不能静默丢弃，也不能将旧 HEAD 评论并入新 HEAD Run。
- Main Bot 的 Wakeup 只负责提醒它重新读取 Issue 和委派状态；Worker 委派本身仍有独立身份及 Task 绑定。

### 3.4 评论委派的恢复矩阵

| 故障点 | 权威事实 | 恢复动作 |
|---|---|---|
| 评论未提交 | 没有评论来源 | 可以重试创建 |
| 评论已提交，触发尚未开始 | Comment 已存在，目标委派待核对 | 按 Comment ID 扫描 / 恢复目标委派，不重发评论 |
| 某些目标已 enqueue，另一些目标未处理 | 每个目标结果不同 | 逐目标查回 Task / planned input，只补未解决目标 |
| enqueue 已成功但响应丢失 | Task 可能已存在 | 按委派身份与来源 Comment 查回 Task |
| 已有同 HEAD queued Task | 既有 Task 可覆盖新评论 | 原子合并并绑定既有 Task |
| 只有不同 HEAD blocker | 当前无法安全覆盖 | 保留 blocked / pending obligation，等待 blocker 变化后再判断 |
| Worker 已终态，Main Bot 未消费 | 原 Run 终态事实存在 | 重新读取原 Task 和交付，重放消费，不重跑 Worker |

## 4. SOP 节点：Node Activation 是业务身份，Run 是执行身份

### 4.1 已有的 AgentPlatform 对象足够承载业务状态

当前核心对象模型已经定义：
- SOP Execution：一次调用某个 SOP 发布版本的流程实例；
- Node Activation：节点在固定工作约定、输入和授权下的一次有效进入；
- Node Attempt：该激活中的具体履行、修正或检查尝试，可关联一个或多个 Run。

因此不再引入 SOP Task、节点队列或新的 Runtime。需要补的是 Node Attempt 与实际 Run 之间的持久化派发关系，以及结果消费回执。

LoopForge 的经验也说明 Definition、Run、NodeRun、Artifact、Evaluation 是不同事实；Run 快照固定流程版本，节点依赖决定 Ready，结果消费后才推进下游。参见[LoopForge SOP 生命周期研究](loopforge-sop-lifecycle.md)。

### 4.2 节点派发契约

一次 Agent 节点派发必须由已存在的 Node Activation / Node Attempt 固定：
- 调用 Issue、SOP Execution 和节点定义版本；
- 当前 Activation / Attempt 身份；
- 固定的 Work Agreement、输入 Candidate / Artifact 版本；
- 目标 Agent、允许使用的 Runtime 范围和当前授权代际；
- 执行契约、必需输出和验收 / 消费条件。

派发处理：
1. Node Attempt 进入可派发状态时，先留下可恢复的派发意图。
2. 调用 Multica 原生 Issue / Task 派发入口；不创建平台自己的 Run。
3. Task 创建后将真实 Task ID 绑定回原 Node Attempt。
4. 如果 Task 已创建但绑定回执丢失，按稳定派发身份查回 Task 并补绑定。
5. 同一派发身份的重复请求必须回到原 Task；若底座无法按身份查回，则保持 unknown 并先对账，不能直接创建第二个。
6. Task 已排队但 Runtime 离线时，节点等待执行。中心 Start 回执确认原 claim 的状态转换，此后仍在启动宿主；取得对应 Backend / 宿主启动回执后，才确认实际开工。中心 Task 的原生 `running` 保留其本来含义，产品按已取得的启动证据呈现。两版调用位置及既有启动失败测试见[中心 Start 与宿主实际启动](d5-write-recovery-evidence.md#63-中心-start-与宿主实际启动)。

一个 Node Attempt 可引用多个 Run，但每次实际 Run 调用必须有独立、可查回的派发身份；不能只用 Node Activation ID 把不同执行调用误合并。

### 4.3 结果消费契约

Run 终态只是生产完成。节点推进还需要：
- 查回原 Task / Run 的终态和实际结果；
- 验证结果归属当前 Node Activation / Attempt；
- 固定实际 Candidate / Artifact 版本及来源；
- 核对必需产物、检查证据、缺项和失败原因；
- 在节点结果消费记录中绑定 Run ID 与结果版本；
- 只有消费记录提交后，才重新计算后继节点的 Ready 条件。

若 Run 已终态但消费中断，重放消费；不能重跑生产。若节点已被新候选、新授权或新 Activation 取代，旧 Run 结果归回旧 Attempt，只能作为历史证据，不能推进当前节点。

### 4.4 节点恢复矩阵

| 故障点 | 恢复动作 |
|---|---|
| Node Attempt 已就绪，派发请求未发送 | 重新读取当前 Activation / Attempt，补发同一派发意图 |
| Task 已创建，Node Attempt 未绑定 Task ID | 按稳定派发身份查回原 Task，补绑定 |
| Task 已排队，Runtime 未上线 | 等待原 Task 被领取，或经授权改绑；不创建新 Task |
| Claim / Start 响应丢失 | 沿 Multica 原 Task ID 与 claim generation 重放 |
| Run 已终态，Node Attempt 未消费 | 查回原终态和制品，重放消费 |
| 消费已完成，通知 / 下游调度未发生 | 从 Node Attempt 当前状态重新计算 Ready；幂等安排后继 |
| 输入 Candidate / 授权已变化 | 旧 Attempt 不再推进新激活；创建新的业务激活 / Attempt，明确继承哪些旧结果 |
| 撤权 / 取消与迟到回报竞争 | 保留旧 Run 事实，按当前授权代际拒绝旧回报改变当前流程 |

## 5. 三个场景的统一恢复模型

三者共用同一组边界，但不共享同一种业务身份：

| 边界 | Main Bot 首次激活 | Worker 委派 | SOP 节点 |
|---|---|---|---|
| 意图来源 | Issue 当前指派 / 授权代际 | Comment + 目标 Agent | Node Activation / Attempt |
| 意图生效 | Issue 指派已提交 | Comment 已提交且目标解析有效 | Node Attempt 已就绪且授权有效 |
| 执行绑定 | 首次协调 Task ID | Worker Task ID 或被复用 Task ID | Node Attempt ↔ Task ID |
| 中心 Start 已确认 | 原 Task / claim 的 Start 回执 | 原 Task / claim 的 Start 回执 | 原 Task / claim 的 Start 回执 |
| 实际启动 | 原 Task 对应的 Backend / 宿主启动回执 | 原 Task 对应的 Backend / 宿主启动回执 | 原 Task 对应的 Backend / 宿主启动回执 |
| 结果来源 | Main Bot Run / 后续委派结果 | Worker Run / Candidate | 节点所引用的一个或多个 Run |
| 结果消费 | Main Bot 读取当前 Issue 和交付 | Main Bot / Issue 接收该次委派结果 | Node Attempt 结果消费记录 |
| 新一轮条件 | 新的指派 / 授权代际 | 新评论或明确新委派 | 新 Activation / Attempt |

恢复的共同顺序：
1. 读取权威业务对象，确认原意图仍有效。
2. 查询该意图已关联的 Task / Run 和已有消费记录。
3. 如果已有 Task，恢复绑定或投递同一 Task。
4. 如果尚无 Task，且能证明未创建，才按原身份创建。
5. 如果无法证明是否创建，标记 unknown 并对账。
6. Run 终态后重放结果消费，不重跑生产。
7. 每次补派、领取、启动和消费都重新核对当前授权与版本。

## 6. 本阶段仍需保留的底座缺口

1. Issue 指派写入与首次 Agent Task 入队不在同一事务；Agent 入队错误未被当前 Handler 作为业务失败处理。AgentPlatform 需要持久化首次激活意图和恢复入口。
2. Comment 写入与每个目标 Agent 的触发入队分离。评论本身是可重读来源，但尚不能保证 Handler 中断后所有显式 Worker 委派都有可扫描的目标级状态。
3. 评论处理对同 HEAD queued / active Task 有较成熟的合并与 planned-comment 机制；不同 HEAD queued blocker 仍是明确例外，需要平台持久化待处理义务或在 blocker 变化时可靠恢复。
4. Multica 原生 Task 有持久化队列、Claim reclaim 和 Start replay；但当前研究未证明它为所有外部业务意图提供通用幂等键 / 按来源意图查回接口。
5. SOP Node Activation / Attempt 是 AgentPlatform 侧对象，Multica 不知道它们的业务身份；Task 与节点的绑定和结果消费必须由平台维护。
6. Wakeup 事件捕获可靠，但其 Receipt 可以合并同类变化。它适合唤醒 Main Bot 重新读取事实，不适合替代目标级 Worker 委派、Node Attempt 或审计记录。

## 7. 下一步需要收敛的实现前置问题

本阶段不决定实现方案，但进入技术设计前必须回答：
- 如何让 Issue 首次指派与协调激活意图可恢复，而不把 Run 状态复制到 Issue？
- Multica Task 如何携带或关联稳定的外部派发身份，使 Task 创建成功但平台绑定回执丢失时可查回？
- 评论目标解析结果、每目标委派状态和 Task 关联放在哪里，才能支持逐目标恢复及不同 HEAD blocker 的后续接续？
- Node Attempt 与多个 Run 的关联如何表达，怎样区分技术重试、人工重跑和新的业务尝试？
- 结果消费记录如何成为节点推进的唯一依据，并防止迟到 Run 推进新激活？
