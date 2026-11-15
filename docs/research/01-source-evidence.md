# 专题一源码研究依据

研究日期：2026-11-14。用途：支撑[统一工作生命周期](../architecture/01-unified-work-lifecycle.md)及其与专题二、三、四的职责边界。设计全局关系见[统一架构总览](../architecture/overview.md)。

## 1. 版本、方法与核验记录

本轮先完整阅读产品架构设计输入，再分别研究三个项目的模型、实际执行调用链及代表性测试源码。下列提交与当时获取的上游 HEAD 一致；所有引用固定到提交，不随 `main` 漂移。

| 项目 | 固定研究提交 | 本轮主要范围 |
|---|---|---|
| Multica | `dfcc633dda2e8ee865b2feb23a1778ce20f93988` | Issue、负责人、Leader、评论派发、Run、Daemon、离线、上下文收据、Project Workflow |
| TeamAI | `94a7514629ae66cee3dc728fad7b8d5cb263114b` | Workflow 引擎与 driver、作用域、资源来源与版本、执行报表、Scorer、Benchmark、自改进 |
| LoopForge | `97b3cdc2f29a88e8767a8dc6c03bfb8865622653` | SOP 图、节点执行、门禁、返工、Sub-SOP、制品、Trace、评测与建议应用 |

本轮完成静态源码和测试用例审阅，逐项记录测试输入、动作与断言。测试执行状态：本轮未执行。系统运行、真实 Agent 与多机业务演练按后续实现计划取证。

“代码事实”描述已读实现；“提示词约定”描述交给 Agent 遵循的要求；“设计推论”是本平台的选择。三类结论分别标注依据。本文件以固定上游链接作为正式依据，不依赖本地临时研究副本长期存在。

## 2. Multica：共享工作与本地执行

### M1. Issue / 子 Issue 承载工作，内部 Task 名称对应产品 Run

**代码事实：** `AgentTaskQueue` 保存 agent、issue、runtime、会话、开始结束时间、输出、失败、重试和重跑关系，描述一次执行。CLI 术语测试要求 `run-id`、`per-run`、`polls for runs`，排除旧的产品 Task 叫法。

