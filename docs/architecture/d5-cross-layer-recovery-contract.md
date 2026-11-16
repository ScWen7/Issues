# D5-3 · 跨层派发、执行绑定与结果消费契约

> 本文收敛 D5-1 / D5-2 的源码证据，定义 AgentPlatform 的跨层业务恢复契约。
> Multica 取证基准：`0f3e15f1d9dca781155e2fe475161f8c5e499b44`；Wakeup 数据库事务捕获另见 [D5-1 固定版本证据](../research/d5-write-recovery-evidence.md)。
> 本文是产品与架构契约，不指定表结构、API、消息中间件或部署拓扑。

## 1. 设计结论

跨层恢复只需要把三件事连起来：

1. **业务意图**：原有权威业务对象说明为什么要执行、谁有权执行、适用哪个版本。
2. **原生执行**：沿 Multica Task / Run / Runtime 执行，保存真实 Task ID 和宿主回执。
3. **业务消费**：由发起该工作的业务层读取结果，确认它仍适用于当前激活，再决定是否推进。

不增加第二套 Task、Run、Runtime、Coordinator Pool 或全局事件总线。也不建立一个独立的通用“操作中心”取代 Issue、Comment、Node Attempt。稳定派发身份和恢复状态附着在各自的业务权威来源及其关联记录上。

**跨层恢复的责任归业务发起层；执行恢复的责任归 Multica；结果消费的责任归原业务接收方。** 不存在一个常驻中央 Agent 替所有业务对象恢复流程。

## 2. 权威对象与恢复责任总表

| 场景 / 阶段 | 业务权威与身份 | 执行权威 | 恢复责任主体 | 恢复后允许做什么 |
|---|---|---|---|---|
| Main Bot 首次激活 | Issue 当前 Assignee、Work Agreement、持续委托授权代际；激活来源是本次有效指派 / 工作流进入 | Multica Task / Run | Issue 派发入口及其可恢复对账机制 | 补齐首次协调 Task，或绑定已证明覆盖本次激活的原 Task |
| Main Bot 后续唤醒 | 原 Issue 当前授权 + Wakeup 订阅 / Receipt；Receipt 是协调信号 | Wakeup 派发产生或复用的 Task / Run | Multica Wakeup Scheduler；Main Bot 在新 Turn 消费 | 重新读取 Issue、在途委派和待消费结果；不能把 Receipt 当成命令正文 |
| 一次性 Worker 委派 | 原 Comment + 目标 Agent + 本次目标解析 / 授权判定 | 该目标对应的 Task / Run | 评论委派解析与恢复入口 | 逐目标补齐未解决委派；已合并、已登记 planned input 的不重复创建 |
| SOP 节点派发 | SOP Execution + Node Activation + Node Attempt + 本次 Run 调用身份 | Multica Task / Run | SOP 执行推进器 | 查回原 Task、恢复启动或等待；不创建第二个节点队列 |
| Task 领取 / Start | 原 Task ID + Runtime + claim generation | Multica Task / Daemon / Backend | Multica 原生 Claim / reclaim / Start | 重新投递同一 Task 或重放同一 claim 的 Start；不创建新业务执行 |
| Run 结果消费 | 原 Task 终态、结果与 Artifact / Candidate 版本 + 目标业务激活 | Run 只提供生产事实 | Main Bot 所属 Issue 协调回合，或 SOP Node Attempt 的执行推进器 | 重放消费、更新业务进度；不重跑已经完成的生产 |
| 业务交付与验收 | Issue 当前 Candidate、Work Agreement、Decision | Issue 权威写入 | Issue 当前负责人 / 有权决定者 | 核验当前候选与决定；不由 Run 或 SOP 自动替代业务验收 |

## 3. 三类业务派发身份

### 3.1 Main Bot 首次激活

身份由以下事实共同确定：
- Issue ID；
- 本次有效指派 / 工作流进入的来源版本；
- 目标 Main Bot Agent ID；
- Work Agreement / Delegation Contract 的适用版本或授权代际。

