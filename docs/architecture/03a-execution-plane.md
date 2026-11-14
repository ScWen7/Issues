# 专题三 A · 执行平面与宿主适配

版本：V0.1 探索基线  
日期：2026-11-14  
状态：源码研究与设计探索中  
前置：[专题一：统一工作生命周期](01-unified-work-lifecycle.md)、[专题二：SOP 与研发工作流融合](02-sop-workflow.md)  
源码依据：[Multica 执行平面研究](../research/03a-source-evidence.md)

## 1. 目标

建立一套面向团队成员本地 Agent 环境的统一执行平面。平台负责把已授权的工作送达适合的执行环境，管理执行生命周期，收集过程与结果，并在失败、离线、重启和人工接管时保持工作连续性。

专题三 A 聚焦真实执行能力：

- 成员机器及其本地 Agent 工具如何注册、发现和保持在线。
- Run 如何从服务端进入本地环境，经过准备、领取确认、执行、回报和清理。
- 不同 Agent 宿主如何接入统一的执行与观测契约。
- 本地目录、Git 工作树、远端仓库和普通制品如何成为执行输入。
- 会话、工作区和执行结果如何在同机连续、跨机接续及崩溃恢复中保持关联。
- Script 如何作为受管执行类型使用相同的授权、派发、Run 与结果回报链。
- 凭证、项目访问、Runtime 共享、进程树和文件系统如何落实执行边界。

本专题交付执行平面业务模型、宿主适配模型、工作区与会话连续性模型、生命周期与恢复规则、平台能力契约，以及可运行原型的验收场景。数据库表、接口字段、部署拓扑和具体实现框架在机制评审后展开。

## 2. 研究起点：先区分四个概念

Multica 当前实现揭示了四个容易混淆的层次：

| 概念 | 含义 | 关键问题 |
|---|---|---|
| Daemon / Host Agent | 成员机器上常驻的本地执行管理进程 | 如何连接平台、发现本机工具、领取工作、管理进程与本地资源 |
| Runtime | 平台可调度的具体执行目标，通常对应一台机器上的一个 Agent 工具或自定义 Runtime Profile | 哪台机器上的哪种执行能力可以承接这项工作 |
| Agent / Role | 工作承担者及其指令、模型、技能和配置 | 谁负责这项工作，以什么角色和能力执行 |
| Run / Execution | 一次实际执行记录 | 何时领取、何时真正启动、执行了什么、结果和证据是什么 |

**当前研究判断：Runtime 是可调度的执行目标，Daemon 是该机器上的执行管理者，Agent 是工作身份 / 配置，Run 是一次实际执行。** 后续设计将验证是否需要把 Host、Runtime Profile、Provider Adapter、Workspace 等进一步显式区分。

## 3. Multica 当前执行链：需要吸收的机制

按源码追踪，Multica 的执行路径可概括为：

```text
服务端 Run 队列
  → 匹配 Runtime / Daemon
  → Daemon claim
  → 本地准备（工作目录、上下文、技能、MCP、环境）
  → StartTask 确认实际开工
  → Provider Backend 启动宿主工具
  → 消息 / 工具活动 / 用量持续回传
  → 完成、失败或取消
  → 终态回报与清理
  → 恢复扫描、会话接续和 GC
```

这里有三个特别重要的设计点：

1. **Claim 不代表真正开工。** Daemon 领取任务后还要准备执行环境，准备完成后调用 StartTask，服务端才将执行标记为 running。这样工作目录和上下文已经就绪，其他系统读取运行状态时不会提前访问一个尚未创建的目录。
2. **执行状态需要多个回执。** 已入队、已派发、已领取、已 Start、进程已启动、Agent 已产生语义活动、已得到终态结果，是不同事实。平台需要根据实际可观测能力定义统一状态和证据。
3. **本地执行需要独立的恢复闭环。** 服务端持有工作与 Run 事实；Daemon 持有本机进程、工作目录和宿主会话的管理责任。重启后先恢复原执行和工作材料，再决定继续、重试、转交或等待人工。

详细源码路径和反例见[研究记录](../research/03a-source-evidence.md)。

## 4. 需要形成的平台执行抽象

本节列出待设计的概念，不预设最终类名或实现结构。

### 4.1 Host / Daemon

Host 表示成员提供的物理或虚拟执行环境；Daemon 是该 Host 上负责注册、心跳、领取、启动、停止、恢复和本地资源管理的常驻服务。

需要研究：

- 一个 Host 能否运行多个 Daemon Profile，多个 Workspace 如何共享同一机器资源。
- Daemon 重启、升级、退出和系统休眠时，运行中任务如何收敛。
- 多个 Daemon 或用户会话访问同一工作目录时，如何协调文件锁、进程和容量。
- Host 的可用性、能力、资源容量和所有者共享授权如何表达。

### 4.2 Runtime / Provider Adapter

Runtime 是可被调度的具体执行目标。Provider Adapter 把平台统一执行契约映射到宿主实际协议。

宿主协议可能包括：

- CLI 参数与标准输入输出流。
- JSONL / JSON-RPC / App Server。
- ACP 等标准化 Agent Client Protocol。
- 厂商 SDK 或本地服务 API。
- 远端托管执行服务。

平台统一的是执行生命周期和结果契约，不要求所有宿主采用同一种底层通信协议。

适配器需要明确支持能力：启动、流式消息、工具事件、取消 / 中断、会话恢复、追加指令、Token / Cost Usage、文件与制品访问、结构化终态结果。能力需要可协商、可报告，并区分“宿主原生支持”和“平台补偿实现”。

### 4.3 Execution Environment / Workspace

执行环境负责提供 Agent 或 Script 实际工作的目录、代码和配置。

