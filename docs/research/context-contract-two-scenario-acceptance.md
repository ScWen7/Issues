# AgentPlatform · Context Contract 双场景端到端验收

> 研究状态：基于 Topic 3B 已有固定实验进行架构场景回归；不是新一轮宿主实跑  
> 分支：design/system-architecture-convergence  
> 验收对象：项目内功能研发、跨项目经验复用  
> 验收目标：验证 Knowledge Recall、Project Source Search / Read、Code Retrieval、确定性 Work Context 和 Harness Resolution 是否各司其职，并在同一 Issue 工作中正确组合。  
> 重要限制：本报告区分“已有实验直接证明”“本轮架构回归判断”“尚未实证”。没有运行新的模型或宿主请求，不将旧实验包装成新一轮端到端运行。

## 1. 验收结论

现有 Topic 3B 已经对 Context Contract 最危险的部分提供了较强实证：项目资料按角色选段、来源修订和权限变化后的重新选择、真实 Codex 输入观察、跨 Codex / Claude Code 宿主工具调用、C1 / C2 交付核验、项目证据派生团队经验的授权与复审。

但它**尚未直接证明 AgentPlatform 的正式 Knowledge Recall 已经能在 Team / Project Knowledge 上正确检索和返回知识候选**，也未证明跨项目的真实消费 Agent 能通过统一入口发现 Team Knowledge、保留引用并继续读取自己的 Project Sources。

因此本轮结论分成两部分：

- **已通过的架构边界验收**：原始项目资料不必先知识化；项目与团队知识不同权威；来源权限按接收者核验；角色化选材；版本变化与撤权触发重新选择；实际宿主输入和工具调用可以被观察；项目经验派生团队知识需要单独许可和复审。
- **尚未通过的 Recall 产品验收**：正式 Knowledge Recall 的查询入口、Team / Project 范围过滤、Claim 级结果、证据展开、无命中语义，以及跨项目消费者对团队知识的发现和使用，缺少本项目自身的完整实测。

不能据现有 3B 结果宣称“Recall 已验收”。正确状态是：**Context Contract 的来源、权限、版本和宿主消费基线已有实证；Knowledge Recall 的产品行为仍需补一轮专门验证。**

## 2. 验收场景 A：项目内功能研发

### 2.1 场景定义

Issue：修改订单导出能力，满足当前业务决定 D2。

已有材料：
- Project Source：订单需求文档，包含共同业务约定和角色专属说明；
- Project Knowledge：项目内反复使用的订单导出规则和历史决策；
- Team Knowledge：从 C1 / C2 复盘中形成的通用区域权限测试经验；
- Project Code Knowledge：订单导出模块、调用关系和代码实现（本次既有 3B 项目知识实验没有将完整代码 Wiki 作为必需输入）；
- Harness：当前工作适用的 Role、Skill、Playbook 和已发布验证规则；
- Issue / Work Context：D2、目标、责任、验收条件和当前执行节点。

### 2.2 正确的取得路径

| 依据 | 本场景取得动作 | 为什么 |
|---|---|---|
| Issue / Work Agreement / Project | 确定性加载 | 当前工作目标、决定和项目身份已有稳定对象身份，不用 Recall 猜 |
| Team Knowledge | Knowledge Recall（如果任务确实需要区域权限经验） | 发现跨项目可复用方法及适用条件 |
| Project Knowledge | Knowledge Recall，限定当前 Project | 发现项目内长期规则、决策和例外 |
| 订单需求原文 | Source Read；显式引用时直接按 Source Item / Revision 读取 | 原始 PRD 是业务权威来源，不要求先知识化 |
| 开发 / 核验专属章节 | Source Search / Read，按接收者和角色选段 | 两个角色需要不同内容，不能因一人有整份读权而全量投递 |
| 当前模块实现 | Code Retrieval 或本地代码工具，绑定 Commit / Tree | 代码事实随仓库基准变化，不属于团队知识 |
| Role / Skill / Playbook / Rule | Capability Resolution | 是否采用由发布、项目采用、工作类型和授权决定，不能由 Recall 命中决定 |

### 2.3 现有实验直接证明了什么

**A. 项目来源的角色化读取**

topic-03b/project-knowledge.md 使用三份合成来源模拟订单需求、核验笔记和财务私有资料，按飞书 Docx 的页面、二级标题和文本块形式固定修订并分页读取。

