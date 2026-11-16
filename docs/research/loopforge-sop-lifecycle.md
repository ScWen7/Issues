# LoopForge SOP 形成、使用与演进机制调研

> 研究对象：Tencent/LoopForge 的 SOP 与 Main Bot 源码机制。
> 本次源码复核基准（2026-11-16）：LoopForge `97b3cdc2f29a88e8767a8dc6c03bfb8865622653`。原稿未记录提交号，本文固定链接对应此次复核，不追认原始研究所用版本。
> 研究用途：为 AgentPlatform 的 SOP 专题提供机制参考。本文记录 LoopForge 已实现的机制与对 AgentPlatform 的设计启发，不将其全部视为 AgentPlatform 已决策方案。

## 1. 核心认识

LoopForge 的 SOP（源码中的 WorkflowDefinition）不是单纯的预设流程模板，也不是任意一次 Agent 对话的自动归档。它是将一类交付方法表达为可执行、可版本化、可观察、可返工和可持续修订的流程定义。

其生命周期包含四个相互关联但不同的部分：

1. 形成：模板复制、人工设计、AI 自然语言编排生成草稿。
2. 固化：编辑定义、校验、保存修订、发布版本。
3. 使用：选择 SOP、创建 Run、冻结执行快照、按节点依赖执行、消费产物、处理失败和人工介入。
4. 演进：基于运行事实和评价提出局部建议，维护者决定是否修改、发布新版本，供后续工作采用。

不能把“AI 生成了草稿”“SOP 已发布”“一次 Run 成功”“SOP 已被证明有效”视为同一件事。

## 2. SOP 如何产生

LoopForge 当前至少支持三条明确创建路径。

### 2.1 从模板复制

- 内置通用模板和项目 SOP 可作为起点。
- 创建向导提供名称、负责人、标签、说明和沙箱选择，可选择模板或空白流程；负责人等信息可留空。
- 通用模板复制到具体项目时，不只复制节点图，还会把模板依赖的 Agent 角色复制到项目，并将节点的 agentId 重映射到项目角色。
- 复制结果成为项目自己的 draft，可继续编辑；模板本身不因项目使用而被修改。
- 复制时同时处理项目可用沙箱、模板声明的 requirements 和默认 MCP 依赖。

关键源码：
- `web/app/flows.js`：`openSOPWizard`、`createSOPFromWizard`、`cloneWorkflow`
- `internal/httpapi/generic_workflows.go`：`adoptGenericWorkflow`
- `internal/httpapi/catalog.go`：`/api/workflows/:id/clone`

### 2.2 从空白人工设计

- 用户可以新建空白 WorkflowDefinition。
- 在可视化设计器中添加 Agent、Script、Approval、Sub-SOP 等节点。
- 通过 Edges 描述成功路径依赖；通过节点配置声明角色、脚本、产物、执行范围、失败策略、重试和返工参数。
- 保存时进行定义校验和乐观修订冲突检查。
- 发布动作与保存草稿分离。

关键源码：
- `web/app/flows.js`：`newWorkflow`、`addNode`、`saveWorkflow`、`publishWorkflow`
- `internal/domain/workflow.go`：`WorkflowDefinition`、`WorkflowNode`、`WorkflowEdge`
- `internal/repo/catalog.go`：`PutWorkflow`、`PublishWorkflow`

### 2.3 AI 自然语言编排

LoopForge 有专门的 AI Orchestrator：

- 用户用自然语言描述要构建或修改的流程。
- 编排器将当前项目、已有角色、可引用的 SOP 和当前画布内容提供给模型。
- AI 返回一个 `workflows_save` 草稿，内容是节点和边组成的完整 Workflow 定义。
- 前端把草稿呈现在流程画布上；用户可以继续自然语言修改或手动调整。
- 修改已有流程时要求保留未要求变更的节点、连线、ID 和脚本，做增量修改。
- 流程画布的 AI Orchestrator 请求显式使用确认模式，只接收 `workflows_save` 草稿；保存和发布沿设计器各自的入口进行。普通 Main Bot 对话另按所选审批模式处理写入。

关键源码：
- `web/orchestrate.js`：`aiOrchestratePrompt`、`runAIOrchestrator`、`completeAIEdit`
- `webtest/tests/orchestrate-ai.test.mjs`：验证 AI 草稿能转成画布定义
- `internal/httpapi/assistant.go`：助手草稿协议、SOP 角色绑定约束

重要边界：AI 生成的是定义草稿，不是自动发布，也不是实践有效性的证明。当前生成协议要求 Agent 节点绑定项目中已有角色；缺少角色时应先创建角色资产。AI 修改已有 SOP 前要读取完整定义，因为保存接口会按完整 nodes / edges 覆盖定义。

