# 整体系统架构与模块边界

## 1. 架构目标与组织原则

AgentPlatform 将团队成员、项目、Issue、Agent 与成员本地 Runtime 连接成一套协作系统。成员在项目中承担工作，按自己的授权使用本地 Agent 环境；平台维护共享工作事实、责任交接、受托流程、执行记录、交付证据和可复用改进。

本架构把既有五项职责收敛为可实现的模块边界。模块是业务职责和事实归属边界，不预设独立服务、数据库、进程或部署单元。

1. **一个协作核心。** Project 与 Issue 是团队工作的组织入口和业务归属；Issue 维护目标、责任、决定和完成状态。
2. **执行不等于协作。** Issue 决定谁对工作负责；SOP 只管理明确委托的流程范围；Run 记录实际受管执行。
3. **中心不接管成员电脑。** 中心负责授权、派发、协调和接收回执；实际宿主、代码副本、Session、工具调用和未共享内容留在成员本机。
4. **复用底座，不复制控制面。** Multica 继续提供 Issue、项目工作流、指派、Squad、Run、Runtime、Daemon、Backend、Session 与原生 Usage 等协作执行能力。AgentPlatform 在其上补足跨层业务语义和缺失能力，不另建平行 Issue、Run 或 Runtime 控制体系。
5. **扩展按需参与。** 团队 Wiki、项目资料、代码 Wiki、评测和改进不成为每项工作的必经阶段；由当前工作需要触发。
6. **事实单一归属。** 各模块维护自己拥有的事实，其他模块通过引用、命令和事件协作。工作台与分析视图不成为第二权威数据源。
7. **五层是职责视角。** 它们可以在同一中心应用或模块中协作，不等于五个服务，更不构成严格串行流水线。

## 2. 整体系统架构

~~~mermaid
flowchart TB
  subgraph People["团队参与者与工作入口"]
    Member["成员"]
    Agent["Agent"]
    Squad["Squad / Leader"]
    UI["统一工作台"]
  end
  subgraph Center["中心协作平台 · 权威共享事实"]
    Org["组织与项目范围"]
    Work["工作协作核心<br/>Project / Issue / Decision"]
    Method["方法与上下文<br/>Skill / Rule / Playbook / SOP Definition"]
    Flow["受托流程编排<br/>SOP Execution / Node Activation"]
    Delivery["交付与证据<br/>Artifact / Candidate / Evidence / Delivery"]
    Insight["度量、评价与改进<br/>Usage / Evaluation / Finding / Proposal / Release"]
    Read["工作台查询与视图"]
    Multica["Multica 原生协作与执行底座<br/>Issue / Assignment / Workflow / Squad / Run / Runtime Registry / Usage"]
  end
  subgraph Local["成员本地执行环境"]
    Daemon["Daemon"]
    Adapter["Host Backend / Adapter"]
    Runtime["成员授权的 Runtime"]
    Session["宿主 Session / Agent Process"]
    Workspace["工作副本 / 文件 / 工具"]
    Observation["宿主观察与本地用量"]
  end
  subgraph Sources["外部权威来源"]
    Repo["代码仓与工程资源"]
    Docs["飞书 / 外部文档 / 团队 Wiki"]
    CodeWiki["项目代码 Wiki"]
    Tools["MCP / Plugins / 项目服务"]
  end
  Member --> UI
  Agent --> UI
  Squad --> UI
  UI --> Read
  Read --> Work
  Org --> Work
  Work <--> Multica
  Method --> Work
  Work -->|"按需委托"| Flow
  Flow -->|"就绪节点请求原派发"| Multica
  Work -->|"直接派发"| Multica
  Multica -->|"受授权安排"| Daemon
  Daemon --> Adapter --> Runtime --> Session
  Session <--> Workspace
  Tools <--> Session
  Repo --> Method
  Docs --> Method
  CodeWiki --> Method
  Method -->|"选版与权限过滤后的上下文"| Daemon
  Session -->|"结果、制品、可观察事实"| Daemon
  Observation --> Daemon
  Daemon -->|"Run 回执 / Usage / Artifact"| Multica
  Multica --> Delivery
  Delivery -->|"当前工作消费"| Work
  Delivery -->|"按需评价"| Insight
  Insight -->|"审核发布、项目采用"| Method
  Insight --> Read
  Delivery --> Read
  Work --> Read
