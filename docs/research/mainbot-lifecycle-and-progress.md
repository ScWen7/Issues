# Main Bot 生命周期与 Issue 持续推进模型

> 本阶段研究问题：Member 将 Issue 的执行协调委托给 Main Bot 后，Main Bot 如何接手、组织工作、等待、恢复、重新规划并交付？  
> 研究范围：产品工作生命周期与现有 Multica 机制映射。本文不定义数据库表、API、独立 Planner 服务或第二套任务状态机。

## 1. 核心结论

Main Bot 不需要一套独立于 Issue、Run 的完整业务生命周期。它是 Issue 上被授权的持续协调职责，由多个短生命周期 Coordinator Turn 完成。

- **Issue 生命周期**：这项业务工作是否待安排、推进、等待、审查、完成或取消。
- **Main Bot 委托关系**：当前是否有一个 Main Bot 获准持续协调该 Issue，授权范围是什么。
- **Coordinator Turn**：Main Bot 每次被唤醒后读取最新事实、决策、采取动作并结束本轮。
- **Worker Run**：实际 Agent 在某个 Runtime 上执行的记录。
- **交付与决定**：Worker 结果回到 Issue，由 Main Bot 汇总。Owner 处理保留的业务决定，需具名验收时交给工作约定指定的成员。

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

### 8.2 普通 Agent 的原生回唤