初步拆分：

| 输入类型 | 例子 | 需要解决的问题 |
|---|---|---|
| Git Repository | GitHub 仓库、指定 commit | Checkout、分支 / Worktree、补丁交接、合并和交付 |
| Local Directory | 成员本地已有项目 | 原地执行、路径授权、互斥或隔离副本、清理边界 |
| Non-Git Workspace | 普通目录、文件包、生成式项目 | 快照、增量同步、冲突处理、交付格式 |
| Artifact Input | XLSX、图片、文档、构建产物 | 内容寻址、版本、可访问性、校验和 |
| Multi-Repo Workspace | 前后端多个仓库 | 基准组合、依赖关系、跨仓库候选和统一交付 |

Multica 的 Git Worktree 是 Git 仓库场景下的一种隔离与交付策略，不应直接成为平台所有工作区的统一抽象。平台需要把“工作区生命周期”和“代码隔离策略”分开研究。

### 4.4 Session / Continuity

Session 是宿主工具的会话连续性载体；它与 Run、Issue 和 Workspace 关联，但生命周期不同。

需要分别回答：

- 一项 Issue 多次 Run 是否继续同一宿主 Session。
- 同一个 Agent 在不同 Runtime 上能否恢复同一 Session。
- Session 是否绑定本机凭证、CLI 版本、HOME / CODEX_HOME、工作目录或宿主账号。
- 宿主会话历史丢失、不可访问或恢复被拒绝时，如何生成连续性缺口并从 Work Context 恢复。
- 一个 Run 内部的宿主重试与平台创建新的 Run 如何区分。

平台的长期工作连续性应以 Issue Work Context、Decision、Artifact 和 Evidence 为基础；宿主 Session 是加速连续工作的执行资源。

### 4.5 Script Executor

Script 与 Agent 共用 Run、Runtime、授权、工作区和终态回报机制，但执行适配不同：

- Agent Adapter 启动智能体宿主并消费消息流。
- Script Executor 启动受管命令，采集 stdout / stderr、退出码、耗时、制品和副作用记录。

Script 不需要模拟 Agent Session，也不需要伪造模型消息。它应作为统一执行平面中的另一种执行类型。

## 5. 生命周期与恢复必须分层建模

初步将执行生命周期拆为以下阶段：

1. **Eligible**：工作已满足业务与 SOP 的启动条件。
2. **Queued**：已形成待派安排，等待 Runtime 容量。
3. **Claimed**：某个 Runtime 已领取该次执行。
4. **Preparing**：本地工作区、上下文、能力和授权正在准备。
5. **Started**：服务端确认实际执行开始。
6. **Running**：宿主进程已运行并持续产生执行事实。
7. **Terminal**：成功、失败、取消或超时等终态已确定。
8. **Settling**：用量、制品、会话、工作区和终态回执正在收敛。
9. **Recovered / Handoff**：原执行恢复、重新派发或交接到新的 Runtime。

这些阶段是研究模型，后续将与 Multica 的真实状态、专题二的 Node Attempt / Run 关系及宿主能力逐项对照。

重点研究以下恢复场景：

- Claim 成功但响应丢失。
- 准备环境时 Daemon 崩溃。
- Start 请求成功但回执丢失。
- Agent 进程运行时机器掉线。
- 用户取消与 Daemon 关闭同时发生。
- 宿主已完成但终态回报失败。
- 代码已修改但工作区交付尚未完成。
- 原 Runtime 离线，另一成员接管。
- 原 Leader Runtime 离线，Issue 由其他成员接续协调。

恢复策略需要区分：同一执行重连、同一 Run 的安全重试、新 Run 继续原工作、交接到新 Runtime、人工接管。对外部副作用先对账，再决定是否重放。

## 6. 3A 与其他专题的衔接

| 专题 | 3A 提供 | 3A 消费 |
|---|---|---|
| 专题一 | Run 的真实生命周期、Runtime 资源和执行归属、Session 与 Work Context 的关联 | Issue、负责人、授权、工作范围、代码基准和完成要求 |
| 专题二 | Agent / Script 执行、结构化结果回报、停止与恢复、Artifact 交付 | SOP Node Attempt、Execution Contract、Delegation Grant、候选和节点激活 |
| 专题 3B | 资产实际加载与运行环境信息、宿主能力清单 | Agent、Skill、Rule、SOP、Playbook 的版本与作用域 |
| 专题四 | Run / Trace / Usage / Artifact 的真实执行事实和采集覆盖 | 成本、质量、评测和改进归因要求 |
| 专题五 | 在线状态、执行进度、等待原因、结果与恢复信息 | 工作台对状态判断、操作选择和后果解释的需求 |

## 7. 本轮研究顺序

1. **Multica Runtime / Daemon 底层机制**：注册、心跳、Claim、Start、并发、权限、取消、终态回报和重启恢复。
2. **Agent 宿主适配机制**：统一 Backend 契约、CLI / JSON-RPC / ACP / SDK 的差异、会话恢复、流式消息、工具活动和取消语义。
3. **执行环境与工作区机制**：Prepare / Reuse、隔离、Local Directory、Git Worktree、制品和跨机接续。
4. **Script 受管执行**：命令执行、能力声明、输入输出契约、权限、超时、停止和结果回报。
5. **结合专题二形成平台设计**：确定 Host、Runtime、Adapter、Workspace、Session、Execution 的边界和生命周期。
6. **原型验收**：把专题二 17 项状态模型测试扩展为真实 Daemon、Runtime、宿主和工作区集成场景。

本版只建立研究框架和源码初步发现；最终架构以完成源码追踪、反例分析和原型验证后的专题评审稿为准。