~~~

图中中心协作与 Multica 的关系是逻辑职责关系，不表示必须把 Multica 拆成独立部署服务。产品实现应优先复用其原生写入入口和数据模型。

## 3. 核心模块及职责边界

### 3.1 模块总表

| 模块 | 维护的权威事实 | 主要输入 | 主要输出 / 协作者 |
|---|---|---|---|
| A. 组织与项目范围 | Team、Project、成员参与关系、项目配置、资源授权范围 | 成员与项目管理动作 | Work、Capability、Runtime 授权 |
| B. 工作协作核心 | Issue、Work Agreement、负责人、业务决定、项目阶段与交接 | 工作发起、评论、指派、决定 | Context、Workflow、Execution、Delivery |
| C. 方法与上下文 | 资产定义与版本、适用范围、项目采用、来源引用、选择与投递记录 | 团队 / 项目维护、Issue 约定、资料来源 | 执行输入、SOP 定义、评价规则 |
| D. 流程编排 | SOP Definition 的流程语义、SOP Execution、Node Activation、Node Attempt | Issue 的明确委托、节点结果、人工决定 | 对 Multica 原派发入口的执行请求、结果交还 |
| E. 执行集成 | Run 的业务扩展关联、宿主能力映射、执行契约、观察来源与覆盖 | Multica 派发、Daemon / Backend 回执 | 执行结果、Usage、Artifact、Observation |
| F. 交付与证据 | Artifact 引用、Candidate、Evidence、Delivery Record 及消费关系 | Run 回报、成员提交、检查结果 | Issue / SOP 消费、Evaluation 输入 |
| G. 度量、评价与改进 | Usage 归集视图、Evaluation、Finding、Proposal、Benchmark、Release 与效果观察 | 原生产 Run、交付证据、评价任务 | 工作判断、候选改进、已发布方法 |
| H. 工作台与查询 | 不拥有业务权威事实；维护查询投影、视图和操作入口 | 各模块的可读事实 | 成员查看状态、发起有权操作 |
| I. 来源与宿主适配 | 连接器和宿主协议的映射、同步游标、能力覆盖与来源标识 | 外部资料、代码仓、宿主协议 | C、E 的标准化输入与证据 |

A–G 是业务领域模块；H 是横向呈现；I 是横向适配。它们是逻辑模块，不预设一模块一服务。

### 3.2 模块边界的关键解释

- **组织与项目范围**只回答谁属于哪个协作范围、哪些资源可在何种范围使用。它不拥有 Issue 的工作状态，也不因为成员注册了 Runtime 就自动授权所有项目使用。
- **工作协作核心**是系统业务主线。Issue 是唯一业务工作归属。成员、Agent 或 Squad 可以承担责任或参与工作；工作负责人决定自主推进、邀请协助、拆分子 Issue，或委托 SOP。Project Workflow 管项目阶段与责任交接，不替代 SOP。
- **方法与上下文**把可复用方法与本次工作实际使用分开。Skill、Rule、Playbook、SOP、知识和工具配置有自己的版本及适用范围；项目采用、本项选择、实际投递、宿主加载和实际使用分别留证。它不负责启动 Run。
- **流程编排**只管理 Issue 明确委托的范围。Squad Leader 是受托协作主体，可以自主分析和组织 Agent；SOP 是可执行的依赖、节点、核验、返工和出口定义。Squad 不必经过 SOP；SOP 也不替代 Squad Leader 对未知问题的判断。
- **执行集成**把中心的授权安排交给 Multica 原生 Run / Daemon 链。Backend 适配具体宿主。Runtime 是执行资源，Agent 是执行主体，Session 是宿主连续性，三者不能合并。成员的私人活动只有在授权共享且来源可识别时才进入平台记录。
- **交付与证据**将交付了什么和凭什么相信分开。Artifact 指向具体版本，Candidate 固定交付组合，Evidence 支持具体事实，Delivery Record 汇总接收方消费结果。生产方报告成功不代表接收方接受。
- **度量、评价与改进**消费原 Run、Usage、Candidate 和 Evidence。成本首先归属实际生产 Run；评价、Benchmark 和改进自身的执行消耗另行归集。Finding 可先帮助当前 Issue 修正，只有具有跨工作价值时才进入提案、对照、审核和发布。发布后由项目采用，后续工作记录实际使用和效果。
- **工作台与查询**是统一入口而不是新业务核心。展示状态、等待原因和下一责任人；所有写操作回到拥有该事实决定权的模块或 Multica 原生入口。

