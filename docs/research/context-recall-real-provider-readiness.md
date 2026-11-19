# AgentPlatform · 真实 Recall Provider 可用性审查与本地验证边界

> 审查状态：完成  
> 分支：design/system-architecture-convergence  
> 目标：确认仓库中是否已有可供 AgentPlatform 双项目 Recall 实验直接调用的真实知识检索入口，并划清云端研究与成员本地宿主实测的边界。  
> 非目标：不新建生产 Recall 服务，不做数据库 / API / 部署选型。

## 1. 结论

**当前仓库没有可直接调用的 AgentPlatform 生产级 Knowledge Recall Provider。**

现有材料包含：
1. Team / Project Knowledge 的业务对象和生命周期设计；
2. Topic 3B 的项目来源读取、角色范围过滤、权限复核和真实 Codex 输入观察研究原型；
3. C1 / C2 项目证据派生团队知识的授权、审核、发布和撤回实验；
4. 本轮新增的双项目 Recall 契约模拟。

但尚未发现一个把正式 Knowledge Item / Revision / Release 作为真实数据源、能够由 AgentPlatform Agent 在工作中调用的通用 Knowledge Recall 运行入口。不能把已有原型或本轮确定性 Provider 模拟称为真实 Recall Provider。

因此，本轮能由研究环境继续完成的是代码与对象审计、产品行为契约、测试夹具、验收脚本、文档和仓库回归；真实 AgentPlatform Recall 产品行为必须等真实 Provider 可调用后才能实测。真实 Codex / Claude Code 本地模型请求的观察，也需要成员本地宿主环境或已授权的真实执行环境。

## 2. 仓库现有实现的真实边界

### 2.1 Knowledge 对象目前处于架构模型层

core-business-object-model.md 已定义：
- Knowledge Item；
- Knowledge Revision；
- Knowledge Release；
- Knowledge Feedback；
- Evidence / Evidence Anchor；
- Team / Project 作用域；
- Work / Run Asset Pin 与 ContextReceipt / Asset Usage Observation。

这些定义足以表达 Recall 应该返回什么、引用什么版本和证据，但它们本身不是可调用的查询实现。

### 2.2 source_context.py 是项目来源研究原型，不是正式 Knowledge Recall

prototypes/topic-03b/knowledge/source_context.py 实现：
- 合成 Docx 来源分页读取和章节解析；
- 模拟来源修订与读取权限；
- 依据预先绑定的 Project / Role / Run 选择允许的来源章节；
- 在章节标题 / 正文中进行简单子串匹配；
- 返回章节引用、修订、块 ID 和正文摘要；
- 在来源变化或权限变化时拒绝旧选择和新投递。

其 Assembly.lookup() 的搜索范围是预先配置的项目、角色与来源章节计划。它没有：
- Team / Project Knowledge Item / Revision / Release 的通用查询入口；
- Team Knowledge 与 Project Knowledge 的跨作用域 Recall；
- 基于 Claim 的正式知识候选排序；
- 知识适用范围和 Evidence 可见性组合过滤；
- 可供任意 Agent 宿主调用的 AgentPlatform 工具入口。

它证明的是 Project Source 的受限检索、角色化读取和来源修订治理，不是正式 Knowledge Recall。

### 2.3 order_knowledge.py 与 contribution.py 是研究驱动程序

- order_knowledge.py 组合合成项目来源、角色计划、来源权限时钟和真实 Codex CLI 请求观察。
- contribution.py 对 C1 / C2 固定证据执行派生许可、受众授权、团队复审、发布、撤回和复审回归。

两者可复用案例和验证规则，但它们没有提供一个供任意 Issue / Agent 查询 Team / Project Knowledge 的长期运行 Provider。

### 2.4 two_project_contract.py 是确定性契约模拟

本轮脚本以 JSON fixture 模拟 Team / Project 知识、来源、代码和 Harness Provider。它验证：
- 作用域过滤先于候选序列化；
- Project A / B 的结果隔离；
- Team 派生文案和原始 Evidence 分权；
- Source / Code / Harness 各走独立路径；
- 成员撤权和派生许可撤回后的新 Recall 资格。

脚本内的词法匹配仅是最小确定性测试逻辑。它没有连接 AgentPlatform 数据、外部来源系统或本地 Agent 工具。20 / 20 通过仅代表契约模拟通过。

## 3. 现有真实宿主证据覆盖到哪里

| 已有实验 | 已证明 | 没有证明 |
|---|---|---|
| Codex CLI 0.144.6 Responses 观察 | 精确章节正文实际进入模型请求；历史线程保留旧输入；新线程可以按当前授权重建 | Codex 能通过 AgentPlatform Knowledge Recall 查询正式 Team / Project Knowledge |
| Multica 项目撤权测试 | 项目访问撤销后任务主体读取被拒，索引变化可被观察 | 所有知识 Provider 在真实召回时都正确按当前接收者过滤 |
| C1 / C2 知识贡献实验 | 项目证据可在逐来源许可、去敏和独立复审后形成团队派生知识 | 另一个真实 Project 的 Agent 能通过 Recall 找到并使用该派生知识 |
| Codex / Claude Code 跨宿主工具实验 | 不同宿主可以实际调用被授权工具并形成可关联结果 | 两个宿主都已接入 AgentPlatform Knowledge Recall |
| Recall 契约模拟 | 双项目作用域、元数据隔离和独立 Provider 语义可被自动回归 | 生产搜索质量、真实连接器鉴权、真实宿主输入和知识使用 |

