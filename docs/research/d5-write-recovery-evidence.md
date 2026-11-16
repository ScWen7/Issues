# D5 · 跨层写入、幂等与故障恢复取证

> 取证基准：AgentPlatform 设计分支 `design/system-architecture-convergence`；Multica 固定提交 `fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc`。
> 目的：核对 Issue 写入、评论触发、Main Bot 委派、Issue Wakeup、SOP 节点和 Run 执行链在超时、重复投递及进程中断时的真实行为。
> 边界：源码审阅，不把尚未验证的崩溃窗口标成已覆盖；本文是研究证据，产品规则以[核心协作一致性与并发控制模型](../architecture/core-consistency-concurrency.md)为准。

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

- [Issue Handler 的 expected_revision 检查](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/issue.go#L4053-L4068)
- [UpdateIssue SQL 的最终条件](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/issue.sql#L303-L316)

Issue 更新后，Handler 根据当前指派、状态和项目工作流判断是否需要触发 Agent，并在后续调用 `dispatchIssueRun`。该函数调用 TaskService 入队时忽略了返回错误。Issue 更新事件先于入队动作发布，二者不在同一事务中：

- [Issue 更新后计算触发并发布事件、再派发](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/issue.go#L4310-L4510)
- [dispatchIssueRun 的入队调用](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/issue_trigger.go#L80-L105)
- [TaskService 创建 Issue Run](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/service/task.go#L1150-L1390)

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

- [评论提交后执行 Agent 触发](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/comment.go#L1930-L2055)
- [触发结果与队列处理](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/comment.go#L2055-L2190)

评论 ID 是评论持久化后的稳定来源身份。相同 Issue / Agent 的并发待派通过唯一约束收敛；评论可以合并进现有 queued Task，或登记为待回放评论。归并逻辑要求只有在评论已被持久化合并、登记为计划输入、或确认可由现有 Run 接手时，才返回 queued / coalesced / deferred 等成功形态。

- [待派评论归并与边界说明](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/comment.go#L2180-L2320)
- [评论计划 ID 与 Task 的归并字段](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/agent.sql)

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

Scheduler 扫描未处理的 Wakeup receipt。派发时锁定 Issue / Wakeup，复核 Wakeup revision、启用状态、权限和目标 Agent。若已有合适的 queued / dispatched Task，可将证据合并到该 Task；否则创建新的 Wakeup Task。随后在同一事务中消费 receipts、更新 Wakeup 的 last task / fire count 等事实。事务提交后才广播和通知 Daemon。

- [Wakeup dispatch 与 Task 创建 / receipt 消费](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/service/issue_wakeup.go#L900-L1130)
- [Wakeup 任务创建、消费和扫描 SQL](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/wakeup.sql)

这条路径具备 D5 需要的几个关键性质：输入先持久化、事件去重、目标版本固定、待处理输入可扫描、创建执行与消费输入原子提交、权限在领取前再次核验。

### 5.3 仍需核对的边界

注册时的 terminal snapshot 能关闭“先完成、后登记”的竞态；它本身不证明所有运行中的 Task 终态事件都具有事务外通知丢失后的持久重放。需要进一步核对 Task terminal commit 到 Wakeup receipt 写入之间的故障窗口，以及 scheduler 是否存在基于终态源记录的补扫。未取得该证据前，不将其标为完全 crash-safe。

## 6. Run 队列、领取与 Start

### 6.1 持久化 Task 与并发领取

Issue Run 入队后成为持久化 `agent_task_queue` 记录。Daemon 通过原生 Claim 领取，Task 状态变为 dispatched，写入 `dispatched_at` 和 prepare lease。Claim 的唯一 Task ID 不因 HTTP 通知丢失而改变。

- [ClaimAgentTask 的原子领取与同 Issue / Agent 串行](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/agent.sql#L770-L850)
- [过期 dispatched Task 重新投递同一 Task](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/agent.sql#L850-L960)

### 6.2 Claim generation 与 Start replay

Claim response 可能已在中心提交但未抵达 Daemon。Multica 在租约 / 恢复窗口过后重新投递同一 Task，并刷新 `dispatched_at` 作为新 claim generation。Start 时，Daemon 必须携带 Task ID、Runtime ID 和该次 `dispatched_at`；服务端锁定并核对三者。旧 claim 不能启动新 claim。若同一 claim 的 Start 响应丢失，而 Task 已是 running，重放会返回现有 Task，不重复执行 Start 副作用。

- [LockAgentTaskStartClaim](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/agent.sql#L985-L1030)
- [StartTaskForClaim 的锁定、重放和事务提交](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/service/task.go#L4500-L4560)

### 6.3 对外执行结果

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

## 8. D5 后续验证问题

1. Issue terminal event 到 Wakeup receipt 的事件捕获是否存在持久化补扫；服务器在 commit 后、publish 前退出时能否恢复？
2. Issue 更新后的 Run 入队是否有可用的原生待办扫描或对账入口？如何在不重复 Run 的情况下补齐？
3. 评论创建后的触发是否能按 comment ID 补扫？不同 HEAD queued blocker 的 obligation 是否会在后续状态变化中自动恢复？
4. Issue / Comment / Worker 委派入口是否能为调用者提供稳定 operation ID 和可查回的原结果？
5. SOP Node Activation 到 Multica Task 的绑定，如何复用 Task 唯一约束与原生 Run 谱系，避免重复执行和错误合并？
6. 取消、撤权、接管与迟到结果之间，所有写入点是否都核对当前授权代际？