## 4. 五层职责与模块映射

五层表达的是系统需要持续完成的五类工作，不是模块调用顺序，也不要求每个 Issue 都经过全部层。

| 五层职责 | 主要模块 | 权威事实 | 主要依赖 |
|---|---|---|---|
| 第一层：工作协作 | A 组织范围、B 工作协作 | Team / Project / Issue / Decision / Project Workflow | 组织身份、权限、项目配置 |
| 第二层：能力与上下文 | C 方法与上下文、I 来源适配 | 资产版本、项目采用、工作约定引用、ContextReceipt | Issue、项目范围、成员读权、来源系统 |
| 第三层：流程编排 | D 流程编排 | SOP Definition / Execution / Node Activation / Attempt | Issue 委托、能力版本、交付消费契约 |
| 第四层：执行与回报 | E 执行集成、I 宿主适配、Multica | Run / Runtime / Session / Observation / Usage 原始记录 | Issue 或 SOP 授权、上下文、Runtime 资格 |
| 第五层：度量、评价与改进 | F 交付证据、G 度量改进 | Artifact / Candidate / Evidence / Delivery / Evaluation / Release | Run、工作约定、检查标准、授权与来源 |

交付与证据 F 是第四层结果进入业务消费和第五层评价的共同边界，不是独立的第六条工作流。工作台 H 横跨五层读取与呈现，但不拥有任何一层的业务决定权。

## 5. 中心协作与成员本地 Runtime 边界

~~~mermaid
flowchart LR
  subgraph Central["中心协作域"]
    Issue["Issue / 负责人 / 决定"]
    Grant["委托与执行授权"]
    Context["版本化上下文引用"]
    Dispatch["Multica 派发 / Run"]
    Receive["结果接收与交付归集"]
    Usage["Usage / 评价 / 改进"]
  end
  subgraph Member["成员本地 Runtime 域"]
    Daemon["Daemon"]
    Host["Backend / Host Adapter"]
    Agent["Agent / 宿主进程"]
    Session["Session"]
    Files["工作副本 / 本地文件"]
    Tools["本地工具 / MCP / IDE"]
    LocalObs["宿主观察 / 本地计量"]
  end
  Issue --> Grant --> Dispatch
  Context --> Dispatch
  Dispatch --> Daemon --> Host --> Agent
  Agent <--> Session
  Agent <--> Files
  Agent <--> Tools
  Agent --> LocalObs
  LocalObs --> Daemon
  Agent --> Daemon
  Daemon --> Receive --> Usage
  Receive --> Issue
~~~

### 5.1 中心负责

- 组织、项目、Issue、责任、讨论、业务决定与项目工作流。
- 受托范围、执行身份、资源资格和本次执行契约。
- Run 的派发安排、中心可观察到的状态和收到的回执。
- 资产发布、项目采用、版本引用和权限范围。
- 交付版本、消费关系、评价记录、Usage 汇总与改进发布。
- 成员离线时仍可处理的共享协作事实、已共享材料和责任交接。

