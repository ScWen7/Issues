# Main Bot 生命周期与 Issue 持续推进模型

> 本阶段研究问题：Member 将 Issue 的执行协调委托给 Main Bot 后，Main Bot 如何接手、组织工作、等待、恢复、重新规划并交付？  
> 研究范围：产品工作生命周期与现有 Multica 机制映射。本文不定义数据库表、API、独立 Planner 服务或第二套任务状态机。

## 1. 核心结论

Main Bot 不需要一套独立于 Issue、Run 的完整业务生命周期。它是 Issue 上被授权的持续协调职责，由多个短生命周期 Coordinator Turn 完成。

- **Issue 生命周期**：这项业务工作是否待安排、推进、等待、审查、完成或取消。
- **Main Bot 委托关系**：当前是否有一个 Main Bot 获准持续协调该 Issue，授权范围是什么。
- **Coordinator Turn**：Main Bot 每次被唤醒后读取最新事实、决策、采取动作并结束本轮。
- **Worker Run**：实际 Agent 在某个 Runtime 上执行的记录。
- **交付与决定**：Worker 结果回到 Issue，Main Bot 汇总，Issue Owner 作保留的业务决定和验收。

**持续的是 Issue 上的协调工作，不是 Main Bot 进程、Session 或某个 Runtime。**

## 2. 整体生命周期

~~~mermaid
flowchart TD
  A["Member 创建 / 接手 Issue"]
  B["明确 Owner、目标、范围、验收和授权"]
  C{"是否委托 Main Bot 持续协调？"}
  D["Owner 自主推进 / 一次性请求 Agent 协助"]
  E["Main Bot 接手 Issue"]
  F["Main Bot Turn：读取最新事实"]
  G["理解工作与授权，形成当前工作安排"]
  H{"下一步"}
  I["Main Bot 直接执行"]
  J["派发一个或多个 Worker Agent"]
  K["调用局部 / 完整 SOP"]
  L["等待 Worker、资源或 Owner 决定"]
  M["消费结果、检查交付与证据"]
  N{"是否需要继续推进？"}
  O["重新规划 / 返工 / 补充委派"]
  P["向 Owner 汇总交付与待决定事项"]
  Q["Owner 接受 / 退回 / 改变范围 / 接管"]
  R["Issue 按原完成条件推进或结束"]
  A --> B --> C
  C -->|否| D --> M
  C -->|是| E --> F --> G --> H
  H --> I --> M
  H --> J --> L --> F
  H --> K --> L
  H --> L
  L -->|有新事件 / 结果| F
  M --> N
  N -->|是| O --> F
  N -->|否| P --> Q --> R
~~~

这不是一个要求每个 Issue 走完全部步骤的固定工作流。Main Bot 可在任意一轮选择直接执行、委派、调用 SOP、等待或交付。

## 3. 生命周期中的责任边界

| 参与者 | 生命周期职责 | 不应替代谁 |
|---|---|---|
| Member / Issue Owner | 定义目标、保留业务责任、授予或撤销协调权、处理业务决定、验收交付 | 不需要亲自拆分每个 Agent 子任务 |
| Main Bot | 接手受托协调，规划、选择方法、委派、消费结果、处理异常、汇总交付 | 不替 Owner 作超授权业务决定 |
| Worker Agent | 在明确委托范围内执行、验证、报告和交付 | 不自行改变 Issue 目标或 Main Bot 的整体工作安排 |
| Multica | 保存 Issue、执行派发、Run、Runtime 领取、回执、权限和可追溯活动 | 不替 Main Bot 做工作规划 |
| SOP | 在明确委托范围内推进稳定步骤、依赖、核验、返工和出口 | 不接管 Issue 的整体协调权 |

Main Bot 的协调权必须来自 Owner 对具体 Issue 的有效委托。Agent 身份、评论中被提及或拥有 Runtime 本身，都不自动产生持续协调权。

## 4. Main Bot 的工作周期：短 Turn，持续推进

Main Bot 每次唤醒执行一个有界 Turn：

