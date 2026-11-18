# AgentPlatform · Recall 与多来源工作上下文的职责边界研究

> 研究状态：完成  
> 研究分支：design/system-architecture-convergence  
> 目标：明确 AgentPlatform 中 Recall 的语义边界和工作位置，避免把不同权威来源误建成一个通用知识检索库。  
> 非目标：不决定搜索引擎、索引架构、API、数据库或部署方式。

## 1. 结论先行

**AgentPlatform 不应把所有工作上下文都变成一个 Recall 检索对象。**

TeamAI 的 Recall 是面向团队 AI 资产的检索工作流。它从 Agent 的任务描述产生查询，在当前成员已获得的资源范围内检索经验、文档、规则、技能和代码认知，再将结果压缩返回给主 Agent。

AgentPlatform 的工作依据具有不同权威和生命周期。一次研发工作可能使用：
- Team Knowledge：团队范围正式知识；
- Project Knowledge：项目范围正式知识；
- Project Sources：飞书 PRD、接口文档、项目决策等原始权威来源；
- Project Code Knowledge：指定仓库和代码基准下的代码认知；
- Harness：项目采用的规则、Skill、Playbook、SOP、Script 和 Evaluation；
- Issue / Work Context：当前目标、责任、决定、执行与交付状态。

这些内容不能因为都可能被 Agent 读取，就全部进入同一个 Recall 索引。

### 1.1 推荐模型

| 动作 | 主要对象 | 作用 | 是否属于 Recall |
|---|---|---|---|
| 工作上下文加载 | Issue、Work Agreement、Project、当前 Run、显式引用 | 按稳定身份读取当前权威事实 | 否 |
| Knowledge Recall | Team Knowledge、Project Knowledge | 按任务意图发现相关正式知识 | 是 |
| Source Search / Read | Project Sources 和外部权威来源 | 查找并读取原始资料及具体修订 | 是检索能力，但不是正式知识 Recall |
| Code Retrieval | Project Code Wiki、当前代码仓和代码工具 | 查找模块、调用关系和指定代码基准的实现 | 独立代码检索能力 |
| Capability Resolution | Harness Release、Project Adoption、工作约定 | 确定本次可用 / 必需的能力版本 | 否；不是按语义相似度决定是否生效 |

Context Contract 规定这些动作在当前 Issue 中如何被允许、选择、核验、固定和投递；它本身不是搜索引擎、索引或独立 Context Compiler 服务。

### 1.2 核心原则

- Recall 找候选，不负责定义事实权威。
- Issue / Project 的确定性工作事实按 ID 和关系直接读取，不通过语义 Recall 猜测。
- 正式知识使用 Knowledge Recall；原始文档使用来源检索；代码使用代码检索；Harness 使用采用与版本解析。
- 多来源可以在一个工作上下文中组合，但不必在一个索引里混合排序。
- 权限和范围过滤先于内容返回；适用性、来源修订和实际接收者仍需在投递前复核。

## 2. TeamAI Recall 当前机制：从 learnings 扩展到 Team Context 检索

### 2.1 当前版本事实

TeamAI 当前 main 分支的产品文档将 Team Context 描述为 learnings、代码知识图谱和 teamwiki 等团队知识资源的可检索能力。当前 src/recall.ts 的实现已经超出最初的 learnings 单一索引。

普通搜索索引包含四种内容：
- learnings；
- docs；
- rules；
- skills。

代码知识图谱由 src/code-knowledge-recall.ts 单独检索，再与普通索引结果合并排序。因此 TeamAI 提供一个 Agent-facing 检索入口，但内部包含不同索引和不同召回机制。

