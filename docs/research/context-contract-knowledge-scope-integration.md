# AgentPlatform · Context Contract 中 Team Knowledge / Project Knowledge 融合审查

> 研究状态：完成  
> 分支：design/system-architecture-convergence  
> 研究范围：Team Knowledge、Project Knowledge、Project Sources、Project Code Knowledge 如何在 Issue 工作中被发现、授权、选用、固定和投递。  
> 非目标：不新增能力域或上下文控制平面；不设计数据库 Schema、API、部署或检索引擎。

## 1. 结论摘要

**Team Knowledge 与 Project Knowledge 是同一知识管理能力中的两种知识作用域，共享内容组织、证据、修订、发布、反馈和检索机制，但拥有不同的权威归属、维护责任、可见范围和跨域复用规则。**

同时，Project Sources 和 Project Code Knowledge 不应与 Project Knowledge 混为一谈：

- **Project Sources**：项目已有的权威原始资料，例如飞书 PRD、项目文档、接口文档、Git 和项目系统记录。原文仍由来源系统维护，可以直接被有权的 Issue / Agent 引用，不必先转化成知识。
- **Project Knowledge**：从项目资料和研发证据中提炼、由项目责任人维护、在项目范围内可长期复用的正式知识。
- **Project Code Knowledge**：绑定仓库和代码基准的代码结构、模块、调用关系与实现定位，是可选的项目代码认知能力，不属于团队知识，也不必全部转化为 Project Knowledge。
- **Team Knowledge**：团队范围可复用的经验、约定、技术实践和跨项目知识，由团队领域责任人维护。

Context Contract 是跨能力的工作依据选择和供给契约。它按 Issue 的实际工作需要组合上述来源，不统一拥有这些来源，也不把它们复制到一个知识库。

## 2. 四类内容的权威归属

| 内容 | 权威归属 | 维护者 | 默认使用范围 | 是否正式 Knowledge |
|---|---|---|---|---|
| Team Knowledge | Team 范围的 Knowledge Item / Revision / Release | 团队领域维护者 | 团队授权范围内，按明确适用条件跨项目复用 | 是 |
| Project Sources | 飞书、Git、项目系统等原始来源 | 原来源责任人 | 原来源授权范围 | 否 |
| Project Knowledge | Project 范围的 Knowledge Item / Revision / Release | 项目业务 / 技术责任人 | 当前 Project | 是 |
| Project Code Knowledge | 指定仓库和代码基准下的派生代码认知 | 项目代码 Wiki 维护者；代码本身由工程仓维护 | 当前 Project 和获准代码读者 | 不自动属于正式 Knowledge |
| Issue Work Context | Multica / Issue / Run 等原权威对象 | 当前工作责任人和对应事实生产者 | 当前工作及获准接手者 | 否 |

### 2.1 一个重要区别：适用范围不是访问权限

例如，Team Knowledge 的一条经验可能适用于支付、订单和库存三个项目，但这不意味着所有能搜索到该知识的成员都能查看其证据原文。

需要分别判断：
- 知识发布作用域：Team 或 Project；
- 知识适用范围：哪些项目、系统、版本、环境或工作类型适用；
- 知识可见权限：当前成员是否有权读取该知识；
- Evidence 原文权限：当前成员是否有权查看支持它的来源；
- 派生许可：来源责任人是否允许将该来源内容提炼给目标受众。

适用范围不能扩大访问权限；原文读权也不自动授予跨范围派生权。

## 3. Team Knowledge 与 Project Knowledge：同一机制、不同治理

### 3.1 共享的内容组织机制

两者沿用 K0-A：
- Knowledge Topic / Item 作为稳定主题身份；
- Topic Revision 组织主题结构和结论；
- Claim 是可独立核验、引用和局部复核的语义单元；
- Evidence 记录支持、反驳、限定或背景依据；
- Knowledge Release 固定经核验可供指定范围消费的修订；
- Knowledge Feedback 记录帮助、无关、错误、冲突和过期反馈。

