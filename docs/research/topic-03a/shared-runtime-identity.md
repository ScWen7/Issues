# 共享 Runtime 上的任务身份与 Issue 操作

固定版本为 [Multica fdfbfcd](https://github.com/multica-ai/multica/tree/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc)。测试运行 Go 1.26.9、PostgreSQL 17.5，隔离数据库实际迁移至 657。测试用真实 Multica Claim、Start、HTTP 认证中间件、Issue 详情、评论与撤销 handler，所有业务数据和凭据均由本次夹具创建。[实验源码](../../../prototypes/topic-03a/shared-runtime-identity_test.go)

## 权限沿什么路径决定

| 问题 | 固定源码的行为 | 本项目怎样使用 |
|---|---|---|
| 谁提供机器 | 乙持有私有 Runtime 并将它共享给丙。任务交付重新读取并锁定 Runtime，核对 Agent 绑定、共享对象与当前所有者后签发任务令牌。本次令牌记录的 user_id 是乙 | 记录机器所有人和共享同意，发起工作、执行和验收各自保留主体。[交付复核](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon.go#L2464-L2520) · [签发字段](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon.go#L4409-L4452) |
| 谁在回报 | 认证中间件查数据库内哈希及有效期，绑定 workspace、Agent、任务和用户。业务层把任务请求的行为者认作该 Agent，评论另记 source_task_id。Run 中的 originator 是发起工作的丙 | Issue 展示“验证 Agent 在乙的 Runtime 上为丙执行”，并保留回报的真实 Run。[凭据查找](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/task_token.sql#L1-L14) · [认证中间件](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/middleware/auth.go#L100-L145) · [行为者解析](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/handler.go#L891-L898) |
| 谁能看哪个 Issue | 详情和评论先定位当前 workspace 内的目标 Issue，再检查私有项目可见性。任务请求的项目权限取发起人（无值时取 accountable）和 Agent 所有人的共同可见范围。原生允许在另一可见 Issue 中协作，并沿用原 Run 来源 | 同工作区另一可见 Issue 可以收到一般协作评论。本项目受托报告还要匹配专题二 Grant、目标 Issue、节点尝试和候选。原生 201 表示评论获准落库，业务回执另行校验 C2 和验收契约。[定位目标](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/handler.go#L1076-L1129) · [项目权限](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/projectaccess/projectaccess.go#L129-L177) · [任务请求的项目主体](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/project_access.go#L18-L69) · [跨 Issue 评论来源](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/comment.go#L1741-L1775) |
| 撤销共享或令牌过期如何收敛 | 收回共享后，受影响的 Agent 解绑定，活动任务取消。任务取消处理负责清理对应令牌。原生令牌有独立有效期，鉴权时同时校验。数据库任务状态、资源访问和操作认证是三项可分别观察的事实 | 中心回执记录各动作结果。宿主进程是否已经停止以及本机产物是否清理，另取 Daemon 回报。[共享撤销](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/runtime.go#L1153-L1208) · [取消时清理令牌](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/service/task.go#L888-L902) |

上游任务令牌在此路径绑定了工作区、Agent、运行任务、用户和到期时间。签发与普通评论接收链没有本项目的 Delegation Grant 版本、SOP 节点尝试及候选校验。平台应在受托报告进入 SOP 之前读取当前 Grant，校验该 Run 对指定 Issue、节点、候选和操作的权限，并把结果写入回执。普通跨 Issue 讨论继续使用原生协作权限。

## 实验结果

丙是任务发起人及验证 Agent 所有者，乙是 Runtime 所有者，只有乙拥有夹具工作区的所有者角色。D2 规定订单导出 C2 需要付款时间列。测试分别使用内建合成 JSON 和本阶段 Claude 宿主实验导出的 JSON 运行各一次。源 Issue 的评论保存输入文件的 SHA-256 和其中的付款时间检查结果，另一条 Issue 仅收到一般协调说明。

| 操作 | 实际结果 |
|---|---|
| 乙把 Runtime 共享给丙，领取丙的验证任务，按本次 dispatched_at 开工 | 三个 handler 均返回 200。测试使用 local 模式的 Runtime 与 Agent。数据库保存 task_token.user_id = 乙、任务 originator_user_id = 丙 |
| 验证 Agent 以真实任务令牌读取指定 Issue | 200，返回 D2 文字 |
| 向指定 Issue 提交 C2 报告摘要，随后向同一工作区里获准协作的另一 Issue 提交协调说明 | 两次均 201。两条记录分别属于各自目标 Issue，作者都是验证 Agent，source_task_id 相同 |
| 从源 Issue 的评论列表读取刚提交的宿主报告引用 | 200。读回文件 SHA-256 为 `fa62cdc8d28be2b59e735ce051d687b44f914c5b1b641d678da604a1c161c64b`，与原文件逐字节计算结果相同。付款时间核验为 `false`，原 Issue、Agent 作者、源任务均匹配 |
| 请求当前任务主体无权查看的私有项目 Issue | 404。Runtime 所有者的工作区角色未扩展本次 Agent 的项目可见范围 |
| 乙收回共享，随后检查运行状态和凭据 | 收回操作 200。任务状态 cancelled，Agent 解绑，查询到该任务仍有效的令牌行 0 条。丙随后读取 Runtime 用量得 404 |
| 撤销后使用原任务凭据再次读取原 Issue 并提交迟到报告 | 两次均 401，迟到报告写入数为 0 |
| 在共享仍有效且任务运行时，对照已到期夹具凭据和有效的 Claim 凭据 | 同一任务、同一目标 Issue，已到期凭据读取 401，有效凭据读取 200。夹具使用生产令牌生成器并在写入数据库时指定过去的到期时间 |

两次运行均通过同一组断言。运行管理操作由夹具提供已认证的所有者身份并调用生产 handler。Issue 读写使用 Claim 签发的任务令牌并经过生产认证中间件，数据保存于隔离 PostgreSQL。宿主实验先独立生成 JSON，然后集成测试将其哈希和付款时间结果提交为评论。服务端在此步骤确认作者、来源、目标与回读内容。本轮该字段核验失败，候选仍须补齐付款时间才能满足 D2。

## 复跑

在 Multica 固定版本的独立 checkout 中运行。准备 PostgreSQL 17 的空白临时数据库，将 DATABASE_URL 指向它。下面的 go test 临时目录位于 server 模块内，以便复用上游内部包。实验文件取自本项目的 prototypes/topic-03a/shared-runtime-identity_test.go。

```bash
set -eu
: "${MULTICA_CHECKOUT:?set to the pinned Multica checkout}"
: "${AGENTPLATFORM_CHECKOUT:?set to this design repository}"
: "${DATABASE_URL:?set to the disposable PostgreSQL database}"
cd "$MULTICA_CHECKOUT/server"
test "$(git rev-parse HEAD)" = fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc
go run ./cmd/migrate up
probe_dir=$(mktemp -d ./phase3probe.XXXXXXXX)
trap 'rm -f "$probe_dir/identity_test.go"; rmdir "$probe_dir"' EXIT
cp "$AGENTPLATFORM_CHECKOUT/prototypes/topic-03a/shared-runtime-identity_test.go" "$probe_dir/identity_test.go"
go test -p=1 -count=1 -v "$probe_dir"
# 可选，使用本轮或新一轮宿主实验保存的 JSON。
AP_CANDIDATE_REPORT=/absolute/path/to/claude-results.json go test -p=1 -count=1 -v "$probe_dir"
```