依据：
- [TeamAI 中文产品概览](https://github.com/Tencent/teamai-cli/blob/main/docs/product-overview.zh-CN.md)
- [Recall 实现](https://github.com/Tencent/teamai-cli/blob/main/src/recall.ts)
- [代码知识 Recall 实现](https://github.com/Tencent/teamai-cli/blob/main/src/code-knowledge-recall.ts)
- [Search Index 实现](https://github.com/Tencent/teamai-cli/blob/main/src/utils/search-index.ts)

### 2.2 普通索引如何工作

Recall 读取当前项目或用户作用域的本地索引。索引缺失、旧 Schema 或成员资源清单变化时重新构建。构建时收集当前成员实际收到的 learnings、docs、rules 和 skills，并按项目命名空间和已投递资源清单过滤。

检索使用词法 Token / TF-IDF 类评分逻辑，带标题、标签、领域和类型权重。TeamAI 的 Recall Rule 明确要求中英文扩展关键词，因为这一路径以词法匹配为主，单一语言查询可能无法命中另一种语言的内容。

这是一种“团队已分发资产的本地检索”，不是实时访问所有外部权威来源。

### 2.3 项目和角色范围

TeamAI 在项目目录检测 Project Scope：
- 默认只搜索当前项目作用域；
- 项目可显式配置 inheritUserScope，再将用户作用域结果纳入；
- 项目范围优先；
- 项目中的同逻辑资源可遮蔽用户继承副本；
- 资源清单和 namespace 解析确保索引内容与当前成员 / 项目实际收到的资源一致。

这说明 TeamAI 的检索范围不是“所有 Git 仓库里存在的东西”，而是“当前成员在当前工作目录可用的团队资产范围”。

### 2.4 代码知识采用独立检索路径

queryCodeKnowledge 在 teamwiki 代码知识图谱中检索页面：
- 使用 BM25；
- 对图关系邻居进行加权；
- 支持 route、context、lookup 三种深度；
- 返回代码页面、摘要、源码锚点和相关文件；
- 检查代码来源锚点的 current / stale / missing / unknown；
- 再将代码命中分数转换到普通 Recall 结果排序所用的尺度。

因此 TeamAI 虽然提供一个 teamai recall 命令，但它不是把所有资源扁平化成一种索引。它把普通团队资产检索和代码图谱检索组合为统一输出。

### 2.5 teamai-recall Subagent 是检索工作流，不是 Recall 的定义

当前 TeamAI 提供专用 teamai-recall 子 Agent：
- 主 Agent 将自然语言任务描述委托给子 Agent；
- 子 Agent 先用 teamai recall --check 做低成本相关性预检；
- 按问题类型和复杂度选择检索深度；
- 某些图谱问题直接读取 G1–G6 结构化关系文档，不走普通 BM25；
- 需要时读取 Recall 命中的完整文件、图索引和源码锚点；
- 返回紧凑的结构化摘要和候选文件给主 Agent；
- 主 Agent 再决定是否读取完整内容。

它解决的是避免主 Agent 上下文被检索原文污染、封装检索策略和深度、隔离代码图谱深挖，而不是创建新的知识库或负责项目 Issue 授权。

依据：
- [Recall Rule](https://github.com/Tencent/teamai-cli/blob/main/rules/teamai-recall/RULE.md)
- [Recall Subagent](https://github.com/Tencent/teamai-cli/blob/main/agents/teamai-recall.md)
- [Recall Agent README](https://github.com/Tencent/teamai-cli/blob/main/agents/README.md)

### 2.6 对 AgentPlatform 的启发与不可照搬之处

可借鉴：
- 从自然语言任务描述生成检索查询；
- 检索前做低成本相关性预检；
- 以专用检索 Agent / Worker 隔离检索上下文；
- 按问题类型选择检索深度；
- 返回结构化摘要和可回读来源，而非把所有全文塞给主 Agent；
- 对成员实际可见的资源进行索引和过滤；
- 记录 Recall Run、结果命中和后续读取反馈。

不能直接照搬：
- TeamAI 的 learnings / docs / rules / skills 是其团队 Git 资产分发模型；AgentPlatform 的 Team Knowledge、Project Knowledge 和 Project Sources 有不同权威和授权语义。
- TeamAI 普通索引针对已分发本地资产；AgentPlatform 需要支持来源系统当前权限、原文修订和逐接收者核验。
- TeamAI 代码图谱是 Team Context 的一类资源；AgentPlatform 的代码认知是 Project 级可选能力，不应被归入 Team Knowledge。
- TeamAI 通过一个命令合并结果，不代表 AgentPlatform 应让不同来源共用一个全局相关性分数或统一索引。
- TeamAI 子 Agent 是可选的宿主工作流优化，不应成为所有 AgentPlatform 工作必须经过的角色或步骤。

## 3. AgentPlatform 中 Recall 的正确语义

### 3.1 将 Recall 限定为知识发现动作

AgentPlatform 的 Knowledge Recall 应主要检索正式知识：
- Team Knowledge；
- 当前 Project 的 Project Knowledge；
- 经授权、可供当前接收者消费的知识版本。

返回结果应是可核查的知识候选包：
- Knowledge Item / Revision / Release 身份；
- Claim 摘要；
- 适用范围、前提、例外；
- 有效状态和冲突提示；
- Evidence 引用及当前可访问性；
- 主题入口和完整内容读取位置。

Recall 返回“可能相关的知识”，不等于已被本次工作采用。只有当前工作实际选择并依赖的版本，才需要按既有规则固定引用。

### 3.2 Project Sources 使用来源检索与直接读取

项目原始资料包括飞书 PRD、评审纪要、接口文档、项目工程文档和 Git 文件。

需要区分：
- Search：在有权来源范围内发现文档 / 章节；
- Read：按 Source Item / Revision / Block / Page / File 读取原始内容；
- Reference：将本次真正使用的修订和位置带入 Issue 上下文。

不要求所有 Project Sources 先转成 Project Knowledge，也不应默认将所有原文复制到 Knowledge Recall 的统一索引中。

当 Issue 已经明确引用某份 PRD 或文档时，优先按稳定来源身份直接读取，不需要再 Recall 一次来猜测它在哪里。

### 3.3 Project Code Knowledge 使用代码检索

模块地图、调用关系、符号、接口实现和变更影响属于指定仓库 / 代码基准下的代码认知。

代码检索可以由项目代码 Wiki、本地 Agent 的代码搜索 / AST / IDE 工具、Git / 构建 / API 来源或其他获准代码认知能力分别提供。

代码检索返回必须标明仓库、Commit / Tree、覆盖范围和证据锚点。代码关系不应为了统一 Recall 而被转写成 Team Knowledge。

### 3.4 Issue / Project / Run 上下文确定性加载

当前工作已有明确身份的事实，应按权威对象读取：
- Issue 的 Work Agreement、当前负责人和决定；
- 父子 Issue 和依赖关系；
- Project 成员、配置、仓库关联和采用版本；
- 当前 Run、Artifact、Candidate 和已共享 Evidence；
- 已明确引用的 Knowledge Revision、Source Revision 和 Harness Release。

这些对象不是语义搜索结果，而是当前工作必须读取的确定性上下文。

例如，读取当前 Issue 的正式 Work Agreement 不应该调用 Recall 搜索“当前 Issue 目标是什么”；应按 Issue ID 直接读取当前有效版本。

### 3.5 Harness 使用能力解析，不是知识 Recall

Harness 的 Rule、Skill、Playbook、SOP、Script 和 Evaluation 可能存在检索 / 发现入口，但本次工作实际可用和必需的能力必须由团队 / 项目发布版本、Project Adoption / Project Configuration、工作类型、阶段、风险、当前 Work Agreement 和授权共同确定。

Recall 命中一条 Skill 文档不代表该 Skill 已安装、已发布、已采用或本次有权调用。Harness 的 Published、Adopted、Selected、Delivered、Invoked / Used 仍然分别举证。

## 4. Context Contract 与 Recall 的关系

### 4.1 Context Contract 不是 Recall，也不是 Context Compiler 服务

Context Contract 是跨层业务契约，规定当前工作需要什么依据、从哪里取得、谁有权消费、使用哪个版本、如何投递以及如何证明实际消费。

它不负责实现具体的 BM25 / 向量搜索、代码图谱检索、飞书文档查询、Git 文件搜索、Issue / Run 读取或 Agent 子代理编排。这些由对应的权威来源、检索能力或执行宿主提供。

### 4.2 工作启动时的合理动作

将 Issue 工作上下文准备分成两类：

**A. 确定性加载（必需基线）**
- 当前 Work Agreement 和决定；
- Project 身份、成员、仓库与必要配置；
- 明确引用的资料和版本；
- 本次已采用 / 必需 Harness 版本；
- 已有交付依赖和当前 Run 信息。

这些通过原生业务对象和明确引用读取，不依赖 Recall。

**B. 按需发现（可选补充）**
- Knowledge Recall：发现相关 Team / Project Knowledge；
- Project Source Search：发现尚未明确引用的原始资料；
- Code Retrieval：定位模块、调用关系和实现；
- Harness Discovery：发现可选方法，再由 Capability Contract 确定是否采用。

简单工作可以不执行部分甚至全部补充检索。复杂工作可以由 Agent 在启动时或执行过程中主动调用。

### 4.3 不应有“每个 Issue 必须 Recall”的硬规则

Recall 应根据工作类型和信息缺口触发：
- 用户已提供充分上下文时可以跳过；
- 本地代码和当前 Issue 已足够时可以跳过；
- 工作涉及团队特定规则、历史经验或架构决策时值得 Recall；
- 不确定项目业务口径时优先查 Project Sources / Project Knowledge；
- 不确定当前实现时使用代码检索，而不是只检索历史经验；
- 检索没有结果时，不能推断来源不存在或项目没有资料。

这与 TeamAI 的 relevance precheck / skip conditions 有相似的优化思路，但 AgentPlatform 必须按来源类型分别判断，不将一次 Knowledge Recall 的无命中等同于所有项目资料和代码认知均无结果。

## 5. 多来源结果不应强行全局排序

不同来源的搜索分数不可直接比较：
- Team Knowledge 的语义相关性；
- Project Knowledge 的适用性；
- PRD 的文本命中；
- 代码图谱的关系邻居分数；
- Harness 的发布 / 采用状态；
- Issue 当前工作对象的权威性。

建议先按来源类型和范围过滤，再在各自来源内排序，最后根据当前工作目的组合，而不是将所有来源的结果压成一个“全局最相关 Top 5”。

一个结果可以语义高度相关但不适用于当前项目；适用于当前项目但当前接收者无权查看；是有效知识但只作参考，不是强制规则；是代码当前事实但与业务意图不一致；是项目原文但已被新修订替代；是 Harness 资产但未被当前项目采用。

这些情况不能靠一个 relevance / confidence 数字表达。

## 6. 统一入口与不同 Provider：推荐的产品体验

用户和 Agent 不必理解底层有多少来源 Provider。平台可以提供统一的发现入口和结果浏览，但底层保留不同来源的读取语义。

推荐体验：
1. 从 Issue / Project 进入相关依据；
2. 默认展示确定性加载的工作对象和显式引用；
3. 需要补充时，可以发现团队知识、项目知识、项目原始资料和代码认知；
4. 结果明确标明来源类型、作用域、适用范围、版本 / 基准和权限；
5. 展开时调用对应来源的 Read，而不是统一返回一段无法追溯的混合文本；
6. 负责人 / Agent 选用后，才按工作契约固定必要版本；
7. 通过 ContextReceipt / Observation 分别记录准备、投递、加载和使用证据。

统一的是入口和使用体验，不是把所有内容变成一个同质化检索语料库。

## 7. 对现有架构文档的具体修订建议

### 7.1 Cross-layer Contracts

在 Context Contract 下明确：
- Recall 仅是按查询发现候选的能力；
- 确定性 Work Context 按原对象身份直接读取；
- Team / Project Knowledge 用 Knowledge Recall；
- Project Sources 用 Source Search / Read；
- Project Code Knowledge 用代码检索；
- Harness 由 Capability Contract / Project Adoption 解析；
- 多来源结果不做未经校准的全局排序；
- 无命中只表示当前检索未找到，不代表其他来源没有内容。

### 7.2 Knowledge Management Lifecycle

将知识检索明确为正式知识消费：
- Team / Project Knowledge 的检索；
- 结论包返回；
- Evidence 和有效状态；
- 使用反馈。

原始 Project Sources 的检索和读取由 Source Connection / Context Contract 按来源权限消费，不应误解为所有原始文档都属于 Knowledge Recall。

### 7.3 Core Business Object Model

不新增 Recall 业务对象。检索运行日志如需观察，可作为技术 / 消费证据；只有被实际选用并参与工作时才固定 Work / Run Asset Pin。

不新增 Recall Issue / Task、Context Compiler Runtime、通用 Knowledge Search Result 资产或所有检索命中都创建的 Asset Pin。

## 8. 已有证据与待验证假设

### 8.1 TeamAI 源码直接证明

- src/recall.ts 将当前作用域的普通索引与代码知识图谱检索合并为一个 Recall 命令结果。
- src/utils/search-index.ts 的普通索引包括 learnings、docs、rules、skills；资源清单和 namespace 过滤确保索引符合成员实际收到的资源。
- src/code-knowledge-recall.ts 独立执行代码 Wiki BM25 + 图关系增强，并返回源码锚点。
- agents/teamai-recall.md 定义了任务描述输入、相关性预检、检索深度、代码图谱深入读取和结构化摘要输出。
- rules/teamai-recall/RULE.md 定义了任务开始时的推荐召回规则和跳过条件。
- Recall Run、Recall Quality 和后续文件读取反馈用于追踪 Recall 与 adoption 信号。

### 8.2 AgentPlatform 仓库既有实证支持

- Context Contract 已要求 Work Agreement、来源、版本、权限和实际投递分别处理。
- Topic 3B 的真实宿主实验表明，检索 / 磁盘变化不代表历史 Session 自动获得新内容；实际送达必须从宿主输入证据证明。
- Multica 项目权限实测表明，执行者的项目读取资格要按实际主体核验；搜索索引清理和原宿主历史内容是不同问题。
- C1 / C2 实验证明 Project Evidence 派生为 Team Knowledge 需要逐来源授权、目标受众授权和独立复审。
- Project Code Wiki 已有独立的仓库 / Commit 基准、来源锚点和权限过滤设计。

### 8.3 本轮设计推断

- AgentPlatform 的 Recall 应聚焦正式知识发现，而不是取代所有来源检索。
- Project Sources、Code Knowledge、Harness 和 Work Context 应保留各自权威读取路径。
- 统一发现入口可以隐藏底层 Provider 复杂性，但不能抹去来源差异。
- Recall 可以由 Agent 自主调用，也可以由轻量检索 Agent 封装；是否使用子 Agent 属于宿主适配策略，不是业务契约。
- Issue 工作启动不应强制执行 Recall；应按信息缺口和任务类型触发。

### 8.4 仍需真实项目验证

- 对同一 Issue，Knowledge Recall、Source Search 和 Code Retrieval 的结果能否互补而非重复；
- 只提供 Work Agreement 和显式引用时，简单工作是否无需额外 Recall；
- Agent 自主 Recall 与启动时推荐 Recall 哪种更能减少遗漏且不过度加载；
- Team / Project Knowledge 的范围过滤是否能避免项目私有知识误命中；
- 多来源结果按类型呈现是否比全局 Top-K 更利于 Agent 做正确判断；
- 不同宿主是否能稳定调用 Recall / Source / Code 工具，并记录实际加载和使用；
- 子 Agent 检索摘要是否真正降低主上下文污染，而没有丢失关键例外和证据。

## 9. 最终建议

AgentPlatform 应采用：

**确定性工作上下文加载 + 按需 Knowledge Recall + 来源专属 Search / Read + 独立 Harness 能力解析。**

其中：
- Context Contract 是统一的业务规则；
- Knowledge Recall 是正式知识的检索能力；
- Project Sources 由来源连接和原文读取能力提供；
- Project Code Knowledge 由可选代码认知能力提供；
- Harness 由能力发布、项目采用和本项工作选择机制提供；
- Issue / Run 的工作事实由原权威对象直接提供。

不要将 TeamAI 的 teamai recall 直接等价为 AgentPlatform 的 Context Contract，也不要因为 TeamAI 有一个统一 recall 命令，就要求 AgentPlatform 建立一个覆盖所有资料、代码、Issue 和 Harness 的全局检索引擎。

**AgentPlatform 要统一的是工作依据的组织与消费规则，而不是把所有工作依据都变成同一种知识。**

---

## 参考资料

### AgentPlatform
- [跨层业务契约与协作协议](../architecture/cross-layer-contracts.md)
- [知识管理生命周期](../architecture/knowledge-management-lifecycle.md)
- [核心业务对象与统一关系模型](../architecture/core-business-object-model.md)
- [Team / Project Knowledge 融合研究](context-contract-knowledge-scope-integration.md)
- [项目代码 Wiki](../architecture/code-wiki.md)
- [专题三 B 来源与知识实证](03b-source-evidence.md)

### TeamAI
- [TeamAI 中文产品概览](https://github.com/Tencent/teamai-cli/blob/main/docs/product-overview.zh-CN.md)
- [Recall 实现](https://github.com/Tencent/teamai-cli/blob/main/src/recall.ts)
- [Search Index 实现](https://github.com/Tencent/teamai-cli/blob/main/src/utils/search-index.ts)
- [代码知识 Recall 实现](https://github.com/Tencent/teamai-cli/blob/main/src/code-knowledge-recall.ts)
- [Recall Rule](https://github.com/Tencent/teamai-cli/blob/main/rules/teamai-recall/RULE.md)
- [Recall Subagent](https://github.com/Tencent/teamai-cli/blob/main/agents/teamai-recall.md)
- [Recall Agent README](https://github.com/Tencent/teamai-cli/blob/main/agents/README.md)