已有实测：
- 开发读取共同业务约定和开发时区说明；
- 独立核验读取共同业务约定和核验说明；
- 即使核验者有整份需求的读权，在核验任务中搜索开发专属标记仍返回空；
- 财务私有段落在来源授权、角色范围和宿主输入三个层面均未泄漏；
- 需求从修订 1 到 2 后，在队列中的开发与核验都重新选择；
- 已经送达的历史输入仍保留原正文；撤权后新线程按当前权限重建；
- 真实 Codex CLI 0.144.6 App Server 四次模型请求由本机 Responses 端点观察，并逐段核对正文摘要和输入位置。

这证明了 Project Sources 的角色化 Search / Read 和宿主投递边界，不证明正式 Knowledge Recall 的检索质量。

**B. Team / Project 知识派生边界**

topic-03b/knowledge-contribution.md 使用 C1、C2 两份具名核验报告：
- C1 的付款时间列 A3 通过，但东区普通账号拿到西区订单，A2 失败；
- C2 在相同 D2 和核验器下修复区域订单集合问题；
- 含项目订单号的第一份团队经验草稿被退回；
- 第二份仅保留可迁移的测试方法；
- 来源派生许可、目标受众授权、项目来源读取权和独立团队发布权分别核验；
- 团队读者只收到获准文案，不能读取项目审核账本和原始报告；
- 单来源许可撤回只影响依赖该来源的派生知识和新投递；
- 同字节恢复仍要求新授权和独立复审。

这证明 Project Evidence → Team Knowledge 的派生治理边界，不证明其他 Project 已通过 Recall 找到并使用该 Team Knowledge。

**C. 执行和实际消费**

topic-03b/cross-host-handoff.md 的同机矩阵包含 Codex 与 Claude Code 原生工具调用；两台独立运行机的发送和接收通过 GitHub Actions 接续。C1 返工，C2 通过；工具回执、候选、三份工作簿和消费记录可以关联。它证明真实宿主工具调用和交付证据，不证明 Agent 曾通过 Knowledge Recall 找到团队经验。

### 2.4 场景 A 验收结果

| 验收点 | 结果 | 依据 / 缺口 |
|---|---|---|
| Issue / Work Agreement 确定性加载 | 已有架构契约 | 现有对象模型和 Context Contract |
| Project Source 直接读取，不强制知识化 | 已有实证 | project-knowledge 实验 |
| 不同角色只取得所需章节 | 已有实证 | Codex 四次真实请求 |
| 来源修订后在途工作重新选择 | 已有实证 | 修订 1 → 2 的角色取材实验 |
| 撤权后阻止新投递、保留历史事实 | 已有实证 | 原线程 / 新线程对照、Multica 撤权实测 |
| C1 / C2 经验派生团队知识 | 已有实证 | 45 项贡献检查及 5 项单来源撤回回归 |
| Team Knowledge 通过正式 Recall 被找到 | 未实证 | 3B 验证派生与可见性，没有 AgentPlatform Knowledge Recall 产品实测 |
| Project Knowledge 通过 Recall 被找到 | 未实证 | 项目规则通过来源和角色检索，尚非正式 Knowledge Recall |
| Code Retrieval 对同一 Issue 提供代码依据 | 未实证 | Code Wiki 有独立设计与 TeamAI 检索机制，尚未与此订单工作流完成同一轮实测 |
| Harness Resolution 和知识 Recall 明确分离 | 部分实证 | 3B 有发布、采用、角色组合和工具授权实验；Recall 与 Capability Resolution 的产品入口分离仍需联测 |

### 2.5 场景 A 判断

场景 A 的核心边界成立：**项目资料应按来源直接读取；知识只在有长期复用价值时形成；团队经验只作为适用的补充依据；代码和 Harness 继续走各自路径。**

无需要求每个功能 Issue 强制调用 Knowledge Recall。真正需要补测的是：当任务明确需要历史团队经验时，Recall 是否能发现正确的正式知识 Claim，且不把 Project Source、代码摘要或 Harness 文档混入一个无差别结果列表。

## 3. 验收场景 B：跨项目经验复用

### 3.1 场景定义

- Project A：订单项目，发生 C1 返工并通过 C2 修复；
- Team Knowledge：从两份项目证据派生并独立发布的通用区域权限测试经验；
- Project B：另一个使用区域数据权限的项目，具有自己的业务规则和代码实现；
- Project B Issue：新增区域数据导出功能，需要决定是否采用该通用测试经验。

