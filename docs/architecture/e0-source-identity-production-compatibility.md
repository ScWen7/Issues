# E0 · 来源身份查回与生产兼容设计

> 本文定义 E0 在进入 Schema / API 设计前必须成立的来源身份、原生 Task 绑定、普通生产兼容和故障恢复契约。它细化 VS-5，不替代 VS-0 / VS-1 的业务规则。
> 目标 Multica 基准：`71683141a764ed3b1620db4bc26a2d0a098f135c`。进入实现前必须对实际集成目标分支重新核对；本文不把该提交以后的能力推定为已存在。
> 本文不决定数据库表、API 路径、部署形态或具体代码扩展位置。

## 1. E0 要解决的核心问题

一项有效的生产执行意图，在任何时刻都必须能回答：

1. 为什么这次执行应该发生？
2. 谁授权、授权给谁、授权范围是什么？
3. 它对应哪个原生 Multica 主 Task？
4. 如果派发响应丢失或进程中断，怎样证明应查回、补派还是保持 Unknown？
5. 现有生产任务、Session、Wakeup、Usage 和 Runtime 行为是否保持兼容？

E0 只建立**生产执行来源身份与查回能力**，不实现完整 Main Bot 协调、SOP Runtime、交付验收或治理执行。它必须覆盖普通 Agent 一次性执行，不能只为 Main Bot 首次激活服务。

## 2. 统一生产执行意图分类

Production 是执行用途；一次性执行、Main Bot 协调和 SOP 节点是不同业务来源 / 角色，不是不同执行控制面。

| 生产来源 | 触发含义 | 业务身份 | 执行授权边界 |
|---|---|---|---|
| Issue 普通 Agent 指派 | 成员把当前 Issue 的一次执行交给 Agent | Issue + 本次有效指派转换 ID + 目标 Agent + 执行模式 | 只完成本次约定的交付；不自动获得持续协调、追加委派或改变责任的权力 |
| Main Bot 首次激活 | 成员明确把 Issue 的持续协调职责委托给 Agent | Issue + 本次持续委托转换 ID + 授权代际 + 目标 Agent | 在有效 Work Agreement / Delegation 范围内跨多个协调回合推进 |
| Comment 目标级协助 | 在原讨论中请求一个或多个 Agent 本次协助 | Comment ID + Target Agent ID + 目标解析版本 | 仅限本次请求；原 Issue 负责人不变 |
| SOP Node Attempt | 已委托 SOP 的节点需要一次受管执行 | SOP Execution + Node Activation + Node Attempt + 本次 Run 调用身份 | 限于节点定义、输入和本轮授权 |

上述来源分别保留身份，不合并成一个万能 Intent 对象。它们都通过同一原生 Task 创建 / 查回能力关联 Multica Task。

## 3. 普通指派与 Main Bot 的边界

### 3.1 普通 Agent 指派是完整的一次执行模式

成员把 Issue 指派给 Agent，但没有明确授予持续协调权时：

- 该指派产生一次 Production 执行意图，并沿 Multica 原生 Task / Run 执行。
- Agent 只负责当前工作约定中明确的交付目标和允许动作。
- Agent 可以完成工作、提交 Artifact / 结果、报告缺项或请求成员决定。
- 它不能仅凭 Assignee 身份继续委派 Worker、扩大范围、创建后续独立分工或代表成员作业务决定。
- 执行结束后，结果回到原 Issue，由当前有权成员消费；是否接受、是否继续、是否转成持续协调由成员决定。

这不是“缺少 Main Bot 的半成品模式”，而是完整、低复杂度的普通协作方式。

### 3.2 转为 Main Bot 是新的明确授权转换

同一 Agent 已经被普通指派，之后成员决定让它持续协调：

- 通过有权入口明确授予持续协调范围，产生新的授权代际和 Main Bot 首次激活意图。
- 不把原普通执行 Task 追认成 Main Bot 首次激活；不把普通执行历史改写成持续授权。
- 原 Task 的结果仍归原普通指派；新的 Main Bot Task 是新的受托协调执行。
- 即使目标 Agent ID 相同，授权模式和代际不同也必须是不同业务意图。

撤权后再次委托同一 Agent，同样产生新授权代际和新首次激活意图。

## 4. 稳定身份与绑定要求

### 4.1 身份字段的逻辑要求

每个来源身份至少可唯一确定：

