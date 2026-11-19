# VS-4 · TeamAI Benchmark 与自改进机制源码取证

> 固定源码基准：Tencent/teamai-cli @ 556b5246f2c13ad28b8b79b5b513a78ed8ab9dae。
> 本文记录上游实现能证明的实验定义、Trial 执行、配对比较和自改进提案机制；不将 TeamAI 的 Git PR 流程误写为 AgentPlatform 的 Release / Project Adoption。

## 1. 结论

TeamAI 的 Benchmark 不只是“同一个 Prompt 跑两次比较分数”。它固定实验计划，按多个 Arm 对相同任务执行隔离 Trial，使用明确 Scorer 评价，并在报告阶段检查配对可比性和回归。

对 AgentPlatform 最有价值的机制：
1. 实验先生成 Definition / Plan，再运行 Trial；
2. 每个 Arm 使用相同任务输入和新鲜隔离副本；
3. Judge 的 Rubric、Tool、Model、Effort 和批量方式会影响结果可比性；
4. Task sourceHash 不同的配对被排除，不能混入结果；
5. Judge Calibration 与正式 Verdict 分开；
6. 失败样本进入回归集，自改进有明确候选阈值和 PR 提案流程。

它没有提供 AgentPlatform 所需的 Team / Project 权限、资产 Release、Project Adoption、在途工作迁移或生产实际使用证明；这些必须由平台自己的权威对象补齐。

## 2. Benchmark Workflow 的阶段边界

源码：[teamai-benchmark.yaml](https://github.com/Tencent/teamai-cli/blob/556b5246f2c13ad28b8b79b5b513a78ed8ab9dae/workflows/teamai-benchmark.yaml)

工作流顺序：
- plan：通过 suite、aliases、tasks、arms 生成实验定义和计划；
- trials：按 Plan 执行，要求严格 sandbox isolation；
- subjects / score：为 Trial 产生评价主体并调用 Scorer；
- calibration-subjects / calibrate：对确定性检查与模型 Judge 进行校准，校准标签不写入正式 Trial Verdict；
- finally.report：无论前序如何结束都汇总结果；
- regression：仅在报告明确返回 dropped regression 时让流程失败。

这说明实验计划、执行、评分、校准和最终报告是不同步骤。AgentPlatform 应将 Experiment Definition 与各 Trial Result 固定，而不是只保存最后一张平均分报表。

## 3. 配对比较的可比性规则

源码：[pairing.ts](https://github.com/Tencent/teamai-cli/blob/556b5246f2c13ad28b8b79b5b513a78ed8ab9dae/src/benchmark/pairing.ts)

TeamAI 对同一任务的两个 Trial 配对检查：
1. Task sourceHash 不同，排除并标记 task_changed；
2. 两侧都由 Judge 判定，但 Rubric、Tool、Model、Effort 或 batched 设置任一不同，排除并标记 judge_changed；
3. 其余情况进入比较集合。

排除结果按原因聚合并展示数量。没有 Judge 判定的错误、未运行或未评分结果也不会被当成成功；它们按未通过侧参与规则。

AgentPlatform 应采用更完整的条件集合：除任务输入与 Judge 外，固定 Work Agreement、资产依赖、Runtime / Backend、工具、权限、确定性检查、环境和计量覆盖。若某个变量本来就是候选改动的一部分，则将结论限定为组合效果。不可比配对必须单独列出，不得静默丢弃。

## 4. 自改进如何从失败形成回归样本和提案

源码：
- [teamai-self-improvement.yaml](https://github.com/Tencent/teamai-cli/blob/556b5246f2c13ad28b8b79b5b513a78ed8ab9dae/workflows/teamai-self-improvement.yaml)
- [self-improvement.ts](https://github.com/Tencent/teamai-cli/blob/556b5246f2c13ad28b8b79b5b513a78ed8ab9dae/src/self-improvement.ts)

实现要点：
- 先按 Scorer / Suite 汇总失败，判断失败是否有可用的起始 Commit；
- 已有回归任务覆盖的 Failure Subject 不重复生成；
- 没有可复现 Commit 或当前 Checkout 不包含该 Commit 的失败会被拒绝；
- 默认流程至少需要两个可用失败样本，或一个新失败加一个已存在的开放提案，才开始改进；
- 改进 Agent 只修改 Team 维护的资源，不修改业务应用代码；
- 每个被选失败生成一个回归任务，任务描述固定原始请求、起始 Commit、成功标准和来源 Subject；
- 同一 Scorer 使用稳定提案分支，后续运行更新现有 PR，而不是每次另开一份。

这为“重复失败先归并、可复现后提案、每个问题增加回归覆盖”提供了实现参照。但其阈值是 TeamAI 默认工作流选择，不应被 AgentPlatform 固定成所有团队通用规则；Proposal 是否跨工作有价值仍由平台资产维护者分诊。

## 5. AgentPlatform 复用边界

| TeamAI 已实现的机制 | 可借鉴 | AgentPlatform 仍需定义 |
|---|---|---|
| Experiment Plan / Definition | 固定实验定义后再执行 | Team / Project 权限、Proposal / Candidate Revision / Baseline 身份 |
| 多 Arm + Fresh Clone + Sandbox | 同样本隔离执行 | Multica Task / Run 的治理用途和 Trial 来源身份 |
| Scorer / Rubric Pin | 固定评价器版本 | 评价器发布权限、校准样本和审计 |
| Paired Comparison | 输入 Hash 与 Judge Facet 可比性 | Runtime、权限、环境、工具、Usage 覆盖等完整可比条件 |
| Regression Failure | 失败样本回流 | Sample 授权、版本、代表性和去重治理 |
| Improvement PR | 变更通过 PR 审核 | 平台 Release、Project Adoption、在途工作版本 Pin |
| Team Repo 当前分支 | 后续提案复用同一分支 | 多资产、多项目、多个维护者与版本兼容关系 |

## 6. 证据边界

上述源码证明 TeamAI 在该提交中的 Benchmark 工作流、配对可比性规则和自改进提案阈值。它不证明实验结果足以代表真实生产收益，也不提供 AgentPlatform 的项目采用和生产使用确认机制。AgentPlatform 的 VS-4 必须将离线 Benchmark 与后续生产 Observation 分开。