Claim 默认不独立发布；只有确有独立授权、责任、发布 / 撤回或冲突治理需求时才提升为独立 Knowledge Item。

### 3.2 不同的治理主体

| 治理事项 | Team Knowledge | Project Knowledge |
|---|---|---|
| 创建候选 | 团队成员、Agent、项目经验派生 | 项目成员、Agent、项目资料和 Issue / Run |
| 内容责任 | 对应团队领域维护者 | 当前 Project 的业务 / 技术责任人 |
| 事实核验 | 核验跨项目适用性、反例和团队范围 | 核验项目事实、项目决策和项目适用条件 |
| 来源许可 | 对每份来源检查目标团队受众派生许可 | 按项目来源读权和处理授权 |
| 正式发布 | 团队范围发布者 / 领域责任人 | 项目有权维护者 |
| 适用范围 | 明确声明可适用的项目 / 工作条件 | 默认当前 Project |
| 复核与退役 | 团队责任人处理 | 项目责任人处理 |
| 跨域复用 | 被项目按需引用或采用 | 经许可、去敏、重新核验后派生为 Team Knowledge |

**共享的是内容模型和生命周期原则，不共享所有权、审核权和默认可见范围。**

### 3.3 不建立两套独立知识系统

不建议：
- Team Knowledge 使用一套知识模型，Project Knowledge 再使用另一套；
- 项目知识复制一份团队知识正文；
- 每个 Project 建立自己的知识发布系统；
- 将 Team / Project 仅作为目录名称，却不区分维护者和访问策略。

更合理的是在同一知识管理能力中按作用域归属资产，统一维护来源证据、版本、检索和治理能力。

## 4. Project Sources 不等于 Project Knowledge

不是所有项目资料都需要经过知识提炼。

### 4.1 直接消费原始资料的情况

以下情况优先引用原始来源：
- 当前 Issue 需要理解某份 PRD 的具体需求；
- 需要查看最新接口定义或字段说明；
- 需要核对某次评审的原始决定；
- 需要查看代码、配置、测试和构建文件；
- 资料仅在当前 Issue 中使用，没有跨工作复用价值；
- 原文具有重要上下文，摘要容易丢失限定条件。

Context Contract 应允许直接取得来源身份、修订、位置和当前读权，将原始材料作为工作依据。它不应强迫成员先把材料加工成 Knowledge Item。

### 4.2 形成 Project Knowledge 的情况

当内容满足长期复用价值时，才形成项目知识候选：
- 多个 Issue 反复需要的项目业务规则；
- 项目架构决策及其取舍理由；
- 多个模块共同遵守的接口约定；
- 原始资料分散但需要统一解释的项目约束；
- 已验证的项目故障根因和预防经验；
- 原始文档没有明确写出、但有充分证据支持的项目事实。

正式 Project Knowledge 不是原文副本，而是带证据、适用范围、维护责任和有效状态的派生结论。

### 4.3 项目代码认知单独处理

模块地图、调用关系和当前实现状态由代码仓和可选 Project Code Knowledge 提供：
- 绑定仓库身份和具体 Commit / Tree 基准；
- 自动生成的关系标明静态推断、动态观测或人工确认；
- 设计动机和架构决定通过 Project Knowledge / 原始决策来源引用；
- 不要求全仓 AST 图谱；
- Issue 只分析本次涉及模块及必要上下游；
- 代码变化触发代码认知更新和相关知识影响分析，不直接判定 Project Knowledge 失效。

## 5. Team Knowledge 如何进入 Project，而不复制正文

### 5.1 默认采用引用，不做复制

Team Knowledge 在团队范围发布后，Project 可以按适用范围发现和引用该版本。引用保留：
- 原 Team Knowledge Item 身份；
- 具体 Revision / Release；
- 适用条件；
- 原 Evidence 关系；
- 当前可见权限和使用范围。

项目不创建一份同正文的 Project Knowledge 副本，也不因引用而取得 Team Knowledge 的编辑权。

### 5.2 什么时候需要 Project Adoption

不要求每条 Team Knowledge 都经过 Project Adoption。应区分：

