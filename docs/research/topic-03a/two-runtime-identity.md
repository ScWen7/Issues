# A 离线之后，谁能启动 B，谁能提交结果

订单导出的验证 Issue 同时发生了两件事。A 的验证者已得到 C1 返工报告，回传时遇到断线。B 的成员随后在同一 Issue 中点名自己的验证 Agent，B 领取新任务并先交回 C2 通过报告。恢复连接后，A 把之前落盘的 C1 回报给中心。Multica 接受原任务仍在运行的迟到结果，按任务保留两份报告。AgentPlatform 需要用此前登记的节点尝试判定哪一个结果可推进订单验收。[集成探针](../../../prototypes/topic-03a/two-runtime/handoff_test.go) · [已有结果接纳实验](../../../prototypes/topic-03a/result-admission/test_admission.py)

## 实测经过

使用 Multica `fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc`、Go 1.26.9、PostgreSQL 17.5 和已执行 657 号迁移的临时数据库。A、B 各有一个真实 Daemon 实例、一个本地 Runtime、独立的机器凭据、配置和工作目录。A 的机器所有者只把 Runtime 共享给验证者 V。A 这条线由 V 点名 V 的 Agent，B 这条线由普通成员 B 点名自己的 Agent。HTTP 凭据由夹具生成，领取任务时的任务令牌由实际 claim handler 签发。数据库逐条核对机器、Agent、任务令牌绑定用户及触发评论的作者。A 的机器所有者在断线前通过成员凭据把 C2 东区工作簿上传到目标 Issue，并以相同字节另行上传到私有项目 Issue，形成两次独立交付。[成员点名分派](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/comment.go#L2608-L2668) · [领取与签发任务身份](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon.go#L4389-L4453)

| 顺序 | 发生的动作 | 服务端与客户端的实测结果 |
|---|---|---|
| 1 | A 领取 C1，启动任务，回报前断开本实例的 HTTP 传输 | 原生终态队列先持久化 C1。服务端仍记录 running，成功输出为空，源评论 0 条 |
| 2 | 把 A 的最后心跳调到 2 分钟前，用原生条件更新把它标为 offline，再执行设置为 20 分钟宽限的清理 | C1 继续 running。B 用自己的机器凭据领取，队列为空 |
| 3 | 成员 B 在目标 Issue 点名自己的 Agent | 服务端新建一条来源为该评论的任务。B 的机器领取并开工，任务 ID、凭据均区别于 A。B 用该任务凭据读取已交付文件 |
| 4 | B 通过原生终态回报交回 C2 | 数据库为 completed，输出为 C2 原报告文本，出现 1 条关联该任务及 Agent 的评论。A 此时仍是 running |
| 5 | 用 A 的原配置、原凭据新建 Daemon 实例，上报心跳并回放磁盘队列，再把相同完成请求发送一次 | 队列从 1 份到 0 份。原 A 任务 completed，保留 C1；原 B 任务 completed，保留 C2。两次快照中两条任务各有 1 条源评论 |
| 6 | 另起 A 对照任务，断线暂存结果后，A 的资源所有者撤回对 V 的共享 | 撤回 200，旧任务凭据读取目标 Issue 为 401。恢复连接后机器回报得到确认并清理待发队列。原任务保持 cancelled，输出为空，新增源评论 0 条，B 的 C2 未变 |
| 7 | 另起 B 对照任务，暂存报告，将最后心跳调到 21 分钟前；调用相同 20 分钟宽限清理及失败处理 | 原任务 failed，原因为 runtime_offline。同一 Agent 产生带父任务及重试来源的 deferred 第 2 次尝试。恢复连接后机器的迟到回报获确认，原任务保持 failed，输出为空，源评论仍为 0。C2 原任务保持 completed |

*注*　宽限数值由本实验设置。测试用过期的心跳时间执行生产 SQL 与 TaskService 的清理、后续失败处理，轮询时钟和实际断开 21 分钟的网络属于部署观测。两份报告来自同一订单夹具的 C1/C2 工作副本，测试只裁去文件外围空白再与数据库文本逐字比较。[离线与宽限 SQL](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/runtime.sql#L281-L325) · [后台清理入口](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/cmd/server/runtime_sweeper.go#L304-L328) · [失败后派生重试](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/service/task.go#L5813-L5903)

## B 读取的究竟是哪一份

B 的独立 Python 子进程经本机 HTTP 向活动中的生产认证中间件与 handler 发出六个请求。子进程只得到 B 本次任务的短期凭据和夹具对象标识。对照中的两份文件同名、同字节，附件 ID 和所属 Issue 各自独立。A 的所有者在 B 读取前通过相同下载接口确认私有附件可取。[接收端脚本](../../../prototypes/topic-03a/machine-handoff/identity_read.py) · [任务身份绑定](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/middleware/auth.go#L101-L146)

| B 的任务凭据访问 | HTTP | 验证 |
|---|---:|---|
| 当前订单验证 Issue | 200 | 可读取目标 |
| 私有项目中的对照 Issue | 404 | 不向 B 返回对照 Issue |
| 挂在目标 Issue 的东区工作簿 | 200 | 收到 5,494 字节，ZIP 校验通过，包含工作簿结构 |
| 同名、同摘要的私有 Issue 附件 | 404 | 不向 B 交付这一次发布的内容 |
| A 只共享给 V 的 Runtime 用量 | 404 | B 读取 A 的 Runtime 用量得到 404 |
| B 自己的 Runtime 用量 | 200 | B 可读取自己 Runtime 的用量 |

下载字节的 SHA-256 为 `5784c6c9f6660ac89a3bd4188541f5bfaee85b2e21a39b47a55923983380e852`。下载处理从附件记录解析工作区，再调用归属 Issue 的可见性检查。机器用量走另一条 Runtime 读取授权。两种资源可以自然给同一主体不同答案。产品可用内容摘要校验字节，以本次交付记录、目标 Issue 和当前可见性决定是否向成员提供下载。[附件加载与下载](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/file.go#L884-L946) · [附件归属对象权限](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/project_access.go#L255-L273) · [Runtime 读取](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/runtime.go#L873-L904)

## AgentPlatform 的接续决定

1. **谁启动 B。** 案例中，成员 B 主动点名 B 的验证 Agent。原生离线处理先保留 A，在逾期对照中为原 Agent 排入重试。若产品将接续改为自动执行，由专题二已授权的 SOP 运行控制器作出决定，检查当前节点、候选、Grant 和可用执行资源，登记 B 的新 Run、节点尝试和发起依据。A 的心跳变化可以提示需要处理；谁接受工作、依据哪条授权，应能在 Issue 上查到。
2. **怎样保留迟到结果。** A 的本地终态队列按服务端、profile 和机器标识分开，重启后继续投递原任务。服务端对 running 到 completed 做条件更新，重复请求读出现有终态。给成员看的结果应展示原 Run、独立回执和最终处置。C1 仍有效时归入历史尝试；撤销或超时后的响应按服务器原有终态记录。C2 只有在当前节点、候选身份、Grant 和所需制品全部符合时才由 SOP 消费。[本地队列分区](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/terminal_report_queue.go#L94-L113) · [先落盘后发送](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/daemon.go#L6539-L6586) · [回放](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/terminal_report_queue.go#L703-L753) · [终态写入](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/agent.sql#L1028-L1050) · [已有终态回执](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon.go#L4973-L4993)
3. **向 B 交付什么。** B 用自己的身份取得已登记目标、批准公开的输入和可复核制品引用。A 主机上尚未发布的文件、其宿主会话和待发队列仍归 A。此处已经实测独立进程的 HTTP 授权与读回。两套 Daemon 驱动和 HTTP 中心运行在同一个 Go 测试进程，独立 Python 接收端与中心共用内核及网络、进程、挂载命名空间；本探针直接回报已有订单验证产物，未再次启动模型或订单导出器。另见[上一阶段宿主到结果的实测](result-handoff.md)。

## 两台 GitHub 托管虚拟机上的原生授权与回放

中心作业所在虚拟机运行临时 PostgreSQL、仅监听回环的 Multica HTTP 中心，以及 A、B 两套 Daemon 对象。A 暂存 C1 后，成员 B 点名自己的 Agent，B 的 Daemon 领取新任务。接收作业在第二台虚拟机生成临时密钥，解封本次 B 的任务凭据，用它构造六个 GET 请求。两个作业通过本次运行的私有 Actions 制品交换密封信封。中心侧夹具只转发预期的六个固定路径，把认证和逐项可见性判断交给原生中间件及 handler，再将实际响应状态与主体传回接收机。接收机比对带本次挑战的内核启动摘要，验证两台虚拟机具有不同启动实例；它取得目标 Issue、已发布 XLSX 及 B 的机器用量（三项 200），访问私有 Issue、同字节私有附件及 A 的机器用量时取得三项 404。它在自己的磁盘上读取固定 C2 报告，用报告核实工作簿的 5,494 字节、SHA-256 和 ZIP 结构，再把 C2 报告原文密封送回。中心上的 B Daemon 把收到的原文交给生产完成入口，随后 A 才重放并重复发送 C1；两项输出仍各属原任务、各有 1 条源评论。此轮覆盖跨虚拟机的接收者和真实权限决策；Daemon 的中心回调与 A 的重放均发生在第一台虚拟机。[远端运行与两份作业日志](https://github.com/ScWen7/Issues/actions/runs/43621447364) · [交换夹具](../../../prototypes/topic-03a/native-runner/exchange.py) · [原生集成探针](../../../prototypes/topic-03a/two-runtime/handoff_test.go)

远端复跑可在 GitHub Actions 选择 **AgentPlatform native cross-VM handoff** 并运行当前版本。工作流会创建两台新的 Ubuntu 虚拟机，使用固定 Multica 提交并运行完整迁移；五个跨作业制品分别含 B 的临时公钥、密封的身份交接、请求、响应和 B 的回执。本轮身份只对应临时库。接收作业输出六项 HTTP 状态、工作簿长度、摘要、C2 核验和 `distinct_boots`，中心作业输出 B 回报、A 的两次投递以及撤销与超时对照。下节命令复跑日常单机基线。[跨虚拟机工作流](../../../.github/workflows/agentplatform-native-vm.yml)

## 复跑

在 Linux 上准备固定版本的 Multica 和一个已迁移的临时 PostgreSQL 数据库，设置 `MULTICA_CHECKOUT`、`DATABASE_URL`。在 AgentPlatform 仓库根目录执行以下命令。第一行建立新的临时父目录，订单脚本会创建其中的 `orders`。

```bash
work=$(mktemp -d)
python3 prototypes/topic-03a/order-export/run.py "$work/orders"
python3 prototypes/topic-03a/two-runtime/run.py "$MULTICA_CHECKOUT" "$work/orders"
```

订单生成依赖 Python 的 XlsxWriter 与 openpyxl。运行器通过 Go overlay 把单份测试装入固定版本的 daemon 包，同时排除该包不相关的上游测试单元；生产源文件使用原件。测试写入临时数据库，结束时清除本次的本机凭据交换文件。HTTP 回传保留摘要和状态码。[运行器](../../../prototypes/topic-03a/two-runtime/run.py)
