# Team Agent Collaboration Platform
# 产品架构设计输入 V1

## 1. 项目定位

建设一套面向研发团队的 Agent Native Engineering Workspace（Agent 原生研发协作工作台）。

平台连接团队成员与各自本地的 Agent 执行环境，让 Human、Agent、Squad 能够共同参与研发工作，实现从需求输入、任务规划、协作执行、质量验证、交付到团队能力持续进化的完整闭环。

核心目标：

1. 支持团队成员共同管理和推进研发工作。
2. 支持 Human、Agent、Squad 三种工作负责人模式。
3. 支持多个成员的本地 Agent 协同完成跨角色、跨仓库任务。
4. 支持人工讨论、决策、审批、介入和接管。
5. 建立统一的团队 Agent 能力、项目知识和研发工作方法体系。
6. 将稳定的研发流程转化为可执行、可验证、可复用的 SOP。
7. 通过成本统计、质量评测和持续改进，让团队的 Agent 能力与研发流程不断进化。

最终目标不是把几个 Agent 工具和管理系统拼接起来，而是建设一个完整的团队人机协作工作系统。

---

## 2. 整体架构方向

采用中心化协作管理、分布式本地执行的架构。

### 2.1 控制平面：团队协作工作台

负责：

- Project、Member 管理
- Issue 与 Task 管理
- Human / Agent / Squad 负责人管理
- Squad 协作与任务组织
- 评论、共享会话和通知
- Run 与执行记录
- 决策、审批与人工介入
- SOP 与工作流程管理
- Agent 能力、项目知识和工作方法管理
- 成本、质量分析和持续改进

### 2.2 执行平面：成员本地 Runtime

负责：

- 调用本机 Agent 工具
- 加载团队 Harness、Skills、Rules 和知识
- 执行代码修改与命令
- 管理本地 Git Worktree
- 执行测试与验证
- 回传任务状态、执行 Trace 和交付制品

支持 Codex、Claude Code、CodeBuddy、Qoder、OpenCode 等不同 Agent 工具。

服务器统一保存工作状态和协作数据。本地 Runtime 负责真实执行。

成员离线时，Issue、Task、评论、历史 Run 和交付记录仍然可访问。依赖离线成员 Runtime 的智能工作，在执行资源恢复后继续。

---

## 3. 现有项目的参考定位

本项目以三个现有项目为重要研究基础，但不照搬它们的产品边界和底层组织方式。

### 3.1 Multica：协作管理与执行底座

重点借鉴：

- Issue 生命周期
- Human / Agent / Squad 负责人模型
- Squad Leader 动态组织协作
- Daemon / Runtime 本地执行
- Run 生命周期
- Comments / @提及
- Inbox / 通知
- 多成员协作与任务交接

关键设计认知：

Issue 可以由 Human、单个 Agent 或 Squad 负责。

Squad 是一个具备自主组织能力的智能体小队，不是每个 Issue 必然触发的固定角色集合。

只有 Issue 指定 Squad 作为负责人时，才启动 Squad Leader 的自动协调过程。

Leader 根据 Issue 的目标和实际情况动态分析、拆分任务、选择执行者、收集结果并持续推进。

不引入中心化 Coordinator Pool 作为前提。智能协调能力依赖实际承载 Leader 的本地 Runtime。

### 3.2 TeamAI：团队 Agent 能力与持续改进机制

重点借鉴：

**Team Execution**
- Agent / Role
- Harness
- Skills
- Rules
- Principles
- Hooks
- MCP
- Models
- Workflows

**Team Context**
- Project Wiki
- Learnings
- Codebase Knowledge Graph
- Recall
- Knowledge Contribution

**Team Improvement**
- Session Evaluation
- Scorers
- Benchmarks
- Dashboard
- Self-improvement

关键设计认知：

TeamAI 当前基于 Git 仓库组织团队资源，通过 CLI 向成员本地 Agent 工具分发。

我们的平台不受 Git 仓库作为底层管理架构的限制。

应该借鉴它的资源组织、作用域、版本管理、分发、知识检索、质量评价和自我改进机制，重新设计平台原生的能力管理体系。

