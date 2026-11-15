# 工作流执行、交接与结果回报的源码及测试

研究日期为 2026-11-14。三套上游按提交分别追踪 Issue 写入、流程推进、执行领取和结果回报。各分册列出源码位置、环境、用例和运行结果。[产品设计](../architecture/02-sop-workflow.md) · [状态模型实验](topic-02/prototype-validation.md)

| 上游及固定提交 | 实际追踪的路径 | 运行结果 |
|---|---|---|
| [Multica · f337d4d](topic-02/multica.md) | 普通 Issue 写入 → 工作流交接 / Squad Leader → 子事项事件与收据 → Run 入队 → PostgreSQL 并发领取 → Daemon 开始及重投 | Go 1.26.9、PostgreSQL 17.5。37 个顶层用例通过，含 HTTP、WebSocket 和数据库竞争 |
| [TeamAI · 556b524](topic-02/teamai.md) | CLI → 解析器和引擎 → 两类 driver → 租约、回报与文件存储 → 跨机交接；结算后追到 Scorer、Benchmark 与改进提案 | Node 24.22.1、Vitest 4.1.12。639 个单元及集成用例、12 个构建后的 CLI 端到端用例通过 |
| [LoopForge · 97b3cdc](topic-02/loopforge.md) | Issue / 直接运行入口 → 图与节点 → 并行执行、Runner、SQL 租约 → 制品、门禁、返工、父子恢复 → 评测与选定建议写回 | Go 1.26.11。25 个 Go 顶层用例、13 个流程编辑器用例通过。另用两个小测试直接验证了条件边和迟到成功回报 |

TeamAI 跨机交接使用本机多个安装目录与 Git 仓库模拟。TeamAI 和 LoopForge 的模型测试使用上游测试替身。

## 各上游在相同场景中的行为

| 对照问题 | 固定提交的行为 |
|---|---|
| 两个“完成”能否互换 | Multica 的 stage 会统计关闭和取消，唤醒有权的负责人解释影响。LoopForge 普通就绪判定要求所有直接前序成功；Issue 上多个 SOP 的 DependsOn 在派发入口会生成交接提示。TeamAI 的显式依赖、跳过和失败处理又有自己的语义 |
| 谁在并行工作时占用资源 | Multica 领取时同时约束 Agent 与共享 Runtime 的容量。TeamAI 将写入串行化，对单个已签发尝试分别校验回报。LoopForge 的顶层运行配额还可保留给等待恢复的实例 |
| 重放是不是返工 | Multica 同次 Squad 交接重放去重，重新进入同名列可有新 Run。TeamAI 合法并行回报按签发版本核对。LoopForge 受控返工使后代重新待执行，成功回写的尝试检查比失败宽松 |
| 节点自修正与重新执行怎样区分 | LoopForge 可把节点后置检查反馈送回执行者，在显式轮次上限内修正；执行错误重试和上游返工另有处理路径 |
| 离线后能恢复哪一部分 | LoopForge 会重接既有子实例，子流程也依赖实际工作区；TeamAI 在慢加载后的最终安装处重新检查，保护此间已响应的领取和取消；Multica 重投校验领取代次 |
| 谁可以改变运行依据 | LoopForge 有图快照，重试/返工仍可刷新部分绑定。TeamAI 同时固定子定义与材料，缺少可用版本时存在读取当前 checkout 的路径 |
| 评分如何改进后续工作 | TeamAI 可将评分作为独立工作流，Benchmark 比较有样本与口径约束。LoopForge 能从终态 Run 提取事实，用户选中建议后可实改项目节点或角色 |
