# SOP 如何从 Squad / Main Bot 动态协作中被发现和提炼

> 研究范围：第一阶段“发现值得固化的方法”和第二阶段“从真实协作实践提炼流程”。  
> 主要源码依据：Multica Squad Leader / Issue delegation；LoopForge Main Bot / Subagent activity。  
> 本文是研究结论与候选设计，不表示这些机制已经全部进入 AgentPlatform 的正式架构决策。

## 1. 研究问题

Agent 在处理一个真实 Issue 时，往往并没有预先确定完整流程。Coordinator 会根据当前目标、成员能力、工具可用性、执行结果和新出现的问题，动态决定下一步。

因此 SOP 的形成不能从“把现有流程画成 DAG”开始，而要回答：

1. 如何观察一次动态协作，且不把不可见的推理当成事实？
2. 如何从多个工作案例中识别重复出现的稳定方法？
3. 如何区分稳定的工作流程、角色专业方法、通用约束和一次性决策？
4. 如何把真实轨迹抽象成有适用条件、输入输出、角色职责、分支和异常处理的候选 SOP？
5. 如何避免把某个 Agent、某台 Runtime、某次 Session 或某个 Issue 的偶然特征固化进流程？

核心认识：**SOP 候选来自多次真实工作中重复出现、可以解释且能被验证的协作模式，而不是单次执行轨迹的复制。**

## 2. Coordinator：Main Bot 与 Squad Leader 的共同点和差异

### 2.1 共同职责

两者都承担 Coordinator 职责：
- 理解当前工作目标与约束；
- 选择执行主体和协作方式；
- 将工作切分并交接给 Agent / 成员；
- 接收执行结果并判断下一步；
- 处理阻塞、失败、返工和人工升级；
- 在工作结束时汇总结果并交还业务责任方。

这是一种职责抽象，不意味着需要建立中央常驻 Coordinator 服务或 Coordinator Pool。

### 2.2 Multica Squad Leader 的实际模式

源码 `server/internal/handler/squad_briefing.go` 的 Squad Operating Protocol 明确要求 Leader：
- 读取 Issue 目标、描述、最新评论和验收条件；
- 根据 Squad Roster 中成员角色与 Skills 选择适合成员；
- 通过精确 @mention 评论委派工作；
- 每次触发都记录 `action`、`no_action` 或 `failed`；
- 委派并记录后结束当前轮，不亲自做成员的工作；
- 成员更新、完成或再次 @mention 时重新唤醒，再评估下一步；
- 对不属于本 Squad 的 Issue 不越权修改状态。

Squad Roster 会提供 Leader、成员类型、角色和 Agent Skills；Squad 自身还具有 instructions。Issue 被指派给 Squad 时，后端把 Squad Leader Agent 作为实际运行主体，并在 claim 时注入 Leader Protocol 与动态 roster。

相关源码：
- `server/internal/handler/squad_briefing.go`
- `server/internal/handler/issue_trigger.go`
- `server/internal/service/issue_trigger.go`
- `server/internal/handler/daemon.go`
- `server/internal/handler/comment.go`
- `packages/core/types/squad.ts`

因此 Squad Leader 是一个**事件触发、逐轮重新评估、以委派为中心**的协调者。它不是一个持续占用执行资源的总控进程；成员执行期间它可以停止，等待工作事件再醒来。

### 2.3 LoopForge Main Bot 的实际模式

LoopForge Main Bot 更开放：
- 可以自己调用工具，也可以动态派发 Subagent；
- 可按角色定义加载角色 Prompt、Rules 和 Skills；
- 可继续之前的 Subagent Session；
- 能在一个对话 / 工作区中串联多轮 Agent 工作；
- 能收集角色声明的交付物；
- 可根据需求推荐 SOP、启动 SOP，或在 SOP 运行中 pause / resume / takeover。

