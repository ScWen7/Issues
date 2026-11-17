# AgentPlatform · 技术方案准备与最小纵向切片

> 本文将整体架构、D5 / D6 / D7 / D11 契约转化为技术方案准备边界，明确复用底座、平台扩展、权威写入、恢复责任和最小验证顺序。
> 当前阶段只定义技术承载原则和纵向切片，不确定数据库表、API 路径、服务拆分、消息中间件或部署拓扑。
> Multica 复核基准：`71683141a764ed3b1620db4bc26a2d0a098f135c`（2026-11-17 main）；与此前 D5 / D6 取证基准不同，本文对新增机制按此提交固定引用。

## 1. 结论：沿一个协作执行底座，补齐业务语义

AgentPlatform 的技术承载不是重新实现一套协作系统，而是在 Multica 原生 Issue / Project / Comment / Task / Run / Runtime / Usage 上补足业务域能力。

| 能力 | 权威承载 | AgentPlatform 需要补齐的内容 |
|---|---|---|
| 工作与责任 | Multica Issue / Project / Comment / Decision 相关事实 | Work Agreement 版本、Main Bot 授权代际、目标级委派身份和业务决定范围 |
| 受管执行 | Multica Task / Run / Runtime / Daemon | 稳定业务派发身份到原生 Task 的绑定、SOP / Evaluation / Benchmark 归属引用 |
| 本地观察与用量 | Multica Adapter / Daemon / Task Usage | 异构宿主覆盖声明、原生身份映射、unknown 与更正轨迹；不伪造缺失用量 |
| 流程编排 | AgentPlatform SOP Definition / Execution / Node Activation / Attempt | 固定流程版本、节点输入输出、Task 绑定和结果消费；不另建执行队列 |
| 交付与验收 | AgentPlatform Artifact / Candidate / Evidence / Delivery Record / Acceptance Decision | 不可变送审组合、标准版本、验收权限、并发竞争和附件长期可取性 |
| 评价与改进 | AgentPlatform Evaluation / Finding / Improvement Proposal / Benchmark | D11 评价策略、资源预算、独立评价执行与候选验证 |
| 方法与能力发布 | 对应资产域的 Release | 由资产维护者审核发布不可变版本，供项目或工作选用 |
| 项目采用 | Multica Project 配置与 AgentPlatform Project Adoption 决定 | 记录采用范围、生效条件、在途工作和后续实际使用版本 |
| 工作台 | 读取各权威来源 | 查询聚合、动作路由、状态解释；不复制业务状态机 |

**Multica 是唯一协作执行控制面；AgentPlatform 负责业务契约与缺失的治理语义。** 不建设第二套 Issue、Run、Runtime、Daemon、Coordinator Pool 或通用任务队列。

## 2. 最小纵向切片的范围

### 2.1 首个切片要证明什么

首条工作链对应 E0–E2，选一个普通研发 Issue 验证：
1. 成员确认目标、范围、完成条件、人工总责和验收人，形成 Work Agreement；
2. 有权成员将 Issue 指派给现有 Agent，并明确持续协调授权；
3. Main Bot 在授权内委派一个 Worker，原委派及目标可以查回；
4. Worker 在本地 Runtime 实际启动，交付沿原 Task / Run 回到 Issue；
5. Main Bot 通过受控入口消费结果；有权整合者选择 Artifact，组成固定 Candidate；
6. 确定性检查产生 Evidence，指定成员对当前候选接受或退回；
7. 有效决定和其余完成条件满足后，经统一入口完成 Issue。

