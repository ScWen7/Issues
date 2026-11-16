# D5-3 · 最小派发绑定与结果消费契约

> 研究基准：AgentPlatform 当前设计分支；Multica 源码固定提交 `0f3e15f1d9dca781155e2fe475161f8c5e499b44`。
> 目标：把 D5-1 / D5-2 的分散恢复规则收敛为一份跨层契约，明确每种业务动作的身份、权威来源、Task 绑定、执行确认、结果消费和恢复责任。
> 范围：架构设计收敛，不指定数据库表、API、消息中间件或部署实现。

## 1. 最终设计判断

D5 不需要新增一套统一任务系统，也不需要把 Main Bot、Worker、SOP 节点都变成平台自有 Run。

**最小闭环是：现有业务权威对象 + 可持久查回的派发绑定 + Multica 原生 Task / Run + 业务结果消费记录。**

派发绑定不是新的业务对象，也不是第二套队列。它是业务来源与原生 Task 之间必须可查回的一条关系：
- 来源对象保留“为什么要执行、当前授权是否仍有效、该意图是否已经被某个 Task 覆盖”；
- Task 保留实际执行身份和可定位的来源证据；
- 来源对象或目标消费者保留结果是否已被消费；
- 通知和 Wakeup 只负责促使参与者重新读取这些权威事实。

不能只在 Task 侧留来源字段，也不能只在来源侧写一个“已派发”布尔值。两端都要能够核对。

## 2. 三类业务触发的身份和绑定

| 维度 | Main Bot 首次激活 | 一次性 Worker 委派 | SOP 节点执行 |
|---|---|---|---|
| 业务权威来源 | Issue 当前指派、有效 Work Agreement / 持续授权 | 原 Comment 及本次解析出的目标 Agent | SOP Execution、Node Activation、Node Attempt |
| 稳定意图身份 | 指派 / 授权生效的具体转换身份 + 授权代际 | Comment ID + Target Agent ID + 触发类型 / 目标解析版本 | Node Attempt ID + 本次 Run 调用身份 |
| 一项来源可有多少派发 | 每个有效持续委托代际有一个首次协调激活；后续协调回合按新唤醒 / 待处理工作产生 | 同一 Comment 可面向多个目标；每个目标分别记录状态 | 一个 Attempt 可关联多个 Run；每个实际 Run 调用有独立身份 |
| 当前授权来源 | Issue 当前 Assignee 和 Work Agreement | 发起评论时的调用许可；补派时重新核对当前委托、目标权限和 Issue 状态 | 当前 SOP Execution / Activation / Attempt 及其授权版本 |
| Task 来源证据 | Issue assignment / activation 来源引用 | Comment 来源引用；可使用 Task 原生 trigger_comment_id / coalesced_comment_ids | Node Attempt / Run 调用来源引用 |
| Task 绑定位置 | 原 Issue 的首次激活关联 | 原 Comment 的目标级委派关联 | 原 Node Attempt 的 Run 关联 |
| 执行开始确认 | Task 的 Runtime Start 回执 | Worker Task 的 Runtime Start 回执 | 本次 Run 的 Runtime Start 回执 |
| 结果消费方 | 当前 Main Bot 协调回合；必要时交回 Issue Owner | 原委派接收方 / Main Bot，按原 Comment 逐目标消费 | 原 Node Attempt；消费成功后才决定 Activation 成功与后继 Ready |
| 唤醒机制 | 持续委托的 Wakeup / Issue 事实变化 | 可唤醒 Main Bot 重读 Comment 和目标状态 | SOP 调度恢复；必要时使用 Issue Wakeup 提醒协调方 |
| 新一轮条件 | 新的指派 / 授权代际 | 新 Comment 或明确新委派意图 | 新 Activation / Attempt 或同 Attempt 中明确的新 Run 调用 |

### 2.1 稳定身份不等于 Issue revision

Issue revision 是并发写入版本，不是派发操作身份。标题、描述、优先级等无关字段变化不应让 Main Bot 的首次激活变成一个新动作。

Main Bot 首次激活应引用**导致本次持续委托生效的具体指派 / 授权转换**。同一 Agent 后续被再次指派时，必须有新的授权代际；即使 Assignee ID 相同，也不能沿用旧激活身份。若现有 Issue Activity 不能唯一表示这次转换，需在权威 Issue 变更记录中补足稳定的转换身份；不能用时间戳或当前字段值推测。

