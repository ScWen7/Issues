# 成员本地执行与工作交接

上下文投递和执行授权遵循[跨层业务契约与协作协议](cross-layer-contracts.md)，Run 状态与事件遵循[统一生命周期、状态机与事件模型](lifecycle-state-event-model.md)，Runtime 租约、旧 Daemon 隔离、取消回执、Run 幂等重取和接管遵循[核心协作一致性与并发控制模型](core-consistency-concurrency.md)。本专题维护成员本地执行的具体行为与适用边界。
Main Bot 跨多个成员 Runtime 的协调、委派回唤、状态恢复和交付汇总机制研究见[Main Bot 跨 Runtime 持续协调机制](../research/mainbot-runtime-coordination.md)。本专题仍以 Multica 原生执行链为基础，不另建执行控制平面。

在工作台把 Issue 指派给 Agent 后，由该 Agent 获准使用的本地 Runtime 领取并执行。成员也可以先在自己的 CLI 或 IDE 工作，在支持的入口中关联后续执行，或事后把选定的变更和报告交给团队。三种入口汇合到同一 Issue。Multica Run 记录一次受管执行，宿主 Session 负责对话连续性。团队按实际来源查看交付，每个成员以自己的身份和工具授权接续工作。[宿主能力矩阵](execution-capabilities.md)

## 1. 从哪里开工

| 入口 | 如何与 Issue 关联 | 接手者看到什么 |
|---|---|---|
| 平台派发 | 沿用原 Issue 的指派、评论协助或项目工作流。进入队列后，Daemon 在获准的 Runtime 领取并调用对应 Backend，沿原 Run 回报 | 从 Issue 查看该次 Run 的进展，以及已经交回的变更、报告或附件。机器离线时仍可读取已共享的材料 |
| 成员正在本机工作 | 成员在支持分段的入口选择有权提交的 Issue，从下一次可识别的输入开始关联。在本机预览并提交选定的消息、工具结果或制品 | 按权限看到成员实际共享的选区和宿主来源。能核对已有 Run 时关联原记录。仅核对到宿主轮次时标明该来源 |
| 事后补交 | 有评论权限的成员可从任何宿主回到原 Issue，用评论说明结论，并按权限上传补丁、报告或引用工程仓中的提交。需要团队接续新的目标时可另建 Issue | 看到提交者、提交时间、选定的材料及可知的原发生时间。只有成员说明时保留署名。能够查回原执行时再补上来源引用 |

### 首版提供进行中关联的条件

| 原来的工作入口 | 何时提供“从下一轮关联” |
|---|---|
| Codex | 成员授权接入原 App Server，或原宿主已启用并信任相应 Hook，且能将事件映射到该线程与轮次（`threadId + turnId`）。0.167.0-alpha.4 的源码支持这两条路径，0.144.6 前台终端另有通过开放端点接入第二客户端的实验。独立 IDE 入口仅在取得同样的身份与事件后提供此动作。[Codex 线程和 Hook](../research/topic-03a/codex.md) · [已有端点实验](../research/topic-03b/existing-session.md) |
| Claude Code | 已生效的 Hook 能用 `session_id + prompt_id` 定位下一次输入，工具活动按 `tool_use_id` 与结果对应。2.1.325 的受控 CLI 已产生这些事件。缺少分段依据时，成员仍能将选定成果交回原 Issue。[Claude Code 本地入口与实跑](../research/topic-03a/claude.md) |
| Qoder、CodeBuddy | 首版沿用 Qoder 的受管 ACP 通道和 CodeBuddy 的受管流式 CLI。成员已在独立 CLI 或 IDE 开工时，采用原评论与附件补交。现有适配器证据覆盖受管执行，Qoder SDK 和 CodeBuddy CLI 的现场回执覆盖各自的计量入口。独立会话的实时分段与跨入口身份仍未知。[宿主能力矩阵](execution-capabilities.md) · [本机回执](../research/topic-04/runtime-validation-1.1.88-2.181.0.md) |

### 接手者取得哪一版工作

成员可以从项目已关联的工程仓或本机绑定目录开工。交代码时，提交者注明工程仓和基准修订，引用可取得的提交，或在原 Issue 评论中上传补丁。交付区已有同名同类型文件的版本历史，接手者按具体附件版本取用补丁，用自己的仓库读权取得基准，再在自己的工作副本继续。接手者按本项工作约定核对交付。成员自述保留署名，附带的检查报告指向当时的候选，有可核对的生产 Run 时引用原记录。某项必需检查缺少证据时，接手者可以使用获准的方法针对收到的候选补查，保留此次检查的实际来源。此前的执行过程按已获准的证据记录。[Multica 交付区源码依据](../research/05-source-evidence.md) · [工作副本与跨机交接](../research/topic-03a/workspace-continuity.md)

