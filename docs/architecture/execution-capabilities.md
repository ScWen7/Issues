# 本地宿主与执行入口的能力矩阵

成员从平台派发、本地关联或事后补交工作时，可用的能力取决于宿主、版本、连接入口和已授予的权限。工作台据此决定可以向成员提供哪些动作，以及结果能精确归到哪次执行。下表引用固定版本的事实，产品行为见[成员本地执行与工作交接](03a-execution-plane.md)。

## 哪个入口能看到什么

表中「宿主实测」指官方发行的 CLI 在回环模型服务上实际产生的协议记录。「适配器实测」指固定上游程序处理协议夹具。「源码」指对固定版本调用链的核对。「原型」指独立实验。覆盖未知的入口单列。每份现场回执另记实际通道、版本、观察区间及遗漏。

| 宿主与证据 | 中心派发 | 成员正在本地工作 | 结束后关联及缺项 |
|---|---|---|---|
| [Codex 0.167.0-alpha.4](../research/topic-03a/codex.md) | **宿主实测** App Server 开 thread、开 turn、返回条目与用量。持有执行授权的客户端可按协议发输入、中断或答复审批 | **源码** 在原宿主启用并信任 Hooks，或显式接入原 App Server。按下一次 `threadId + turnId` 划段。另起 stdio 客户端连接自己的子进程。此项源码研究未覆盖独立 IDE 的实际入口 | 只读回查指定线程与轮次，再选 Item。resume 可能重送审批和累计用量。CLI JSON 的 `item_N` 属进程本地，`turn.started` 可无 turn ID。旧历史或临时线程缺少定位和落盘内容时显示可恢复的选区 |
| [Claude Code 2.1.325 / Python SDK 0.2.182](../research/topic-03a/claude.md) | **宿主实测** 受控 CLI 双向 stream-json、工具前后 Hook 和结果。SDK 契约可用输入 UUID 对 `user_message_uuids` 识别本轮已处理的输入 | **宿主实测** 已配置的 Hook 用 `session_id + prompt_id` 分段，`tool_use_id` 串起调用和结果。本地 OTel 接收器取得 request_id 并对回 prompt 和消息 UUID。此实验仅覆盖已启用采集的受控入口 | 本机读取选中会话与可见消息。主链、压缩摘要、子代理历史按各自来源标注。Stop 可携带仍在运行的后台任务。多条输入合入一轮时，保留共同用量和待归属部分 |
| Qoder、CodeBuddy、OpenCode，固定 Multica `fdfbfcd` | **适配器实测** Qoder 用 ACP 建立或恢复 Session，再 prompt，能从协商的默认模型归集用量。CodeBuddy 在流式回报里取得实际 Session、结果和 Token；当前 Backend 尚缺 `usage_update` Stage / Credits 解析。OpenCode 区分 ACP 与 `run` 通道，受管 MCP 的可投递性取决于所选通道 | 此组证据的范围是受管适配器。独立成员 CLI / IDE 的实时关联和共享粒度未知。工作台按已验证的受管通道提供开工，已有本地工作可提交选定材料 | 有可定位的来源时登记外部证据，只有成员说明时显示署名与提交时间。独立会话历史与跨入口 ID 的对应关系在此版本证据中未知。[Qoder](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/qoder.go#L251-L302) · [CodeBuddy](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/codebuddy.go#L383-L437) · [OpenCode](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/opencode_acp.go#L20-L76) |
| [受管 Script](../research/topic-03a/order-export-workspace.md) | **独立命令驱动实验** 固定脚本版本、候选及输入启动进程，分别得到 C1、C2 和退出码，四角色用例用合成订单。LoopForge 的命令与声明输出、Multica 的附件读写可复用；通用确定性 Script 经 Multica Run / Daemon 托管是设计扩展 | 成员手工执行的脚本，可共享实际命令结果或制品，标明执行主体和环境。其归属走与其他本地工作相同的认领路径 | 使用报告、具名产物、原始字节摘要及独立回读。C1 退出 0 但 A2 失败，C2 退出 0 且 A2、A3 通过。缺输入导致脚本退出 1、没有报告，后继显示缺少哪份材料。[通道实测](../research/topic-03a/binary-artifacts.md) |

### 受管执行怎样报告中止和恢复

| 已测适配器 | 停止、恢复与复用时看什么 |
|---|---|
| Qoder | `session/resume` 回了原 ID 仍可能在 `session/prompt` 被明确拒绝。适配器清掉旧 ID 并回报恢复拒绝。正常响应后还要收尾部通知，再交付输出和按模型归集的用量。[源码](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/qoder.go#L344-L454) |
| CodeBuddy | stderr 的「Session 不存在」可与失败及请求的 Session 对照。权威 result 到达后，随后的普通错误行保留为诊断。多帧共用响应 ID 的兜底用量在本次执行内折叠。[恢复与终态测试](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/codebuddy_test.go#L587-L630) · [晚到错误](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/codebuddy_test.go#L741-L783) |
| OpenCode | ACP 源码对实际 Session 发 `session/cancel`，经等待后可终止进程。强制选择 2.x `run` 的夹具则以进程退出判断终态，任务带受管 MCP 会在启动前返回具体错误。记录实际 transport 和失败原因，需 MCP 的工作可换用已验证可投递该服务的 Runtime。上述三个宿主的固定 Multica Session 实现均仅提供消息与 Result，清理与复用另查实际回执。[ACP 取消](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/opencode_acp.go#L604-L630) · [2.x 两种 MCP 路径](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/opencode_v2.go#L97-L115) |

在 Codex 0.144.6 前台终端验证了第二客户端接入已开放端点，在 Claude Code 2.1.325 验证了已有控制流接入一个晚到的订单工具。历史不再全量获准、成员仍可并发输入或 Hook 改写返回时，分别记录切换会话或停止接收的依据。[现有会话实测](../research/topic-03b/existing-session.md)

## 一个执行怎样进 Issue、怎么停

- **归属与共享。** 中心派发在启动时保留派发回执，本地主动关联从下一次可识别输入生效，事后补录保留原发生时间、导入时间和生产方。三条入口先找同一宿主命名空间内的原生执行单元，再绑定原 Run。命中不同 Issue 时查原生产归属，其余 Issue 引用。成员在本机分别预览消息、工具名和结果、参数和输出、模型用量、制品，按选区投递。离线补传按当前授权和选区复核，缩小范围后取消旧版待发项。界面分别展示成员自述、带宿主标识的记录，以及中心实际核对的目标、身份、摘要或标准。[三种入口与共享](03a-execution-plane.md#5-本地主动会话与-agentobservation)
- **一次消耗。** Codex 在两轮后总量为 33，恢复原线程仍报 33，同期回环模型只收到两次请求。Claude 两轮的会话估价分别为 0.00009 和 0.00018 美元。用请求身份或被证实相同的计量范围合并观察，同口径累计值只在基线连续、范围属于该段时求差。私有轮、混合 Issue、计数重置或缺基线时保留未归属量。重放、补录、上级汇总只加来源引用。Token、宿主估价和原生计费量分别注明单位与来源；本地 Runtime 未提供的费用保留 unknown。[计量来源](../research/03a-source-evidence.md#两个现有适配器如何消费用量)
- **停止与收尾。** 控制者分别取得停止请求、宿主终态、进程退出、资源清理和中心接受的回执。Codex `turn/completed`、Claude `result` 各说明一次宿主调用已给出结论。固定 Multica 的两种 Backend 均未实现其可选 `TerminalObserved` 回调。Pi、Cursor 等实现了该回调，`pi / omp / museapp` 另协商取消清理确认，原生等待以同 Agent、Runtime 为范围。脚本退出、内容核验及 SOP 消费也分别留据。真实 Daemon 与模拟宿主联合实验中，中心撤权时本机进程仍在运行。资源占用未知时继续查持有者、进程或清理回执，再决定复用。[源码及适配器事实](../research/03a-source-evidence.md#74-terminalobserved-与结果交接) · [撤销和结果重发](../research/topic-03a/result-handoff.md)
- **恢复与晚到。** 先区分丢了观察连接、丢了终态确认、宿主明确拒绝恢复。观察者分别重连、读取或重发原结果。固定 Daemon 在已请求恢复、结果失败、观察到的工具调用数为零，并且符合明确拒绝或特定兼容条件时尝试一次 fresh；永久拒绝退休旧 Session，暂时占用保留后续接续资格。已有外部动作或过程不完整时，原控制者先查实际副作用和候选，再决定续跑或新开 Run。受管内部重试保留每次宿主调用及增量用量，迟到结果回原尝试。对同次回报的重复消费，独立原型具有可复跑用例。[恢复判据](../research/03a-source-evidence.md#75-恢复拒绝与新会话重试的真实条件) · [消费原型](../../prototypes/topic-03a/result-admission/test_admission.py)

## 能力选择与实际执行回执

项目配置给出已选用的 Agent、规则、工具和方法，Issue 提供当前决定，受托执行的 SOP 提供固定的节点与输入。成员在自己的获准 Runtime 执行。能力选择记录注明适用范围、发布版本、材料来源、预期投递通道和必需回执。生产 Run 保留实际取得的材料、调用与输出，供节点或接收人核对。[团队能力与工作上下文](03b-capability-governance.md) · [SOP 与工作流](02-sop-workflow.md)

| 材料 | 生产 Run 上可查的回执 | 证据缺失、冲突或换版时的动作 |
|---|---|---|
| Agent / Role、Rule、知识、Playbook 或 Issue 决定 | 保留期望版本、实际投递版本 / 摘要、通道、宿主版本、对应 Run / 节点尝试 / 宿主调用或轮次。分别登记写入、路径读取、材料进入**当前**输入或只出现在历史、显式补发。知识或 Playbook 按实际投递通道取证 | 写入已确认而加载证据缺失时显示「已写入，本轮加载未知」；投递证据也缺失时显示「投递状态未知」；明确 not_delivered 时显示「未投递」。Codex 0.144.6 项目文件、Claude 2.1.325 项目文件都实测同进程换版后仍只带 D1。受影响执行显式补发 D2 或核对副作用后重新装载，重取相应回执。0.167.0-alpha.4 的 HOME 已实测热更新；独立虚拟机的项目文件热继续仍见 D1，冷恢复出现 D2 替换通知。[Codex 版本与通道](../research/topic-03a/codex-context.md) · [Claude 换版](../research/topic-03a/claude-context.md) |
| Skill、MCP | Skill 分列目录可发现、请求方、实际选择 / 调用及正文进入哪轮。MCP 分列配置、连接、工具发现、由谁发起调用、服务返回和结果进入哪次请求。关联原生调用 ID 与获准共享的结果引用 | 只列出工具时显示「已发现，实际调用未观察到」。本节点要求工具产出时，查当前尝试的调用与输出。由执行控制者补操作、改用契约允许的手段或报告缺项。普通可选参考材料缺少使用回执时保留记录，照常执行已有授权工作。[Skill 与 MCP 的两条实测路径](../research/topic-03a/claude-context.md#skill-的发现与调用) |
| SOP、Script 与验证输出 | 节点按已选发布版本消费输出。Run 回报实际执行脚本 / 核验器版本、候选、输入摘要、退出、报告、具名制品及接收侧回读依据。SOP 引用结果和原 Run，按当前尝试的门禁决定下一步 | 缺失版本或必需制品时，显示可补齐的引用与待验证内容。候选 C1 的 A2 失败只影响依赖它的后继。C2 的检查另记尝试，旧报告回原候选。模板换版以及受影响节点如何交接，按 SOP 在途实例的版本规则处理。[输出契约](02-sop-workflow.md) · [C1/C2 报告](../research/topic-03a/order-export-workspace.md) |

每项回执附观察来源、发生与接收时间、覆盖范围、实际核验动作及缺失原因。服务端按材料与宿主调用保留原件及后续更正，区分已取得证据、宿主未开放该通道、尚未采到和版本冲突。能力维护者可据此修订适用范围、调整投递说明或提出新版。有效输入、候选满足业务标准、指定成员正式接受分别留在宿主证据、验证报告、Issue 决定里。SOP DAG 只计算流程依赖；实际派发、权限和 Run 生命周期均沿用 Multica。[回执与结果交接](03a-execution-plane.md#contextreceipt-与逐调用证据) · [SOP 与工作关系](02-sop-workflow.md)

## 固定版本的能力边界

以下事实以 Multica `fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc` 源码或表中标出的宿主实验为依据。

| 能力 | 原生行为或实验覆盖 | 现行产品设计 |
|---|---|---|
| ContextReceipt | 准备阶段生成，记录 brief / Skill / MCP、摘要和加载判断；恢复历史在 sources 列表之外；按 task 重报覆盖 | 复用原生准备回执，D1→D2 与逐调用实际输入另关联原 Run 的证据。历史含失权材料时，从当前获准的来源在新会话重建工作上下文 |
| 验收资产版本 | 普通 Skill 可接受服务端新版，原生删除清除历史；插件已安装版本与升级独立 | Rule / Script 使用不可变内容引用，执行前查实际字节摘要；退役保留获准历史内容 / 不变引用。不可变的验收引用属于平台扩展 |
| 确定性 Script | Backend 工厂是编码 Agent 协议；C1/C2 当前由 TeamAI 命令驱动执行 | 沿现有 Run / Daemon 适配命令、工作目录、取消、退出和制品。该命令承载属于产品扩展 |
| 本地 Credits 通路 | `TokenUsage` / `TaskUsageEntry` 无 Credits，CodeBuddy `system` 分支未解析 Stage；服务端已有 `credits_micros` | 扩展现有 Backend → Daemon → Usage，保留请求 / Stage 身份、单位与更正；用真实 CodeBuddy 0.69 Credits 回执核对只计一次 |
| Qoder 请求 Credits | SDK 1.0.59 / CLI 1.1.88 仅有 Session `total_credits=0`，没有 Assistant 用量和原生请求 ID；该记录的范围为 SDK，ACP 的请求级覆盖未知 | 请求 Credits 显示未知。Session 快照按原口径保留，独立 SDK 探针单列来源。使用 ACP 时，以该入口实际取得的事件与单位为准 |
| Hook 后结果与复验 | 服务报告、模型收到的结果与节点消费各有回执；已观察 Hook 改写 | 按本轮契约拒收不符结果；宿主结束后重验建立后继 Run，原节点尝试可按仍有效的目标 / 候选 / 标准保留 |

固定源码：[ContextReceipt](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/context_receipt.go#L62-L89) · [task 覆盖](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/task_context_receipt.sql#L1-L8) · [TokenUsage](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/agent.go#L273-L293) · [TaskUsageEntry](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/types.go#L309-L322) · [CodeBuddy 分支](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/codebuddy.go#L243-L277) · [Backend 工厂](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/agent.go#L502-L564)。固定实验：[资产原生语义](../research/topic-03b/native-assets.md) · [Credits 与进程实际回执](../research/topic-04/runtime-validation-1.1.88-2.181.0.md) · [成员会话 / Hook](../research/topic-03b/existing-session.md)。

## 订单执行与消费核对

以下是订单案例对上述能力的使用示例。D1 的四列对照与 D2 五列要求分开；C1、C2 都按 D2 核验。工作台先呈现候选、规则、核验结果与待决动作，追查时再展开调用和摘要证据。

| 订单环节 | 本轮必须对上的对象 | 异常动作 |
|---|---|---|
| D2 选版与开工 | Issue 工作约定、Rule / Script 发布引用、实际输入与脚本摘要 | 只见 D1 或缺必需版本时停相关执行，明确补发 / 重载 |
| C1 核验 | C1、D2、A2 / A3、具名 XLSX、原生调用与报告 | 技术退出 0、A3 通过仍保留 A2 失败；返工依赖 A2 的部分 |
| C2 重验 | 新 Run / 候选、同一有效标准、实际核验器、服务与模型所得报告 | Hook 改写时拒收；结束后重验用后继 Run，分别归集工作量 |
| 换成员与迟到结果 | 新成员授权、Runtime、新 Run，原 Run 与候选引用 | 旧报告留原来源，当前有效报告消费一次；先查原副作用再复跑写操作 |
| 从核验提炼团队经验 | C1/C2 原证据、确切文案、来源派生许可、独立团队发布 | 单来源许可撤回停发；同字节恢复仍重新授权和复审 |

报告使用合成订单，C2 的现有回执覆盖区域权限和付款时间内容。指定成员按当前候选和有效标准决定是否接受交付。跨成员接续复用目标与可取得的交付，按接手者自己的授权重建必要输入。[完整订单场景](01-unified-work-lifecycle.md) · [源码与宿主证据](../research/03a-source-evidence.md)

## 实验覆盖

| 来源 | 可以据此确认的行为 |
|---|---|
| Multica `fdfbfcd`，Go 1.26.9，17 项上游适配器测试 | Qoder、CodeBuddy、OpenCode、Pi、Claude 与 Codex 的协议或子进程夹具覆盖恢复拒绝、晚到事件、分块计量和部分清理行为。实际成员机器的独立 CLI / IDE 覆盖范围按入口注明。[上游适配器与证据](../research/03a-source-evidence.md) |
| Codex 0.144.6 App Server、Claude Code 2.1.325 受控入口 | 已观察到指定项目工具实际被调用、原服务回报与宿主取得的结果。缺少工具、选择个人同名工具、服务端撤权各有单独回执。跨宿主接手使用新成员的授权与新 Run。[跨宿主交付](../research/topic-03b/cross-host-handoff.md) |
| TeamAI `1bc2ce1` 的 Driver、Hooks 及转录回放 | `next / ack / report` 可在当前会话或子代理中推进步骤。配置指纹可跨执行重复，转录换路径后可被重复观察。平台按原生执行或计量单元归并来源。[Driver 与采集行为](../research/topic-03a/teamai.md) |
