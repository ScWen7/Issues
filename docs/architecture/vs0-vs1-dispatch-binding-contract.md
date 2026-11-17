# VS-0 / VS-1 · 业务意图身份、Task 绑定与执行恢复契约

> 本文细化[技术方案准备与最小纵向切片](technical-solution-readiness.md)的 VS-0 / VS-1。
> 目标：把 Issue 首次 Main Bot 激活和 Comment 目标级 Worker 委派，可靠转换为 Multica 原生 Task，并在提交成功但响应丢失时查回同一 Task。
> Multica 源码基准：71683141a764ed3b1620db4bc26a2d0a098f135c。
> 本文定义逻辑身份、操作和事务边界；不指定物理表名、HTTP 路径或部署拆分。

## 1. 设计结论

**业务来源先形成稳定、可恢复的派发意图；原生 Task 创建必须按该意图幂等；Task ID 绑定成功后，后续 Claim / Start / 终态全部沿 Multica 原生执行链。**

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

| 状态 | 含义 | 是否允许创建 Task |
|---|---|---|
| Pending | 业务意图已生效，尚未确认绑定 Task | 是；前提是当前授权和来源仍有效 |
| Bound | 已绑定唯一的原生 Task ID，或已证明由兼容 Task 覆盖 | 否；沿原 Task 等待 |
| Blocked | 已知权限、Agent、Runtime、输入或 HEAD 冲突阻止派发 | 否；条件改变后重新判断 |
| Unknown | 不能证明 Task 是否创建 / 绑定 | 否；先按意图身份查回和对账 |
| Superseded | 授权代际、Comment 解析版本或业务范围已被新事实替代 | 否；旧 Task 仍保留原执行归属 |
| Cancelled | 有权主体明确撤销该意图 | 否；已启动 Task 的停止另按原生取消与副作用核验处理 |

Bound 只表示“业务意图已关联原生 Task”，不代表 Task 已排队、已领取或已启动。执行状态继续读取 Multica。

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
1. 相同 Intent ID 重复调用只返回同一个 Task；
2. Task 写入同时保存可反查的 Intent 来源身份；
3. Task 已创建但调用方响应丢失时，重试通过 Intent ID 查回原 Task；
4. 同一 Issue / Agent 的 pending Task 可以被复用，但只有证明其执行范围、HEAD、输入和授权确实覆盖当前意图时，才能将 Intent 绑定到该 Task；
5. 只有确定 Task 不存在时才允许新建；
6. 出现多个候选或来源证据不足时返回 Unknown，不猜测、不新建。

Task 的原生来源证据字段仍保留用于导航和审计；严格幂等查回需要一个具有唯一语义的派发身份。它可以作为 Multica Task 创建边界的扩展能力，不要求引入第二套 Run。

### 4.3 绑定结果

BindIntentToTask(intentId, taskId, bindingEvidence)

绑定前核对：
- Task 属于同一 Workspace / Issue / Target Agent；
- Task 的触发来源与 Intent 相符；
- Task 的授权代际和执行契约没有超出来源授权；
- Task 不是已被取消、已被其他不兼容意图占用或属于旧激活的执行。

同一 Intent 已绑定相同 Task 时幂等成功；已绑定不同 Task 时不得覆盖，进入冲突核查。

### 4.4 启动与终态

Task 绑定后不再由平台自建状态机：
- Queued：Multica 已持久化等待执行；
- Dispatched / Claimed：Runtime 已领取，尚未证明实际启动；
- Started / Running：收到真实 Start 回执；
- Completed / Failed / Cancelled：读取 Multica 终态；
- Unknown / Lost：按 Multica 原生恢复、租约、进程和写入隔离规则核实。

Main Bot / Worker 不能仅凭收到派发请求就声称已开工。

## 5. 事务边界：先保存来源意图，再做外部派发

### 5.1 Issue 指派路径

当前 Multica 的路径是 Issue 更新成功后再调用 dispatchIssueRun；Agent enqueue 返回错误在 Handler 中被忽略。因此 Issue 写入成功并不保证首次 Main Bot Task 已创建。

目标语义：
1. Issue 当前 Assignee / Work Agreement / 授权代际的权威写入生效；
2. 同一权威事务内保存该次指派转换的首次激活意图；
3. 事务提交后，由现有后台恢复 / 派发路径处理 Pending Intent；
4. 通过 CreateOrGetTask(intentId) 创建或查回原生 Task；
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
4. 若找到唯一兼容 Task，补绑定；
5. 若找到多个候选或证据不一致，保持 Unknown 并交给对账；
6. 若能证明 Task 不存在且 Intent 仍有效，执行 CreateOrGetTask；
7. 若授权 / 来源版本已失效，标记 Superseded / Cancelled，不再派发；
8. 发送通知失败只重发通知，不重复创建 Task；
9. Task 已终态但业务消费者未消费时，转交原结果消费契约，不重跑生产。

## 7. 故障场景与验收

| 故障注入 | 预期权威事实 | 恢复结果 |
|---|---|---|
| Issue 指派写入前进程退出 | Issue 与 Intent 均未提交 | 不创建 Task |
| Issue 与 Intent 已提交，派发进程退出 | Pending Intent 存在 | 恢复后创建一个 Task |
| Task 创建成功，响应在返回前丢失 | Task 保存 Intent ID；来源尚未 Bound | 重试查回同一个 Task 并补绑定 |
| 两个恢复者并发派发同一 Intent | 同一 Intent 身份 | 只产生一个 Task，另一方取得同一 Task |
| 同 Agent 已有不兼容 HEAD 的 queued Task | 原 Task 不能证明覆盖当前意图 | 当前 Intent 保持 Pending / Blocked，不绑定旧 Task |
| Runtime 离线 | Task 已 Bound / Queued | 等待原 Task，不新建 |
| Claim 成功但响应丢失 | 原 Task 处于 Dispatched，未 Start | Multica reclaim 同一 Task |
| Start 已成功，回执迟到 | 原 Task 已 Started | 读取原 Task / Run，不创建新执行 |
| 授权在派发前撤销 | Intent 代际已失效 | Superseded，不创建 Task |
| 授权在 Task 运行中撤销 | 原 Task 仍有执行事实 | 阻止新派发 / 新业务推进；停止旧 Run 按原生取消和副作用核验 |
| 一条 Comment 的三个目标只有两个成功 | 三个目标 Intent 独立 | 只恢复未解决目标 |
| Comment 已保存、目标触发尚未开始 | Comment 与目标解析版本可回读 | 重新解析 / 核对权限并逐目标恢复 |

首个真实验收至少要覆盖：事务提交后进程退出、Task 创建响应丢失、并发重复派发、Runtime 离线和撤权竞争。只用模拟 Task ID 不算通过。

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
- Task 创建可按 Intent 幂等查回；
- 来源侧和 Task 侧能互相核验；
- Pending、Bound、Blocked、Unknown、Superseded / Cancelled 语义明确；
- Claim / Start / 终态完全复用 Multica；
- 通知丢失、进程退出、重复触发和 Runtime 离线不造成重复执行；
- 撤权和旧代际迟到结果不会推进新授权；
- 真实故障注入结果可回溯到 Issue、Intent、Task、Run 和消费记录。

## 10. 下一步

VS-0 / VS-1 的逻辑身份和恢复契约收敛后，下一步进入 VS-2：Candidate manifest、Artifact 不可变定位、Evidence 版本绑定和 Acceptance Decision 的权威条件写入。不要在 VS-2 完成前并行设计所有领域的数据库结构。