Issue 当前 Assignee 是持续协调授权的权威来源。首次激活身份只用于确保这次指派所要求的首次协调 Turn 被安排一次，不把每次 Issue 更新都变成新 Turn。

以下变化会产生新的业务意图：重新指派给不同 Agent；撤权后重新授权；有权成员明确要求重新启动协调；工作流进入一个明确要求新执行的 handoff。普通描述字段变化、通知重发、Runtime 恢复和 HTTP 重试不产生新的首次激活。

### 3.2 一次性 Worker 委派

身份由以下事实共同确定：
- 原 Comment ID；
- 目标 Agent ID；
- 触发类型（显式 @、回复路由或明确委派）；
- 目标解析 / 输入基准（例如适用的 review HEAD）；
- 当前授权判定。

一个 Comment 可解析出多个目标，每个目标独立有结果。不能只保存“评论触发成功”这一总状态。已有 Task 可覆盖时，必须记录实际覆盖的 Task 及依据；若 Comment 已合并进 queued Task 或登记为 planned input，不再创建第二个 Task。

评论内容和目标解析来源必须可重读；但历史 Comment 不授予永久执行权。每次恢复都重新核对目标 Agent 当前可调用性、Issue 当前授权、输入版本和已有 Task。

### 3.3 SOP Node Attempt 派发

身份由以下事实共同确定：
- SOP Execution ID；
- Node Activation ID；
- Node Attempt ID；
- 本次 Run 调用身份；
- 固定的流程定义版本、Work Agreement、输入 Candidate / Artifact 和授权代际。

Node Attempt 可以引用多个 Run，例如一次执行、后续技术恢复或独立检查；每次真实 Run 调用仍须有可查回的派发身份。Node Activation ID 本身不足以去重多个不同执行调用。

## 4. 派发与执行的共同阶段

三类业务意图使用相同的阶段语义，但状态记录仍留在各自业务来源中。

| 阶段 | 含义 | 必须具备的证据 | 不能推断什么 |
|---|---|---|---|
| Intent Effective | 业务来源已确认意图有效 | Issue 指派 / Comment 与目标 / Node Attempt Ready 的权威事实 | 不代表派发已安排 |
| Dispatch Pending | 派发责任已产生，等待执行层接收 | 可恢复的派发待办或等价的可扫描来源 | 不代表 Task 已创建 |
| Task Bound | 已创建 Task 或已证明由兼容 Task 覆盖，并保存 Task ID | 业务来源到 Task 的持久关联及覆盖依据 | 不代表 Runtime 已领取 |
| Queued / Dispatched | Multica Task 已排队或已领取 | 原生 Task 状态、claim generation | Dispatched 不代表 Start |
| Running | Runtime 已确认 Start | 原生 Start 回执及当前 claim generation | 不代表业务结果已消费 |
| Awaiting Consumption | Run 已有终态，业务接收方尚未确认消费 | Task 终态、结果引用和目标业务激活 | 不代表节点成功或 Issue 完成 |
| Consumed | 目标业务对象已按当前版本消费结果 | 消费记录 / Node Attempt 结果及版本 | 不代表更高层验收已通过 |
| Blocked / Unknown / Superseded | 已知阻塞、结果无法证明或旧意图已失效 | 原因、最后确认边界、关联版本 | 不得伪装成成功，也不得盲目新建执行 |

这些是跨层观察语义，不要求把它们做成一个跨对象共享的巨大状态机。Issue、Comment 委派关联、SOP Node Attempt 和 Multica Task 分别维护自己拥有的事实。

## 5. Task 绑定与恢复规则

### 5.1 Task 创建必须可关联回业务意图

当原生 Task 创建成功时，必须在可恢复边界保存其业务来源关联。优先复用 Multica 已有来源字段（Issue、trigger comment、delegated-from、Wakeup context 等）；若这些字段不足以唯一定位某次业务意图，应在原生 Task 派发边界补充最小来源身份及查回能力。

不能仅以 Issue ID + Agent ID 认定某个 Task 覆盖本次意图，因为同一 Issue / Agent 可以有不同评论、不同 review HEAD、不同 SOP Attempt 和不同授权代际。

