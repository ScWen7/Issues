# Multica 源码研究 · 从工作交接到 Runtime 领取

研究快照为 `multica-ai/multica` 默认分支 `main` 的 `f337d4d5972c19f27ba645d4caaaca40cff86c5a`。本轮从远端获取代码，沿普通 Issue 写入、子 Issue 唤醒和 Daemon 领取三条调用链，交叉阅读 Go handler、service、SQL 查询、数据库迁移、调度器和测试断言。下文以“平台取舍”标明我们的选择。[固定快照](https://github.com/multica-ai/multica/tree/f337d4d5972c19f27ba645d4caaaca40cff86c5a)

### M1　Project Workflow 解决列与负责人的交接

工作区共用状态目录。项目通过 `workflow_id` 引用有序步骤，每步包含状态、处理人、指令和可选前进、退回目标。HTTP 写入校验目标状态是否属于定义，进入配置了交接的列才解析负责人；请求显式指定负责人时保留该选择。`NextStatus` 给出后继建议，普通更新入口检查的是目标列成员资格和旧 Run 的阶段绑定。迁移注释直接给出选型理由：跨项目过滤依赖共享状态键，编辑器整份保存定义，跨定义查询单步没有当前用途，所以步骤存 JSONB。平台取舍：保留 Issue 状态给人协作和交接，SOP 的并行完成条件由一次执行中的节点记录表达。[定义和后继](https://github.com/multica-ai/multica/blob/f337d4d5972c19f27ba645d4caaaca40cff86c5a/server/internal/issueworkflow/issueworkflow.go#L147-L169) · [后继选择](https://github.com/multica-ai/multica/blob/f337d4d5972c19f27ba645d4caaaca40cff86c5a/server/internal/issueworkflow/issueworkflow.go#L300-L326) · [迁移理由](https://github.com/multica-ai/multica/blob/f337d4d5972c19f27ba645d4caaaca40cff86c5a/server/migrations/573_issue_workflow.up.sql#L3-L28) · [写入口](https://github.com/multica-ai/multica/blob/f337d4d5972c19f27ba645d4caaaca40cff86c5a/server/internal/handler/issue_workflow_entry.go#L48-L115)

### M2　交接重放和返工重入有不同身份

Squad 交接经过 Leader 的调用权限检查。服务在事务内取得 Issue 范围的 advisory lock，以 `issue + agent + squad + handoff revision` 查重，把新的工作写成可延期晋升的 Run，保留交接所在步骤。八个并发重放都命中同一历史交接，而退出再重入同一列会创建第二条。队列占用期间不覆盖先前 Run 的身份、指令或 Squad。对直接指定 Agent 的另一条路径，已有该 Issue 的 pending Run 可以覆盖新步骤，说明 Squad 的逐次保留是特定分支的语义。平台取舍：每次 SOP 节点激活分配稳定标识，网络重放复用它，业务返工创建新的激活。容量不足时保留意图。[入口差异](https://github.com/multica-ai/multica/blob/f337d4d5972c19f27ba645d4caaaca40cff86c5a/server/internal/service/issue_trigger.go#L151-L210) · [事务](https://github.com/multica-ai/multica/blob/f337d4d5972c19f27ba645d4caaaca40cff86c5a/server/internal/service/workflow_squad_handoff.go#L13-L46) · [SQL](https://github.com/multica-ai/multica/blob/f337d4d5972c19f27ba645d4caaaca40cff86c5a/server/pkg/db/queries/workflow_handoff.sql#L1-L16) · [并发和重入断言](https://github.com/multica-ai/multica/blob/f337d4d5972c19f27ba645d4caaaca40cff86c5a/server/internal/handler/issue_workflow_squad_test.go#L85-L174)

### M3　写权限还需要本轮激活身份

`workflowStepMoved` 比较 Run 绑定的 `workflow_step` 与 Issue 当前状态，人工移到另一列后，旧 Run 写状态得到 HTTP 409，仍可提交普通信息。自动重试保留原步骤，人工从历史 Run 发起重跑绑定当前步骤并保留来源。交接的去重键与写入检查是两处判断。由判定式推断，单靠步骤名会混淆 `A → B → A` 的两次 A。平台取舍：节点结算在同一事务核对执行实例、激活 ID、当前尝试和制品版本。迟到回报留作历史证据，活动激活决定推进资格。[写入检查](https://github.com/multica-ai/multica/blob/f337d4d5972c19f27ba645d4caaaca40cff86c5a/server/internal/handler/issue_workflow_entry.go#L80-L123) · [409 与留证测试](https://github.com/multica-ai/multica/blob/f337d4d5972c19f27ba645d4caaaca40cff86c5a/server/internal/handler/issue_workflow_test.go#L1255-L1307) · [重试、重跑与来源](https://github.com/multica-ai/multica/blob/f337d4d5972c19f27ba645d4caaaca40cff86c5a/server/internal/service/issue_wakeup_workflow_test.go#L58-L104)

### M4　工作事件可以有多个观察者，同一次交接只授权一个派发来源

Issue 写入先标记本次交接的 Agent，数据库 capture 对该 Agent 的 Issue 订阅跳过触发，其他观察者和平台规则仍能收到事件。新旧变更合并时轮换收据 ID，旧消费者只可消费它实际读取的版本。普通交接在 Issue 更新之后走统一 `WillEnqueueRun` 决策，预览也用同一判定；普通交接与业务写入存在提交间隔。唤醒服务另有把创建 Run、消费收据、推进游标放进同一事务的路径。平台取舍：沿用共同判定和按目标抑制，另把推进决定与待派工作同事务持久化，重试读取该记录。[普通交接路径](https://github.com/multica-ai/multica/blob/f337d4d5972c19f27ba645d4caaaca40cff86c5a/server/internal/handler/issue.go#L4386-L4433) · [SQL 合并与查重](https://github.com/multica-ai/multica/blob/f337d4d5972c19f27ba645d4caaaca40cff86c5a/server/migrations/579_wakeup_skip_handed_to_agent.up.sql#L30-L54) · [三个目标的断言](https://github.com/multica-ai/multica/blob/f337d4d5972c19f27ba645d4caaaca40cff86c5a/server/internal/handler/issue_workflow_test.go#L1438-L1462) · [事务内消费](https://github.com/multica-ai/multica/blob/f337d4d5972c19f27ba645d4caaaca40cff86c5a/server/internal/service/issue_wakeup.go#L1335-L1366)

### M5　子 Issue 的 stage 汇总前序关闭事实，Leader 或人判断如何推进

`stageProgress` 对子 Issue 按阶段排序，记录已连续关闭的前序阶段和第一个仍等待的阶段。末阶段结束后，无阶段子项仍会影响整体关闭。已取消子项分别计入关闭数和取消数。系统按父 Issue 的当前负责人选择 Agent、Squad Leader 或成员通知，锁内重查目标；默认指令让接收者核对取消项和依赖是否满足，再启动后续工作。设计理由可从分工读出：平台能可靠数出状态，协调者掌握取消项对目标的实际影响。平台取舍：stage 用于自由分工的提示。同一阶段内 A、B 并行，若 C 只依赖 A，C 的放行由 SOP 的 A→C 边和 A 的具体产出决定；B 可继续工作。[阶段算法](https://github.com/multica-ai/multica/blob/f337d4d5972c19f27ba645d4caaaca40cff86c5a/server/internal/service/issue_wakeup_condition.go#L653-L710) · [测试矩阵](https://github.com/multica-ai/multica/blob/f337d4d5972c19f27ba645d4caaaca40cff86c5a/server/internal/service/issue_wakeup_system_test.go#L19-L55) · [默认指令](https://github.com/multica-ai/multica/blob/f337d4d5972c19f27ba645d4caaaca40cff86c5a/server/internal/service/issue_wakeup_system.go#L24-L54) · [目标复核](https://github.com/multica-ai/multica/blob/f337d4d5972c19f27ba645d4caaaca40cff86c5a/server/internal/service/issue_wakeup_system.go#L424-L451)

### M6　Leader 的判断与基础设施派发分别存在于提示词和服务端

Leader brief 要求阅读目标和能力、委派、记录 `action/no_action/failed` 并结束本轮。服务端评论路由则解析实际负责人或来源委派，Worker 的结果能唤醒 Leader；上游还有 guest Squad 的路由。集成测试沿 HTTP 评论、保存的来源身份、Worker Run、结果回复一直查回 Leader Run 数量。平台取舍：保留短轮次协调和可追踪回报。自动协调只由我们项目里获指派的 Squad 启动；SOP 托管期间，Leader 提交异常处理或范围调整，工作流协调端消费已授权动作。[Leader 协议](https://github.com/multica-ai/multica/blob/f337d4d5972c19f27ba645d4caaaca40cff86c5a/server/internal/handler/squad_briefing.go#L44-L92) · [服务端分支](https://github.com/multica-ai/multica/blob/f337d4d5972c19f27ba645d4caaaca40cff86c5a/server/internal/handler/comment.go#L2712-L2732) · [实际 HTTP 回路断言](https://github.com/multica-ai/multica/blob/f337d4d5972c19f27ba645d4caaaca40cff86c5a/server/internal/handler/squad_worker_comment_wakes_leader_test.go#L425-L500)

### M7　已就绪、可领取和已开始是三个时刻

任务写入时取 Issue 优先级。claim 事务锁 Agent，复核绑定与并发上限，再锁共享 Runtime 容量，队列 SQL 检查在线与心跳，按优先级、创建时间、ID 拣选，同时串行化同一 Issue 上同一 Agent 的活动执行。项目注释明确解释，多 Agent 可能共用一台机器，单看个人上限会超发；先锁后读还保护管理员动态调低上限。领取只把状态改成 `dispatched` 并设置准备租约。派发回滚、重新领取、Start 均检查领取代次；旧处理器收尾不会撤销后来一次领取。平台取舍：依赖满足即持久化 ready。现场容量、优先级和权限决定实际投递，Start 回执写入执行开始。Leader 离线影响协调与它负责的队列，受托且已有授权的其他执行可独立回报。[优先级来源](https://github.com/multica-ai/multica/blob/f337d4d5972c19f27ba645d4caaaca40cff86c5a/server/internal/service/task.go#L1324-L1337) · [Agent 与 Runtime 双层容量](https://github.com/multica-ai/multica/blob/f337d4d5972c19f27ba645d4caaaca40cff86c5a/server/internal/service/task.go#L3692-L3764) · [原子领取](https://github.com/multica-ai/multica/blob/f337d4d5972c19f27ba645d4caaaca40cff86c5a/server/pkg/db/queries/agent.sql#L770-L831) · [带代次的回滚与重领](https://github.com/multica-ai/multica/blob/f337d4d5972c19f27ba645d4caaaca40cff86c5a/server/pkg/db/queries/agent.sql#L874-L907) · [开始确认](https://github.com/multica-ai/multica/blob/f337d4d5972c19f27ba645d4caaaca40cff86c5a/server/pkg/db/queries/agent.sql#L1002-L1008)

### 本轮执行记录

使用 Go 1.26.9、临时 PostgreSQL 17.5，执行上游 `cmd/migrate up` 到 `656_runtime_profile_add_amp`。固定提交上运行 `go test -v ./internal/issueworkflow` 全包 20 个顶层用例，以及 `./internal/service` 精选 11 个和 `./internal/handler` 精选 6 个，合计 37 个顶层用例通过。service 组覆盖并发消费新事件、stage、重试与重跑、错误 Runtime、并发容量；handler 组覆盖八次同时重放、队列占用下的跨阶段保留、旧 Run 写冲突、同一交接的观察者、WebSocket 领取超时重投和防止旧代回滚。数据库按上游迁移初始化，断言实际读取记录状态。[领取竞争用例](https://github.com/multica-ai/multica/blob/f337d4d5972c19f27ba645d4caaaca40cff86c5a/server/internal/service/task_claim_race_test.go#L22-L85) · [WebSocket 与五种恢复状态](https://github.com/multica-ai/multica/blob/f337d4d5972c19f27ba645d4caaaca40cff86c5a/server/internal/handler/daemon_batch_claim_recovery_test.go#L115-L196)


以下命令在上游的 `server/` 目录运行，`DATABASE_URL` 指向供本次测试使用的 PostgreSQL 库。

```sh
go run ./cmd/migrate up
go test -v ./internal/issueworkflow
go test -count=1 -v ./internal/service -run '^(TestIssueWakeupCaptureRacingConsumptionKeepsNewInput|TestStageProgress|TestStageProgressCountsCancellations|TestChildrenDoneStageCondition|TestChildDoneInstructionPrecedence|TestWakeupRunKeepsTheRegisteringRunsStep|TestRetryKeepsWorkflowHandoffBrief|TestManualRerunBindsToCurrentWorkflowStep|TestJoinedWakeupKeepsTheWaitingRunsWorkflowStep|TestClaimTaskRejectsMismatchedAgentRuntime|TestClaimTaskConcurrentCapacityRespected)$'
go test -count=1 -v ./internal/handler -run '^(TestClaimTasksByRuntime_DeadlineRecoveryOverWebSocket|TestRequeueUndeliveredBatchClaims_PreservesOtherGenerationsAndStates|TestWorkflowSquadHandoffReplayDoesNotDuplicate|TestWorkflowSquadHandoffPreservesPendingStages|TestAgentStatusChangeRefusedAfterIssueMoved|TestHandoffDoesNotAlsoWakeTheHandler)$'
```