### 5.2 本地 Runtime 负责

- 成员授权提供的 Host、Runtime、Daemon 与本地 Backend。
- Agent 宿主进程、Session、实际模型输入、工具调用和工作副本。
- 本地凭据、私有历史、未提交修改及未选择共享的资料。
- 宿主实际提供的消息、工具、退出、文件和用量观察。
- 断连期间的本地状态与待回报记录；恢复连接后按原 Run、当前授权和共享选择交回。

### 5.3 边界交接规则

1. 中心派发的是有身份、有范围、有输入输出要求的授权安排，不是把中心进程远程执行在成员电脑上。
2. Daemon 领取后仍需核对本地 Runtime、宿主和当前授权；派发成功不代表实际启动。
3. Context 的选择、准备、投递、加载和使用是不同证据层级；中心不得把投递回执描述成模型已读取。
4. 本地执行回报关联原 Run、Issue、SOP 节点及本轮激活；Session ID 不能替代这些身份。
5. Runtime 断联不应使 Issue 失效。中心可以继续讨论、改派、作决定和使用已共享交付；涉及原机写入的接续须先核对旧进程、写入隔离和副作用。
6. 本地无法提供的用量或活动证据保持未知，不用估算值伪装成真实成本。
7. 成员主动工作可按授权共享范围关联 Issue；不能证明来源、身份或归属时，保留为成员说明或未知观察。

## 6. 组织与资源关系贯通

~~~mermaid
flowchart TB
  Team["Team"]
  Project["Project"]
  Member["Member"]
  Agent["Agent Identity"]
  Squad["Squad"]
  Leader["Squad Leader"]
  Runtime["Member-owned Runtime"]
  Host["Host / Backend"]
  Issue["Issue"]
  SOP["SOP Execution"]
  Run["Run"]
  Session["Host Session"]
  Team --> Project
  Team --> Member
  Team --> Squad
  Project -->|"成员参与 / 项目权限"| Member
  Project -->|"项目采用配置"| Agent
  Squad -->|"由 Leader 协调"| Leader
  Squad -->|"组织成员 Agent"| Agent
  Member -->|"拥有 / 授权"| Runtime
  Runtime --> Host
  Host -->|"提供宿主能力"| Agent
  Issue -->|"负责人可为"| Member
  Issue -->|"负责人可为"| Agent
  Issue -->|"负责人可为"| Squad
  Issue -->|"按需委托"| SOP
  Issue -->|"直接执行或派发"| Run
  SOP -->|"就绪节点经原派发链"| Run
  Agent -->|"实际执行主体"| Run
  Runtime -->|"实际执行资源"| Run
  Run -->|"宿主连续性"| Session
~~~

### 6.1 对象关系语义

| 对象 | 所属 / 关联关系 | 不应采用的建模方式 |
|---|---|---|
| Team | 组织成员、项目、团队级能力与 Squad | 不直接成为 Issue 的执行者 |
| Project | 工作范围、参与成员、工程资源、项目配置与采用资产 | 不复制团队成员身份或成为单项工作 |
| Member | 人员身份、项目参与、Runtime 所有权、业务决定权 | 不等于 Agent 或 Runtime |
| Agent | 可被指派 / 邀请的执行主体，可在不同项目配置中采用 | 不与某台机器或某个 Session 一一绑定 |
| Squad | 可被指派为 Issue 负责方的协作主体，由 Leader 组织 Agent 参与 | 不作为所有 Issue 的必经调度器 |
| Runtime | 成员拥有并授权的执行资源，声明宿主、Backend 和能力覆盖 | 不成为业务负责人，也不等同于 Agent |
| Host / Backend | 提供实际宿主协议、工具入口与运行能力 | 不决定 Issue 的业务状态 |
| Session | 宿主内连续对话 / 线程身份，可被多个 Run 先后引用 | 不作为跨 Issue 的工作主键 |
| Run | 一次实际受管执行，关联工作归属、Agent、Runtime、Session 和派发来源 | 不由 Agent 或 Runtime 静态拥有 |

