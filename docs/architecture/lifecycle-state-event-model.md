# 统一生命周期、状态机与事件模型

本文定义核心对象在运行期间如何变化，以及这些变化如何跨层传递。它建立在[核心对象模型](core-object-model.md)之上，是各专题共同遵循的生命周期语义。并发写入、跨层动作恢复、结果消费和旧执行隔离见[核心协作一致性与并发控制模型](core-consistency-concurrency.md)。本文不定义数据库表、API 字段、消息中间件或页面结构。

## 1. 统一规则

### 1.1 状态属于对象，事件描述事实

状态是某个对象当前有效的生命周期位置；事件是主体已经发起或观察到的事实。事件被接收，不代表目标对象的状态必然改变。

- Issue 的业务状态由 Issue 的有效写入决定。
- Project Workflow 的步骤与交接由项目配置及 Issue 上的实际步骤记录决定。
- SOP Execution 与节点状态由对应流程实例推进。
- Run 的执行状态由实际派发链和宿主回执推进。
- Candidate 内容及制品版本固定；接受、退回或替代是对该版本的处置。
- Evaluation 的结论属于评价记录；是否接受交付仍由 Issue 的有效决定确定。

### 1.2 不建立覆盖全系统的总状态机

各对象拥有独立生命周期，通过关联、事件和结果引用协作。Run 失败不自动意味着 Issue 失败；SOP 等待人工决定不意味着 Run 正在运行；Evaluation 完成不意味着 Candidate 已接受；Issue 完成也不意味着所有历史 Run 都成功。

### 1.3 每次状态转换必须满足四个条件

1. 谁发起或观察：主体身份及权限。
2. 改变哪个对象：对象身份、当前版本和当前状态。
3. 为什么允许改变：前置条件、授权范围、适用的输入版本与候选、因果来源。
4. 改变后谁接续：等待、派发、交接、消费结果，或不触发后续动作。

不满足条件时，保留拒绝或待处理事实，不通过猜测补齐状态。

## 2. 生命周期总览

| 对象 | 生命周期管理的问题 | 权威状态来源 |
|---|---|---|
| Issue | 业务工作是否待安排、推进、等待、审查、完成或取消 | Issue 工作记录与有效工作流写入 |
| Project Workflow | 当前步骤、进入条件和负责人交接 | 项目配置及 Issue 上的实际步骤记录 |
| SOP Definition | 定义如何草拟、审核、发布、弃用 | 能力资产维护与发布机制 |
| SOP Execution | 受托流程是否准备、推进、等待、交还或终止 | 对应流程实例 |
| Node Activation | 节点本轮是否就绪、执行、等待、通过或未通过 | 对应流程实例中的本轮激活 |
| Node Attempt | 本轮节点履行是否完成、失败或被中断 | 节点尝试及其关联执行结果 |
| Run | 受管执行是否排队、领取、运行、终止或失联待核实 | Multica 派发、Daemon、Runtime 和宿主回执 |
| Candidate | 固定交付版本是否待检查、接受、退回或被替代 | Issue 对该候选的处置决定 |
| Evaluation | 一次评价是否待执行、执行中、完成或证据不足 | 评价任务与评价结果 |
| Improvement Proposal | 改进是否提出、评估、对照、审核、发布 | 资产维护者及项目有权成员的决定 |

这些是概念语义，不要求每个对象都新增一套物理状态字段。

## 3. Issue 生命周期

Issue 表达业务工作，不表达 Agent 进程的运行情况。沿用项目配置中的状态目录与生命周期类别；下表给出统一语义，不强制所有项目使用完全相同的状态名称。

| 语义状态 | 含义 | 允许的后续 |
|---|---|---|
| Backlog | 已记录，尚未进入当前执行安排 | 安排为待办、取消 |
| Todo | 已纳入工作安排，等待负责人或资源开始 | 开始推进、阻塞、取消 |
| In Progress | 有负责人正在组织或推进工作 | 提交候选待审、阻塞、按轻量约定完成、取消 |
| In Review | 已有明确候选，等待检查或验收 | 接受并完成、退回推进、补充材料、阻塞、取消 |
| Blocked | 当前工作因明确依赖或决定暂不能推进 | 解除阻塞并恢复适当工作状态、取消 |
| Done | 按本 Issue 的完成约定完成 | 终态；后续工作创建新 Issue 或按显式重开规则处理 |
| Cancelled | 有权主体决定不再继续该工作 | 终态；重新开展需新 Issue 或显式重开 |