`AssistantActivityEvent` 记录 `Parent`、`Subagent`、`Role`、`AgentID`、`Input`、`Output`、工具事件和失败状态；Parent 将 Subagent 的活动挂到产生它的 Agent Dispatch 下。前端 `collectSubagents` 将多次派发和产物按 Subagent 聚合。

相关源码：
- `internal/domain/assistant.go`
- `internal/httpapi/assistant_subagents.go`
- `chatbot/src/activity.js`
- `docs/conversation-workspaces.md`

### 2.4 角色边界

| 维度 | LoopForge Main Bot | Multica Squad Leader |
|---|---|---|
| 作用域 | 用户对话及关联工作 | 一个 Squad 获得的工作 |
| 自己执行 | 可以 | Squad 设计原则上应委派，不能替代成员 |
| 委派对象 | 动态选择工具和 Subagent | Squad roster 中的成员 |
| 协作节奏 | 可在一轮中连续多次规划和调用 | 通常委派后停止，等待事件再唤醒 |
| 持续性 | Conversation / Workspace / Subagent Session | Issue / Task / Comment / Squad Activity |
| 最有价值的观察 | 规划变化、工具使用、角色派发、结果消费 | 能力匹配、任务切分、委派、等待、反馈、再委派 |

AgentPlatform 可以从两种上游机制中提炼同一项工作的经验。对 Main Bot 组织的一次协作，沿 Issue、委派和实际 Run 查明谁作了分工、依据什么结果调整、哪个交接可以复用。比较两种上游实现时，保留各自的权限边界和证据来源。

## 3. 第一阶段：发现值得固化的方法

### 3.1 观察对象不是“聊天记录”，而是一次工作协作 Episode

建议将一次 Episode 定义为：围绕一个 Issue 的目标和交付要求，从协调者开始组织工作，到结果被消费、接受、退回或明确终止的一个可追溯工作片段。

一个 Issue 可能包含多个 Episode：
- 初始方案探索；
- 后端实现；
- 独立评审；
- 缺陷修正；
- 集成验证；
- 发布准备。

一个 Episode 也可能跨越多个 Coordinator turn、多个 Agent Task / Subagent Dispatch、多个 Run 和多份 Artifact。

因此不能把 Conversation、Session、Task、Run 中任何一个单独当成 Episode 的等价物。

### 3.2 真实协作可观察事实

从 Multica 和 LoopForge 的已有机制看，至少可从以下事实重建工作过程：

| 事实类别 | Multica 可观察来源 | LoopForge 可观察来源 |
|---|---|---|
| 工作目标和范围 | Issue 描述、验收条件、评论、Project Workflow | 对话输入、关联 Issue、引用对象 |
| 协调者身份 | Squad / Leader、Issue Assignee、Task | Conversation Speaker、Main Bot |
| 成员能力与分工 | Squad Roster、成员 Role、Agent Skills | Role Definition、绑定 Rules / Skills |
| 协调决策 | Leader turn、Squad Activity outcome / reason | Main Bot 可见活动、Dispatch 输入 |
| 委派行为 | @mention 评论、Task、Task lineage | Agent tool call、Parent、Subagent、Role |
| 实际执行 | Task 状态、执行记录、工具和结果回报 | Subagent activity、Tool event、Input / Output |
| 交付结果 | Issue comments、附件、Artifacts、提交与 PR | 角色交付物、Workspace Artifact、Assistant Output |
| 反馈与返工 | 成员评论、再次触发、Task 重试 / 重跑 | 后续 Agent Dispatch、工具活动、工作区变更 |
| 结束与决定 | Issue 状态、业务负责人决定、Squad Activity | Main Bot 汇总、SOP Run 状态、人工决定 |

