# Team Agent Collaboration Platform

本项目维护面向研发团队的人机协作工作台产品架构设计，采用中心协作、本地分布式执行的方向。

## 当前交付

当前为专题三 A「执行平面与宿主适配」V0.2 探索基线。本版补齐本地交互接入、上下文投递与加载回执、结构化节点回报、任务凭据及宿主终态 / 恢复拒绝五条研究线，校准 Provider 清理确认与取消专项收敛的源码结论。入口：[专题三 A 探索基线](docs/architecture/03a-execution-plane.md)，[源码研究记录](docs/research/03a-source-evidence.md)。第一阶段 Runtime / Daemon 底层机制已完成源码追踪；后续按 V0.2 顺序研究宿主与本地交互入口、上下文与任务身份、Workspace / Script / 结构化回报，再形成完整设计。

专题二「SOP 与研发工作流融合」当前设计基线为 V0.3。[设计稿](docs/architecture/02-sop-workflow.md)明确 Delegation Grant 委托授权、Dispatch Control Binding 单一派发控制、SOP 结果到 Project Workflow 的出口校验，以及子 Issue 委托轮次与 child_done 的关系；保留节点自修正、Script 执行、代码工作副本接续和成本归集设计。配套 [17 项原型状态模型测试](docs/research/topic-02/prototype-validation.md)，本次修正回执去重判断的变量笔误后复跑为 17 PASS / 0 FAIL。[源码研究](docs/research/02-source-evidence.md)保留三个上游的固定版本、调用链与已有实跑记录。

专题一 V0.3 的关键设计如下。

1. **确立底座工作假设决策：** 明确以 Multica 作为平台工作平面主干（Issue/子 Issue 共模、status 目录、Project Workflow、Run、Runtime 共享授权与 child_done 唤醒）作为后续专题展开的设计前提，并明确其推翻条件与重审范围（详见[架构总览 1.1 节](docs/architecture/overview.md#11-底座工作假设决策)）。
2. **建立设计基线表：** 在架构总览中设立【用户已确认】/【当前工作假设】/【待定】三栏基线（详见[架构总览 1.2 节](docs/architecture/overview.md#12-设计基线表)），统一界定决策效力，消除冗余限定词。
3. **明确与设计输入 V1 的对应与偏离：** 明确具体分工由子 Issue 或同 Issue 委派承担，不建独立 Task 层，待用户确认偏离（详见[架构总览 1.3 节](docs/architecture/overview.md#13-与设计输入-v1-的对应与偏离)）。
4. **深化专题一核心规则：** 制定平台强制规则最小清单，人工验收覆盖所有完成入口及成功完成类别；区分稳定人工总责人与流转的当前负责人，将核验主体、方法、证据类型和结果分别记录。保留子 Squad 一层限制与事后关联路径，并通过贯穿案例推演。
5. **明确专题二与专题三演进路径：** 明确专题二首要问题为分工组织双轨矛盾（Leader 子 Issue 分工 vs SOP 节点调度；线性 stage vs DAG 依赖）；将专题三拆解为 3A（执行平面先行线）与 3B（能力治理顺延线）。

专题一保留六项待验证事项，包括轻量工作单元 / Task 边界、总责人适用范围、验收决定与候选及标准版本绑定、Squad 嵌套深度、Leader 离线后的协调接续，以及多 Issue 的项目级优先级、结果依赖与 Runtime 容量。它们作为后续专题的验证输入，不改变当前工作主线。

专题一收口了人工验收覆盖、核验分类、Default Workflow 守卫适用范围和离线访问表述四项问题。项目目标继续保持中心协作、本地分布式执行；Runtime 离线期间，在线成员仍可访问中心协作数据。

| 文档 | 何时阅读 |
|---|---|
| [产品架构设计输入 V1](Team%20Agent%20Collaboration%20Platform.md) | 了解用户给定的方向、五个专题与研究要求（只读输入） |
| [统一架构总览](docs/architecture/overview.md) | 查看底座工作假设、设计基线表、跨专题职责与双轨矛盾 |
| [专题一：统一工作生命周期](docs/architecture/01-unified-work-lifecycle.md) | 审阅平台强制规则、总责人、父子分工、结果核验、以及订单导出完整推演 |
| [统一术语](CONTEXT.md) | 核对总责人、当前负责人、平台强制规则、结果核验方式等统一概念 |
| [专题二：SOP 与研发工作流融合](docs/architecture/02-sop-workflow.md) | 审阅分工、图依赖、人工门禁、返工与接管规则以及实现前的验证条件 |
| [专题二：三库源码与测试](docs/research/02-source-evidence.md) | 查看 Multica、TeamAI、LoopForge 的实际执行路径、设计原因和本轮运行记录 |
| [专题二：状态模型验证](docs/research/topic-02/prototype-validation.md) | 查看模型场景、运行命令、本次修复后的结果及真实集成验证任务 |
| [专题三 A：执行平面与宿主适配](docs/architecture/03a-execution-plane.md) | 查看执行分层、五条研究线、停止与恢复观察以及订单导出核对场景 |
| [专题三 A：源码研究记录](docs/research/03a-source-evidence.md) | 查看固定版本的注册、授权、加载回执、任务凭据及宿主结果证据 |
| [专题一：源码研究依据](docs/research/01-source-evidence.md) | 查看固定提交、代码事实与提示词约定对照、代表测试及设计推论 |

后续专题完成后同步更新架构总览、相关术语和贯穿案例；不在各专题另建一套工作状态、上下文或执行证据。

> [!NOTE]
> `docs/review/topic-01/recipe.json` 是此前为窗口和手机展示生成的配方文件，本轮评审修订未同步更新该展示副本，当前内容已过期；正式设计维护源以上表中的 Markdown 文档为准，展示配方将在后续里程碑中统一重建。

## 研究与核验

专题二保留上游定向测试记录和状态模型复跑结果。专题 3A 本轮以固定版本源码、代表测试断言阅读、工作场景及跨文档复核为依据。案例采用模拟决定与证据，宿主能力、真实多进程和跨机执行进入后续原型验证。

参考仓库副本和阶段笔记存放于已忽略的 `.tmp/`；正式文档引用固定的上游源码链接，不依赖临时目录长期存在。
