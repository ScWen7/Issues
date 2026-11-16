# 整体系统架构与模块边界

## 1. 架构目标与组织原则

AgentPlatform 将团队成员、项目、Issue、Agent 与成员本地 Runtime 连接成一套协作系统。成员在项目中承担工作，按自己的授权使用本地 Agent 环境；平台维护共享工作事实、责任交接、受托流程、执行记录、交付证据和可复用改进。

本架构把既有五项职责收敛为可实现的模块边界。模块是业务职责和事实归属边界，不预设独立服务、数据库、进程或部署单元。

1. **一个协作核心。** Project 与 Issue 是团队工作的组织入口和业务归属；Issue 维护目标、责任、决定和完成状态。
2. **执行不等于协作。** Issue 决定谁对工作负责；SOP 只管理明确委托的流程范围；Run 记录实际受管执行。
3. **中心不接管成员电脑。** 中心负责授权、派发、协调和接收回执；实际宿主、代码副本、Session、工具调用和未共享内容留在成员本机。
4. **复用底座，不复制控制面。** Multica 继续提供 Issue、项目工作流、指派、Issue Wakeup、Run、Runtime、Daemon、Backend、Session 与原生 Usage 等协作执行能力。AgentPlatform 在其上补足跨层业务语义和缺失能力，不另建平行 Issue、Run 或 Runtime 控制体系。
5. **扩展按需参与。** 团队 Wiki、项目资料、代码 Wiki、评测和改进不成为每项工作的必经阶段；由当前工作需要触发。
6. **事实单一归属。** 各模块维护自己拥有的事实，其他模块通过引用、命令和事件协作。工作台与分析视图不成为第二权威数据源。
7. **五层是职责视角。** 它们可以在同一中心应用或模块中协作，不等于五个服务，更不构成严格串行流水线。

## 2. 整体系统架构

~~~mermaid
flowchart TB
  subgraph People["团队参与者与工作入口"]
    Member["成员"]
    Agent["Agent · 协调或执行"]
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
    Multica["Multica 原生协作与执行底座<br/>Issue / Assignment / Workflow / Wakeup / Run / Runtime Registry / Usage"]
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
  UI -->|"创建或关联 Issue"| Work
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
  Work -->|"成员提交所选版本与署名说明"| Delivery
  Delivery -->|"节点核对本轮候选与证据"| Flow
  Flow -->|"交还出口或请求决定"| Work
  Delivery -->|"当前工作消费"| Work
  Delivery -->|"按需评价"| Insight
  Insight -->|"资产维护者审核发布方法"| Method
  Insight -->|"有权成员在项目内采用配置变更"| Org
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
- **工作协作核心**是系统业务主线。Issue 是唯一业务工作归属。成员可亲自推进，或指派一个 Agent 并把持续协调权交给它。这个 Agent 作为 Main Bot 自行执行、邀请 Worker、拆分子 Issue 或委托 SOP。Project Workflow 管项目阶段与责任交接，不替代 SOP。
- **方法与上下文**把可复用方法与本次工作实际使用分开。Skill、Rule、Playbook、SOP、知识和工具配置有自己的版本及适用范围；项目采用、本项选择、实际投递、宿主加载和实际使用分别留证。它不负责启动 Run。
- **流程编排**只管理 Issue 明确委托的范围。本次 SOP Execution 按固定定义判断节点就绪、核验、返工和出口。工作负责人或受托 Main Bot 接回其结果，并负责 SOP 范围以外的分工和决定请求。
- **执行集成**把中心的授权安排交给 Multica 原生 Run / Daemon 链。Backend 适配具体宿主。Runtime 是执行资源，Agent 是执行主体，Session 是宿主连续性，三者不能合并。成员的私人活动只有在授权共享且来源可识别时才进入平台记录。
- **交付与证据**将交付了什么和凭什么相信分开。Artifact 指向具体版本，Candidate 固定交付组合，Evidence 支持具体事实，Delivery Record 汇总接收方消费结果。生产方报告成功不代表接收方接受。
- **度量、评价与改进**消费原 Run、Usage、Candidate 和 Evidence。成本首先归属实际生产 Run；评价、Benchmark 和改进自身的执行消耗另行归集。当前 Issue 可依据发现直接修正。跨工作改进经对照和审核，按对象发布方法或调整项目配置。效果从后续工作实际使用的版本和交付中核对。
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

