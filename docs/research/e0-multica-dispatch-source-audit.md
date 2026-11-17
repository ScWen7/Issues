# E0 · Multica 来源身份与派发链源码审查

> 本文记录 E0 对 Multica 原生 Issue 指派、Task 创建、Comment 协助、Retry 和 pending 去重的源码核验，并据此收敛最小扩展方向。
> 核验基准：`multica-ai/multica` 的 `main`，提交 `b70c8b96d0c638e73802336063abfe3734f69f65`。
> 与此前 VS-0 / VS-5 使用的 `71683141a764ed3b1620db4bc26a2d0a098f135c` 相比，当前 main 前进 46 个提交。以下结论按 b70c8b9 取证；进入实际集成前仍需对用户确定的目标分支复核。

## 1. 结论

**Multica 已有可复用的执行链和来源导航字段，但还没有满足 AgentPlatform 要求的“业务来源意图可持久恢复、按来源身份唯一查回主 Task”的完整契约。**

本次核验确认：

1. Issue 指派先完成 Issue 写入，之后才调用 `dispatchIssueRun`；Agent 分支忽略 `EnqueueTaskForIssueWithHandoff` 返回的错误。Issue 已指派不保证 Task 已创建。
2. Task 已有 `trigger_evidence_kind/ref_id`，可记录 `issue_assignment` 等来源导航，但它不是幂等键，没有唯一约束，也没有来源意图尚未派发时的持久记录。
3. Task 创建依赖 pending 部分唯一索引防止部分重复。当前 main 的索引已按 `issue_id + agent_id + comment_thread_id` 区分线程，并覆盖特定 deferred channel task；不能继续把它概括成简单的 `(Issue, Agent)` 唯一约束。
4. pending 冲突会转成 `ErrDuplicatePendingTask`。这只能说明某个 pending Task 占据了唯一槽位，不能证明它的输入、授权和交付范围覆盖本次新意图。
5. Retry 沿原生 `retry_of_task_id` 谱系创建，并继承父执行的来源归因。来源唯一性不能误伤合法 Retry 子 Task。
6. Comment 的触发目标在评论保存后解析并逐目标 enqueue；当前已有触发结果和失败日志，但没有覆盖 AgentPlatform 所需的持久化目标意图与统一查回关系。
7. 当前 Task 数据模型尚未发现可查询的 Execution Purpose 字段。Production / Governance 隔离仍是平台扩展，不能假设已由上游提供。

因此，**不能只给现有 Task 增加一个 `issue_assignment` evidence 标签就宣布 E0 完成**。需要在业务来源侧保存可恢复的操作身份，并在原生 Task 创建边界写入可查回的主来源身份。

## 2. 固定源码事实

