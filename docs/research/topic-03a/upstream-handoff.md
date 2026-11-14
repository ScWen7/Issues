# TeamAI 与 LoopForge 如何处理换人接手

订单导出的 A 已离线，B 要复核已发布的 C2，A 恢复后仍可提交此前对 C1 的检查。两个上游对“谁继续驱动”和“哪个结果可改变节点”给出了不同答案。以下对照使用 TeamAI `1bc2ce1` 与 LoopForge `97b3cdc` 的固定源码和原生测试。[订单交接实测](machine-handoff.md)

## TeamAI

| 机制 | 固定版本的实现与实测 | 对订单交接的取舍 |
|---|---|---|
| 发布和接手 | 发布时根据当前 owner、已确认的状态修订和远端快照决定写入。接手者读取快照，只在远端仍持有同一写入标识时替换 owner，远端接受后才安装本地状态。原 owner 排队的发布与另一方排队的旧 claim 均未覆盖较新的决定。接手释放在途租约，独立新工作副本进入新 pass，避免接着原执行者已写入一半的分支运行。[条件写入](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/workflow/handoff.ts#L1018-L1035) · [快照对照](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/workflow/handoff.ts#L1075-L1090) · [释放租约](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/workflow/step-state.ts#L375-L399) | 采用“已读版本仍有效才接手”。以中心派发记录为准，B 领取自己的任务身份，A 的旧回包按原派发登记。Git 分支承担代码传输，Issue、授权和接手顺序由中心保存。 |
| place 与 Git 工作区 | place 按 Run、attempt 记录本机准备和结束阶段，同一准备请求可重入，已结束的 place 可回读结论。受管工作树与宿主借出的工作树有不同收集规则，后者发现未申报的额外改动即保留现场。跨安装交接先检查业务远端的基线与工作分支，B 从独立 checkout 接出 A 的已发布提交。若业务分支先行移动，原生用例得到 `branch_diverged` 并保持快照修订与 B 的本地状态。[准备和结算](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/workflow/place/place.ts#L704-L745) · [宿主目录改动核对](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/workflow/place/writer.ts#L172-L220) · [远端校验](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/workflow/handoff.ts#L478-L540) | 分别记录本机可复用目录和已发布候选。B 核验历史 C2 时按固定提交与附件摘要检出；若要继续写同一工作分支，再比较分支头。这样分支随后前移也不妨碍核验 C2。 |
| Session 接续 | 原生夹具将要继续的 Claude 转录清理后单独归档，快照里只出现会话引用。B 恢复出新的本机会话 ID，接续的内容相同。上游使用真实 Git 归档和测试适配器接收恢复参数。[原生用例](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/__tests__/workflow-handoff-sessions-and-offers.test.ts#L113-L157) | 只有成员选入共享范围的片段进入 Issue。C2 的交接可只带代码和制品。实际接续时另外记录来源会话或执行段与目标宿主新会话的关系。 |

## LoopForge

| 机制 | 固定版本的实现与实测 | 对订单交接的取舍 |
|---|---|---|
| 所有者代次和节点尝试 | 数据库事务校验已有租约与 generation，换 owner 后提高 generation。节点成功和失败都检查代次与节点是否尚在执行；失败还要求 attempt 相同。成功有意允许同代次的旧 attempt 在节点仍执行时提交，保留通过门禁的活跃 Agent 结果。原生用例明确让当前 attempt 8 接受 attempt 1 的成功，另一个用例让 B 接替到第 2 代后，A 的失败和 Run 终止都未生效。[获得和续租](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/repo/runs.go#L1101-L1152) · [成功与失败判定](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/node_outcome.go#L30-L49) · [原生断言](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/run_lease_test.go#L663-L686) | 接手时更新中心派发版本。无论回包成功还是失败，都用原 Run、节点尝试、候选和授权版本判定能否影响当前节点。C1 即使迟到的是通过结论，也只进入 C1 历史。 |
| 子流程制品和旧输出 | 子 SOP 按约定的产物名筛选，缺必需项则失败，同名按 `CreatedAt` 取最近的一条。导入时重设制品 ID、父 Run、父节点和父 attempt。工作区恢复在有正式快照时保留删除动作；旧归档补回机制排除当前和下游节点的产出，避免旧文件蒙混过新检查。[子流程交接](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/sop_node.go#L243-L291) · [旧文件筛选](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/workspace_artifacts.go#L15-L70) | 复用按名声明所需制品、缺件时停止的规则。B 的 `east.xlsx` 由 C2 清单指定，保留来源 Run、attempt、附件 ID 和字节摘要。父节点另建引用；同名和到达时间均不决定采用哪份文件。 |

## 原生测试复跑

在相应固定提交的 checkout 执行。TeamAI 使用 Node 24.22.1、Vitest 4.1.12 和项目原配的测试环境。按文件逐次启动单 worker，同时限制 Node、esbuild 的内存与并发后，五个文件的定向用例分别通过 3、3、3、3、2 项。随后完整复跑上轮受影响的 `workflow-handoff-ends-and-workspaces.test.ts`，54/54 通过，耗时 68.39 秒。其中 3 项与定向用例重合，合计 65 项不同用例。Git 远端由上游夹具在本机建立。先前单独运行大套件也曾以 137 退出，此处统计以测试器报告为准。

```bash
export GOGC=10 GOMEMLIMIT=32MiB GOMAXPROCS=1 RAYON_NUM_THREADS=1 UV_THREADPOOL_SIZE=1
export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=gc.auto GIT_CONFIG_VALUE_0=0
# 若工作机限定 CPU 范围，选当前进程实际获准使用的第一个核。
cpu=$(awk '/Cpus_allowed_list/ {print $2}' /proc/self/status | cut -d, -f1 | cut -d- -f1)
export NODE_OPTIONS='--max-old-space-size=160 --max-semi-space-size=1'
run_cases() {
  taskset -c "$cpu" node ./node_modules/vitest/vitest.mjs run --pool=threads --maxWorkers=1 \
    --no-file-parallelism "src/__tests__/$1.test.ts" -t "$2"
}
run_cases workflow-handoff-ends-and-workspaces 'hands over a run with a workspace|refuses to claim a workspace whose branch on origin moved|keeps the state last published when a run ends with a commit'
run_cases workflow-handoff 'never lets a queued publish replace a claim|never lets a queued claim replace a publish|keeps its own progress and leases when it claims'
run_cases workflow-place 'reuses a prepared lease without overwriting edits|does not prepare a second attempt in the place another open attempt holds|commits and pushes nothing when an adopted writer leaves a path'
run_cases workflow-workspace 'does not lease a continue step to a driver that does not own the copy|starts from the retried pass of a need|fails workspace_base, naming both commits'
run_cases workflow-handoff-sessions-and-offers 'archives the session a step will continue, scrubbed|refuses a member who no longer owns the run before it pins a base'
taskset -c "$cpu" node ./node_modules/vitest/vitest.mjs run --pool=threads --maxWorkers=1 \
  --no-file-parallelism src/__tests__/workflow-handoff-ends-and-workspaces.test.ts
```

LoopForge 使用 Go 1.26.11 和原配的测试数据库，九项引擎测试和两项 Runtime 测试通过。Runtime 验证 Git 与二进制文件恢复、传输的 Run 范围、摘要、完整性和过期。21 MiB 随机文件的 `TestConversationWorkspaceChunkedWorkerTransportRoundTrip` 起初通过 `go test` 启动时收到 `signal: killed`。改为先编译同一原生测试，再以磁盘临时目录单独运行测试二进制，2.96 秒通过。它用同机 worker 与 controller 走实际回环 HTTP，保存并清理源工作区，再恢复并比较全部字节，单次请求及响应均未超过 8 MiB。[工作区大文件测试](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/workspace_checkpoint_stream_test.go#L84-L146)

```bash
GOMAXPROCS=2 GOMEMLIMIT=140MiB GOTOOLCHAIN=local go test -p 1 -parallel 1 -count=1 -v \
  -run '^Test(NonOwnerExecuteNodeDoesNotMutateRun|StaleOwnerCannotFailAfterGenerationTakeover|StaleAttemptFailureIsIgnored|ShouldCommitNodeOutcome|ImportChildArtifactsTakesNewestAttempt|ArchivedReplayDoesNotResurrectCurrentOrDownstreamOutputs|RealSnapshotKeepsIntentionalArtifactDeletion|ConversationWorkspaceSurvivingDirectoryRequiresSavedChecksum)$' ./internal/engine
GOMAXPROCS=1 GOMEMLIMIT=32MiB GOGC=10 GOTOOLCHAIN=local go test -p 1 -parallel 1 -count=1 -v \
  -run '^Test(WorkspaceCheckpointRoundTrip|WorkspaceCheckpointTransfersBoundScopeIntegrityAndExpiry)$' ./internal/runtime
# 在有可用磁盘空间的目录中运行，编译和测试先后执行。
outdir=$(mktemp -d "$PWD/ap5-loopforge.XXXXXX")
GOMAXPROCS=1 GOMEMLIMIT=50MiB GOGC=20 GOTOOLCHAIN=local go test -p 1 -c -o "$outdir/engine.test" ./internal/engine
TMPDIR="$outdir" GOMEMLIMIT=32MiB GOGC=10 GOMAXPROCS=1 "$outdir/engine.test" \
  -test.count=1 -test.parallel=1 -test.v -test.run '^TestConversationWorkspaceChunkedWorkerTransportRoundTrip$'
```

在独立 Ubuntu 24.04 虚拟机上又用普通 go test 运行同一 21 MiB 分块恢复用例和节点尝试语义用例，两项均通过。大文件用例耗时 2.91 秒。[远端 LoopForge 作业日志](https://github.com/ScWen7/Issues/actions/runs/43621807704/job/132528935018)

同一轮在另一台 Ubuntu 24.04 虚拟机从固定 TeamAI 提交全新安装依赖，完整串行执行 workflow-place（80 项）、workflow-handoff-ends-and-workspaces（54 项）和 shell-command（5 项）。三个文件共 139 项通过，其中包含前述本地已覆盖用例；两次结果分别统计。[远端 TeamAI 作业日志](https://github.com/ScWen7/Issues/actions/runs/43621807704/job/132528935082)
