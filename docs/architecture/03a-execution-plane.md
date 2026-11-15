# 成员本地执行与工作交接

在工作台把 Issue 指派给 Agent 后，由该 Agent 获准使用的本地 Runtime 领取并执行。成员也可以先在自己的 CLI 或 IDE 工作，在支持的入口中关联后续执行，或事后把选定的变更和报告交给团队。三种入口汇合到同一 Issue。Multica Run 记录一次受管执行，宿主 Session 负责对话连续性。团队按实际来源查看交付，每个成员以自己的身份和工具授权接续工作。[宿主能力矩阵](execution-capabilities.md)

## 1. 从哪里开工

| 入口 | 如何与 Issue 关联 | 接手者看到什么 |
|---|---|---|
| 平台派发 | 现有队列把任务交给获准的 Runtime。Daemon 领取、准备上下文，调用宿主 Backend，向同一 Run 回报 | 指派和排队、实际开工、交付结果各自有记录。机器离线时可从 Issue 查看已共享内容和其他成员的进展 |
| 成员正在本机工作 | 在可识别原生线程和执行段的入口选择 Issue，从下一次可识别的输入开始关联。共享之前在本机预览选区 | 仅取得获准的消息、工具活动、变更或制品。有可信映射时可点回原 Run 和来源 |
| 事后补交 | 成员从本机选取文件、补丁、报告或说明，提交到已有 Issue，或为需要团队接续的新工作创建 Issue | 看到原发生时间（若可得）、提交时间、提交者和材料来源。仅有成员说明时按署名说明呈现 |

成员在本机接续 Issue 时，可以引用项目已关联的工程仓，或使用绑定在本机的目录。跨机时列出可获取的代码基准、变更和交付物。另一台机器从获得的材料建立自己的工作副本。仅保存在原机且尚未共享的修改，需要先由能访问原机的成员提供。[工作副本与跨机交接](../research/topic-03a/workspace-continuity.md) · [跨机交付实验](../research/topic-03a/machine-handoff.md)

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

## 3. 执行回执与资源释放

派发、领取、本地准备、真正开工、宿主终态、直接进程退出、派生进程清理、中心收到结果，是分别可观察的事实。界面在收到哪一种回执时就呈现哪一种。若进程仍可能写入共享位置，接手者先取得退出或隔离证据，再接续写操作。审批、撤权或超时发生后，中心控制状态和原机清理情况分别留痕。[清理与回报](../research/topic-03a/result-handoff.md)

丢失观察连接时重连并查原记录，已产生结果但中心漏收时重送原结果。Daemon 持有原任务、恢复请求被拒、尚未观察到工具调用且满足原生判据时，可在同一 Run 中用新 Session 重试一次。两个宿主调用的实际用量仍归该 Run。已有外部副作用或观测不完整时，先核对实际变更，再决定接续办法。[恢复判据](../research/03a-source-evidence.md#75-恢复拒绝与新会话重试的真实条件)

### ContextReceipt 与逐调用证据

Multica 在准备环境时汇总 brief、Skill、MCP、版本与摘要。恢复会话所携带的历史可在这份清单之外，按 task 再次提交会覆盖原准备回执。需要追溯实际采用情况时，在原 Run 下关联材料版本、通道、宿主调用及来源。文件写入、目录可发现、正文进入当前输入、只在聊天历史出现、工具实际调用，分别显示所能证明的事实。凡涉及摘要，同时指出摘要针对的对象和算法。可选材料缺少加载证据时，工作可继续。必需规则缺失时，相关核验等待补发或重新加载。[原生准备回执](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/context_receipt.go#L62-L89) · [按 task 更新](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/task_context_receipt.sql#L1-L8)

### 回报、消费与接续

服务返回的原报告、模型在 Hook 处理后实际收到的内容、SOP 节点最终采用的报告分别可查。消费时核对生产 Run、当前节点尝试、交付候选、规则和核验器版本、具名制品与当前授权。重复交付复用已有消费结果，旧候选的迟到报告回归其来源。原 Run 已结束且需再次核验时，新的派发产生后继 Run，并引用被拒报告。如果只读复验的目标、候选与标准仍有效，可沿用原节点尝试。换成员时使用接替者的授权、Runtime 和新 Run。[结果交接](../research/topic-03a/result-handoff.md) · [Hook 改写与后继复验](../research/topic-03b/existing-session.md)

## 4. 受管脚本与本地用量的能力边界

**受管脚本。** SOP 选择固定脚本、输入、候选和输出要求。产品设计将命令交给 Multica Run 和 Daemon，沿原工作目录、取消通道及附件通道返回退出状态、报告与具名制品。固定版 Backend 工厂提供编码 Agent 协议。现有确定性脚本实验使用 TeamAI 命令驱动，其中一次退出码为零但报告指出订单权限检查失败。该实验支持脚本与交付契约的设计，直接经 Multica 托管通用命令属于扩展能力。[Backend 工厂](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/agent.go#L502-L564) · [脚本与工作簿实验](../research/topic-03a/order-export-workspace.md)

**本地用量。** 中心 Task Usage 可存 Credits。固定版 Backend 与 Daemon 的本地用量结构尚缺 Credits，CodeBuddy 的适配器也尚缺 Stage 解析。设计通过对应 Backend、Daemon 和 Task Usage 回传原生计量身份、单位、覆盖和更正。成员使用的 Runtime 未报告某项费用时，该项显示未知。[Daemon 用量结构](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/types.go#L309-L322) · [分宿主与单位的计量规则](04-cost-quality-improvement.md)

## 5. 本地主动会话与 AgentObservation

成员选择允许共享的消息、工具名称与结果、参数与输出、模型用量和文件。可以只交结果。离线待发送的内容在恢复连接时按当前授权与选区核对，已移出选区的材料取消发送。观察记录可来自宿主原生事件、Multica 回报、Hook、OTel、转录或成员说明，界面注明各自的来源和覆盖区间。

原生线程、会话、回合、请求或工具调用的标识仅在其宿主和账号命名空间内解释。用派发时的绑定或已核对的原生映射把事件归回原 Run。多个来源观察同一执行时可保留各自的记录，计量按同一原生单元归并。一个私人会话跨越多个 Issue、共享记录缺段或身份不足时，只呈现能确定的范围。[工作归属与共享](execution-capabilities.md#一个执行怎样进-issue怎么停)

### 已有会话的控制与授权

共享材料、让模型读取已有聊天、把本轮输入控制交给执行者，分别由对应权限决定。受限工作继续使用原会话时，需要能核对历史读权、模型、工具与 Hook，并确保接手者控制下一次输入。成员仍可并发输入、旧历史含已失权正文或工具来源无法核对时，使用新会话，从当前 Issue 和获准来源重建所需内容。必需资料仍缺时，只等待依赖它的工作。[历史与来源读权实验](../research/topic-03b/project-knowledge.md) · [双客户端与 Hook 实验](../research/topic-03b/existing-session.md)
