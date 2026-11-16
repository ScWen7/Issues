# D5 · 跨层写入、幂等与故障恢复取证

> 取证基准：AgentPlatform 设计分支 `design/system-architecture-convergence`；Multica 仓库基线 `fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc`。D5-2 的 `0f3e15f1d9dca781155e2fe475161f8c5e499b44` 是补充对照快照，逐项关系如下。
> 目的：核对 Issue 写入、评论触发、Main Bot 委派、Issue Wakeup、SOP 节点和 Run 执行链在超时、重复投递及进程中断时的真实行为。
> 边界：源码审阅，不把尚未验证的崩溃窗口标成已覆盖；本文是研究证据，产品规则以[核心协作一致性与并发控制模型](../architecture/core-consistency-concurrency.md)为准。

## 取证版本对照

下文主体取证链接沿用仓库基线 `fdfbfcd`；[业务触发与恢复闭环](d5-business-trigger-recovery.md)的源码链接固定到对照快照 `0f3e15f`。本节及 §6.3 并列两版链接供核对。本次以两版 Git 对象逐文件、逐相关函数核对，沿用关系如下；未据此替换仓库其他专题的取证基线。

| 核对范围 | 两版实际关系 | 本专题采用的结论与定位 |
|---|---|---|
| Issue 写入与派发 | `handler/issue.go` 有实际修改：同项目更新的处理及批量更新 dry-run / 逐项结果等已变化；单项更新仍先写 Issue、后计算与调用派发。`issue_trigger.go` 与 `queries/issue.sql` 全文件相同。 | [基线单项派发](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/issue.go#L4323-L4425) · [对照单项派发](https://github.com/multica-ai/multica/blob/0f3e15f1d9dca781155e2fe475161f8c5e499b44/server/internal/handler/issue.go#L4338-L4440)；修订号保护和派发分离结论分别保留。 |
| Issue Task 创建与来源字段 | `service/task.go` 有实际修改，包含直接聊天补充输入、终态处理和批量 Claim 缓存重查；Issue Task 创建函数及来源字段写入未变化。Migration 184 全文件相同。 | [基线创建字段](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/service/task.go#L1316-L1379) · [对照创建字段](https://github.com/multica-ai/multica/blob/0f3e15f1d9dca781155e2fe475161f8c5e499b44/server/internal/service/task.go#L1316-L1379)；来源引用仍只提供归因证据。 |
| 评论、目标触发与归并 | `handler/comment.go` 全文件相同。`queries/agent.sql` 有 CodeBuddy 恢复判据及旧查询移除等修改；评论归并 / planned-input SQL 内容未变化，行号前移。 | [共同的目标级处理](https://github.com/multica-ai/multica/blob/0f3e15f1d9dca781155e2fe475161f8c5e499b44/server/internal/handler/comment.go#L2080-L2195) · [基线 planned input](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/agent.sql#L1885-L1926) · [对照 planned input](https://github.com/multica-ai/multica/blob/0f3e15f1d9dca781155e2fe475161f8c5e499b44/server/pkg/db/queries/agent.sql#L1875-L1916)；评论提交后触发与不同 HEAD blocker 缺口保留。 |
| Wakeup 捕获与派发 | `service/issue_wakeup.go`、`queries/wakeup.sql`、Migration 518 / 520 / 530 及 `issue_wakeup_collaboration_test.go` 全文件相同。 | [基线派发事务](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/service/issue_wakeup.go#L1335-L1399) · [对照派发事务](https://github.com/multica-ai/multica/blob/0f3e15f1d9dca781155e2fe475161f8c5e499b44/server/internal/service/issue_wakeup.go#L1335-L1399)；事务捕获和 Receipt 合并按相同源码解释。 |
| Claim / reclaim 与中心 Start | `queries/agent.sql` 的 Claim、reclaim 和锁定 Start 查询未变化。`service/task.go` 的批量 Claim 新增强制重查信号；`StartTaskForClaim` 函数内容相同，行号后移。 | [基线 Start](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/service/task.go#L4511-L4558) · [对照 Start](https://github.com/multica-ai/multica/blob/0f3e15f1d9dca781155e2fe475161f8c5e499b44/server/internal/service/task.go#L4628-L4675)；同 claim 的中心 Start 重放保证保留，批量 Claim 实现按各版区分。 |
| 宿主实际启动 | `daemon.go` 有 Runtime 强制重查、项目归档与直接聊天补充输入等修改；两版均先请求中心 Start，再执行 Backend，成功后才记 runtime-started。`workdir_race_test.go` 全文件相同。 | 具体调用位置及既有失败路径测试见[中心 Start 与宿主实际启动](#63-中心-start-与宿主实际启动)。 |

## 1. 核心结论

Multica 已经提供若干可复用的可靠性机制，但它们不是一套自动覆盖所有业务入口的统一幂等协议：

- Issue 单项更新有 `expected_revision` 条件写入；这保护同一 Issue 的竞争修改，不等于把后续 Run 入队与 Issue 更新放进同一事务。
- 评论与随评提交的附件关联在同一事务内；评论保存后，Agent 触发和入队在事务外执行，并通过响应返回每个目标的派发结果。
- Issue 指派或状态变化先写 Issue、发布事件，再调用 Run 入队；当前 Handler 的直接 Agent 入队调用忽略返回错误。不能把“Issue 已更新”推断为“Run 已可靠创建”。
- 评论触发已有按 Issue / Agent 的待派唯一约束、并发冲突归并、待处理评论合并与回放机制；它仍存在源码明确标注的不同 HEAD 排队阻塞例外，尚无持久化 obligation 记录。
- Issue Wakeup 的订阅、事件回执、待处理输入、Wakeup Task 创建和回执消费具有较强的事务边界与重复事件去重；这是可复用的原生模式。
- Run 队列本身是持久化记录。领取使用状态与租约，响应丢失后可重新领取同一 Task；Start 按 claim generation 核对并支持同一 running Task 的请求重放。
- AgentPlatform 的 SOP Execution / Node Activation / Node Attempt 不是 Multica 原生对象。节点派发意图、结果消费回执和跨节点恢复必须由平台自身的流程权威记录落实，最终仍创建和使用 Multica 原生 Run。

因此，D5 的工作不是再发明 Run 或 Wakeup，而是把每个跨层入口的“权威写入、待执行意图、下游执行、结果消费”连成可对账的链条。

## 2. Issue 更新与 Run 入队不是一个原子动作

### 2.1 已覆盖的部分

单项 `PUT /api/issues/:id` 可携带 `expected_revision`。Handler 先检查读取到的修订号，SQL 在真正更新目标行时再次比较修订号；并发写入等待后，旧修订的请求不能覆盖新值。源码：

- [Issue Handler 的 expected_revision 检查](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/issue.go#L4058-L4068)
- [UpdateIssue SQL 的最终条件](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/issue.sql#L303-L316)

Issue 更新后，Handler 根据当前指派、状态和项目工作流判断是否需要触发 Agent，并在后续调用 `dispatchIssueRun`。该函数调用 TaskService 入队时忽略了返回错误。Issue 更新事件先于入队动作发布，二者不在同一事务中：

- [Issue 更新后计算触发并发布事件、再派发](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/issue.go#L4323-L4425)
- [dispatchIssueRun 的入队调用](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/issue_trigger.go#L80-L105)
- [TaskService 创建 Issue Run](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/service/task.go#L1281-L1390)

Task 入队本身会持久化 `agent_task_queue`，并通过 `(issue, agent)` 待派唯一约束处理并发重复；已存在待派项时返回 `ErrDuplicatePendingTask`。这是队列插入的并发保护，不是对原始 Issue 更新命令的通用幂等键。

### 2.2 已确认的缺口

若 Issue 指派 / 状态更新已提交，而进程在 Run 入队前退出，或入队因临时错误失败，Issue 仍保留新状态。该 Handler 没有在 Issue 更新事务中持久化一个可扫描的派发意图。重复提交同样的 Issue 字段也不必然重新触发派发，因为第二次请求可能已不再满足 `assigneeChanged` / `statusChanged`。

因此：

- Issue 的权威写入可以成功，而相应 Run 尚未创建。
- Issue 更新事件、工作流时间线中的“预计会运行”信息，不是 Run 已创建或已启动的证明。
- 当前实现不能仅依靠客户端重试保证补齐遗漏的 Run。

这不是要求把 Issue 与整个 Agent 运行做分布式事务；需要的是在 Issue 权威写入时一并留下可恢复的派发意图，或提供等价的持久化对账机制。

## 3. 评论、附件与 Agent 触发

### 3.1 已覆盖的部分

当评论同时提交附件时，Multica 在同一事务中创建评论、锁定并校验附件、建立附件关联。事务提交后评论与附件组合才对外可见：

- [评论与附件原子提交](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/comment.go#L1845-L1917)

评论提交后，Handler 才发布评论事件、处理线程自动解除，并调用 `triggerTasksForComment` 计算和入队 Agent 触发。触发结果通过评论响应中的 `TriggerOutcomes` 返回：

- [评论提交后执行 Agent 触发](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/comment.go#L1930-L2011)
- [触发结果与队列处理](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/comment.go#L2080-L2195)

评论 ID 是评论持久化后的稳定来源身份。相同 Issue / Agent 的并发待派通过唯一约束收敛；评论可以合并进现有 queued Task，或登记为待回放评论。归并逻辑要求只有在评论已被持久化合并、登记为计划输入、或确认可由现有 Run 接手时，才返回 queued / coalesced / deferred 等成功形态。

- [待派评论归并与边界说明](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/comment.go#L2102-L2137)
- [评论计划 ID 与 Task 的归并字段](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/agent.sql#L1807-L1954)

### 3.2 已确认的缺口

评论记录和 Agent 入队是两个提交边界。若评论事务提交后，服务进程在触发处理前退出，评论仍然存在，但没有证据表明对应 Agent 已收到任务。评论 API 没有把客户端请求身份作为评论创建的通用幂等键；客户端响应丢失后直接重发，可能创建另一条评论。

评论归并源码还明确保留一个 best-effort 例外：不同 HEAD 的 queued blocker 既不能接收旧评论，也不能覆盖新 HEAD 的任务；当前路径记录错误，但没有持久化 obligation 让系统保证未来补交。该边界不能被“已有评论回放”概括掉。

因此，评论的稳定来源 ID 应成为触发意图的幂等身份；评论触发需要可扫描的待处理状态，不能只依赖一次 Handler 调用完成后续入队。

## 4. Main Bot 委派与 Worker Run

Main Bot 的 Worker 委派复用 Issue 评论 / 提及、子 Issue 和 Multica Run，不创建第二套执行对象。对于同一 Issue 的 Worker 协助，委派评论是业务来源，实际 Task ID / Run 是执行身份。回唤注册需要指向具体 Task；Main Bot 不能仅凭“评论已保存”推断目标 Worker Run 已创建。

- [Main Bot 委派和源 Run 的恢复方法](mainbot-lifecycle-and-progress.md#82-普通-agent-的原生回唤)
- [Main Bot 对评论路由与在途协作的边界](mainbot-lifecycle-and-progress.md#83-普通-agent-协调对既有协作的影响)

平台应在委派记录中保留：稳定委派身份、目标 Agent、来源评论 / 子 Issue、预期输入输出、当前授权版本，以及最终对应的 Task ID。若评论触发被合并到已有 queued Task，委派应明确记录“由哪个既有 Task 覆盖”，而不是假造一个新 Run。无法确认目标 Task 时，保留待核对状态，不启动第二个 Worker 来掩盖不确定性。

## 5. Issue Wakeup：当前最完整的原生恢复样板

### 5.1 注册与事件回执

Issue Wakeup 在事务中锁定 Issue 和 Wakeup，保存订阅版本，并处理源 Task 已经终态的情况：如果注册时目标 Task 已是 completed / failed / cancelled，服务在同一事务写入 registration snapshot receipt。回执使用 `(wakeup_id, revision, event_key)` 唯一约束，重复事件不会生成多份待处理输入。

- [注册时捕获已终态 Task](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/service/issue_wakeup.go#L560-L660)
- [Wakeup receipt 的去重 SQL](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/wakeup.sql)

### 5.2 Receipt 到 Task 的事务交接

Scheduler 扫描未处理的 Wakeup receipt。派发时锁定 Issue / Wakeup，复核 Wakeup revision、启用状态、权限和目标 Agent。已有 queued Wakeup Task 可接收合并证据；dispatched Task 的输入已固定，新输入保留待处理，由原 Claim / prepare lease 恢复或后续交接。实际新建或合并 Task 的路径在同一事务中消费 receipts、更新 Wakeup 的 last task / fire count 等事实，提交后才广播和通知 Daemon。

- [dispatched 输入保留](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/service/issue_wakeup.go#L1150-L1169)
- [Wakeup Task 创建 / receipt 消费与提交](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/service/issue_wakeup.go#L1335-L1399)
- [Wakeup 任务创建、消费和扫描 SQL](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/wakeup.sql)

这条路径具备 D5 需要的几个关键性质：输入先持久化、事件去重、目标版本固定、待处理输入可扫描、创建执行与消费输入原子提交、权限在领取前再次核验。

### 5.3 已核实：源事实与 Receipt 在同一数据库事务内捕获

进一步检查固定版本迁移源码后，前一版“Task 终态到 Receipt 的事件捕获仍待核实”需要修正。Multica 不依赖 Task 完成 Handler 在提交后再发布一个内存事件来驱动 Wakeup；它通过数据库触发器，在源记录写入的同一事务内生成匹配的 Wakeup Receipt。

- [迁移 518：Task 终态、评论创建与 Issue 状态捕获](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/migrations/518_wakeup_event_capture.up.sql)
- [迁移 520：扩展 Task 状态、评论生命周期、Issue 变更、Reaction、Attachment 的事务捕获](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/migrations/520_collaboration_wakeup_events.up.sql)
- [迁移 530：同一事件类型的未处理 Receipt 合并、事件去重和容量保护](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/migrations/530_wakeup_bounded_capture.up.sql)
- [事务回滚、真实写入覆盖和身份隔离测试](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/service/issue_wakeup_collaboration_test.go)

这带来一个重要结论：**对于 Multica 明确列入 WakeupTypes 的事实，源写入事务提交即意味着匹配订阅的 Receipt 已一并提交；源事务回滚则 Receipt 一并回滚。** 这覆盖 HTTP Handler、后台任务以及直接数据库写入等非单一入口，不依赖某个 Handler 成功运行到最后一步。

迁移 520 的 `capture_issue_wakeup` 会把事件 ID、事件类型、发生时间、Workspace / Issue、来源 Task、Agent 和 Actor 写入 Receipt，并且只存引用与变更字段，不复制评论正文、附件 URL 或任意元数据值。迁移 530 对同一 Wakeup revision 下相同 event type 的待处理输入做合并，保留 coalesced_count、首次发生时间和最新来源；同一源事件通过稳定 event key 去重。该 Receipt 是待处理协作输入，不是永久事件档案。

因此，Wakeup 这条链的核心捕获窗口已经闭合：源写入与 Receipt 同事务，后续 scheduler 只负责消费持久化 Receipt。剩余核验点不再是“是否漏捕获”，而是**消费、保留和下游 Run 的边界**：
- 同一类型的多条输入可合并为一个 Receipt，因此它适合触发 Agent 重新读取当前状态，不适合承载必须逐条处理的业务命令或精确事件历史。
- Receipt 只在规则有效、Issue 未关闭、事件类型匹配且过滤器匹配时捕获；规则创建之前的历史状态不会自动补发，只有精确 Task 订阅的注册时终态快照会接住已终态源 Task。
- 事件 Receipt 有保留与清理策略，已处理输入可以清理；不能把 Wakeup Receipt 当作长期审计记录。
- Scheduler 消费 Receipt 后，会在同一事务创建 / 复用 Task 并标记输入已消费；但仍须单独核对 Run 的实际启动和目标 Agent 是否真正处理了输入。

## 6. Run 队列、领取与 Start

### 6.1 持久化 Task 与并发领取

Issue Run 入队后成为持久化 `agent_task_queue` 记录。Daemon 通过原生 Claim 领取，Task 状态变为 dispatched，写入 `dispatched_at` 和 prepare lease。Claim 的唯一 Task ID 不因 HTTP 通知丢失而改变。

- [ClaimAgentTask 的原子领取与同 Issue / Agent 串行](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/agent.sql#L770-L850)
- [过期 dispatched Task 重新投递同一 Task](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/agent.sql#L850-L960)

### 6.2 Claim generation 与 Start replay

Claim response 可能已在中心提交但未抵达 Daemon。Multica 在租约 / 恢复窗口过后重新投递同一 Task，并刷新 `dispatched_at` 作为新 claim generation。Start 时，Daemon 必须携带 Task ID、Runtime ID 和该次 `dispatched_at`；服务端锁定并核对三者。旧 claim 不能启动新 claim。若同一 claim 的 Start 响应丢失，而 Task 已是 running，重放会返回现有 Task，不重复执行 Start 副作用。

- [LockAgentTaskStartClaim](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/agent.sql#L985-L1030)
- [StartTaskForClaim 的锁定、重放和事务提交](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/service/task.go#L4511-L4558)

### 6.3 中心 Start 与宿主实际启动

中心接受 `StartTaskForClaim` 后，会把原生 Task 转为 `running` 并返回 Start 回执；Daemon 随后继续准备启动宿主。两版都在 `backend.Execute` 成功返回会话后才记录 `taskPhaseRuntimeStarted`。因此，中心 `running` / Start 回执与宿主启动是两个观察边界，产品的 Running 按后者取证。

| 固定版本 | 中心 Start 与启动中进度 | 宿主执行与启动标记 | 既有失败路径测试 |
|---|---|---|---|
| `fdfbfcd` | [StartTask → Launching](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/daemon.go#L8768-L8784) | [Backend.Execute → runtime-started](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/daemon.go#L9967-L9984) | [缺失二进制仍先经过 StartTask](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/workdir_race_test.go#L120-L123) |
| `0f3e15f` | [StartTask → Launching](https://github.com/multica-ai/multica/blob/0f3e15f1d9dca781155e2fe475161f8c5e499b44/server/internal/daemon/daemon.go#L8929-L8945) | [Backend.Execute → runtime-started](https://github.com/multica-ai/multica/blob/0f3e15f1d9dca781155e2fe475161f8c5e499b44/server/internal/daemon/daemon.go#L10128-L10145) | [缺失二进制仍先经过 StartTask](https://github.com/multica-ai/multica/blob/0f3e15f1d9dca781155e2fe475161f8c5e499b44/server/internal/daemon/workdir_race_test.go#L120-L123) |

上述既有测试以不存在的宿主二进制走过 Prepare → StartTask → ReportProgress，随后在实际启动时报错，直接说明 Start 成功后仍可启动失败。本次核对源码与测试定义，未重跑该测试。只有中心回执时，工作台显示“启动中”；宿主启动缺少回执时保留待确认，启动失败记录实际失败及原因。

### 6.4 对外执行结果

Run 的终态必须由原 Task 记录承载。技术重试、人工重跑和业务返工保留各自的原生关系；不能因通知重发而创建新的业务执行。终态之后的通知、Wakeup、SOP 消费和工作台刷新是下游动作，分别核对其权威来源与消费状态。Task 终态已写入但下游没有回执时，不能将 Run 改回 running，也不能直接再执行一遍；应查原 Task、下游待处理输入和已有消费记录。

## 7. SOP 节点：平台必须补齐的恢复语义

SOP Execution、Node Activation、Node Attempt 是 AgentPlatform 的业务流程对象，不是 Multica 的原生 Task / Run 状态别名。节点状态变为 Ready 后，若派发前进程退出，平台必须能重新发现“该激活尚未获得有效 Run”；若 Run 已创建但派发通知丢失，平台应查回原 Run；若 Run 已终态但节点未消费，平台应重放消费，而不是重跑生产。

建议的身份关系：

- 派发意图：`SOP Execution + Node Activation + Node Attempt + target executor + contract revision`。
- 实际执行：引用唯一的 Multica Task / Run ID。
- 结果消费：`Node Activation + Run ID + Candidate / Artifact version`。
- 同一意图重送：返回原 Run 或已证明覆盖它的现有 Run。
- 新 Attempt：只有业务修正、输入候选替换、授权代际变化或明确的新履行才创建；HTTP 超时不是新 Attempt 的理由。

不得为了 SOP 恢复再建一套 Agent 队列、Run 或 Runtime。

## 8. Wakeup 能承担什么，不能承担什么

Migration 518 / 520 / 530 证明了 Wakeup 的事件捕获和消费模型，但不能因此把它提升成所有跨层命令的通用总线。

### 8.1 适合：让协调者因事实变化重新读取当前状态

适合的场景：
- Issue 的状态、负责人、范围或属性发生变化，Main Bot 需要重新判断下一步；
- Worker Run 完成、失败或取消，Main Bot 需要消费结果；
- 评论、回复或交付发生变化，协调者需要重新读取 Issue 的讨论和交付；
- 多个快速连续变化可以合并，Agent 只需读取最新权威状态；
- 同一事实可能从不同 Handler、后台任务或直接数据库写入产生，必须在源事务内可靠捕获。

这与 Main Bot 的短 Turn 模型相容：Wakeup 负责让协调者有机会恢复；新 Turn 再读取 Issue、Run、Artifact 和授权的当前事实，而不是把一份事件 payload 当作完整工作上下文。

### 8.2 不适合：每条都必须独立履行的业务命令

以下场景不能只依赖 Wakeup：
- 每条评论都代表一个独立且不可丢失的委派命令；
- 每个 SOP 节点激活必须精确对应一个独立 Attempt；
- 每次候选版本变化都必须分别完成核验；
- 需要按原始顺序处理、且不能合并的外部副作用；
- 需要永久审计的完整事件历史。

原因是 Migration 530 对同一 Wakeup revision 下同一 event type 的待处理 Receipt 做合并。它会更新 Receipt 身份和 payload，保留合并数量、首次时间和最新来源，而不会把每条原始事实都保留为独立待处理命令。已处理 Receipt 也允许清理。

### 8.3 对 AgentPlatform 的使用边界

| 工作需求 | 是否可直接依赖 Wakeup | 必须额外保留什么 |
|---|---|---|
| Main Bot 需要知道 Issue 有变化 | 可以 | 重新读取 Issue 当前版本和未决工作 |
| Main Bot 等待 Worker 终态 | 可以，优先订阅精确 Task ID | 原委派身份、实际 Task ID、结果消费记录 |
| 评论触发 Main Bot 重新读取讨论 | 可以 | 评论本身和可分页读取的原始讨论记录 |
| 一次 @Worker 要求一个独立交付 | 不能只依赖 | 委派记录、目标 Agent、输出要求、实际 Task ID 或被复用 Task 的证明 |
| SOP Node Activation 启动一个 Attempt | 不能只依赖 | Node Activation / Attempt 与唯一 Task ID 的绑定 |
| 每个 Candidate 版本都要有独立检查结果 | 不能只依赖 | Candidate 版本、检查输入和结果记录 |
| 审计所有业务变更 | 不可以 | 对应权威对象的版本和审计记录 |

**设计结论：Wakeup 是协调者的可靠唤醒入口；委派、SOP 激活和结果消费仍然必须有自己的权威业务身份。** 不为此复制 Run 队列，也不把 Wakeup Receipt 当作业务对象。

### 8.4 对持续委托 Main Bot 的具体含义

1. Main Bot 获得持续协调授权后，必须有可恢复的后续唤醒来源；它不能依赖当前 Session 一直在线。
2. Main Bot 可以在当前 Turn 内登记精确 Worker Task 的终态 Wakeup；注册与源 Task 终态快照之间的竞态由 Multica 原生事务处理。
3. Issue / Comment 的状态变化可用于唤醒 Main Bot，但合并后的 Receipt 只表示“有变化需要检查”，Main Bot 必须重新读取当前权威数据。
4. 一次性 @Worker 的委派身份和结果不能只存在 Wakeup 中；Main Bot 必须能从原 Issue 找回这次委派及其实际执行结果。
5. Main Bot 自身 Runtime 断联时，Issue、Wakeup 和 Worker Run 仍然存在。恢复后重新读取，不恢复旧 Session 的内存计划。

## 9. D5 后续验证问题

1. Wakeup 的 Receipt 已证明与源事实同事务。下一步核对其消费时的并发竞争、Receipt 合并后是否满足具体工作流的逐条处理语义，以及已消费 Receipt 的保留期是否满足审计需要。
2. Issue 更新后的 Run 入队是否有可用的原生待办扫描或对账入口？如何在不重复 Run 的情况下补齐？
3. 评论创建后的触发是否能按 comment ID 补扫？不同 HEAD queued blocker 的 obligation 是否会在后续状态变化中自动恢复？
4. Issue / Comment / Worker 委派入口是否能为调用者提供稳定 operation ID 和可查回的原结果？
5. SOP Node Activation 到 Multica Task 的绑定，如何复用 Task 唯一约束与原生 Run 谱系，避免重复执行和错误合并？
6. 取消、撤权、接管与迟到结果之间，所有写入点是否都核对当前授权代际？
