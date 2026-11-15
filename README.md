# Team Agent Collaboration Platform

本项目建设面向研发团队的人机协作产品，**以 Multica 为协作与执行基座，融合 TeamAI 团队能力治理与 LoopForge SOP / 工程级 RSI 能力**。本仓库维护产品架构、源码研究、原型验证和真实宿主实验；不把专题设计误解为必须自建所有底层能力。

## 当前架构基线

**V1.1 · Multica 基座融合架构 · 交叉审查修订**

- **Multica**：Issue / Sub-Issue、Squad、Project Workflow、Run、Daemon、Runtime、Provider Backend、Session、Process、Trace、上下文准备 / 投递回执及 Task Usage 等工作与执行底座。
- **TeamAI**：Role / Skill / Rule / Playbook、知识检索、作用域与版本、上下文选择和投递、Skill Driver、AgentObservation、Scorers。
- **LoopForge**：可组合 SOP / DAG、Agent / Script / Human Gate、执行 Trace 评价、结构化 Findings、改进处方、Benchmark 和 RSI 自改进闭环。

专题一至四已有设计与分项研究证据，真实 Multica 融合验收仍按各专题追踪。专题五首轮已将十二类用户工作映射到现有入口，并完成订单、轻量工作和资源等待场景的交互设计。可下载[离线交互原型](prototypes/topic-05/workbench.html)走查 C1 失败、C2 补证及具名验收。

先复用 Multica 已有能力，再对真实缺口做最小扩展。不得建设第二套 Issue、Run、Runtime、派发控制、权限或成本账本。

本轮保留 Multica 的所有权边界，并补回受托范围的派发前置、本轮激活、结果消费、不可变验收资产和撤权后的历史处置。Script 托管、本地 Credits 上报及调用级证据按固定源码列为扩展项。改进流程统一为候选、Benchmark、审核发布和后续观察；订单案例与六问审查表随各专题维护。

## 架构入口

| 文档 | 用途 |
|---|---|
| [架构治理基线](docs/architecture/governance-baseline.md) | 最高层架构所有权、复用原则和禁止重复建设的约束 |
| [统一架构总览](docs/architecture/overview.md) | V1.1 产品定位、决策效力、共享契约、专题职责与订单贯穿案例 |
| [专题一：统一工作生命周期](docs/architecture/01-unified-work-lifecycle.md) | Issue First、Human / Agent / Squad 责任、工作约定和验收 |
| [专题二：SOP 与研发工作流融合](docs/architecture/02-sop-workflow.md) | LoopForge SOP 如何附着于 Issue，并通过 Multica Run 执行 |
| [专题三 A：Multica 执行底座审计](docs/architecture/03a-execution-plane.md) | Multica Daemon / Runtime / Backend / Session / Process 的覆盖与最小扩展 |
| [专题三 A：宿主能力证据矩阵](docs/architecture/execution-capabilities.md) | 不同宿主和入口的能力、证据与缺项 |
| [专题三 B：TeamAI 能力与知识治理融合](docs/architecture/03b-capability-governance.md) | 资产作用域、版本、检索、投递、Skill Driver 与 AgentObservation |
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

## 当前专题四真实用量状态

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