- 来源类别；
- 来源权威对象及其稳定 ID；
- 导致本次执行意图生效的具体转换 / 操作 ID；
- 目标 Agent；
- 适用的工作约定版本与授权代际（适用时）；
- 执行模式 / 用途；
- 必要的输入基准或解析版本。

不得使用 Issue revision、Session ID、时间戳、Agent ID 单独或 (Issue, Agent) 组合冒充稳定身份。

### 4.2 主 Task 与 Retry 谱系

- 同一业务执行意图最多绑定一个主 Task。
- Multica 按原生规则创建的 Retry 子 Task 属于该主 Task 的执行谱系，不是第二个业务意图。
- 同一意图的网络重送查回原主 Task 及其已存在的 Retry 谱系。
- 人工明确要求重新执行是新的业务动作，使用新的重跑身份，并保留 Multica 原生 Rerun 关系。
- Task 来源字段用于导航和审计；稳定来源身份负责唯一查回。不能仅靠 `trigger_evidence_kind/ref_id` 或 `trigger_comment_id` 推断唯一性。

### 4.3 双向可核对

来源侧必须能查回主 Task；Task 侧必须能反查来源身份、目标 Agent、执行用途和输入版本。两侧任一关联缺失时，不得仅凭最近 Task、同 Issue / Agent 或相同 Session 猜测绑定。

## 5. 派发恢复语义

| 来源意图状态 | 含义 | 允许动作 |
|---|---|---|
| Pending | 意图已生效，尚未确认主 Task 绑定 | 当前授权仍有效且能证明主 Task 不存在时创建 / 查回 |
| Bound | 已绑定唯一主 Task | 只沿原 Task 与 Retry 谱系接续 |
| Blocked | 目标不可调用、权限不足、输入冲突等已知阻塞 | 保留原因；条件变化后重新核对 |
| Unknown | 无法证明 Task 是否已创建或绑定 | 先按稳定来源身份查回并对账；禁止直接重新 enqueue |
| Superseded | 来源版本、指派转换或授权代际已被新事实替代 | 停止旧意图的新派发；旧 Task 保留历史归属 |
| Cancelled | 有权主体撤销意图 | 停止新派发；已启动 Task 另按原生取消和副作用规则处置 |

恢复顺序：

1. 读取来源对象、来源意图和当前授权；
2. 已 Bound 则查回原主 Task 与 Retry 谱系；
3. Unknown 则先按稳定来源身份查找原生 Task；
4. 找到唯一兼容主 Task，补齐关联；发现多个独立主 Task 或证据冲突则保持 Unknown；
5. 只有证明主 Task 不存在且意图仍有效，才允许创建；
6. 授权或来源已失效时 Supersede / Cancel，不再派发；
7. Task 已终态但结果未消费时，恢复业务结果消费，不重跑生产。

## 6. Multica 复用与最小扩展边界

### 6.1 直接复用

- Issue、Assignee、Comment、Project Workflow 和权限入口；
- 原生 Task / Run、Task Queue、Runtime Claim / Start / Reclaim；
- 原生 Retry / Rerun 谱系；
- Issue Wakeup 作为协调唤醒信号；
- 原生 Task Usage 与宿主回执。

### 6.2 必须证明或补足

- 来源身份与主 Task 创建 / 查回之间的唯一、可恢复关联；
- Issue 指派转换与对应生产执行意图的持久化关系；
- Comment 每个目标的独立委派状态，以及与既有 coalescing / planned input 的覆盖依据；
- 普通 Agent 指派、Main Bot 激活、Comment 协助和 SOP Attempt 均能使用来源查回能力；
- Task 的执行用途可被查询，至少能区分 Production 与 Governance；E0 先保证 Production 路径不回归，Governance 的隔离在 E3 启用前完成；
- 目标 Agent、授权、输入基准和执行模式在 Task 创建时可核对。

不能为了来源幂等而另建 Task 队列、Run 系统、Coordinator Pool 或常驻恢复 Agent。若 Multica 原生 Task 创建边界无法支持稳定来源查回，应在原生派发边界做最小扩展。

## 7. 生产兼容要求

E0 扩展不得破坏现有 Production 行为：

- 既有 (Issue, Agent) pending 去重继续作为并发保护，但不作为业务意图身份。
- Comment coalescing 只在输入、目标、授权和执行范围兼容且有真实合并回执时复用；不兼容输入不得静默吸收。
- Main Bot 后续回合继续使用 Multica 原生 Wakeup / Task 链；Wakeup 只触发重新读取，不替代来源身份或结果消费。
- Production Session continuity 保持原语义；E0 不提前引入 Governance Session 策略，但用途字段设计不能阻碍 E3 将其隔离。
- Task Usage 仍由 Multica 记录；来源绑定不得复制或重算原生用量。
- Runtime 离线、Claim 超时和 Start 响应丢失沿原生恢复；不创建第二个业务 Task。
- 未上报的 Token / Credits / 费用保持 Unknown，不以估算补数。