成员、Agent、Squad 的责任身份与 Runtime 资源授权必须分开判断。一个 Agent 可以在不同获准 Runtime 上执行；一个 Runtime 可以在授权范围内承载多个 Agent 或宿主；同一 Session 也可能跨越多个 Run。具体能否共享和接续，由宿主能力、授权与实际回执决定。

## 7. Multica、TeamAI、LoopForge 的融合关系

### 7.1 三者不是三套平行平台

| 来源 | 在 AgentPlatform 中承担的角色 | 采用的机制 | 不引入的重复能力 |
|---|---|---|---|
| Multica | 协作与受管执行底座 | Issue、Assignee、评论协助、Project Workflow、Squad、Run、Runtime、Daemon、Backend、Session、原生 Usage | 不另建 Issue 系统、任务队列、Runtime 注册与第二套派发控制面 |
| TeamAI | 方法资产与 Agent 工作过程增强 | 项目作用域、Skill / Role / Principles、步骤驱动、Driver 协议、Observation 与知识资产治理经验 | 不把 Git 独立仓、CLI 或 TeamAI 的完整运行体系作为平台前置依赖 |
| LoopForge | 稳定流程与交付质量增强 | SOP 依赖图、节点就绪、结果消费、条件判断、定向返工、执行评测与改进闭环 | 不另建与 Multica 冲突的 Issue / Run / Runtime 或第二个总协调 Agent |

~~~mermaid
flowchart TB
  Work["Multica · Issue / Project Workflow / Squad"]
  Method["TeamAI 思路 · 项目方法 / Skill / Role / Driver"]
  SOP["LoopForge 思路 · SOP 依赖 / 节点核验 / 定向返工"]
  Run["Multica · Run / Runtime / Daemon / Backend"]
  Evidence["统一交付证据与 Usage"]
  Improve["LoopForge + TeamAI 思路<br/>Evaluation / Benchmark / 改进候选"]
  Release["审核发布 / 项目采用"]
  Work -->|"负责人自主规划或明确委托"| SOP
  Work -->|"工作约定与责任"| Method
  Method -->|"选版与上下文投递"| Run
  SOP -->|"就绪节点请求执行"| Run
  Run --> Evidence
  Evidence -->|"当前工作消费"| Work
  Evidence -->|"按需评价"| Improve
  Improve --> Release
  Release --> Method
  Release --> Work
~~~

### 7.2 关键融合约束

- Multica 的 Issue 是工作主线，Squad 是否参与由 Issue 的负责人安排决定。
- Squad Leader 在授权范围内自主规划；若遇到稳定且可定义的步骤，可以调用局部 SOP，不再由另一个总规划 Agent 重复规划。
- TeamAI 的 Driver 只负责约定步骤的领取、确认和报告；真实执行仍由 Multica 原 Run / Runtime 链承载。
- LoopForge 的节点判断、结果消费和返工作用于 SOP Execution / Node Activation，不另建任务身份。
- 执行计量沿原生产 Run 归集。评价和 Benchmark 产生自己的执行记录与成本，不回写污染生产执行成本。
- 评测结果先服务当前交付；跨工作方法改进必须有候选版本、可比样本、成功标准、审核和发布。
- 发布的 Skill、Rule、Playbook、SOP 或流程配置由项目采用；后续 Issue 记录实际使用版本和结果。

## 8. 团队 Wiki、项目资料与代码 Wiki 的扩展接入

### 8.1 它们属于资料与能力域，不是协作主线模块