1. **触发与领取**：因 Issue 被委托、Worker 结果、Owner 决定或需要处理的协作事件而唤醒。核对当前委托仍有效。
2. **重建当前工作**：读取 Issue 目标和最新约定、Owner 决定、当前候选、已完成交付、活跃 Worker Run、失败和等待项。
3. **判断下一步**：判断哪些事实已经足够，哪些结果仍在途，哪些工作可以并行，哪些需要新决定。
4. **采取动作**：直接执行、派发 Worker、调用 SOP、请求澄清、暂停部分工作、返工、改派或准备交付。
5. **记录必要的协作事实**：把关键委派、边界、交付要求、决策和结果引用留在原 Issue / Run / SOP 记录中。
6. **结束本轮**：如果下一步依赖外部事件或人类决定，结束 Turn，不占用 Runtime 等待。
7. **再次唤醒**：新事件到达后重新读取权威事实，不能假设上一轮计划仍然有效。

Turn 不是 Issue 的状态，也不是一个长期运行的 Planner 实例。它只是 Main Bot 完成一次协调动作的实际 Run。

## 5. Main Bot 在 Issue 上的工作阶段

为了让用户看懂进度，可以呈现以下工作阶段，但这些是**由 Issue、Run、委托和决定事实推导出的工作视图**，不是另建一套权威状态机。

| 工作视图 | 进入条件 | 当前主要动作 | 结束 / 转换条件 |
|---|---|---|---|
| Awaiting Main Bot | Owner 已授权持续协调，尚未取得有效协调 Turn | 等待获准 Main Bot Runtime 领取 | Main Bot 实际开始 Turn，或授权失效 |
| Understanding | Main Bot 正在读取工作约定、项目上下文和已有结果 | 澄清目标、约束和完成条件 | 信息足够进入当前工作安排，或提出 Owner 决定请求 |
| Coordinating | Main Bot 正在规划、直接执行、派发 Agent 或选择 SOP | 组织工作并记录有效委托 | 已进入等待、消费结果或交付 |
| In Progress | 至少有 Main Bot 自身或 Worker 的有效执行正在推进 | 继续执行和收集结果 | 执行终态、等待、返工或交付 |
| Waiting | 当前没有可立即合法推进的动作，等待明确的 Worker、Runtime、资料或 Owner 决定 | 结束 Turn，保留等待原因和解除条件 | 相关事件到达并重新核对后唤醒 |
| Reviewing Results | 收到 Worker / SOP / 本地交付，正在检查其来源、制品和证据 | 接受为可用输入、要求补充或返工 | 结果消费完成，或产生新安排 |
| Replanning | 结果、失败、目标变化或约束变化使原计划不再适用 | 重评剩余工作，修改后续安排 | 新安排明确或需要 Owner 决定 |
| Ready to Handoff | 受托工作已达到交付条件，剩余事项已整理 | 形成交付摘要和待决事项 | 交付提交给 Owner |
| Owner Decision | 有超出授权的业务决定、风险接受或验收需要 Owner 处理 | 展示问题、候选、证据、选项和后果 | Owner 决定后恢复协调或结束委托 |
| Handed Back | Main Bot 已将交付、风险和未完成项交还 Owner | 不再自行扩大执行 | Owner 接受、退回、重新授权或接管 |

重要约束：
- 一个 Issue 同时可能有多个 Worker Run 处于不同状态；Main Bot 的用户视图不能把它们压扁成一个 Run 状态。
- Waiting 不是所有执行都停止。它只表示 Main Bot 当前没有可执行的下一步。
- Main Bot Turn 结束不意味着 Issue 完成。
- Ready to Handoff 不等于 Issue Done；是否完成仍按 Issue 原完成条件判断。
- 需要 Owner 决定时，只暂停依赖该决定的工作；无关分支可以继续。

## 6. Main Bot 如何组织和调整工作

Main Bot 维护的是一份当前有效的工作安排，而不是不可修改的固定计划。

### 6.1 选择执行方式

| 当前工作特征 | Main Bot 选择 |
|---|---|
| 自己可以安全完成且不需要独立执行者 | 直接执行 |
| 需要一种明确专业能力 | 委派一个获准 Worker Agent |
| 存在独立并行交付或不同专业领域 | 并行委派多个 Worker |
| 需要独立负责人和单独生命周期 | 创建子 Issue |
| 已有成熟稳定方法 | 调用局部或完整 SOP |
| 未知、探索性或例外情况 | 自主分析与动态协作 |
| 业务目标、权限、预算或风险边界不清 | 向 Owner 请求决定 |

### 6.2 计划不是新对象的前提

首期工作安排可以用 Issue 上的委派记录、评论、子 Issue、SOP Execution、Run 和交付引用表达。Main Bot 每轮根据这些事实重建当前安排。

不因为 Main Bot 有规划能力，就立即增加 Planner、Plan、Subtask 等平行领域对象。只有在真实恢复或交付场景证明现有 Issue 时间线无法表达必要的计划事实时，才考虑最小补充。