重要限制：
- 记录到 Agent Dispatch 不代表实际 Agent 已启动；记录到 Task queued 也不代表执行完成。
- Leader 的 action/no_action 是协调决策事实，不等同于工作成功。
- Agent 自述的完成、宿主实际回执、制品存在、检查通过和负责人接受必须区分。
- 不需要也不应该采集模型私有思维链。只使用可授权的输入、输出、工具活动、状态、制品、决定和证据。
- 成员没有授权共享的本地活动不进入团队提炼数据集。
- 观察缺失时标记未知，不能从沉默推断成功或失败。

### 3.3 发现信号

以下信号可以提示“可能存在可固化方法”，但单个信号不能直接触发正式 SOP 生成。

1. **重复的工作结构**：不同 Issue 中反复出现相似阶段、依赖、角色分工和交付物。
2. **重复的协调策略**：Coordinator 在同类工作中反复选择相同能力组合或交接顺序。
3. **稳定的交付契约**：每次都需要相同的输入、产物、检查或业务决定。
4. **重复的返工路径**：某类失败总是回到相同的修正步骤，且修正后能稳定解决。
5. **高成本的重复决策**：Coordinator 每次都要重新分析相同的分工、顺序或检查安排。
6. **跨 Coordinator 可迁移**：不同 Leader / Main Bot、不同 Agent 组合也能复现相同方法。
7. **显式方法引用**：现有 Playbook / Skill / Rule 已反复被选择，并逐渐形成固定的节点衔接关系。

发现信号应基于跨 Episode 的统计和证据，而不是单个 Agent 的主观总结。

### 3.4 候选发现的分级

| 观察结果 | 推荐处理 |
|---|---|
| 只出现一次，且高度依赖特殊背景 | 保留为 Issue 经验，不提炼 |
| 重复的是某个专业操作或判断方法 | 提炼为 Skill / Role / Verification |
| 重复的是可按情况选用的解决策略 | 提炼为 Playbook |
| 重复的是跨角色、具有依赖和交付约定的工作流程 | 进入 SOP 候选 |
| 重复的是团队不可违反的约束 | 进入 Rule / Principle |
| 只有结果相似，但过程和适用条件差异很大 | 暂不合并，继续观察或拆成不同候选 |

### 3.5 发现时的核心判断

判断一个模式是否值得成为 SOP，至少检查：
- 是否有稳定的工作目标和适用范围？
- 是否存在可复用的阶段或依赖？
- 是否需要多个执行主体或明确的交接？
- 是否存在可检查的输入、产物或决定？
- 是否有可描述的异常、失败和返工路径？
- 能否把 Agent 身份替换成角色能力，而不依赖某个特定 Agent？
- 能否在不同 Issue、不同执行环境中复现？

如果一个方法的核心价值在于 Agent 根据情境灵活选择策略，而不是固定步骤，那么它更适合 Playbook，而非 SOP。

## 4. 第二阶段：如何从真实协作实践提炼 SOP

### 4.1 不复制轨迹，而是抽象“工作方法”

单次协作轨迹通常包含：
- 偶然的执行顺序；
- 当时可用的 Agent；
- 特定人员的偏好；
- 临时工具和环境；
- Issue 特有的背景信息；
- 中途改变方向的决策；
- 失败重试和无效操作。

这些内容不能原样进入 SOP。

提炼需要把具体事实转成可复用的抽象：

| 真实轨迹中的具体内容 | SOP 中应该提炼的内容 |
|---|---|
| @后端 Agent A | 需要具备某项后端能力的执行角色 |
| 某个具体 Session | 本节点的一次执行实例，不进入定义 |
| 某个 Issue 编号 | 适用的工作类型和输入条件 |
| 先读某个文件再修改 | 输入依据与执行要求，文件路径改为参数或来源引用 |
| Agent 写出 fix.md | 具名产物契约及其内容要求 |
| Leader 发现测试不通过后重新委派 | 测试失败条件、返工目标和回退节点 |
| 某成员临时提供业务解释 | 人工输入 / 决策门禁，不能默认每次由该成员执行 |
| 特定机器或宿主 | 能力要求和环境约束，不固定绑定具体 Runtime |