规则：

- Blocked 必须说明阻塞原因、等待对象或解除条件；它不意味着所有子项、Run 或 SOP 都停止。
- In Review 表示有具体候选待处理，不等同于代码已经提交或 Run 已结束。
- Done 必须满足工作约定。若要求具名验收，必须有针对当前候选和现行标准的有效接受决定。
- Cancelled 是业务决定，不等同于停止 Run。仍在运行的执行需单独请求停止并核对实际终态和副作用。
- 改派负责人本身不必改变 Issue 状态；负责人变化与执行处置是两个独立事实。
- 子 Issue 独立推进。父 Issue 是否可完成，按父项工作约定消费子项交付，不由子项状态简单汇总推导。

**持续协调委托。** 有权成员把 Issue 指派给承担 Main Bot 职责的 Agent，并确认范围后，委托可跨多个 Coordinator Turn（协调回合）持续。每个回合对应一次原生 Task / Run。等待 Worker 时，Main Bot 可结束当前回合，已派发的 Worker 按自己的授权和 Run 继续。改派、撤销、Issue 完成或取消结束当前委托。重新指派给同一 Agent 也须依据新的委托继续。

## 4. Project Workflow 生命周期

Project Workflow 是项目定义的步骤和交接规则，不是每项工作都必须启动的独立流程引擎。

1. **配置定义**：项目维护者定义步骤、进入条件、默认负责人和交接行为。
2. **步骤进入**：Issue 满足进入条件后，记录本次进入及负责人交接。
3. **步骤推进**：当前步骤所需决定或交付满足后，进入后续步骤；需要人处理时把工作交给指定成员。
4. **步骤等待**：缺少依赖、资源或业务决定时，Issue 保持适用业务状态，并明确等待原因。
5. **步骤退回**：工作交回适当负责人或前序步骤，保留退回原因和针对的候选。
6. **步骤结束**：Issue 完成或取消时停止后续步骤推进；历史步骤与交接保留。

Project Workflow 可以触发责任交接或受托 SOP，但不能代替 SOP 管理节点依赖，也不能在没有完成条件证据时直接把 Issue 标为 Done。

## 5. SOP Definition 与 SOP Execution 生命周期

### 5.1 SOP Definition

| 语义状态 | 含义 |
|---|---|
| Draft | 可编辑工作版本，不可被正式工作调用 |
| In Review | 等待维护者审核定义、权限、节点依赖、输出和失败处置 |
| Published | 不可变发布版本，可按适用范围被调用 |
| Deprecated | 不再建议新调用；既有实例仍按固定版本处理 |
| Withdrawn | 因安全、权限或正确性问题停止新调用，并按影响范围处置在途实例 |

发布新版本不改变既有 SOP Execution 固定的版本。弃用或撤回不自动修改在途实例；是否暂停、迁移或取消由有权维护者按影响范围决定。

### 5.2 SOP Execution

| 语义状态 | 含义 | 典型后续 |
|---|---|---|
| Prepared | 已固定 SOP 版本、Issue、授权范围和调用输入，尚未开始节点推进 | Running、Waiting、Cancelled |
| Running | 至少一个节点已就绪或正在履行，实例仍可推进 | Waiting、Returned、Completed、Failed、Cancelled |
| Waiting | 当前没有可合法推进的节点，等待输入、资源或人工决定 | Running、Returned、Cancelled |
| Returned | 已将受托范围的结果、缺项或决定请求交回调用方 | 调用方决定后续 |
| Completed | 满足 SOP 声明的出口条件并交回结果 | 终态 |
| Failed | 在授权范围内无法满足流程出口，且没有合法修正路径 | 终态；负责人决定后续 |
| Cancelled | 受托范围被撤销或取消，停止新节点推进 | 终态；在途 Run 单独核对 |

Returned 是交接结果，不等于成功或失败。Completed 只说明受托范围已完成，不自动完成调用 Issue。Failed 不自动把 Issue 标为 Blocked 或 Cancelled。Waiting 必须定位等待依赖、资源或决定及解除条件。

## 6. Node Activation 与 Node Attempt 生命周期

### 6.1 Node Activation

