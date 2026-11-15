# 专题三 A · 执行底座源码研究记录

> **架构治理说明（2026-11-15）：** 本文的源码、测试和多机实验是理解 Multica 执行底座的证据。当前设计以 Multica Daemon / Runtime / Backend / Run / Session / Process / Workspace / Usage 为事实权威；专题三 A V1.1 已将 Script 托管、本地 Credits 通路和调用级证据列为明确扩展项，并保留会话、进程和结果消费的具体规则。历史实验结果保持原来源与范围；融合机制以[专题三 A V1.1](../architecture/03a-execution-plane.md)和[架构治理基线](../architecture/governance-baseline.md)为准。

更新日期：2026-11-15  
第一阶段上游快照：[multica-ai/multica @ fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc](https://github.com/multica-ai/multica/tree/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc)  
第一阶段采用源码与测试断言阅读。第二阶段的四份固定源码、上游定向测试、真实 CLI 回环实验及设计模型见[第二阶段研究](#11-第二阶段宿主协议与本地观察)。  
第三阶段用两个真实 CLI 和 Multica 服务端验证上下文换版、共享任务身份与报告归属。[第三阶段研究](#12-第三阶段上下文与任务身份)  
第四阶段沿两个真实 Git 候选、XLSX、脚本与 Daemon 回报检查制品及结果归属。[第四阶段研究](#13-第四阶段工作副本受管脚本与结果交接)  
第五阶段核对独立虚拟机、双身份权限、原机重连和本地会话恢复。[第五阶段研究](#14-第五阶段跨主机接续与设计收口)  
平台设计入口：[专题三 A：执行平面与宿主适配](../architecture/03a-execution-plane.md)

## 1. 已追踪的底层路径

| 研究主题 | 实际代码路径 | 初步发现 |
|---|---|---|
| Daemon / Runtime 身份 | `server/internal/daemon/types.go`、`daemon.go` Runtime 注册与运行时索引 | Daemon 是 Host 上的管理进程；Runtime 是 workspace 下的具体工具执行目标，provider 与 runtime profile 共同决定实际适配器 |
| Claim 与 Start 分离 | `server/internal/daemon/client.go` Claim / Start；`server/internal/handler/daemon.go` Claim / StartTask | Claim 先占用任务，Daemon 完成本地准备后再 Start；claim-aware Start 绑定 runtime_id 与 dispatched_at，旧 claim 返回冲突；legacy 路径保留兼容语义 |
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
- [WS RPC 优先领取](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/wsrpc.go#L315-L386)
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
- [Runtime Identity 与 Protocol Family 映射](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/builtin_runtimes.go#L18-L203)
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

本地准备可能包含仓库、工作目录、技能包、MCP、Provider Home 和上下文文件等步骤。若领取即标记 running，工作台和其他消费者可能读取一个尚未准备完成的工作目录。Multica 因此在本地准备后才调用 StartTask；claim-aware Start 再绑定 runtime_id 与 dispatched_at，防止过期领取者启动已经转交的任务。新旧路径的具体行为见[第 10.4 节](#104-claim--start-generation-与丢失响应恢复)。

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
- [Runtime Profile 测试](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/runtime_profile_test.go#L205-L544)
- [服务端注册与 Runtime Upsert](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon.go#L448-L572)
- [Runtime 所有者 / Daemon 身份授权](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon.go#L58-L227)
- [心跳与在线状态更新](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon.go#L1483-L1605)

**源码观察：**

1. Daemon 先在机器级探测本地 CLI，再按 Workspace 注册 Runtime；自定义 Runtime Profile 是 Workspace 配置，但由每台机器本地解析命令路径，只有命令在该 Host 可用的机器才注册对应 Runtime。
2. Profile 只选择已支持的 Protocol Family，并配置 command / fixed args。命令行包装器可以复用现有协议族；协议不兼容的工具需要新的 Adapter。
3. Runtime 注册有配置漂移收敛：profile 列表签名变化触发重新注册；本地 CLI 不可用、版本探测失败和确认不可执行的处理不同，避免一次探测故障就把正在运行的 Runtime 全部下线。
4. Runtime 授权分 Workspace、Daemon ID 与资源授权校验。普通 daemon token 与特定 Daemon 和 Runtime Owner 绑定；Qoder 托管采用连接级凭据授权，具体分支见[第 10.7 节](#107-runtime-所有权与共享授权)。

### 5.2 Claim / Start / Heartbeat 的控制链

- [Claim 与 Start 入口](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon.go#L2100-L2455)
- [StartTask claim generation 校验](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon.go#L4674-L4794)
- [Runtime heartbeat 与授权校验](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon.go#L1483-L1605)
- [Claim 决策原因分类](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/service/task_claim_decision.go#L41-L191)

**源码观察：** Claim 响应有交付截止和失败重排；claim-aware Start 使用 Runtime ID + dispatched_at 识别具体 claim generation；Heartbeat 同时承载在线状态和服务端发给 Runtime 的待处理命令。三者分别回答“拿到工作”“当前领取者仍有权开始”“执行资源仍在线”。

### 5.3 进程树停止与执行准备隔离

- [进程树统一控制入口](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/processtree/run.go#L19-L92)
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
- [Runtime 容量 Advisory Lock](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/runtime.sql#L694-L726)
- [Agent 并发竞争数据库测试](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/service/task_claim_race_test.go#L22-L88)
- [Runtime 并发上限数据库测试](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/service/task_runtime_concurrency_db_test.go#L55-L305)
- [Runtime 上限修改与 Claim 锁同步测试](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/runtime_concurrency_test.go#L20-L133)

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
- [Start claim generation 锁定 SQL](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/agent.sql#L1002-L1008)
- [StartTaskForClaim 事务](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/service/task.go#L4480-L4560)
- [Start 请求携带 runtime_id / dispatched_at](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon.go#L4674-L4794)
- [Start 丢失回执、重领代次、并发重放和取消竞争测试](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon_start_claim_test.go#L17-L212)

Claim 将任务从 queued 改为 dispatched，并写入 dispatched_at 和短期 prepare_lease_expires_at。Start 存在两条兼容路径：

| 路径 | 请求与状态检查 | 回执重放 |
|---|---|---|
| Claim-aware Start | 携带 task ID、Runtime ID 与本次 dispatched_at，服务端锁定精确领取代次；旧代次返回冲突 | 同代次已 running 时返回原 started_at，复用同次状态迁移 |
| Legacy Start | Runtime ID 与 dispatched_at 均为空时调用原 StartTask，保留单次状态迁移行为 | 首次有效请求成功，重复请求返回 400；采用原有兼容语义 |

新 Daemon 按 StartClaimSupported 选择代次请求和对应重试行为。代次校验及同代次幂等保证属于 claim-aware 路径。[Handler 分支](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon.go#L4694-L4763)、[客户端选择](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/client.go#L510-L525)、[legacy 重复请求断言](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon_start_claim_test.go#L166-L180)。

Claim 成功但响应未送达时，90 秒 recovery window 之后，且 prepare lease 已过期，服务端刷新 dispatched_at 并重新交付。环境准备超过初始 45 秒时，Daemon 通过 ExtendTaskPrepareLease 延长租约，避免仍在准备的任务被误回收。claim-aware Start 与 cancel、reclaim 对同一任务行锁串行化；取消提交后，该路径的迟到 Start 返回冲突。

**设计原因：** Runtime ID 只说明执行目标，不能识别同一任务的哪一次领取。dispatched_at 作为 generation token，使同 Runtime 重领、响应重放、取消和 Start 之间具备可比较的所有权版本。

### 10.5 Heartbeat、WebSocket 与 Runtime 在线状态

源码：
- [Daemon 每 Runtime 心跳循环与 WS fallback](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/daemon.go#L4545-L4680)
- [WS RuntimeLease 与连接生命周期](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemonws/hub.go#L23-L158)
- [WS 心跳帧处理](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemonws/hub.go#L1087-L1173)
- [批量 Heartbeat Scheduler](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/heartbeat_scheduler.go#L104-L324)
- [Redis Liveness Store 与 DB fallback](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/runtime_liveness_store.go#L13-L140)

**代码事实：**
1. Daemon 默认约每 15 秒为每个 Runtime 发送心跳；收到近期 WS heartbeat ack 时跳过重复 HTTP heartbeat，WS ack 连续缺失后 HTTP 自动恢复。
2. WS 握手时批量读取并校验固定 Runtime 集合，建立连接级 RuntimeLease。每次 WS 心跳复用这份授权快照，避免每 15 秒重新读取 Runtime 行；Runtime 被删除时通过 RuntimeGone 消息从连接范围剔除。
3. 生产 Heartbeat Scheduler 将 Runtime ID 合并，每 30 秒批量写一次 DB；Redis TTL 记录更近实时的 liveness。Redis 不可用时回退 DB heartbeat；批量写入遗漏项会进一步区分刚被明确下线、被 sweeper 竞争下线和已经删除。
4. RuntimeClaimFreshnessSeconds 为 150 秒，覆盖 60 秒 DB heartbeat flush、15 秒 Daemon heartbeat 和 30 秒 batch scheduler 的最坏组合，并留出余量。
5. Runtime Sweeper 每 30 秒运行。DB stale 候选还要经过 Redis liveness 过滤；Redis 不可用时按 DB stale window 工作。真正标记 offline 的 UPDATE 会再次核对 stale 条件，防止与刚到达的心跳竞争。
6. Runtime 离线后的活动任务收敛使用默认 3 小时 reconnect grace，按最后心跳计算；缺少 last_seen_at 时采用 updated_at。Daemon 真正重启另走启动孤儿恢复路径。
7. 在线判定、失联保护和任务 backstop 分别使用下表条件。数值为本固定版本的默认值。

| 判定 | 条件与时间基准 |
|---|---|
| 领取及健康在线判定 | 采用 150 秒 Runtime 心跳新鲜度 |
| 离线 Runtime 的活动任务收敛 | 心跳年龄超过默认 3 小时 grace，覆盖 dispatched / running / waiting_local_directory |
| running backstop，Runtime 记录存在 | started_at 超过 9000 秒，且 Runtime 心跳年龄超过 grace |
| dispatched backstop，Runtime 记录存在 | dispatched_at 超过 300 秒、prepare lease 已失效，且 Runtime 健康在线或心跳年龄已超过 grace |
| Runtime 引用为空或记录缺失 | 按对应任务 backstop 条件另行收敛；dispatched 仍检查准备租约 |

[FailStaleTasks 组合条件](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/agent.sql#L1294-L1328)、[离线 Runtime 的 grace 条件](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/runtime.sql#L300-L328)。

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
- [Runtime Owner / Shared With 判定](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/service/runtime_access.go#L12-L15)
- [Claim 最终交付事务与锁定重验](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon.go#L2440-L2540)
- [跨 Workspace、Ownerless Runtime 拒绝测试](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon_batch_claim_test.go#L231-L347)
- [Runtime 可见性撤销测试](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/runtime_visibility_revocation_test.go#L1-L260)

权限按用途分层：

| 层次 | 校验内容 |
|---|---|
| Workspace | 请求身份是否有该 Workspace 的访问权 |
| Daemon | daemon token 是否绑定请求中的 Daemon ID |
| 普通 Daemon / Runtime Owner | 用户凭据对应 Runtime Owner；普通 daemon token 的 owner 与 Runtime 当前 owner 一致 |
| Qoder 托管连接 | qoder-managed-* 在 Daemon ID 匹配后走连接级授权，校验连接启用、当前 token、hash、有效期及连接所有者的 Workspace owner/admin 身份 |
| Private Runtime sharing | Agent Owner 是否为 Runtime Owner 或在 shared_with 范围内 |
| Task delivery | 交付前锁定 Runtime 和 Agent，重新校验 owner、visibility、runtime binding，再签发任务级 token |

普通本地 Runtime 的共享授予资源使用权，任务交付要求有效 Owner，并按当前共享范围复核。Qoder 托管按 Daemon 身份进入专门的连接凭据路径；普通本地 Qoder CLI 仍采用普通 Daemon 规则。访问撤销会事务性取消受影响的活动任务，并收敛关联的聊天输入、Session 指针和补充任务。

[普通与托管绑定分支](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon.go#L132-L147)、[Qoder 连接凭据校验](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/qoder_connection.go#L596-L609)。

### 10.8 第一阶段结论

Multica 的 Runtime / Daemon 不是一个“机器在线列表 + 任务轮询器”，而是一套围绕执行资源身份、数据库原子派发、容量互斥、Claim generation、心跳租约、故障分类、授权复核和恢复收敛形成的执行控制机制。

对本项目的直接设计输入：

1. Host、Daemon、Runtime Instance 分开建模；Runtime Instance 按 Workspace 和 Provider / Profile 形成。
2. 以 Run 作为实际执行记录，派发需包含可比较的 Claim Generation；领取、准备、Start、进程启动和终态观察分别留证。
3. 资源调度同时考虑 Daemon 本地槽、Runtime 容量和执行者 / Agent 容量；容量更新与 Claim 使用同一互斥机制。
4. 所有入口最终进入同一派发服务；数据库原子占用是并发正确性的最终依据，通知与轮询只负责降低延迟。
5. Runtime 在线状态采用心跳租约与持久状态结合；短暂离线、进程退出、Daemon 重启和 Runtime 删除必须走不同恢复分支。
6. 平台后续验证逐项核对准备续租、Waiting、Start 与结果回报的代次资格；原生已核对的领取重放及 claim-aware Start 保护与待补链路分别记录。
7. Workspace、Host / Daemon、Runtime Owner、共享授权和 Task Token 是不同权限层，最终交付时必须重新核验当前授权。

本阶段完成源码路径与代表测试断言追踪，未执行上游 Go 测试。下一阶段按 V0.2 顺序进入“宿主与本地交互入口”，重点比较中心派发、成员从 CLI / IDE 主动关联、事后补录，以及会话观察和真实用量归属。

### 10.9 本轮收口与后续验证输入

已收口新旧 Start 路径、超时组合条件、Qoder 托管授权和 Start 锁定 SQL 引用。以下事项按固定提交核对后保留为后续研究输入。

**Prepare 跨代写入。** 固定提交 fdfbfcd 中，准备续租按任务、Runtime 与准备状态更新；等待目录 `MarkAgentTaskWaitingLocalDirectory` 和失败更新按任务及活动状态匹配。这些更新条件未包含 dispatched_at，入口仍执行 Daemon / Runtime 授权检查。本轮关注同一仍获授权 Runtime 重领时的旧准备动作。[准备续租](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/agent.sql#L989-L1000)、[等待目录](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/agent.sql#L1010-L1026)、[失败更新](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/agent.sql#L1201-L1214)、[执行者鉴权](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon.go#L220-L292)。

续租失败仅记录 warning，准备流程继续；旧领取到达 Start 并收到 409 时，Daemon 识别 `errStartClaimRejected` 并丢弃其终态回报。静态链路揭示：旧准备在租约失效、任务重领后继续运行，若在到达 Start 前失败，普通失败回报仍可能命中当前活动任务。[续租失败处理](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/daemon.go#L7494-L7526)、[Start 拒绝与普通失败分支](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/daemon.go#L5956-L6031)。

目录锁保护工作副本，同任务终态回报跟踪串行化本地发送；两处保护分别围绕目录占用与任务回报投递，领取代次隔离仍需逐项验证。[目录锁](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/execenv/execenv.go#L1464-L1503)、[终态回报跟踪](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/daemon.go#L6539-L6600)。

| 后续验证输入 | 已核对依据与待取得的结果 | 承接阶段 |
|---|---|---|
| Prepare 跨代写入 | 用同 Runtime 的租约失效、重领和旧准备失败注入，分别观察续租、Waiting、失败回报对新代次的影响；以旧 Start 返回 409 且无终态回报为对照，取得实际时序与结果后确定适配范围 | 恢复链路与原型验证 |
| 同 Issue / Agent 串行与 SOP 并行 | 原生 Issue + Agent 活动互斥及每批按 Agent 去重已确认；比较并行 Script、同角色 DAG 节点的执行身份与目录策略，按实际开工情况确定互斥粒度 | Workspace / Script 与设计收敛 |
| 共享 Runtime 的任务身份 | 已核对任务 token 的 UserID 取 Runtime Owner；继续跟踪服务端任务作用域、Issue 访问和 Grant 校验，分别判断资源所有者身份与实际平台操作权限。[签发身份](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon.go#L4441-L4456) | 上下文与任务身份 |

后续阶段进度：共享 Runtime 身份已由第三阶段验证；Issue / Agent 串行及旧准备的本地写入、目录隔离、Start 409 和清理由第四阶段验证。上表 Prepare 项中的旧续租、Waiting 和 Start 前失败回报三条服务端写入路径继续保留故障注入任务；[工作副本实验](topic-03a/workspace-continuity.md#两条新实验)记录各自的实际覆盖。

本轮新增 Prepare 结论采用固定源码的静态路径核对，故障注入结果由后续原型取得。第一阶段源码研究已收口；下一项仍按计划研究宿主与本地交互入口。

## 11. 第二阶段：宿主协议与本地观察

这一阶段固定四份源码，沿“本地开始工作、宿主产生事件、重读历史、多路结算、成员选择共享”追到协议、适配器和记账实现。实验使用临时配置与合成输入，真实 CLI 执行协议和本地操作，模型响应由回环服务提供。[项目接入规则](../architecture/03a-execution-plane.md#5-本地主动会话与-agentobservation)

| 对象 | 读到哪一层 | 可复核结果 |
|---|---|---|
| [TeamAI](topic-03a/teamai.md) | Skill Driver 交接与回报、AgentObservation 结算、宿主 Hooks、转录解析、账本、制品 | 同一原始请求从原路径重读只计一次，换路径导入同一文件后上游再次计费。配置指纹在项目和驱动不同的两次执行中可相同 |
| [Codex](topic-03a/codex.md) | App Server 的线程、回合、事件、只读回放与监听，CLI JSON 的事件转换，宿主 Hooks | 同线程两轮的 last/total 为 11/11、22/33。resume 再次给出 33，回环服务仍只收到两次请求。第三轮单独测试 CLI JSON 中的累计语义 |
| [Claude Code](topic-03a/claude.md) | Hooks、流式 CLI、官方 SDK 的消息及本地会话读取、身份关联、成本口径 | 同会话两轮恢复后的估价分别为 0.00009 与 0.00018 美元。展示消息 ID、转录 UUID 和模型消息 ID 属于不同域。真实 Read 的前置、后置 Hook 与流式结果共享同一工具调用 ID。本地 OTel 接收器取得四条请求，两轮都经 prompt 和消息 UUID 对回宿主记录 |
| Multica | 固定 `fdfbfcd` 的两种宿主适配、消息入库、用量 upsert、恢复与回报 | 以下 9 项上游 Go 定向测试通过。验证层为宿主适配器，存储与 Daemon 恢复路径为源码追踪 |

### 两个现有适配器如何消费用量

Multica 的 Codex Adapter 在处理 turn 状态之前过滤其他 thread；它只把属于本次活动或刚结束 turn 的用量计入。首个匹配快照取 last，后续读取 total 变化。对历史重放、重复快照、终态之后的最后一次用量、多次模型请求分别有测试。RPC 提供了实际用量时优先使用它，必要时从落盘记录补模型名；RPC 缺量才从会话记录取量。补录设计沿用该来源顺序，并保留观察缺口、乱序和计数重置的处理。[线程过滤](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/codex.go#L3035-L3062) · [快照差量](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/codex.go#L3885-L3925) · [落盘补充](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/codex.go#L4067-L4092) · [四个用量回归场景](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/codex_test.go#L3951-L4059)

Claude Adapter 保留所有内容块，按模型消息 ID 对主循环输入和缓存用量去重。恢复前捕获基线，读取最终 modelUsage 时按模型计算差额。若恢复时基线捕获失败，优先保留流式取得的本次用量。它的返回值与 SDK 会话估价分别解释。[块与消息去重](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/claude.go#L539-L573) · [基线缺失分支](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/claude.go#L327-L358) · [按模型相减](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/claude.go#L811-L904)

控制平面接收任务消息时检查 Daemon 的任务访问权；提供幂等键时在任务的命名空间派生消息 ID。缺键会生成新 ID，因此两个独立采集器还需要共享宿主标识或明确对应。用量按 task / provider / model 以当前快照覆盖，过程快照跳过加法指标，防止每次刷新重复记账。SQL 基于已有 task，所以跨系统先解析到同一个 Run，再使用这条写入路径。多来源并发更新、覆盖关系、来源冲突和修订次序是本项目的设计工作。[消息身份及任务鉴权](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon.go#L5765-L5813) · [生成 ID 与脱敏](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon.go#L5851-L5871) · [过程和最终用量](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon.go#L5529-L5595) · [用量 SQL](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/task_usage.sql#L1-L25)

Codex 收到 turn/completed，Claude 收到 result，两者都能表明一次宿主交互已给出终态。固定版本的两个 Multica Backend 构造 Session 时都未设置可选的 TerminalObserved 回调。应分别呈现宿主的终态、Daemon 已收到 Result、清理以及副作用是否可重做。Codex 恢复遇传输错误就上抛，部分协议错误会新建 thread，特定恢复读取溢出会显式标记；Claude 则结合失败、是否请求过恢复、拒绝原因和实际会话 ID 来判定。外部观察只补事实；决定是否重试的是原执行控制者。已有工具动作、可能遗漏副作用或仅仅丢了观察连接时，先核对原执行。[Codex 终态](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/codex.go#L3532-L3582) · [Codex Session](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/codex.go#L1073-L1080) · [Claude Session](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/claude.go#L519-L538) · [Codex 恢复与回退](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/codex.go#L2040-L2065) · [Claude 拒绝判据](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/claude.go#L1284-L1317) · [Daemon 的重试条件](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/daemon.go#L9602-L9646)

### 如何复核

在 Multica 固定提交的 server 目录执行以下命令。使用 Go 1.26.9，按顶层用例计 9 项通过。第一阶段当时的测试断言阅读与此次实跑分别记录。

```bash
go test -count=1 -v -run '^(TestCodexRawTurnCompletedDeduplication|TestCodexRawTurnCompletedWithoutIDDeduplicatesLifecycleAndUsage|TestCodexThreadTokenUsageUpdatedDropsResumeReplay|TestCodexThreadTokenUsageUpdatedDeduplicatesSnapshot|TestCodexTokenUsageArrivingAfterTurnCompleted|TestCodexThreadTokenUsageUpdatedAccumulatesCurrentTurnResponses|TestClaudeResultUsageSinceCumulativeTurns|TestClaudeExecuteReportsResumeRejectedOnAccountBinding|TestCodexResumeOverflowError)$' ./pkg/agent
```

本仓库的两个回环探针和一组设计模型可以分别运行。回环探针使用真实宿主二进制、临时工作区和标准库实现的模拟服务；模型测试使用合成的归一化观察。用量数值是可复现的协议输入。供应商实付在这一采集范围内保持未知。

```bash
python3 prototypes/topic-03a/codex_observation_probe.py
python3 prototypes/topic-03a/claude-local-probe.py /path/to/claude
node --test prototypes/topic-03a/local-observation.test.mjs
```

[Codex 探针](../../prototypes/topic-03a/codex_observation_probe.py)使用 codex-cli 0.167.0-alpha.4。[Claude Code 探针](../../prototypes/topic-03a/claude-local-probe.py)使用 Claude Code 2.1.325。[13 项设计模型测试](../../prototypes/topic-03a/local-observation.test.mjs)通过，涵盖重复观察、部分重叠绑定、切换 Issue、撤权后补传、累计值与重置、父子计量覆盖和 C1 迟到回报。模型验证单进程下的归属规则，两个探针验证各自宿主的实际行为。

后续集成验收以同一成员同时打开 CLI 和 IDE 为起点。让已授权的本地适配器与中心 Daemon 同时观察同一回合，再断网、缩小选区、重连、补录并在新回合切换 Issue。应得到原 Run 或明确的外部观察、有效选区的单份投影，以及与唯一原生请求集合一致的用量。另验证无原始标识、部分消息缺失、父子代理并行和只有会话总额时的降级结果。下一阶段研究上下文投递、加载回执与任务身份。

## 12. 第三阶段：上下文与任务身份

订单导出的 D2 要求在 C2 增加付款时间列。实验沿着两个问题追踪同一份报告：D2 在哪一轮到达宿主，谁有权把 C2 的核验结果交到哪个 Issue。宿主使用真实可执行文件、本机模拟模型服务和合成工作材料；权限实验运行 Multica 生产 handler、认证中间件与实际迁移过的 PostgreSQL。两组实验以同一份结果文件的 SHA-256 贯通。

| 已跑的实验 | 主要结果 | 可复核材料 |
|---|---|---|
| Codex 0.144.6 项目文件与 HOME；0.167.0-alpha.4 HOME。每组 11 回合、12 次模型请求 | 两个 0.144.6 通道热继续、同服务恢复均只带 D1，跨进程恢复带回历史 D1 并加入新版 D2。显式补发可在原线程交付 D2。alpha 的 HOME 热继续能读取 D2。另验证 Skill 正文和 MCP 调用者、结果去向 | [版本、源码与矩阵](topic-03a/codex-context.md) · [探针](../../prototypes/topic-03a/codex-context-probe.py) |
| Claude Code 2.1.325，含 Multica 原生材料生成，共 10 个进程、12 回合、14 次模型请求 | 同进程立即续轮仍只带 D1；显式补发和跨进程恢复都能把 D2 放进请求，进入的通道不同。文件过期仍可触发路径 Hook。Skill 描述与正文、MCP 工具发现与调用均可分别举证 | [版本、源码与矩阵](topic-03a/claude-context.md) · [探针](../../prototypes/topic-03a/claude-context-probe.py) |
| Multica fdfbfcd，共享 Runtime、真实 Claim / Start 与目标 Issue 读写；PostgreSQL 17.5 迁移至 657 | 在独立用例中各用内建报告和 Claude 实测报告跑一遍。获授权评论 201，私有项目 404，过期凭据 401，撤销后原任务读写均 401；源 Issue 回读作者、源任务、摘要及失败值 | [权限调用链、结果、复跑命令](topic-03a/shared-runtime-identity.md) · [集成用例](../../prototypes/topic-03a/shared-runtime-identity_test.go) · [本次输入文件](topic-03a/fixtures/claude-c2-observation.json) |
| Multica 上游 24 项定向回归；本项目 8 项新增设计模型测试 | 上游 Daemon 10、execenv 7、CLI 7 全部通过，覆盖投递、Skill、身份和工作区 marker。模型覆盖历史与本轮、证据冲突、受托操作范围、迟到回报和失败检查值 | [模型断言](../../prototypes/topic-03a/context-decision.test.mjs)；原始命令见下文 |

**为什么要保留每次尝试。** Daemon 在 Backend 执行前编制 ContextReceipt。文件加载等级沿用固定宿主的既有探测，记录中的指纹取 SHA-256 前 12 个十六进制字符。恢复失败后开启新会话重试时，Daemon 为同一 Task 再次上报，服务端以 task_id 更新原回执。该机制便于排查最近一次执行准备。C1 用哪版规则、C2 何时补发和工具在哪一轮使用，需保留带调用及回合的证据，并关联到原尝试。候选和报告以完整内容摘要核对。[等级与版本筛选](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/context_receipt.go#L37-L127) · [构建与指纹](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/context_receipt.go#L151-L265) · [首次上报](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/daemon.go#L9206-L9231) · [重试上报](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/daemon.go#L9298-L9315) · [存储行为](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/task_context_receipt.sql#L1-L13)

**从文件到 Issue 的实测结果。** Multica 原生函数将 D2 写入项目文件，Claude 读取后，其模型请求含 D2。合成模型固定返回只含 `order_id` 的列清单，独立字段检查得到 `payment_time_check=false`。源 Issue 的评论回读得到同一文件摘要 `fa62cdc8d28be2b59e735ce051d687b44f914c5b1b641d678da604a1c161c64b` 和相同的失败值。服务端确认了评论作者、源任务、目标和回报内容；D2 对应 A3 内容要求，这次候选缺少必需字段。A2 的导出资格与订单可见范围、A3 的空值和时区规则仍需用实际导出样例检查。[专题一订单导出案例](../architecture/01-unified-work-lifecycle.md) · [本次回读对应的宿主报告](topic-03a/fixtures/claude-c2-observation.json)

### 在本地复跑

在本项目根目录执行。将 `MULTICA_CHECKOUT` 指向上述固定提交的独立工作副本，使用 Go 1.26.9、Python 3.10+ 和目标宿主版本。构建器通过 Go overlay 调用上游实现。在 Codex 命令中用 PATH 选择目标版本；Claude 命令接受 CLI 的绝对路径。使用临时 HOME 与只监听本机的模型端点。安装来源与具体选项见两个宿主的实验页。

```bash
python3 prototypes/topic-03a/multica-context/build.py "$MULTICA_CHECKOUT" /tmp/ap-context-materialize
AP_CONTEXT_MATERIALIZER=/tmp/ap-context-materialize python3 prototypes/topic-03a/codex-context-probe.py project
python3 prototypes/topic-03a/codex-context-probe.py home
AP_CONTEXT_MATERIALIZER=/tmp/ap-context-materialize python3 prototypes/topic-03a/claude-context-probe.py "$CLAUDE_CLI" > /tmp/claude-c2-observation.json
node --test prototypes/topic-03a/context-decision.test.mjs prototypes/topic-03a/local-observation.test.mjs
```

按[服务端复跑说明](topic-03a/shared-runtime-identity.md#复跑)准备一次性数据库，先执行内建报告组，再把 `AP_CANDIDATE_REPORT` 指向刚生成的 JSON 或上述已提交的固定样本，执行同一组断言。动态生成的报告用自身完整摘要比对，固定样本可核对此处列出的摘要。宿主实验与服务端测试交接的是结果文件；本轮没有运行跨机常驻 Daemon、商业模型端点或完整订单导出应用。

以下为 24 项上游回归的选集，在 Multica 工作副本的 server 目录运行。定向测试读取固定提交的生产源码。此次运行在 Daemon、CLI 两个较大的包用 Go overlay 略去无关测试文件以控制编译资源，保留所选测试源码、生产实现与依赖。

```bash
go test -count=1 -run '^Test(BuildContextReceiptFileDeliveredBrief|BuildContextReceiptLoadStates|BuildContextReceiptOmitsEmptySections|ExistingRuntimeConfigContentStripsManagedBlock|ReportContextReceiptPostsAndToleratesOldServer|ContextReceiptFailedBriefWrite|ContextReceiptUsesMaterializedSkill|RunTaskRejectsMismatchedAgentIdentityBeforePreparation|ValidateTaskIdentityRequiresExpandedAgent|ValidateTaskIdentityAcceptsMatchingAgent)$' ./internal/daemon
go test -count=1 -run '^Test(WriteRuntimeConfigFilePreservesUserContent|WriteRuntimeConfigFileReplacesExistingBlock|WriteRuntimeConfigFileIsIdempotent|PreparedSkillNamesMatchPrivateDiscoveryDirectories|WriteContextFilesHydratesDisableModelInvocationSkillButDoesNotAdvertiseIt|Prepare_WritesWorkspacesRootMarker|Reuse_SelfHealsWorkspacesRootMarker)$' ./internal/daemon/execenv
go test -count=1 -run '^Test(IssueReadCommandsUseInjectedTaskToken|IssueReadCommandsFailClosedWithoutTaskToken|NewAPIClient_WorkdirMarkerRequiresTaskToken|NewAPIClient_AgentContextRequiresTaskToken|ResolveWorkspaceID_AgentContextSkipsConfig|ResolveToken_AgentContextSkipsConfig|NewAPIClient_WorkdirParentEscapeFailsClosed)$' ./cmd/multica
```

### 留给下一阶段的测试要求

1. 在支持 Codex 文件沙盒的机器上用 0.167.0-alpha.4 跑项目 `AGENTS.md` 通道。固定预期 D1 → D2、热继续、显式补发、同进程恢复、跨进程恢复、文件移除；保存各次实际请求对应的版本。当前容器在读取项目文件阶段遇到 NETLINK_ROUTE 限制。该版本已跑通 HOME 组；以上项目通道保留为独立验项。
2. 用真实工作副本和受管 Script 产出订单导出 C2。A2 用不同角色和订单范围核对；A3 对候选实际文件核对付款时间、未付款空值和时区，记录候选摘要、执行版本、退出与检查结果。
3. 在真实 Daemon 和共享 Runtime 上复跑两端交接。在节点尝试换代、撤销后回报、重复上报与跨机恢复时，核对关联到的 Run、尝试、制品和历史；对比服务端已取消与宿主已停止的时间点。SOP 专属的 Grant 检查本轮由设计模型验证，服务端实现和在途回报竞争留在集成阶段。
4. 对 Prepare 跨领取代次和同一 Issue / Agent 的 SOP 并行设置独立工作副本，检查迟到的旧进程写入、目录占用、清理与 C2 接续。结合这些结果确定结构化回报和制品回收规则。

## 13. 第四阶段：工作副本、受管脚本与结果交接

本轮从同一订单导出规则 D2 出发，把两个真实 Git 提交、导出的 XLSX、核验器、结构化报告和控制平面回执对到同一次节点尝试。实验分段使用同一批报告或文件字节衔接。业务数据取自四类角色和三个合成订单，宿主使用协议夹具，Daemon 与 PostgreSQL 使用 Multica 的真实实现。专题一保留其完整验收规则。[阶段设计](../architecture/03a-execution-plane.md#回报消费与接续)

| 要回答的问题 | 实际测到的结果 | 复跑与固定源码 |
|---|---|---|
| 谁可并行，哪一代可继续写？ | 同 Issue、同 Agent 的另一讨论等待，不同 Agent 能分别领取。本地锁保护占用的工作副本；G2 已获准开工后，G1 仍可在独立目录完成准备，随后 Start 返回 409。G1 清理后 G2 分支保留自己的改动。原生 20 项 execenv 与 9 项 Daemon 回归，另有 2 项组合用例 | [工作区、领取与恢复](topic-03a/workspace-continuity.md) |
| 接收方如何重建 C2？ | 只发布 C1 时，独立接收仓库在 fetch 后缺少 C2；发布后以固定 C2 提交检出，从 HTTP 取得东区 XLSX 并复核摘要。迟到推送移动了 main，已检出的 C2 保持原值。附件被改动一个字节、长度相同时，接收方拒收且保留原件。Git HTTP 与附件 HTTP 均在本机 | [独立接收端交接](topic-03a/workspace-continuity.md#从独立接收端取回-c2) |
| 核验脚本退出 0，工作流该往哪边走？ | C1 的 XLSX 格式和金额正确，但东区多看了一条西区订单。C1 退出 0、A2 失败、A3 通过，进入返工。C2 退出 0、A2/A3 通过。真实 TeamAI 本地命令驱动重算两份报告，两个后续节点按报告分支；缺输入时验证器退出 1，无报告 | [工作副本、四角色、五个内容反例和 TeamAI](topic-03a/order-export-workspace.md) · [C1](topic-03a/fixtures/order-export-c1.json) · [C2](topic-03a/fixtures/order-export-c2.json) |
| 下载的工作簿是否就是核验过的工作簿？ | 同一份 5,494 字节 XLSX 走 LoopForge 普通 Runner 具名输出，JSON 接收端得到 9,406 字节，ZIP 无法打开。走 Multica 授权附件上传下载，长度、SHA-256 与字节完全一致。重复上传相同内容取得不同附件 ID | [真实协议与附件对照](topic-03a/binary-artifacts.md) |
| 发出回报后断线、撤销或旧回复晚到，会改写哪次结果？ | 真实 Daemon 的 C2 回报在服务端落库后首次收到 503，待确认队列从 1 到 0，重复回调只留一条源评论。重放 C1 后两份原报告仍可分别读取。按 C1 留下的本机路径，则已读到 C2。撤销后服务端先取消，再观察到本机子进程退出与一次取消确认。另复跑 5 项原生终态队列测试 | [生产 Daemon / 服务端 / PostgreSQL 贯通](topic-03a/result-handoff.md) |
| 平台何时允许 SOP 消费？ | 13 项 SQLite 设计原型测试通过。包含对照派发、Grant、核验器版本、候选提交、供应端文件摘要和验收值。首交并发与缺附件补齐后并发分别重复 50 次，两种情形均只消费一次。当前结果与旧尝试证据分别归档 | [接收原型与并发断言](../../prototypes/topic-03a/result-admission/test_admission.py) |

**三个上游各能复用什么。** Multica 的领取、运行身份、终态重放和附件读写可作为执行底座。LoopForge 在 Script 节点运行前准备工作区、按运行范围启动命令，在自动检查前校验声明制品，并在提交节点结果时核对 owner generation 和节点仍在执行。失败还须匹配 attempt；同代运行节点允许已通过门禁的成功跨 attempt 提交。AgentPlatform 对候选验收另核本次尝试与精确候选。[成功与失败的实际条件](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/node_outcome.go#L29-L48)其具名文件与节点尝试关联，适合追溯返工。TeamAI 的命令产生退出和结构化输出，后续节点可根据这些输出选择动作；其驱动和派发把尝试、修订及来源带回。这里借用命令与回报机制，平台的成员关系、分派和结果仍由中心工作模型维护。[LoopForge 的命令执行](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/node_execute.go#L597-L637) · [产物门禁与提交](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/node_execute.go#L1015-L1043) · [制品先于检查的测试](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/engine_test.go#L2521-L2553) · [TeamAI 命令到回报](https://github.com/Tencent/teamai-cli/blob/556b5246f2c13ad28b8b79b5b513a78ed8ab9dae/src/workflow/protocol.ts#L1023-L1043)

### 原型与回归如何复跑

1. 按[订单实验](topic-03a/order-export-workspace.md#复跑)安装 Python 依赖并运行，输出 C1/C2 工作副本、各角色实际文件和核验报告。C2 东区原件 SHA-256 为 `5784c6c9f6660ac89a3bd4188541f5bfaee85b2e21a39b47a55923983380e852`。运行文中的 TeamAI 命令可验证回报确实驱动后续节点。
2. 将 C2 的 east.xlsx 作为[制品传输对照](topic-03a/binary-artifacts.md#复跑)的输入，将 C1/C2 的 report.json 作为[终态回报实测](topic-03a/result-handoff.md)的输入。各自的原生存储、服务端认证及隔离数据库条件见对应研究页。
3. 参照[工作区实验](topic-03a/workspace-continuity.md#复跑)运行两个组合用例与原生回归。在本项目根目录执行下面两条命令，可重建订单样本、核对平台接收规则，并回归专题二、三 A 既有的 38 项状态模型测试。

```bash
python3 prototypes/topic-03a/result-admission/test_admission.py
node --test prototypes/topic-02/state-model.test.mjs prototypes/topic-03a/local-observation.test.mjs prototypes/topic-03a/context-decision.test.mjs
```

LoopForge 固定提交 `97b3cdc`、Go 1.26.11，原生定向回归的以下 8 个顶层测试全部通过。覆盖脚本顺序、逐仓库产物、制品门禁、旧代/旧尝试、最近尝试和准备脚本的重复执行。在该上游仓库根目录执行。

```bash
go test -count=1 -run '^Test(ShellAndPythonScriptNodesExecuteInOrder|ArtifactContractIsValidatedBeforeAutomaticGate|RunnerScriptAndCommandTerminalResults|RepositoryScopedRoleGateAndScriptArtifacts|StaleOwnerCannotFailAfterGenerationTakeover|StaleAttemptFailureIsIgnored|ImportChildArtifactsTakesNewestAttempt|WorkspacePreparationRecordFailureDoesNotRetrySuccessfulBusinessScript)$' ./internal/engine
```

TeamAI 的业务贯穿采用专题二固定提交 `556b524`，C1 和 C2 都通过真实 CLI 及本地命令驱动。另在专题三宿主研究提交 `1bc2ce1` 上独立运行 shell-command 原生测试，5 项通过，覆盖进程停止、超时、输出和启动失败。一次并跑交接、工作区与命令的扩展原生套件被运行环境终止（退出 137）；本轮没有该组合的通过结果。可在该版本的 checkout 用 `npm ci` 安装依赖后分别执行下列命令。[命令执行原生测试](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/__tests__/shell-command.test.ts)

```bash
./node_modules/.bin/vitest run --pool=threads --maxWorkers=1 src/__tests__/shell-command.test.ts
./node_modules/.bin/vitest run --pool=threads --maxWorkers=1 src/__tests__/workflow-handoff-ends-and-workspaces.test.ts
./node_modules/.bin/vitest run --pool=threads --maxWorkers=1 src/__tests__/workflow-place.test.ts
```

### 第五阶段验收输入

下列为第四阶段结束时的验收输入，实际完成结果见[第五阶段记录](#14-第五阶段跨主机接续与设计收口)。

- 用两台独立主机与各自的成员身份跑一次跨机接续。原机离线、另一台按精确提交及具名附件恢复、原机重连后发送旧结果，把三次观察对到同一 Issue 和各自的 Run。记录接管时不可达的未提交文件和仍占用的资源。
- 汇总中心派发、本地关联和事后补录三种入口在每个已测宿主上的能力。逐项注明证据由谁提供、缺失时用户看到什么、重要决定换版后怎样继续，并据此明确 3A 交给 3B 的资产加载回执。
- 对 Codex 0.167.0-alpha.4 的项目 AGENTS.md 通道，本轮重跑仍在原生文件沙盒创建 NETLINK_ROUTE socket 时被宿主环境拒绝，模型请求数为零。保留正常文件沙盒的独立主机复跑项。真实部门订单服务、其余验收项和用户接受按专题一另行核验。

## 14. 第五阶段：跨主机接续与设计收口

同一个订单验证 Issue 有两份候选。C1 的东区工作簿多出一条西区订单，检查结论为返工；C2 修正了选区，A2、A3 通过。以“C1 卡在原机发送队列，接替者先处理 C2”为共同场景，分别观察机器中断、权限、会话和结果消费。下表给出每个结论对应的运行环境。

| 验证对象 | 实际怎么跑 | 得到的证据 |
|---|---|---|
| 原机任务结束，接替者取回已发布内容 | 两个 GitHub 托管 Ubuntu 24.04 作业串行，A 作业结束后 B 才启动。每次以同一随机挑战对各自内核的启动标识计算摘要 | 两个启动标识不同；B 从发布的 bundle 检出 C2 完整提交，核对报告及真实东区工作簿的字节、摘要和 ZIP 结构。[两台独立 VM](https://github.com/ScWen7/Issues/actions/runs/43619920271) |
| 接替者先完成，原机随后重连 | 新一轮使用并行的 A、B 作业。A 生成 C1/C2，单独进程将本轮实际生成的 C1 存在 A 本地后退出。A 的协调进程等待；独立 VM 上的 B 核对 C2 后回执，原 A VM 再起进程从本地出队 | 同一 A 内核在 B 确认后送出原 C1；B 逐字节核对 C1、C2 两份原报告。此处模拟工作进程停止，A 的协调进程持续在线。最初探索轮用仓库中的固定 C1 作对照，正式回归改用本次生成的 C1。[实际 C1 回归](https://github.com/ScWen7/Issues/actions/runs/43620893430) · [工作流](../../.github/workflows/agentplatform-independent-runners.yml) |
| 进程中断、未发布材料和节点消费 | 同一内核，中心、A、B、恢复 A 的网络 / PID / 挂载命名空间各自独立。A 工作进程实收 SIGKILL，B 在独立副本重算；中心使用第四阶段事务接收原型 | A 退出 137。B 重算的东区工作簿字节与发布件相同，A 未提交的文件和会话草稿未进入 B。C2、C1 晚报、C1 重发依次为 current、historical、duplicate；仅消费一次 C2。[探针与复跑](topic-03a/machine-handoff.md) |
| 谁可新开 Run，谁可下载或回报 | Multica 两套 Daemon / 成员身份、原生生产 handler、PostgreSQL 17.5 和独立 Python 接收进程 | B 初次领取为空，成员点名后 B 获得独立任务。目标 Issue、其附件和 B Runtime 用量均 200；私有 Issue、相同字节的私有附件、A Runtime 用量均 404。两任务各一条源评论。A 撤权后旧任务令牌 401，旧任务保持取消；长期离线对照为原 Agent 排入 deferred 重试。[逐项结果](topic-03a/two-runtime-identity.md) |
| 双 VM 在一次运行中交接 B 的任务身份、成品与 C2 回报 | 第一台 VM 运行 Multica、PostgreSQL 及两套 Daemon 对象。第二台 VM 持 B 的临时任务凭据构造六个请求。两机以本次运行的密封制品转送固定请求和原生响应 | B 在另一内核读回并核对 5,494 字节工作簿；三项允许和三项拒绝与本机对照一致。B 送回的 C2 原文经 Daemon 入库后，A 两次投递 C1，两任务各留一条源评论。撤权和超宽限分支保留取消和失败。[同次远端运行](https://github.com/ScWen7/Issues/actions/runs/43621447364) · [拓扑及复跑](topic-03a/two-runtime-identity.md#两台-github-托管虚拟机上的原生授权与回放) |
| 移交工作材料及恢复原宿主历史 | 单机、两个独立 HOME，分别使用真实 Codex 0.144.6、Claude Code 2.1.325，各测五步 | 两种宿主在 B 上恢复 A 的 ID 都于模型调用前拒绝。B 新会话的请求含 D2、C2 提交和报告摘要，A 私有标记均缺席；A 原 HOME 恢复成功。共 6 次真实宿主发出的回环模型请求。[独立配置与恢复对照](topic-03a/session-handoff.md) |
| Codex 项目文件换版 | Ubuntu 24.04 VM，官方 0.167.0-alpha.4 release，经发布摘要核对。探针在受信项目直接写合成 AGENTS.md，使用原生 read-only 沙盒；先观察，再固定该组合的回归断言 | 11 回合、12 次回环模型请求。热继续和同进程 resume 仍只带 D1；冷恢复出现 D2 替换通知，显式提交能在当轮带入 D2。该组合与 HOME 文件热更新实测不同。[严格回归日志](https://github.com/ScWen7/Issues/actions/runs/43620893430/job/132526101232) · [四组合对照](topic-03a/codex-context.md) |
| 各宿主的入口和停止、恢复、计量 | 固定 Multica 提交直接运行 17 项宿主适配器测试，运行真实适配器及协议夹具，并与既有 Codex、Claude、TeamAI 上游代码与宿主实测对照 | 对三种入口逐项列出可观察的原生事实、平台按版本补足的行为、成员独立 IDE 仍待现场实测的通道。[宿主能力表、3B 交接与复跑](../architecture/execution-capabilities.md) |

Git 交付和工作簿下载有不同的可见范围。两机实验中完整仓库接收者可读 bundle 内 C2 的祖先 C1，也能读取合成订单库中的东、西区数据；C2 的东区 XLSX 只包含两个东区订单。平台据接收者权限选择“仓库及可达历史”或“具名附件”，分别校验。原生双身份实验另以两次相同内容、不同附件归属验证了下载权限。GitHub 运行仅使用本研究仓库和合成材料，工作流可以从仓库 Actions 手动运行；跨作业的制品名称带当前 run attempt，复跑时选择全部作业。

TeamAI 交接的条件写入和分支前移检查可复用于可写副本；查验历史 C2 时仍按固定提交取回。LoopForge 在同代次内允许较早 attempt 的成功提交，并按生成时间挑同名子流程制品。AgentPlatform 对当前节点的消费同时核对尝试、候选和具名制品的来源。本轮在本地重新跑通 TeamAI 此前因资源退出的 54 项交接套件，连同其余定向用例共 65 项不同测试。在独立 runner 上完整串行执行 TeamAI 的三个工作区、交接与命令套件，139/139 通过。LoopForge 通过 11 项原生测试，其中 21 MiB 工作区经分块传输后清理、恢复，全部字节匹配；该用例在独立虚拟机也通过。[两库源码、复跑与设计取舍](topic-03a/upstream-handoff.md)

本轮设计交付见[执行平面](../architecture/03a-execution-plane.md)及[宿主能力与 3B 交接](../architecture/execution-capabilities.md)。3B 首个实验沿 D2 的规则、核验脚本及其发布版本检查选择和在途换版，通过 3A 的回执定位实际材料、调用、候选和验证结果。

本次同步复跑 38 项工作流、观察与上下文状态模型测试，以及 13 项结果接收断言，全部通过。两套远端工作流的五个宿主与上游作业、两个原生双虚拟机作业均通过。[上游与宿主作业](https://github.com/ScWen7/Issues/actions/runs/43621807704) · [Multica 跨虚拟机验收](https://github.com/ScWen7/Issues/actions/runs/43621447364)

### V0.6 交叉审查修订

Prepare 的阶段结论已限定为本地写入、目录占用、Start 拒绝和清理；旧续租、Waiting、准备失败回报三条服务端路径保持待验证。恢复设计明确按原领取代次核验这些操作。上下文展示同步区分写入已确认但加载未知、投递状态未知和明确未投递。

结果接收原型修复返工报告先到、附件后到时的提前去重返回。相同报告在当前授权下重新核对清单中的晚到文件，幂等补登记交付引用，原报告、归属和节点消费回执保持原值。新增两项回归先在旧逻辑上复现失败，再随修复通过：当前返工报告补件后并发重发只补一份引用；历史返工报告先拒绝错误字节，收到正确原件后补齐且保持历史归属。有权接收者均能查回补齐文件的摘要。

本次本地复跑结果为结果接收原型 **15 / 15 通过**，工作流、观察与上下文模型 **38 / 38 通过**。运行命令沿用本页，设置 `PYTHONDONTWRITEBYTECODE=1` 避免生成 Python 缓存。以上为本轮修订验证；前述远端作业保留第五阶段的运行记录。