关键点：Project B 不应读取 Project A 的私有报告；它应当通过 Team Knowledge 取得经授权的通用结论，再结合 Project B 自己的 Project Sources、Project Knowledge 和代码依据。

### 3.2 正确的取得路径

| 依据 | Project B 的取得动作 | 不允许发生的事 |
|---|---|---|
| Project B Issue / Work Agreement | 确定性加载 | 不把 Project A 的 Issue 当作当前工作 |
| Team Knowledge | Knowledge Recall，Team 作用域 | 不因经验源自 A 就要求 B 读取 A 的私有报告 |
| Project B Knowledge | Knowledge Recall，限定 B | 不返回 Project A 的项目私有知识 |
| Project B PRD / 业务资料 | B 自己的 Source Search / Read | 不用 A 的业务规则替代 B 的规则 |
| Project B 代码 | B 自己的 Code Retrieval / 本地代码工具 | 不把 A 的模块地图当作 B 的实现 |
| Team Harness | Capability Resolution，核对 B 的采用和例外 | 不把 Team Knowledge 的建议自动升级为强制门禁 |

### 3.3 现有实验直接证明了什么

topic-03b/knowledge-contribution.md 已证明：
- 项目 A 的原始 C1 / C2 报告可以作为 Team Knowledge 派生依据；
- 派生给团队的内容可以只保留通用测试方法，不包含订单号、项目路径和审核账本；
- 团队读者获得批准的文案，但无权读取项目原始报告；
- 原始证据权限和派生文案受众权限彼此独立；
- 来源撤回、派生许可撤回和重新授权后的独立复审均有对照；
- 历史派发保持原正文摘要，撤回不会改写过去的共享事实。

这说明“跨项目派生可被安全治理”，但不是“Project B 的 Agent 已经成功 Recall 并使用该知识”。

### 3.4 场景 B 验收结果

| 验收点 | 结果 | 依据 / 缺口 |
|---|---|---|
| A 的经验提炼为 Team Knowledge | 已有实证 | C1 / C2 贡献实验 |
| 原始项目证据不向普通团队读者泄漏 | 已有实证 | team projection 与权限负向检查 |
| 派生许可撤回和重新审核 | 已有实证 | 45 + 5 项贡献检查 |
| Project B 通过 Knowledge Recall 找到 Team Knowledge | 未实证 | 现有夹具未建立 B 的真实消费者检索请求 |
| Recall 不返回 A 的私有 Project Knowledge / Source | 未实证 | 贡献实验验证可见投影和读取权限，不是 Recall 索引的完整隔离验收 |
| B 将 Team Knowledge 与自身规则组合 | 未实证 | 尚无 B 的 Issue、PRD、代码与 Team Claim 同轮输入记录 |
| B 的不同业务条件不会被 Team 经验覆盖 | 未实证 | 需要引入 B 的反例或适用条件差异进行真实检索和决策观察 |
| Team Knowledge 实际送达 B 的 Agent 并参与工作 | 未实证 | 缺少 B 的宿主输入与工具 / 产物引用 |

### 3.5 场景 B 判断

跨项目派生治理已有强证据，但跨项目消费仍然是当前最重要的实证缺口。

不能把“Team Knowledge 发布成功”当成“项目能正确消费”。必须验证 Project B 的接收者：
1. 能检索到 Team Knowledge 的正式版本；
2. 看不到 Project A 私有来源及其摘要；
3. 能读取自己的 Project Sources 和 Project Knowledge；
4. 能识别团队经验的适用条件和不适用条件；
5. 不会把建议知识当作强制 Harness Rule；
6. 在真实宿主请求中收到必要的知识正文或引用；
7. 能在产物、决策或工具调用中提供知识实际参与的证据。

## 4. 两场景共同暴露的产品设计要求

### 4.1 Recall 不应返回混合的“万能知识结果”

Recall 的结果应分成正式知识候选，至少标明：
- Team / Project 作用域；
- Knowledge Item 与 Revision / Release；
- Claim 和适用条件；
- 反例、限制和有效状态；
- Evidence 引用和原文当前可访问状态；
- 当前接收者是否可查看正文及证据。

Project Sources、Code Retrieval 和 Harness Resolution 应由各自 Provider 提供结果。统一入口可以展示多个来源分组，但不能用一个未经校准的全局相关性分数替代来源语义。