| 能力 | 主要回答的问题 | 权威来源 | 与协作主线的连接 |
|---|---|---|---|
| 团队 Wiki | 团队共识、跨项目经验、规范和方法是什么 | 团队维护的条目及其来源授权、修订 | 作为有版本、有范围的 Knowledge / Rule / Playbook 被项目采用或 Issue 引用 |
| 项目资料 | 当前项目的 PRD、接口约定、评审纪要和业务资料是什么 | 飞书等原始文档系统，或明确标注来源的导入快照 | Issue / Context 引用具体文档修订、章节和适用范围 |
| 项目代码 Wiki | 指定仓库与代码修订的模块、调用关系和实现事实是什么 | 工程仓库、提交、文件位置与代码索引 | 按 Project、仓库和提交基准检索，结果以引用进入 Issue / Run 上下文 |

~~~mermaid
flowchart LR
  Sources["飞书 / 文档 / Git 仓 / 项目材料"]
  Ingest["来源连接与索引适配"]
  Knowledge["团队 Wiki / 项目资料 / 代码 Wiki"]
  Scope["项目范围、版本、权限过滤"]
  Context["Context 选择与投递"]
  Issue["Issue / Run"]
  Sources --> Ingest --> Knowledge
  Knowledge --> Scope --> Context --> Issue
  Issue -->|"引用、反馈、修订建议"| Knowledge
~~~

- 来源系统继续维护原文；Wiki 组织可检索说明、关联关系、适用范围和来源定位。
- 代码 Wiki 绑定明确仓库与提交，不把生成的解释当作比代码更高的事实来源。
- 普通 Issue 直接使用已有文档和代码仓即可，不要求先建设 Wiki。
- 检索命中必须保留来源、修订、位置、适用范围和读权限；内容变化只影响受影响的引用与后续投递，不静默改写历史执行上下文。
- 三种资料能力可以独立启用和演进，但统一通过 Context Contract 向协作主线提供材料；不要求统一底层存储或统一索引产品。

## 9. 成本、评测与自改进如何自然接入主流程

~~~mermaid
flowchart TB
  Issue["Issue 工作约定"]
  Run["生产 Run"]
  Delivery["Candidate / Artifact / Evidence"]
  Consume["Issue 或 SOP 消费结果"]
  Finding["当前问题 / Finding"]
  Evaluation["按需 Evaluation"]
  Proposal["跨工作 Improvement Proposal"]
  Benchmark["固定样本与标准的 Benchmark"]
  Release["审核发布 Release"]
  Adoption["项目采用"]
  Next["后续 Issue 固定实际使用版本"]
  Outcome["观察真实质量与成本效果"]
  Issue --> Run --> Delivery --> Consume
  Consume -->|"缺陷或缺项"| Finding
  Finding -->|"本项修正"| Issue
  Delivery -->|"有评价价值时"| Evaluation
  Run -->|"评价输入"| Evaluation
  Evaluation --> Finding
  Finding -->|"有跨工作价值时"| Proposal
  Proposal --> Benchmark --> Release --> Adoption --> Next --> Outcome
  Outcome -->|"形成新证据"| Proposal
~~~

### 9.1 三种不同粒度

1. **本次交付反馈。** 发现问题后，当前负责人或受托 SOP 决定修正、返工、等待或接受例外。无需先建立改进项目。
2. **单次执行评价。** 对 Run、Candidate 或交付做按需评价，结果作为当前负责人和维护者的证据。评价不是业务验收。
3. **跨工作自改进。** 重复出现或有推广价值的问题形成 Proposal；固定候选、依赖、Benchmark 样本、评价器和成功标准，比较后由维护者审核发布；项目决定是否采用，后续工作验证实际效果。

### 9.2 成本归属原则

- 生产活动的 Usage 归属实际生产 Run，并可按 Issue、父项、Project、Squad 等关系汇总；不得因同一执行被多个系统观察而重复计费。
- 原生供应商单位分别记录，例如 Token、Credits、请求数或其他原生计量；只有来源真实上报才展示数值。
- Runtime 未上报的费用或无法映射的活动保持未知，不从耗时、模型名或订阅套餐推算。
- Evaluation、Benchmark、知识整理和改进任务有自己的执行来源与消耗，不混入生产 Issue 的成本。
- 成本统计模块读取原始用量事实并生成汇总，不反向改写 Run 终态或 Issue 状态。

