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

### 3.5 为什么取消不等于杀进程

取消需要经过宿主适配器的中断路径、进程树清理和最终确认；若进程清理没有确认，平台会阻止后续任务直接复用同一执行资源，防止旧进程与新任务同时写入。

**本项目启发：** Stop 请求、进程已退出、资源已释放、取消结果已持久化是不同事实。平台需要等待停止回执，并为清理未知状态保留恢复流程。

## 4. 本轮尚未完成的源码研究

下一轮继续追踪以下实现与测试，完成后再收敛 3A 设计：

1. Runtime 注册、Profile 解析、在线状态、心跳、批量 Claim 和队列公平性：`daemon.go` 注册路径、`handler/daemon.go` Claim、`task_claim_decision.go`、相关 SQL。
2. 进程树管理、OS 差异、优雅停止、停止回执与重启恢复：`processtree`、`shutdown.go`、`daemon_process_cleanup_test.go`、`shutdown_retry_test.go`。
3. Session 与工作区连续性：PriorSessionID / PriorWorkDir 的服务端选择、Provider ResumeRejected、会话文件 / 账号绑定、工作区复用和跨 Runtime 接续。
4. 隔离与授权：本地文件系统隔离、Codex sandbox、进程环境继承、Task-scoped Token、Runtime 所有者授权和跨成员共享。
5. 多平台适配：Windows / macOS / Linux 的命令启动、进程树、路径、临时目录和 Worktree 行为。
6. Script 执行：当前受管命令、Environment Command 与 Run 之间的真实边界，确认是复用现有执行器还是增加独立 Script Executor。
7. 对照宿主官方协议文档与上游测试，验证各 Provider 的能力矩阵和版本兼容策略。

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
3. Cancel Ack 不只是状态确认，还会持久化 branch / durable workdir / preserved-work error / retired session 等恢复指针；重复写入采用幂等更新与 cancelled 状态条件保护。
4. 停止请求、进程树已结束、资源可复用、终态回执已持久化是不同阶段。清理确认缺失会影响下一次运行的接续策略。

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
- **停止确认与资源回收是平台级能力。** Agent Adapter 报告中断结果，Host Daemon 负责进程树和本地资源，服务端记录最终确认与后续可复用状态。