- **一般知识参考**：根据 Issue 意图、项目和适用条件检索，引用当时实际选用的版本。
- **项目明确采用**：某项团队知识需要作为项目持续约定或固定基线时，由项目有权成员通过既有 Project Adoption / Project Configuration 采用明确版本。
- **项目强制执行**：如果内容需要成为 Agent 必须遵守、可检查的规则，应进入 Harness Rule / Principle 的独立治理与发布；不能仅凭 Knowledge Release 将经验描述变成强制门禁。

项目采用一个版本，不意味着复制或取得原知识的维护权。团队新版本发布也不应静默改写已固定的在途工作。

### 5.3 Team Knowledge 与 Project Knowledge 可以组合

例如：
- Team Knowledge：通用区域权限测试方法；
- Project Knowledge：项目 A 的区域权限模型和例外；
- Project Sources：项目 A 当前 PRD；
- Project Code Knowledge：项目 A 当前订单服务实现。

检索时可以组合四者，但各自保留自己的来源、范围和责任。

## 6. Project Knowledge 如何派生为 Team Knowledge

项目知识跨项目复用不是作用域字段从 Project 改成 Team，而是一个新的知识治理决定。

必须经过：
1. Agent 或成员发现候选经验；
2. 选择需要派生的具体 Claim，而非复制整个项目主题；
3. 逐份核对 Evidence 来源的派生许可和目标团队受众；
4. 去除项目标识、敏感内容和不可迁移前提；
5. 重新核验跨项目适用性、反例和限制；
6. 团队领域维护者审核并发布新的 Team Knowledge Revision / Release；
7. 原 Project Knowledge 保持原范围、历史和责任不变。

项目成员对来源的读取权、来源派生许可、目标团队受众授权、团队发布权相互独立。任何一项缺失都不能以团队成员可读、Agent 已经总结或项目知识已发布为理由绕过。

C1 / C2 实验已证明：单来源撤回只影响依赖该来源的派生结论及后续投递资格；其他证据和历史派发不被连带抹除。同字节恢复也不自动恢复旧授权，需要重新复审。

## 7. Team 与 Project 内容发生冲突时如何处理

不能设置“Team 永远优先”或“Project 永远优先”的全局排序。先判断争议事实的类型和权威来源，再区分以下情况。

| 情况 | 正确处理 |
|---|---|
| Team Knowledge 是通用实践建议，Project Knowledge 记录项目特定实现 | 两者可以同时成立；Project 条目声明项目适用条件，不覆盖团队一般经验 |
| Team Knowledge 是基于某类前提的通用事实，Project 具有不同前提 | 明确适用条件和不适用范围，不制造虚假冲突 |
| Project Knowledge 记录本项目偏离团队建议的原因 | 保留项目决策及理由；团队建议仍可作为参考 |
| Team Harness Rule 是项目必须遵守的强制约束，Project 希望例外 | 不允许 Project Knowledge 静默覆盖；走 Harness 例外 / 项目采用与 Issue 有权决定机制 |
| Team / Project 对同一事实给出互相矛盾的断言 | 并列证据、范围和修订，标记冲突，路由给该事实的责任人；不按更新时间或模型分数覆盖 |
| 项目实现与已批准项目决策不同 | 分别保留“已批准意图”和“当前代码实现”，报告偏差；代码不能自动改写决策 |

知识描述事实和经验；Harness 描述必须遵守的行为；Issue Decision 处理当前工作中的有权例外。三者不可互相代替。

## 8. Context Contract 的端到端选择流程

### 8.1 输入不是一个“知识库查询”

当前工作从 Issue 的正式 Work Agreement 开始，按需要选择不同权威来源：