首批使用一个默认验收通道和 Accept / Reject。详细启用范围、工程前置和故障验收以[VS-5 的工程顺序](vs5-overall-technical-consistency-review.md#9-实施依赖与最小工程切片)为准。

Evaluation / Finding 在 E3 接入；Proposal、Benchmark、Release、Project Adoption 与生产效果观察在 E4 接入。SOP 运行时另按项目需要安排后续切片。

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
| Artifact / Candidate / Evidence / Acceptance Decision | AgentPlatform 交付域；Issue 的业务完成仍经统一权威入口 | 不可变 Locator / Digest、Candidate Manifest / Generation、Evidence Applicability、追加式 Decision 与统一 Completion Gate；Delivery Record 聚合这些事实及原 Issue 交付注记 |
| Evaluation Policy / Evaluation / Finding | Team / Project 配置及 AgentPlatform 评价域 | 评价执行通过 Multica Task / Run，结果回原目标 |
| Improvement Proposal / Benchmark | AgentPlatform 改进治理域 | Benchmark 执行沿 Multica Run；提案不改变生产默认资产 |
| Release | 对应资产维护者的发布入口 | 项目可选用，不自动生效 |
| Project Adoption | Project 有权成员的项目配置决定 | 后续工作记录实际选用和投递版本 |
| Usage | Multica Task Usage 及真实宿主来源 | 汇总按 Task 去重、按原生单位分开；缺失保持 unknown |

一个模块可以在同一中心应用内实现多个领域，但不能因共用代码或数据库而混淆事实归属。

## 4. 最关键的技术承载契约

各行为在对应正文维护，工程准备按下列入口核对：

| 要落实的行为 | 权威契约 |
|---|---|
| 工作约定、正式责任引用与持续委托如何生效、修订和撤销 | [Work Agreement 与授权](cross-layer-contracts.md#3-work-contract定义工作和决定权) |
| Issue 首次激活、评论目标如何绑定主 Task，怎样查回 Retry 谱系 | [派发身份与绑定](vs0-vs1-dispatch-binding-contract.md) |
| 中心 Start、宿主启动及 Main Bot 结果消费如何确认 | [D5 执行与消费](d5-cross-layer-recovery-contract.md) |
| Candidate 怎样固定业务内容，解释性补充写在哪里，验收怎样与 Done 竞争 | [交付验收技术契约](vs2-candidate-acceptance-technical-contract.md) |
| Evaluation 怎样固定 Policy、核对开工资格并结算预算 | [D11 策略](d11-evaluation-trigger-budget-policy.md) · [VS3 评价技术契约](vs3-evaluation-technical-contract.md) |
| 改进怎样对照验证、发布或实施配置，再由项目采用 | [D7 改进规则](d7-continuous-improvement-loop.md) · [VS4 发布采用契约](vs4-benchmark-release-adoption-technical-contract.md) |
| 共用权威边界和实际工程顺序如何安排 | [VS5 横向契约与工程切片](vs5-overall-technical-consistency-review.md) |

## 5. 最小纵向切片的阶段顺序

| 切片 | 交付能力 | 真实验收条件 | 失败时保留什么 |
|---|---|---|---|
| VS-0 · 身份与关联 | Issue、授权代际、Comment 目标、Node Attempt、Evaluation 目标都有稳定来源身份 | 任一来源能查到授权版本、对象版本和目标 Agent | 来源记录、Unknown 原因 |
| VS-1 · 委派与执行 | Main Bot 首次激活、一次 Worker 委派、原生 Task / Run | 中心 Start 与宿主启动分别取证、主 Task 绑定、Retry 谱系与结果消费可查回 | 委派身份、Task 谱系、回执 |
| VS-2 · 交付与验收 | Artifact、Candidate manifest / Generation、Evidence Applicability、Acceptance Decision、Completion Gate | 固定版本可回读；Candidate 替代、验收、权限撤销、PR 集合变化和 Issue Done 竞争只有一个符合条件的结果 | 旧 Candidate、旧 Evidence、旧 Decision、来源失效记录 |
| VS-3 · 评价与预算 | 固定目标快照的 Evaluation、全范围预算预留、独立治理用途 Task / Run、Finding 消费 | 真实 Runtime 执行；Evaluation 与 Task 双向查回；不污染生产 coalescing / Session / Wakeup；预算、Usage 和 Finding 幂等 | Evaluation 输入、预算预留 / 结算、Task / Run / Usage 与 Finding 归属 |
| VS-4 · 改进发布与采用 | Proposal Candidate Revision、固定样本 / 双臂 Benchmark、不可变 Release、Project Adoption、Actual Usage 与生产 Observation | 可比配对与硬门槛有效；有权审核；后续生产工作证明实际选择 / 投递 / 使用；退化可回退且保留历史 | 候选修订、实验 / Trial、Release、Adoption、Usage 与生产效果证据 |

VS 表达技术契约的覆盖范围，E 表达实际工程步骤。先完成 E0–E2 验证生产工作链；E3 启用治理执行前完成用途隔离，再接评价与预算；E4 验证改进发布采用。SOP、首批预算及验收范围统一见[VS5 工程顺序](vs5-overall-technical-consistency-review.md#9-实施依赖与最小工程切片)。

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

当前源码复核基准为 `71683141a764ed3b1620db4bc26a2d0a098f135c`：
- Issue 指派后调用 `dispatchIssueRun`；Agent enqueue 返回错误被忽略，派发与 Issue 写入不是一个事务。
- `CreateAgentTask` 使用 (Issue, Agent) pending 唯一约束，并通过任务队列持久化和 Runtime Claim / Start 机制执行；它没有证明通用外部业务幂等键可按来源查回。
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

当前进入 **E0 · 来源查回与生产兼容设计**，设计正文见 [E0 来源身份与生产兼容设计](e0-source-identity-production-compatibility.md)。E0 已补齐普通 Issue Agent 一次性指派这一 Production 来源：它与 Main Bot 首次激活使用不同业务身份和授权边界，但共用 Multica 原生 Task / Run 创建、查回和 Retry 谱系。

E0 仍需在实际目标 Multica 分支完成源码差异核验、扩展维护方式、历史 Task 兼容、主 Task / Retry 查回和生产回归设计。未完成这些前置及故障注入标准前，不进入工程修改。之后再按 E1 授权 / 消费、E2 交付验收、E3 治理隔离与评价、E4 改进采用推进。

数据库、API 和部署方案按各切片的权威写入与恢复要求细化，不提前展开。