### 4.2 Knowledge Recall 命中不等于本次采用

Recall 返回候选后：
- Agent 可以展开读取；
- Agent / 负责人可以判断不适用；
- 实际选用的正式版本才进入本项工作引用；
- 高影响工作按已有规则固定版本；
- 无命中只表示当前知识检索未找到，不能推断 Project Sources 或代码仓也没有相关信息。

### 4.3 项目来源和团队知识不能互相代替

Project A 的经验被抽象为 Team Knowledge 后，Project B 应获得的是通用方法，不是 A 的完整业务背景。B 仍需读取 B 自己的 PRD 和业务规则。若通用方法与 B 的业务条件不适用，必须显示限制并允许不采用，而不是让团队知识自动覆盖项目事实。

### 4.4 宿主证据分层

两场景都使用统一证据区分：
- Selected：本次选了什么；
- Prepared：准备了什么；
- Delivered：投递到了哪个宿主入口；
- Loaded / Observed：宿主输入中实际出现了什么；
- Used：哪些工具调用、决策或产物能够证明使用；
- Outcome：本项交付是否通过。

某宿主无法观察到 Used 时保持 Unknown，不用“Recall 命中”或“Delivered”替代。

## 5. 下一轮必须补齐的 Recall 专项实验

这是本轮唯一建议继续的直接验证，不扩展为通用搜索平台研究。

### 5.1 建立最小可区分的测试语料

使用现有 C1 / C2 派生出的团队经验，再准备以下受控内容：
- Team Knowledge T1：区域账号和跨区账号分别核对数据集合，并独立验证付款时间字段；
- Project A Knowledge A1：订单项目自己的区域订单授权规则；
- Project A Source A-S1：包含项目私有标识的 C1 / C2 原始报告；
- Project B Knowledge B1：采用组织树授权的另一种项目业务规则；
- Project B Source B-S1：Project B 自己的 PRD；
- Project Code B-C1：Project B 的代码模块 / 调用关系；
- Team Harness H1：一项需要明确发布与采用的强制检查规则（与 T1 经验知识区分）。

测试语料必须保留明确的项目归属、来源授权、受众和适用条件。T1 不包含 Project A 的私有标识；A-S1 仍只对 Project A 授权成员可见。

### 5.2 必须执行的查询和负向对照

| 查询主体 / 任务 | 预期结果 | 必须拒绝或不返回 |
|---|---|---|
| Project A 开发者：订单导出权限改造 | T1、A1；按需读取 A-S1 的获准段落 | 无关 Team / Project 知识 |
| Project B 开发者：区域数据导出 | T1、B1；按需读取 B-S1 和 B-C1 | A1、A-S1、A 的报告摘要和项目标识 |
| 非项目成员：搜索 A 的私有订单规则 | 不返回任何可推断 A 私有内容的标题、摘要、关系或结果 | A1 / A-S1 的所有派生索引痕迹 |
| Project B：只询问组织树授权规则 | B1 优先提供 | 不因 T1 语义相似就将其误认为 B 的具体业务规则 |
| Project B：查询当前必须执行的强制检查 | 解析 H1 是否发布、是否被 B 采用 | 不以 Recall 命中 T1 或 H1 文档替代采用状态 |
| Project B：检索一个无相关知识的任务 | 明确无 Knowledge Recall 命中 | 不得推断 B 的 PRD、代码或 Harness 不存在 |

### 5.3 实际宿主验证

至少选一个真实宿主完成完整输入观察；优先复用已有 Codex 0.144.6 探针。再选择一个不同宿主（Claude Code / Qoder / CodeBuddy）验证同一接收者和相同授权下的能力差异。

需要保存：
- 查询文本和接收者身份；
- 知识检索候选及作用域过滤结果；
- 每个返回项的 Knowledge Item / Revision / Release；
- 展开读取的 Evidence 引用和来源当前读权；
- 明确选择 / 不选择的结果；
- 实际宿主请求中的正文或引用位置及摘要；
- 后续工具调用、决策或制品对知识的引用；
- 撤权后再次检索和新线程输入；
- 各宿主无法观察到的层级及原因。

### 5.4 通过标准