### 2.4 实践提炼不是已实现的自动生成通道

LoopForge 具备从 Run 评价中发现问题、提出并应用有限修改建议的能力，但不能据此声称它已把任意成功 Run 自动提炼成一条全新 SOP。

更准确的区别：
- AI Orchestrator：从自然语言意图生成或修改流程草稿。
- Run Evaluation：从已完成执行中识别质量问题并提出受限补丁。
- 人工维护与发布：决定哪些改动应成为未来正式流程版本。

将成功实践提炼为新 SOP，仍需要专门的样本筛选、规律归纳、流程抽象、验证和发布机制；这正是 AgentPlatform 后续需要独立研究的方向。

## 3. SOP 定义表达什么

核心对象是 `WorkflowDefinition`，不是 Run。

- WorkflowDefinition：流程名称、说明、项目范围、版本、修订、发布状态、沙箱、节点和边。
- WorkflowNode：Agent / Script / Approval / SOP 节点；Agent 绑定角色；Script 定义确定性命令；Approval 表达人工门禁；SOP 节点引用子流程。
- WorkflowEdge：描述节点成功依赖。
- ArtifactContract：节点声明的产物名称、路径、媒体类型和是否必需。
- 失败与返工配置：`onFailure`、`rejectTo`、`retryStrategy`、`maxAttempts`、`maxReworks`、`carryOver`。
- Requirements：声明运行前必须具备的外部能力或凭据配置。
- Sandbox Profile：定义执行环境；启动 Run 时解析并冻结环境快照。

正常依赖图要求是 DAG。受控返工通过独立的 rejectTo 机制表达，而不是把普通依赖边绕成循环。

## 4. SOP 如何被使用

### 4.1 Definition → Run → NodeRun

- 选择一个 SOP 定义和版本。
- 输入具体需求和项目上下文。
- 创建 Run。
- Run 保存 WorkflowSnapshot，冻结本次执行使用的流程定义及沙箱资源。
- 为每个定义节点初始化 NodeRun 状态。
- 执行引擎根据节点依赖计算 readyNodes：只有所有直接前置节点 succeeded，pending 节点才就绪。
- 多个节点同时就绪时可以并行执行。
- 节点结果、产物、日志、遥测和用量写入本次 Run 记录。

源码：
- `internal/engine/run_start.go`：`startWorkflowDefinition`
- `internal/engine/workflow_graph.go`：`readyNodes`、`workflowForRun`
- `internal/domain/workflow.go`：定义与快照对象

### 4.2 结果消费与交付

节点完成状态、产物存在、产物符合契约、下游认可和最终用户验收是不同事实。不能把 Agent 返回成功或 Script 退出码为 0 自动等同于业务验收。

节点声明 Artifact Contract，下游节点可读取上游产物；Run 归集 Artifact 元数据、执行事实与交付结果。Issue dispatch 路径优先用于与 Issue 关联的工作，避免仅启动孤立 Run 而丢失业务归属。

### 4.3 失败、重试与返工

- `maxAttempts`：节点技术执行尝试边界。
- `maxReworks`：业务返工次数边界。
- `retryStrategy`：局部 targeted_fix 或 full_redo。
- `rejectTo`：失败结果退回指定上游节点。
- `carryOver`：向返工携带失败检查、最近错误、上游产物等上下文。
- Human Approval：等待人工批准或退回。

正常执行依赖和返工路径分开表达，避免 DAG 依赖环。

### 4.4 人工介入与接管

Main Bot / 人可以在 SOP Run 执行过程中介入：
- pause：在当前节点暂停。
- resume：带补充说明恢复流程。
- takeover：取消自动 SOP 执行，转为直接在其工作区处理。
- SOP 完成后再按交付机制提交代码或 MR。

因此 SOP 不是“启动后不可干预的黑盒流水线”；人工可以在流程中改变执行条件和后续推进方式。

## 5. Main Bot 与 Squad Leader 的类比

两者在功能上相似：都可以理解任务、规划工作、委派 Agent、汇总结果，并在合适时使用 SOP。

但它们的作用域不同：
- LoopForge Main Bot 是面向用户的主协调入口，管理对话上下文、工作区、Issue、Agent 委派、SOP 推荐 / 派发及运行中的介入。
- Multica Squad Leader 是一个 Squad 内部的协调主体，负责该 Squad 获得的工作及其成员协作；它不是平台级用户入口，也不应成为每个 Issue 的默认角色。
- Squad Leader 可以被视为一种作用域受限的 Coordinator；Main Bot 是用户侧 Coordinator。此处 Coordinator 是职责抽象，不意味着 AgentPlatform 必须新增一个中央常驻 Agent 或 Coordinator Pool。
- Squad Leader 与 SOP 的职责也不同：Leader 组织当前问题的动态协作；SOP 固化一类稳定、可重复的交付方法。Squad 可以局部调用 SOP，Issue 也可以直接委托 SOP 而不经过 Squad。