一次 Node Activation 表示某个节点在确定的工作约定、输入和授权下的一次有效进入。首次生产可以只固定工程或资料基准及必需输入，尚无 Candidate 也可按前置条件启动。针对已有交付的检查或修正节点，须固定其输入 Candidate。

本轮生成的 Artifact 及其组成的 Candidate 记录为该激活的输出，后继节点将选定的输出版本作为自己的输入。首次产出或在原修正预算内改进输出，均保留在本轮生产激活中。

| 语义状态 | 含义 |
|---|---|
| Pending | 前置尚未全部满足 |
| Ready | 前置与授权满足，可以请求执行或等待人工处理 |
| Active | 已开始处理；可有关联 Run，也可正在消费已有结果 |
| Waiting | 等待外部输入、资源或人工决定 |
| Succeeded | 本轮节点输出满足节点契约，结果已记录 |
| Failed | 本轮无法满足节点契约，且没有授权内修正路径 |
| Skipped | 按已声明条件和授权跳过，并记录依据 |
| Cancelled | 本轮被取消，不再接受其结果推进后继 |

节点重新进入、已固定的输入候选被替换或发起业务返工时，受影响节点必须创建新的激活轮次。本轮产出新 Candidate 不会自行重开生产节点；若新版替换了下游节点已绑定的输入，则为受影响的下游节点建立新激活并重验。同一激活内的技术重试和执行重跑保留各自尝试及 Run 关系。旧激活的迟到结果只能补充旧轮次，不能推进新轮次。

### 6.2 Node Attempt

Node Attempt 记录一次具体履行，包括修正或核验。结果语义为：

- **Succeeded**：本次尝试得到满足输出要求的结果；节点是否成功仍由激活规则消费结果后确定。
- **Failed**：有明确结果表明本次尝试未满足要求。
- **Interrupted**：停止、断联或宿主中断使本次尝试未正常结束。
- **Unknown**：缺少足够回执判断是否执行或结果如何。

一次 Attempt 可以关联多个 Run。一个 Run 也可因明确执行安排关联某个节点尝试，但不能仅凭同一 Session、Agent 或时间相近推断关系。

## 7. Run 生命周期

Run 是实际受管执行记录。状态名称以 Multica 固定版本及具体 Backend 的原生回执为依据；下表是跨宿主统一语义，不要求上游所有状态逐字一致。

| 语义状态 | 含义 | 关键事实 |
|---|---|---|
| Queued | 执行安排已保存，等待可用 Runtime / Daemon | 已安排，不代表已领取或已执行 |
| Claimed | 某 Runtime 已领取安排 | 已领取，不代表宿主进程已启动 |
| 等待本地目录（`waiting_local_directory`） | 已领取的执行因原地目录占用或准备工作树快照而等待真实路径释放 | 只在取得相应回执时显示。释放后原 Run 继续准备，也可由有权主体取消 |
| Starting | Daemon 正在准备环境或启动宿主 | 启动尚未得到确认 |
| Running | 宿主已确认开始执行 | 可继续产生观察、结果和用量 |
| Stop Requested | 平台或有权主体已请求停止 | 请求不等于已停止 |
| Succeeded | 宿主或 Backend 给出可信成功终态 | 仍需检查制品与业务要求 |
| Failed | 取得可信失败终态 | 失败范围和副作用另行记录 |
| Cancelled | 取得可信取消终态 | 区分停止请求与实际终止 |
| Lost / Unknown | 无法取得可靠终态或资源失联 | 不得猜测成功、失败或释放资源 |

关键规则：

- Run 进入 Succeeded 不代表 Candidate 合格，也不代表 Issue 完成。
- 请求取消后，在收到终态或按可靠租约 / 进程清理机制确认之前，不能视为已停止或资源已释放。
- Daemon 恢复、Backend 重试、宿主重启等执行内部动作保留原生谱系；只有确实产生新的受管执行时才创建新 Run。
- 系统暂态重试与人工重跑保留 Multica 原生关系。业务返工是工作层的新激活或新候选，不应伪装成技术重试。
- Lost / Unknown 是不确定性状态，不是可直接清理的终态。恢复后以实际回执校正；无法确认时保留未知，由有权主体决定隔离或接管。

## 8. Candidate、Delivery Record 与验收

Candidate 的内容和组成版本一经创建即固定。后续变化形成新 Candidate 或新版本引用，不覆盖旧内容。

