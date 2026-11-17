# VS-0 / VS-1 · 业务意图身份、Task 绑定与执行恢复契约

> 本文细化[技术方案准备与最小纵向切片](technical-solution-readiness.md)的 VS-0 / VS-1。
> 目标：把 Issue 首次 Main Bot 激活和 Comment 目标级 Worker 委派，可靠转换为 Multica 原生 Task，并在提交成功但响应丢失时查回同一 Task。
> Multica 源码基准：71683141a764ed3b1620db4bc26a2d0a098f135c。
> 本文定义逻辑身份、操作和事务边界；不指定物理表名、HTTP 路径或部署拆分。

## 1. 设计结论

**业务来源先形成稳定、可恢复的派发意图；同一来源幂等绑定一个主 Task；合法 Retry 后继保留原生谱系；绑定后 Claim、中心 Start、宿主启动和终态全部沿 Multica 原生执行链取证。**

需要两个方向都可核对：
- 来源侧知道“这次业务意图对应哪个 Task，当前授权是否仍有效”；
- Task 侧知道“自己由哪个业务意图产生”。

不能只保存来源字段，也不能只在来源侧写 dispatched=true。

当前 Multica 的 trigger_evidence_kind/ref_id 提供来源导航，(Issue, Agent) pending 唯一约束保护部分并发重复项；两者都不能替代业务意图幂等身份。D5 的三个来源身份继续各自独立，不统一成模糊的 Issue revision。

## 2. 两类意图的稳定身份

### 2.1 Main Bot 首次激活

业务身份由以下内容组成：
- Issue ID；
- 本次**有效指派 / 持续协调授权转换 ID**；
- 授权代际；
- 目标 Agent ID；
- 触发类型（首次持续协调激活）。

不能使用：
- 任意 Issue revision（标题、评论等无关修改也会增加 revision）；
- Issue ID + Agent ID（同一 Agent 可能被撤权后再次获派）；
- Session ID（Session 不是业务授权）；
- 时间戳（不具备稳定业务唯一性）。

同一 Agent 被撤权后再次获派，即使 Agent ID 没变，也产生新的授权代际和首次激活身份。首次激活意图只创建该代际的首个协调 Task；后续 Main Bot Turn 由新的工作变化 / Wakeup / 明确待处理工作驱动，不反复复用“首次激活”身份。