### 6.3 计划变化

发生以下情况时，Main Bot 必须重新判断：
- Worker 交付改变了对问题的理解；
- 失败或评审发现原方案不成立；
- 新结果使部分工作不再必要；
- Owner 修改目标、范围或验收要求；
- Agent / Runtime 不可用或权限被撤销；
- SOP 不适用或产生未覆盖分支。

计划变化只影响后续安排。已经发生的 Run、Artifact、Decision 和历史委派不被重写。

## 7. 跨 Runtime 持续协作

Main Bot 本身和 Worker 都由 Agent 承载，但执行资源可以分布在不同成员本地 Runtime。

### 7.1 正常路径

~~~mermaid
sequenceDiagram
  participant O as Issue Owner
  participant I as Multica Issue
  participant M as Main Bot Runtime A
  participant W1 as Worker Runtime B
  participant W2 as Worker Runtime C
  O->>I: 授权 Main Bot 持续协调
  I->>M: 触发 Main Bot Turn
  M->>I: 读取工作约定与已有事实
  M->>I: 创建 Worker A / B 委派
  I->>W1: 派发 Agent A Run
  I->>W2: 派发 Agent B Run
  M-->>M: 结束当前 Turn
  W1-->>I: Run 终态与交付
  W2-->>I: Run 终态与交付
  I->>M: 形成待处理协调唤醒
  M->>I: 新 Turn 读取全部最新结果
  M->>I: 检查、返工或继续派发
  M->>O: 汇总交付与待决事项
  O->>I: 接受、退回或改变授权
~~~

### 7.2 Main Bot 的持续性

Main Bot 不需要常驻：
- Main Bot Turn 使用一个获准 Runtime；
- Worker 可在其他 Runtime 独立执行；
- Main Bot 等待时结束 Turn；
- Worker 终态和 Owner 决定回到中心；
- 下一次 Turn 根据 Issue 当前事实恢复。

首期不要求 Main Bot Agent 自身跨 Runtime 多活或透明热迁移。若其 Runtime 长期不可用，由 Owner 显式更换 / 重绑协调 Agent，再按现有事实接续。

## 8. 事件如何让 Main Bot 继续推进

不建立一个全局事件总线作为产品前提。先利用 Multica 已有 Issue、评论、Task / Run、工作流和回执事实。

### 8.1 值得触发协调的事件

| 事件来源 | 典型事实 | Main Bot 应做什么 |
|---|---|---|
| Owner | 目标 / 范围 / 授权变化、补充信息、接管请求 | 重新核对工作约定和权限 |
| Worker | Run 成功、失败、取消、阻塞、提出问题 | 消费结果、安排修正或请求决定 |
| SOP | 受托范围完成、等待、失败、交还结果 | 接收结果并重新规划整体工作 |
| Runtime | 不可用、恢复、能力变化 | 判断受影响委派是否仍可继续 |
| 交付 | Artifact / Candidate 新增、版本变化、验证结果产生 | 核对当前候选和证据 |
| 时间 / 外部依赖 | 约定的等待条件到期或依赖变化 | 重新判断是否继续、提醒或升级 |

普通进度通知不一定需要立即唤醒 Main Bot。只有可能改变下一步决策的事件才需要触发；多个相关事件可以合并为一次 Turn，但原始事实必须分别保留。

### 8.2 需要通用化的回唤能力

Multica 当前存在 Squad Leader 专用回唤路径，不能假设普通 Agent 协调者自然获得相同能力。

Main Bot 需要一个通用语义：

- 派发时能追溯由哪个 Issue 上的 Main Bot 委托发起；
- Worker 的终态和交付能够定位到原委派；
- 平台能识别原协调者仍有待处理结果；
- Main Bot 离线时，待处理义务不丢失；
- 多个结果可合并唤醒，但每个结果独立消费；
- 重复事件不重复创建执行；
- 事件到达后仍需检查 Issue 当前授权、目标版本和结果适用性。

实现应优先复用现有 Task lineage、Issue 时间线和失败恢复机制，不引入第二套业务任务队列。

## 9. 等待、失败、重试和重新规划

这些情况必须区分：

