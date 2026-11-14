# 从本地宿主回报到 Issue 的执行结果

订单验证 C1 和 C2 共用验证 Issue、Agent 和共享 Runtime，各有单独的 Multica 任务。C1 的权限测试未通过，C2 修复后通过。两份结果都经相同的 Daemon 执行路径交回服务端。这个组合能区分“验证程序正常完成”“候选通过检查”和“有人接受交付”。[C1 固定报告](fixtures/order-export-c1.json) · [C2 固定报告](fixtures/order-export-c2.json) · [集成测试](../../../prototypes/topic-03a/daemon-result-handoff_test.go)

## 实际运行链

测试固定 Multica `fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc`，使用 Go 1.26.9、PostgreSQL 17.5，数据库迁移至 657。资源所有者用夹具签发的成员凭据共享 Runtime，Daemon 用独立的机器凭据通过实际 HTTP 领取验证者任务。服务端走生产认证中间件和业务 handler。测试从 Daemon 的单任务入口进入，由它调用独立的 Prepare / Reuse 助手、Start、内置 Claude 适配器和独立 POSIX 子进程。子进程把上一环节生成的实际订单报告复制进工作目录，将报告文本作为 Claude 协议的终态输出返回。数据库中的 `result.output` 逐字匹配去掉外围空白的报告文本，工作目录文件与原始报告逐字节匹配。受控子进程只承担可重现的宿主协议输出，不调用模型。服务器路由和 Daemon 驱动同属一个 Go 测试进程，准备助手、宿主和 PostgreSQL 均独立运行；物理网络、机器注册和 WebSocket 重连另有验证范围。[生产 HTTP 路由](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/cmd/server/router.go#L1648-L1707) · [独立准备进程](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/daemon.go#L7737-L7759) · [Claude 终态解析](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/claude.go#L299-L359)

| 场景 | 实际观测 | 平台如何使用 |
|---|---|---|
| C1 请求返工 | 宿主协议成功结束，任务状态 completed，A2 失败、A3 通过，verdict 为 rework。一次完成回调，源 Issue 出现一条关联该任务与 Agent 的评论 | 按标准把 C1 交回返工。技术完成和候选结论各自保留 |
| C2 已落库，第一次回调响应丢失 | 真实 handler 提交事务后，实验只把它对客户端的首次响应改成 503。Daemon 的待确认队列当时有一份报告，生产客户端重试后队列为零。完成回调共两次，C2 的源评论仍只有一条；A2、A3 均通过，verdict 为 pass | 按既有任务和节点尝试关联原结果。SOP 可消费这次核验，人工接受沿用 Issue 的验收决定 |
| C2 复用 C1 的工作目录与文件名 | 同一 Issue / Agent 的 C1 与 C2 使用完全相同的工作路径。C2 完成后打开 C1 记录的本地路径，读出的是 C2 字节；数据库中 C1 的终态输出仍是原报告 | 需要长期复核的制品在确认回报时按内容摘要保存，历史记录以这个版本作为引用 |
| C2 完成后重发 C1 完成回调 | 服务端向机器凭据返回成功，两条任务各自保存原报告，两条原评论均保持单份 | 原生 CAS 保护已终结任务；SOP 还要按已登记的 Run、尝试、候选及授权判断哪个结果可推进当前节点。报告正文里自述的候选标签用于比对 |
| 撤销共享时子进程仍在工作 | 送达服务端的撤销计划命中当前 Agent 与活动任务。暂缓一条真实状态轮询返回，数据库已 cancelled，原任务凭据访问 Issue 为 401，此刻子进程 PID 仍存活。恢复该轮询后，宿主子进程退出，服务端收到一次 cancel-ack | 分别呈现共享已撤回、任务已取消和本地宿主已停止。单机一次 PID 退出证明此用例的宿主退出，子树清理和跨机器重连按具体宿主另行观测 |
| 已取消任务的迟到完成 | 用 Daemon 机器凭据重发 /complete 得到成功响应。数据库仍是 cancelled、没有成功输出，源任务的评论数为零 | 显示已存的原状态。回调得到响应、实际写入业务输出、SOP 收到当前结果，各自记录 |

C1 源文件 SHA-256 为 `da022445c03fa787af994101f47cd8cfb777913f882a6b7aa32116a3493afcb1`，C2 为 `e9c93051c5b844cf23aa89061eed967c5a2267e846e26b37ece7275f194bd514`。本用例只在宿主工作目录和固定样本上比较原始字节。通过完成接口送达的是文本及其原有的具名工作簿摘要，获取工作簿本体要走文件交付通道。

## 为什么这样设计

网络成功响应可能丢在数据库提交之后。Daemon 先把终态写入本机待确认队列，收到服务端确认再清理；服务端只允许 running 记录做一次完成转换，重发时读取现有状态。该条件同时覆盖已经被取消的任务。一条正常 Issue 的执行如果尚无匹配 Agent 评论，服务层可从这次输出生成评论，带上 `source_task_id`。本次实验的两条源评论依靠这一回退行为产生，其他检查点或既有评论会影响是否生成。专题二需要的节点尝试版本、可消费的候选和 Grant 由本项目校验。[本地队列与回执](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/daemon.go#L6525-L6586) · [服务端状态转换](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/agent.sql#L1028-L1050) · [重复请求的 HTTP 行为](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon.go#L4973-L4993) · [服务层回退与评论来源](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/service/task.go#L4823-L4886)

共享撤销发生在服务端，Daemon 随后可从状态轮询获知终态、停止宿主、等待收尾，再确认取消。实验只暂缓一次状态响应，以便稳定观察两地状态暂时不同。独立于这条集成用例，实际复跑上游 5 项待确认队列回归，覆盖落盘与权限、崩溃后的临时记录恢复、客户端重试耗尽后的回放、Daemon 重启后的回放，以及前台回报与回放的并发互斥，5 项通过。[共享撤回](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/runtime.go#L1153-L1208) · [取消观察与收尾](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/daemon.go#L5941-L6009) · [Claude 子进程终止](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/claude.go#L247-L292)

## 复跑

POSIX、Python 3、Go 1.26.9，以及空白的临时 PostgreSQL 17 数据库。先将 `DATABASE_URL` 指向该临时库，`MULTICA_CHECKOUT` 指向固定上游，`AGENTPLATFORM_CHECKOUT` 使用本设计仓库的绝对路径。复跑使用 Go overlay 为上游 daemon 包加载集成测试，并保留独立工作目录。

```bash
set -eu
cd "$MULTICA_CHECKOUT/server"
test "$(git rev-parse HEAD)" = fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc
go run ./cmd/migrate up
overlay_dir=$(mktemp -d)
trap 'rm -f "$overlay_dir/overlay.json"; rmdir "$overlay_dir"' EXIT
python3 - "$AGENTPLATFORM_CHECKOUT" "$overlay_dir/overlay.json" <<'PY'
import json, sys
from pathlib import Path
virtual = Path.cwd() / 'internal/daemon/agentplatform_phase4_result_test.go'
source = Path(sys.argv[1]).resolve() / 'prototypes/topic-03a/daemon-result-handoff_test.go'
Path(sys.argv[2]).write_text(json.dumps({'Replace': {str(virtual): str(source)}}))
PY
export AP_C1_REPORT="$AGENTPLATFORM_CHECKOUT/docs/research/topic-03a/fixtures/order-export-c1.json"
export AP_C2_REPORT="$AGENTPLATFORM_CHECKOUT/docs/research/topic-03a/fixtures/order-export-c2.json"
go test -p=1 -count=1 -v -overlay "$overlay_dir/overlay.json" -run '^TestPhase4DaemonResultHandoff$' ./internal/daemon
go test -p=1 -count=1 -v -run '^TestTerminalReport(StoreRoundTripAndPermissions|StoreRecoversFlushedTempFileAfterCrash|ReplaysAfterClientRetryWindow|ReplaysAfterDaemonRestart|ForegroundAndReplayDoNotSendConcurrently)$' ./internal/daemon
```

本次资源受限容器在 Go overlay 中一并略去与所选用例无关的上游测试文件，生产实现、两份订单样本、被选测试及其辅助函数均照原样运行。