| 处置 | 含义 | 影响 |
|---|---|---|
| Submitted | 候选已交回 Issue，等待处理 | 可进入检查、补充或验收 |
| Under Review | 当前候选正在按约定检查 | 不改变候选内容 |
| Accepted | 有权主体接受该候选及适用标准 | 满足 Issue 完成条件时可用于完成 |
| Rejected | 有权主体或约定检查流程指出未满足项 | 当前负责人按范围修正或重新提交 |
| Superseded | 新候选替代其作为当前待处理版本 | 历史检查和决定仍指向旧候选 |
| Withdrawn | 提交者或有权主体撤回候选 | 保留原因和已有检查；不得作为当前完成依据 |

Candidate 的处置按具体版本保存。旧候选的 Accepted 不能自动接受新候选；旧报告是否可复用，由检查要求和变化范围决定。

Delivery Record 汇总候选、要求、制品、证据、缺项和决定。它可以逐步补全，不应把记录已生成当成完整交付。

## 9. Evaluation 与 Improvement Proposal 生命周期

### 9.1 Evaluation

| 语义状态 | 含义 |
|---|---|
| Requested | 已请求评价，尚未开始 |
| Running | 评价器正在处理固定评价输入 |
| Completed | 已形成有版本、输入范围和证据引用的评价结论 |
| Insufficient Evidence | 无法得出可靠结论，已明确列出缺项 |
| Failed | 评价执行本身失败，不能把它当成被评对象失败 |
| Cancelled | 评价任务被撤销 |

评价器执行自身可有 Run；Run 终态与 Evaluation 结论分别记录。Insufficient Evidence 不等同于质量失败；Failed 也不意味着被评 Run 失败。

### 9.2 Improvement Proposal

| 语义状态 | 含义 |
|---|---|
| Proposed | 从工作证据提出待评估改进 |
| Triaged | 维护者确认问题归属、范围和是否继续 |
| Evaluating | 正在进行根因分析、候选准备或对照 |
| Ready for Approval | 已具备审核所需证据 |
| Approved | 有权维护者批准候选发布或配置采用 |
| Released | 不可变资产版本已发布 |
| Adopted | 项目已决定在声明范围采用该版本或配置 |
| Rejected / Withdrawn | 提案被拒绝或撤回，保留依据 |

方法资产获批后由维护者发布，项目可将它设为默认，工作负责人也可在授权范围内为本项选用。若批准的是项目工作流或分工配置，有权成员直接在原项目或 Issue 记录生效范围及在途安排。后续工作分别记录本次选择、投递和可核对的实际使用。

## 10. 跨对象事件模型

### 10.1 事件类别

| 类别 | 典型事件 | 权威事实来源 |
|---|---|---|
| Work | IssueCreated、WorkAgreementChanged、AssigneeChanged、IssueBlocked、IssueUnblocked、CandidateSubmitted、CandidateAccepted、IssueCompleted、IssueCancelled | Issue 的有效写入 |
| Workflow | WorkflowStepEntered、WorkflowHandoffRequested、WorkflowHandoffCompleted、WorkflowStepReturned | Project Workflow 与 Issue 交接记录 |
| SOP | SOPInvoked、SOPPrepared、NodeReady、NodeActivated、NodeResultReceived、HumanDecisionRequested、HumanDecisionRecorded、SOPReturned、SOPCompleted、SOPFailed、SOPCancelled | SOP Execution 及其权威状态变化 |
| Execution | RunQueued、RunClaimed、RunStarted、RunStopRequested、RunSucceeded、RunFailed、RunCancelled、RunLost、RunRecovered | Multica、Daemon、Runtime、Backend 和宿主回执 |
| Delivery | ArtifactProduced、ArtifactAttached、CandidateCreated、CandidateSuperseded、EvidenceRecorded、DeliveryReturned | 生产者与交付通道 |
| Evaluation | EvaluationRequested、EvaluationStarted、EvaluationCompleted、EvaluationInsufficientEvidence、EvaluationFailed、FindingRecorded | 评价任务及结果 |
| Improvement | ImprovementProposed、CandidateCompared、ImprovementApproved、AssetReleased、ProjectAdopted、AssetDeprecated | 维护者审核、资产发布和项目采用 |

事件名称表示语义类别，不要求直接作为 API 名称或消息 Topic。实现可沿用 Multica 原生事件，并映射到这些语义。