## 6. SOP 如何演进

### 6.1 定义版本与修订

- 草稿可多次保存，修改形成 revision。
- 发布形成 version，并记录 publishedRevision。
- Revision 支持查看和恢复。
- Run 冻结 WorkflowSnapshot，因此未来修改定义不会悄悄改变历史执行。
- 项目或 Issue 后续选择新版本，不会改写既有 Run 的历史版本。

### 6.2 Run Evaluation

已完成 Run 可以单独发起 LLM 质量评价。评价输入包括结构化 facts 和压缩后的执行轨迹，输出包括：
- Score 和 Dimensions；
- Findings，要求指向具体节点和证据；
- Recommendations，提供可应用的改进建议。

当前可应用建议受到限制，主要包括：
- Workflow 节点的 maxAttempts、maxReworks、onFailure、retryStrategy 等配置调整；
- Agent 角色指令补充；
- Agent Verification Gate 的新增或移除。

评价模型被明确要求不要整份重写 SOP，不要改边或删除节点。用户选择建议后才应用；跨项目或通用模板会先复制为项目级副本，避免直接污染共享定义。

源码：
- `internal/runeval/prompt.go`
- `internal/runeval/apply.go`
- `internal/httpapi/run_eval.go`
- `internal/domain/run_eval.go`

### 6.3 更大范围的流程演进

如果变化涉及节点增删、依赖重构、并行关系改变或新的交付阶段，就不是简单的参数补丁。需要维护者基于多个执行样本和业务目标提出新的流程候选，比较新旧方案，做回归或 Benchmark，再审核发布。

LoopForge 当前具备流程编辑、版本修订、Run Evaluation 和受限建议应用等基础能力；不能把完整自动 DAG 重构与持续 Benchmark 自动发布描述为当前已经全自动实现的能力。

## 7. 对 AgentPlatform 的设计启发

1. SOP 的形成必须支持模板、人为设计和 AI 辅助生成，不应只支持维护者预先画好流程。
2. AI 生成 SOP 应先产出可审阅草稿，检查角色、工具、权限、产物契约、环境和依赖；不能直接把生成结果视为成熟 SOP。
3. 从实际执行提炼 SOP 是单独的能力：需要从多个有代表性的工作样本中归纳稳定步骤和分支条件，而不是把单次 Run 的轨迹原样转成流程。
4. SOP 应按适用范围管理：团队模板、项目版本和具体工作引用；项目复制应解决角色和能力绑定，不只复制节点图。
5. SOP 定义、发布版本、Run 快照、节点执行事实、产物、评价和项目采用必须分开记录。
6. Main Bot 负责本 Issue 的动态分工。遇到可重复且足够明确的环节时，可以把这部分委托给 SOP。
7. 执行引擎应处理确定性依赖、就绪判断、并行、等待、返工和人工门禁；Agent 仍负责节点内部无法完全预定义的判断。
8. 局部参数优化和流程结构演进分开处理；前者可由受限建议辅助，后者必须经过样本验证和版本审核。
9. 成本和质量评价从原 Run、产物和证据派生，评价自身消耗单独记录，不污染生产 Run。
10. 在 AgentPlatform 中应优先将 SOP Execution 映射到既有 Issue / Run / Multica 执行链，避免复制第二套任务和运行控制面。

## 8. 尚待 AgentPlatform 专题研究的问题

- 实际工作中哪些轨迹或重复模式具备提炼为 SOP 的价值？
- 如何识别“偶然路径”与“稳定方法”，需要多少样本和何种证据？
- 哪些参与者可以提出提炼建议，谁负责核对证据并维护候选 SOP？
- 如何将自由执行中的 Agent 委派、工具调用、检查和产物抽象成可复用节点，而不把某次 Session 细节固化进去？
- SOP 生成时如何抽象参数、适用条件、可变分支、角色能力和外部依赖？
- 何种证据足以从草稿晋级为候选、从候选晋级为已发布版本？
- 如何通过历史样本回放、Benchmark、影子执行或小范围项目采用验证新 SOP？
- 旧版本、项目定制版和团队通用版如何演进与回流，避免项目分叉后无法治理？
- 当 Main Bot 发现 SOP 不适用时，是局部偏离、暂停委托、创建改进建议，还是直接回到动态协作？如何记录偏离原因？
- SOP 执行的确定性与 Agent 自主判断的边界如何表达？