| 输入类别 | 提供方 | 取得依据 |
|---|---|---|
| 当前工作目标与责任 | Multica / Issue | 当前 Work Agreement、版本、委托和决定 |
| 团队可复用知识 | Team Knowledge | Team 作用域、适用范围、有效 Release、当前读权 |
| 项目长期知识 | Project Knowledge | Project 作用域、项目责任、有效 Revision / Release、项目读权 |
| 项目原始资料 | 飞书、Git、项目系统等 | Source Item / Revision、原文位置和来源系统当前读权 |
| 当前代码依据 | 项目仓库 / 可选 Code Wiki | 仓库身份、Commit / Tree、文件或符号位置和代码读权 |
| 工作方法 | Harness | 发布版本、Project Adoption、适用范围和本项选择 |
| 执行历史 | Multica Run / Artifact / Evidence | 实际共享授权、Run / Artifact 身份和版本 |

### 8.2 选择顺序

1. 读取 Issue 当前 Work Agreement、目标、完成条件和责任。
2. 识别当前工作涉及的项目、业务领域、模块、工作类型和角色。
3. 按工作需要分别查询 Team Knowledge、Project Knowledge、Project Sources、Code Knowledge 和 Harness。
4. 对每项结果检查接收者读权、作用域、适用条件、来源状态和版本。
5. 对有冲突的事实分别展示依据，不进行全局来源排序或静默覆盖。
6. 选择完成当前工作的最小充分材料；无关项目资料不进入上下文。
7. 对实际选用的 Knowledge Revision / Release、来源修订、代码基准和 Harness 版本建立工作引用；不为每次检索命中都创建 Pin。
8. 通过现有宿主通道准备和投递，记录 ContextReceipt；实际加载、使用和效果按可观察证据分别记录。
9. 后续协调回合或在途执行继续时，重新核对当前权限、来源修订和约定版本；不静默替换已固定的历史输入。

### 8.3 权限核验必须针对接收者

同一个 Issue 负责人有权读取某份飞书文档，不代表所有 Worker 都有权读取。Main Bot 有权也不代表被委托 Agent 有权。

因此：
- 每个接收者按自身成员身份、项目参与关系和来源系统权限判断；
- Team Knowledge 可见性按团队范围授权；
- Project Knowledge 可见性按项目范围授权；
- Evidence 原文可见性独立检查；
- 不可见来源不得通过搜索摘要、主题标题、模块关系或生成上下文泄漏；
- 撤权后停止新投递；已经进入宿主历史的内容保留真实共享记录，不声称远程删除。

### 8.4 最小充分上下文与按需加载

| 工作类型 | 常见必需输入 | 通常不需要 |
|---|---|---|
| 小型代码 Bug | Issue 约定、目标模块代码、相关团队经验 | 整份 PRD、完整项目代码图谱 |
| 新业务功能 | Issue 约定、相关 PRD、项目业务规则、适用团队知识、目标模块代码 | 与本次功能无关的项目历史资料 |
| 跨服务架构调整 | 项目架构决策、相关 API / 服务关系、代码基准、团队架构经验、适用 Harness | 全团队所有知识 |
| 故障排查 | 故障 Issue / Run / 日志证据、相关项目历史故障、模块调用链、团队排障经验 | 不相关的产品需求文档 |
| 独立核验 | Work Agreement、验收标准、必要业务规则、被测 Candidate 和允许查看的证据 | 开发 Agent 的私有推理历史或无关项目材料 |

## 9. 真实案例回归

### 9.1 订单导出 D2 / C1 / C2

已有实证：
- D2 是本次订单导出的业务规则；
- C1 中付款时间列检查通过，但东区普通账号拿到了西区订单，整体返工；
- C2 在相同 D2 和核验器下修复了区域订单集合问题，跨区账号仍可导出两区订单，整体通过；
- C1 / C2 组合提炼出的团队测试方法经过来源派生许可和独立团队审核。

本次边界验证：
- D2 的项目业务规则属于 Project Knowledge / Issue Decision 的项目范围依据；
- C1 / C2 的原始报告是项目执行证据，不自动成为 Team Knowledge；
- 经许可和独立复审的通用区域权限测试方法才成为 Team Knowledge；
- 后续项目引用 Team Knowledge，不需要读取订单项目的私有原始报告；
- 如果项目 A 和项目 B 的权限模型不同，通用经验声明适用条件，项目规则分别补充差异。