### 2.2 评论目标必须分别处理

Comment ID 是稳定来源，但一条评论可以 @ 多个 Agent / Squad。恢复时不能只记录“这条评论已触发”，而要逐目标核对：
- 目标解析是否成功；
- 目标当前是否仍有调用权限；
- 是否创建新 Task；
- 是否被某个兼容的 queued Task 合并；
- 是否登记为某个已领取 Task 的 planned input；
- 是否明确 blocked / superseded；
- 结果是否已经由委派方消费。

同一 Comment + 同一目标的网络重送沿用原委派身份。不同目标之间不能互相覆盖成功状态。目标解析版本用于解释原始目标集合；补派前仍重新校验当前权限，历史解析不构成永久授权。

### 2.3 一个 Node Attempt 可以有多个 Run，但不能共享一个模糊的 Run 身份

Node Attempt 表示一次业务履行，可包含修正、检查或多次受管执行。每个 Run 调用都要有自己的派发身份，例如由 Attempt 与本次调用序号 / 调用标识组成。技术 Retry 和宿主内部恢复沿用 Multica 原生谱系；人工 Rerun 和业务返工保留不同关系。

不能将 Node Attempt ID 直接当作唯一 Run ID，否则一个 Attempt 的第二次合法执行会被错误去重；也不能只用 SOP Node ID，否则不同 Activation 会串线。

## 3. 派发绑定不是新领域对象

核心对象模型已包含 Issue、Comment、SOP Execution、Node Activation、Node Attempt 和 Run。D5 不新增 Dispatch、ExecutionJob、PlatformTask 或 CoordinatorRun 等并行对象。

派发绑定是一种跨对象关系，最少包含：
- 来源业务身份；
- 目标执行 Agent；
- 授权 / 工作约定代际；
- 固定输入与执行契约版本；
- 绑定的 Multica Task ID（若尚无则明确未绑定）；
- 复用已有 Task 时的覆盖依据；
- 派发处理结果与阻塞 / 未知原因；
- 目标结果消费状态。

它可以由现有权威对象中的关联、Task 的来源证据和消费记录共同表达。**不要求所有信息塞进同一张表，也不要求每条普通通知都成为业务对象。**

来源侧的关系是恢复依据；Task 侧的来源引用是反向核验依据；两者不一致时以查证为先，不自动挑一端覆盖另一端。

## 4. Multica 原生字段的可复用边界

Multica 固定版本已有：
- `trigger_comment_id` / `coalesced_comment_ids`：标识 Task 的评论触发输入；
- `trigger_evidence_kind` / `trigger_evidence_ref_id`：自由文本类型 + 来源记录 ID，作为统一的直接触发证据引用；
- `delegated_from_task_id`：记录执行归因链中的父 Task；
- `retry_of_task_id` / `rerun_of_task_id`：区分系统 Retry 与人工 Rerun；
- Task 持久化队列、Claim Generation、过期 Claim reclaim 和 Start replay。

