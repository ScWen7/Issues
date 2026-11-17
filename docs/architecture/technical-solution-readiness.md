# AgentPlatform · 技术方案准备与最小纵向切片

> 本文将整体架构、D5 / D6 / D7 / D11 契约转化为技术方案准备边界，明确复用底座、平台扩展、权威写入、恢复责任和最小验证顺序。
> 当前阶段只定义技术承载原则和纵向切片，不确定数据库表、API 路径、服务拆分、消息中间件或部署拓扑。
> Multica 复核基准：\`71683141a764ed3b1620db4bc26a2d0a098f135c\`（2026-11-17 main）；与此前 D5 / D6 取证基准不同，本文对新增机制按此提交固定引用。

## 1. 结论：沿一个协作执行底座，补齐业务语义

AgentPlatform 的技术承载不是重新实现一套协作系统，而是在 Multica 原生 Issue / Project / Comment / Task / Run / Runtime / Usage 上补足业务域能力。

| 能力 | 权威承载 | AgentPlatform 需要补齐的内容 |
|---|---|---|
| 工作与责任 | Multica Issue / Project / Comment / Decision 相关事实 | Work Agreement 版本、Main Bot 授权代际、目标级委派身份和业务决定范围 |
| 受管执行 | Multica Task / Run / Runtime / Daemon | 稳定业务派发身份到原生 Task 的绑定、SOP / Evaluation / Benchmark 归属引用 |
| 本地观察与用量 | Multica Adapter / Daemon / Task Usage | 异构宿主覆盖声明、原生身份映射、unknown 与更正轨迹；不伪造缺失用量 |
| 流程编排 | AgentPlatform SOP Definition / Execution / Node Activation / Attempt | 固定流程版本、节点输入输出、Task 绑定和结果消费；不另建执行队列 |
| 交付与验收 | AgentPlatform Artifact / Candidate / Evidence / Delivery Record / Acceptance Decision | 不可变送审组合、标准版本、验收权限、并发竞争和附件长期可取性 |
| 评价与改进 | AgentPlatform Evaluation / Finding / Improvement Proposal / Benchmark / Release | D11 评价策略、资源预算、独立评价执行、候选验证与治理权限 |
| 项目采用 | Multica Project 配置与 AgentPlatform Project Adoption 决定 | 记录采用范围、生效条件、在途工作和后续实际使用版本 |
| 工作台 | 读取各权威来源 | 查询聚合、动作路由、状态解释；不复制业务状态机 |

**Multica 是唯一协作执行控制面；AgentPlatform 负责业务契约与缺失的治理语义。** 不建设第二套 Issue、Run、Runtime、Daemon、Coordinator Pool 或通用任务队列。

## 2. 最小纵向切片的范围

### 2.1 首个切片要证明什么

选一个普通研发 Issue，完整走通：
1. 成员创建 / 选择 Issue，确认目标、范围、完成条件和人工总责人；
2. 成员将 Issue 指派给现有 Agent，并明确持续协调授权，形成 Main Bot；
3. Main Bot 在授权内决定由自己处理或一次性委派一个 Worker；
4. Worker 在成员本地 Runtime 实际启动并执行，结果能回到原 Issue；
5. Worker 交回一个可定位 Artifact；有权整合者明确组成固定 Candidate；
6. 必需确定性检查产生 Evidence；指定成员对当前 Candidate 作 Acceptance Decision；
7. 对该生产 Run 或 Candidate 按 D11 策略触发一次独立 Evaluation（首个切片可使用确定性 / Trace Scorer；模型评分作为后续扩展）；
8. Evaluation 的 Finding 回到原 Issue；只有经维护者分诊才建立 Improvement Proposal；
9. 提案候选通过固定样本 Benchmark，资产维护者发布 Release；
10. 项目有权成员作 Project Adoption，后续工作能记录实际选择 / 投递 / 使用的版本。

该切片不要求一开始实现所有宿主、所有 SOP 节点类型、所有 Evidence 类型或自动化模型评价。它要求每个阶段的真实权威身份、状态和交接已经可查，不能用模拟成功回执冒充。

### 2.2 首个切片明确不做什么

- 不实现第二套 Issue / Task / Run / Runtime；
- 不让 Main Bot 成为平台常驻服务或唯一协调节点；
- 不要求每个 Issue 都调用 SOP、Evaluation 或 Benchmark；
- 不对所有生产 Run 做全量模型评分；
- 不让 Evaluation 自动修改团队默认 Skill / SOP；
- 不自动把 Release 推送给所有项目或在途工作；
- 不实现统一 USD 成本换算，不为 Qoder / CodeBuddy 缺失字段估算 Credits；
- 不以完整报表或工作台 UI 代替真实端到端执行证据。

## 3. 技术边界：谁写什么、谁只引用

| 权威事实 | 唯一写入责任 | 其他模块如何使用 |
|---|---|---|
| Issue 当前状态、Assignee、Project 关系、评论 | Multica Issue / Comment 写入入口 | 平台通过授权命令更新；订阅事件后重新读取权威对象 |
| 持续协调授权与 Work Agreement | AgentPlatform Issue 工作约定域，关联 Multica Issue 和版本 | Main Bot 每次派发 / 消费前核对当前版本 |
| Main Bot 首次激活 / Worker 委派意图 | AgentPlatform 对应业务来源记录 | 绑定一个真实 Multica Task；Wakeup 只唤醒，不替代意图 |
| Task / Run / Claim / Start / Runtime | Multica 原生执行入口 | SOP / Evaluation / Benchmark 保存 Task / Run 引用，不复制执行状态 |
| SOP Definition / Execution / Node Activation / Attempt | AgentPlatform 流程域 | Node Attempt 绑定实际 Task / Run，消费原结果 |
| Artifact / Candidate / Evidence / Acceptance Decision | AgentPlatform 交付域；Issue 的业务完成仍经统一权威入口 | 不可变 Locator / Digest、Candidate Manifest / Generation、Evidence Applicability、追加式 Decision 与统一 Completion Gate |
| Evaluation Policy / Evaluation / Finding | Team / Project 配置及 AgentPlatform 评价域 | 评价执行通过 Multica Task / Run，结果回原目标 |
| Improvement Proposal / Benchmark | AgentPlatform 改进治理域 | Benchmark 执行沿 Multica Run；提案不改变生产默认资产 |
| Release | 对应资产维护者的发布入口 | 项目可选用，不自动生效 |
| Project Adoption | Project 有权成员的项目配置决定 | 后续工作记录实际选用和投递版本 |
| Usage | Multica Task Usage 及真实宿主来源 | 汇总按 Task 去重、按原生单位分开；缺失保持 unknown |

一个模块可以在同一中心应用内实现多个领域，但不能因共用代码或数据库而混淆事实归属。

## 4. 最关键的技术承载契约

### 4.1 业务派发身份必须能查回原生 Task

三类来源身份保持不同：
- Main Bot 首次激活：Issue 指派 / 授权转换身份 + 授权代际；
- 一次性 Worker 委派：Comment ID + Target Agent ID + 目标解析版本；
- SOP 节点执行：Node Attempt ID + 本次 Run 调用身份。

派发成功后必须绑定真实 Task ID。Task 创建后绑定回执丢失时，先按稳定来源身份查回；能证明唯一兼容 Task 才补绑定。存在多个候选或无法查回时保持 Unknown 并对账，不新建第二个 Task 掩盖不确定性。

Multica 当前可复用：
- \`trigger_evidence_kind / trigger_evidence_ref_id\`：来源导航 / 审计引用；
- \`trigger_comment_id / coalesced_comment_ids\`：评论触发输入；
- \`delegated_from_task_id\`、\`retry_of_task_id\`、\`rerun_of_task_id\`：归因和执行谱系；
- (Issue, Agent) pending Task 唯一约束：特定排队 / 派发重复保护；
- Claim Generation、过期 Claim reclaim、Start 回执及原生 Retry / Rerun。

这些字段和约束不能单独表达所有业务身份：来源证据字段不是通用幂等键，pending 唯一约束也不证明两个业务意图相同。严格幂等仍需在原生派发边界补足稳定来源身份查回能力，或由来源权威记录提供等价的对账关系。

### 4.2 首次指派和后续唤醒必须分开

Issue 指派写入与 Agent Task 入队在 Multica 当前路径上分离；Issue Handler 在派发调用处忽略入队错误。Issue 事务中的 Wakeup 捕获只覆盖当时已存在且匹配的 Wakeup 订阅。

因此：
- 指派 / 授权生效必须有可恢复的首次激活意图；
- Task 创建后保存实际 Task ID；
- 入队失败、Runtime 不可用、授权失效分别记录，不把 Issue 指派成功伪装成 Run 已启动；
- 后续 Issue / Comment / Worker 事实变化由 Wakeup 唤醒 Main Bot 重读；
- Wakeup Receipt 可合并，不是逐条命令或委派记录。

### 4.3 Comment 保存与多目标 Worker 委派分开确认

评论是委派来源，不等于每个目标都已接单。目标解析后逐 Agent 记录待处理、已绑定 Task、被兼容 Task 覆盖、planned input、blocked、superseded 或结果待消费。

Multica 已有同 Issue / Agent queued Task 归并、同 HEAD 评论合并、planned comment 和完成后 reconcile；不同 HEAD blocker 仍需平台可恢复的目标级待办。重放评论触发时只补尚未解决的目标，不重复创建评论或已覆盖 Task。

### 4.4 SOP Attempt 到 Run 是关系，不复制 Run

Node Attempt 可关联多个 Run；每次真实派发有自己的稳定调用身份。Task 进入 queued、Claimed、Started 和终态分别由 Multica 确认。Run 完成后，SOP 重新读取原 Task / Artifact，核对当前 Activation、输入 Candidate 和授权，写入结果消费记录后才计算后继 Ready。

### 4.5 Candidate 与 Acceptance 的权威写入

Candidate manifest 固定 Artifact 版本、来源、摘要、工作约定和检查标准版本。Candidate 换版、Acceptance Decision 和 Issue Done 必须在统一的 Issue 业务写入边界竞争。

不能只依赖 Multica Issue revision：
- revision 是并发版本，不是 Candidate 身份；
- 无关评论也可能推进 revision；
- 验收命令必须明确携带 Candidate ID 和标准版本；
- 服务端在提交时重新核对当前 Candidate、manifest、标准、Evidence、权限和完成条件；
- PR merge 是工程事实，不能绕过具名验收门槛。

### 4.6 Evaluation 与预算预留

Evaluation 是业务评价记录，Evaluation Run 是实际执行。Evaluation 记录至少固定：
- 被评 Issue / Run / Candidate / SOP 及其版本；
- 触发类型和原因；
- Team / Project Evaluation Policy、Work Agreement、Scorer / Rubric 版本；
- 输入 Evidence 快照、覆盖与缺项；
- 预算预留、实际 Run、原生 Usage 和结论。

启动评价前按单次、Issue、Project 周期和 Team 周期核对预算资格。预算预留、Evaluation Requested 身份和派发绑定必须防止重复触发；Run 终态后按真实 Usage 结算并释放未消耗预留。不同 Credits / Token / USD 单位分别核算；缺失用量不阻止记录已知 Run 数 / 时长，但不能宣称真实费用已知。

强制门禁预算耗尽时等待、转人工或使用预先批准的等价检查；不得静默跳过。抽样预算耗尽时停止新增抽样，不影响已经完成的生产工作。Evaluation Failed、Insufficient Evidence 和 Not Passed 必须分开。

### 4.7 Finding、Proposal、Benchmark、Release、Adoption 各自推进

- Evaluation 产生 Finding，不自动生成 Proposal。
- 维护者分诊后才建立 Improvement Proposal。
- Proposal 固定基线、改进候选修订、范围、样本、Rubric 和成功标准。
- Benchmark 结果只支持审核，不自动发布。
- 资产维护者发布不可变 Release。
- Project 有权成员另行决定 Project Adoption。
- 后续 Work / Run 记录实际选择、投递和宿主使用；采用不等于已使用。
- 生产效果观察不足时保持 Pending Observation；发生退化可暂停默认采用或回退，不覆盖历史记录。

## 5. 最小纵向切片的阶段顺序

| 切片 | 交付能力 | 真实验收条件 | 失败时保留什么 |
|---|---|---|---|
| VS-0 · 身份与关联 | Issue、授权代际、Comment 目标、Node Attempt、Evaluation 目标都有稳定来源身份 | 任一来源能查到授权版本、对象版本和目标 Agent | 来源记录、Unknown 原因 |
| VS-1 · 委派与执行 | Main Bot 首次激活、一次 Worker 委派、原生 Task / Run | 真实 Runtime Start、Task ID 绑定、断联恢复不重复创建 | 委派身份、Task 谱系、回执 |
| VS-2 · 交付与验收 | Artifact、Candidate manifest / Generation、Evidence Applicability、Acceptance Decision、Completion Gate | 固定版本可回读；Candidate 替代、验收、权限撤销、PR 集合变化和 Issue Done 竞争只有一个符合条件的结果 | 旧 Candidate、旧 Evidence、旧 Decision、来源失效记录 |
| VS-3 · 评价与预算 | 固定目标快照的 Evaluation、全范围预算预留、独立治理用途 Task / Run、Finding 消费 | 真实 Runtime 执行；Evaluation 与 Task 双向查回；不污染生产 coalescing / Session / Wakeup；预算、Usage 和 Finding 幂等 | Evaluation 输入、预算预留 / 结算、Task / Run / Usage 与 Finding 归属 |
| VS-4 · 改进发布与采用 | Proposal Candidate Revision、固定样本 / 双臂 Benchmark、不可变 Release、Project Adoption、Actual Usage 与生产 Observation | 可比配对与硬门槛有效；有权审核；后续生产工作证明实际选择 / 投递 / 使用；退化可回退且保留历史 | 候选修订、实验 / Trial、Release、Adoption、Usage 与生产效果证据 |

先完成 VS-0 到 VS-2，证明平台真实工作链；再接 VS-3；最后接 VS-4。VS-4 不是首个工作交付的阻断前置，但它是完整持续改进闭环的最终验证。

## 6. 故障注入与验收场景

至少验证：
1. Issue 指派已提交、Task 尚未创建时服务退出；
2. Task 已创建、业务绑定回执丢失；
3. Main Bot Runtime 离线，其他成员 Worker 继续执行；
4. Comment 已保存，目标解析或部分目标 enqueue 中断；
5. 同 HEAD queued Task 合并、不同 HEAD blocker、planned comment；
6. Claim / Start 响应丢失与过期 Claim reclaim；
7. Run 终态回执迟到，结果消费响应丢失；
8. Candidate 换版与 Acceptance 同时提交；
9. PR 全部合并但具名验收缺失；
10. Evaluation 重复触发、预算预留并发、Runtime 无 Credits 上报；
11. Evaluation Run 失败、证据不足、质量不通过、预算耗尽；
12. Benchmark 样本或 Rubric 变化后拒绝不可比结论；
13. Release 成功但 Adoption 未完成；
14. Adoption 已完成但某次 Runtime 未收到 / 未加载版本；
15. 发布后质量退化，项目默认回退而在途工作保留原版本。

每个场景都要记录：初始权威事实、并发动作、故障点、预期唯一结果、实际 Multica Task / Run、恢复动作、最终业务消费状态。只检查 UI 最终显示不足以证明正确。

## 7. 当前 Multica 复用依据与明确缺口

当前源码复核基准为 \`71683141a764ed3b1620db4bc26a2d0a098f135c\`：
- Issue 指派后调用 \`dispatchIssueRun\`；Agent enqueue 返回错误被忽略，派发与 Issue 写入不是一个事务。
- \`CreateAgentTask\` 使用 (Issue, Agent) pending 唯一约束，并通过任务队列持久化和 Runtime Claim / Start 机制执行；它没有证明通用外部业务幂等键可按来源查回。
- Task 有 trigger evidence、comment source、delegation、retry / rerun 归因字段，可作来源导航和谱系，不等于平台业务对象。
- Wakeup Receipt 在源事务内捕获匹配事件；Receipt 会消费 / 清理，不是永久事件历史。
- Task Usage 按 (Task, Provider, Model) upsert，支持 Token、Provider 原生 USD ticks 和 Credits micros；它是 Task 级计量事实，不证明每个 Runtime 都有完整上报。Runtime rate-limit snapshot 是额度窗口观察，不是执行消耗。
- PR auto-complete 在写 Issue 状态时再次检查关联 PR 是否全部 merged 和 Issue 原状态；不检查 Candidate / Acceptance Decision。

关键源码：
- [Issue 指派与触发](https://github.com/multica-ai/multica/blob/71683141a764ed3b1620db4bc26a2d0a098f135c/server/internal/handler/issue.go)
- [Issue 派发入口](https://github.com/multica-ai/multica/blob/71683141a764ed3b1620db4bc26a2d0a098f135c/server/internal/handler/issue_trigger.go)
- [Task 创建与来源证据](https://github.com/multica-ai/multica/blob/71683141a764ed3b1620db4bc26a2d0a098f135c/server/internal/service/task.go)
- [Task 队列与 Claim / Reclaim](https://github.com/multica-ai/multica/blob/71683141a764ed3b1620db4bc26a2d0a098f135c/server/pkg/db/queries/agent.sql)
- [Task Usage](https://github.com/multica-ai/multica/blob/71683141a764ed3b1620db4bc26a2d0a098f135c/server/pkg/db/queries/task_usage.sql)
- [PR 自动完成](https://github.com/multica-ai/multica/blob/71683141a764ed3b1620db4bc26a2d0a098f135c/server/internal/handler/pr_auto_complete.go)
- [Task 来源字段迁移](https://github.com/multica-ai/multica/blob/71683141a764ed3b1620db4bc26a2d0a098f135c/server/migrations/184_agent_task_attribution.up.sql)
- [Wakeup 事务捕获](https://github.com/multica-ai/multica/blob/71683141a764ed3b1620db4bc26a2d0a098f135c/server/migrations/518_wakeup_event_capture.up.sql)

## 8. 当前阶段结论与下一步

当前已经具备进入详细技术设计的统一边界，但还不能据此宣称已完成可直接开发的数据库 / API 方案。

VS-0 / VS-1 的逻辑接口、事务边界、故障恢复和验收条件见[业务意图身份、Task 绑定与执行恢复契约](vs0-vs1-dispatch-binding-contract.md)。VS-2 的 Artifact、Candidate、Evidence、Acceptance 与 Completion Gate 技术契约见[VS-2 技术承载契约](vs2-candidate-acceptance-technical-contract.md)，其 Multica 当前附件 / PR 路径证据见[VS-2 源码取证](../research/vs2-multica-delivery-source-evidence.md)。VS-3 的 Evaluation 身份、独立 Task / Run、治理用途隔离、预算预留 / 结算和 Finding 消费契约见[VS-3 技术承载契约](vs3-evaluation-technical-contract.md)，Multica pending 去重、Session 恢复、Wakeup 和 Usage 的适配缺口见[VS-3 源码取证](../research/vs3-evaluation-multica-runtime-evidence.md)。VS-4 的 Benchmark、Release、Project Adoption、Actual Usage 和生产效果回收契约见[VS-4 技术承载契约](vs4-benchmark-release-adoption-technical-contract.md)，上游实验比较机制见[TeamAI Benchmark 源码取证](../research/vs4-teamai-benchmark-source-evidence.md)。D5 / D6 / D7 / D11 纵向契约现已齐备；下一步进入整体技术方案一致性审查和最小实现切片选择，不再扩展新的架构专题。

不应并行让多个 Agent 各自设计 D5、D6、D7 的数据库表；先确定共用的身份、版本、授权和恢复基础，再按业务域细化持久化和接口。