## 10. 模块依赖与禁止越界

~~~mermaid
flowchart TB
  Org["A 组织与项目范围"]
  Work["B 工作协作核心"]
  Context["C 方法与上下文"]
  Workflow["D 流程编排"]
  Execution["E 执行集成 / Multica"]
  Delivery["F 交付与证据"]
  Improve["G 度量评价与改进"]
  Workbench["H 工作台与查询"]
  Adapters["I 来源与宿主适配"]
  Org --> Work
  Org --> Context
  Org --> Execution
  Work --> Context
  Work --> Workflow
  Work --> Execution
  Context --> Workflow
  Context --> Execution
  Workflow -->|"仅就绪节点"| Execution
  Execution --> Delivery
  Delivery --> Work
  Delivery --> Workflow
  Delivery --> Improve
  Improve -->|"审核发布与项目采用"| Context
  Improve -->|"效果反馈"| Work
  Adapters --> Context
  Adapters --> Execution
  Workbench -.->|"只读投影 / 有权命令入口"| Org
  Workbench -.-> Work
  Workbench -.-> Context
  Workbench -.-> Workflow
  Workbench -.-> Execution
  Workbench -.-> Delivery
  Workbench -.-> Improve
~~~

### 10.1 依赖方向

- 组织与项目范围提供身份、范围和授权基础；不依赖工作台或评价模块。
- 工作协作核心是业务入口，能引用能力、委托 SOP 或请求 Run；不直接控制宿主内部进程。
- 方法与上下文依赖组织范围和 Issue 工作约定；不直接改变 Issue 状态或启动执行。
- 流程编排依赖 Issue 的明确委托、固定 SOP 版本和交付契约；只能通过原派发入口请求执行。
- 执行集成依赖有效授权与上下文引用；只报告执行事实，不决定业务验收。
- 交付与证据消费执行结果；不能替生产方制造执行事实，也不能替 Issue 决定接受。
- 度量评价与改进读取生产记录和交付证据；不能成为生产派发的必经中间层。
- 工作台不直接写其他模块的存储，不在 UI 中重实现业务规则；命令交给权威入口。
- 来源与宿主适配只负责连接、协议转换和来源证据；不拥有 Issue、Candidate 或 Release 的业务决定权。

### 10.2 禁止的直接依赖

| 禁止关系 | 原因 | 正确协作方式 |
|---|---|---|
| Runtime / Backend 直接改变 Issue 业务状态 | 本地执行资源不拥有业务决定权 | 回报原 Run 与交付，由 Issue 有权入口推进 |
| SOP 直接越权修改 Issue 目标、负责人或验收 | SOP 仅拥有受托范围 | 请求 Issue 决定或交还负责人 |
| Agent / Session 作为工作主键 | 宿主连续性与业务归属不同 | 用 Issue、Run、Node Activation 关联 |
| 工作台直接修改 Run / Issue 的底层状态 | 绕开权威写入与并发校验 | 调用 Multica 或对应领域命令入口 |
| Evaluation 直接完成 Issue 或发布资产 | 评价结论不是业务决定或资产审核 | 有权成员在对应入口决定 |
| Wiki 直接覆盖 PRD / 代码等来源正文 | Wiki 不是外部权威来源 | 维护原来源，Wiki 更新索引与引用 |
| 观察器直接创建新的生产 Run | 多源观察会造成执行与成本重复 | 将 Observation 映射到已知 Run；无法证明归属时独立标记 |
| 项目配置直接改变在途工作已固定版本 | 破坏历史可追溯与执行一致性 | 显式决定迁移范围并重验受影响部分 |

## 11. 尚未解决的架构决策

以下事项需要后续设计或源码 / 运行证据，不在本阶段通过假设强行定案。