### 10.2 事件必要语义

每个跨层事件至少能解释：发生了什么、作用于哪个对象、由谁产生、基于什么前置事实、何时发生及何时收到、来源可信度、影响范围，以及如何处理重复。发生时间与接收时间分别保留；成员自述、平台写入、宿主回执、外部来源和推断必须区分。来源没有提供的身份、时间、用量或结果保持未知。

这是事件语义要求，不是要求所有宿主提供全部字段，也不是预先规定统一事件序列化格式。

### 10.3 事件处理规则

1. **先验证，再转换。** 消费者核对目标对象当前状态、版本、授权和因果来源，满足条件后才执行转换。
2. **幂等处理。** 同一事件重送不应重复创建子项、Run、候选或决定。使用上游事件身份或稳定业务操作关联判断。
3. **因果隔离。** 事件只能影响明确关联的 Issue、Run、Candidate、SOP Execution 和 Node Activation；不能因名称相同或时间接近影响另一轮。
4. **迟到事件归原对象。** 迟到回执可补充原 Run 或原激活历史；若当前候选或授权已变化，不得推进当前流程。
5. **不假设全局顺序。** 不同来源事件可能乱序。转换按对象版本和前置事实判断；必要时等待缺失事实或重新读取权威对象。
6. **区分事实与派生。** 通知、列表、统计和工作台状态是可重建的派生视图，不作为业务状态权威来源。
7. **失败可恢复。** 状态写入与后续通知、派发分开处理。下游动作失败时，从已生效的权威状态恢复仍适用的动作，不能重复执行原业务转换。
8. **保留未知。** 没有宿主回执、请求身份或用量证据时标为未知，不根据模型自述或 Session 推测补齐。

### 10.4 Issue 回唤与结果消费

