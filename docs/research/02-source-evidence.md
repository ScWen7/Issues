# 专题二 · 三套工作流的源码与验证

> **架构治理说明（2026-11-15）：** 本文记录 Multica、TeamAI、LoopForge 的固定版本源码事实与历史设计推论。当前架构已明确以 Multica 为基座；文中曾提出的 Grant、Dispatch Control Binding、独立 SOP 控制事务等属于当时的候选设计，不是当前生产实现要求。应以 [现行专题二设计](../architecture/02-sop-workflow.md) 和[架构治理基线](../architecture/governance-baseline.md)为准。上游源码证据与测试结果不因设计治理而失效。

研究日期为 2026-11-14。起点是本项目远端 `master@00afb0c` 和原始设计输入的十一项问题。重新从三个上游的默认分支获取代码，按具体业务动作跟踪实现，分别与存储条件、失败分支和测试断言核对。[专题二设计](../architecture/02-sop-workflow.md)

专题二 V0.3 的设计审查在 V0.1 上游源码与测试记录基础上完成；本轮四项修正属于平台设计收敛，没有新增上游源码版本或重跑上游测试。原型状态模型的设计级测试另见 [专题二原型验证记录](topic-02/prototype-validation.md)，配套测试代码位于 `prototypes/topic-02/state-model.test.mjs`。上游运行结果仍以表中固定提交和分册记录为准。

| 上游及本轮固定提交 | 实际追踪的路径 | 运行结果 |
|---|---|---|
| [Multica · f337d4d](topic-02/multica.md) | 普通 Issue 写入 → 工作流交接 / Squad Leader → 子事项事件与收据 → Run 入队 → PostgreSQL 并发领取 → Daemon 开始及重投 | Go 1.26.9、PostgreSQL 17.5。37 个顶层用例通过，含 HTTP、WebSocket 和数据库竞争 |
| [TeamAI · 556b524](topic-02/teamai.md) | CLI → 解析器和引擎 → 两类 driver → 租约、回报与文件存储 → 跨机交接；结算后追到 Scorer、Benchmark 与改进提案 | Node 24.22.1、Vitest 4.1.12。639 个单元及集成用例、12 个构建后的 CLI 端到端用例通过 |
| [LoopForge · 97b3cdc](topic-02/loopforge.md) | Issue / 直接运行入口 → 图与节点 → 并行执行、Runner、SQL 租约 → 制品、门禁、返工、父子恢复 → 评测与选定建议写回 | Go 1.26.11。25 个 Go 顶层用例、13 个流程编辑器用例通过。另用两个小测试直接验证了条件边和迟到成功回报 |

