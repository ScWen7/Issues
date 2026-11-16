# D7 · 持续改进内循环的上游机制与平台映射

> 本文从既有 LoopForge、TeamAI 和 AgentPlatform 源码研究中提炼 D7 机制，不重复抄录完整源码报告。
> LoopForge 研究基准见[LoopForge SOP 生命周期研究](loopforge-sop-lifecycle.md)；TeamAI 真实宿主与资产发布实验见[专题三 B 实证](03b-source-evidence.md)；平台计量现状见[成本、质量评价与持续改进](../architecture/04-cost-quality-improvement.md)。

## 1. 结论

三个来源提供的是不同环节的能力，不能整体照搬成一个产品：

- **LoopForge** 证明流程执行可以产生独立评价；评价结果可以给出受限、可审查的局部建议；更大范围的流程改动需要固定样本、对照和新版本发布。
- **TeamAI** 证明方法资产有明确版本、项目覆盖、发布与采用边界；实际宿主输入、来源修订、权限和交接都必须有证据，不能把本地文件变化当作所有 Agent 已经使用。
- **AgentPlatform / Multica** 提供真实业务工作、Run、Runtime、Issue、Candidate、Usage 和项目责任的权威归属。评价和改进应沿这条主线接入，而不是再造一套执行队列。

持续改进的核心不是“模型自动写 Skill”，而是**让真实工作形成可复核的证据，再让经过对照和审核的改变进入后续工作，最后从实际使用结果验证是否真的改善。**

## 2. LoopForge 值得吸收的具体机制

### 2.1 Run Evaluation 与生产执行分离

LoopForge 已完成 Run 可以独立发起 LLM 质量评价。评价输入读取具体 Run / Step / Pass 及对应 Scorer 版本，输出 Score、Dimensions、Findings 和 Recommendations。

关键设计：
- 评价有自己的执行和结果身份，不改写原生产 Run；
- 评价启动失败与被评执行失败是两件事；
- Findings 应指向具体节点和证据，不只给一个总体分；
- 评价模型不是业务验收人，评分通过也不自动接受 Candidate。

AgentPlatform 应复用 Multica 原生 Run 承载评价活动，引用被评 Run / Candidate；评价 Usage 归评价 Run，不计入生产 Run。