### 4.2 推荐的提炼步骤

~~~mermaid
flowchart TD
  A["选取一组相关 Episode"]
  B["重建事实时间线"]
  C["对齐共同目标和工作类型"]
  D["识别重复阶段与交接"]
  E["区分稳定步骤和偶然路径"]
  F["抽象角色能力、输入和产物"]
  G["归纳依赖、条件和并行"]
  H["提炼失败、返工和人工决策"]
  I["形成 SOP Candidate"]
  A --> B --> C --> D --> E --> F --> G --> H --> I
~~~

每一步都需要保留证据来源，尤其是“为什么认为某个步骤是必需的”“为什么把某两个步骤定义为依赖”“为什么某个失败应该退回某个节点”。

### 4.3 从多次执行中识别稳定结构

例如收集到 8 个 API 需求的协作 Episode：

- 8 次都先明确接口范围和兼容约束；
- 7 次都先形成实现方案；
- 8 次都需要代码实现；
- 8 次都需要测试；
- 6 次进行了独立评审；
- 3 次评审后退回开发；
- 2 次因为兼容问题需要人工确认；
- 有 2 次没有独立评审，但都属于小范围文档变更。

不能简单将所有动作合并成一条固定串行流程。

更合理的候选结构可能是：

- 需求定型：必需；
- 方案设计：按变更复杂度决定；
- 开发实现：必需；
- 独立评审：按风险和变更范围触发；
- 测试：按变更类型和验证要求执行；
- 人工确认：仅在兼容性或业务风险条件满足时触发；
- 交付：必需。

这说明 SOP 提炼必须同时提炼：
- 必需步骤；
- 条件步骤；
- 可并行步骤；
- 允许跳过的步骤；
- 返工路径；
- 人工决定边界。

**频率不是流程规则。** 一个步骤出现得多，不代表它在所有情况下都必需；一个步骤只出现少数几次，也可能是重要风险门禁。

### 4.4 角色抽象，而不是 Agent 绑定

提炼时必须将执行主体从具体 Agent ID 转成能力角色。

例如：

| 真实协作主体 | 抽象角色 |
|---|---|
| Agent A（后端开发） | Backend Implementer |
| Agent B（代码评审） | Independent Reviewer |
| Agent C（测试） | Verification Engineer |
| 在 Issue 上组织该项协作的 Agent | Coordinator |
| 项目负责人 | Business Approver |

角色需要描述：
- 必需能力；
- 责任边界；
- 输入；
- 输出；
- 可用工具要求；
- 不能做的事情；
- 结果交付契约。

实际运行时再根据项目采用的角色和成员可用能力解析到具体 Agent / Runtime。

否则 SOP 会退化成某个 Agent 的个人脚本，无法在团队中复用。

## 5. Main Bot 与 Squad Leader 的观察重点不同

### 5.1 Main Bot 观察重点

Main Bot 的动态活动更适合发现：
- 哪些问题需要先调查再规划；
- 什么条件下应该直接执行，什么条件下应该委派；
- 哪些角色组合经常共同完成一类工作；
- 哪些工具或资料经常成为前置条件；
- 执行结果如何改变下一步计划；
- 哪些任务经常被交给现有 SOP；
- 哪些 SOP 经常无法覆盖，导致 Main Bot 接管。

特别是“经常绕开 SOP”与“经常从 SOP 中途接管”，可能是发现 SOP 适用边界和流程缺口的重要信号。

### 5.2 Squad Leader 观察重点

Squad Leader 的动态协作更适合发现：
- 如何根据成员能力分配工作；
- 哪些工作可以并行；
- 哪些工作必须等待其他成员；
- 哪些结果需要独立复核；
- 哪些反馈会触发重新委派；
- 哪些成员交付不满足预期；
- 什么时候应该升级给人；
- Leader 在什么情况下判断无需继续动作。