成员提交的成果和第四层回报的执行结果，经 F 形成可交接的候选与证据，供 Issue、受托 SOP 和第五层评价分别取用。工作台 H 横跨五层读取与呈现，但不拥有任何一层的业务决定权。

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
  Team["团队 · Workspace"]
  Member["工作区成员"]
  Project["Project"]
  Issue["Issue"]
  Agent["Agent"]
  Runtime["成员的 Runtime"]
  Run["受管 Run"]
  Team --> Member
  Team --> Project
  Team --> Agent
  Project -->|"工作与适用约定"| Issue
  Member -->|"按项目读权参与或接手"| Issue
  Issue -->|"指派或邀请"| Agent
  Member -->|"机主决定共享范围"| Runtime
  Agent -->|"当前绑定"| Runtime
  Issue -->|"工作归属"| Run
  Agent -->|"执行主体"| Run
  Runtime -->|"实际领取"| Run
~~~

### 6.1 对象关系语义

成员从项目打开 Issue，先取得本人可读的工作约定和已有交付。亲自推进时，沿原 Issue 提交结果。需要调用 Agent 时，项目配置可提供适用的方法、工具及 Agent 选择，指派或一次性协助仍在原 Issue 办理。团队、成员和项目的对应关系见[核心对象模型](core-object-model.md#31-组织与参与主体)。

私有项目中的受管执行，分别核对本次发起人与 Agent 所有者的项目访问范围、发起者的 Agent 调用资格，以及所绑定 Runtime 对该 Agent 的使用授权。成员委托多个 Agent 时，每个实际执行者按自己的绑定领取工作。项目或资料来源对执行地点有要求时，只向符合本次要求的机器投递。受托 SOP 的就绪节点沿同一派发入口运行，实际宿主及 Session 按该次 Run 的回执追溯。[项目访问、调用与机器授权](../research/05-source-evidence.md#项目访问与执行资格)

换人或换机时，接手者沿原 Issue 取得送交的候选、可访问的资料及工程修订，再在自己的工作副本继续。上一个 Daemon 的目录路径只在原机解释。缺少尚未共享的修改时，能取得修改的成员可以补交；其他已具备输入的工作可以继续。[能力与上下文](03b-capability-governance.md#1-issue-的上下文) · [交付与接手](05-unified-workbench.md#交付与接手)

## 7. Multica、TeamAI、LoopForge 的融合关系

### 7.1 三个上游的分工

| 来源 | 在 AgentPlatform 中承担的角色 | 采用的机制 | 不引入的重复能力 |
|---|---|---|---|
| Multica | 协作与受管执行底座 | Issue、Assignee、评论协助、Issue Wakeup、Project Workflow、Run、Runtime、Daemon、Backend、Session、原生 Usage | 不另建 Issue 系统、任务队列、Runtime 注册与第二套派发控制面 |
| TeamAI | 方法资产与 Agent 工作过程增强 | 项目作用域、Skill / Role / Principles、步骤驱动、Driver 协议、Observation 与知识资产治理经验 | 不把 Git 独立仓、CLI 或 TeamAI 的完整运行体系作为平台前置依赖 |
| LoopForge | 稳定流程与交付质量增强 | SOP 依赖图、节点就绪、结果消费、条件判断、定向返工、执行评测与改进闭环 | 不另建与 Multica 冲突的 Issue / Run / Runtime 或第二个总协调 Agent |

~~~mermaid
flowchart TB
  Work["Multica · Project / Issue"]
  Method["TeamAI 机制 · 项目方法与获准上下文"]
  SOP["LoopForge 机制 · 受托 SOP"]
  Run["Multica · Run / 成员 Runtime"]
  Delivery["候选交付与检查证据"]
  Method -->|"本项适用的规则与资料"| Work
  Method -->|"选定版本及授权输入"| Run
  Work -->|"成员提交所选本地成果"| Delivery
  Work -->|"负责人安排受管执行"| Run
  Work -->|"委托明确的工作范围"| SOP
  SOP -->|"就绪节点沿原入口派发"| Run
  Run -->|"回报成果与来源"| Delivery
  Delivery -->|"节点按本轮尝试核验或返工"| SOP
  SOP -->|"交还出口或请求决定"| Work
  Delivery -->|"按工作约定接收或转交验收"| Work
~~~

### 7.2 关键融合约束

- Multica 的 Issue 保存工作约定和责任。成员可以从中心开工，也可从本地关联工作或事后交回获准共享的成果。接手者从同一 Issue 找到所用版本、检查结果和待决事项，按自己的权限取用。
- 工作负责人可直接推进或把稳定步骤交给 SOP。Issue 指派给 Agent 并授予持续协调权时，由该 Agent 担任 Main Bot，自行安排执行、协助、子项或 SOP。需要接续已登记的协调时，沿原生 Issue Wakeup 重读委托与结果。
- TeamAI 的 Driver 只负责约定步骤的领取、确认和报告；真实执行仍由 Multica 原 Run / Runtime 链承载。
- LoopForge 的节点判断、结果消费和返工作用于 SOP Execution / Node Activation，不另建任务身份。
- 执行计量沿原生产 Run 归集。评价和 Benchmark 产生自己的执行记录与成本，不回写污染生产执行成本。
- 当前交付的检查和评价供负责人或受托节点处理本项问题。有跨工作价值的发现才进入候选对照，按变更对象决定发布或配置生效。后续实际效果见下文第 9 节。

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
  Change["有权成员调整项目工作流或分工"]
  Next["后续 Issue 的实际使用记录"]
  Outcome["观察真实质量与成本效果"]
  Issue -->|"成员提交所选成果"| Delivery
  Issue -->|"受管执行"| Run --> Delivery
  Delivery --> Consume
  Consume -->|"缺陷或缺项"| Finding
  Finding -->|"本项修正"| Issue
  Delivery -->|"有评价价值时"| Evaluation
  Run -->|"评价输入"| Evaluation
  Evaluation --> Finding
  Finding -->|"有跨工作价值时"| Proposal
  Proposal --> Benchmark
  Benchmark -->|"方法资产通过审核"| Release
  Benchmark -->|"项目配置获准变更"| Change
  Release -->|"按项目默认或本项选择实际使用"| Next
  Change -->|"适用的工作按新配置推进"| Next
  Next --> Outcome
  Outcome -->|"有新的跨工作发现时"| Proposal
~~~

### 9.1 三种不同粒度

1. **本次交付反馈。** 发现问题后，当前负责人或受托 SOP 决定修正、返工、等待或接受例外。无需先建立改进项目。
2. **单次执行评价。** 对 Run、Candidate 或交付做按需评价，结果作为当前负责人和维护者的证据。评价不是业务验收。
3. **跨工作自改进。** 重复出现或有推广价值的问题形成 Proposal；维护者固定候选、样本和成功标准进行对照。团队方法由资产维护者审核发布，项目可设为默认，负责人也可为本项选用获准版本。工作流或分工配置由有权成员在原项目或 Issue 指明生效范围并安排在途工作。后续按实际使用的版本或配置核对质量、返工和可获知的成本。

### 9.2 成本归属原则

- 生产活动的 Usage 归属实际生产 Run，可按 Issue、父项和 Project 汇总。同一执行的多份观察使用同一计量归属。
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
  Work -->|"成员的直接交付"| Delivery
  Delivery --> Work
  Delivery --> Workflow
  Delivery --> Improve
  Improve -->|"已审核发布的方法"| Context
  Improve -->|"有权成员变更项目配置"| Org
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
- 交付与证据接收成员署名提交和受管执行结果，按具体版本交给 Issue 或受托节点，由接收方核验。
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

责任交接的生效条件、私有 Issue 接收者读权、交付提交中断后的查回，以及旧通知和项目入口回到当前 Issue 的规则，见[工作生命周期](01-unified-work-lifecycle.md#62-状态推进与负责人交接)、[统一工作台](05-unified-workbench.md#交接确认与旧入口接续)和[底座覆盖边界](governance-baseline.md#一致性与并发能力覆盖)。下表只保留仍需单独收敛的架构问题。

| 何时需要 | 编号与问题 | 要解决到什么程度 |
|---|---|---|
| 提交交付、改派或跨层派发时 | D5 写入与恢复 | 跨层恢复契约已定义稳定操作身份、权威写入与待办意图、Task 查回、结果消费回执及 unknown 对账规则。Multica 的 Issue 首次指派与 Run 入队分离，Handler 忽略 Agent 入队错误；评论保存与目标级 Worker 触发分离，Wakeup 只能唤醒已有订阅者，不能代替委派记录。SOP Node Activation / Attempt 到 Task 的绑定与结果消费由平台补齐。Wakeup 源事实与 Receipt 已在同一事务捕获，但 Receipt 可合并，不是业务命令档案。[统一恢复契约](core-consistency-concurrency.md#54-跨层操作的统一恢复契约) · [业务触发与恢复闭环](../research/d5-business-trigger-recovery.md) · [Wakeup 源码取证](../research/d5-write-recovery-evidence.md) · [底座覆盖](governance-baseline.md#一致性与并发能力覆盖) |
| **工作约定要求具名验收时** | D6 候选与成功完成 | 先有可定位的交付版本，再核对指定人按适用标准作出的有效决定，以及手动、批量和启用的 PR 自动完成入口在换版或重复提交时的结果。[候选与验收竞争](core-consistency-concurrency.md#63-candidate-与验收竞争) |
| **启用受管 Agent 时** | D2 执行等待与恢复 | 一次协助即可用到。先区分收到请求、排队、真正开工与回报。要让成员干预目录占用、取消或恢复时，再核对宿主能回报哪些原因，以及谁有权看见。[并发名额与目录](core-consistency-concurrency.md#71-runtime-与执行容量) |
| **持续委托或使用 SOP 时** | D9 委托与结果接收 | 接收结果时辨认本次委托、原分工或节点、已采用的版本。撤权、同一 Agent 再次获派、节点返工或候选换版时，沿原归属核对迟到结果。[受托工作与接管](02-sop-workflow.md#53-授权撤销和接管) |
| 需要在原执行可能仍写入时换机或接管 | D3 旧执行处置 | 取得实际退出或写入隔离的依据后，再按接手者授权继续修改。已共享材料可先由其他成员读取。[本地执行与工作交接](03a-execution-plane.md#3-执行回执与资源释放) |
| 选用步骤驱动的方法 | D8 TeamAI Driver 与宿主 | 只为实际选用的宿主核对步骤领取、确认、报告、取消与恢复。普通规则和资料按项目适用版本及接收者权限提供。[方法选用与步骤驱动](03b-capability-governance.md#步骤驱动与观察) |
| **项目需要跨次比较用量时** | D7 多来源计量 | 单次 Run 先保留已有原生单位和实际覆盖，缺失的指标保持未知。按项目或多来源汇总时再处理请求身份、Credits、去重及更正。[归集与覆盖](04-cost-quality-improvement.md#35-汇总范围与重复引用) |
| 项目启用资料或代码 Wiki | D10 来源连接与索引 | 可先引用现有资料。需要自动接入或检索时，再确定修订定位、读取权限、时效和索引策略。[资料扩展](#8-团队-wiki项目资料与代码-wiki-的扩展接入) |
| 团队决定评价或对照改进方法 | D11 评价触发与资源预算 | 另行明确谁能发起、取得哪些证据、占用多少资源以及怎样比较效果。生产工作按本项完成条件收尾。[评价与改进](04-cost-quality-improvement.md#5-单次修正与跨次-rsi) |
| 工程方案需要确定进程与存储边界 | D4 实际部署 | 用已明确的写入、权限及故障恢复要求判断哪些职责沿用 Multica 的现有部署，哪些需要独立承载。 |

## 12. 架构验收标准

本架构进入详细技术设计前，应能对以下问题给出一致答案：

- 一项工作只有一个 Issue 作为业务归属；任何 Run、SOP、交付和评价都能追溯到来源工作或明确的独立活动。
- 能从 Issue 的指派和委托确认成员与 Agent 各自的责任，从 Run 确认其实际 Runtime 和 Session。
- 负责人可以自主推进或按需委托。采用同项 Worker 协助、独立子 Issue 或 SOP 时，可查明每份交付由谁安排、由谁接收。
- 中心协作不依赖某一成员的 Runtime 在线；本地执行失联不会抹掉共享工作事实。
- 成员直接交付时能核对署名、选交版本和可读材料。受管执行请求沿 Multica 原派发链，能核对授权、实际启动、结果、取消和迟到回报。
- 方法和资料从来源到选择、投递、使用均保留相应证据；没有证据的层级保持未知。
- 交付、证据、评价、验收、发布和采用是不同事实，候选换版不污染旧结果。
- 团队 Wiki、项目资料和代码 Wiki 可以独立启用，不成为普通协作的基础设施前置条件。
- 成本归属原生产 Run，多源观察不重复计量；评价与 Benchmark 的成本独立归集。
- 工作台只呈现和路由，不复制权威状态机与业务规则。

本架构定义模块边界与协作关系，不定义数据库表、API、微服务拆分、页面布局或具体部署拓扑。上述未决项应在后续技术设计中逐项依据 Multica 真实实现和宿主能力收敛。