Git 可以作为外部资源来源、版本协作和导入导出方式，但不是平台运行的必要前提。

### 3.3 LoopForge：SOP 执行与工程级 RSI

重点借鉴：

**SOP 执行**
- 可视化 SOP
- Agent / Script / Human Gate
- DAG 节点依赖
- 并行执行
- Sub-SOP
- 节点输入输出与 Artifact Contract
- 失败重试与定向返工
- 暂停、恢复与人工接管
- 执行 Trace 与质量门禁

**执行评测**
- Run Trace 结构化提取
- 目标达成度评估
- 产物契约评估
- 门禁防线评估
- 控制流、耗时、工具、Token、恢复、交付等多维评分
- 结构化 Findings 和改进建议

**工程级 RSI**
- 从真实执行中发现问题
- 分析执行失败和低效原因
- 生成 SOP 优化建议
- 生成 Agent 角色规范与门禁改进建议
- 经确认后应用改进

关键设计认知：

LoopForge 的 SOP 既可以覆盖完整研发交付流程，也可以只承担其中一个相对独立的环节。

它采用可组合的流程单元，支持通过 Sub-SOP 复用。

SOP 不是整个研发协作系统，而是工作过程中可被调用的标准化执行机制。

LoopForge 的价值不仅是 SOP 编排，还包括从执行 Trace 到评测、改进处方和流程/角色进化的工程级 RSI 机制。

---

## 4. 统一研发工作生命周期

需要围绕一项真实研发工作，设计完整的生命周期。

建议从以下七个阶段展开：

### 4.1 工作输入

- 创建需求、Bug、技术调查等 Issue
- 明确工作目标和预期结果
- 关联项目、仓库及必要背景

### 4.2 分析规划

- Agent 获取必要项目知识
- 理解目标、约束和验收标准
- 分析影响范围
- 动态拆分工作
- 判断需要哪些角色和执行者

### 4.3 协作组织

- 确定 Human / Agent / Squad 负责人
- Squad Leader 组织协作
- 分配成员和 Agent
- 确定任务依赖与执行方式

### 4.4 工作执行

- Agent、Script、Human 执行任务
- 本地 Runtime 提供执行环境
- 动态加载 Agent 能力和项目知识
- 记录执行 Trace 和中间成果

### 4.5 质量验证

- 自动化测试
- 代码 Review
- SOP 门禁
- Agent 质量评价
- 人工审批和验收
- 失败后的返工和重新验证

### 4.6 交付关闭

- 汇总执行结果
- 关联代码、报告、日志和交付制品
- 验证目标是否达成
- 形成可追溯的交付记录

### 4.7 经验与能力改进

- 提取可复用经验
- 更新项目知识
- 改进 Harness、Skills、Rules
- 优化 Agent Role、Playbook 和 SOP
- 通过 Benchmark 验证改进效果

这七个阶段代表工作系统需要具备的能力，不意味着每个 Issue 都必须按照固定的七步流程执行。

复杂任务由 Agent 自主规划；稳定的重复工作逐步固化为 Playbook 和 SOP。

---

## 5. 核心对象

初始核心业务模型：

| 对象 | 职责 |
|---|---|
| Project | 项目与资源组织 |
| Member | 团队真实成员 |
| Issue | 业务工作单元 |
| Agent | 智能体角色与能力定义 |
| Squad | 智能体协作小队 |
| Runtime | 本地 Agent 执行环境 |
| Task | 可分配的具体工作 |
| Run | 一次实际执行记录 |
| Conversation | 共享协作上下文 |
| Decision | 人工与 Agent 的决策记录 |
| Playbook | 某类工作的指导方法 |
| SOP | 可执行的标准化流程 |
| Artifact | 代码、报告、日志与交付制品 |
| Knowledge | 项目和团队知识 |
| Evaluation | 工作质量评价 |
| Improvement Proposal | 能力与流程改进提案 |
| Benchmark | 改进效果回归验证 |

这些是初始概念，不代表最终数据模型。专题设计需要进一步明确对象边界、关系和生命周期。

---

# 6. 五个核心设计专题

## 专题一：统一工作生命周期

目标：