它的价值在于揭示协作拓扑，而不仅仅是任务执行步骤。

### 5.3 两种观察如何合并

| Main Bot 贡献 | Squad Leader 贡献 | 最终可提炼内容 |
|---|---|---|
| 发现任务类型和方法选择条件 | 根据成员能力安排执行 | SOP 适用条件与角色配置 |
| 动态调整执行计划 | 形成并行或依赖分工 | DAG 结构 |
| 判断工具和资料要求 | 发现成员交接所需信息 | 输入契约 |
| 消费执行结果 | 判断成员结果是否可交接 | 节点结果消费与检查 |
| 决定是否接管 SOP | 发现小队无法完成的情况 | 异常与人工升级路径 |
| 跨多次工作比较方法 | 跨成员比较协作效果 | 可迁移性和候选成熟度 |

## 6. 提炼时需要保留的最小事实模型

这里先不设计新的平台对象，而是定义研究和分析所需的逻辑信息。

### 6.1 Episode

代表一段可分析的工作协作：
- 来源 Issue；
- 目标与验收要求；
- Project / 工作类型；
- 承担协调的成员或受托 Agent 及其授权范围；
- 实际参与的成员、Agent 与各自分工；
- 开始和结束边界；
- 结果状态及其证据；
- 是否存在授权和共享限制。

### 6.2 Coordination Step

代表协调者一次可观察的决策或行动：
- 触发原因；
- 当时的工作状态；
- 决策动作：直接执行、委派、等待、返工、升级、结束；
- 目标执行者和能力理由；
- 交付范围与附加约束；
- 实际触发结果；
- 是否发生后续修正。

不能将模型的私有推理链作为必要字段；记录可审计的决策输入摘要、行动和结果即可。

### 6.3 Execution Step

代表 Agent / Member 的实际工作：
- 执行主体及当时角色；
- 输入来源；
- 工具和宿主活动（在共享授权范围内）；
- 开始、结束、失败、取消和恢复事实；
- 实际输出；
- 产物及其版本；
- 执行来源和可信度等级。

### 6.4 Handoff / Consumption

代表一方交付、另一方消费：
- 生产者；
- 接收者；
- 交付物；
- 接收方检查要求；
- 采用、拒绝、退回或待决；
- 反馈内容和下一步；
- 与前一轮执行及候选的关系。

这四类信息共同支持从 Issue 时间线重建一次协作过程。它们不要求在首期变成四张数据库表。

## 7. 如何避免错误提炼

| 常见错误 | 为什么错误 | 正确处理 |
|---|---|---|
| 将一次成功路径直接生成 SOP | 不能证明可重复 | 收集多个独立 Episode，比较共同结构和例外 |
| 把 Leader 每次的所有操作都编进流程 | 其中包含临时判断和噪声 | 只保留有稳定价值的交接、检查和依赖 |
| 把具体 Agent ID 固定进 SOP | 无法跨项目和成员复用 | 用能力角色，运行时解析执行主体 |
| 把出现频率当作必需条件 | 高频不等于必要 | 分析工作条件、失败案例和反例 |
| 只收集成功案例 | 无法提炼异常路径 | 同时分析失败、返工、接管和人工介入 |
| 把成员自述当成实际执行事实 | 可能没有真实执行或交付 | 区分自述、宿主观察、工具回执和接收方确认 |
| 将完整聊天记录输入模型总结 | 隐私、噪声和上下文污染风险 | 先形成结构化事实与必要证据，再做提炼 |
| 发现重复就自动发布 | 可能把错误方法规模化 | 只生成候选，进入后续验证和审核 |

## 8. 第一、第二阶段的研究结论

### 8.1 第一阶段的产出

不是 SOP，而是**SOP 发现候选**：

- 哪一类工作反复出现；
- 共同目标是什么；
- 重复出现哪些阶段和协作关系；
- 哪些角色组合经常使用；
- 哪些输入、产物和检查稳定出现；
- 哪些例外反复发生；
- 为什么值得进一步提炼。