| 情况 | 语义 | Main Bot 处理 |
|---|---|---|
| Worker 正常执行中 | 有效 Run 仍在推进 | 等待结果，不重复派发 |
| Runtime 未就绪 | 尚未实际启动或无法领取 | 显示资源阻塞；按授权选择其他 Worker / Runtime 或等待 |
| Worker 可信失败 | 已有失败终态 | 检查原因，决定重试、换人、调整方案或向 Owner 升级 |
| Worker 终态未知 | 断联或缺少可靠回执 | 不假定成功、失败或资源释放；核实旧进程和副作用 |
| 结果不合格 | 执行可能成功，但交付不满足契约 | 指定修正范围和接收标准，产生新候选后重验 |
| 业务决定缺失 | 需要 Owner 决定范围、风险或例外 | 提交明确决定请求，只等待依赖它的工作 |
| SOP 不适用 | 现有方法无法覆盖当前情况 | 暂停或交还该受托范围，由 Main Bot 自主规划 |
| 目标发生变化 | 旧计划部分失效 | 以新工作约定为准，旧结果保留并逐项判断可复用性 |

技术重试、业务返工和重新规划是不同动作：
- 技术重试由原生 Run / Task 机制表达；
- 业务返工由原工作安排和新的候选 / 检查表达；
- 重新规划是 Main Bot 根据最新事实改变后续委派，不应伪装成 Run 重试。

## 10. Owner 介入、授权变化与接管

Main Bot 的自主性必须受 Owner 授权边界约束。

| Owner 动作 | Main Bot 应如何响应 |
|---|---|
| 补充事实或澄清 | 更新当前理解，检查受影响工作 |
| 批准已请求的决定 | 只在批准范围内继续 |
| 改变目标或验收要求 | 停止基于旧约定的新派发，检查在途执行与旧结果 |
| 扩大授权或预算 | 新授权生效后才执行超出原范围的动作 |
| 暂停协调 | 停止新的委派和协调推进，保留已有 Run 状态 |
| 撤销协调授权 | Main Bot 不再创建新工作；在途 Worker 按决定继续、暂停或取消 |
| 接管 Issue | Main Bot 交回已知事实、结果和未决项；Owner 或新负责人以自己的授权继续 |
| 退回交付 | 明确不满足的要求、针对的 Candidate 和修正归属，重新进入推进 |

撤销 Main Bot 授权不等于所有 Worker Run 自动停止。每个在途 Run 的停止请求、实际终态、工作副本隔离和外部副作用仍须独立处理。

## 11. Main Bot 交付与 Issue 完成

Main Bot 的责任是交付一个足以让 Owner 判断和继续工作的结果包，而不是自行宣告业务工作完成。

交付至少汇总：
- 已完成的目标和实际范围；
- 关键变更、Artifact 和 Candidate 版本；
- Worker / Run 的来源和执行状态；
- 已执行的测试、Review、验证及其证据；
- 未验证项、失败项、遗留风险和外部依赖；
- 已知用量与未知计量覆盖；
- 已采用的 SOP / Skill / Rule 版本；
- 需要 Owner 决定或验收的事项。

Owner 根据原 Issue 工作约定：
- 接受当前 Candidate；
- 退回具体缺项；
- 接受明确列出的限制或例外；
- 改变目标并授权下一轮；
- 结束 Main Bot 委托并自行接管。

**Main Bot 完成一次交付 ≠ Issue Done。** Issue 仍由原有完成条件和有权主体推进。

## 12. 对现有架构模型的影响与需要统一的冲突

本阶段不直接修改正式架构基线，但发现现有正式设计需要在下一次整体收敛时统一：

1. `01-unified-work-lifecycle.md` 当前仍将 Squad 作为 Issue 可选 Assignee，并将 Squad Leader 作为该 Assignee 的协调者；这与 Main Bot 成为统一 Issue Coordinator、Squad 不再是必需调度层的方向不完全一致。
2. `core-object-model.md` 当前将 Squad / Leader 定义为核心组织参与对象；需要重新评估 Squad 是否只是可选资源配置，以及 Main Bot 是否应作为 Agent 的受托职责而非新增领域对象。
3. `cross-layer-contracts.md` 当前 Delegation Contract 仍以 Squad / SOP 为主要受托主体；需要将 Main Bot 的 Issue 级持续协调委托纳入统一职责关系，同时不创造新的业务任务对象。
4. `lifecycle-state-event-model.md` 已经明确不建立全系统总状态机；Main Bot 视图应由 Issue、Task / Run、交付和授权事实推导，不能另建与之竞争的状态机。
5. `core-consistency-concurrency.md` 已定义权威写入、幂等投递、旧执行隔离和恢复语义；Main Bot 应复用这些规则，具体缺口只针对现有 Multica 回唤和委派链补齐。