源码入口：internal/runeval/prompt.go、internal/runeval/apply.go、internal/httpapi/run_eval.go。详见[LoopForge Run Evaluation](loopforge-sop-lifecycle.md#62-run-evaluation)。

### 2.2 评价建议应用受限

LoopForge 的 Run Evaluation 不允许评价模型整份重写 SOP。当前可应用建议主要限制在：
- 节点 maxAttempts、maxReworks、onFailure、retryStrategy 等局部参数；
- Agent 角色指令补充；
- Agent Verification Gate 的新增或移除。

用户选择建议后才应用；跨项目或通用模板先复制为项目级副本，避免直接污染共享定义。

这给 AgentPlatform 的启发是：**评价器只提出结构化建议，建议修改对象和允许修改范围由平台定义。** 局部参数优化与流程结构重构必须分开，不能让评分模型直接改 DAG、删除节点或覆盖已发布版本。

### 2.3 大范围改动走 Benchmark 与版本审核

LoopForge 的研究还表明，节点增删、依赖重构、并行关系改变和交付阶段变化不是参数补丁。它们需要：
- 多个有代表性的执行样本；
- 明确的新旧方案比较；
- 回归或 Benchmark；
- 维护者审核和发布新版本。

不能把 LoopForge 当前的受限建议应用夸大成全自动 DAG 重构和自动发布。其成熟启发恰恰是把局部建议和结构性演进分开。

### 2.4 Benchmark 比较条件必须固定

既有研究中的 Benchmark 先生成试验定义，再独立启动评分，最后汇总。配对比较会排除题目摘要变化；当双方均由模型判定时，还会核对 Rubric、工具、模型、effort 和评分方式。

默认自改进流程从可复现、尚未被回归样本覆盖的失败中筛选输入，达到阈值后才在专用分支生成改动并交付 PR。失败样本应转成回归题，但题目质量与实际修改仍需独立判断。

平台应把这套机制抽象为：固定基线、候选、样本、评价器、实验变量、成功标准和覆盖范围；不在不可比条件下宣称改善。

源码与流程：workflows/teamai-benchmark.yaml、src/benchmark/pairing.ts、src/self-improvement.ts、workflows/teamai-self-improvement.yaml。详见[LoopForge T8](loopforge-sop-lifecycle.md#63-更大范围的流程演进)。

## 3. TeamAI 值得吸收的具体机制

TeamAI 的价值不在于复制 Git 独立知识库或 CLI，而是它对方法资产的版本、范围、发布、拉取、实际投递和使用证据的处理。

既有实证说明：
- 团队默认资产与项目覆盖可以并存，项目覆盖需要明确指向关系；
- 同名 Rule 可以在不同活跃命名空间中分别交付；
- 发布、评审、合并、pull、startup / resume Hook 是不同动作；
- pull 成功不等于 Agent 一定收到新版本，必须读回并核对实际落地版本；
- 已在途的工作继续引用旧版本，新版本通过后续明确采用生效；
- 权限撤回、源修订和同字节恢复都需要重新判断来源授权与有效性。

这直接支持 D7 的两个分离：
1. Release 不是 Adoption；
2. Adoption 不是实际 Usage。

后续工作要记录实际使用的资产版本和来源；不能只凭项目默认配置推断 Agent 已收到或实际采用。

来源：[TeamAI 发布与选用实证](03b-source-evidence.md#三库实跑了什么) · [角色取材记录](03b-source-evidence.md#角色取材)。

## 4. 映射到 AgentPlatform 的完整内循环

| 环节 | LoopForge 机制 | TeamAI 机制 | AgentPlatform 的权威事实 / 责任 |
|---|---|---|---|
| 真实生产 | SOP Run / NodeRun / Artifact | 工作流步骤与宿主活动 | Issue、Run、Node Activation / Attempt、Artifact / Candidate |
| 事实观察 | Run 状态、节点结果、Trace | Driver / Observation / 实际输入回执 | Multica Run、宿主来源证据、Usage、Candidate / Evidence |
| 单次评价 | Run Evaluation / Scorer | 可复用规则与核验方法 | 独立 Evaluation 及其 Run，引用被评对象 |
| 问题归纳 | Findings / Recommendations | 经验与方法资产治理 | Finding 归源 Issue / Run，维护者分诊 |
| 候选修改 | 受限局部建议、流程候选 | 资产修订、项目覆盖 | Improvement Proposal + 候选资产修订 |
| 对照验证 | Benchmark / 回归样本 | 实际版本投递与核对 | 固定样本、Rubric、环境、候选和成功标准 |
| 发布 | 新 SOP / 资产版本 | 版本发布与审核 | 资产维护者发布不可变 Release |
| 采用 | 新 Run 选择发布版本 | 项目默认或显式覆盖 | Project Adoption / Issue 选择，并记录实际投递版本 |
| 效果回收 | 后续 Run 评价 | 真实使用与来源时效 | 后续生产 Issue / Run 的质量、返工、人工介入和可知成本 |

## 5. 为什么这不是一个自动学习飞轮

闭环需要有控制点，不是每一步都自动：

- 事实采集可自动化，但必须尊重来源权限和可观察边界；
- Evaluation 可以按门禁、抽样或人工请求触发；
- Finding 归并和根因分析可由 Agent 辅助，但维护者决定是否跨工作推广；
- 候选生成可以自动化，但必须限定修改对象和权限；
- Benchmark 可自动执行，但成功标准、可比性和风险阈值需预先固定；
- Release 必须由相应资产维护者审核；
- Project Adoption 必须由有权成员决定；
- 生产效果可持续回收，但样本不足时保持待观察，不能自动宣布成功。

否则系统会形成自证偏差：模型提出改动、模型挑样本、模型评分、模型宣布改进、模型把改动推广给自己使用，却没有独立基准和责任人。

## 6. 对现有架构的增量结论

现有核心对象已经包含 Evaluation、Finding、Improvement Proposal、Benchmark、Release 和 Project Adoption。D7 不需要再新增一套对象或执行引擎，主要是把它们之间的门槛和责任关系收敛：

1. 生产 Run 与评价 / Benchmark Run 分开归属；
2. Finding 必须引用真实来源和证据；
3. Proposal 固定基线、候选、范围、预期改善和潜在退化；
4. Benchmark 固定样本、Rubric、环境和可比性；
5. Release、Adoption、实际 Usage 分开记录；
6. 发布后按真实生产结果决定扩大、暂停或回退；
7. 任何改进都不绕过 Issue 责任、Candidate 验收、资产权限和项目采用。

这些规则已汇总到[持续改进内循环契约](../architecture/d7-continuous-improvement-loop.md)。