### 9.2 项目文档修订与角色化上下文

已有实证：
- 同一需求修订中，开发与核验需要不同段落；
- 两个角色的队列固定旧来源修订后，文档变化要求重新选择；
- 失权后新线程按当前权限重建；历史线程可能仍保留旧正文；
- 真实 Codex 请求探针记录了实际送达的内容，而非只看平台检索结果。

本次边界验证：
- 需求原文仍属于 Project Sources；
- 需要长期复用的业务规则才提炼成 Project Knowledge；
- 开发和核验角色通过 Context Contract 分别取得获准内容；
- 不因一个成员可以读取整份文档，就将整份文档注入所有 Agent；
- Project Knowledge 的可见权限与原始证据可见权限分别核对。

### 9.3 项目代码 Wiki

现有设计明确：
- 代码 Wiki 解释指定代码修订的系统结构、模块关系、调用路径和变更影响；
- 每个仓库分别标明基准和覆盖范围；
- 自动生成的实现说明归纳指定版本可观察到的事实；
- 设计动机和历史取舍单独署名并引用已确认决策；
- 私有仓库读权限制同样适用于目录、搜索摘要、正文和关系图；
- Issue / Run 引用具体章节、仓库基准和源码位置。

本次边界验证：代码 Wiki 是 Project 可选能力，不能与 Project Knowledge 或 Team Knowledge 混合。代码事实与业务决策通过引用关联，而不是合并成一个不区分权威的项目摘要。

## 10. 与现有对象和能力的边界

| 现有对象 / 能力 | 本轮确认的职责 | 不新增 |
|---|---|---|
| Team / Project | 知识作用域和项目成员 / 配置边界 | 不新增团队知识项目或项目知识子系统 |
| Source Connection / Source Item / Revision | 外部来源连接、身份、修订、权限和原文 | 不把原始资料复制成知识 |
| Knowledge Item / Revision / Release | Team / Project 范围正式知识及其版本治理 | 不为每个 Claim / Chunk 新建独立发布对象 |
| Evidence / Evidence Anchor | 结论依据和可定位来源 | 不把解析 Chunk 当正式知识 |
| Project Adoption / Project Configuration | 项目明确采用某个知识或 Harness 版本 / 配置 | 不要求每条知识都强制 Adoption |
| Project Code Wiki | 指定代码基准下的结构化代码认知 | 不把模块地图并入团队知识 |
| Issue / Work Agreement / Decision | 当前目标、责任和有权决定 | 不建立知识专用 Issue |
| Multica Task / Run / Runtime | 实际执行和执行事实 | 不建立第二套知识 Runtime |
| Context Contract / ContextReceipt / Observation | 本项上下文选择、投递和可观察消费 | 不新增 Context Compiler 控制平面 |
| Harness Asset / Revision / Release | 可执行 / 可评估的规则、方法和流程 | 不把知识经验自动变成强制规则 |

## 11. 已有实证与本轮设计判断的边界

### 11.1 仓库实验直接支持

- TeamAI 代码证明了项目 / 角色命名空间、增量索引、来源定位、代码锚点新鲜度和检索范围过滤等机制；42 项定向测试覆盖导入、角色召回、索引更新和失效。
- Multica 项目权限实测证明，执行者的实际项目访问资格需要按执行主体核验；成员失权后搜索索引会收到删除实体，但已送达宿主的历史正文仍可能保留。
- Codex 0.144.6 App Server 探针证明，同一线程的历史输入不会因磁盘资料变化自动更新；需要新一轮明确投递才能证明当前正文实际送达。
- C1 / C2 知识贡献实验证明，项目来源派生到团队知识需要逐来源许可、目标受众授权和独立复审；单来源撤回不应影响无关证据。
- 项目文档修订实验证明，角色需要的来源段落不同，在途材料应固定具体修订，投递前复核权限和来源变化。
- 项目代码 Wiki 设计已明确仓库 / Commit 基准、来源权限和引用语义。

### 11.2 本轮形成的设计判断

