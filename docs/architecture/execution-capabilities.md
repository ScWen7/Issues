# 专题三 A · 宿主接入能力与 3B 交接

订单导出的后端、前端和验证可以各用不同宿主。开工前查所选 Runtime、宿主及版本、接入方式、实际启用的通道。Issue 提供目标与当前约定，专题二的绑定确定谁有权派发，3A 回答这次在哪里执行、看到了哪些活动、哪些材料和结果可以交给下一位成员。[工作约定与执行](01-unified-work-lifecycle.md#43-完成要求工作约定版本与交付) · [统一派发](02-sop-workflow.md#33-派发控制绑定与依赖推进)

## 哪个入口能看到什么

表中「宿主实测」指官方发行的 CLI 在回环模型服务上实际产生的协议记录。「适配器实测」指固定上游程序处理协议夹具。「源码」指对固定版本调用链的核对。「原型」指本项目独立运行的设计验证。「待测」说明仍缺哪一种外部证据。每份现场回执另记实际通道、版本、观察区间及遗漏。

| 宿主与证据 | 中心派发 | 成员正在本地工作 | 结束后关联及缺项 |
|---|---|---|---|
| [Codex 0.167.0-alpha.4](../research/topic-03a/codex.md) | **宿主实测** App Server 开 thread、开 turn、返回条目与用量。持有执行授权的客户端可按协议发输入、中断或答复审批 | **源码** 在原宿主启用并信任 Hooks，或显式接入原 App Server。按下一次 `threadId + turnId` 划段。另起 stdio 客户端连接自己的子进程。成员独立 IDE 的现场覆盖待测 | 只读回查指定线程与轮次，再选 Item。resume 可能重送审批和累计用量。CLI JSON 的 `item_N` 属进程本地，`turn.started` 可无 turn ID。旧历史或临时线程缺少定位和落盘内容时显示可恢复的选区 |
| [Claude Code 2.1.325 / Python SDK 0.2.182](../research/topic-03a/claude.md) | **宿主实测** 受控 CLI 双向 stream-json、工具前后 Hook 和结果。SDK 契约可用输入 UUID 对 `user_message_uuids` 识别本轮已处理的输入 | **宿主实测** 已配置的 Hook 用 `session_id + prompt_id` 分段，`tool_use_id` 串起调用和结果。本地 OTel 接收器取得 request_id 并对回 prompt 和消息 UUID。独立 IDE 的启用和覆盖起点待测 | 本机读取选中会话与可见消息。主链、压缩摘要、子代理历史按各自来源标注。Stop 可携带仍在运行的后台任务。多条输入合入一轮时，保留共同用量和待归属部分 |
| [TeamAI Skill Driver、AgentObservation 与 Hooks `1bc2ce1`](../research/topic-03a/teamai.md) | **上游实测及源码** `next/ack/report` 把步骤交给当前会话或子代理，attempt、revision 和 driver 定位回报。四种宿主配置的驱动能力均为 `tokens:false`、`max_turns:false` | 已配置的宿主 Hook 提供 prompt、工具、Stop 等事件。AgentObservation 保存工具、模型、配置、环境与工作副本，配置指纹可跨不同执行重复 | 按宿主格式读取转录。实测同一请求换转录路径后，上游账本重复计入。采集器、文件路径和配置指纹作为来源线索，按原生请求或可验证的执行映射结算 |
| Qoder、CodeBuddy、OpenCode，固定 Multica `fdfbfcd` | **适配器实测** Qoder 用 ACP 建立或恢复 Session，再 prompt，能从协商的默认模型归集用量。CodeBuddy 在流式回报里取得实际 Session、结果和用量。OpenCode 区分 ACP 与 `run` 通道，受管 MCP 的可投递性取决于所选通道 | 三者独立成员 CLI / IDE 的实时关联、可见事件和共享粒度待目标版本实测。工作台按已验证的受管通道提供开工，已有本地工作可提交选定材料 | 有可定位的来源时登记外部证据，只有成员说明时显示署名与提交时间。独立会话历史、跨入口 ID 映射与商业账户结算待测。[Qoder](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/qoder.go#L251-L302) · [CodeBuddy](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/codebuddy.go#L383-L437) · [OpenCode](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/opencode_acp.go#L20-L76) |
| [受管 Script](../research/topic-03a/order-export-workspace.md) | **实测** 固定脚本版本、候选及输入启动进程。真实 TeamAI 命令驱动分别得到 C1、C2 和退出码，四角色用例用合成订单。LoopForge 的命令与声明输出、Multica 的附件读写可复用 | 成员手工执行的脚本，可共享实际命令结果或制品，标明执行主体和环境。其归属走与其他本地工作相同的认领路径 | 使用报告、具名产物、原始字节摘要及独立回读。C1 退出 0 但 A2 失败，C2 退出 0 且 A2、A3 通过。缺输入导致脚本退出 1、没有报告，后继显示缺少哪份材料。[通道实测](../research/topic-03a/binary-artifacts.md) |

### 受管执行怎样报告中止和恢复

| 已测适配器 | 停止、恢复与复用时看什么 |
|---|---|
| Qoder | `session/resume` 回了原 ID 仍可能在 `session/prompt` 被明确拒绝。适配器清掉旧 ID 并回报恢复拒绝。正常响应后还要收尾部通知，再交付输出和按模型归集的用量。[源码](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/qoder.go#L344-L454) |
| CodeBuddy | stderr 的「Session 不存在」可与失败及请求的 Session 对照。权威 result 到达后，随后的普通错误行保留为诊断。多帧共用响应 ID 的兜底用量在本次执行内折叠。[恢复与终态测试](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/codebuddy_test.go#L587-L630) · [晚到错误](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/codebuddy_test.go#L741-L783) |
| OpenCode | ACP 源码对实际 Session 发 `session/cancel`，经等待后可终止进程。强制选择 2.x `run` 的夹具则以进程退出判断终态，任务带受管 MCP 会在启动前返回具体错误。记录实际 transport 和失败原因，需 MCP 的工作可换用已验证可投递该服务的 Runtime。上述三个宿主的固定 Multica Session 实现均仅提供消息与 Result，清理与复用另查实际回执。[ACP 取消](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/opencode_acp.go#L604-L630) · [2.x 两种 MCP 路径](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/opencode_v2.go#L97-L115) |

## 一个执行怎样进 Issue、怎么停

- **归属与共享。** 中心派发在启动时保留派发回执，本地主动关联从下一次可识别输入生效，事后补录保留原发生时间、导入时间和生产方。三条入口先找同一宿主命名空间内的原生执行单元，再绑定原 Run。命中不同 Issue 时查原生产归属，其余 Issue 引用。成员在本机分别预览消息、工具名和结果、参数和输出、模型用量、制品，按选区投递。离线补传按当前授权和选区复核，缩小范围后取消旧版待发项。界面分别展示成员自述、带宿主标识的记录，以及中心实际核对的目标、身份、摘要或标准。[三种入口与共享](03a-execution-plane.md#46-本地交互式执行的接入)
- **一次消耗。** Codex 在两轮后总量为 33，恢复原线程仍报 33，同期回环模型只收到两次请求。Claude 两轮的会话估价分别为 0.00009 和 0.00018 美元。用请求身份或被证实相同的计量范围合并观察，同口径累计值只在基线连续、范围属于该段时求差。私有轮、混合 Issue、计数重置或缺基线时保留未归属量。重放、补录、上级汇总只加来源引用。Token、宿主估价、供应商实际结算各有单位和来源，实际账单仍待对账。[计量来源](../research/03a-source-evidence.md#两个现有适配器如何消费用量)
- **停止与收尾。** 控制者分别取得停止请求、宿主终态、进程退出、资源清理和中心接受的回执。Codex `turn/completed`、Claude `result` 各说明一次宿主调用已给出结论。固定 Multica 的两种 Backend 均未实现其可选 `TerminalObserved` 回调。Pi、Cursor 等实现了该回调，`pi / omp / museapp` 另协商取消清理确认，原生等待以同 Agent、Runtime 为范围。脚本退出、内容核验及 SOP 消费也分别留据。真实 Daemon 与模拟宿主联合实验中，中心撤权时本机进程仍在运行。资源占用未知时继续查持有者、进程或清理回执，再决定复用。[源码及适配器事实](../research/03a-source-evidence.md#74-terminalobserved-与结果交接) · [撤销和结果重发](../research/topic-03a/result-handoff.md)
- **恢复与晚到。** 先区分丢了观察连接、丢了终态确认、宿主明确拒绝恢复。观察者分别重连、读取或重发原结果。固定 Daemon 在已请求恢复、结果失败、观察到的工具调用数为零，并且符合明确拒绝或特定兼容条件时尝试一次 fresh；永久拒绝退休旧 Session，暂时占用保留后续接续资格。已有外部动作或过程不完整时，原控制者先查实际副作用和候选，再决定续跑或新开 Run。受管内部重试保留每次宿主调用及增量用量，迟到结果回原尝试。设计原型已验证同次回报原子消费，生产部署的覆盖由对应实测记录说明。[恢复判据](../research/03a-source-evidence.md#75-恢复拒绝与新会话重试的真实条件) · [消费原型](../../prototypes/topic-03a/result-admission/test_admission.py)

## 3B 把什么交给 3A，3A 回什么

3B 发布并选择有版本的 Agent / Role、Rule、Skill、MCP 配置、Playbook、SOP 或 Script。一次选择交付材料引用、不可变版本或摘要、适用团队与项目、材料来源和选中理由。预期宿主通道、可交换的版本引用和已声明的兼容条件随材料传递。Issue 提供 D2 等现行工作决定，专题二已固定的主图、子图与节点定义沿用原引用。当前执行契约说明哪些输入为本次工作必需、需要何种回执及影响哪个节点。运行时凭据由既有授权链取得。[职责分工](overview.md#5-跨专题职责草案) · [工作事实](01-unified-work-lifecycle.md#72-work-context-的来源与组装) · [定义版本与必需输入](02-sop-workflow.md#41-定义与制品版本)

| 材料 | 3A 的逐项回执 | 证据缺失、冲突或换版时的动作 |
|---|---|---|
| Agent / Role、Rule、知识、Playbook 或 Issue 决定 | 保留期望版本、实际投递版本 / 摘要、通道、宿主版本、对应 Run / 节点尝试 / 宿主调用或轮次。分别登记写入、路径读取、材料进入**当前**输入或只出现在历史、显式补发。知识或 Playbook 按实际投递通道取证 | 仅有文件回执即显示「已写入，本轮加载未知」。Codex 0.144.6 项目文件、Claude 2.1.325 项目文件都实测同进程换版后仍只带 D1。受影响执行显式补发 D2 或核对副作用后重新装载，重取相应回执。0.167.0-alpha.4 的 HOME 已实测热更新；独立虚拟机的项目文件热继续仍见 D1，冷恢复出现 D2 替换通知。[Codex 版本与通道](../research/topic-03a/codex-context.md) · [Claude 换版](../research/topic-03a/claude-context.md) |
| Skill、MCP | Skill 分列目录可发现、请求方、实际选择 / 调用及正文进入哪轮。MCP 分列配置、连接、工具发现、由谁发起调用、服务返回和结果进入哪次请求。关联原生调用 ID 与获准共享的结果引用 | 只列出工具时显示「已发现，实际调用未观察到」。本节点要求工具产出时，查当前尝试的调用与输出。由执行控制者补操作、改用契约允许的手段或报告缺项。普通可选参考材料缺少使用回执时保留记录，照常执行已有授权工作。[Skill 与 MCP 的两条实测路径](../research/topic-03a/claude-context.md#skill-的发现与调用) |
| SOP、Script 与验证输出 | 节点消费已发布版本。3A 返回实际执行脚本 / 核验器版本、候选、输入摘要、退出、报告、具名制品及接收侧回读依据。SOP 引用结果和原 Run，按当前尝试的门禁决定下一步 | 缺失版本或必需制品时，显示可补齐的引用与待验证内容。候选 C1 的 A2 失败只影响依赖它的后继。C2 的检查另记尝试，旧报告回原候选。模板换版以及受影响节点如何交接，按专题二的在途实例规则处理。[输出契约](02-sop-workflow.md#41-定义与制品版本) · [C1/C2 报告](../research/topic-03a/order-export-workspace.md) |

每项回执附观察来源、发生与接收时间、覆盖范围、实际核验动作及缺失原因。服务端按材料与宿主调用保留原件及后续更正，区分已取得证据、宿主未开放该通道、尚未采到和版本冲突。3B 可以据此修订适用范围、改善投递说明或提出新版。有效输入、候选满足业务标准、指定成员正式接受分别留在宿主证据、验证报告、Issue 决定里。专题二沿用已有 DAG、Delegation Grant 与派发绑定，纯汇合及查看回执沿用已有结果引用。[回执与结果交接](03a-execution-plane.md#47-上下文注入与加载回执) · [SOP 与工作关系](02-sop-workflow.md#31-节点采用哪一种工作关系)

## 第五阶段适配器复核

在 Multica `fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc` 的 `server` 目录，Go 1.26.9 实跑以下 17 个顶层测试。Qoder 4 项、CodeBuddy 5 项、OpenCode 4 项、Pi 2 项、Claude 与 Codex 各 1 项。测试运行真实适配器及上游协议或子进程夹具，覆盖恢复拒绝、迟到通知、结果归属、分块计量、资源检查及传输差异。目标成员账户、独立 IDE 与商业计费另按现场验收。[Qoder 测试](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/qoder_test.go#L870-L967) · [CodeBuddy 用量测试](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/codebuddy_usage_test.go#L23-L152) · [OpenCode ACP 测试](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/opencode_acp_unix_test.go#L87-L156)

```bash
go test -count=1 -run '^Test(QoderBackendHappyPath|QoderBackendAttributesUsageToACPDefaultModel|QoderBackendClearsSessionIDWhenResumedSessionNotFoundAtPrompt|QoderDrainsNotificationsAfterPromptResponse|CodebuddyExecute_Success|CodebuddyExecuteResumeRejectedFromStderr|CodebuddyExecuteFallbackUsage|CodebuddyFallbackUsageIsScopedToExecution|CodebuddyExecuteErrorAfterResultDoesNotFlipOutcome|PiCleanupInspectionFailureIsNotSuccess|PiCleanupNormalCompletionDoesNotSignal|ClaudeExecuteKeepsCompletedTerminalReason|CodexExecuteDoesNotClaimResumeRejectedWhenOverflowIsNotAResume)$' ./pkg/agent
go test -count=1 -run '^TestOpencode(ACPStreamsToolStartAndSumsTurnUsage|ProcessEventsTokenUsage|V2ExecuteRefusesMCPConfig|V2ExecuteExitIsTerminal)$' ./pkg/agent
```