约定版本、持续协调模式及授权代际由[工作约定权威入口](cross-layer-contracts.md#32-工作约定的逻辑操作)产生；普通 Agent 指派不自动建立持续协调身份。总责和 Acceptor 使用正式 Work Agreement 引用，通用成员属性只作展示 / 联系人投影。项目已有配置直接继承，成员只确认本项差异。

### 2.2 Comment 目标级 Worker 委派

每个目标独立形成业务身份：
- Comment ID；
- Target Agent ID；
- 触发类型（显式 @Agent、回复 Agent 或其他明确触发）；
- 目标解析版本 / 解析结果版本。

一条 Comment @ 三个 Agent，必须有三个目标级意图。一个目标成功不代表其他目标成功。

解析版本固定“当时这条评论想交给谁”；恢复时仍需重新核对当前权限和 Issue 状态。历史解析不是永久授权。若重新解析后目标集合变化，按新的解析修订处理，不覆盖旧目标事实。

## 3. 派发意图的逻辑状态

派发意图不是 Task，也不是新的执行队列。它是来源业务对象上的可恢复关联和处理状态。

| 状态 | 含义 | 是否允许创建主 Task |
|---|---|---|
| Pending | 业务意图已生效，尚未确认绑定 Task | 是；前提是当前授权和来源仍有效 |
| Bound | 已绑定唯一的原生 Task ID，或已证明由兼容 Task 覆盖 | 否；沿原 Task 等待 |
| Blocked | 已知权限、Agent、Runtime、输入或 HEAD 冲突阻止派发 | 否；条件改变后重新判断 |
| Unknown | 不能证明 Task 是否创建 / 绑定 | 否；先按意图身份查回和对账 |
| Superseded | 授权代际、Comment 解析版本或业务范围已被新事实替代 | 否；旧 Task 仍保留原执行归属 |
| Cancelled | 有权主体明确撤销该意图 | 否；已启动 Task 的停止另按原生取消与副作用核验处理 |

Bound 只表示“业务意图已关联原生 Task”，不代表 Task 已排队、已领取或已启动。执行状态继续读取 Multica。

主 Task 是该 Intent 首次创建或经覆盖核验后绑定的 Task。表中的查重和创建限制针对这一绑定；Multica 合法 Retry 后继按原生恢复关系创建和查回，保留实际 Task ID 与 `retry_of_task_id`。它们不会把 Bound 改回 Pending，也不构成第二个主 Task。

## 4. 逻辑操作契约

### 4.1 建立意图

RecordDispatchIntent(source, target, authorization, sourceVersion)

前置：
- 来源业务写入已经通过权限和版本检查；
- 目标 Agent 已被解析；
- 记录当时的授权代际和来源版本。

结果：
- 返回稳定 Intent ID；
- 同一来源身份重复提交返回原 Intent；
- 同一 Comment 的不同目标返回不同 Intent；
- 只有真实指派 / 授权转换才产生 Main Bot 首次激活 Intent。

### 4.2 幂等创建或查回 Task

CreateOrGetTask(intentId, targetAgent, issueId, executionContract)

必须满足：
1. 相同 Intent ID 重复调用返回同一个主 Task，并提供其合法原生 Retry 后继的查回关系；
2. Task 写入同时保存可反查的 Intent 来源身份；
3. 主 Task 已创建但调用方响应丢失时，重送通过 Intent ID 查回原主 Task；即使已有原生终态或 Retry 后继，也不再创建另一个主 Task；
4. 同一 Issue / Agent 的 pending Task 可以被复用，但只有证明其执行范围、HEAD、输入和授权确实覆盖当前意图时，才能将 Intent 绑定到该 Task；
5. 只有确定主 Task 不存在时才允许新建；
6. 出现多个独立主 Task 或来源证据不足时返回 Unknown；同一合法 Retry 谱系中的多次执行可分别查回，不作为重复主 Task。

Task 的原生来源证据字段仍保留用于导航和审计；严格幂等查回需要一个具有唯一语义的派发身份。它可以作为 Multica Task 创建边界的扩展能力，不要求引入第二套 Run。

来源唯一性约束只保证一个主 Task；Retry 子项按 Multica 的原生重试身份与谱系查重，不能因继承同一来源就被全局唯一约束挡住。技术重试不授予新的业务权限，执行和消费仍核对当前授权。明确人工 Rerun 使用新的重跑动作身份并保留 `rerun_of_task_id`，普通网络重送不伪装成重跑。

### 4.3 绑定结果

BindIntentToTask(intentId, taskId, bindingEvidence)

绑定前核对：
- Task 属于同一 Workspace / Issue / Target Agent；
- Task 的触发来源与 Intent 相符；
- Task 的授权代际和执行契约没有超出来源授权；
- 新复用的 Task 仍可合法接收本次输入，未被取消、被不兼容意图占用或属于旧激活。

同一 Intent 已绑定相同主 Task 时幂等成功；已绑定不同主 Task 时不得覆盖，进入冲突核查。恢复原创建结果时，主 Task 已终态也应补回真实历史关联，并查回合法 Retry 后继；补绑定不恢复已失效授权，也不把终态 Task 重新入队。

### 4.4 启动与终态

Task 绑定后读取原生执行事实，以下为统一观察语义；原生状态映射见[Run 生命周期](lifecycle-state-event-model.md#7-run-生命周期)：
- Queued：Multica 已持久化等待执行；
- Dispatched / Claimed：Runtime 已领取，尚未证明实际启动；
- Start Acknowledged / Starting：中心已接受当前 claim 的 Start，Task 的原生状态可为 `running`，宿主仍在启动；
- Running：取得对应 Backend / provider-session / 宿主的真实启动回执；
- Succeeded / Failed / Cancelled：分别根据 Multica 原生 `completed` / `failed` / `cancelled` 终态映射；
- Unknown / Lost：按 Multica 原生恢复、租约、进程和写入隔离规则核实。

Main Bot / Worker 不能仅凭收到派发请求就声称已开工。

`7168314` 的 Daemon 在[中心 Start 成功后仍报告 Launching](https://github.com/multica-ai/multica/blob/71683141a764ed3b1620db4bc26a2d0a098f135c/server/internal/daemon/daemon.go#L8955-L8971)，随后在[Backend.Execute 成功返回会话后](https://github.com/multica-ai/multica/blob/71683141a764ed3b1620db4bc26a2d0a098f135c/server/internal/daemon/daemon.go#L10159-L10173)才记录 `taskPhaseRuntimeStarted`。只有中心回执时显示启动中；启动失败记录真实失败，缺宿主回执时保留启动待确认。

## 5. 事务边界：先保存来源意图，再做外部派发

### 5.1 Issue 指派路径

当前 Multica 的路径是 Issue 更新成功后再调用 dispatchIssueRun；Agent enqueue 返回错误在 Handler 中被忽略。因此 Issue 写入成功并不保证首次 Main Bot Task 已创建。

正式工作约定先按[创建 / 修订 / 撤销操作](cross-layer-contracts.md#32-工作约定的逻辑操作)确认普通执行或持续协调模式及责任引用；下面的首次激活流程仅适用于已确认持续授权的转换。

目标语义：

1. Issue 当前 Assignee / Work Agreement / 授权代际的权威写入生效；
2. 同一权威事务内保存该次指派转换的首次激活意图；
3. 事务提交后，由现有后台恢复 / 派发路径处理 Pending Intent；
4. 通过 CreateOrGetTask(intentId) 创建或查回原生主 Task 及其 Retry 后继；
5. 绑定成功后发送 Task Queued 通知；
6. Runtime Claim / Start 仍由 Multica 原生路径负责。

若 Issue 写入事务回滚，首次激活意图不得存在；若事务提交后进程退出，Pending Intent 必须仍可被恢复扫描发现。

### 5.2 Comment / Worker 路径

目标语义：
1. Comment 与附件先按 Multica 原生事务原子保存；
2. 在 Comment 保存时固定本次目标解析结果及解析版本，或保存足以按固定解析器版本确定性恢复的原始提及信息；不能在恢复时用当前 Agent 名称 / 目录重新解释历史文本并静默改变目标集合；
3. 为解析出的每个目标形成稳定 Intent；若目标解析需要异步完成，Comment 的持久化事实必须足以恢复同一解析修订，目标解析完成前状态为待解析而非已派发；
4. 每个目标独立调用 CreateOrGetTask(intentId) 或登记到可证明覆盖的现有 Task；
5. 某个目标失败不回滚已保存 Comment，也不抹去其他目标成功；
6. 目标级 Pending / Blocked / Unknown 可从 Comment 重新查回；
7. 同 HEAD 评论可复用 Multica coalescing / planned comment；不同 HEAD blocker 保留目标级未解决状态，不能虚报已接单。

评论事务和派发事务不要求跨外部 Runtime 做全局事务。关键是来源意图持久存在、Task 创建幂等、恢复可查回。

## 6. 恢复算法

所有恢复入口执行同一顺序：

1. 读取来源对象及 Intent，确认其授权代际 / 来源版本仍有效；
2. 若 Intent 已 Bound，直接查回原 Task，不再创建；
3. 若 Intent 为 Unknown，按稳定 Intent ID 查回 Task；
4. 若找到唯一兼容主 Task，补绑定，并查回原生 Retry 谱系；
5. 若找到多个独立主 Task 或证据不一致，保持 Unknown 并交给对账；
6. 若能证明主 Task 不存在且 Intent 仍有效，执行 CreateOrGetTask；
7. 若授权 / 来源版本已失效，标记 Superseded / Cancelled，不再派发；
8. 发送通知失败只重发通知，不重复创建 Task；
9. Task 已终态但业务消费者未消费时，转交原结果消费契约，不重跑生产。Main Bot 使用[受控消费操作](d5-cross-layer-recovery-contract.md#611-main-bot-使用的受控消费操作)列未消费委派、读取固定交付并条件提交结论；内容适用性由 Main Bot 判断，服务端负责身份、版本、当前权限与幂等检查。

## 7. 故障场景与验收

| 故障注入 | 预期权威事实 | 恢复结果 |
|---|---|---|
| Issue 指派写入前进程退出 | Issue 与 Intent 均未提交 | 不创建 Task |
| Issue 与 Intent 已提交，派发进程退出 | Pending Intent 存在 | 恢复后创建一个 Task |
| 主 Task 创建成功，响应在返回前丢失 | 主 Task 保存 Intent ID；来源尚未 Bound | 重送查回同一个主 Task 并补绑定 |
| 两个恢复者并发派发同一 Intent | 同一 Intent 身份 | 只产生一个主 Task，另一方取得同一主 Task |
| 主 Task 已失败，Multica 已创建合法 Retry 子项 | 原主 Task 与 `retry_of_task_id` 谱系均存在 | 重送查回原主 Task 和 Retry 后继；不创建第二个主 Task，不拒绝合法原生 Retry |
| 同 Agent 已有不兼容 HEAD 的 queued Task | 原 Task 不能证明覆盖当前意图 | 当前 Intent 保持 Pending / Blocked，不绑定旧 Task |
| Runtime 离线 | Task 已 Bound / Queued | 等待原 Task，不新建 |
| Claim 成功但响应丢失 | 原 Task 处于原生 `dispatched`，未 Start | Multica reclaim 同一 Task |
| 中心 Start 已成功，回执迟到 | 中心 Task 已是 `running`，宿主启动证据单独核对 | 查回 / 重放同 claim 的 Start，不创建新执行；缺宿主启动回执时仍显示启动中 |
| 中心 Start 成功后宿主启动失败 | 中心曾确认 Start，Backend 返回实际启动失败 | 记录启动失败，不显示宿主已开工；恢复按原生失败 / Retry 关系处理 |
| 授权在派发前撤销 | Intent 代际已失效 | Superseded，不创建 Task |
| 授权在 Task 运行中撤销 | 原 Task 仍有执行事实 | 阻止新派发 / 新业务推进；停止旧 Run 按原生取消和副作用核验 |
| 一条 Comment 的三个目标只有两个成功 | 三个目标 Intent 独立 | 只恢复未解决目标 |
| Comment 已保存、目标触发尚未开始 | Comment 与目标解析版本可回读 | 重新解析 / 核对权限并逐目标恢复 |
| Main Bot 消费结论已提交，返回响应丢失或新 Turn 重送 | 原消费身份、结论与后继意图已保存 | 返回原消费记录，只恢复尚未完成的后继；不重复委派或推进 |
| Main Bot 撤权后旧代际消费请求到达 | 当前正式委托已改变，旧结果保留原归属 | 服务端拒绝推进当前业务；当前负责人复用旧结果须按新代际显式提交依据 |

首个真实验收至少要覆盖：事务提交后进程退出、主 Task 创建响应丢失、并发重复派发、合法 Retry 查回、Runtime 离线、中心 Start 后宿主启动失败、消费响应丢失、跨 Turn 重复消费及旧代际撤权竞争。只用模拟 Task ID 不算通过。

## 8. 与现有 Multica 的复用与扩展边界

| 现有能力 | 直接复用 | 必须补充 / 核验 |
|---|---|---|
| Issue / Comment 权威写入 | 是 | Issue 指派转换与首次激活 Intent 同事务持久化 |
| Task / Run 队列与 Runtime | 是 | 原生 Task 增加稳定 Intent 查回语义 |
| (Issue, Agent) pending 唯一约束 | 是，作为第二道防线 | 不能代替来源身份幂等 |
| trigger_evidence_kind / ref_id | 是，作来源导航 | 不能作为唯一幂等键 |
| trigger_comment_id / coalesced_comment_ids | 是，作评论输入与合并 | 不能替代逐目标 Intent |
| Claim / Start / Reclaim | 是 | 平台消费真实回执，不自建状态 |
| Issue Wakeup Receipt | 是，作唤醒信号 | 不作为 Intent 或永久事件历史 |
| Task Usage | 是，按原生 Task 归集 | 不完整上报保持 Unknown |

固定源码：
- [Issue 更新后派发](https://github.com/multica-ai/multica/blob/71683141a764ed3b1620db4bc26a2d0a098f135c/server/internal/handler/issue.go)
- [派发入口](https://github.com/multica-ai/multica/blob/71683141a764ed3b1620db4bc26a2d0a098f135c/server/internal/handler/issue_trigger.go)
- [Task 创建、pending 去重和来源写入](https://github.com/multica-ai/multica/blob/71683141a764ed3b1620db4bc26a2d0a098f135c/server/internal/service/task.go)
- [Task 队列与 Claim / Reclaim](https://github.com/multica-ai/multica/blob/71683141a764ed3b1620db4bc26a2d0a098f135c/server/pkg/db/queries/agent.sql)
- [Task 来源字段](https://github.com/multica-ai/multica/blob/71683141a764ed3b1620db4bc26a2d0a098f135c/server/migrations/184_agent_task_attribution.up.sql)
- [Wakeup 源事务捕获](https://github.com/multica-ai/multica/blob/71683141a764ed3b1620db4bc26a2d0a098f135c/server/migrations/518_wakeup_event_capture.up.sql)

## 9. VS-0 / VS-1 完成标准

- 每种业务来源身份稳定，不使用 Issue revision、Session 或时间戳冒充身份；
- Issue 指派 / 授权转换与首次激活 Intent 原子生效；
- Comment 的每个目标 Agent 都有独立可恢复 Intent；
- 主 Task 可按 Intent 幂等查回，合法 Retry 后继保留原生谱系；
- 来源侧和 Task 侧能互相核验；
- Pending、Bound、Blocked、Unknown、Superseded / Cancelled 语义明确；
- Claim / 中心 Start / 宿主启动 / 终态按 Multica 的不同回执分开确认；
- 通知丢失、进程退出、重复触发和 Runtime 离线不造成重复执行；
- 撤权和旧代际迟到结果不会推进新授权；
- 正式 Work Agreement / Delegation 产生可核验版本、责任引用及授权代际；联系人属性修改不改变正式权限；
- Main Bot 通过受控操作幂等消费委派结果，服务端拒绝旧代际及重复后继动作；
- 真实故障注入结果可回溯到 Issue、Intent、Task、Run 和消费记录。

## 10. 下一步

本契约为后续交付与验收提供来源、授权和执行依据；交付规则由 [VS2](vs2-candidate-acceptance-technical-contract.md)维护。当前工程从 [VS5 的 E0 来源查回与生产兼容设计](vs5-overall-technical-consistency-review.md#9-实施依赖与最小工程切片)开始，再按 E1 / E2 落实本契约及交付闭环。