- 任何 Project A 私有内容均不出现在 Project B 或无权主体的结果、摘要、关系或宿主请求中；
- Team Knowledge T1 在适用任务中可被 B 找到，但不覆盖 B1 的项目特定规则；
- Project B 的 Source 和 Code 检索能够补充 Team Knowledge，而不是被 Knowledge Recall 替代；
- Recall 无命中不阻断 Agent 使用其他来源；
- Harness 的强制性由发布和项目采用决定，不由知识排序决定；
- 实际宿主输入与平台所记录的 Selected / Delivered 内容一致；
- 撤权后不再新投递，历史已送达内容如实保留；
- 无法证明的实际使用状态保持 Unknown。

## 6. 现有实验与本轮判断的证据分级

| 结论 | 证据类型 | 当前状态 |
|---|---|---|
| 项目资料可直接按角色读取 | Codex 真实请求探针 + 来源模拟实验 | 已实证 |
| 来源修订后在途工作重新选择 | 固定修订、影响映射和宿主请求观察 | 已实证 |
| 权限撤回后新投递被阻止 | Multica PostgreSQL 权限实测 + 宿主线程对照 | 已实证 |
| 项目证据可派生为团队知识 | 45 项贡献检查 + 5 项单来源撤回回归 | 已实证 |
| Team Knowledge 可被另一个 Project 的 Agent 通过 Recall 正确发现 | 尚无目标消费者的真实 Recall 输入 | 未验证 |
| Recall 结果不会泄漏 Project A 私有内容 | 贡献投影 / 权限测试存在，但 Recall 结果层未全量验收 | 部分证据、未通过产品验收 |
| Team / Project Knowledge 的多源结果组合优于全局 Top-K | 架构推断 | 待验证 |
| 不同宿主的 Recall / Source / Code 工具调用一致 | 既有宿主能力实证不覆盖新 Recall 产品入口 | 待验证 |

## 7. 最终判断与下一步

当前可以确认：
- Context Contract 的业务职责边界是合理的；
- Recall 不应该等于所有资料的统一检索；
- Knowledge Recall、Source Search / Read、Code Retrieval、确定性 Work Context 和 Harness Resolution 必须保留不同语义；
- Team Knowledge 和 Project Knowledge 共用知识机制但不共用默认作用域；
- Topic 3B 已证明很多关键的权限、修订、派生、真实宿主输入和交付约束。

当前不能确认：
- AgentPlatform 的 Knowledge Recall 已经形成可用产品能力；
- 跨项目 Team Knowledge 能被目标 Project 的 Agent 正确发现和使用；
- 一个统一入口能在真实任务中正确编排各来源，而不产生泄漏、误覆盖和上下文膨胀。

**下一步不再扩大 Context Contract 设计，而是专门补齐 Knowledge Recall 的双项目检索与真实宿主消费实验。** 这次实验应以已有 C1 / C2 派生经验为 Team Knowledge 样本，建立一个具有不同业务模型的 Project B，直接验证发现、隔离、组合和实际使用。

这不是进入技术选型或工程实现，而是把现有业务契约转成可判定的产品验收。


## 8. Recall 双项目契约实验的实际执行结果

随后新增并执行了[Knowledge Recall 双项目隔离实验](context-recall-two-project-experiment.md)。该实验使用 T1 / A1 / A-S1 / B1 / B-S1 / B-C1 / H1 最小语料，在确定性 Provider 模拟下检查作用域、权限、结果元数据、Evidence 可见性、来源分流和 Harness 采用边界。

GitHub Actions 实际执行 **20 / 20 项断言通过**。其中 Project A 返回 T1 + A1，Project B 返回 T1 + B1，非成员无私有知识结果；Project B 的 PRD 与代码检索分别只返回 B-S1、B-C1；未采用的 H1 不会通过能力解析，显式采用后才可解析；团队成员资格撤销和 Team 派生授权暂停分别阻止后续 T1 召回。

必须保留实验限制：这是契约级确定性 Provider 模拟，不是生产检索算法、真实 Connector 权限或真实 Agent 宿主输入测试。它验证了结果边界和过滤次序，不验证语义 Recall 质量。

因此双场景验收状态更新为：
- 来源、权限、版本、角色化读取、知识派生和真实宿主执行基础：已有 Topic 3B 实证；
- Recall 的 Team / Project 作用域与私有元数据隔离：契约模拟通过；
- 真实 Knowledge Recall Provider、跨项目真实消费者和宿主实际使用：仍未验收。

下一步应将确定性候选替换为真实知识检索入口并接入至少一个真实 Agent 宿主，继续使用相同双项目负向用例，不重新扩大产品范围。