| 编号 | 未决问题 | 为什么影响架构 | 下一步需要回答 |
|---|---|---|---|
| D1 | 组织、项目、Agent、Squad 与成员身份在 Multica 中的映射边界 | 决定授权和跨项目复用 | 哪些原生实体可直接复用，哪些需增加关系或产品配置 |
| D2 | Runtime 的所有权、共享授权、可见范围与并发容量 | 决定跨成员派发与故障接续 | Runtime 能否被多个项目 / Agent 使用，授权撤回如何影响在途 Run |
| D3 | 多 Runtime、多宿主与 Agent 的选择策略 | 决定同一 Agent 在不同执行环境的可移植性 | 选择依据、优先级、故障转移和成员确认边界 |
| D4 | 逻辑模块与实际部署边界 | 决定工程组织与数据事务边界 | 首期是否沿 Multica 单体扩展，哪些能力需要独立进程或存储 |
| D5 | 跨模块写入、事件投递、幂等与恢复的实现映射 | 决定状态一致性和故障恢复 | 逐项映射 Multica 现有事务、队列、回执与缺口，不预设新总线 |
| D6 | Artifact / Candidate / Delivery 与 Multica 原生附件和仓库交付的映射 | 决定交付版本、检查和验收的权威引用 | 识别原生附件 ID、提交基准、候选组合及消费记录的最小扩展 |
| D7 | Usage 原生单位、Credits、Stage 与多源观察的统一归集 | 决定成本覆盖率和去重 | 逐宿主确认上报字段、原生身份、修正语义；缺失值保持未知 |
| D8 | TeamAI Driver 与各宿主的运行时支持范围 | 决定步骤协议能否跨 Codex、Claude Code、Qoder、CodeBuddy | 分宿主确认领取、确认、报告、取消与恢复能力 |
| D9 | SOP 与 Squad 同时参与一个 Issue 时的协调权表达 | 决定是否发生双重编排 | 明确 Leader 的总协调范围与 SOP 的局部受托范围及冲突交还规则 |
| D10 | Wiki、飞书、代码索引的连接器与索引部署策略 | 决定检索时效、权限和维护成本 | 先确定来源协议、修订定位、权限过滤和按需启用边界，再选底层实现 |
| D11 | Evaluation / Benchmark 的触发策略和资源预算 | 决定是否干扰生产工作及成本 | 哪些情况自动建议评价，哪些必须由维护者发起，实验隔离如何落实 |
| D12 | 工作台查询投影与权威数据的更新一致性 | 决定状态展示是否可信 | 明确投影延迟、版本标识、过期提示及写入后回读语义 |

## 12. 架构验收标准

本架构进入详细技术设计前，应能对以下问题给出一致答案：

- 一项工作只有一个 Issue 作为业务归属；任何 Run、SOP、交付和评价都能追溯到来源工作或明确的独立活动。
- 成员、Agent、Squad 的责任身份与 Runtime、Session 的执行资源身份没有混淆。
- 负责人自主推进、邀请协助、子 Issue 分工、Squad 负责和 SOP 委托可以按需组合，不存在默认双重协调者。
- 中心协作不依赖某一成员的 Runtime 在线；本地执行失联不会抹掉共享工作事实。
- 任一执行请求都沿 Multica 原派发链，能核对授权、实际启动、结果、取消和迟到回报。
- 方法和资料从来源到选择、投递、使用均保留相应证据；没有证据的层级保持未知。
- 交付、证据、评价、验收、发布和采用是不同事实，候选换版不污染旧结果。
- 团队 Wiki、项目资料和代码 Wiki 可以独立启用，不成为普通协作的基础设施前置条件。
- 成本归属原生产 Run，多源观察不重复计量；评价与 Benchmark 的成本独立归集。
- 工作台只呈现和路由，不复制权威状态机与业务规则。

本架构定义模块边界与协作关系，不定义数据库表、API、微服务拆分、页面布局或具体部署拓扑。上述未决项应在后续技术设计中逐项依据 Multica 真实实现和宿主能力收敛。