项目锁定的 Multica `fdfbfcd` 已支持普通 Agent 在 Issue 上登记回唤。另对照提交 `24b8035`，两处的工程说明与回唤服务实现分别为相同 Git blob。以下为源码核查，未进行 AgentPlatform 多 Runtime 联调。[固定版本工程说明](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/docs/engineering/issue-wakeups.md) · [对照版本实现](https://github.com/multica-ai/multica/blob/24b80353158cbf7a59f18a7e8cc640ff77899044/server/internal/service/issue_wakeup.go)

| 正在等什么 | 原生入口和边界 | Main Bot 恢复时怎么判断 |
|---|---|---|
| 同 Issue 指定 Worker Run | 订阅实际 Task ID 的 `task.completed`、`task.failed` 和 `task.cancelled`。登记时加锁检查已有终态，可接住先完成、后登记的情况。宽泛 Agent 订阅只观察后续事件，精确订阅仍指向原 Run。[注册检查](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/service/issue_wakeup.go#L600-L625) · [过滤范围](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/docs/engineering/issue-wakeups.md#L99-L109) | 读原委派及 Run 谱系，检查是否已有重试、重跑或可核对的制品。 |
| 请求成员答复、等待阻塞解除 | 可订阅指定成员的评论、Issue 字段变化，或设置有期限的检查。原生目录含 `task.deferred`、`task.waiting_local_directory` 等具体事实。[事件目录](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/docs/engineering/issue-wakeups.md#L124-L172) | 到原 Issue 核实谁作出了什么决定或哪项条件已满足。SOP 出口和候选验收按各自记录判断。 |
| 子 Issue 或外部依赖 | 父项的 `child_done` 系统规则按配置及当前 Assignee 通知。还可观察同工作区指定 Issue 的有限状态或已关联 PR 的条件。[父项规则](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/docs/engineering/issue-wakeups.md#L462-L477) · [条件范围](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/docs/engineering/issue-wakeups.md#L601-L623) | 回父项查子项的实际交付及适用版本。子项取消也可能满足关闭条件。 |

**从委派找到源 Run。** Main Bot 在原 Issue 显式提及目标 Agent 时，先保留委派评论与目标。评论回执可能显示已入队、已合并、延期或受阻；它没有为每个目标返回新 Task ID。按触发评论及合并评论定位计划覆盖的 Run，领取后优先核对实际投递的评论引用。暂时无法确认时，保留分工和原评论，安排有截止时间的复核。中途退出或恢复时，查回尚未登记的源 Run 和已生效的规则，再补上仍适用的订阅。普通 Agent 自发回复和 Squad 专用的隐式评论路由是另外的入口。[评论派发结果](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/comment.go#L83-L109) · [评论与 Run 的关联](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/packages/core/types/agent.ts#L369-L384) · [显式与隐式路由](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/comment.go#L2693-L2732)

**从回唤找到尚待处理的交付。** 匹配事件与源变更一起写回执，调度在派发事务内处理回执。多条通知可压缩，符合条件时可加入已有 Run。待处理通知同类合并后仅保留次数、首次时间和最近来源，已处理回执七天后可清理。恢复时按原 Issue 的未结委派、Run、候选版本、制品和消费记录逐项核对。若此时已改派、撤权或同一 Agent 已获新委托，旧 Run 交回历史结果，后续写入按当前委托决定。[原生派发](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/docs/engineering/issue-wakeups.md#L201-L235) · [保留边界](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/docs/engineering/issue-wakeups.md#L363-L373) · [领取权限](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/service/issue_wakeup.go#L1468-L1518)

### 8.3 普通 Agent 协调对既有协作的影响

核查对象是 Multica 固定提交 `fdfbfcd` 下两种派发入口。下表第二列记录源代码行为，第三列记录 AgentPlatform 的采用方式及仍需联调之处。复用相同的 Task / Run 链，仍可能产生不同的上下文、线程路由和执行环境。

| 协作场合 | 固定版本的行为差异 | 产品处理 |
|---|---|---|
| 单次协助、选择 Worker | Leader 的专用上下文含成员角色、可直接提及的身份、小队自定义指令。普通 Agent 领取 Issue 时不会经由这个分支获得上述信息。[上下文构造](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/squad_briefing.go#L256-L295) · [领取分支](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon.go#L3241-L3285) | 仅当本 Issue 有持续委托时才使用协调上下文。提供当前范围内候选 Agent 的能力与可路由身份，派发时复核实际调用资格。若团队依赖旧指令中的审查或交付要求，由项目显式采用适用规则。 |
| Worker 等待答复、成员插话 | 普通 Worker 的无提及评论不会自动回给主责 Agent。成员回复 Worker 的评论优先路由给原作者。普通 Agent 与成员均可在获准时指定支持追加输入的本 Issue Run，无法投进去时保留普通后续处理。[线程路由](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/comment.go#L2693-L2764) · [在途纠偏](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/task_supplement.go#L167-L199) | 终态等待与途中提问各有继续入口。用显式提及或预先登记的限定来源订阅找回问题，用投递回执判断纠偏何时能起效。重复唤醒时查原问题与消费记录，成员之间的日常讨论无需逐条唤醒 Main Bot。 |
| Worker 局部受阻、交付或提审 | 默认运行提示可引导 Agent 写 Issue 状态，Leader 另有派工时维持父项进度的指令。具名工作流或启用交接的默认工作流会按当前指派生成步骤或观察者提示；观察者提示本身不证明写入受限。[默认状态规则](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/execenv/runtime_config_sections.go#L678-L697) · [任务身份与步骤提示](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/issue_workflow_entry.go#L350-L396) | Worker 报自己这份分工的结果和影响。整体状态写入须核对本次委托、项目规则及当前候选；需要具名验收时还要有指定成员的决定。继续核验默认、受控工作流两类入口。 |
| 工作流换人、重入与在途 Run | 小队专用交接按 Issue 修订保留进入步骤的记录。普通 Agent 已有匹配的 pending Run 时可能不另排任务。工作流步骤名检查能拒绝部分过期状态更新，无法区分同名步骤的两次进入。普通改派和取消 Issue 也各自独立于停止 Run。[普通入队](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/service/issue_trigger.go#L152-L174) · [小队交接](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/service/workflow_squad_handoff.go#L13-L46) · [步骤守卫](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/issue_workflow_entry.go#L80-L123) · [改派与在途工作](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/issue.go#L4400-L4432) | 把持续授权和交接事实保存在 Issue 可重读的位置。积压或同一步骤再次进入时，查本次交接是否已经处理。若旧 Run 的绑定无法推进当前步骤，沿原工作流恢复入口处理。撤权后旧回执归原分工；在途 Worker 单独继续、停止或隔离。 |
| 同机协调与写文件 | 原生 Leader 在绑定判断中跳过项目本地目录。普通 Issue Run 在命中本机 `in_place` 目录时会参与路径互斥，即使本轮只是收报告，也可能被正在构建的 Worker 挡住。[本地目录与锁](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/local_directory.go#L106-L156) | 对仅需 Issue 材料的协调选用隔离环境；确需写代码时按普通写入规则取得工作副本。若宿主只能绑定同一目录，显示排队。Worker 持锁等答复时，应先记录问题和可恢复进度，在能安全暂停时释放目录，再接续该分工。 |
| 进度、权限与计量 | 小队的活动记录和评论静默退出有 Leader 身份条件。普通 Run 保留自身执行和评论记录。调用人、Run 审计归因、Issue 业务总责分别有来源。Usage 按原 Task、供应商和模型记录，可按 Issue 查回。[活动记录条件](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/squad.go#L1091-L1138) · [执行归因](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/attribution/attribution.go#L148-L165) · [用量归集](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/task_usage.sql#L1-L53) | 工作台从 Run、原委派、等待原因和实际结果显示进度。按原执行计量，未知保留未知。历史活动保留其来源。项目可见的 Agent 仍须满足目标的调用权限及资源授权。 |
| 父子项、SOP 与存量配置 | 启用的 `child_done` 按父项当前指派选择 Agent Run 或成员通知，子项取消也可满足关闭条件。项目工作流进入配置了处理人的步骤会按配置重新指派。[父项回唤](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/docs/engineering/issue-wakeups.md#L462-L496) · [步骤交接](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/issue_workflow_entry.go#L18-L38) | 父项按目标核实子项交付，SOP 继续负责已托付的节点和返工，Main Bot 只接收相应出口。同一分工只走一个派发入口。存量流程若仍指向原小队，可沿原配置走完；切换时明确接手者、新配置生效点及旧 Run 的处置，历史指派和 Run 保留原义。 |

实施前优先联调三条交互。第一，同一 Issue 中 Worker 尚未终结便提问，成员在原线程答复，Main Bot 在目标 Run 支持或不支持追加输入时均能判断答复去了哪里。第二，带着待处理 Run 完成工作流交接、再进入同名步骤，同时收到旧结果，观察新交接按当次授权处理且旧结果未推进新步骤。第三，Worker 占用原地工作目录时触发纯协调，再让 Main Bot 实际修改代码，分别核对目录等待、隔离和写入互斥。这些是设计需要取得的运行证据，本轮只核查了固定版本源码。

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

Main Bot 汇总当前候选、证据及缺项。满足完成条件时由有完成权的主体推进 Issue；工作约定要求具名验收时，交给约定的 Acceptor。

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

## 12. 与正式架构的对应

[核心对象模型](../architecture/core-object-model.md)与[工作生命周期](../architecture/01-unified-work-lifecycle.md)定义人工总责、受托 Main Bot 与 Worker 分工的关系。[跨层契约](../architecture/cross-layer-contracts.md)定义谁能派发、谁能接收结果，以及何时交回决定。[状态与事件](../architecture/lifecycle-state-event-model.md)和[一致性规则](../architecture/core-consistency-concurrency.md)定义原生回唤后重新核对的事实、撤权和迟到结果的处理。

## 13. 下一步验证的边界

在进入实现验证时，沿既有 Multica 入口走通从委派评论定位实际 Worker Run、登记回唤、恢复协调到逐项消费的链路。重点覆盖 Worker 先结束、回唤合并、协调 Runtime 离线以及同一 Agent 再次受托后旧结果才到达。每种情况分别观察原 Run 归属、是否重复派发、当前候选的消费记录以及实际有效的授权。

## 14. 本阶段退出标准

满足以下条件，Main Bot 生命周期设计才算具备进入实现映射的基础：

- Member 可以保留 Issue Owner，同时把持续协调委托给 Main Bot。
- Main Bot 可在本次授权内直接执行或委派 Worker。
- Main Bot 可以跨多个成员 Runtime 组织并行工作。
- Main Bot Turn 可结束，Worker 仍独立执行。
- 指定 Worker Run 的成功、失败与取消，以及用原生事实表达的等待条件，均有明确的继续入口。未获可靠终态的分工保留为待核实。
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
- [Issue Trigger](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/issue_trigger.go)
- [Task Service](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/service/task.go)
- [Comment Trigger / Routing](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/comment.go)
- [Squad Leader Briefing](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/squad_briefing.go)
- [Daemon Claim](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon.go)

上游事实与建议边界：
- Multica 当前 Issue 指派为 Agent 时，会沿普通 Issue Agent Task 入口派发；指派为 Squad 时，使用 Squad Leader 专用派发。
- Squad Leader 的运行提示要求向名册成员委派。指派普通 Agent 并将 Issue 协调权交给它时，沿普通 Agent 入口运行。
- 普通 Agent 可登记 Issue Wakeup 等待 Worker Run 终态。原生 Squad 的评论路由另有规则。两条入口的源码边界见第 8.2 节。
- Task 创建会读取目标 Agent 绑定的 Runtime；首期 Main Bot 可绑定一个 Runtime，Worker 分布在其他 Runtime，无需先支持同一 Main Bot Agent 跨 Runtime 多活。
- 本文中的 Main Bot 阶段视图是产品语义建议，不是 Multica 已存在的状态字段或功能承诺。