## 8. 正式工作约定的投递

Production 执行在启动前必须取得当前有效 Work Agreement 正文、版本及当前授权代际。Issue 标题用于识别，描述和评论可作背景 / 变更建议，不能代替正式工作目标和授权。

评价等 Governance 执行将使用固定评价目标与证据快照，不直接套用生产执行的“当前工作正文”作为评价目标。Governance Task 启动时仍复核当前读权、授权、目标继续资格和预算资格；其固定输入范围按 VS-3 执行。Governance 的用途隔离在 E3 实施，不属于 E0 的生产路径改造。

## 9. E0 最小真实验证矩阵

所有验证使用实际 Multica Task ID、Run / Runtime 回执和目标分支源码，不接受模拟 Task ID 或仅凭 UI 状态判断。

| 场景 | 操作 / 故障点 | 必须得到的结果 |
|---|---|---|
| 普通指派成功 | 成员把 Issue 指派给 Agent，不授予 Main Bot | 一个 Production 主 Task；Agent 只获得一次交付范围 |
| 普通指派入队失败 | Issue 指派已生效，Task enqueue 失败 | 来源意图仍可查；可恢复补派；不误显示已启动 |
| 主 Task 创建响应丢失 | Multica 已创建 Task，调用方未收到响应 | 重送查回同一主 Task，不创建第二个 |
| 并发恢复 | 两个恢复者同时处理同一 Pending / Unknown 意图 | 最多一个主 Task；另一方查回相同 Task |
| 普通转 Main Bot | 同一 Agent 从一次执行转为持续协调 | 新授权代际、新意图、新主 Task；普通执行历史不被追认 |
| 撤权后重新授权 | 同一 Agent 被撤权后再次获派 | 新授权代际；旧意图不能恢复派发或消费新工作 |
| 合法 Retry | 主 Task 失败，Multica 创建 Retry 子 Task | 原主 Task 与 Retry 谱系均可查回；不误判为重复主 Task |
| Comment 多目标 | 一条评论请求多个 Agent，其中一个失败 | 每个目标独立可查、独立恢复；已成功目标不重复派发 |
| 不同输入基准 | 同 Issue / Agent 有不同 HEAD 或不兼容输入 | 不错误复用 pending Task；保留 Blocked / Unknown |
| Runtime 离线 | Task 已 Bound / Queued 时 Runtime 不在线 | 等待原 Task；恢复后继续，不新建业务意图 |
| Claim / Start 响应丢失 | 原生 Claim 或中心 Start 已生效但响应丢失 | 查回并继续同一 Task / claim；宿主启动证据单独确认 |
| 宿主启动失败 | 中心 Start 已确认，Backend 启动失败 | 记录实际失败；不能显示 Running |
| 终态消费响应丢失 | Run 已终态，业务消费写入响应丢失 | 查回原消费，不重复执行生产 |
| 撤权与迟到回执竞争 | 旧 Run 在新授权生效后回报 | 结果归原代际；不能推进当前工作 |

## 10. E0 退出条件

E0 只有在以下条件全部满足后才可进入 E1：

1. 目标 Multica 提交、扩展维护位置和上游同步策略已固定；
2. 普通指派、Main Bot、Comment 目标和 SOP Attempt 的身份映射已明确；
3. 同一来源身份的主 Task 创建 / 查回具备唯一语义，合法 Retry 谱系可查回；
4. 来源侧与 Task 侧可以双向核对；
5. 普通 Production 的 pending、coalescing、Session、Wakeup、Usage 和 Runtime 行为回归通过；
6. 普通 Agent 指派失败恢复、响应丢失、并发恢复和撤权场景通过真实故障注入；
7. 无法证明的场景保持 Unknown，不通过猜测补齐；
8. 未引入第二套 Task / Run / Runtime / Queue / Coordinator；
9. 输出目标分支源码差异、兼容迁移方案和可复现验收记录。

E0 完成只表示来源身份与生产兼容设计可进入实现；不表示 E1 授权 / 受控消费、E2 交付验收或 E3 Governance 隔离已经完成。