协调方等待同一 Issue 的具体 Worker Run 时，可为该源 Task 登记 Issue Wakeup，匹配成功、失败或取消。原生派发可合并唤醒信号。收到信号的回合重新读取当前 Issue、原委派和相关 Run，逐项核对待消费结果。子 Issue 的交付、SOP 的出口以及针对 Candidate 的验收分别回到其权威记录核对。[Multica 回唤事件与投递语义](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/docs/engineering/issue-wakeups.md#L124-L223)

## 11. 关键跨层转换

| 触发事实 | 权威转换 | 允许的后续动作 | 不允许的推断 |
|---|---|---|---|
| Issue 指派给 Agent | Issue 负责人变化 | 按资格安排受管执行。工作约定授予持续协调权时，由该 Agent 担任 Main Bot | 指派生效只能证明责任发生变化 |
| Worker 的终态或其他匹配事实触发已登记回唤 | 来源事实归原 Issue / Run，匹配回执供原生派发处理 | 现任协调方核对原委派、授权及结果版本，决定消费、补交、重排或交还 | 单次回唤不证明每份结果均已消费 |
| SOP 节点满足前置 | Node Activation 进入 Ready | Agent / Script 节点请求原派发入口；人工节点在 Issue 等待决定 | Ready 不代表 Run 已存在 |
| Runtime 领取执行 | Run 进入 Claimed | Daemon 准备环境并启动 | Claimed 不代表执行开始 |
| 宿主确认开始 | Run 进入 Running | 收集可观察活动、结果和用量 | Session 或进程句柄不必然证明业务已开始 |
| 成员从本地交付 | 原 Issue 记录提交者、所选材料及对应版本 | 接收方按自己的读权取用并核对本项要求 | 成员署名只证明本次提交，关联宿主活动须另有来源依据 |
| Run 产生终态 | Run 记录真实终态 | 对应 Attempt 接收结果，节点按契约判断；负责人可检查 Candidate | Run 成功不代表节点成功、候选接受或 Issue 完成 |
| 节点结果满足契约 | Node Activation 进入 Succeeded | 激活满足依赖的后继节点，或准备 SOP 出口 | 不能完成超出 SOP 授权范围的 Issue |
| SOP 出口交回 | SOP Execution 进入 Returned 或 Completed | Issue 负责人或 Project Workflow 消费结果并安排下一责任 | SOP 返回不自动改变 Issue 为 Done |
| Candidate 被接受 | Issue 记录针对当前候选的有效 Decision | 满足全部完成条件时，Issue 可完成 | 旧候选的接受不能用于新候选 |
| Issue 被取消 | Issue 记录业务取消决定 | 撤销后续派发并分别处理在途 SOP / Run | Issue Cancelled 不代表所有 Run 已 Cancelled |
| Evaluation 完成 | Evaluation 保存独立结论 | 维护者评估是否提出改进 | Evaluation 通过不自动发布资产 |
| 方法资产发布 | Release 固定审核通过的版本和适用范围 | 项目可设为默认，或由负责人在获准 Issue 内选用 | 发布和选版均不证明实际使用 |
| 项目批准工作流或分工变更 | 有权成员在原配置或 Issue 记录范围及在途安排 | 适用工作按该决定继续，并记录实际使用的配置 | 新配置不自动改变既有交付或验收 |

## 12. 重试、返工、取消与接管

| 情况 | 所属层 | 必须保留的关系 | 继续条件 |
|---|---|---|---|
| 同一请求因传输或暂态故障重送 | 派发 / 事件层 | 原安排与幂等关联 | 查回原安排和 Run，补投未完成动作 |
| 宿主内部恢复或系统 Retry | Run 层 | 原生 Retry 谱系和各次宿主调用 | 由原执行链恢复；是否新 Run 以 Multica 记录为准 |
| 人工要求重新执行 | Run 层 | 原 Run 与人工 Rerun 关系 | 核对当前授权、输入和执行资源后创建新执行 |
| 节点在同一输入与授权下自修正 | Node Attempt 层 | 同一 Node Activation 下的修正尝试及 Run | 未超过节点修正预算，且范围未改变 |
| 候选或业务目标变化后的返工 | Issue / SOP 层 | 新候选、新激活或新工作约定；旧结果保留 | 重新判断受影响依赖和证据，授权范围足够 |
| 取消 Issue / SOP | 对应业务或流程层 | 取消决定、影响范围、待停止执行 | 停止新派发；在途 Run 分别确认终态和副作用 |
| 成员或 Runtime 离线后的接管 | Issue / 执行层 | 原负责人、旧 Run、交付版本、授权与接管决定 | 接手者以自己的身份和权限取得共享材料，确认旧执行不会继续写入冲突工作副本 |
| 迟到回执 | 原 Run / Attempt | 原事件身份、Run、激活和候选轮次 | 只补充原记录；只有当前有效性检查通过才可被当前节点消费 |

业务返工不能用 Multica 的系统重试或人工重跑关系代替。技术重试、人工重跑、节点修正、业务返工和新 Issue 各自保留不同因果关系。

## 13. 状态联动总原则

跨层联动遵循单向事实消费，而不是双向状态同步：

- Issue 提供目标、责任、约定和业务决定。
- Project Workflow 根据 Issue 事实决定是否交接项目步骤。
- SOP Execution 在受托范围内消费 Issue 约定和节点结果，决定自己的节点推进。
- Run 只报告真实受管执行事实；节点和负责人消费结果。
- Artifact、Evidence、Candidate 和 Delivery Record 固定交付与依据；Issue 有权主体决定接受与完成。
- Evaluation 消费已授权证据并给出评价；维护者决定是否改进、发布，项目维护者决定是否采用。
- 后续工作记录实际选择、投递和使用，不把发布或采用推断成执行事实。

平台可以从多个对象重建某项工作的完整轨迹，但任何单一状态都不能代替整条轨迹。

## 14. 与现有专题的边界

| 专题 | 维护的状态与行为 |
|---|---|
| [工作生命周期](01-unified-work-lifecycle.md) | Issue 状态、工作约定、责任交接、候选处置、验收与完成 |
| [SOP 与工作流](02-sop-workflow.md) | SOP Definition / Execution、节点激活与尝试、依赖、门禁、返工和出口 |
| [本地执行](03a-execution-plane.md) | Run、Session、Runtime、Daemon、宿主回执、取消、恢复与执行归属 |
| [能力与上下文](03b-capability-governance.md) | 资产定义、发布、采用、选择、投递及实际使用记录 |
| [成本、质量与改进](04-cost-quality-improvement.md) | Usage、Evaluation、Finding、Proposal、Benchmark 和 Release |
| [统一工作台](05-unified-workbench.md) | 呈现权威状态、等待原因、因果关系和下一责任人 |

若专题状态描述与本文冲突，应修订对应专题，使其符合统一语义；不能在局部文档中另造相互矛盾的状态定义。