### 5.2 Task 创建与业务绑定必须有明确恢复窗口

Task 创建与业务来源保存关联可能跨越不同写入边界。若响应丢失：
1. 先查业务来源是否已经绑定 Task；
2. 再按稳定来源身份查找 Task；
3. 只有唯一候选且输入、目标 Agent、Issue、授权代际和执行目的均匹配，才补写关联；
4. 有多个候选或证据不足，保留 Unknown 并对账；
5. 只有能证明 Task 未创建，才允许按原业务身份重试创建。

**禁止**“查不到绑定就再 enqueue”。查不到绑定不等于 Task 不存在。

### 5.3 复用既有 Task 的条件

只有同时满足以下条件，才能把既有 Task 记为本次意图的覆盖者：
- 同一业务 Issue / 受托范围；
- 同一目标 Agent（Squad Leader 的实际执行身份按原生规则核对）；
- 输入基准兼容，review HEAD 等强约束一致；
- Work Agreement、执行契约和授权范围兼容；
- 该 Task 仍能接收本次输入（queued merge 或 active planned input 有真实写入回执）；
- 业务来源关联能明确记录本次意图由该 Task 覆盖。

同一 Issue / Agent 的唯一待派槽位只防止某些并发重复任务，不足以证明不同业务意图可以合并。不同 HEAD blocker 不得静默覆盖；保留目标级阻塞义务，等待 blocker 状态变化后重新判断。

## 6. 结果消费契约

### 6.1 Main Bot 消费 Worker 结果

Main Bot 被唤醒后：
1. 读取当前 Issue 指派和授权，确认自己仍有协调权；
2. 按原 Comment / 委派身份列出各 Worker 目标；
3. 逐个查回其 Task、终态、交付版本及既有消费状态；
4. 核对结果是否对应当前 Work Agreement、输入 Candidate 和目标；
5. 记录本次结果已被协调回合消费，或明确缺项 / 阻塞 / 过期；
6. 再决定继续委派、采用结果、请求返工或交回成员。

Wakeup Receipt 可合并多次事实变化，只触发重新读取；不能代替逐项核对委派，也不能证明 Main Bot 已消费结果。

### 6.2 SOP Node Attempt 消费 Run 结果

SOP 执行推进器：
1. 查回 Attempt 关联的所有 Run；
2. 只消费归属当前 Attempt、符合输入和授权代际的终态；
3. 固定 Artifact / Candidate 版本、检查结果、缺项和失败原因；
4. 在 Node Attempt 上保存消费结论；
5. 只有消费结论提交后，才重新计算后继节点 Ready。

消费中断时重复消费必须查回原结果，不重复推进后继。旧 Activation / Attempt 的迟到 Run 只补充原历史，不能推进新激活。

### 6.3 Main Bot 与 SOP 的边界

Main Bot 消费的是 Worker 委派及其交付；SOP Node Attempt 消费的是本节点安排的 Run 结果。若 Main Bot 委托一段 SOP，SOP 先消费自己的节点结果，再按出口契约把结果交回 Main Bot。不能由 Main Bot 直接绕过 SOP 内部节点消费，也不能由 SOP 越权改变 Issue 业务完成状态。

## 7. 授权代际与迟到结果

每次新派发、领取、Start 和业务结果消费，都必须核对对应授权和激活仍然有效。

- Issue 改派或撤权：旧 Main Bot 不再创建新协调 Turn；已启动 Run 可按停止决定处理，迟到结果归原授权代际。
- Worker 委派取消：旧 Comment 仍可审计；尚未启动的派发不得继续，已启动 Run 的处置独立进行。
- SOP 暂停 / 取消 / 新 Activation：旧 Attempt 不再产生新的派发；旧 Run 的终态保留，但不能推进当前激活。
- 输入 Candidate 换版：旧 Run 结果绑定旧 Candidate；接收方判断是否可复用，不自动迁移。
- Runtime 重新绑定：Task 仍按 Multica 的 Runtime / claim generation 规则处理；旧 claim 不得 Start 新 claim。
- 结果迟到：可以补充原 Run / Attempt 历史；当前 Issue 或节点状态只有在当前授权、候选和版本核验通过后才能变化。

