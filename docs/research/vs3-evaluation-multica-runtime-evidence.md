# VS-3 · Evaluation Run 与 Multica 原生执行链源码取证

> 固定源码基准：multica-ai/multica @ 71683141a764ed3b1620db4bc26a2d0a098f135c。
> 本文只记录该版本能证明的执行、会话、去重、回唤和 Usage 语义，并据此标明 VS-3 必须补齐的底座边界。

## 1. 结论

Multica 已具备 VS-3 所需的执行基础：原生 Task / Run、Runtime Claim / Start / terminal、Task 来源证据、事件、Issue Wakeup 和 Task Usage。

但不能简单地“给评价创建一条普通 Issue Task”就认为完成了独立评价隔离。源码显示至少存在四个会影响正确性的耦合点：

1. 同一 Issue / Agent 的 pending Task 唯一约束会让评价 Task 与生产 Task 竞争同一个排队槽位；
2. 普通 Task 的 Session 恢复会读取该 Agent 在同一 Issue 上最近的终态 Session，治理 Task 若不隔离可能污染后续 Main Bot 上下文；
3. Issue Wakeup 可以按 Task ID 过滤，也可不限定 Task；评价 Task 终态若被普通回唤捕获，可能误唤醒生产协调；
4. Issue Usage 聚合包含 Issue 下的所有 Task；若不区分 Task 用途，评价消耗会混入生产成本视图。

因此 VS-3 的必要底座扩展不是新队列，而是在现有 Task / Run 中明确执行用途，并让去重、Session 恢复、Wakeup 和 Usage 视图尊重该用途。

## 2. Task 来源身份可表达 Evaluation，但不等于完整隔离

Migration 184 为 Task 增加：
- trigger_evidence_kind：自由文本来源类别；
- trigger_evidence_ref_id：对应来源记录 ID；
- 注释明确允许新增 evidence kind 而不要求枚举迁移。

这适合让 Evaluation Task 指向 Evaluation ID，并由 Evaluation 反向保存 Task ID。它只提供来源导航 / 审计关联，不自动改变 pending 唯一约束、Session 恢复和 Wakeup 规则。

