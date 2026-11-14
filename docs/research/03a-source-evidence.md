# 专题三 A · 执行平面源码研究记录

日期：2026-11-14  
本轮上游快照：[multica-ai/multica @ fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc](https://github.com/multica-ai/multica/tree/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc)  
本轮方式：读取远端仓库树、实现文件、官方项目文档及对应测试文件；本轮尚未在本地克隆运行上游测试。  
平台设计入口：[专题三 A：执行平面与宿主适配](../architecture/03a-execution-plane.md)

## 1. 已追踪的底层路径

| 研究主题 | 实际代码路径 | 初步发现 |
|---|---|---|
| Daemon / Runtime 身份 | `server/internal/daemon/types.go`、`daemon.go` Runtime 注册与运行时索引 | Daemon 是 Host 上的管理进程；Runtime 是 workspace 下的具体工具执行目标，provider 与 runtime profile 共同决定实际适配器 |
| Claim 与 Start 分离 | `server/internal/daemon/client.go` Claim / Start；`server/internal/handler/daemon.go` Claim / StartTask | Claim 先占用任务，Daemon 完成本地准备后再 Start；Start 绑定 runtime_id 与 dispatched_at，旧 claim 返回冲突 |
| 任务执行与终态 | `server/internal/daemon/daemon.go` handleTask / runTask / reportTaskResult；`client.go` Complete / Fail / Cancel Ack | Run 管理不止子进程生命周期，还包括进度、消息、Usage、会话 ID、工作目录、分支和清理确认 |
| 取消与恢复 | `daemon.go` watchTaskCancellation / handleTask；`handler/daemon.go` AckTaskCancelled / CancelTask；`task_lifecycle.go` RecoverOrphanedTasks | 取消采用服务端状态检查与本地进程中断配合；取消后仍需回传保留的工作目录、分支和会话处置结果 |
| Runtime / Agent 适配 | `server/pkg/agent/agent.go` Backend / Session / Result / New；`builtin_runtimes.go` ResolveBackend / NewRuntime | 多宿主通过统一 Backend 接口归一化，但底层协议和能力由各自 Adapter 实现；Runtime Identity 与 Protocol Family 分开 |
| Claude / Codex / OpenCode | `claude.go` Execute；`codex.go` Execute / executeOnce；`opencode_acp.go` ACP 与 run transport 选择 | 宿主协议差异显著：Claude 使用流式 CLI 交互，Codex 使用 App Server RPC，OpenCode 可按版本和配置选择 ACP / run |
| 执行环境准备 | `server/internal/daemon/execenv/execenv.go` Prepare / Reuse / Cleanup；`daemon.go` prepareExecutionEnvironment | 工作区准备与 Agent 启动分开；准备包含目录、上下文、技能、MCP、Provider Home 和本地配置 |
| Git Worktree | `execenv/local_worktree.go` PrepareLocalWorktree / Finalize / Discard | 通过快照用户未提交改动、创建独立 Worktree、跨轮次分支归属和冲突重放实现 Git 场景隔离与交付 |
| 资源授权 | `handler/daemon.go` daemonRuntimeBindingAllowed / requireDaemonRuntimeAuthorized；`agent.go` Task-scoped token | Workspace 访问、Runtime 所有者、Daemon 身份和 Agent 执行凭证是不同授权层次 |
| Runtime Profile | `daemon.go` registerRuntimesForWorkspace；`agent.go` Config.LaunchPrefix / BuiltinRuntime | 自定义 Runtime Profile 复用已支持的协议族，固定命令和参数；不等于随意支持任意 Agent 协议 |

## 2. 关键源码证据

### 2.1 Daemon、Runtime 与任务领取

- [Runtime / Task 数据结构](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/types.go#L12-L120)
- [Daemon ClaimTasks 客户端](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/client.go#L230-L370)
- [WS RPC 优先领取](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/wsrpc.go#L315-L387)
- [服务端批量领取](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon.go#L2100-L2380)
- [StartTask 绑定 claim generation](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon.go#L4674-L4794)
- [Runtime / Daemon 官方说明](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/apps/docs/content/docs/daemon-runtimes.mdx#L12-L23)

### 2.2 本地执行生命周期

- [handleTask：本地领取后生命周期、取消监听与终态回报](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/daemon.go#L5834-L6140)
- [runTask：身份校验、Runtime Profile 解析和准备流程](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/daemon.go#L7986-L8370)
- [runTask：Provider Backend 构造与执行参数](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/daemon.go#L8811-L9100)
- [任务会话、工作目录与结果回报客户端](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/client.go#L483-L828)
- [Daemon 取消确认与进程清理测试](https://github.com/multica-ai/multica/tree/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler)

### 2.3 Provider Adapter

- [统一 Backend / Session / Message / Result 契约](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/agent.go#L18-L120)
- [Session 的流式消息、补充指令与终态能力](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/agent.go#L194-L248)
- [Backend 工厂与 Provider 路由](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/agent.go#L449-L574)
- [Runtime Identity 与 Protocol Family 映射](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/builtin_runtimes.go#L18-L204)
- [Claude CLI 适配入口](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/claude.go#L56-L180)
- [Codex Backend 重试与 Session 包装](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/codex.go#L956-L1082)
- [OpenCode ACP 选择逻辑](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/opencode_acp.go#L97-L180)
- [OpenCode ACP 执行入口](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/opencode_acp.go#L300-L430)

### 2.4 工作区与隔离

- [PrepareParams：Local Directory / Local Worktree 等输入](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/execenv/execenv.go#L39-L130)
- [Prepare：目录、工作区与 Provider 环境初始化](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/execenv/execenv.go#L422-L768)
- [Reuse：已有工作区与上下文刷新](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/execenv/execenv.go#L827-L910)
- [Environment Cleanup 与 EnvRoot Claim](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/execenv/execenv.go#L1277-L1410)
- [Worktree Prepare：快照用户状态并建立隔离副本](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/execenv/local_worktree.go#L314-L425)
- [Worktree Finalize：交付、保留和冲突处理](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/execenv/local_worktree.go#L563-L670)
- [Worktree 测试矩阵](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/execenv/local_worktree_test.go)

### 2.5 安全与授权

- [Runtime 所有者与 Daemon 绑定校验](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon.go#L70-L160)
- [Daemon 取消确认及保留工作结果](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon.go#L5985-L6070)
- [本地 Runtime Profile 官方说明](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/apps/docs/content/docs/daemon-runtimes.mdx#L191-L235)

## 3. 已识别的设计动机与本项目启发

### 3.1 为什么 Claim 与 Start 分离

本地准备可能包含仓库、工作目录、技能包、MCP、Provider Home 和上下文文件等步骤。若领取即标记 running，工作台和其他消费者可能读取一个尚未准备完成的工作目录。Multica 因此在本地准备后才调用 StartTask；Start 又绑定 runtime_id 与 dispatched_at，防止过期领取者启动已经转交的任务。

**本项目启发：** Run 生命周期至少需要区分领取、准备、实际启动和终态回报；SOP 节点的 ready 不能直接当作 Agent 已开工。

### 3.2 为什么 Runtime 和 Protocol Family 分离

Runtime 是具体可调度的工具身份；Protocol Family 是适配器实现的通信协议族。Multica 的 Runtime Profile 选择一个已支持的协议族，再提供命令与固定参数。自定义命令复用已有协议，不会自动获得新协议能力。

**本项目启发：** Runtime Identity、Host、Provider Adapter 和 Agent Role 应分别建模。不能把“能执行某个命令”当作“已支持这个 Agent”。

### 3.3 为什么 Backend 统一、底层协议不统一

平台统一 Backend.Execute 与 Session.Messages / Result，使 Daemon 不需要理解每个工具的协议细节；每个 Provider Adapter 负责启动参数、传输协议、事件解析、会话恢复、取消和 Usage。Claude、Codex 和 OpenCode 的实现证明其协议差异远大于命令行参数差异。

**本项目启发：** 平台应统一生命周期和结构化执行结果，不强制所有宿主使用 ACP 或 JSON-RPC。适配能力需要显式声明和验证。

### 3.4 为什么本地工作区需要独立生命周期

Prepare / Reuse 处理工作目录、Provider 配置、技能、MCP、会话数据和清理；EnvRoot Claim 防止同一目录被并发复用；GC 需要读取归属和工作状态后才能回收。Worktree 进一步保存用户未提交改动快照、跨轮次分支状态和冲突信息。

**本项目启发：** Workspace 是执行资源，有自己的准备、占用、交接、清理和恢复生命周期。代码副本策略只是 Workspace Adapter 的一种实现。

### 3.5 取消确认与资源复用的适用范围

当前取消清理确认按 Provider 能力协商生效：`pi / omp / museapp` 在 Start 时声明对应能力，取消后记录待确认状态。服务端的等待及清理失败保护按同一 Agent 与 Runtime 关联；EnvRoot 锁另负责本地目录的运行期互斥。两项机制分别回答“这条执行链能否继续”和“这个本地目录是否正在被占用”。

**源码补充：** 对该清理确认路径，Cancel Ack 缺少所需确认或报告 `cleanup_unconfirmed` 时，会调用专项失败收敛，将原 `cancelled` 更新为 `failed`。常规完成回报的状态条件保护与这条专项路径分别记录，取消事实、清理原因及恢复材料继续关联同一工作。

证据：[能力协商](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/daemon.go#L8753-L8759)、[清理确认回报](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/daemon.go#L6147-L6151)、[同 Agent / Runtime 匹配](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/task_cleanup.sql#L15-L20)、[等待确认条件](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/task_cleanup.sql#L50-L93)、[取消确认异常入口](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon.go#L6067-L6079)、[专项状态更新](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/task_cleanup.sql#L37-L48)、[Provider 差异与收敛断言](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon_process_cleanup_test.go#L115-L177)。

**本项目启发：** 分别观察 Stop 请求、宿主结果、进程退出、资源占用、清理结论及持久化回执。3A 的能力矩阵按宿主及版本标明原生覆盖，专题一的复用说明同步采用这组事实。

## 4. 后续研究与验证清单

已有静态追踪记录在第 2、5、7 节，下一轮围绕下列问题补齐调用链、宿主覆盖和运行验证，再收敛 3A 设计：

1. Runtime 注册、Profile 解析、在线状态、心跳、批量 Claim 和队列公平性：`daemon.go` 注册路径、`handler/daemon.go` Claim、`task_claim_decision.go`、相关 SQL。
2. 进程树管理、OS 差异、优雅停止、停止回执与重启恢复：`processtree`、`shutdown.go`、`daemon_process_cleanup_test.go`、`shutdown_retry_test.go`。
3. Session 与工作区连续性：PriorSessionID / PriorWorkDir 的服务端选择、Provider ResumeRejected、会话文件 / 账号绑定、工作区复用和跨 Runtime 接续。
4. 隔离与授权：本地文件系统隔离、Codex sandbox、进程环境继承、Task-scoped Token、Runtime 所有者授权和跨成员共享。
5. 多平台适配：Windows / macOS / Linux 的命令启动、进程树、路径、临时目录和 Worktree 行为。
6. Script 执行：当前受管命令、Environment Command 与 Run 之间的真实边界，确认是复用现有执行器还是增加独立 Script Executor。
7. 对照宿主官方协议文档与上游测试，验证各 Provider 的能力矩阵和版本兼容策略。
8. 本地主动交互与事后关联：对照 Multica 会话关联和 TeamAI skill driver / agent observation，明确实际执行段、身份、选定共享、重复观察和用量来源。
9. 上下文注入与加载证据：以 `context_receipt.go`、`execenv/context.go` 和各宿主 Skill / Rule / MCP 入口建立通道矩阵，分别验证投递、读取、使用及加载探测的适用版本。
10. 结构化节点回报：对照原始宿主结果、显式结构化提交、具名制品及候选，研究 Adapter、Daemon、控制平面与 SOP 的职责分配。
11. 任务身份与平台个人凭据：追踪 task token、marker、CLI 配置回退和实际文件访问；把模型服务登录态与平台操作凭据按用途区分。
12. 权威终态与恢复拒绝：对照 TerminalObserved、永久 / 暂时恢复拒绝、兼容性回退及工具观测，验证各宿主的结果保留、重试与收尾行为。

本记录是源码探索阶段材料，不作为最终平台架构结论。


## 5. 第二轮追踪：注册、授权、心跳、隔离与测试反例

### 5.1 Runtime 注册与配置漂移

- [Daemon Runtime 探测与注册](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/daemon.go#L2923-L3238)
- [Runtime Profile 测试](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/runtime_profile_test.go#L205-L545)
- [服务端注册与 Runtime Upsert](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon.go#L448-L572)
- [Runtime 所有者 / Daemon 身份授权](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon.go#L58-L227)
- [心跳与在线状态更新](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon.go#L1483-L1605)

**源码观察：**

1. Daemon 先在机器级探测本地 CLI，再按 Workspace 注册 Runtime；自定义 Runtime Profile 是 Workspace 配置，但由每台机器本地解析命令路径，只有命令在该 Host 可用的机器才注册对应 Runtime。
2. Profile 只选择已支持的 Protocol Family，并配置 command / fixed args。命令行包装器可以复用现有协议族；协议不兼容的工具需要新的 Adapter。
3. Runtime 注册有配置漂移收敛：profile 列表签名变化触发重新注册；本地 CLI 不可用、版本探测失败和确认不可执行的处理不同，避免一次探测故障就把正在运行的 Runtime 全部下线。
4. Runtime 授权至少分 Workspace、Daemon ID、Runtime Owner 三层。Workspace 成员身份本身不足以领取其他成员机器的任务；daemon token 与特定 Daemon 和 Owner 绑定。

### 5.2 Claim / Start / Heartbeat 的控制链

- [Claim 与 Start 入口](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon.go#L2100-L2455)
- [StartTask claim generation 校验](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon.go#L4674-L4794)
- [Runtime heartbeat 与授权校验](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon.go#L1483-L1605)
- [Claim 决策原因分类](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/service/task_claim_decision.go#L41-L192)

**源码观察：** Claim 响应有交付截止和失败重排；Start 使用 Runtime ID + dispatched_at 识别具体 claim generation；Heartbeat 同时承载在线状态和服务端发给 Runtime 的待处理命令。三者分别回答“拿到工作”“当前领取者仍有权开始”“执行资源仍在线”。

### 5.3 进程树停止与执行准备隔离

- [进程树统一控制入口](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/processtree/run.go#L19-L93)
- [Unix 进程组 interrupt / stop / finish](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/processtree/controller_unix.go#L17-L88)
- [执行环境准备的隔离 helper](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/execenv/isolation.go#L109-L222)
- [EnvRoot Claim 与复用锁](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/execenv/execenv.go#L1277-L1453)
- [取消回执与清理状态持久化](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon.go#L5985-L6070)

**源码观察：**

1. 进程管理按进程树而非只杀根 PID 设计；Unix 使用进程组执行 interrupt / stop / finish，其他平台有对应控制器实现。
2. 执行环境准备可以放到短生命周期 helper 中隔离；EnvRoot 的运行期锁由 Daemon 父进程持有，因为 helper 退出会释放 OS 文件锁。
3. Cancel Ack 保存 branch / durable workdir / preserved-work error / retired session 等恢复指针；普通回执更新带幂等及状态条件，所需清理确认缺失时按第 3.5 节专项收敛。
4. 停止请求、进程树已结束、资源可复用、终态回执已持久化分别记录。Provider 协商决定清理确认路径，EnvRoot 锁决定本地目录占用保护。

### 5.4 Worktree 测试所揭示的设计目的

- [Worktree 测试：用户未提交变更快照、基线和交付](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/execenv/local_worktree_test.go#L178-L425)
- [Worktree 测试：跨轮次继续、用户并行修改与冲突](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/execenv/local_worktree_test.go#L834-L1200)
- [Worktree 测试：忙分支、重派和分支归属](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/execenv/local_worktree_test.go#L1504-L1710)
- [Worktree 测试：拒绝错误交付点和基线回退](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/execenv/local_worktree_test.go#L1899-L2249)

**源码观察：** Worktree 的核心目标不是简单地创建一个 Git 分支，而是确保 Agent 看到的输入与用户当前工作状态一致、Agent 输出可单独审查、用户本地工作树不被改写、多个并行执行互不污染、跨轮次执行可识别同一工作分支，并且冲突或交付点异常时保留可恢复现场。

### 5.5 当前已读测试范围

本轮定位并阅读了以下测试用例与断言片段；尚未运行这些上游测试：

| 测试文件 | 重点场景 |
|---|---|
| `runtime_profile_test.go` | Profile 命令解析、协议族兼容、命令缺失与路径覆盖 |
| `local_worktree_test.go` | 用户 WIP 快照、并行 Worktree、跨轮次分支、冲突与交付验证 |
| `execenv_test.go` | EnvRoot 身份、并发 claim、上下文注入、Provider Home、安全配置 |
| `daemon_batch_claim_recovery_test.go` | Claim 响应超时、重投、领取代次和恢复 |
| `daemon_start_claim_test.go` | 旧 claim 与新 claim 的 Start 竞争 |
| `daemon_process_cleanup_test.go` | 进程清理未确认时的任务恢复 |
| `shutdown_retry_test.go` / `shutdown_test.go` | Daemon 关闭、运行任务清理与回报 |
| `runtime_visibility_revocation_test.go` / `runtime_ownership_test.go` | Runtime 共享、撤销和所有者权限 |

## 6. 第二轮研究后的设计判断

- **Runtime 注册属于能力发现与授权绑定，不是单纯心跳登记。** 需要记录 Host、Runtime Profile、协议族、命令版本、能力和所有者。
- **统一 Backend 契约应覆盖完整交互生命周期。** 至少包括 Start、Message Stream、Tool Activity、Supplement、Cancel、Terminal Result、Usage、Session Resume 和 Cleanup；每项能力需可选并显式报告。
- **Execution Environment 应独立于 Provider Adapter。** Workspace 准备、代码获取、上下文和技能注入不应全部散落在各宿主适配器中。
- **Git Worktree 只是一种可选代码隔离 / 交付策略。** 平台还要研究非 Git 目录、压缩包、Artifact 和远端 Workspace 的策略。
- **停止确认与资源回收分别记录能力和事实。** Adapter 报告宿主结果，Host Daemon 管理本地进程与资源，服务端按实际协商和回执处理后继执行；平台通用策略结合能力矩阵与原型结果收敛。


## 7. 新增追踪：上下文、凭据与会话结果

以下核对沿用本记录的固定提交，证据为公开实现与测试断言阅读。代表路径用于补齐探索输入，各宿主的真实运行覆盖由下一轮能力矩阵验证。

### 7.1 ContextReceipt 的生成时机与证据等级

Daemon 在 Backend 执行前构造并上报 ContextReceipt，用于保留启动即失败时的材料与通道信息。回执描述本轮交付清单；当前宿主实际接收、读取和采用需对应实际观测。[生成时机](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/daemon.go#L9206-L9245)

| 源码等级 | 记录的依据 |
|---|---|
| delivered | 本轮通过输入请求或内联内容提供材料的通道 |
| verified | 文件投递方式有对应宿主版本的既有加载探测 |
| verified_other_version | 当前运行版本与已探测版本不同，或当前运行版本未知 |
| unverified | 材料已物化，加载发现尚缺探测依据 |
| not_delivered | 本轮材料未交付，包括没有适用通道或文件写入失败 |

文件型等级按探测表与版本匹配计算；自定义 Runtime 单独标记其观测等级。Skill 可用回执使用 file / unverified；MCP 回执列出配置名，连接和调用结果另行观察。回执上报失败记录日志，因此回执缺失也需作为采集覆盖状态保留。[等级定义](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/context_receipt.go#L37-L59)、[版本探测](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/context_receipt.go#L93-L120)、[Skill 与 MCP 回执](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/context_receipt.go#L231-L281)

### 7.2 两个宿主的实际注入路径

| 材料 | Claude | Codex |
|---|---|---|
| Agent 指令与仓库规则 | Agent 指令随 runtime brief 写入 CLAUDE.md 受管区块，既有仓库规则保留在区块外 | Agent 指令随 runtime brief 写入 AGENTS.md 受管区块，既有仓库规则保留在区块外 |
| Skill | 写入工作目录下的 .claude/skills | 写入本次任务 CODEX_HOME 下的 skills |
| MCP | 构造配置并通过 CLI 参数提供，受管配置采用对应限制选项 | 写入任务 CODEX_HOME/config.toml，受管配置按代码清理继承项 |

对应入口：[指令受管区块](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/execenv/runtime_config.go#L161-L225)、[Claude Skill 物化](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/execenv/context.go#L161-L183)、[Skill 路径](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/execenv/context.go#L332-L341)、[Codex Skill 物化](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/execenv/execenv.go#L1087-L1125)、[Claude MCP](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/claude.go#L74-L88)、[Codex MCP](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/codex.go#L619-L684)。

这些是原生交付路径。平台独立的 Rule 资源选择、作用域和冲突治理由 3B 设计；3A 验证选定内容如何进入指定宿主以及实际回执的证据强度。

### 7.3 任务令牌、CLI 配置根与 marker

Daemon 检查并注入任务 token 和任务配置根。CLI 优先读取显式任务 token；识别到任务上下文而 token 缺失时，返回缺失结果。创建 API client 时进一步检查 `mat_` 前缀；服务端有效性、绑定和 scope 校验另行追踪。默认及命名 profile 路径可统一重定向到任务目录。[Daemon 身份注入](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/daemon.go#L171-L197)、[CLI token 解析](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/cmd/multica/cmd_auth.go#L74-L87)、[任务客户端身份检查](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/cmd/multica/cmd_agent.go#L258-L287)、[任务配置根](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/cli/config.go#L235-L299)

CLI 还从 cwd 向父目录查找受管 marker。根 marker 覆盖任务环境变量全部丢失、工作目录移到父级但仍在 workspaces tree 的路径；写入失败按现有实现记录警告并继续。所有任务信号都消失且 cwd 已离开 marker 祖先覆盖范围时，依据判定式会进入普通 profile 解析，这是后续需要验证的场景。[marker 查找](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/cmd/multica/cmd_agent.go#L449-L486)、[根 marker 建立](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/execenv/context.go#L33-L118)、[初始化失败的处理](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/execenv/execenv.go#L444-L452)、[移到父目录的测试断言](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/cmd/multica/cmd_agent_test.go#L246-L303)

此机制保护 CLI 的平台身份解析。原生实现刻意保留 HOME / XDG，供其他工具使用 Daemon 所在操作系统用户的已有状态；平台成员、Runtime Owner 与 OS 用户分别识别。同 UID 文件访问、宿主 sandbox、外部工具凭据和平台任务授权分别研究。[环境保留说明](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/daemon.go#L8895-L8899)

### 7.4 TerminalObserved 与结果交接

Backend 可在读取到单次宿主调用的权威终态后，通过 TerminalObserved 报告该事实；契约要求在可能阻塞的清理以及最终 Result 发送前发布，成功与失败都适用。该能力用于保留宿主结果与清理过程的区别。[Session 契约](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/agent.go#L228-L244)

Cursor 在协议 result 事件后先标记已观察终态再关闭后台执行；Pi 保留已经读到的 provider error。Daemon 的 watchdog 检查终态观察；取消先到达时，对提供此能力的 Backend 给定 Result 交接时间，再判断实际结果。当前交接预算为 30 秒，未提供能力的 Backend 使用原有取消和 watchdog 路径。[Cursor 实现](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/cursor.go#L270-L298)、[Daemon 交接及结果分类](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/daemon.go#L10379-L10546)、[watchdog 检查](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/daemon.go#L10647-L10690)、[终态交接对照测试](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/cursor_terminal_boundary_test.go#L220-L293)

平台探索需对照已读成功、已读失败、尚无终态、提供能力和未提供能力的路径。宿主调用结果、受管 Run 最终回报、业务验收和资源释放分别记录。

### 7.5 恢复拒绝与新会话重试的真实条件

原生区分永久恢复拒绝与暂时占用拒绝，二者对旧 Session 的后续资格处理不同。`shouldRetryWithFreshSession` 首先要求执行失败、存在 prior SessionID 且已观察到的 `tool-use` 次数为 0；再检查明确拒绝、共同错误识别或受限兼容分支。[拒绝类型](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/agent.go#L308-L343)、[重试判定](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/daemon.go#L9631-L9716)

`resumeRejectionUndetectable` 列出缺少明确拒绝信号的兼容 Provider。显式拒绝及共同错误识别先行判断；剩余情况仅对表内 Provider、空结果 SessionID 和适用错误类型尝试兼容回退。未知 Provider 默认跳过猜测分支。该计数只统计已观察到的 `tool-use`，实际副作用仍需结合来源核实。[能力表](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/agent.go#L458-L485)、[错误类型筛选](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/daemon.go#L9814-L9844)

fresh fallback 在该原生分支中执行一次，并重新构造冷启动上下文；永久拒绝退休旧会话，暂时拒绝保留旧会话资格，两次用量合并。本轮平台 Run 的最终报告发生在这段内部恢复之后。[执行与上下文重建](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/daemon.go#L9255-L9330)、[结果及用量合并](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/daemon.go#L9797-L9811)、[忙会话恢复断言](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/pi_busy_retry_unix_test.go#L24-L100)

3A 的下一轮矩阵应分别覆盖明确拒绝与兼容判断、永久与暂时拒绝、有无工具事件、新旧会话 ID、原始失败和重试结果。具体重放策略结合宿主版本及工作副作用确定。
