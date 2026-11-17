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