仅存在原机的改动仍由能访问原机的成员补交。提交者可以在原 Issue 说明“另有修改待补”，接手者先使用已交回且可读的部分。外部仓库或报告的读权依各自来源检查，缺少所需材料时只显示该成员有权知道的缺项及可联系的人。分享补丁或获准的会话片段后，私人历史和原机输入控制仍按各自授权处理。[跨机交付实验](../research/topic-03a/machine-handoff.md) · [工作台上的接手操作](05-unified-workbench.md)

## 2. 执行由谁承载

| 对象 | 职责 |
|---|---|
| Issue、Run | Issue 提供目标、责任和本次约定。Run 记录派发、领取、执行、结果以及它服务的工作 |
| Daemon、Runtime | 处理本机注册、在线状态、容量、成员共享、领取和准备。平台按访问权显示实际可用资源 |
| Provider Backend | 把同一次执行交给对应宿主协议，取得消息、工具活动、终态和宿主原生身份。协议与可观察字段因宿主而异 |
| 工作目录与附件 | 原工作目录或工作副本承载本次修改。能被下一位成员使用的工件，通过已有附件通道或获准的工程仓交付 |
| 进程与 Session | Multica 管理启动、取消、等待和资源回收。宿主返回的 Session ID 可被后续 Run 引用，同一 Run 也可能经历恢复与重新开会话 |
| Trace、Result、ContextReceipt、Task Usage | 依原 Run 记录实际活动、结果、材料准备回执和用量。附加观察携带来源、授权、覆盖区间和原生身份 |

Multica 固定源码版本为 `fdfbfcd`。具体宿主的可用入口、取消与恢复行为、计量能力及证据类型见[能力矩阵](execution-capabilities.md)和[执行源码与实验记录](../research/03a-source-evidence.md)。

### 项目如何选择工作目录

项目配置工程资源时，可关联仓库，交给 Runtime 按约定修订准备工作副本。也可在 Desktop 的「项目 → 资源 → 本地文件夹」中选成员机器上的目录。两种执行模式保存在这条本地目录资源上，同一项目在不同机器可各自选择。

| 本地目录设置 | 普通 Issue Run 在哪里工作 | 对交付的影响 |
|---|---|---|
| 直接修改（`in_place`） | 在原文件夹读写当前内容。该 Daemon 上使用同一真实路径的普通 Issue Run 依次取得目录，非 Git 目录也可使用。 | 文件变更留在原机。跨机接手时，在原 Issue 提供接收者可取的修订、补丁或制品。 |
| 并行运行（`worktree`） | 在有提交的 Git 仓库为本次执行准备独立工作树，带入可重现的本地修改。准备快照要先取得原目录，完成后释放，各工作树可在剩余执行名额内并行。 | 后续轮次可接续已有工作分支，分支被占用时可能另行分叉。提交方标明实际分支与提交，负责人决定是否合入及采用哪版，检查针对相应候选。 |