## 4. 我可以不依赖本地环境继续完成的工作

- 继续审查仓库中 Knowledge、Source、Evidence、ContextReceipt、Asset Pin 的对象和契约一致性；
- 维护双项目测试语料、正负向测试和 CI；
- 检查架构文档是否把模拟能力误写成生产能力；
- 设计真实 Recall Provider 的最小产品行为契约和验收接口，但不提前选择数据库或搜索引擎；
- 编写本地宿主探针和回执解析器；
- 对用户上传的本地回执做分析、交叉核验和修正建议；
- 当仓库出现真实 Provider 或连接器实现时，直接审查源码并扩展自动测试。

## 5. 哪些工作必须在真实成员环境完成

以下动作需要真实 AgentPlatform Provider、来源权限和宿主运行时，不能由纯文档或确定性模拟替代：

1. 在真实 Team / Project Knowledge 数据上执行 Recall；
2. 以 Project B 成员身份检查是否能检索 T1、B1，且看不到 A1 / A-S1 的任何元数据；
3. 展开 T1 的 Evidence，验证派生文案可读而原始 C1 / C2 报告不可读；
4. 使用 Project B 自己的 PRD 和代码检索补充团队经验；
5. 将实际选用的知识投递到 Codex / Claude Code / Qoder / CodeBuddy；
6. 检查模型实际收到的请求输入；
7. 观察知识是否参与工具调用、决定或产物；
8. 撤销 Team 成员资格或来源派生许可，再次执行 Recall 和投递；
9. 证明已送达历史和新投递资格的差异。

若当前没有可调用的 AgentPlatform Recall Provider，以上步骤不能通过本地随便运行一个 Codex 命令来替代。此时应先在整体架构中确认真实 Provider 的业务承载和调用归属，再做本地宿主实验；不要为测试临时造一套平行 Recall 服务。

## 6. 建议的协作方式

### 我负责
- 先完成仓库内真实 Provider 缺口审查；
- 继续完善最小测试夹具和可复跑脚本；
- 在真实 Provider 出现前，不虚报 Recall 真实产品验收；
- 设计最小本地验证命令和机器可读回执格式，避免你手工整理日志。

### 你只需在必要时负责
- 提供真实 Provider 的运行入口 / 环境；
- 运行我准备好的本地探针；
- 在需要真实账号、项目权限或本机宿主时完成授权和执行；
- 将脚本生成的回执交给我分析。

不需要你自己重做研究、重新设计测试或手工编写报告。

## 7. 下一步决策

当前最重要的下一步不是让成员立即在本地执行一套没有真实 Provider 的 Recall 测试。

先回到 AgentPlatform 整体架构，明确：
- Knowledge Item / Revision / Release 的权威读取入口在哪里；
- Team / Project 范围与成员权限由谁在检索前提供；
- Knowledge Recall 作为 Agent 可调用能力归属于哪一层；
- Recall 返回结果如何被现有 Context Contract 选择和引用；
- Project Sources / Code Retrieval 为什么继续由各自 Provider 提供；
- 本地宿主通过什么现有授权工具取得结果，而不是新建一套独立知识服务。

这属于现有知识能力如何进入工作台主线的产品 / 业务承载审查，不是数据库或搜索技术选型。

**结论：我可以继续推进仓库审查、产品契约、测试和文档；你只需要在真实 Provider 和本地宿主不可替代的环节参与。当前真实 Recall Provider 缺位，应先如实补齐架构承载设计，不应让你先去跑一个实际上不存在的产品入口。**


## 8. Knowledge Recall 的架构承载审查结论

后续形成[Knowledge Recall 的能力归属与调用承载审查](knowledge-recall-ownership-and-invocation.md)，并将关键规则同步到跨层业务契约和知识管理生命周期。

职责归属明确为：
- A · 团队知识管理拥有正式 Team / Project Knowledge 的查询与读取权威；
- B · 产研工作与流程协作以 Issue / Work Agreement 决定是否触发 Recall、候选是否适用及是否纳入本项工作；
- D · 执行与交付证据负责通过现有宿主适配通道投递获准内容并记录实际消费证据；
- C · Harness 治理独立解析发布、采用和执行资格。

Recall 可由工作准备阶段或 Agent 执行中主动触发，不要求每个 Issue 必须执行。它不是独立能力域、Recall Runtime、Issue / Task / Run 或 Context Compiler。Agent 不能自行声明 Team / Project scope，身份与授权必须由现有受信任工作 / 宿主上下文提供。

当前缺口因此被准确定位为：**A 域尚未形成可供 B 和获准 Agent 调用的正式 Knowledge Recall / Read 能力实现**，而不是缺少一个新的统一搜索服务。真实 Provider 出现前，双项目 20 / 20 测试仍然只是契约模拟；本地宿主验证应等 A 域真实读取入口可用后再执行。