## 9. 本文使用的源码入口

本次复核核对了模板复制与角色重映射、创建 / 保存 / 发布、AI 画布草稿、执行快照及依赖判断、受限评价建议、Main Bot 推荐与审批模式。以下入口均存在于上述固定提交；本次取证为源码阅读，运行效果沿各专题的实验记录判断。

- [LoopForge README](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/README.md)
- [SOP Designer](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/web/app/flows.js)
- [AI Orchestrator](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/web/orchestrate.js)
- [Main Bot 推荐与审批协议](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/httpapi/assistant.go#L1018-L1058)
- [Issue dispatch 与直接启动](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/docs/api/orchestration.md#L90-L107)
- [平台操作定义](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/application/operations.go)
- [Workflow Domain](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/domain/workflow.go)
- [Workflow Graph](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/workflow_graph.go)
- [Run Start](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/run_start.go)
- [Generic Workflow Adoption](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/httpapi/generic_workflows.go)
- [Workflow Catalog](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/repo/catalog.go)
- [Run Evaluation Prompt](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/runeval/prompt.go)
- [Run Evaluation Apply](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/runeval/apply.go)
- [Run Evaluation API](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/httpapi/run_eval.go)
- [Conversation Workspaces](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/docs/conversation-workspaces.md)


## 10. Main Bot 如何判断和使用 SOP

LoopForge 不只有 SOP 目录和手动启动入口。Main Bot 的自然语言助手还承担需求与 SOP 之间的匹配工作：

- 根据需求性质和当前项目绑定情况，给出明确的 SOP 推荐。
- 提示词列出产品、前端、后端三套通用模板，并要求读取实际 SOP 定义后结合需求推荐；产品探索与编码交付分别选用适合的方法。
- 前后端都需要时，Main Bot 的指引允许先用产品 SOP 定型，再分别派发前端和后端 SOP。
- Main Bot 的提示词要求用户明确请求执行后，按当前审批模式操作。确认模式提交待确认草稿；完全权限模式直接调用平台写入工具；“帮我批准”模式交独立审批判断，未获批的平台写入转为草稿。
- 已保存为 Issue 的工作，接口文档指引优先用 Issue dispatch 建立工作关联；`runs_start` 同时保留直接启动 SOP 的入口。
- Main Bot 仍可以在执行过程中读取状态、解释节点、暂停、恢复或接管工作区。

这说明 SOP 使用不是简单的“有 Issue 就运行绑定工作流”。在自然语言交互中，Main Bot 的指引将工作类型判断、方法推荐和获准执行分开。以上推荐和执行意图约束来自提示词；实际写入还取决于审批模式与工具结果。

证据入口：
- `internal/httpapi/assistant.go`：`assistantNativeSystemPrompt` 的 SOP 推荐、`assistantDraftProtocolPrompt` / `assistantAutoWriteProtocolPrompt` / `assistantAssistedProtocolPrompt` 的写入协议。
- `docs/api/orchestration.md`：Issue dispatch 优先用于保存为 Issue 的工作，以建立 Task / Issue 关联。
- `internal/application/operations.go`：`issues_dispatch`、`issues_save` 与 `runs_start` 的平台操作定义。
- `docs/conversation-workspaces.md`：Main Bot 在 SOP 执行中介入的 pause / resume / takeover 语义。

## 11. 对 AgentPlatform 的补充启发：SOP 选择也属于形成机制的一部分

形成 SOP 不只包括“如何写出 WorkflowDefinition”，还包括“什么时候认为某类工作适合采用已有 SOP”。

因此需要把以下动作分开：
1. **识别工作类型**：从 Issue 目标、约束、资料和工作上下文判断它属于什么类型，确定是否稳定到适合使用 SOP。
2. **推荐已有 SOP**：按项目采用范围、适用条件、所需能力和版本状态筛选候选。
3. **解释匹配依据与差异**：说明候选流程覆盖了什么、没有覆盖什么、有哪些前置依赖。
4. **获得使用授权**：需要时由 Issue 负责人确认采用；拒绝或不适用时回到动态协作。
5. **启动既有版本**：在 Issue 上记录本次使用的 SOP 版本和授权范围，沿原 Run 链执行。
6. **发现不适用并反馈**：若执行中出现偏离，记录原因和未覆盖工作；不要为迁就 SOP 而强行套用。

因此 SOP 的完整生命周期至少包括：形成 / 提炼 → 审核固化 → 适用范围发布 → 工作识别与选择 → 授权执行 → 结果消费 → 评价反馈 → 修订与再发布。