- Team / Project 是同一知识机制下不同作用域，不是两套独立知识系统。
- Project Sources 不等于 Project Knowledge；原始资料可以直接被工作消费。
- Project Code Knowledge 是独立可选项目能力，不属于 Team Knowledge。
- Team Knowledge 默认通过引用被项目消费；只有需要固定项目采用的规则 / 基线时才采用特定 Release。
- Project Knowledge 跨项目复用必须形成新的 Team Knowledge 派生候选，不能直接修改 Scope。
- Context Contract 负责跨来源组合，知识管理只负责提供其有权消费的知识结果。

### 11.3 仍待真实项目验证

- 多个项目共享同一 Team Knowledge 时，适用条件能否被准确表达，避免错误召回；
- Team Knowledge 的版本更新如何通知已显式采用该版本的项目；
- Project Knowledge 的维护者交接与项目生命周期结束后的归档责任；
- 同一 Team / Project 下多人并发修改主题时，如何保持 Claim 局部更新和证据关系完整；
- 不同宿主的来源权限、上下文投递和实际加载能力；
- 复杂飞书文档的块级修订和角色化选段；
- Team Knowledge / Project Knowledge 与 Harness Rule 冲突时，项目例外流程是否能在真实 Issue 中顺畅完成。

## 12. 最终设计准则

1. Team Knowledge 与 Project Knowledge 共用知识内容和治理机制，但分别归属 Team 与 Project。
2. 知识作用域、适用范围、可见权限和来源派生许可必须分开表达。
3. Project Sources 可以直接作为工作依据，不要求全部转成 Project Knowledge。
4. Project Knowledge 是经过提炼和治理的项目长期认知，不是 PRD 副本。
5. Project Code Knowledge 绑定仓库与代码基准，独立可选，不并入团队知识中心。
6. Team Knowledge 被 Project 引用时保留原身份和版本，不复制正文、不转移维护权。
7. Project Knowledge 跨项目复用时形成新的 Team Knowledge 派生候选，逐来源授权、去敏、重新核验和团队发布。
8. Team Knowledge 的适用性不自动等于强制约束；强制规则由 Harness 独立治理和发布。
9. 项目例外不能静默覆盖团队强制规则；事实冲突按事实类型和权威来源处理。
10. Issue 是上下文选择的起点；Context Contract 按当前工作组合最小充分输入，不要求每项工作加载所有资料。
11. 权限、版本和实际投递按每个接收者核验；命中、投递、加载、使用和效果分别记录。
12. 不新增第二套 Wiki、Issue、Run、Runtime、Release 或 Context Compiler 控制平面。

## 13. 后续推进

本轮完成 Team / Project Knowledge 的业务边界和 Context Contract 的选择规则。下一步可基于这些规则选择两类真实 Issue 场景（一个项目内功能开发、一个跨项目复用经验），逐项验证：
- Team / Project 知识与来源命中是否正确；
- 项目原始资料能否不经知识提炼直接消费；
- Team Knowledge 是否以引用方式进入 Project；
- 权限不足、来源修订、冲突和代码基准变化如何处理；
- Codex、Claude Code、Qoder、CodeBuddy 等宿主分别能证明到 Selected、Delivered、Loaded、Used 的哪一层。

这属于 Context Contract 场景验收，不提前进入技术选型。

## 参考资料

- [知识管理生命周期](../architecture/knowledge-management-lifecycle.md)
- [核心业务对象模型](../architecture/core-business-object-model.md)
- [跨层业务契约与协作协议](../architecture/cross-layer-contracts.md)
- [团队 Wiki 与项目资料](../architecture/team-project-wiki.md)
- [项目代码 Wiki](../architecture/code-wiki.md)
- [K0 第二轮架构边界回归审查](k0-architecture-boundary-regression-review.md)
- [项目知识与真实宿主输入](topic-03b/project-knowledge.md)
- [知识来源与可见性](topic-03b/knowledge-sources.md)
- [知识贡献与复审](topic-03b/knowledge-contribution.md)
- [专题三 B 来源与知识实证](03b-source-evidence.md)