源码：[Task attribution migration](https://github.com/multica-ai/multica/blob/71683141a764ed3b1620db4bc26a2d0a098f135c/server/migrations/184_agent_task_attribution.up.sql)。

## 3. Pending 唯一约束与 Coalescing 的边界

Task Service 的 Issue enqueue 通过 CreateAgentTask 创建 Task；注释和 Issue Trigger 代码说明 (issue_id, agent_id) 的 pending 部分唯一索引保护 queued / dispatched 任务。

Comment 路径还会主动把新评论并入同 Issue / Agent 的 pending Task，或登记为 active Task 的 planned comment。该行为是生产协作的重要语义，但 Evaluation 不是评论输入，也不能被并入 Main Bot 正在执行的生产任务。

如果 Evaluation Task 与生产 Task 使用相同 Issue / Agent 且没有用途隔离，就可能发生：
- 被生产 pending Task 的唯一索引拒绝；
- 误合并 / coalesce 到生产任务；
- 评价任务与生产工作共用一个 prompt / 输入计划。

因此需在现有队列模型内区分 Task Purpose / Execution Lane，并对 Evaluation ID 建立自己的唯一来源绑定。普通生产 Task 的既有去重 / coalescing 语义必须保持不变。

源码：[CreateAgentTask / enqueue](https://github.com/multica-ai/multica/blob/71683141a764ed3b1620db4bc26a2d0a098f135c/server/internal/service/task.go) · [Issue trigger](https://github.com/multica-ai/multica/blob/71683141a764ed3b1620db4bc26a2d0a098f135c/server/internal/service/issue_trigger.go) · [Task queue queries](https://github.com/multica-ai/multica/blob/71683141a764ed3b1620db4bc26a2d0a098f135c/server/pkg/db/queries/agent.sql)。

## 4. Session 恢复必须排除治理执行

GetLastTaskSession 按 Agent + Issue 读取最近终态 Task 的 Session，并明确排除 context.type = triage 的 Task。该查询被普通 Issue Task 的恢复路径使用。

如果 Evaluation Task 与生产 Task 共用 Agent / Issue，而其 Session 被写入普通历史，则后续 Main Bot 可能恢复到评价对话，而不是生产协作对话。仅设置 fresh session 不足以表达永久隔离：该 Task 的终态 Session 仍可能进入后续“最近 Session”选择，除非查询明确按用途排除。

VS-3 要求：
- Evaluation Task 使用隔离的上下文和新 Session；
- Evaluation Purpose 必须被普通生产 Session 恢复查询排除；
- 评价结果通过 Evaluation 业务记录回到 Issue，而不是通过共享对话历史传递；
- 评价 Task 的重试仍沿评价 Task 的原生 retry 谱系，但不得进入生产 Main Bot 的 Session 恢复池。

源码：[GetLastTaskSession](https://github.com/multica-ai/multica/blob/71683141a764ed3b1620db4bc26a2d0a098f135c/server/pkg/db/queries/agent.sql)。

## 5. Issue Wakeup 不应误消费 Evaluation 终态

Multica Issue Wakeup 可以匹配事件类型、Agent 和 Task ID；filter_task_id 为空时，事件类型匹配即可捕获同 Issue 的事件。Receipt 由源事务捕获，并非每个事件都自动与特定业务消费者绑定。

Evaluation Task 若使用普通 task.completed / task.failed 并被宽泛 Issue Wakeup 捕获，可能把评价完成误当作 Worker 生产结果到达，唤醒 Main Bot 走生产结果消费路径。

VS-3 要求：
- Evaluation Task 的终态由 Evaluation 消费器按 Evaluation ID 处理；
- 普通生产 Worker Wakeup 默认不捕获 Evaluation Purpose；
- 如需唤醒原 Issue 的负责人，应在 Evaluation 结果成功写入后发出明确的 Evaluation-result 业务通知 / 事件；
- 不将 Evaluation Task 本身伪装成 Worker 委派，也不把它放入普通 Worker 的待消费集合。

源码：[Wakeup service](https://github.com/multica-ai/multica/blob/71683141a764ed3b1620db4bc26a2d0a098f135c/server/internal/service/issue_wakeup.go) · [Wakeup source transaction](https://github.com/multica-ai/multica/blob/71683141a764ed3b1620db4bc26a2d0a098f135c/server/migrations/518_wakeup_event_capture.up.sql) · [Wakeup event join](https://github.com/multica-ai/multica/blob/71683141a764ed3b1620db4bc26a2d0a098f135c/server/internal/service/issue_wakeup_join.go)。

## 6. Task Usage 的覆盖语义与分类

Task Usage 以 (task_id, provider, model) 为唯一维度 upsert。冲突时新的 Token、Provider USD ticks 和 Credits micros 覆盖旧值；它们代表同一 Task / Provider / Model 的当前累计快照或更正，不是需要相加的事件增量。

Issue Usage 查询把该 Issue 下 Task Usage 聚合起来；terminal task coverage 也以 Issue 下终态 Task 为总体。因此：
- 原生 Usage 保持归 Task；
- Evaluation Task 的成本不改写生产 Task 的 Usage；
- AgentPlatform 的生产成本视图必须按 Task Purpose / 来源身份排除 Evaluation / Benchmark / Improvement；
- 团队治理总成本仍应包含这些治理 Task；
- 同一累计快照迟到更正时覆盖，不重复累加；
- 没有 Usage 行只说明没有取得可计量回执，不代表成本为零。

源码：[Task Usage upsert and rollup](https://github.com/multica-ai/multica/blob/71683141a764ed3b1620db4bc26a2d0a098f135c/server/pkg/db/queries/task_usage.sql) · [Task Usage schema](https://github.com/multica-ai/multica/blob/71683141a764ed3b1620db4bc26a2d0a098f135c/server/migrations/032_task_usage.up.sql)。

## 7. VS-3 必须补齐的 Multica 适配点

| 当前机制 | 复用 | VS-3 需要补齐 |
|---|---|---|
| Task / Run / Runtime / Claim / Start / terminal | 完全复用 | Evaluation Task Purpose / 来源身份 |
| trigger_evidence_kind / ref_id | 作为 Evaluation ID 来源引用 | 与 Evaluation 记录双向查回及唯一性 |
| Issue / Agent pending 唯一约束 | 保留生产 Task 既有行为 | Evaluation Task 不与生产 Task 共用 coalescing slot；Evaluation ID 自身幂等 |
| GetLastTaskSession | 保留生产会话恢复 | 普通生产 Session 恢复排除治理 Task |
| Issue Wakeup | 保留生产 Worker 回唤 | 默认排除 Evaluation Task；结果写回后由 Evaluation 业务通知唤醒负责人 |
| Task Usage | 继续作为原生消耗事实 | 平台成本视图按用途区分生产与治理消耗 |
| Task lifecycle events | 保留原生状态事件 | Evaluation 消费器按来源身份消费，不能当普通 Worker 结果 |

这属于现有 Multica Task 执行链的语义扩展，不是建设 Evaluation 专用队列、Daemon 或 Runtime。

## 8. 证据边界

本源码快照证明上述字段、唯一约束、Session 查询、Wakeup 捕获和 Usage upsert 的具体语义。它不证明 Multica 已有 Evaluation Task Purpose、Evaluation 对象、预算预留或 Finding 消费能力；这些是 AgentPlatform / Multica 适配需要设计和验证的内容。

## 9. Execution Purpose 与 Trigger Evidence 的语义必须分离

固定版本的 `CreateAgentTask` 写入 Issue、Agent、Runtime、Context、归因、Trigger Evidence 和 Workflow Step；Task Response 暴露来源、Session、Retry / Rerun、Wakeup、Usage 等信息，但没有标准化 Execution Purpose。Migration 184 对 `trigger_evidence_kind / trigger_evidence_ref_id` 的定义是“直接触发原因及其来源定位”，并明确允许自由文本 Kind；它不是任务用途或隔离类别。

源码：[CreateAgentTask](https://github.com/multica-ai/multica/blob/71683141a764ed3b1620db4bc26a2d0a098f135c/server/pkg/db/queries/agent.sql#L319-L388) · [AgentTaskResponse](https://github.com/multica-ai/multica/blob/71683141a764ed3b1620db4bc26a2d0a098f135c/server/internal/handler/agent.go#L399-L690) · [Attribution / Evidence migration](https://github.com/multica-ai/multica/blob/71683141a764ed3b1620db4bc26a2d0a098f135c/server/migrations/184_agent_task_attribution.up.sql)。

因此 `trigger_evidence_kind='evaluation'` 可以让 Task 指向 Evaluation ID，却不能让其他查询自动排除它。不能把 Purpose 从 Evidence Kind、Prompt、Agent Role、Squad Leader 标记或随意的 Context 字段推导出来。

## 10. Pending 唯一索引的准确范围

固定源码中的唯一约束已经从早期 Issue / Agent 粒度演进到 Issue / Agent / Comment Thread 粒度；但仍没有 Purpose 条件。Migration 257 创建的 pending v2 按 Issue / Agent 唯一；Migration 452 将唯一键扩展到 Comment Thread；两者的部分索引条件都是 queued / dispatched，或特定 channel media deferred，均不按治理用途区分。

源码：[migration 257](https://github.com/multica-ai/multica/blob/71683141a764ed3b1620db4bc26a2d0a098f135c/server/migrations/257_agent_task_queue_channel_media_pending_unique_v2.up.sql) · [migration 452](https://github.com/multica-ai/multica/blob/71683141a764ed3b1620db4bc26a2d0a098f135c/server/migrations/452_agent_task_pending_thread_unique.up.sql)。

**关键修正：** 不能只修改 `HasPendingTaskForIssueAndAgent` 查询。物理唯一索引同样必须允许同一 Issue / Agent / Thread 下，生产 Task 与 Governance Task 各自合法排队；治理 Task 自身则按稳定 Evaluation 来源身份幂等，不能因放开生产槽位而失去去重。

## 11. Comment Coalescing 是独立于 Pending Lookup 的第二道边界

`MergeCommentIntoPendingTask` 会把新评论合并到 queued 的同 Issue / Agent / Thread Task，并重新盖章 Trigger、Originator、Accountable、Evidence、Connected Apps 等信息。该 SQL 只排除 Wakeup Task，没有 Purpose 判断。

源码：[MergeCommentIntoPendingTask](https://github.com/multica-ai/multica/blob/71683141a764ed3b1620db4bc26a2d0a098f135c/server/pkg/db/queries/agent.sql#L1779-L1865)。

因此 G1 生产 / 评价任务并存后，还必须测试成员评论不会被并入 Evaluation 输入；评价快照不能被后来评论改写；普通生产评论仍能按原路径进入生产 Task。只在 pending 检查中区分 Purpose，而漏掉 Merge SQL，仍然不安全。

## 12. Wakeup 不只消费 Task 终态，还捕获 Comment 与 Issue 写入

Migration 520 为 Task 状态变化、Comment 创建 / 更新 / 删除、Issue 字段变化、Label、Reaction、Attachment 等建立事务性 Wakeup 捕获。Migration 579 解决的是 Issue 已交给某 Agent 时避免该 Agent 重复收到同一 Issue 变更；它明确保留其他订阅者，以及 Task、Comment、Reaction 事件。

源码：[migration 520](https://github.com/multica-ai/multica/blob/71683141a764ed3b1620db4bc26a2d0a098f135c/server/migrations/520_collaboration_wakeup_events.up.sql) · [migration 579](https://github.com/multica-ai/multica/blob/71683141a764ed3b1620db4bc26a2d0a098f135c/server/migrations/579_wakeup_skip_handed_to_agent.up.sql)。

因此不能只过滤 `task.completed`。治理 Task 的评论、Issue 更新及其他事务性副作用同样可能形成普通 Wakeup Receipt。治理执行应默认不产生普通生产 Wakeup 输入；治理结果由 Evaluation 消费器成功写入后，再通过明确的结果通知交回原 Issue 负责人。Task Purpose 必须能从来源 Task ID 解析，并在数据库触发捕获处或等价权威边界实施过滤。

## 13. Usage 与执行列表的用途展示

`ListIssueTaskUsage` 和 `GetIssueUsageSummary` 按 Issue 关联的 Task / Usage 汇总，原生账本没有 Purpose 分类。该行为保留团队总资源统计是合理的，但 AgentPlatform 的生产成本视图必须有可信 Purpose 来源，将治理 Task 单列；不能把 Evaluation Task 的费用记成生产交付成本。

源码：[ListIssueTaskUsage / GetIssueUsageSummary](https://github.com/multica-ai/multica/blob/71683141a764ed3b1620db4bc26a2d0a098f135c/server/pkg/db/queries/task_usage.sql#L27-L120)。

同理，任务历史可以保留治理 Task 的可追溯记录，但必须清楚标注用途；不能将它伪装成普通生产 Worker 结果，也不能为隔离而从团队治理总成本中删除。

## 14. 最小 Purpose 隔离契约与测试门禁

不增加第二套队列、Run 或 Runtime。沿用 Multica Task / Run，在现有任务语义中补充可查询、可继承、可传递到 Claim 的 Purpose：Production；Governance 下分 Evaluation、Benchmark、Improvement、Calibration。

| 边界 | 必须满足的契约 |
|---|---|
| 创建 | 既有入口缺省为 Production；仅明确治理入口创建 Governance；未知 Purpose 不得获得治理权限 |
| 来源 | Evaluation ID 是治理 Task 的稳定来源身份；与 Purpose 分开存储 / 查询 |
| 幂等 | 同一 Evaluation ID 只绑定一个主 Task；响应丢失可查回；Retry 子 Task 继承 Purpose 和来源 |
| Pending | 治理 Task 不占用也不被合并进生产 pending / coalescing 槽位；生产既有去重行为保持不变 |
| Session | 治理与生产双向不恢复；不同 Evaluation 之间也不共享 Session |
| Wakeup | 治理 Task 终态、评论和 Issue 副作用默认不进入普通生产 Wakeup |
| Claim | Claim / Runtime 可识别 Purpose；实际 Agent、Runtime、Model 仍是真实执行主体 |
| Usage | Usage 仍归 Multica Task；生产成本视图排除治理 Task，治理成本和团队总成本保留 |
| 历史兼容 | 无 Purpose 的旧 Task 按 Production 解释；混合版本下治理隔离能力缺失时不得启动治理 Task |

进入真实 Evaluation Run 前，必须完成以下控制面回归：

| 编号 | 场景 | 通过条件 |
|---|---|---|
| G1 | 同 Issue / Agent / Thread 已有 queued Production Task，再创建 Evaluation Task | 两者分别存在，不冲突、不共用 pending 槽位 |
| G2 | Evaluation Task queued 时成员发表评论 | 评论不进入 Evaluation 快照，生产评论不丢失 |
| G3 | Evaluation Task queued 时新生产 Task 到达 | 生产任务可按原规则入队 |
| G4 | Evaluation 终态后生产 Task 开始 | 不恢复 Evaluation Session |
| G5 | Evaluation Task 开始 | 不恢复生产 Session 或生产 Transcript |
| G6 | Evaluation Task 自动 Retry | 子 Task 保留 Purpose、Evaluation 来源和原生 Retry 谱系 |
| G7 | Evaluation Task 终态 | 不触发普通生产 Wakeup，不产生评价递归 |
| G8 | Evaluation Task 写入 Comment / Issue / Reaction | 默认受限或拒绝；不向普通 Wakeup 注入治理噪声 |
| G9 | Evaluation Usage 写入 | 原生 Usage 可见；生产 / 治理 / 团队总量口径正确 |
| G10 | Purpose 缺失、未知、旧 Server / Daemon 混合版本 | 旧生产兼容；治理任务 fail closed |
| G11 | 同 Evaluation ID 并发触发 | 只创建一个主 Task；重复请求查回原 Task |
| G12 | Task 创建成功但响应丢失 | 按 Evaluation 来源身份查回原主 Task，不重复创建 |

每个用例记录 Multica commit、Evaluation ID、Target Version、Purpose、主 Task / Retry 谱系、Session ID、Claim / Start / 宿主启动 / 终态、Usage、Wakeup Receipt 和原 Issue 的生产 Task 状态。

## 15. 当前结论与 VS-3 状态修正

| 能力 | 当前状态 |
|---|---|
| Multica 原生 Task / Run / Runtime / Claim / Start / terminal | 可复用 |
| Evaluation ID 作为 Task 来源证据 | 可复用现有 Evidence Kind / Ref 机制，但必须另有 Purpose |
| Governance Purpose 原生字段与 Claim 传递 | 固定源码未提供，待适配 |
| Pending / Unique / Comment Merge 隔离 | 固定源码未提供，待适配 |
| Session 双向隔离 | 固定源码未提供，待适配 |
| Task / Comment / Issue Wakeup 隔离 | 固定源码未提供，待适配 |
| Usage 原生归属 | 可复用；用途分类视图待适配 |
| 真实 Evaluation Task / Run | 尚未执行 |

**当前不应直接在未完成 Purpose 隔离的 Multica 环境创建真实 Evaluation Task。** 先补齐 Purpose 的最小适配和 G1–G12 控制面回归，再进入 VS-3 首个真实 Model-based Evaluation Run。这是复用 Multica 原生执行链、同时保护现有生产协作语义的必要前置。
## 16. 对 Multica 当前 main 的增量复核（2026-11-19）

为避免只沿用架构文档中的历史固定版本，本轮又检查了 Multica 当前默认分支：`main @ 528cd82711f2f99eedd04e4d3a68c6c31b514659`。

检查当前 main 的以下文件，均未发现 `execution_purpose`、`governance_purpose`、`execution_lane`、`ExecutionPurpose` 或 `GovernancePurpose` 标识：

- `server/pkg/db/queries/agent.sql`：仍包含 Task 创建、GetLastTaskSession、pending 检查和 Comment Merge 路径；
- `server/internal/handler/agent.go`：Task Response 仍没有标准化 Purpose 字段；
- `server/migrations/184_agent_task_attribution.up.sql`：仍将 Trigger Evidence 定义为直接触发原因；
- `server/migrations/520_collaboration_wakeup_events.up.sql` 与 `579_wakeup_skip_handed_to_agent.up.sql`：仍按 Wakeup / source Task / handed-to-agent 等现有语义处理事件，没有治理用途过滤；
- `server/pkg/db/queries/task_usage.sql`：Issue Usage 仍按 Issue 下 Task 聚合，没有 Purpose 维度。

当前 main 源码链接：[agent.sql](https://github.com/multica-ai/multica/blob/528cd82711f2f99eedd04e4d3a68c6c31b514659/server/pkg/db/queries/agent.sql) · [agent.go](https://github.com/multica-ai/multica/blob/528cd82711f2f99eedd04e4d3a68c6c31b514659/server/internal/handler/agent.go) · [migration 184](https://github.com/multica-ai/multica/blob/528cd82711f2f99eedd04e4d3a68c6c31b514659/server/migrations/184_agent_task_attribution.up.sql) · [migration 520](https://github.com/multica-ai/multica/blob/528cd82711f2f99eedd04e4d3a68c6c31b514659/server/migrations/520_collaboration_wakeup_events.up.sql) · [migration 579](https://github.com/multica-ai/multica/blob/528cd82711f2f99eedd04e4d3a68c6c31b514659/server/migrations/579_wakeup_skip_handed_to_agent.up.sql) · [task_usage.sql](https://github.com/multica-ai/multica/blob/528cd82711f2f99eedd04e4d3a68c6c31b514659/server/pkg/db/queries/task_usage.sql)。

因此，Purpose 隔离缺口不只是架构文档所 pin 的历史版本问题；在本轮检查的 Multica 当前 main 中仍然存在。该结论仅表示上述源码文件和机制没有对应 Purpose 标识 / 过滤，不代表对所有运行部署版本的现场验证。