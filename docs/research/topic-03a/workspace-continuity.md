# Multica 的工作副本、并行领取与准备代次

以 [Multica 固定提交 fdfbfcd](https://github.com/multica-ai/multica/tree/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc) 为准。实验使用 Go 1.26.9、Git 2.52.0、PostgreSQL 17.5，数据库迁移至 657。贯穿夹具实际调用原生领取和重领 SQL、Start HTTP handler、独立进程中的 Prepare / Reuse helper、Git 工作树和 Finalize。[贯穿用例](../../../prototypes/topic-03a/workspace-continuity_test.go)

## 四个动作分别决定什么

| 动作 | 读取和修改的对象 | 设计原因及项目采用方式 |
|---|---|---|
| 领取任务 | 同一 Issue 内，Claim 查找同 Agent 的 dispatched、running 或 waiting_local_directory 任务。不同评论线程可以分别排队，活动的一条仍会挡住同 Agent 下一条。不同 Agent 可各领一条。领取恢复会更新 dispatched_at，带代次的 Start 在事务中锁住记录再转换状态 | SOP 可以把依赖已满足的节点同时标记就绪；实际并行还要看 Agent、Runtime 容量、目录方式。执行器应展示排队原因。按节点尝试绑定真实 Run，两条工作线采用不同输入和交付引用。[待派唯一性](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/migrations/452_agent_task_pending_thread_unique.up.sql#L1-L5) · [领取](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/agent.sql#L770-L830) · [重领](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/agent.sql#L892-L935) · [Start 事务](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/service/task.go#L4511-L4567) |
| 选择工作副本 | 受管目录首次 Prepare 建立任务目录，按需检出仓库。已有受管目录经路径、工作区、Agent、Issue 或 Chat、marker、来源文件和锁复核后可 Reuse。绑定本地目录时走新 Prepare，按资源设置在成员目录原地执行，或在独立 Git 工作树执行。原地 Issue 工作独占目录；worktree 在快照准备时也短暂等待该目录，准备结束即释放快照锁 | 原地运行有利于访问已有工具和未提交材料；独立工作树能让已获准的不同工作线同时修改同名文件。为继续工作分别取用本地目录、可迁移提交或外部制品，记录输入摘要、原始基准和所有者。[路径与归属复核](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/daemon.go#L7091-L7175) · [父进程管理锁](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/execenv/execenv.go#L1314-L1375) · [受管目录复用及重检](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/daemon.go#L7549-L7659) · [快照等待与释放](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/daemon.go#L8514-L8584) |
| 继续 Git 工作线 | 准备阶段把成员目录中适用的未提交工作快照带到新工作树。同一工作的后续调用按 workspace、Agent、conversation 的固定身份及其记录的 commit 祖先关系判断是否续用已有分支。分支被其他工作树占用时可从其当前提交另开分支 | 适合保留多轮协作中的工作，同时避免同名分支的误认。业务候选固定到不可变提交和外部制品摘要。分支占用时产生的工作线有自己的结果，明确选择或集成之后才能成为下一候选。[快照](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/execenv/local_worktree.go#L310-L397) · [分支归属与忙时分叉](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/execenv/local_worktree.go#L1421-L1563) · [后续用户编辑](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/execenv/local_worktree.go#L1614-L1682) |
| 交付与清理 | 成功 Prepare 后 runTask 安排退出时清理宿主辅助文件并执行 Finalize，后续 Start 报错也经过这组动作。能安全提交时返回分支，清理、冲突或交付验证失败时保留工作树位置。Agent 已提交后留下的其他改动可保存到单独引用 | 记录产物指向的实际 commit、工作树、剩余改动和清理结果。引用已生成、报告已持久化和节点验收分别核对，真实失败的尝试也可留下可找回的工作。[Finalize 安排及结果](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/daemon.go#L8599-L8658) · [辅助文件清理](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/daemon.go#L8679-L8721) · [错误和保留工作树](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/execenv/local_worktree.go#L563-L631) · [剩余改动](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/execenv/local_worktree.go#L885-L953) |

## 两条新实验

1. **旧代准备晚于新代开工。** 原生 SQL 将任务交给 G1。同一 Agent 在同一 Issue 的另一讨论已排队，第二次 Claim 得到空结果；另一个 Agent 成功领取自己的任务。夹具让 G1 的父进程保持任务目录锁，在调用实际 helper 前暂停。测试把准备租约和重领窗口都设为 25 毫秒，用数据库时钟真实过期。以相同 Task 和 Runtime 重领得 G2，G2 争用同一目录被拒，改在独立根和另一份 clone 完成 Prepare。G2 的实际 Start 返回 200。此后放行 G1，在 G1 自己的工作树中确实生成了任务 marker，再调用 Start 得到 409。两侧顺次清理辅助文件并 Finalize；G1 的新建空分支和工作树消失，G2 的分支相对基准只有 candidate.txt。两份原始 checkout 的 HEAD 都保持原提交，数据库仍是 G2 running。该用例运行真实子进程和 PostgreSQL，以夹具调度顺序和经认证的测试主体调用 handler。两个执行根位于同一物理机。生产重领等待窗为 90 秒，准备租约为 45 秒。[原生时间常量](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/service/task.go#L188-L205) · [代次冲突](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon.go#L4694-L4718)
2. **受管目录的接续。** 在父进程持锁时通过生产 helper 准备受管目录，写入 C1 检查点；另一调用申请复用锁，观察到 ErrEnvRootBusy。释放前任锁后，取得同一目录的复用锁，独立进程通过 Reuse 恢复同一工作目录及检查点字节。这里观察到本机代码和文件连续性。宿主对话、未登记外部制品和跨机目录另有各自的接续证据。[Prepare / Reuse 子进程协议](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/execenv/isolation.go#L109-L141) · [复用前读锁](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/execenv/execenv.go#L1381-L1449)

**平台判断。** 收到 G1 的 409 后，可以判定 G1 未获准启动宿主；排队系统看不到已写到 G1 目录的准备产物。新代接管要同时持有自己的有效领取代次和工作副本使用权。回收按旧代的本地资源身份执行；清理尚未确认时保留其位置。跨机继续时，应取双方均可获取的提交和具名制品，检查摘要后开新工作副本。同机独立 clone 的实验只覆盖 Git 对象及目录隔离；真实远端、进程失联时的恢复时延和成员网络权限另做部署测试。

**准备阶段服务端写入待验证。** 本页已测旧准备成功返回后的本地写入、Start 409 和清理。旧代续租、Waiting、Start 前准备失败回报是三条独立路径：分别在同一 Runtime 的 G2 重领后放行 G1 请求，观察实际更新行和 G2 状态；以旧 Start 被拒且不再回报失败为对照。现有贯穿用例的 Prepare 出错会直接结束测试，这三条路径仍保留在[后续验证输入](../03a-source-evidence.md#109-本轮收口与后续验证输入)。

## 复跑

在可处置的 PostgreSQL 数据库和上述固定 Multica 工作副本运行。下面通过临时测试包导入该版本的内部 handler 和 helper。新测试两项均通过。另跑 20 项原生 execenv 回归，覆盖不同 Task 并发工作树、同一会话忙分支、同任务再派、所有者、未提交编辑、清理失败、前任目录锁及失效目录重置。另跑 9 项 Daemon 回归，覆盖 Start 之前工作目录已就绪、租约续期、取消等待、受管目录归属和路径互斥。29 项均通过，跳过零项。Daemon 包为限制编译资源，用 Go overlay 略去无关测试文件，保留生产源码和所选用例。临时目录放在任何 Git 工作树之外，使上游用例里的“普通用户目录”保持其预期语义。

```bash
set -eu
: "${AGENTPLATFORM_CHECKOUT:?set to this design repository}"
: "${MULTICA_CHECKOUT:?set to the pinned Multica checkout}"
: "${DATABASE_URL:?set to a disposable PostgreSQL database}"
cd "$MULTICA_CHECKOUT/server"
test "$(git rev-parse HEAD)" = fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc
go run ./cmd/migrate up
probe_dir=$(mktemp -d ./phase4workspace.XXXXXXXX)
trap 'rm -f "$probe_dir/workspace_test.go"; rmdir "$probe_dir"' EXIT
cp "$AGENTPLATFORM_CHECKOUT/prototypes/topic-03a/workspace-continuity_test.go" "$probe_dir/workspace_test.go"
go test -count=1 -v "$probe_dir"
go test -count=1 -parallel 3 -run '^Test(PrepareLocalWorktreeConcurrentTasks|PrepareLocalWorktreeContinuesTheConversationBranch|PrepareLocalWorktreeForksWhenTheConversationBranchIsBusy|PrepareLocalWorktreeRedispatchWhileTheConversationBranchIsBusy|PrepareLocalWorktreeRefusesToAdoptABranchItDoesNotOwn|PrepareLocalWorktreeReplaysOnlyTheUserEditsSinceTheLastTurn|PrepareLocalWorktreeHandsConflictingUserEditsToTheAgent|PrepareLocalWorktreeRestartsAMergedConversationBranch|PrepareLocalWorktreeSeparatesIdenticallyNamedConversations|PrepareLocalWorktreePrunesStaleRegistrations|WorktreeModeDeliversBranchWithoutSidecars|FinalizeFailsWhenTheBranchRecordCannotBeWritten|FinalizeRefusesToRecordADeliveryThatResetPastItsBaseline|FinalizeKeepsLeftoversOffTheBranchWhenTheAgentCommitted|DiscardKeepsTheContinuedBranch|PrepareConcurrentSameKeyTasksClaimExclusively|PrepareResetsAfterPriorExecutionEnded|ReleaseLockFreesEnvRootForALaterDispatch|PrepareRollsBackSidecarsWhenPrepareFailsInPlace|PrepareRollsBackWhenWriteContextFilesFailsAfterMarker)$' ./internal/daemon/execenv
go test -count=1 -run '^Test(RunTask_StartTaskCalledAfterWorkdirOnDisk|RunTask_ExtendsPrepareLeaseDuringStartTask|RunTask_PrepareTimeoutStopsLeaseDuringBlockedStartTask|LockReusablePriorEnvRootWaitsOutTheDyingPredecessor|LockReusablePriorEnvRootStopsWaitingWhenTheContextEnds|ShouldReusePriorWorkdirSquadLeaderRejectsMismatchedProvenanceOwner|IssueTasksStillSerialiseOnPathMutex|AcquireLocalDirectoryLockSkipsWorktreeMode|RunTaskReusesPriorWorkdirForFreshSession)$' ./internal/daemon
```

## 从独立接收端取回 C2

用订单导出实验的实际提交和 east.xlsx 再跑一次交接。发送端有独立 clone，本机 bare 仓库起初只发布 C1；接收端通过 HTTP 首次 clone 并 fetch，确定对象库里没有 C2。发布 C2 后再次 fetch，只按报告固定的 `005e558ad99a6def3f4dbb2c7a1ec56e71553bf7` 检出，HEAD 处于分离状态。接收端从 HTTP 附件 URL 下载东区文件，核对报告记录的 5,494 字节及 SHA-256 `5784c6c9f6660ac89a3bd4188541f5bfaee85b2e21a39b47a55923983380e852`，打开 XLSX 容器后才接收。发送端随后从 C1 产生迟到提交并推送到 main，接收端刷新后，远端 main 确实移动，已检出的 C2 和已验收的文件均保持原值。最后把同一 URL 上的内容改动一个字节并保持长度，接收端按摘要拒绝，原已接收文件完整。发送与接收在一台机器完成，接收接口只消费 Git HTTP 远端、固定提交、HTTP 附件和预期摘要。[交接探针](../../../prototypes/topic-03a/portable-handoff.py)

在本项目根目录用订单夹具的输出目录复跑。若已有本轮输出，直接运行第二条命令。

```bash
python3 prototypes/topic-03a/order-export/run.py /tmp/phase4-export-example
python3 prototypes/topic-03a/portable-handoff.py /tmp/phase4-export-example
```