对不支持 fencing 的本地目录和外部副作用，仍须按执行平面要求隔离工作副本、确认旧进程或人工核对，不能只依靠状态字段。

## 8. 最小恢复责任矩阵

| 失败 / 中断 | 首要恢复者 | 首先查什么 | 允许动作 | 禁止动作 |
|---|---|---|---|---|
| Issue 已指派，首次 Task 未确认 | Issue 派发恢复入口 | 当前 Assignee、授权代际、首次激活关联、候选 Task | 补齐待派意图或绑定原 Task | 无证据地重复 enqueue |
| Comment 已保存，某 Worker 未确认 | 评论目标委派恢复入口 | Comment、目标 Agent、权限、该目标关联 Task / planned input | 只补未解决目标 | 重发评论、重复派已成功目标 |
| SOP Attempt Ready，Task 未确认 | SOP 执行推进器 | 当前 Activation / Attempt、派发关联、候选 Task | 查回或补派原意图 | 新建第二个 Node Attempt 掩盖不确定性 |
| Task Claim / Start 响应丢失 | Multica Daemon / Task Service | Task ID、Runtime、claim generation、Task 状态 | reclaim 同一 Task、重放同一 Start | 创建新业务 Task |
| Run 终态，结果未消费 | 原业务接收方 | Task 终态、Artifact、候选、Attempt / 委派身份 | 重放消费并记录缺项 | 重跑已完成生产 |
| 业务授权已变化 | 当前 Issue / SOP 权威入口 | 当前负责人、Work Agreement、授权代际 | supersede 旧意图，决定在途执行处置 | 旧 Agent / Run 继续产生新的业务派发 |
| 外部副作用状态未知 | 有权负责人和执行资源所有者 | 宿主进程、工作副本、外部系统和原 Run 证据 | 隔离、核对或人工处理 | 假定未发生并自动重试 |

## 9. 设计边界与禁止新增的重复机制

- 不新增平台自有 Run / Task 队列；实际执行继续使用 Multica 原生 Task / Run。
- 不新增 Coordinator Pool；Issue 当前受托 Agent 在有效授权范围内承担 Main Bot 职责。
- 不把 Wakeup Receipt 改造成永久事件日志或每个 Worker 的委派记录。
- 不为 UI 展示另造一份 Issue / Run 状态权威。
- 不以 Session、模型自述或通知送达作为执行、交付或消费证明。
- 不把通用幂等操作中心变成新的业务权威。操作身份只用于在 Issue、Comment、Node Attempt 与 Task 之间建立可查回关联。
- 不要求跨 Issue、数据库、Runtime 和外部系统全局事务；要求每个边界有可恢复的最后确认事实。

## 10. D5 收敛判定

D5 的产品级设计在以下条件满足时可收敛：
1. 三类业务派发身份已明确且互不混淆；
2. Task 创建、绑定、Claim、Start、终态和消费有分离的确认边界；
3. 每个中断都能确定由哪个既有业务层恢复；
4. Unknown 时先对账，不盲目创建新 Run；
5. 授权变化和迟到回报不会推进新激活；
6. Multica 原生覆盖与 AgentPlatform 待补缺口有证据区分。

仍待技术设计 / 实验验证的内容：
- Multica 原生 Task 是否能按三类来源身份唯一查回；目前只确认部分原生来源字段与待派唯一约束，不宣称通用查回能力已存在。
- Issue 首次指派意图、Comment 目标级委派义务如何持久化及补扫。
- SOP Node Attempt 与多个 Run 的关联、消费记录如何落在原生业务对象上。
- 不同 HEAD blocker 的委派义务如何在 blocker 变化时恢复。
- 取消、撤权、接管与宿主副作用之间的实际 fencing 能力。

上述未决项不阻止产品级恢复契约收敛，但必须在进入工程实现前完成对应技术方案与故障注入验证。