设计 Issue、Task、Run、Squad 和 Human 共同参与的完整工作机制。

重点研究：

1. Issue、Task、Run 的职责边界和关联关系。
2. Human / Agent / Squad 如何参与整个工作生命周期。
3. Squad Leader 如何分析需求、拆解任务和动态组织协作。
4. Task 如何分配给不同成员、Agent 和 Runtime。
5. 评论、人工介入、审批、接管如何影响工作推进。
6. 多个 Issue 并行时如何组织和管理工作。
7. Work Context 如何统一组织。
8. 执行过程如何保留完整的决策和证据。

特别关注：

- Issue 是团队工作的中心。
- Task 是具体工作单元。
- Run 是实际执行记录。
- Squad 是动态协作主体。
- 共享协作上下文不能只依赖单个 Agent 的聊天历史。

## 专题二：SOP 与研发工作流融合

目标：

设计一套与 Issue、Task、Run 和 Squad 自然融合的研发流程执行机制。

重点研究：

1. LoopForge SOP 的完整源码设计及适用范围。
2. TeamAI Workflow Engine 的机制和职责。
3. Playbook、Workflow、SOP 的边界。
4. 哪些工作由 Agent 自主完成，哪些工作需要 SOP。
5. 完整交付流程和局部 SOP 如何组合。
6. SOP 如何组织和驱动 Task。
7. Agent / Script / Human Gate 如何执行。
8. 并行依赖、Sub-SOP、输入输出和 Artifact Contract。
9. 失败重试、定向返工、暂停、恢复和人工接管。
10. SOP 与 Issue 状态、Run、执行证据如何关联。
11. SOP 执行内的自愈和质量门禁机制。

核心原则：

SOP 不取代 Multica 的 Issue、Task 和协作管理。

Playbook 提供工作方法，SOP 固化稳定的执行流程，Agent 保留复杂问题的自主分析与规划能力。

需要重点研究 LoopForge 和 TeamAI Workflow 是否存在执行机制重叠，以及我们是否需要统一的流程定义和执行体系。

## 专题三：TeamAI 与工作台深度融合

目标：

将 TeamAI 的团队 Agent 能力管理机制转化为平台原生能力体系。

重点研究：

### Agent Harness
- Agent / Role
- Skills
- Rules
- Principles
- Hooks
- MCP
- Models
- 工具和执行配置
- 不同本地 Agent 工具的适配

### Project Context
- Project Wiki
- 项目事实
- 技术架构
- 业务知识
- 历史决策
- Learnings
- Codebase Knowledge Graph
- 知识来源、版本和有效性

### Work Intelligence
- Playbooks
- Workflows
- 任务分析方法
- 质量标准
- 验证策略

### Context Assembly
设计 Agent 工作上下文动态组装机制。

根据当前 Issue、Task、执行角色和 SOP 节点，按需提供：

- 当前工作目标和边界
- 项目背景和相关知识
- Agent Harness
- Skills / Rules
- Playbook
- SOP 节点要求
- 验收标准

不同角色需要不同的上下文，不能将整个团队知识库无差别注入每个 Agent。

### Knowledge Contribution
从真实工作中提取经验，形成知识更新建议。

区分事实证据、候选经验、正式知识和规范。

### 版本与分发
设计平台原生的资源版本、审核、发布、适用范围和本地分发机制。

不以 Git 仓库作为资源管理的前置条件。

## 专题四：成本治理与持续自改进

目标：

建立贯穿整个工作台的 Engineering Intelligence & Evolution Engine。

它不仅是统计报表中心，还应该能够发现系统性问题，并推动经过验证的能力和流程改进。

### A. Cost Intelligence

研究成本采集和归集：

- 模型 Token 和费用
- 输入、输出、缓存读写和推理 Token
- Agent / Tool 使用情况
- Runtime 和计算资源
- 重试、返工和无效调用
- 人工介入次数与时间

统计维度：

- Team
- Project
- Member
- Issue
- Task
- Run
- Agent
- Squad
- Model
- SOP

需要区分真实上报费用、估算费用、仅有 Token 和未知费用。

重点指标：