证据：[执行模型](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/pkg/db/generated/models.go#L124-L195)、[Run 术语测试](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/cmd/multica/run_terminology_test.go#L10-L43)。

**专题一方案推论：** 当前候选方案参考 Multica 的 Issue 工作机制：父子 Issue 共用模型，具体分工优先表达为子 Issue，也允许在同一 Issue 内委派；Run 直接关联实际工作的 Issue，Leader 的父事项协调 Run 也挂在父 Issue 上。`AgentTaskQueue` 的内部名称与产品术语分别解释；当前方案优先复用现有工作与执行记录。

### M2. 工作负责人与被邀请参与不同，责任归属区分处理人与发起人

**代码事实：** Issue 支持 Member、Agent、Squad 负责人及父子 Issue；`WillEnqueueRun` 按负责人、状态和可用性判断是否派发。Squad 主责会解析 Leader，但非主责 Squad 也可能经 `@squad` 进入 guest Leader 路径。在数据模型上，`Issue` 表具备 `AssigneeType`/`AssigneeID`、`CreatorType`/`CreatorID` 与 `RequesterUserID`；`issueToResponse` 将其分别序列化为 `AssigneeID`、`CreatorID` 与 `RequesterID`。Member 创建时 `CreatorID` 记录该成员；Agent 触发时 `RequesterUserID` 记录发起 Member。

证据：[Issue 模型字段](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/pkg/db/generated/models.go#L931-L963)、[API 响应映射](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/internal/handler/issue.go#L485-L514)、[触发判断](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/internal/service/issue_trigger.go#L103-L212)、[Leader 派发](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/internal/handler/squad.go#L1234-L1291)。

**提示词约定：** guest Leader 不得推进父 Issue 状态；拥有 Issue 的 Leader 有推进责任。[负责与 guest 边界](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/internal/handler/squad_briefing.go#L181-L191)。

**设计推论：** “仅指定 Squad 主责才启动自动协调”是本平台输入要求，上游 guest 路径单独记录。在责任模型上，Multica 原生支持随步骤流转的当前处理人（Assignee）与发起线索（Creator/Requester），但缺少全局稳定的独立人工总责人概念。平台需在业务模型上扩展总责人角色，显式锚定人工最终责任，防止 Agent/Squad 协作时责任虚化。

### M3. Leader 是短轮次协调，规划质量主要依赖 Agent

**代码事实：** Worker 回报可唤醒 Leader，评论解析与权限检查后创建执行记录。Leader 可记录 action、no_action、failed，普通更新不必触发新的委派。

**提示词约定：** Leader 阅读目标、按能力选择成员、委派后结束，后续结果到达再协调；同一工作不要同时通过子 Issue 和父 Issue 提及重复派发。拆解是否合理、选人是否正确、总体目标是否满足，并非这些提示词本身能保证。

证据：[Leader protocol](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/internal/handler/squad_briefing.go#L44-L95)、[Worker 回报路由](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/internal/handler/comment.go#L2712-L2732)。

**设计推论：** 可借鉴按重要工作变化唤醒 Leader；目标、授权、依赖和验收边界仍需成为平台工作规则。

**代码事实：** 父子 Issue 已有 `child_done` 系统唤醒规则：按子 Issue 的 stage 汇总进度，前序阶段均关闭且后续阶段仍等待时，以及全部子 Issue 关闭时，唤醒父 Issue 的当前负责人；Agent 进入执行、Squad 解析 Leader、Member 收到通知。规则复用已有唤醒收据与 Run 机制，默认开启，可按工作区或事项设置。`closed` 包含取消，触发事实保留取消计数。子 Issue 指派给 Squad 时，针对该负责人的工作唤醒交给子 Squad Leader。满足前述父级唤醒条件时，`resolveWakeTarget` 读取父 Issue 当时的 Assignee；父项由 Squad 主责时才唤醒其 Leader。

证据：[系统规则与默认指令](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/internal/service/issue_wakeup_system.go#L24-L76)、[阶段条件实现](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/internal/service/issue_wakeup_condition.go#L653-L710)、[父负责人与唤醒目标解析](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/internal/service/issue_wakeup_system.go#L303-L353)、[单事项规则配置](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/internal/service/issue_wakeup_system.go#L726-L778)。

**提示词约定与边界：** 默认指令要求被唤醒者检查依赖、判断取消工作是否仍需要，再启动后续阶段或汇总；阶段关闭触发协调，业务成功、依赖结果和阶段验收由相应判断确认。**设计推论：** 优先复用该父子事项回收机制，补充本平台的结果判断和验收约束，不重建平行的分工状态体系。同时确立“子 Squad 限一层嵌套”的明确规则，防止递归发散引发额度失控。

### M4. 评论保存、派发、Agent 读取和工作验收是不同事实

**代码事实：** 评论保存后再尝试派发，部分目标触发失败不使整条评论失败；`/note` 不启动 Agent，steering 有意图判断和投递收据。通用完成路径保存执行结果、会话、分支及活动，没有逐项业务验收检查。

证据：[保存与派发](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/internal/handler/comment.go#L1948-L1988)、[完成路径](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/internal/service/task.go#L4712-L4745)。

**提示词约定：** 未使用 Project Workflow 时，自有 Issue 的 Leader 在目标满足后移入 `in_review`，`done` 留给人工或既有集成；使用 Workflow 时遵循该工作流的步骤，按实际步骤推进。相应测试核对提示词文本；各状态写入的人工批准约束需要分别检查。[默认状态职责](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/internal/handler/squad_briefing.go#L114-L123)、[Workflow 状态职责](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/internal/handler/squad_briefing.go#L152-L171)。

**设计推论：** Conversation、Decision、Run 结果、子 Issue 结果核验与父 Issue 验收需要各自明确效力，消息保存、执行结束和接受交付分别取证。验收是对应 Issue 上关联标准、制品和证据的 Decision / 记录，不必为了验收额外创建一个工作事项。

### M5. Project Workflow 已直接参与工作权威，平台强制规则与约定需清晰切分

**代码事实：** Multica 已有工作区共享 status 目录，包含七个内置状态和 unstarted / started / done / closed 四类生命周期；自定义状态按类别参与生命周期判断。Project Workflow 从同一目录选择并排列状态，规定各状态 handler 和步骤指令；未单独配置的项目使用工作区 Default Workflow。具备步骤绑定的 Run 在命名工作流或启用交接的 Default Workflow 中接受过期步骤检查（`issue_workflow_entry.go#L80-L86`、`#L120-L123`）。未启用交接的 Default 有意保留原有工作方式，这是守卫的适用范围。

证据：[status 目录与生命周期](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/internal/issuestatus/issuestatus.go#L1-L56)、[Workflow 职责与默认值](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/internal/issueworkflow/issueworkflow.go#L1-L19)、[Issue 更新调用](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/internal/handler/issue.go#L4235-L4258)、[过期步骤写入检查](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/internal/handler/issue_workflow_entry.go#L80-L86)、[检查适用范围与默认工作流例外](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/internal/handler/issue_workflow_entry.go#L120-L123)、[Leader 工作流约束](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/internal/handler/squad_briefing.go#L144-L171)。

**提示词约定：** 默认 Leader 指令要求在目标满足后移入 `in_review`，由人工或既有集成完成事项（[默认状态职责](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/internal/handler/squad_briefing.go#L114-L123)）；采用 Workflow 时遵循对应步骤（[Workflow 状态职责](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/internal/handler/squad_briefing.go#L152-L171)）。这些指令描述 Leader 的工作责任；人工验收决定的统一完成校验属于本平台的扩展要求。

**代码事实：** PR 自动完成读取事项的关闭选项、关联 PR 状态和项目允许的目标状态；全部关联 PR 合并且条件满足时，系统直接推进 Issue，并以 `system` / `pr_automation` 记录来源。该入口按 PR 与状态条件执行，已读路径未校验指定验收人对候选的业务接受决定。平台已有单事项关闭 PR 自动完成的选项。自定义成功完成状态归入 done 生命周期，覆盖验收要求时应按类别识别。

证据：[PR 自动完成判定与单事项开关](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/internal/handler/pr_auto_complete.go#L173-L242)、[系统状态推进与来源记录](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/internal/handler/pr_auto_complete.go#L280-L318)、[自定义终态与生命周期](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/internal/issuestatus/issuestatus.go#L1-L9)。

**专题一方案推论：** 当前方案以 Multica status 与 Project Workflow 为工作平面主干作为工作假设。人工验收要求统一覆盖成员、Agent、流程、PR 自动完成等集成入口，以及成功完成类别的全部状态，校验指定验收人对当前候选和标准的有效决定。人工验收事项默认关闭原生 PR 自动完成；自动入口接入统一校验后可依据有效决定推进。过期步骤守卫按原生适用范围复用，普通 Default 工作保留既有行为，新增流程需求交专题二评估。

**代码事实与边界：** 普通改负责人和包括 `cancelled` 在内的状态变更不默认中断正在执行的 Run，新负责人的 Run 可以与既有 Run 并存。Workflow handoff 可显式请求停止前负责人的 Run；该操作保留同 handler 的 Run，也跳过 Agent 自身发起交接的 Run。另有独立收尾规则：Issue 进入 done / closed 时停用普通 wakeup 规则，并取消尚未启动的 wakeup Run；`child_done` 系统规则保持配置、在关闭期间静默，重开后可恢复，已经运行的工作仍使用 Stop 控制。状态收尾据此区分未启动的唤醒执行和正在进行的执行。

证据：[普通变更与显式停止入口](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/internal/handler/issue.go#L4400-L4425)、[前负责人停止范围](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/internal/handler/issue_workflow_entry.go#L300-L326)、[关闭事项的 wakeup 收尾](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/internal/service/issue_wakeup.go#L250-L264)、[普通规则与未启动 Run 范围](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/pkg/db/queries/wakeup.sql#L67-L74)、[系统规则关闭期间行为](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/internal/service/issue_wakeup_system.go#L455-L465)。

**设计推论：** 换人、取消事项、停止执行和结果是否仍可采纳分别说明；若本平台要求停止旧执行或排除过期结果，应显式规定操作与适用范围，执行结果按对应原生控制行为确认。

### M6. Runtime、上下文收据与恢复有实现，但有保证边界

**代码事实：** Daemon 准备实际执行环境后才报告 running，再调用 `backend.Execute`。Runtime 有跨 Agent 的并发容量；断联有重连宽限和后继处理，完成上报可由本地持久队列保留。

证据：[执行前环境准备](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/internal/daemon/daemon.go#L8742-L8784)、[实际执行](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/internal/daemon/daemon.go#L9958-L9984)、[断联处理](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/cmd/server/runtime_sweeper.go#L34-L89)、[持久终态上报](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/internal/daemon/terminal_report_queue.go#L34-L65)。

`ContextReceipt` 区分 delivered、verified、verified_other_version、unverified、not_delivered。它描述交付方式和加载证据，不证明 Agent 正确采用了知识。[收据定义](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/internal/daemon/context_receipt.go#L18-L90)。

**设计推论：** 断联首先记录连接状态，执行结果通过恢复后的事实确认；跨机接续核对制品与会话条件。“已下发、可加载、已采用、已正确完成”分别取证。

### M7. 会话关联与 Runtime 共享授权已有基础

**代码事实：** Run 已关联 Issue、Runtime、宿主 session 和工作目录。同一 Agent 在同一 Issue 上的后续执行会查找既有会话，并仅在 Runtime 相同时给出该宿主 session；缺失或不可延续的会话有明确缺口标记。评论还可按显式 steering 意图关联运行中 Run，并保留投递收据。本地交互接入从这些现有能力继续核对和扩展。

证据：[Run 关联字段](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/pkg/db/generated/models.go#L124-L152)、[Issue 会话延续及缺口](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/internal/handler/daemon.go#L3518-L3554)、[steering 意图](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/internal/handler/comment.go#L1447-L1454)、[关联与收据测试](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/internal/handler/comment_agent_steer_test.go#L61-L114)。

**代码事实：** Runtime 已区分所有者、指定成员共享和工作区公开；工作区成员资格之外还检查机器所有者的使用同意。管理员角色不覆盖私有 Runtime 的使用同意，改变共享范围仅限所有者。共享不授予机器管理权。

证据：[机器使用同意判断](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/internal/service/runtime_access.go#L10-L15)、[使用与共享权限边界](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/internal/handler/runtime.go#L1070-L1086)。

**设计推论与未验证项：** 复用既有会话、Run 归属和机器共享同意机制，按需补足正式决定、结果回传与 Execution Contract；不从零重做权限层。机器共享、目标仓库、业务数据及外部操作分别核对授权。后续验证重点是外部本地会话导入和跨成员、跨机器接续。

**主要调用链：** Issue 创建或变更 → `WillEnqueueRun` → Agent / Leader enqueue → Runtime claim 与容量检查 → 环境准备 → `StartTask` → `backend.Execute` → Trace / usage / receipt → 终态上报 → 完成或失败记录。Leader 委派评论 → Worker Run → Worker 更新 → 后继 Leader Run，形成协作链，业务验收按相应工作约定取证。

## 3. TeamAI：能力资源与真实流程引擎

### T1. Workflow 当前是实际执行引擎

**代码事实：** 定义包含依赖、子流程、并行、循环、人工输入、工作副本、角色、模型、输出和预算；RunState 保存定义、sourceHash、团队资源基准、step / pass / attempt 与交付回执。结果上报检查输出契约、执行归属和预算，不是仅输出提示词。

证据：[节点定义](https://github.com/Tencent/teamai-cli/blob/94a7514629ae66cee3dc728fad7b8d5cb263114b/src/workflow/types.ts#L63-L164)、[运行定义](https://github.com/Tencent/teamai-cli/blob/94a7514629ae66cee3dc728fad7b8d5cb263114b/src/workflow/types.ts#L473-L595)、[启动校验](https://github.com/Tencent/teamai-cli/blob/94a7514629ae66cee3dc728fad7b8d5cb263114b/src/workflow/engine.ts#L1435-L1555)、[结果校验](https://github.com/Tencent/teamai-cli/blob/94a7514629ae66cee3dc728fad7b8d5cb263114b/src/workflow/engine.ts#L3033-L3100)。

**主要调用链：** workflow 命令 → `startRun` → 定义及子流程树固定 → 输入校验 → `createRun` / `TeamPin.capture` → `leaseNext` / `reconcileRun` → driver 执行 → `reportAttempt` → 输出、预算及工作副本检查 → 后继步骤或结束 → 运行报告。[本地 driver](https://github.com/Tencent/teamai-cli/blob/94a7514629ae66cee3dc728fad7b8d5cb263114b/src/workflow/drivers/local/local-driver.ts#L60-L98)。

**设计推论：** 当前 TeamAI 已涵盖真实执行；专题二需比较它与 LoopForge 的机制重叠。

### T2. 人工回答绑定具体执行，但来源线索不是平台身份

**代码事实：** HITL 支持 approve / choose 和 required，回答绑定 pass，拒绝陈旧回答；重试可保留先前 pass 并重新安排依赖。回答来源依据 TTY、driver、dashboard 和 Agent 环境线索，代码说明其是 evidence，并非身份安全证明。

证据：[来源识别](https://github.com/Tencent/teamai-cli/blob/94a7514629ae66cee3dc728fad7b8d5cb263114b/src/workflow/run-controls.ts#L88-L180)、[重试入口](https://github.com/Tencent/teamai-cli/blob/94a7514629ae66cee3dc728fad7b8d5cb263114b/src/workflow/run-controls.ts#L643)。

**设计推论：** 借鉴具体对象和版本绑定、定向返工；平台人工决策仍需明确决定者、作用范围及权限，Member 身份通过平台既有身份关系确认。

### T3. 角色知识与成员可执行能力分开，来源也并非只有 Git

**代码事实：** step role 改变 knowledge 类资源；env / hooks / MCP / models 等 channel 仍受成员角色限制。未知角色不回退到全部知识。`pull` 已有 git、http、self 三种来源路径。

证据：[资源作用域](https://github.com/Tencent/teamai-cli/blob/94a7514629ae66cee3dc728fad7b8d5cb263114b/src/resource-namespaces.ts#L26-L68)、[来源分支](https://github.com/Tencent/teamai-cli/blob/94a7514629ae66cee3dc728fad7b8d5cb263114b/src/pull.ts#L152-L215)。

`TeamPin` 绑定 commit 与本地 patch，Scorer 可按 Run 的 pin 读取当时 rubric；recall 的 RELEVANT 仅表示值得阅读，不表示问题已被覆盖。[版本固定](https://github.com/Tencent/teamai-cli/blob/94a7514629ae66cee3dc728fad7b8d5cb263114b/src/workflow/team-pin.ts#L79-L130)、[Scorer 版本读取](https://github.com/Tencent/teamai-cli/blob/94a7514629ae66cee3dc728fad7b8d5cb263114b/src/scorers/run-scorers.ts#L97-L133)、[召回边界](https://github.com/Tencent/teamai-cli/blob/94a7514629ae66cee3dc728fad7b8d5cb263114b/src/recall.ts#L1085-L1128)。

**设计推论：** 专题三借鉴来源、范围和运行版本追溯；不以 Git 为平台前提，也不通过角色上下文扩大执行权限。

### T4. 执行证据与共享报表有意区分

**代码事实：** 执行尝试报告有模型、工具、Token、成本、变更和结果；Agent observation 保留实际观测缺口。共享 report 每 step / pass 一条，但明确省略原始 message、outputs、results 和 session ID。

证据：[尝试报告](https://github.com/Tencent/teamai-cli/blob/94a7514629ae66cee3dc728fad7b8d5cb263114b/src/workflow/step-state.ts#L94-L128)、[观测约定](https://github.com/Tencent/teamai-cli/blob/94a7514629ae66cee3dc728fad7b8d5cb263114b/src/agent-observation.ts#L1-L8)、[共享报表省略内容](https://github.com/Tencent/teamai-cli/blob/94a7514629ae66cee3dc728fad7b8d5cb263114b/src/workflow/records.ts#L228-L242)。

Scorer 可绑定 run:step:pass 或 session，证据规划会保留 commit、范围和会话缺口。[评价对象](https://github.com/Tencent/teamai-cli/blob/94a7514629ae66cee3dc728fad7b8d5cb263114b/src/scorers/subject.ts#L1-L29)、[证据缺口](https://github.com/Tencent/teamai-cli/blob/94a7514629ae66cee3dc728fad7b8d5cb263114b/src/scorers/scoring-evidence.ts#L114-L139)。

**设计推论：** Dashboard 摘要引用完整工作事实；评分对象与业务验收对象明确关联，缺失数据单独标记。

### T5. 自改进提案生成不证明效果已被验证

**代码事实：** Benchmark 有起始基准、成功标准、来源失败、对照变量和重复次数；默认 self-improvement 流程只有 plan → improve，后者要求修改资源、生成回归试题并提交 PR，没有后续执行 Benchmark 对照的步骤。

证据：[Benchmark 对照定义](https://github.com/Tencent/teamai-cli/blob/94a7514629ae66cee3dc728fad7b8d5cb263114b/src/benchmark/suite.ts#L52-L155)、[回归任务标准](https://github.com/Tencent/teamai-cli/blob/94a7514629ae66cee3dc728fad7b8d5cb263114b/src/benchmark/suite.ts#L498-L542)、[完整默认改进流程](https://github.com/Tencent/teamai-cli/blob/94a7514629ae66cee3dc728fad7b8d5cb263114b/workflows/teamai-self-improvement.yaml#L1-L36)。

**提示词约定：** Agent 应找到共同原因，且无共同原因时不变更；归因和收益通过实际证据与验证判断。**设计推论：** 专题四应把提案、对照验证、审核发布和后续观察分别表达。

### T6. 上报成本、估算与未知有明确区别

**代码事实：** `priceTokens` 优先工具上报金额，否则按价格目录估算并记录版本；缺少适用价格时返回 null，不应用订阅或企业折扣。[定价实现](https://github.com/Tencent/teamai-cli/blob/94a7514629ae66cee3dc728fad7b8d5cb263114b/src/token-usage/pricing.ts#L17-L71)。

**设计推论：** 保留原始来源、单位、实际模型、尝试归属及缺失情况；工具上报也需注明来源，按上报、估算和最终账单等来源分别呈现。统计公式归专题四。

## 4. LoopForge：SOP 执行、验证与评测

### L1. Run 是整张 SOP 图，Task 主要是派发记录

**代码事实：** Run 包含流程快照、节点、事件、遥测、制品及 HumanContext；NodeRun 再有 attempt、rework、session、GateResult 和 child Run。Task 关联 Issue、Workflow、Run，主要表达派发状态。

证据：[Run](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/domain/run.go#L10-L57)、[NodeRun](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/domain/run.go#L141-L179)、[Task](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/domain/task.go#L5-L18)。

**设计推论：** 本平台 Run 与其 Run 不同层；需要区分 SOP Execution、承载具体工作的 Issue / 子 Issue 和实际执行尝试。保留外部项目的真实 Task 名称用于研究，不把该派发模型复制为本平台的独立业务 Task。

### L2. 图调度与定向返工有真实实现

**代码事实：** 启动校验并保存图；就绪节点要求前驱 succeeded，分支并行执行，返工由 RejectTo 定向影响目标及后继，不向 DAG 塞入循环。自修正 iteration、错误重试 attempt 和评审返工是不同机制。

证据：[启动](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/run_start.go#L53-L182)、[调度与分支收敛](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/node_execute.go#L16-L187)、[依赖与图校验](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/workflow_graph.go#L154-L272)、[定向返工](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/run_ops.go#L271-L355)。

**主要调用链：** `StartWithRepositoriesContext` → 流程校验及快照 → `execute` / `readyNodes` → `executeNode` → Agent / Script / approval / Sub-SOP → 产物及门禁检查 → 节点结果 → 等待、返工、失败或 `finishAt`。

**设计推论：** 借鉴有界重试和定向修复，但统一记录原因和影响，三种恢复分别记录原因、次数与影响。

### L3. 结构化 pass、产物存在、人工放行与业务正确不同

**代码事实：** GateResult 区分 pass / rework / fail / human，并检查 reason、返工目标和人工动作。Agent pass 后仍检查产物和命令；Artifact Contract 主要检查文件存在、常规文件与大小。Approve 可使等待节点 succeeded，Pass 可人工放行部分失败状态。

证据：[Gate 结果约束](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/gate_submit.go#L40-L110)、[执行后验证](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/node_execute.go#L877-L1044)、[产物检查](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/artifacts.go#L236-L269)、[人工处置](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/run_ops.go#L140-L241)。

**提示词约定：** Agent 应提交正确的门禁判断，代码检查提交形式，判断正确性依据验证结果。**设计推论：** 人工放行保留原测试失败事实；XLSX 的内容和可见范围另有对应检查。

### L4. 图快照、能力版本、重试和跨成员交接仍需区分

**代码事实：** 执行优先使用冻结的图，但 `workflowAgent` 按当前 catalog 解析角色。手动 Retry 复用并改变原 Run；Agent 恢复可接原 session，Script 从头运行。Sub-SOP 建 child Run，默认共享 checkout，并导入选定产物。

证据：[冻结图读取](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/workflow_graph.go#L41-L50)、[角色解析](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/assets.go#L203-L214)、[Retry / Resume](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/run_ops.go#L350-L634)、[Sub-SOP](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/sop_node.go#L14-L242)。

**设计推论：** 不宣称“所有能力都被冻结”；保留每次实际尝试及资源版本。共享 checkout 是该项目执行布局；跨成员协作通过可交换制品与各自工作副本接续。

### L5. SOP 成功与交付验收之间仍有边界

**代码事实：** 顶层流程成功后尝试依据关联 MR 标记 delivery，子流程成功不交付父 Issue；制品带 Run、节点、attempt、摘要和时间。[交付收敛](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/node_outcome.go#L319-L396)、[制品引用](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/domain/run.go#L231-L248)。

**设计推论：** 工程交付信号支持交付候选；业务验收关联标准、被验制品和环境作出判断。

### L6. 评测到建议应用有实现，Benchmark 前置与完整成本尚未证明

**代码事实：** 终态 Run → `BuildCatalog` / `BuildFacts` → `BuildPrompt` → 模型评分 → 加权与格式校验 → 保存评测 → 人工选择建议 → `ApplyRecommendation` → 修改 Workflow / Agent。Facts 是裁剪后的评测视图，不是全部原始证据。

证据：[事实提取](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/runeval/facts.go#L13-L119)、[评测 prompt](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/runeval/prompt.go#L11-L89)、[建议应用](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/runeval/apply.go#L10-L108)、[人工应用链](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/httpapi/run_eval.go#L225-L404)。

已读应用链没有将 Benchmark 对照设为前置。费用区分 reported / estimated / unknown，analytics 可按公开价重估副本；评测调用中的 usage 在所读执行链被忽略。[费用语义](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/domain/run.go#L181-L194)、[估算视图](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/repo/analytics_pricing.go#L8-L49)、[评测调用](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/httpapi/run_eval.go#L481-L505)。

**设计推论：** 专题四需要明确评价覆盖、评测自身成本、改进验证与发布过程；建议应用与效果验证分别记录结果。

## 5. 代表性测试源码

以下均已阅读，**本轮未执行**。测试证明其断言覆盖的行为，不证明所有宿主、真实模型或生产环境均符合。

| 项目 | 测试入口 | 断言关注点 |
|---|---|---|
| Multica | [负责人 / guest 状态契约](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/internal/handler/squad_parent_status_contract_test.go#L45-L135) | 提示词中的主责、guest 与交付状态边界 |
| Multica | [steering](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/internal/handler/comment_agent_steer_test.go#L61-L114) / [Runtime 容量](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/internal/service/task_runtime_concurrency_db_test.go#L52-L78) | 意图与调用权；同一 Runtime 跨 Agent 的容量 |
| Multica | [共享 Runtime](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/internal/handler/runtime_sharing_test.go#L20-L55) / [Workflow 交接停止范围](https://github.com/multica-ai/multica/blob/dfcc633dda2e8ee865b2feb23a1778ce20f93988/server/internal/handler/issue_workflow_test.go#L1350-L1367) | 指定共享成员可使用、共享修改由所有者负责；显式停止不波及其他 Squad 的 Run |
| TeamAI | [人工回答](https://github.com/Tencent/teamai-cli/blob/94a7514629ae66cee3dc728fad7b8d5cb263114b/src/__tests__/workflow-run-controls.test.ts#L153-L180) / [定向重试](https://github.com/Tencent/teamai-cli/blob/94a7514629ae66cee3dc728fad7b8d5cb263114b/src/__tests__/workflow-run-controls.test.ts#L397-L455) | required、选项、陈旧 pass、失效执行与产物依赖 |
| TeamAI | [资源版本固定](https://github.com/Tencent/teamai-cli/blob/94a7514629ae66cee3dc728fad7b8d5cb263114b/src/__tests__/workflow-team-pin.test.ts#L79-L109) / [评分对象](https://github.com/Tencent/teamai-cli/blob/94a7514629ae66cee3dc728fad7b8d5cb263114b/src/__tests__/workflow-scoring.test.ts#L114-L125) | 同一 Run 用旧资源；具体交付 pass 与整个流程区分 |
| LoopForge | [并行调度](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/parallel_branches_test.go#L50-L151) / [Gate](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/gate_submit_test.go#L12-L74) | 分支重叠与收敛；四种终态、无目标返工、人工动作 |
| LoopForge | [Sub-SOP](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/sop_node_test.go#L15-L122) / [暂停恢复](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/lifecycle_test.go#L204-L255) | 子产物与父交付边界；Agent 续接和 Script 重跑 |
| LoopForge | [评测建议应用](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/httpapi/run_eval_test.go#L42-L120) / [定价](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/repo/analytics_pricing_test.go#L37-L74) | mock 评分后应用；估算不覆盖原始金额，unknown 不变零 |

## 6. 跨项目比较与专题一取舍

| 机制 | Multica | TeamAI | LoopForge | 专题一方案中的取舍 |
|---|---|---|---|---|
| 工作中心 | Issue、子 Issue、同事项委派与阶段唤醒 | 本地 workflow / session 及资源 | Issue 派发与 SOP Run | 沿用 Multica 的同一 Issue 模型，不新增业务 Task 层 |
| 流程控制 | status 目录、Project Workflow 与负责人交接 | 实际依赖引擎、driver、pass | SOP 图、NodeRun、门禁 | Multica 维持事项主干；SOP 按需接入，不保留三套独立权威 |
| Run 语义 | 一次 Agent 执行，直接关联 Issue | 整个 workflow 执行及步骤尝试 | 整图执行及节点尝试 | 沿用一次实际尝试；Leader Run 关联其协调的 Issue，流程实例单独表达 |
| 上下文 | briefing、引用、加载收据、Issue / Runtime 会话关联 | 作用域、资源 pin、观测 | 图快照、输入产物、当前角色 | 复用已有连续性基础，工作事实唯一，资源版本和实际加载可追溯 |
| 交付信号 | Run 输出、Review / PR、Issue 状态 | 输出契约、交付回执、Scorer | 产物、门禁、MR、图成功 | 验证与业务验收逐层说明依据；验收在对应 Issue 上留下 Decision / 记录 |
| 改进 | 可供追溯的执行事实 | Scorer、Benchmark、改进提案 | Run 评测与建议应用 | 统一证据，补齐验证、审核发布和后续观察 |

专题一当前方案重点参考 Multica 的工作机制，并结合 TeamAI / LoopForge 研究能力资源、可执行 SOP、门禁和评价。跨项目同名对象按语义比较，复用与扩展的取舍留在专题方案中，整体整合方式在五个专题贯通后确定。

| 采用方式 | 专题一探索范围 | 证据与约束 |
|---|---|---|
| 原生复用 | Issue / 子 Issue、负责人、评论委派、Leader 唤醒、stage 回收、status / Project Workflow、Issue → Run → Runtime、会话关联、机器共享同意 | 对应 M1—M7 的固定源码；复用不表示已完成本平台运行验收 |
| 配置或工作约束 | Squad 主责才自动协调、步骤 handler 与指令、明确验收人和交付要求、换人与取消时是否同时停止旧 Run | 使用既有入口并明确本平台约束；不得称上游已提供不可绕过的业务保证 |
| 必要扩展 | Issue 上明确的 Decision / 验收记录、可核验的 Execution Contract 与证据关联、SOP Execution 接入，以及后续正式知识与改进闭环 | 从实际工作缺口增补；复用统一工作对象、Work Context、Execution Contract 和 Evidence & Feedback，不另建 Task、状态或证据权威 |

## 7. 后续专题研究入口与未验证项

| 专题 | 后续研究问题 | 当前专题的研究输入 |
|---|---|---|
| 二 | 以 Multica Project Workflow 为主干比较三套流程机制，研究完整 / 局部 SOP、节点与工作对象映射 | 复用 Issue / 子 Issue、Run、Decision；SOP Execution 不夺取事项状态与分配权，SOP 完成不直接替代 Issue 验收 |
| 三 | 知识贡献审核、有效性、宿主适配、真实加载、资源冲突与平台发布 | Work Context 的目标与决定不另设权威；资源来源可替换，实际版本留痕 |
| 四 | 成本完整性、缺失口径、评价证据、Benchmark、提案审核与正式发布 | 原始事实与评价分开；不重复累计调用；提案、应用和效果验证分别留痕 |

订单批量导出案例因此必须覆盖：父 Issue 上的目标澄清、以子 Issue 或同事项委派形成的前后端分工、成员本地执行、范围变更或换人及旧 Run 处置、权限失败的定向返工、具体制品与环境下的 Issue 验收记录，以及后续知识或流程改进。案例的推演结果不应冒充项目的运行结果。

后续运行验证覆盖真实多成员 Runtime 协作、宿主协议行为、断联接续、Trace、模型评价和费用采集。本轮为专题一提供复用候选的源码依据；具体落地适配和整体技术选择继续结合各专题研究评估。