源码：
- [Migration 184：Task 触发证据字段定义](https://github.com/multica-ai/multica/blob/0f3e15f1d9dca781155e2fe475161f8c5e499b44/server/migrations/184_agent_task_attribution.up.sql)
- [Task 创建时写入来源证据](https://github.com/multica-ai/multica/blob/0f3e15f1d9dca781155e2fe475161f8c5e499b44/server/internal/service/task.go)
- [评论目标归并与 planned comment](https://github.com/multica-ai/multica/blob/0f3e15f1d9dca781155e2fe475161f8c5e499b44/server/internal/handler/comment.go)
- [Task Claim / reclaim](https://github.com/multica-ai/multica/blob/0f3e15f1d9dca781155e2fe475161f8c5e499b44/server/pkg/db/queries/agent.sql)

重要限制：
1. `trigger_evidence_kind/ref_id` 的迁移注释定义它是归因 / 直接触发证据的统一引用；它不是幂等键，也没有因此获得唯一约束。
2. 该字段只有一个 UUID 来源引用，不能天然表达“同一 Node Attempt 的第 N 次 Run 调用”或一个 Comment 对多个目标的独立状态。
3. `trigger_comment_id` 与 `coalesced_comment_ids` 对评论场景很有价值，但不覆盖 Main Bot 首次激活和 SOP Node Attempt 的全部来源身份。
4. Task 队列唯一约束防止某些同 Issue / Agent 待派重复项，不证明两个业务意图完全相同，也不能替代业务来源绑定。
5. 当前已核对的源码没有证明所有入口都能按外部业务意图稳定查回 Task，也没有证明 Task 创建与平台侧来源绑定在同一事务内。

因此可复用原生字段做来源导航和审计，但如果平台需要严格幂等查回，仍须在原生派发边界补齐稳定的外部派发身份、唯一性 / 查回能力，或在来源权威侧提供等价的可恢复对账关系。不要把审计字段误用成幂等机制。

## 5. 统一派发状态与确认边界

下面是派发关系的状态语义，不是新的 Task 生命周期，也不要求复制 Multica 的全部状态：

| 派发关系状态 | 何时成立 | 不代表什么 |
|---|---|---|
| Pending | 来源业务意图已生效，等待处理 | 不代表 Task 已创建 |
| Bound | 已绑定新建或可证明兼容的既有 Task | 不代表 Task 已领取 |
| Blocked | 已知权限、资源、输入或冲突条件不允许派发 | 不代表业务意图自动失效 |
| Unknown | 不能证明 Task 是否已创建或绑定 | 不能直接重试创建 |
| Superseded / Cancelled | 原授权、输入或业务意图已被新版本取代或撤销 | 不代表旧 Run 已停止 |
| Consumed | 对应结果已由目标业务对象按契约接收 | 不代表 Issue 已验收或完成 |

绑定之后，执行事实仍使用 Multica 原生状态：
- Queued：已排队；
- Dispatched / Claimed：已领取；
- Running：已实际启动；
- Completed / Failed / Cancelled：已取得终态；
- Lost / Unknown：终态不确定，需核实。

结果消费是另一条独立确认：Task completed 不能直接把 Worker 委派或 Node Attempt 标记为 Consumed。

## 6. 故障恢复的完整责任表

| 故障位置 | 谁负责恢复 | 权威依据 | 恢复动作 | 绝不能做 |
|---|---|---|---|---|
| Issue 指派已生效，首次 Task 未创建 | 协作核心的 Issue 派发恢复责任 | 当前 Assignee、授权代际、首次激活意图 | 确认授权仍有效后，补派同一激活 | 仅因 Issue 仍指派该 Agent 就盲目创建 Run |
| Task 已创建，来源侧绑定未确认 | 派发绑定恢复责任 | 来源身份、Task 来源证据、Issue / Agent / 输入 / 授权 | 查回唯一兼容 Task，补写绑定 | 仅按最新 Task 或时间最近的 Task 猜测 |
| Task 已排队，Runtime 离线 | Multica 执行派发层 | 原 Task ID、当前 Agent Runtime 绑定 | 等待原 Task 被领取；必要时由有权成员调整资源 | 创建第二个 Task 冒充恢复 |
| Claim / Start 响应丢失 | Multica Daemon / Task 层 | Task ID、Runtime ID、Claim Generation | Reclaim 或同一 Claim Start replay | 新建业务 Attempt 或新 Run |
| Comment 已保存，部分目标未派发 | 评论委派恢复责任 | Comment ID + 每个目标 Agent 的派发关系 | 逐目标补齐；复用已有覆盖 Task；保留 blocked | 把整条评论标成成功或重复创建评论 |
| 不同 HEAD queued blocker 阻止评论合并 | 评论委派恢复责任 | Comment HEAD、Task HEAD、目标 Agent | 保留目标级待处理义务；blocker 改变后重新判断 | 把旧 HEAD 评论并入新 HEAD Task |
| Node Attempt Ready，派发未完成 | SOP 编排层 | Node Activation / Attempt / 固定输入和授权 | 查回绑定；证明未创建后补派原调用 | 只凭 Ready 就重建新 Attempt |
| Run 已终态，Main Bot 未消费 | Main Bot 协调层 | 原委派身份、Task / Artifact / Candidate | 恢复协调 Turn，逐项核对并消费 | 因 Wakeup 重复而重复执行 Worker |
| Run 已终态，Node Attempt 未消费 | SOP 编排层 | Attempt ID、Run ID、结果版本 | 重放结果消费，消费成功后重算后继 Ready | 重跑已完成生产来弥补消费回执 |
| 消费成功，后继通知 / 派发未发生 | 消费者所属层（Main Bot / SOP） | 已提交的消费记录及当前状态 | 重算仍有效的后继动作并幂等补投 | 重复消费或重复推进节点 |
| 撤权 / 改派 / 输入换版与旧 Run 竞争 | 当前业务权威对象的负责人 + 执行层 | 当前授权代际、激活轮次、Run 来源 | 旧结果归原轮次；新写入前核对当前授权；必要时停止或隔离 | 让迟到回执推进新授权 / 新候选 |

## 7. 结果消费的共同契约

每个消费者必须在消费时核对：
1. 结果来自哪个真实 Run / Task；
2. 该 Run 对应哪个原业务意图；
3. 生产时使用的 Work Agreement、输入 Candidate、SOP 版本和授权代际；
4. 该结果是否满足本消费者的输出要求；
5. 当前消费者是否仍是该结果的有效接收方；
6. 同一结果是否已经消费，以及本次消费是否产生了后继动作。

消费分为三种业务行为：
- **采用**：结果符合当前约定，登记引用和采用范围；
- **退回 / 修正**：指出缺项或失败依据，按当前授权产生后续工作；
- **仅记录**：结果保留为历史证据，但当前授权、候选或流程轮次已变化，不推进当前状态。

消费记录与通知、后继派发分离。消费已经成功但通知丢失时，重读消费记录并补投后继动作；不得再次产生业务消费副作用。

Main Bot 消费 Worker 结果后，决定继续自主工作、委派下一项、调用局部 SOP 或把决定交回成员。SOP 消费节点结果后，按定义和当前激活判断节点是否成功及后继是否 Ready。两者共享恢复原则，但不共享业务决定权。

## 8. 授权代际与旧执行隔离

派发时捕获的授权只证明当时允许安排执行。真正开工、补派、消费和写入业务状态时，仍要核对当前授权：
- Issue 当前是否仍由该 Agent 持续协调；
- 一次性 Worker 委派是否仍在当前范围内；
- SOP Execution / Node Activation 是否仍有效；
- 输入 Candidate、Work Agreement 和能力版本是否仍适用；
- Runtime 是否仍获准且 Agent 当前绑定是否匹配。

撤权 / 改派不能仅靠删除 Wakeup 订阅来完成。它应阻止旧意图产生新的派发和业务推进；已经启动的 Run 单独请求停止并确认终态、副作用。迟到回报保留原来源，不得写入新激活或新授权的结果。

## 9. D5 完成标准与剩余实现前置

D5 的架构契约在以下方面已经收敛：
- 三类业务触发身份各有明确来源，不混用 Issue revision、Comment ID、Node ID；
- 来源与 Task 的绑定是关系，不新增平行任务对象；
- Multica 原生 Task / Run、Claim / Start / Retry / Rerun 继续作为唯一执行事实；
- Wakeup 只承担可靠唤醒，不承担业务命令记录；
- 结果消费与执行终态分离；
- 故障责任能定位到业务来源层、派发绑定层、执行层或消费者层；
- 授权代际和输入轮次约束迟到结果。

进入技术方案前仍需单独确认：
1. Issue 指派转换是否已有足够稳定的来源身份；若无，在哪个权威记录中补足。
2. Task 原生来源证据字段能否承载导航信息；严格查回所需的唯一身份 / 查询能力需要在哪个原生派发入口补齐。
3. Comment 目标级状态如何在评论持久化后被扫描和恢复，尤其不同 HEAD blocker 的后续接续。
4. SOP Node Attempt 与多个 Run 的绑定、消费记录和后继激活如何与当前对象模型落地。
5. 消费成功与后继动作之间如何保留可恢复关联，避免重复推进。
6. 对真实并发、事务提交后进程退出、响应丢失、撤权与迟到回报做故障注入验证。

这些是实现前置，不是继续扩展领域模型的理由。当前不指定数据库结构或 API。