- 总成本
- 单 Issue 成本
- 单位有效交付成本
- 不同 Agent / Model 的成本差异
- 失败和返工成本
- 成本趋势和异常增长

### B. Quality Intelligence

借鉴 LoopForge Run Evaluation 和 TeamAI Scorers。

评价对象包括：

- 单次 Run
- Issue / Task
- Agent / Role
- Squad
- SOP
- Skill / Rule
- Workflow

评价方式包括：

- 客观验证门禁
- 结构化执行事实
- 大模型深度评测
- 人工 Review 与验收
- Benchmark 回归测试

需要研究如何将执行 Trace、目标达成度、产物契约、质量门禁和人工反馈结合起来。

### C. Continuous Improvement

建立三个改进层次：

**Knowledge Improvement**
- 项目知识更新
- 经验沉淀
- 知识有效性治理

**Capability Improvement**
- Harness
- Agent Role
- Skills
- Rules
- Principles
- Playbooks

**Process Improvement**
- SOP
- Workflow
- 节点依赖
- 验证门禁
- Agent / Human 分工
- Squad 协作策略

### D. Improvement Proposal

建立统一的改进提案机制。

提案包含：

- 问题和证据
- 关联 Issue / Task / Run
- 问题归因
- 改进目标
- 修改对象和修改内容
- 预期收益
- 回归验证方案
- 改进前后的质量、成本和效率对比
- 审核和发布状态

### E. Benchmark

借鉴 TeamAI 的 Benchmark 机制：

- 从真实失败案例提取回归任务
- 固定测试输入和成功标准
- 使用不同 Harness / Agent / Skill / SOP 版本进行对照
- 比较质量、成本和执行时间
- 检查改进是否造成其他任务退化
- 验证通过后发布改进

### F. 双重进化闭环

**单次执行内环：**

执行 → 门禁验证 → 失败反馈 → Agent 修复 → 重新验证 → 完成。

**跨次执行外环：**

执行 Trace → 质量评测 → 问题归因 → 改进提案 → Benchmark → 审核发布 → 后续真实工作验证。

核心原则：

Agent 可以主动发现问题并提出改进，但正式团队资产的变更需要经过验证和适当审核。

## 专题五：统一工作台产品设计

目标：

基于前四个专题的工作机制设计完整产品。

重点研究：

1. 项目、Issue 和任务工作台。
2. Human / Agent / Squad 负责人管理。
3. Squad 协作过程和任务树。
4. 多人共享会话和上下文。
5. 本地 Runtime 与 Agent 资源管理。
6. 人工介入、审批和接管。
7. SOP 设计与执行界面。
8. TeamAI 团队能力管理。
9. 项目知识管理。
10. 执行 Trace 和交付追溯。
11. 成本与质量分析。
12. 评测中心和持续改进中心。

产品原则：

- 围绕真实工作组织产品，而不是围绕底层技术组件组织页面。
- 减少团队成员的额外维护工作。
- 让 Agent 能力和知识自然参与研发工作。
- 让流程治理服务于工作，而不是增加流程仪式。
- 让执行证据、成本、质量和改进结果可以追溯。

---

# 7. 三个贯穿系统的基础机制

五个专题设计时，需要共同考虑以下基础机制。

### 7.1 Work Context

统一关联：

- Issue 目标
- Task 及依赖
- 项目和代码基准
- 历史讨论
- 已确认决策
- 相关知识
- SOP 执行进度
- 验收要求
- 执行结果和交付制品

通过引用、版本和关联关系组织上下文，不要求所有数据复制到 Issue。

### 7.2 Execution Contract

Agent、Script 和 Human 执行任务时，使用统一的输入输出契约。

输入：

- 工作目标
- 工作边界
- 必要上下文
- 执行要求
- 验收标准

输出：

- 实际完成情况
- 修改范围
- 执行记录
- 验证证据
- 交付制品

底层 Runtime 负责适配不同 Agent 工具。

### 7.3 Evidence & Feedback

统一关联：

- 执行 Trace
- Git Diff / Commit
- 自动化测试
- Review
- 人工审批
- 交付制品
- 失败和返工原因
- Scorer 评价
- Benchmark 结果

