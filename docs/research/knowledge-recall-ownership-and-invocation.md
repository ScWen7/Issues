# AgentPlatform · Knowledge Recall 的能力归属与调用承载审查

> 状态：架构承载审查完成  
> 分支：design/system-architecture-convergence  
> 非目标：不新增能力域、不新增 Context Compiler / Recall Runtime、不决定数据库、搜索引擎、API 或部署方式。

## 1. 核心结论

**Knowledge Recall 的权威能力归属 A · 团队知识管理；Recall 的工作触发和采用决策归属 B · 产研工作与流程协作；Recall 结果向本地 Agent 的投递与消费观察归属 D · 执行与交付证据。**

| 职责 | 所属能力域 | 负责什么 | 不负责什么 |
|---|---|---|---|
| 知识查询与读取 | A · 团队知识管理 | 对正式 Team / Project Knowledge 执行授权范围内的查询、候选返回、修订读取、Evidence 引用和知识状态说明 | 不决定当前 Issue 要做什么，不负责所有来源检索，不决定 Agent 是否采用 |
| 工作触发与选择 | B · 产研工作与流程协作 | 从 Issue / Work Agreement 判断是否需要 Recall；限定当前 Project、工作目标、角色和任务范围；决定候选是否进入本项工作 | 不复制知识索引、不维护 Knowledge 正文、不实现 Recall 算法 |
| 宿主能力与投递观察 | D · 执行与交付证据 | 将获准选用的知识引用 / 内容通过成员可用的宿主通道提供给 Agent；记录 Prepared / Delivered / Loaded / Used 的可观察证据 | 不拥有知识查询权威、不改变知识权限、不推断未上报的消费事实 |

**Recall 是 A 域提供的一项知识消费能力，不是独立业务能力域或必经工作流。** 它可以通过平台授权的 Agent 工具、工作台入口或其他现有调用通道暴露；具体通道属于后续宿主适配实现，不在本轮选型。

## 2. 从现有架构看，职责并非空缺，只是调用边界没有写透

### 2.1 A 域已经拥有知识权威

现有整体架构已明确 A 域维护 Knowledge Item / Revision、知识核验、派生许可、发布、反馈、有效性、冲突、撤回和面向 Team / Project / Issue 的检索消费。知识生命周期也定义了正式知识检索、候选知识包、Evidence 和消费反馈。

因此 Knowledge Recall 的查询权威应落在 A 域。否则会出现知识正文由 A 管理、查询规则和结果过滤却由另一个统一搜索服务维护的双重权威。

### 2.2 B 域已经拥有工作上下文决定权

B 域和 Work / Context Contract 已明确 Issue 是研发工作的唯一业务归属，Work Agreement 定义当前目标、责任、完成条件和授权；当前工作对知识、Harness、Run、Artifact 和 Evidence 的引用与消费由工作主线组织。

因此 B 域负责判断这项工作是否需要 Recall、查询意图是什么、结果是否适用于当前 Issue、是否被本项采用。B 不拥有知识正文或搜索索引。

### 2.3 D 域已经拥有宿主投递和消费观察责任

D 域及 ContextReceipt / Execution Contract 已明确成员本地 Agent 宿主由适配能力接入；上下文选择、准备、投递、加载和实际使用是不同证据阶段；Multica 仍然是 Run / Runtime / Usage 权威账本。

因此 D 域负责将 B 已选用、A 已授权的知识内容送入真实宿主，并观察实际输入和使用证据。D 不应另建知识缓存作为权威来源，也不应在投递时绕过 A 的权限检查。

## 3. 推荐的端到端调用关系

~~~mermaid
sequenceDiagram
  participant Agent as 成员本地 Agent
  participant Work as B · Issue / Work
  participant Knowledge as A · Knowledge
  participant Host as D · Host Adapter
  participant Evidence as D · Usage / Evidence

  Agent->>Work: 当前 Issue 与工作意图
  Work->>Work: 判断是否需要 Knowledge Recall
  opt 需要发现正式知识
    Work->>Knowledge: 当前接收者 + Team / Project 范围 + 查询意图
    Knowledge->>Knowledge: 权限与作用域过滤
    Knowledge->>Knowledge: 检索正式 Knowledge 候选
    Knowledge-->>Work: Claim 摘要 + Item / Revision / Release + 适用条件
    Work->>Work: 判断相关性、适用性和是否采用
    opt 选用某条知识
      Work->>Knowledge: 按身份读取完整 Revision / 获准 Evidence
      Knowledge-->>Work: 正文、证据引用和当前可见状态
      Work->>Host: 本项已选知识与工作约束
      Host->>Agent: 通过宿主支持的通道提供内容
      Host-->>Evidence: Prepared / Delivered 回执
      Agent-->>Evidence: 可观察的 Loaded / Tool / Artifact 证据
    end
  end
  Agent->>Knowledge: 执行中可按需再次 Recall / Read
~~~

此图表达业务职责，不代表必须存在 B 域的独立编排服务或 A 域的独立微服务。

