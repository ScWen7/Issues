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

## 10. 第一阶段完成：Runtime / Daemon 注册、调度、领取与恢复

本节沿固定上游提交 fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc，追踪 Daemon 注册、服务端授权、批量 Claim、SQL 原子领取、Start generation、心跳、Runtime liveness、失联收敛和数据库测试。此处为实现与测试断言阅读结果；本轮没有运行 Multica 上游 Go 测试。

### 10.1 Runtime 的真实粒度：不是一台机器一条记录

源码：
- [Daemon 按 Workspace 注册 Runtime](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/daemon.go#L2923-L3052)
- [Builtin Runtime Upsert](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/runtime.sql#L33-L115)
- [Runtime 数据结构](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/types.go#L12-L120)

**代码事实：**
1. Daemon 是本机常驻管理进程，注册时携带 daemon_id、device_name、CLI 版本和一组本机可用 Runtime。
2. Runtime 注册按 Workspace 发生。同一 Host 上的 Codex 可以在多个 Workspace 分别形成 Runtime 实例；一个 Workspace 下也可以由同一 Daemon 注册多个内置 Provider 和自定义 Profile Runtime。
3. Builtin Runtime 的唯一性由 workspace + daemon + provider 约束；Custom Runtime 由 workspace + daemon + profile 约束。Runtime ID 是服务端分配的具体执行目标 ID。
4. 内置 CLI 先按机器探测，再批量用于各 Workspace 注册，避免多个 Workspace 重复启动 version probe。Profile 是 Workspace 级配置，命令路径在每台 Host 本地解析；Profile 只选择已有 Protocol Family。
5. 注册响应与本地 workspaceState 合并；运行时集合变化会通知 heartbeat loop 和 poller 更新 Runtime 集合。

**设计原因：** Host 的物理机器事实与 Workspace 中可被调度的 Runtime 实例不同。注册要把“机器上安装了什么”与“某 Workspace 获得了哪个执行目标”结合，同时避免重复探测。

**对本项目的启发：** 采用 Host / Daemon / Runtime Instance 三层关系。Host 表示机器或虚拟执行节点；Daemon 表示当前运行的管理进程及其连接身份；Runtime Instance 表示该 Host 在某 Workspace 下提供的具体 Provider / Profile 执行能力。Agent Role 不作为 Runtime 的同义词。Daemon 进程重启和 Runtime 实例重注册分别记录。

### 10.2 Claim 调度：机器批量领取，数据库逐 Agent 原子占用

源码：
- [Daemon 批量轮询与本地并发槽](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/daemon.go#L5519-L5658)
- [批量 Claim 服务流程](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/service/task.go#L4173-L4403)
- [单任务原子 Claim SQL](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/agent.sql#L770-L838)
- [批量候选 SQL](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/agent.sql#L2196-L2350)
- [批量 Claim Handler 与上限](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon.go#L2080-L2160)

**真实调度链：**
1. Daemon 维护本地并发槽 semaphore。每轮先拿至少一个空槽，再尽量取满其他空槽；本地无空槽时不请求服务端。
2. Daemon 把本机所有 Runtime ID 和空闲槽数量放进一次批量 Claim 请求。单次最多 32 个任务，避免无界响应和过长数据库事务。
3. 服务端先校验请求中的 daemon_id、Workspace、Runtime 所有权和 daemon 绑定，再对授权 Runtime 集合做一次批量候选查询。
4. 候选按 priority DESC、created_at ASC 排序；服务端按不同 Agent 去重，再逐 Agent 进入 claimTask 事务。
5. Claim SQL 在数据库中执行 FOR UPDATE SKIP LOCKED，将 queued 原子改成 dispatched，并写入 dispatched_at 与 prepare lease。同一 Issue + Agent 的活动执行互斥；不同 Agent 可以并行处理同一 Issue。
6. Claim 成功后，Handler 构造任务上下文并创建 task-scoped token；最终交付前再次读取并锁定 Runtime 和 Agent，重新核验 owner、runtime binding 与私有 Runtime sharing。Token 创建和交付凭据写入同一事务。
7. Handler 返回的每个 Task 带 Runtime ID，Daemon 按 Runtime 路由到本地执行槽。

**设计原因：** 机器级批量请求降低多 Runtime 的 HTTP / DB 往返；数据库仍以 Agent、Issue 和 Runtime 的真实约束做最终原子仲裁。服务端先列候选再逐 Agent Claim，使不同 Agent 可以并行，同时由 SKIP LOCKED 避免并发请求重复占用同一队列行。

**重要边界：** Batch Claim 的 max_tasks 是本次请求可接收的执行数量，不是 Agent 或 Runtime 的长期并发上限。长期容量由 Daemon 本地槽、Agent max_concurrent_tasks 和可选 Runtime max_concurrent_tasks 三层共同限制。

### 10.3 三层并发控制与资源竞争

源码：
- [Agent 与 Runtime 容量检查](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/service/task.go#L3684-L3853)
- [Runtime 容量 Advisory Lock](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/runtime.sql#L694-L727)
- [Agent 并发竞争数据库测试](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/service/task_claim_race_test.go#L22-L88)
- [Runtime 并发上限数据库测试](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/service/task_runtime_concurrency_db_test.go#L55-L306)
- [Runtime 上限修改与 Claim 锁同步测试](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/runtime_concurrency_test.go#L20-L134)

| 层次 | 控制者 | 约束对象 |
|---|---|---|
| Daemon 本地槽 | Host Daemon | 该 Daemon 同时启动的本地任务数 |
| Agent 并发上限 | Agent 配置 | 同一个 Agent 同时承接的任务数 |
| Runtime 并发上限 | Runtime 所有者配置 | 同一执行资源跨多个 Agent 的总活动任务数 |

Agent 容量检查在 Agent 行锁内完成。Runtime 容量使用事务级 Advisory Lock，锁定后才读取 Runtime 上限和活动任务数。容量更新也使用相同锁，保证修改上限返回后，不再有 Claim 按旧上限提交。选用 Advisory Lock 而非 Runtime 行锁，是为了避免 Claim 的 Agent → Runtime 锁顺序与 Runtime 修改 / teardown 的 Runtime → Agent 锁顺序形成死锁环。

上游测试覆盖两个并发 Claim 争一个 Agent 槽、多个 Agent 共享 Runtime 上限、Claim 等待容量锁、等待期间降低容量，以及多个并发 Claim 不超过 Runtime 上限。

### 10.4 Claim / Start generation 与丢失响应恢复

源码：
- [Claim 响应丢失重领 SQL](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/agent.sql#L892-L990)
- [Start claim generation 锁定 SQL](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/agent.sql#L970-L990)
- [StartTaskForClaim 事务](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/service/task.go#L4480-L4560)
- [Start 请求携带 runtime_id / dispatched_at](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon.go#L4674-L4794)
- [Start 丢失回执、重领代次、并发重放和取消竞争测试](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon_start_claim_test.go#L17-L213)

Claim 将任务从 queued 改为 dispatched，并写入 dispatched_at 和短期 prepare_lease_expires_at。Start 必须携带 task ID、Runtime ID 和本次 dispatched_at。服务端按三者锁定精确 Claim generation。同一 generation 的 Start 回执丢失后可以安全重放；已经 running 时返回同一个 started_at，不重复启动状态迁移。旧 generation 即使任务仍属于同一 Runtime，也会被拒绝。

Claim 成功但响应未送达时，90 秒 recovery window 之后，且 prepare lease 已过期，服务端刷新 dispatched_at 并重新交付。环境准备超过初始 45 秒时，Daemon 通过 ExtendTaskPrepareLease 延长租约，避免仍在准备的任务被误回收。Cancel、reclaim 和 Start 对同一任务行锁串行化，取消提交后，迟到 Start 会冲突退出。

**设计原因：** Runtime ID 只说明执行目标，不能识别同一任务的哪一次领取。dispatched_at 作为 generation token，使同 Runtime 重领、响应重放、取消和 Start 之间具备可比较的所有权版本。

### 10.5 Heartbeat、WebSocket 与 Runtime 在线状态

源码：
- [Daemon 每 Runtime 心跳循环与 WS fallback](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/daemon.go#L4545-L4680)
- [WS RuntimeLease 与连接生命周期](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemonws/hub.go#L23-L158)
- [WS 心跳帧处理](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemonws/hub.go#L1087-L1174)
- [批量 Heartbeat Scheduler](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/heartbeat_scheduler.go#L104-L325)
- [Redis Liveness Store 与 DB fallback](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/runtime_liveness_store.go#L13-L141)

**代码事实：**
1. Daemon 默认约每 15 秒为每个 Runtime 发送心跳；收到近期 WS heartbeat ack 时跳过重复 HTTP heartbeat，WS ack 连续缺失后 HTTP 自动恢复。
2. WS 握手时批量读取并校验固定 Runtime 集合，建立连接级 RuntimeLease。每次 WS 心跳复用这份授权快照，避免每 15 秒重新读取 Runtime 行；Runtime 被删除时通过 RuntimeGone 消息从连接范围剔除。
3. 生产 Heartbeat Scheduler 将 Runtime ID 合并，每 30 秒批量写一次 DB；Redis TTL 记录更近实时的 liveness。Redis 不可用时回退 DB heartbeat；批量写入遗漏项会进一步区分刚被明确下线、被 sweeper 竞争下线和已经删除。
4. RuntimeClaimFreshnessSeconds 为 150 秒，覆盖 60 秒 DB heartbeat flush、15 秒 Daemon heartbeat 和 30 秒 batch scheduler 的最坏组合，并留出余量。
5. Runtime Sweeper 每 30 秒运行。DB stale 候选还要经过 Redis liveness 过滤；Redis 不可用时按 DB stale window 工作。真正标记 offline 的 UPDATE 会再次核对 stale 条件，防止与刚到达的心跳竞争。
6. Runtime 先标记 offline，活动任务按 3 小时 reconnect grace 延迟失败，避免短期网络分区直接杀掉仍在本地运行的进程。Daemon 真正重启时则通过启动后的 RecoverOrphanedTasksForRuntime 主动报告，不等待 grace 到期。
7. 运行任务的 9000 秒 backstop 受 Runtime 心跳新鲜度约束，健康 Runtime 上的长任务不会仅因墙钟超时被扫掉；dispatched 的 300 秒 backstop则受 prepare lease 保护。

**设计原因：** 在线状态需要兼顾实时性、DB 写入成本和网络分区。Redis 提供短期活跃证明，DB 保存持久状态，连接级 Lease 减少 WS 热路径查询；任务终止与 Runtime 变 offline 分开，让网络抖动不等于本地进程已经死亡。

### 10.6 Daemon 重启、Runtime 删除与接管边界

源码：
- [Daemon RuntimeGone 去重与 Workspace 重注册](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/daemon.go#L1298-L1484)
- [Runtime 离线后的 reconnect grace sweeper](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/cmd/server/runtime_sweeper.go#L218-L395)
- [RecoverOrphanedTasksForRuntime 查询](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/agent.sql#L1239-L1287)

**两种故障路径：**
- 网络分区 / 心跳暂失：Runtime 先 offline，执行任务仍在 reconnect grace 内保留；Daemon 恢复心跳后 Runtime 回 online，原本地进程仍可能继续。
- Daemon 进程重启：新进程启动后主动调用 RecoverOrphanedTasksForRuntime，将上一个进程遗留的 dispatched / running 工作收敛为失败，再进入统一 HandleFailedTasks 流程决定是否安全重试。已启动的特定远端执行有额外 cleanup fence。

Runtime 被服务端删除时，Daemon 会从本地 Runtime 集合移除对应 ID，并对同一 Workspace 的并发 RuntimeGone 做去重与合并，随后重新注册剩余可用 Runtime。服务端暂时不可达和 Runtime 真实不存在分别处理，避免把一次 DB 故障误判成 Runtime 已删除。

### 10.7 Runtime 所有权与共享授权

源码：
- [Workspace、Daemon、Runtime Owner 三层校验](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon.go#L58-L160)
- [Runtime Owner / Shared With 判定](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/service/runtime_access.go#L12-L30)
- [Claim 最终交付事务与锁定重验](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon.go#L2440-L2540)
- [跨 Workspace、Ownerless Runtime 拒绝测试](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon_batch_claim_test.go#L231-L347)
- [Runtime 可见性撤销测试](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/runtime_visibility_revocation_test.go#L1-L260)

权限按用途分层：

| 层次 | 校验内容 |
|---|---|
| Workspace | 请求身份是否有该 Workspace 的访问权 |
| Daemon | daemon token 是否绑定请求中的 Daemon ID |
| Runtime Owner | user credential 是否为 Runtime Owner；daemon token 的 owner 是否与 Runtime 当前 owner 一致 |
| Private Runtime sharing | Agent Owner 是否为 Runtime Owner 或在 shared_with 范围内 |
| Task delivery | 交付前锁定 Runtime 和 Agent，重新校验 owner、visibility、runtime binding，再签发任务级 token |

Runtime 分享给其他成员只授予使用该执行资源的权限，不授予机器管理权限。Runtime Owner 缺失时不能签发任务级凭据，任务不会送到执行端。访问撤销会事务性取消受影响的活动任务并收敛关联的聊天输入、Session 指针和补充任务。

### 10.8 第一阶段结论

Multica 的 Runtime / Daemon 不是一个“机器在线列表 + 任务轮询器”，而是一套围绕执行资源身份、数据库原子派发、容量互斥、Claim generation、心跳租约、故障分类、授权复核和恢复收敛形成的执行控制机制。

对本项目的直接设计输入：

1. Host、Daemon、Runtime Instance 分开建模；Runtime Instance 按 Workspace 和 Provider / Profile 形成。
2. 以 Run 作为实际执行记录，派发需包含可比较的 Claim Generation；领取、准备、Start、进程启动和终态观察分别留证。
3. 资源调度同时考虑 Host 本地槽、Runtime 容量和执行者 / Agent 容量；容量更新与 Claim 使用同一互斥机制。
4. 所有入口最终进入同一派发服务；数据库原子占用是并发正确性的最终依据，通知与轮询只负责降低延迟。
5. Runtime 在线状态采用心跳租约与持久状态结合；短暂离线、进程退出、Daemon 重启和 Runtime 删除必须走不同恢复分支。
6. Claim / Start / Result 回报都要绑定 Claim Generation；旧执行者的迟到 Start 和结果只能归档，不能覆盖当前代次。
7. Workspace、Host / Daemon、Runtime Owner、共享授权和 Task Token 是不同权限层，最终交付时必须重新核验当前授权。

本阶段完成源码路径与代表测试断言追踪，未执行上游 Go 测试。下一阶段按 V0.2 顺序进入“宿主与本地交互入口”，重点比较中心派发、成员从 CLI / IDE 主动关联、事后补录，以及会话观察和真实用量归属。


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