证据既用于工作追溯，也用于质量分析和能力改进。

---

# 8. 设计原则

1. **Issue First**：以 Issue 为团队工作的中心，而不是以 Agent 或 Task 为中心。
2. **Human / Agent Native**：Human、Agent、Squad 都是正式的工作参与者。
3. **Distributed Execution**：中心化管理，成员本地分布式执行。
4. **Autonomous Planning**：复杂、不确定的工作由 Agent 自主分析和规划。
5. **Progressive Standardization**：重复且稳定的工作逐步固化为 Playbook 和 SOP。
6. **Context-driven**：根据工作动态组装 Agent 上下文。
7. **Evidence-driven**：关键执行结果和改进必须有证据支撑。
8. **Quality over Activity**：评价真实交付质量，而不是简单统计 Agent 活动数量。
9. **Continuous Improvement**：知识、能力和流程都可以持续进化。
10. **Usability First**：团队愿意使用、实际能够维护，比功能数量更重要。

---

# 9. 设计工作方式与交付要求

按照五个专题分别开展研究和设计。

不要直接进入数据库、接口和技术实现。

每个专题需要：

1. 明确需要解决的实际问题。
2. 研究现有项目的相关源码和设计机制。
3. 识别现有方案的能力边界与不足。
4. 结合整个工作台重新设计，而不是简单复制。
5. 分析与其他专题的关系。
6. 通过真实研发场景验证设计。
7. 输出明确的设计结论、待解决问题和后续演进方向。

设计时使用一个贯穿案例：

「为现有系统增加订单批量导出功能」。

模拟产品人员创建 Issue、Squad 分析规划、前后端协作、本地 Agent 执行、人工介入、SOP 验证、最终交付，以及执行评测和能力改进。

确保五个专题最终能够组成一套完整的工作系统。

本阶段最终交付：

- 统一工作生命周期设计
- SOP 与 Workflow 统一机制设计
- 平台原生 TeamAI 能力体系设计
- 成本、质量评价和持续自改进设计
- 完整产品信息架构与交互设计
- 各专题之间的统一架构关系

注意：本资料是产品方向和设计研究输入，不是已经完成的最终技术架构。具体对象、机制、模块边界和实现方案需要在专题研究中进一步推导。

---

# 10. 核心参考资料

## Multica
- https://github.com/multica-ai/multica

## TeamAI
- https://github.com/Tencent/teamai-cli
- https://github.com/Tencent/teamai-cli/blob/main/docs/product-overview.md
- https://github.com/Tencent/teamai-cli/blob/main/docs/guide/sharing.md
- https://github.com/Tencent/teamai-cli/blob/main/docs/guide/knowledge.md
- https://github.com/Tencent/teamai-cli/blob/main/docs/guide/workflow.md
- https://github.com/Tencent/teamai-cli/blob/main/docs/guide/scorers.md
- https://github.com/Tencent/teamai-cli/blob/main/docs/guide/benchmarks.md
- https://github.com/Tencent/teamai-cli/blob/main/docs/guide/self-improvement.md

## LoopForge
- https://github.com/Tencent/LoopForge
- https://github.com/Tencent/LoopForge/blob/main/internal/domain/workflow.go
- https://github.com/Tencent/LoopForge/blob/main/internal/engine/workflow_graph.go
- https://github.com/Tencent/LoopForge/blob/main/internal/engine/node_execute.go
- https://github.com/Tencent/LoopForge/blob/main/internal/domain/analytics.go
- https://github.com/Tencent/LoopForge/blob/main/internal/httpapi/run_eval.go
- https://github.com/Tencent/LoopForge/blob/main/internal/domain/run_eval.go
- https://github.com/Tencent/LoopForge/blob/main/internal/runeval/facts.go
- https://github.com/Tencent/LoopForge/blob/main/internal/runeval/prompt.go
- https://github.com/Tencent/LoopForge/blob/main/internal/runeval/apply.go

研究要求：上述源码链接是第一轮研究入口，Codex 应继续检查当前仓库实际版本、完整调用链、测试用例和数据模型，不能只依据文档或本资料中的概括做最终判断。