已有资源按保存的模式运行，未指定时使用直接修改。Desktop 新增 Git 目录时，若服务端支持校验且目标机器声明支持工作树，界面会预选并行运行，成员可以改选。工作树条件不足时提示具体原因。成员可改用支持的环境，或在了解会直接写入原目录后另选模式。执行并发与恢复见[资源竞争与接管](core-consistency-concurrency.md#71-runtime-与执行容量)，设置及宿主行为见[目录模式源码依据](../research/topic-03a/workspace-continuity.md#项目目录模式与并发容量的源码依据)。

**协调与工作目录。** 只需读取已共享材料、分工或接收交付时，可使用与 Worker 写入目录隔离的已授权执行环境。项目绑定了同一本机原地目录时，普通 Issue Run 会受该目录的实际占用影响，应显示等待原因。Main Bot 自行改动文件时，和 Worker 一样按目标工作副本、写入权限和目录互斥执行。切换环境后的接续以原 Issue、分工和制品为依据。[目录绑定与互斥的源码边界](../research/mainbot-lifecycle-and-progress.md#83-普通-agent-协调对既有协作的影响)

## 3. 执行回执与资源释放

派发、领取、本地准备、真正开工、宿主终态、直接进程退出、派生进程清理、中心收到结果，是分别可观察的事实。界面在收到哪一种回执时就呈现哪一种。若进程仍可能写入共享位置，接手者先取得退出或隔离证据，再接续写操作。审批、撤权或超时发生后，中心控制状态和原机清理情况分别留痕。[清理与回报](../research/topic-03a/result-handoff.md)

丢失观察连接时重连并查原记录，已产生结果但中心漏收时重送原结果。Daemon 持有原任务、恢复请求被拒、尚未观察到工具调用且满足原生判据时，可在同一 Run 中用新 Session 重试一次。两个宿主调用的实际用量仍归该 Run。已有外部副作用或观测不完整时，先核对实际变更，再决定接续办法。[恢复判据](../research/03a-source-evidence.md#75-恢复拒绝与新会话重试的真实条件)

### ContextReceipt 与逐调用证据

Multica 在准备环境时汇总 brief、Skill、MCP、版本与摘要。恢复会话所携带的历史可在这份清单之外，按 task 再次提交会覆盖原准备回执。需要追溯实际采用情况时，在原 Run 下关联材料版本、通道、宿主调用及来源。文件写入、目录可发现、正文进入当前输入、只在聊天历史出现、工具实际调用，分别显示所能证明的事实。凡涉及摘要，同时指出摘要针对的对象和算法。可选材料缺少加载证据时，工作可继续。必需规则缺失时，相关核验等待补发或重新加载。[原生准备回执](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/context_receipt.go#L62-L89) · [按 task 更新](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/task_context_receipt.sql#L1-L8)

### 回报、消费与接续

服务返回的原报告、模型在 Hook 处理后实际收到的内容、SOP 节点最终采用的报告分别可查。消费时核对生产 Run、当前节点尝试、交付候选、规则和核验器版本、具名制品与当前授权。重复交付复用已有消费结果，旧候选的迟到报告回归其来源。原 Run 已结束且需再次核验时，新的派发产生后继 Run，并引用被拒报告。如果只读复验的目标、候选与标准仍有效，可沿用原节点尝试。换成员时使用接替者的授权、Runtime 和新 Run。[结果交接](../research/topic-03a/result-handoff.md) · [Hook 改写与后继复验](../research/topic-03b/existing-session.md)

## 4. 受管脚本与本地用量的能力边界

**受管脚本。** SOP 选择固定脚本、输入、候选和输出要求。产品设计将命令交给 Multica Run 和 Daemon，沿原工作目录、取消通道及附件通道返回退出状态、报告与具名制品。固定版 Backend 工厂提供编码 Agent 协议。TeamAI 命令驱动的研究记录可用于核对脚本退出、制品交接和内容检查各自的结果。通过 Multica 托管通用命令属于执行层扩展。[Backend 工厂](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/agent.go#L502-L564) · [命令与交付回执](../research/topic-03a/order-export-workspace.md)

**本地用量。** 中心 Task Usage 可存 Credits。固定版 Backend 与 Daemon 的本地用量结构尚缺 Credits，CodeBuddy 的适配器也尚缺 Stage 解析。设计通过对应 Backend、Daemon 和 Task Usage 回传原生计量身份、单位、覆盖和更正。成员使用的 Runtime 未报告某项费用时，该项显示未知。[Daemon 用量结构](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/types.go#L309-L322) · [分宿主与单位的计量规则](04-cost-quality-improvement.md)

## 5. 本地主动会话与 AgentObservation

成员选择允许共享的消息、工具名称与结果、参数与输出、模型用量和文件。可以只交结果。离线待发送的内容在恢复连接时按当前授权与选区核对，已移出选区的材料取消发送。观察记录可来自宿主原生事件、Multica 回报、Hook、OTel、转录或成员说明，界面注明各自的来源和覆盖区间。

原生线程、会话、回合、请求或工具调用的标识仅在其宿主和账号命名空间内解释。用派发时的绑定或已核对的原生映射把事件归回原 Run。多个来源观察同一执行时可保留各自的记录，计量按同一原生单元归并。一个私人会话跨越多个 Issue、共享记录缺段或身份不足时，只呈现能确定的范围。[工作归属与共享](execution-capabilities.md#一个执行怎样进-issue怎么停)

### 已有会话的控制与授权

共享材料、让模型读取已有聊天、把本轮输入控制交给执行者，分别由对应权限决定。受限工作继续使用原会话时，需要能核对历史读权、模型、工具与 Hook，并确保接手者控制下一次输入。成员仍可并发输入、旧历史含已失权正文或工具来源无法核对时，使用新会话，从当前 Issue 和获准来源重建所需内容。必需资料仍缺时，只等待依赖它的工作。[历史与来源读权实验](../research/topic-03b/project-knowledge.md) · [双客户端与 Hook 实验](../research/topic-03b/existing-session.md)