| 位置 | 已核实行为 | 对 AgentPlatform 的含义 |
|---|---|---|
| [Issue 指派处理](https://github.com/multica-ai/multica/blob/b70c8b96d0c638e73802336063abfe3734f69f65/server/internal/handler/issue.go) | `WillEnqueueRun` 先计算是否触发；Issue 更新及事件发布后，才调用 `dispatchIssueRun` | Issue 更新和派发不是一个原子业务转换；必须有可恢复的来源事实 |
| [Issue 派发处理](https://github.com/multica-ai/multica/blob/b70c8b96d0c638e73802336063abfe3734f69f65/server/internal/handler/issue_trigger.go) | Agent 分支调用 `EnqueueTaskForIssueWithHandoff`，返回值被忽略 | enqueue 失败不会阻止 Issue 更新成功返回，也没有可由来源身份查回的持久待办 |
| [Issue 触发判定](https://github.com/multica-ai/multica/blob/b70c8b96d0c638e73802336063abfe3734f69f65/server/internal/service/issue_trigger.go) | `WillEnqueueRun` 统一判断创建、指派、状态触发、Backlog、Triage、Agent 可执行性等条件 | 应复用该业务资格判定，不另造一套平行派发规则；但它不是持久化意图 |
| [Task 创建服务](https://github.com/multica-ai/multica/blob/b70c8b96d0c638e73802336063abfe3734f69f65/server/internal/service/task.go) | 统一构造 attribution、来源 evidence、Runtime 和输入参数，再调用原生 CreateAgentTask | 是稳定来源身份写入原生 Task 的主要适配位置之一 |
| [Task 创建 SQL](https://github.com/multica-ai/multica/blob/b70c8b96d0c638e73802336063abfe3734f69f65/server/pkg/db/queries/agent.sql) | `CreateAgentTask` 写入现有 Task 行；没有业务来源意图唯一查回字段 | 需要最小扩展原生创建 / 查回边界，而不是另建 Task 队列 |
| [来源归因迁移](https://github.com/multica-ai/multica/blob/b70c8b96d0c638e73802336063abfe3734f69f65/server/migrations/184_agent_task_attribution.up.sql) | `trigger_evidence_kind/ref_id` 是自由标签 + 来源行 ID，注释明确用于定位直接触发原因 | 可继续用于导航和审计，但不能替代稳定幂等身份 |
| [当前 pending 索引](https://github.com/multica-ai/multica/blob/b70c8b96d0c638e73802336063abfe3734f69f65/server/migrations/452_agent_task_pending_thread_unique.up.sql) | 唯一键为 Issue、Agent、Comment Thread；只约束 queued / dispatched 及指定 deferred 状态 | 现有索引保护调度槽位，不表达业务意图唯一性 |
| [Comment 触发处理](https://github.com/multica-ai/multica/blob/b70c8b96d0c638e73802336063abfe3734f69f65/server/internal/handler/comment.go) | 保存 Comment 后计算目标并逐个 enqueue；单目标失败形成失败结果 / 日志 | 需要保留目标解析版本及每个目标的可恢复绑定；不能因一个目标失败而重派所有目标 |
| [Retry SQL](https://github.com/multica-ai/multica/blob/b70c8b96d0c638e73802336063abfe3734f69f65/server/pkg/db/queries/agent.sql) | Retry 创建新 Task，保留父 Task 归因并记录 retry 谱系 | 来源唯一约束只针对主 Task；Retry 子项仍是独立执行事实 |

### 2.1 两种身份不能混淆

- `originator_source`：谁是这次执行的可归责人，属于归因和审计。
- `trigger_evidence_kind/ref_id`：什么来源触发了执行，属于来源导航。
- AgentPlatform 的业务派发身份：哪一次具体的授权 / 指派 / 评论目标 / 节点尝试产生了这次执行，负责幂等查回。

前两类现有字段不能代替第三类。尤其不能把 Issue ID 作为每次指派的唯一来源 ID：同一 Issue 可以多次改派、撤权后重新授权或由同一 Agent 再次接手。

### 2.2 Pending 冲突不等于意图已完成

当前 pending 唯一索引按 Issue、Agent、Thread 约束队列占位。不同 HEAD、线程、输入和来源仍可能竞争已有槽位；服务层将部分冲突归为 `ErrDuplicatePendingTask`。

处理冲突时必须读取冲突 Task 并核对：

- 目标 Agent、Issue 和线程范围；
- 业务来源与当前授权代际；
- 工作约定、输入版本 / HEAD；
- 执行用途与本次交付范围；
- Task 是否仍处于可接收新输入的状态；
- 对于 Comment，是否存在明确的 coalesced / delivered 覆盖回执。

只有全部满足，才可将新来源绑定到已有 Task；否则保持 Blocked / Unknown，不能把“索引冲突”伪装成“已接单”。

## 2.3 Issue 更新事务与派发事务之间的真实边界

进一步核对 `UpdateIssue`、`updateIssueWithStatusGuard` 与 `dispatchIssueRun` 后，事务边界更明确：

- `UpdateIssue` 通过 `updateIssueWithStatusGuard` 写入 Issue；当需要状态保护时，Issue 更新及关闭状态时停止 Wakeup 在该写事务内完成。
- 部分普通内建状态更新路径可直接使用 Queries，但 Issue 更新仍在派发前完成。
- Handler 在 Issue 更新、事件发布及后续处理之后才调用 `dispatchIssueRun`。
- Agent 派发分支仍忽略 enqueue 错误。
- assignee_changed Activity 由事件监听器消费 IssueUpdated 事件后异步写入；它不是 Issue 更新事务中的可靠来源意图，也不能承担派发恢复。

因此，不能简单把 Activity 当作 outbox，也不能只在派发失败时补一条日志。最小可靠切入点应是：**在 Issue 权威写入事务中，为真实的 assignee / 授权转换追加不可变来源身份记录；该记录同时保存待派发状态或待派发关联。** 后续 Task 创建和绑定可以独立事务完成，按来源身份查回、对账恢复。

注意：若某条路径的 Issue 更新不是显式事务，仍可由 SQL statement 的原子写入边界完成 Issue 变更与来源记录；不能先更新 Issue，再用另一个非原子请求补写来源记录。

## 2.4 普通指派不天然等于“一次性执行”

本轮还发现一个需要修正产品契约表达的边界：

Multica 原生的 Agent Assignee 不只是一个启动按钮。Issue 指派可以触发 Task；Issue 状态从 Backlog 进入可执行状态也可以触发；Comment 路由、Wakeup 和后续 Issue 变化还会继续影响同一 Agent 的执行。

所以“普通 Agent 指派只允许一次交付、不获得持续协调权”是 AgentPlatform 的授权语义，**不是当前 Multica Assignee 字段天然提供的执行保证**。

实现时必须把两件事分开：

- Issue Assignee：当前工作分配给谁，继续沿用 Multica 的责任与展示语义。
- Work Agreement / Delegation Mode：这次被授予的是 One-shot Delivery 还是 Sustained Coordination，决定是否允许后续 Wakeup 消费、主动继续推进、追加委派和跨回合协调。

因此普通 One-shot Agent 的执行结束后，不能仅依靠“它不是 Main Bot”来保证不会再次执行。后续所有能重新触发该 Agent 的入口，都必须检查当前有效授权模式；无持续授权时，只能允许与原一次性交付直接相关的完成回执 / 结果消费，不能被普通状态变更或新评论隐式升级为持续协调。

这项授权门控不能破坏 Multica 对普通 Agent 的既有行为。AgentPlatform 接管的 Issue 才应用新规则；未纳入 AgentPlatform Work Agreement 的原生 Multica Issue 仍保持上游原语义。如何识别受管 Issue、如何对历史 Issue 渐进启用，在集成实现阶段设计。

## 2.5 Comment 路由已有成熟机制，不应重做

Comment 路径并非简单的“逐个 enqueue 后记录失败”。当前代码已经有：

- 按执行 Agent 去重并保留显式 mention targets；
- AlreadyPending 与 enqueue 并发冲突后的 bounded retry；
- 只有在真实 merge、planned-id 注册、新 Task 创建或可证明的 deferred replay 时才返回 success-shaped outcome；
- queued Task 的 head-scoped coalescing；
- Claim 时的 delivered-comment receipt；
- completion reconcile 与 uncovered obligation propagation；
- 每个目标独立 outcome fan-out。

因此 E0 的扩展应当复用并增强这些既有保证，不得把它简化成新的 Comment Intent 队列。

源码同时明确存在一个未闭合边界：不同 HEAD 的 queued blocker 既不能覆盖新 Comment，也不能安全地合并；当前记录 error，持久化 obligation 仍在既有实现范围之外。AgentPlatform 若要求“每个目标最终可恢复”，需要决定是把此类 obligation 纳入来源身份记录，还是先接受明确的 Blocked / Unknown 并在后续专项补齐；不能将它描述成当前已完整解决。

## 3. E0 最小扩展方案

### 3.1 来源侧：由业务来源保存可恢复身份

不建设通用 Intent 服务或第二个执行队列。来源身份由各自权威业务来源保存：

| 来源 | 身份由谁产生 | 需要持久保存什么 |
|---|---|---|
| 普通 Issue 指派 / Main Bot 授权 | Issue 指派或正式授权的权威写入 | 不可变的指派转换 ID、目标 Agent、执行模式、授权代际及绑定 Task |
| Comment 目标级协助 | Comment 及固定目标解析结果 | Comment ID、解析修订、每个目标 Agent、目标处理结果及绑定 Task |
| SOP Node Attempt | SOP 流程域 | Execution / Activation / Attempt / 本次调用身份及绑定 Task |

Issue 指派目前的异步 Activity 记录由事件监听器生成，不能未经事务核验就当成 Issue 更新同事务内的派发意图。若目标分支没有其他可原子写入的指派转换记录，需要在 Issue 权威写入边界增加最小的追加式转换身份记录；它是业务来源事实，不是执行队列。

### 3.2 Task 侧：为主 Task 增加可查回的来源绑定

在 Multica 原生 Task 创建边界补充一个稳定的主来源身份引用：

- 主 Task 创建时，来源身份与 Task 行在同一原生写入事务内共同保存。
- 相同来源身份重送时查回原主 Task，而不是再次插入。
- 来源侧保存的 Task 绑定与 Task 侧来源引用可双向核对。
- 唯一约束只限制主 Task；合法 Retry 子 Task 继承来源身份并通过原生 Retry 谱系查回。
- 人工 Rerun 使用新的动作身份，保留 `rerun_of_task_id`。
- 兼容 coalescing 时，来源记录可绑定到已有 Task；Task 可以覆盖多个来源，但每个来源仍独立保留自己的身份与结果。
- `trigger_evidence_kind/ref_id` 继续用于来源导航，不承载唯一性。

具体字段名、唯一索引表达和事务代码位置留到目标分支复核后确定，不在本轮虚构 Schema。

### 3.3 派发恢复：沿现有入口补齐可恢复性

目标流程：

1. Issue 指派 / 授权权威写入成功时，持久化本次来源身份。
2. 现有派发路径调用 Multica 原生 Task 创建 / 查回。
3. 创建成功后，将 Task ID 绑定回来源记录；若响应丢失，恢复者按来源身份查回 Task 并补齐绑定。
4. 只有能证明不存在主 Task 时才允许创建；无法证明时保持 Unknown。
5. Task 已终态但结果未消费时，恢复业务消费，不重跑生产。
6. 通知失败只补投通知，不重复创建 Task。

不要求 Issue、Task 和 Runtime 之间存在跨进程全局事务；只要求来源事实先持久化、Task 创建幂等、结果可对账。

## 4. Pending / Coalescing / Retry 兼容规则

1. 不扩大或收窄当前 pending 唯一索引来代替业务身份。
2. 保留 Issue + Agent + Thread 的现有槽位语义；HEAD 约束和 deferred media 条件继续有效。
3. 同一来源身份重复请求必须查回同一主 Task；不同来源意图不能因同 Agent 而自动合并。
4. 允许多个 Comment 来源在明确兼容的同一线程中由一个 Task 覆盖；每个 Comment 目标必须保留自己的结果和 Task 绑定。
5. 任务进入 Claim 后，不能再把新输入默认为已 coalesce；以实际 delivered / coverage receipt 为准。
6. Retry 子 Task 继承主来源身份但不参与主 Task 唯一约束；每个 Retry 保留独立 Task ID 和原生 retry 关系。
7. 历史 Task 缺少新来源身份时保留 Legacy / Unknown，不按 Issue、Agent、时间或 Session 猜测补绑定。

## 5. 扩展维护方式建议

当前扩展触及 Issue 权威写入、TaskService、Task SQL / migration、Retry 和 Comment 目标处理，不是纯外部插件可完成的能力。

推荐采用**可持续跟踪上游 main 的窄差异集成分支**：

- AgentPlatform 的业务规则和契约仍维护在 AgentPlatform 仓库。
- Multica 只承载必须进入其原生事务 / Task 创建边界的最小通用扩展。
- 可以独立上游化的通用能力（例如 Task 来源幂等创建 / 查回）优先整理为上游 PR；AgentPlatform 特有的 Work Agreement / 授权语义不强塞进 Multica 通用产品。
- 每次同步上游时，以固定上游 SHA 记录补丁集、迁移兼容和 Production 回归结果。
- 不复制 Multica 成为另一套长期分叉产品，也不把派发恢复放在外围服务中绕过原生事务。

这是一项维护方式建议；在用户确定实际集成仓库 / 分支前，不创建或修改 Multica 代码仓。

## 6. 当前阶段判定

| E0 项目 | 当前判断 |
|---|---|
| 原生 Issue / Task / Runtime 执行链可复用 | 已确认 |
| 普通指派 enqueue 失败可能静默丢失 | 已确认 |
| 来源 evidence 字段可用于导航 | 已确认 |
| 来源 evidence 字段可作为幂等键 | 不成立 |
| pending 索引可替代业务来源身份 | 不成立 |
| Retry 可与主 Task 唯一性分开处理 | 已确认 |
| Comment 目标可逐个 enqueue | 已确认 |
| Comment 目标具备平台所需的持久查回身份 | 尚未确认 / 当前契约未覆盖 |
| Task Purpose 已由当前 Multica 提供 | 未发现；需扩展 |
| 最终目标分支与维护仓库已确定 | 未确定 |

**E0 已完成关键源码差异与最小扩展方向的设计收敛，但尚未达到工程修改准入。** 仍需确定实际集成目标分支，并在该分支复核上述路径；随后补齐历史 Task 兼容方案和可复现故障验收设计。未经该步骤，不进入 Schema / API 或代码实现。
