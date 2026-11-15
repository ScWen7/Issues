# Team Agent Collaboration Platform

本项目设计一套研发团队共用的 Agent 工作台。成员在中心管理多个 Issue，使用各自的本地 Agent 完成跨角色、跨仓库的工作。团队资料和项目现状为规划、实施、核验和交接提供依据。稳定的方法可以成为 SOP，一次交付中得到验证的经验可供另一名成员在后续工作中采用。

## 当前设计重点

从[团队研发协作工作机制](docs/architecture/overview.md#3-工作主线)开始。用订单导出说明负责人怎样组织工作、不同成员如何取得依据、何时调用 SOP、结果如何回到 Issue，再用下一项相似需求研究经验复用。先以轻量修改走通原 Issue，再查订单任务确实缺哪段资料或哪项能力。团队与项目在平台维护可复用配置，资料可沿用原有来源，成员无需维护团队 Git 仓。当前优先核验补充依据对角色判断和人员交接的实际影响。[团队与项目上下文](docs/architecture/overview.md#团队与项目上下文) · [本阶段交付与评审](docs/architecture/overview.md#本阶段交付与评审)

团队知识与代码理解分别开展产品设计。成员可在没有 Issue 时查阅、维护团队资料，或从项目架构读到某个版本的实现。Issue 和本地 Agent 按需引用其中的依据。[团队 Wiki 与项目资料](docs/architecture/team-project-wiki.md) · [项目代码 Wiki](docs/architecture/code-wiki.md)

## 当前架构基线

**V1.1 · Multica 基座融合架构 · 交叉审查修订**

- **Multica**：Issue / Sub-Issue、Squad、Project Workflow、Run、Daemon、Runtime、Provider Backend、Session、Process、Trace、上下文准备 / 投递回执及 Task Usage 等工作与执行底座。
- **TeamAI 机制参考**。平台借鉴能力作用域、角色检索、版本、经验贡献和评价机制，在原生 Issue、Agent / Skill 和 Run 上使用。
- **LoopForge**：可组合 SOP / DAG、Agent / Script / Human Gate、执行 Trace 评价、结构化 Findings、改进处方、Benchmark 和 RSI 自改进闭环。

专题一至四已有设计与分项证据，真实 Multica 融合验收按各专题追踪。专题五已把十二类工作映射到现有入口，其[离线交互原型](prototypes/topic-05/workbench.html)用于核对订单验收、轻量工作和资源等待的具体判断。脚本托管、调用级证据、本地 Credits 上报等工程缺口见[治理盘点](docs/architecture/governance-baseline.md#固定版本的底座盘点)。

## 架构入口

| 文档 | 用途 |
|---|---|
| [架构治理基线](docs/architecture/governance-baseline.md) | 最高层架构所有权、复用原则和禁止重复建设的约束 |
| [统一架构总览](docs/architecture/overview.md) | 团队研发协作工作机制、团队与项目上下文、当前评审重点及五个专题的关系 |
| [专题一：统一工作生命周期](docs/architecture/01-unified-work-lifecycle.md) | Issue First、Human / Agent / Squad 责任、工作约定和验收 |
| [专题二：SOP 与研发工作流融合](docs/architecture/02-sop-workflow.md) | LoopForge SOP 如何附着于 Issue，并通过 Multica Run 执行 |
| [专题三 A：Multica 执行底座审计](docs/architecture/03a-execution-plane.md) | Multica Daemon / Runtime / Backend / Session / Process 的覆盖与最小扩展 |
| [专题三 A：宿主能力证据矩阵](docs/architecture/execution-capabilities.md) | 不同宿主和入口的能力、证据与缺项 |
| [专题三 B：TeamAI 能力与知识治理融合](docs/architecture/03b-capability-governance.md) | 资产作用域、版本、检索、投递、Skill Driver 与 AgentObservation |
| [团队 Wiki 与项目资料](docs/architecture/team-project-wiki.md) | 从原文找到有效业务口径，维护项目说明、团队知识及其适用范围 |
| [项目代码 Wiki](docs/architecture/code-wiki.md) | 按基准阅读项目架构、模块、关键流程和跨仓调用，回到代码核对 |
| [专题四：成本、质量与工程级 RSI](docs/architecture/04-cost-quality-improvement.md) | Multica Usage 扩展、TeamAI Scorers、LoopForge Evaluator / Benchmark / RSI |
| [专题五：统一工作台](docs/architecture/05-unified-workbench.md) | 项目、Issue、待我决定和十二类用户工作的入口；订单、轻量工作及异常走查 |
| [统一术语](CONTEXT.md) | 统一 Issue、Run、Session、SOP、资产、评价和证据概念 |
| [本轮交叉审查修订记录](docs/review/governance-v1.1.md) | 查看审查发现、对应修订与本轮文档核验结果 |

## 研究与验证证据

专题一至四的源码研究、原始回执、订单案例和原型测试全部保留。它们用于证明上游实际能力、目标宿主行为和设计缺口，不自动构成新增平行系统的实现要求。

- [专题一源码研究](docs/research/01-source-evidence.md)
- [专题二三库源码与测试](docs/research/02-source-evidence.md)
- [专题三 A 执行底座研究](docs/research/03a-source-evidence.md)
- [专题三 B 能力治理研究](docs/research/03b-source-evidence.md)
- [专题四真实 Runtime 用量研究](docs/research/04-source-evidence.md)
- [Qoder / CodeBuddy / Copilot 真实回执与验证](docs/research/topic-04/runtime-validation-1.1.88-2.181.0.md)
- [专题五原生操作路径与源码](docs/research/05-source-evidence.md) · [工作台场景走查](docs/research/topic-05/workbench-walkthrough.md) · [真实 CodeBuddy 回执与原生展示函数回放](docs/research/topic-05/codebuddy-display-replay.md)
- [专题二状态模型原型验证](docs/research/topic-02/prototype-validation.md)

### 专题四宿主用量证据

- Qoder CLI 1.1.88 / SDK 1.0.59：PARTIAL。Query / Daemon 关闭与进程清理边界已实测；Assistant 请求事件、原生 request_id 和请求级 Credits 仍 unknown。Session total_credits=0 不作为单次消耗。
- CodeBuddy CLI 2.181.0：PASS（受管 CLI 入口）。单 Stage 0.69 Credits 已取得；真实 Stage 修订覆盖仍待进一步验证。
- GitHub Copilot CLI 1.0.107：PARTIAL。取得 Session 累计 nano-AIU checkpoint，逐请求 nano-AIU 仍 unknown。

这些证据用于扩展 Multica Task Usage，不另建成本账本。未知值保持 unknown。

## 设计与实现审查要求

各专题及改变对象、权威归属或控制机制的实现方案，按[治理基线六问表](docs/architecture/governance-baseline.md#7-设计与实现的强制审查表)回答以下问题。

1. Multica 已有什么源码、对象、接口、事件或测试可以复用？
2. 哪个实际场景仍有缺口，依据是什么？
3. 选择哪种扩展方式？若修改核心，说明现有配置及扩展点为何不足。
4. 谁拥有新增事实，哪些信息仅为引用或派生视图？
5. 是否形成第二权威？说明如何避免重复维护状态、身份、权限或计量。
6. 如何验证适用的正常、失败、重放、撤权、恢复与迟到场景？分别列出已执行的证据和待做的融合验收。

若形成第二套工作状态、Run、Runtime、派发、权限或成本账本，设计不得进入实现。