### 8.2 第二阶段的产出

不是直接发布的 SOP，而是**结构化 SOP Candidate**：

- 名称和目标；
- 适用范围与不适用条件；
- 证据来源和代表性 Episode；
- 角色能力；
- 输入和产物契约；
- 必需步骤和条件步骤；
- 依赖、并行与汇合关系；
- 验证和人工决定；
- 失败、返工和升级路径；
- 尚未确认的假设。

候选必须保留来源证据，不能只留下 AI 总结后的漂亮流程图。

## 9. 对 AgentPlatform 的阶段性设计启发

1. **从 Issue 协作中观察。** 优先读取 Issue 上的委托、评论、Run、交付以及 Runtime 能实际回报的事实。
2. **围绕分工与结果提炼方法。** 对比 Main Bot 如何选择工具、分配工作、处理 Worker 的反馈，找出在不同 Issue 中能复现的做法。
3. **观察和提炼分离。** 原始工作事实先被保存；分析过程再将其转成 Episode、共同结构和候选流程。
4. **不要求每个 Issue 都产出候选。** 大多数工作只需要正常完成；只有出现稳定重复模式或明确改进价值时才进入提炼。
5. **候选 SOP 必须保留证据和反例。** 不能只展示成功样本，也要说明什么条件下不适用。
6. **先抽象工作方法，再映射到执行资产。** 不从 Session、Agent ID、Runtime 或机器路径直接生成流程定义。
7. **Coordinator 参与发现，但不独占固化权。** Agent 可以提出候选，维护者决定是否进入后续验证和发布。
8. **动态协作仍然是默认能力。** SOP 是稳定方法的固化，不应反过来要求所有 Issue 先经过 SOP。

## 10. 下一步研究问题

第一、第二阶段仍有一些需要进一步深入的地方：

- 多个 Episode 如何按工作目标和上下文聚类，而不只是按标题或标签相似度聚类？
- 如何识别一条流程的稳定骨架与可变分支？
- 如何发现“反复绕过某 SOP”意味着 SOP 过时、适用范围错误，还是 Agent 自主判断合理？
- 如何处理不同 Coordinator 对同类问题采取不同但都有效的策略？
- 如何评价一种协作方法的迁移性，而不把特定团队成员的能力优势误认为流程本身有效？
- 何种证据足以将一个模式从观察候选提升为 SOP Candidate？
- 如何在不采集私有思维链、不侵犯成员本地隐私的情况下保留足够的提炼依据？

这些问题应在下一轮专题中继续研究，之后再进入第三阶段的固化与验证设计。

## 11. 源码依据

### Multica
- [Squad Leader Protocol](https://github.com/multica-ai/multica/blob/main/server/internal/handler/squad_briefing.go)
- [Issue Trigger](https://github.com/multica-ai/multica/blob/main/server/internal/handler/issue_trigger.go)
- [Issue Trigger Service](https://github.com/multica-ai/multica/blob/main/server/internal/service/issue_trigger.go)
- [Daemon Claim / Briefing Injection](https://github.com/multica-ai/multica/blob/main/server/internal/handler/daemon.go)
- [Comment Trigger](https://github.com/multica-ai/multica/blob/main/server/internal/handler/comment.go)
- [Squad Types](https://github.com/multica-ai/multica/blob/main/packages/core/types/squad.ts)

### LoopForge
- [Assistant Activity Event](https://github.com/Tencent/LoopForge/blob/main/internal/domain/assistant.go)
- [Subagent Integration](https://github.com/Tencent/LoopForge/blob/main/internal/httpapi/assistant_subagents.go)
- [Activity Reconstruction](https://github.com/Tencent/LoopForge/blob/main/chatbot/src/activity.js)
- [Conversation Workspaces](https://github.com/Tencent/LoopForge/blob/main/docs/conversation-workspaces.md)