这些是正式架构需要统一的差异，不代表本阶段已经决定删除 Multica 原生 Squad 数据或所有 Squad 功能。

## 13. 推荐的最简落地顺序

### 第一步：定义 Main Bot 委托和运行入口
- 复用现有 Squad Leader Agent 作为 Main Bot Agent 的起点。
- 使其可以直接执行，也可以直接委派本次获准的任意 Agent。
- 不再要求固定 Squad Roster。
- 保留 Issue Owner / Accountable Member 的业务责任。
- 明确一次性 Agent 协助与持续 Main Bot 委托的区别。

### 第二步：打通 Worker 结果回到 Main Bot
- 复用原生 Worker Task / Run。
- 将 Squad 专用 Leader 回唤语义推广为普通 Coordinator 回唤。
- 终态、失败、取消和阻塞均能回到原协调者。
- 多个完成事件可合并唤醒，但结果分别保留。
- 离线时待处理回唤可恢复。

### 第三步：打通多轮恢复和交付
- Main Bot 每次 Turn 从 Issue 和原生 Run 重建工作。
- 先不增加独立 Planner 数据库。
- 对交付按来源、版本、证据和缺项消费。
- Owner 可以决定、撤权、接管或验收。

### 第四步：验证后再判断是否需要补充结构
只有在实际测试证明 Issue 时间线和 Run 谱系无法表达某项必要的协调事实时，才补充最小记录。Main Bot 自身跨 Runtime 热迁移不属于首期必要条件。

## 14. 本阶段退出标准

满足以下条件，Main Bot 生命周期设计才算具备进入实现映射的基础：

- Member 可以保留 Issue Owner，同时把持续协调委托给 Main Bot。
- Main Bot 不依赖 Squad 也能直接执行或委派 Worker。
- Main Bot 可以跨多个成员 Runtime 组织并行工作。
- Main Bot Turn 可结束，Worker 仍独立执行。
- Worker 的结果、失败和阻塞能可靠触发 Main Bot 后续协调。
- Main Bot 恢复时能从 Issue 和 Run 事实重建当前工作，不依赖单个 Session。
- Owner 修改目标、撤权或接管后，旧授权不能继续产生新派发。
- 结果汇总回原 Issue，业务完成仍按原有验收规则决定。
- 不新增第二套 Task / Run / Issue 状态机或中央调度服务。

## 15. 依据与边界

### AgentPlatform 现有设计
- [Main Bot 的 Issue 工作组织模型](mainbot-issue-operating-model.md)
- [Main Bot 跨 Runtime 持续协调机制](mainbot-runtime-coordination.md)
- [研究与架构推进规则](../governance/research-and-architecture-rules.md)
- [Issue 生命周期](../architecture/01-unified-work-lifecycle.md)
- [核心对象模型](../architecture/core-object-model.md)
- [统一生命周期、状态机与事件模型](../architecture/lifecycle-state-event-model.md)
- [核心协作一致性与并发控制](../architecture/core-consistency-concurrency.md)

### Multica 源码
- [Issue Trigger](https://github.com/multica-ai/multica/blob/main/server/internal/handler/issue_trigger.go)
- [Task Service](https://github.com/multica-ai/multica/blob/main/server/internal/service/task.go)
- [Comment Trigger / Routing](https://github.com/multica-ai/multica/blob/main/server/internal/handler/comment.go)
- [Squad Leader Briefing](https://github.com/multica-ai/multica/blob/main/server/internal/handler/squad_briefing.go)
- [Daemon Claim](https://github.com/multica-ai/multica/blob/main/server/internal/handler/daemon.go)

上游事实与建议边界：
- Multica 当前 Issue 指派为 Agent 时，会沿普通 Issue Agent Task 入口派发；指派为 Squad 时，使用 Squad Leader 专用派发。
- Squad Leader Briefing 明确规定“必须委派、不能亲自执行”，并将成员选择限制在 Squad Roster；这是需要改造的产品约束。
- Worker 评论回唤 Leader 的特殊路径与 Squad / Leader Task 关联；不能假设普通 Main Bot 已拥有同等通用回唤。
- Task 创建会读取目标 Agent 绑定的 Runtime；首期 Main Bot 可绑定一个 Runtime，Worker 分布在其他 Runtime，无需先支持同一 Main Bot Agent 跨 Runtime 多活。
- 本文中的 Main Bot 阶段视图是产品语义建议，不是 Multica 已存在的状态字段或功能承诺。