相比专题一，Multica 和 TeamAI 更换了研究提交，LoopForge 沿用同一提交重新追踪代码、执行测试。每份分册列出固定行号、具体断言、设计动机及本项目取舍。原作者在代码或迁移中说明的理由标出原处；其他动机属于依据实现作出的推断。TeamAI 跨机交接使用本机多个安装目录与 Git 仓库模拟，TeamAI 和 LoopForge 的模型测试使用项目自带替身。本平台跨机联调的验收条件见专题二[验证计划与已有证据](../architecture/02-sop-workflow.md#12-验证计划与已有证据)。

## 哪些事实改变了本项目的决定

| 对照问题 | 底层行为及原因 | 对本项目的影响 |
|---|---|---|
| 两个“完成”能否互换 | Multica 的 stage 会统计关闭和取消，唤醒有权的负责人解释影响。LoopForge 普通就绪判定要求所有直接前序成功；Issue 上多个 SOP 的 DependsOn 在派发入口会生成交接提示。TeamAI 的显式依赖、跳过和失败处理又有自己的语义 | stage 保留为工作信号；SOP 只按声明的有效结果和制品放行。导入带条件或清理动作的模板时逐项说明映射 |
| 谁在并行工作时占用资源 | Multica 领取时同时约束 Agent 与共享 Runtime 的容量。TeamAI 将写入串行化，对单个已签发尝试分别校验回报。LoopForge 的顶层运行配额还可保留给等待恢复的实例 | 项目优先级、节点已就绪、Runtime 已领取和实际开工分别记录。人等待审批时释放执行槽 |
| 重放是不是返工 | Multica 同次 Squad 交接重放去重，重新进入同名列可有新 Run。TeamAI 合法并行回报按签发版本核对。LoopForge 受控返工使后代重新待执行，成功回写的尝试检查比失败宽松 | 按范围、步骤轮次及尝试区分“同一命令重送”和“合法新工作”；保护迟到成功及失败两种回报 |
| 节点自修正与重新执行怎样区分 | LoopForge 可把节点后置检查反馈送回执行者，在显式轮次上限内修正；执行错误重试和上游返工另有处理路径 | 平台同一节点尝试可关联实施、检查和修正的多个 Run；已结束尝试后的执行重试与跨节点返工使用新尝试，分别计数并按原始 Run 归集消耗 |
| 离线后能恢复哪一部分 | LoopForge 会重接既有子实例，子流程也依赖实际工作区；TeamAI 在慢加载后的最终安装处重新检查，保护此间已响应的领取和取消；Multica 重投校验领取代次 | 恢复先找既有工作、交付物和回执，材料装好再查当前进展。外部动作另做对账 |
| 谁可以改变运行依据 | LoopForge 有图快照，重试/返工仍可刷新部分绑定。TeamAI 同时固定子定义与材料，缺少可用版本时存在读取当前 checkout 的路径 | 平台实例固定主图、子图及选用版本，明确区分期望与实际加载。模板升级产生有接续关系的新实例 |
| 评分如何改进后续工作 | TeamAI 可将评分作为独立工作流，Benchmark 比较有样本与口径约束。LoopForge 能从终态 Run 提取事实，用户选中建议后可实改项目节点或角色 | 用同一份事实分别服务阻塞门禁、事后评价和改进提案。正式变更走回归和发布，原业务验收保留原候选与决定 |

## 原始输入的十一项问题

| 设计输入 | 设计稿落点 |
|---|---|
| 1–2 · LoopForge 完整执行机制、TeamAI Workflow Engine 的职责 | [融合职责](../architecture/02-sop-workflow.md#1-职责分工)、[LoopForge 分册](topic-02/loopforge.md)、[TeamAI 分册](topic-02/teamai.md) |
| 3–4 · Playbook / Workflow / SOP，何时自主完成 | [自主协作、Playbook 与 SOP 的选用](../architecture/02-sop-workflow.md#2-从自主工作到完整-sop) |
| 5–6 · 完整和局部流程组合、节点如何带动具体分工 | [三种工作关系](../architecture/02-sop-workflow.md#52-三种工作关系)、[订单的两条路径](../architecture/02-sop-workflow.md#10-订单批量导出的两条路径) |
| 7–8 · Agent、Script、Human Gate，并行依赖、Sub-SOP、制品契约 | [调用流程](../architecture/02-sop-workflow.md#3-一次-sop-如何运行)、[制品与结果消费](../architecture/02-sop-workflow.md#6-实际候选制品与报告消费)、[Script 承载](../architecture/02-sop-workflow.md#7-script-的执行主体)、[门禁](../architecture/02-sop-workflow.md#8-节点自修正重试返工与人工门禁) |
| 9 · 重试、定向返工、暂停、恢复与接管 | [授权与接管](../architecture/02-sop-workflow.md#53-授权撤销和接管)、[重试与返工](../architecture/02-sop-workflow.md#8-节点自修正重试返工与人工门禁)、[出口与恢复](../architecture/02-sop-workflow.md#9-版本与-project-workflow-出口) |
| 10–11 · Issue / Run 与证据、运行内自愈和质量门禁 | [节点、工作激活与 Run](../architecture/02-sop-workflow.md#4-节点工作激活与-run)、[实际交付核验](../architecture/02-sop-workflow.md#6-实际候选制品与报告消费)、[节点自修正与门禁](../architecture/02-sop-workflow.md#8-节点自修正重试返工与人工门禁)。跨次改进见[专题四](../architecture/04-cost-quality-improvement.md) |

每项结论可回到分册中的上游实现和测试。跨仓库部分经过反例复核，重点校对了两个入口同时首次派工、子实例已启动但父记录写回中断、同名步骤二次进入、旧轮成功晚到、慢接管覆盖期间取消，以及验收时换候选。它们也是后续平台验证的输入。