### 3.1 Recall 可以由 Agent 直接触发

不能把 Recall 限定为“Issue 启动时由平台自动执行一次”。

- 工作准备时触发：B 根据 Issue 意图提示或请求检索相关知识；
- Agent 执行中触发：Agent 发现知识缺口，使用当前授权身份调用 A 域 Knowledge Recall。

两种方式调用同一个 A 域知识查询能力，并遵守相同权限、作用域和结果契约。是否自动触发取决于任务需要，不要求每个 Issue 必须 Recall。

### 3.2 Agent 不应绕过授权调用底层知识存储

Agent 可以是调用发起者，但不能自行声明 Team / Project 范围或伪造成员身份。调用上下文应由现有受信任工作 / 宿主授权链提供：
- 当前成员 / Agent 身份；
- 当前 Project 与 Issue；
- 当前 Run / 执行身份（存在时）；
- 可见 Team / Project 范围；
- 本次工作授权和共享范围。

A 域按真实接收者再次校验知识正文、Evidence 引用和派生内容的可见性。不能只信任 Agent 传入的 project_id 或 scope 字段。

## 4. Knowledge Recall 的最小业务能力边界

Recall 不需要成为一套新的资产管理系统。A 域需要对外表达的业务能力只有：

1. **Search / Recall**：在调用者有权访问的 Team / Project 正式知识范围内，按工作意图发现候选。
2. **Read Revision**：按稳定 Knowledge Item / Revision / Release 身份读取完整知识正文。
3. **Read Evidence Reference**：返回证据身份、来源修订、位置和当前可访问状态；只有调用者有原始来源读权时才可展开原文。
4. **Feedback**：将有帮助、无关、错误、过期、冲突等反馈关联到具体 Knowledge Revision。
5. **Change Awareness**：在来源撤回、派生许可暂停、知识退役或修订替代时，阻止不再合格的新投递，并提供受影响引用信息。

这些是 A 域知识生命周期的查询 / 消费面，不是本轮要定义的 API 端点、搜索引擎或数据 Schema。

### 4.1 Recall 结果不等于全文投递

默认返回可核查的候选摘要：
- Knowledge Item 身份；
- Revision / Release；
- Team / Project 作用域；
- Claim 摘要；
- 适用条件、限制和反例；
- 有效 / 待复核 / 暂停投递等状态；
- Evidence 引用和证据可见性。

Agent 或工作负责人决定展开后，再按身份读取完整 Revision。这样可以减少无关全文进入上下文，也避免把 Recall 命中误当成已经采用。

### 4.2 结果过滤与证据权限

过滤顺序必须保证任何未授权内容都不会通过标题、摘要、Claim、Evidence ID、关系边或错误消息泄漏：
1. 从受信任调用上下文确认接收者身份和允许范围；
2. 在候选检索前过滤 Team / Project 作用域和知识发布状态；
3. 检索和排序仅在可见候选中执行；
4. 返回字段按知识正文可见性过滤；
5. Evidence 原文访问再独立检查来源读权和派生许可；
6. 在投递前重新核验权限、修订和暂停状态。

成员失去 Team 资格、Project 成员资格变化、来源派生许可撤回和知识 Release 暂停是不同变化，不能用一个简单的 scope filter 代替。

## 5. Recall、Source Search、Code Retrieval 和 Harness Resolution 不合并

| 能力 | 权威归属 | 查询对象 | 调用方式 |
|---|---|---|---|
| Knowledge Recall | A · 团队知识管理 | 正式 Team / Project Knowledge | 按工作意图发现知识候选 |
| Source Search / Read | A 域的来源连接与处理能力，原文仍由外部来源维护 | 飞书 PRD、评审、接口文档等 Source Item / Revision | 按来源身份、权限和位置检索 / 读取 |
| Code Retrieval | 可选 Project Code Wiki / 当前代码工具 | 仓库、Commit / Tree、模块、符号、调用关系 | 按代码问题检索 |
| Harness Resolution | C · Engineering Harness 治理，项目采用由项目配置决定 | 已发布资产、Project Adoption、工作约定 | 按发布、采用、适用范围和授权解析 |
| Work Context Loading | B · 产研工作与流程协作，依赖 Multica 原生对象 | Issue、Work Agreement、Decision、Project、Run | 按稳定身份确定性读取 |

来源连接器、代码工具和 Harness 不需要经过 Knowledge Recall 才能被使用。统一工作台可以提供一致的发现体验，但不要求一个 Provider 接管所有权威来源。

## 6. 与 Multica / Runtime / Host Adapter 的关系

### 6.1 不新增 Recall Runtime

- Recall 是一次知识查询 / 读取，不是一个新的研发 Run；
- 不为每次 Recall 创建 Multica Issue、Task 或 Run；
- 如需记录查询延迟、命中、错误或质量，可作为 A 域查询观测 / E 域评价数据；
- 只有检索任务本身成为有独立目标、责任和交付的研发工作时，才沿原 Issue / Run 模型管理。

### 6.2 不新增 Context Compiler 服务

Context Contract 是 B 域与各提供方遵守的跨层业务契约。上下文由工作准备、Agent 自主工具调用和宿主适配共同形成，不需要额外建立一个长期运行的 Context Compiler 控制平面。

### 6.3 Host Adapter 只负责把授权结果送达

D 域适配器：
- 依据真实成员 / Runtime 授权请求或接收知识内容；
- 不能把自己缓存的旧 Knowledge Release 当作当前权威；
- 不能扩大接收者权限；
- 在送达前核对本次选用版本和当前投递资格；
- 记录宿主确认的投递回执；
- 宿主支持时观察模型实际输入、工具调用和结果；
- 宿主不支持时如实标记 Unknown。

Recall 结果可以由 Agent 通过现有工具通道直接读取，也可以由 B 在准备上下文时通过 D 的现有投递能力提供。两者不改变 A 域的知识权威。

## 7. 现有对象如何承载，不新增业务对象

| 现有对象 | 在本链路中的作用 |
|---|---|
| Knowledge Item / Revision / Release | 知识身份、不可变修订和正式可消费版本 |
| Evidence / Evidence Anchor | 结论支持、来源定位和证据访问判断 |
| Project / Team / Membership / Policy | 作用域、成员资格和访问边界 |
| Issue / Work Agreement / Decision | 查询意图、工作责任、当前决定 |
| Work / Run Asset Pin | 仅固定本项实际选用的知识 / Harness 版本，不记录所有 Recall 命中 |
| ContextReceipt | 记录本次上下文准备和投递 |
| Observation / Asset Usage Observation | 记录宿主实际加载、工具调用或其他可观察使用 |
| Knowledge Feedback | 记录针对具体 Knowledge Revision 的反馈 |
| Multica Task / Run / Runtime / Session | 仅在现有受管执行中记录执行，不为 Recall 新建平行 Run |

不新增 Recall Issue、Recall Task、Recall Run、Recall Asset、Context Compiler Runtime 或统一 Search Result 业务资产。

## 8. 真实 Provider 与本地宿主的分工边界

当前仓库没有生产级 Knowledge Recall Provider。该缺口不是让 D 域新建一个搜索服务来解决，而是 A 域尚未从知识治理模型形成可调用的查询 / 读取能力。

本轮完成架构承载审查后，下一步真实实现准备应按以下顺序进行：
1. 明确 A 域现有知识权威数据如何被查询 / 读取（不先决定数据库或搜索引擎）；
2. 定义 A 域对 B / Agent 暴露的最小知识消费能力及授权上下文；
3. 定义 B 如何根据 Issue 意图触发、选择和固定结果；
4. 定义 D 如何将已授权内容送达各宿主并记录证据；
5. 使用双项目 Recall 契约测试作为 A 域查询结果的回归断言；
6. Provider 可调用后，再运行真实 Codex / Claude Code / Qoder / CodeBuddy 宿主验证。

成员本地只需在最后涉及真实宿主、真实账号或真实项目权限时执行脚本；不需要自行建设 Provider 或重做架构研究。

## 9. 结论

AgentPlatform 的 Knowledge Recall 不应被理解为“一个统一检索系统负责找齐所有上下文”，也不应被缩减为“Agent 自己随便搜索知识文件”。

正确边界是：

- **A 域拥有正式知识的检索和读取权威；**
- **B 域以 Issue 为起点，决定是否触发 Recall、如何判断候选适用并纳入当前工作；**
- **D 域通过现有宿主适配和执行证据能力完成获准内容的投递与消费观察；**
- **C 域独立决定 Harness 的发布、采用和执行资格；**
- **Project Sources、Code Retrieval 和确定性 Work Context 保持各自权威读取路径。**

这是一条沿现有五域与 Context Contract 的业务协作关系，不新增产品能力域、服务边界、控制平面或业务对象。


## 10. 消费语义进一步收敛

Recall 的具体产品行为已进一步定义于[Knowledge Consumption Contract](knowledge-consumption-contract.md)，包括可信调用上下文、候选资格过滤、候选响应、稳定 Revision 读取、Evidence 双层权限、明确采用、投递前复核、撤权与反馈语义。

本轮将前文“最小业务能力”收敛为可判定的产品规则：权限和正式发布状态先于排序；命中 / 读取不自动固定 Work Pin；Evidence 引用可见不代表原文可读；B 准备阶段与 Agent 自主调用使用同一 A 域契约；实际投递前按具体接收者重新核验。


## 11. 生命周期与投影可用性

Knowledge Release 与 Recall Projection 的双轨关系、权限回查、无命中 / 不完整检索语义、来源影响分析和在途 Work / Run 引用处理，详见[Knowledge 生命周期与 Recall 可用性融合审查](knowledge-lifecycle-recall-availability.md)。A 域负责正式知识权威和 Recall 候选资格；检索投影只是派生运行视图，不能取代发布状态或授权判断。
