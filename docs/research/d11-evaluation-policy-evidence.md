# D11 · 评价触发与资源预算的上游证据与平台决策

> 本文将固定版本的 LoopForge、TeamAI 和 Multica 研究映射到 D11。上游机制与 AgentPlatform 的产品决策分开陈述；没有源码或实验依据的自动化能力不作推断。

## 1. 结论

上游系统证明了“评价应有独立身份、固定输入和明确触发资格”，但没有一个项目完整提供 AgentPlatform 所需的跨团队风险分层、抽样治理和多原生单位预算闭环。

- **LoopForge**：已完成 Run 才能发起 Run Evaluation；评价事实提取、Scorer 版本和建议应用有明确入口。建议应用受限，不能把模型评价等同于自动发布。它提供终态评价与受控建议机制，不代表已有通用风险抽样调度器或团队预算管理器。
- **TeamAI**：符合条件的已结算 pass 可触发独立评分 Run；评分引用原 Run / Step / Pass 和 Scorer 版本。Benchmark 固定实验定义并核对比较条件；自改进以可复现失败为入口，需达到阈值后才生成候选改动。它证明了 pass 级评价与实验比较机制，不等于为所有 AgentPlatform 工作设定统一采样比例。
- **Multica**：提供原生 Task / Run、Runtime、Usage 和执行恢复链。评价与 Benchmark 应复用该链，不再建立评价专用执行队列。当前不同 Runtime 的用量覆盖不一致，预算必须允许原生单位缺失，不能统一换算成虚构 USD。

## 2. LoopForge：终态资格、独立评价与受限应用

固定源码：LoopForge 97b3cdc2f29a88e8767a8dc6c03bfb8865622653。

- Run Evaluation 的入口检查被评 Run 是否已完成，随后提取 NodeRun、返工、工具重复、错误、耗时和 Artifact 等事实。
- 评价由独立请求与评价过程产生，保留 Scorer / 评价输入，不改写生产 Run 的终态。
- Findings 需定位节点和证据；Recommendations 的可应用范围受限制，用户选择后才写回支持的局部参数或 Agent 指令。
- 评价 API 可由用户主动调用；不能据此宣称 LoopForge 已实现跨项目的风险分层随机抽样、预算预留或防递归策略。

源码入口：[Run Evaluation API](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/httpapi/run_eval.go) · [事实与评价提示](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/runeval/prompt.go) · [受限建议应用](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/runeval/apply.go)。

## 3. TeamAI：已结算 Pass 触发、独立 Scorer 和 Benchmark

固定源码：TeamAI 556b5246f2c13ad28b8b79b5b513a78ed8ab9dae。

- Scorer Hook 对符合条件的已结算 pass 发起独立评分 Run，固定被评 Run / Step / Pass 与 Scorer 版本。
- 评分启动失败不会将原生产 Run 改为失败；评价消耗属于独立 Run。
- Benchmark 在执行前固定样本和实验定义，配对比较排除任务摘要变化；模型裁判比较时还核对 Rubric、工具、模型、effort 和评分方式。
- 自改进优先从可复现且未被回归题覆盖的失败中筛选输入，达到条件后才进入候选改动和 PR。

这提供了“何时可评”和“如何比较”的实现参照，但不提供适合所有团队的采样比例或统一成本阈值。AgentPlatform 必须按团队 / 项目工作类型制定自己的策略。

源码入口：[Scorer Engine Hooks](https://github.com/Tencent/teamai-cli/blob/556b5246f2c13ad28b8b79b5b513a78ed8ab9dae/src/scorers/engine-hooks.ts) · [Scorer Plan](https://github.com/Tencent/teamai-cli/blob/556b5246f2c13ad28b8b79b5b513a78ed8ab9dae/src/scorers/score-plan.ts) · [Benchmark Pairing](https://github.com/Tencent/teamai-cli/blob/556b5246f2c13ad28b8b79b5b513a78ed8ab9dae/src/benchmark/pairing.ts) · [Self Improvement](https://github.com/Tencent/teamai-cli/blob/556b5246f2c13ad28b8b79b5b513a78ed8ab9dae/src/self-improvement.ts)。

## 4. Multica 与异构 Runtime：预算必须尊重原生事实

Multica 固定版本 fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc 提供 Task / Run / Runtime 和 Usage 归属。AgentPlatform 已有专题四证据进一步确认：
- CodeBuddy 2.181.0 受管 stream-json 可取得 Stage Credits 和 Turn snapshot；重复 snapshot 不能重复计费。
- Qoder 1.1.88 的本机 SDK 复测只取得 Session 累计快照，单次请求 Credits 仍 unknown。
- 不同宿主 Credits、Token、请求数和 USD 估算必须分开。
- Runtime 没有上报的用量保持 unknown；不使用企业 API、账户额度或账单接口补数。

来源：[专题四成本与评价证据](04-source-evidence.md#2-已有源码证据) · [本地 Runtime 复测](topic-04/runtime-validation-1.1.88-2.181.0.md)。

## 5. D11 的平台决策及其依据

| D11 决策 | 上游证据 / 风险依据 |
|---|---|
| 必需门禁必须事先声明，不可由事后评分追溯变成门禁 | LoopForge 评价入口与生产 Run 分离；业务验收由 Issue / Work Agreement 决定 |
| 高风险强制检查全覆盖，普通工作使用分层抽样 | 上游没有通用比例；这是平台根据强制要求不可抽样、普通评分成本需控制作出的治理决策 |
| 确定性检查优先，模型评价只处理语义判断 | 专题四区分 Deterministic / Trace / Model-based / Human Review |
| 仅对稳定输入评价；Run 终态或 Candidate manifest 固定 | LoopForge 的已完成 Run 资格；TeamAI 的 settled pass 与固定 Scorer 输入 |
| Evaluation 和 Benchmark 复用 Multica Run | 两个上游都将评价 / 评分作为独立执行；平台不需要再建 Runtime 控制面 |
| 预算按 Run 数、时长和各宿主原生单位分别限制 | 专题四证明 Qoder / CodeBuddy 的单位和覆盖不同，不能统一折算 |
| 预算耗尽时 Mandatory Gate 等待或转人工；Sampling 停止新增 | 避免静默跳过强制要求，同时允许非门禁观察在预算边界内降级 |
| 治理 Run 默认不进入生产抽样池；重试、重评和触发幂等 | 防止评价自身递归、重复事件造成成本放大；属于平台治理要求，不声称上游已完整实现 |
| Release、Project Adoption 和实际使用分开 | TeamAI 的版本发布、pull / 实际投递和宿主使用事实不同 |

## 6. 证据边界

上游源码证明了特定版本中的评价入口、评分执行和 Benchmark 机制；专题四原型验证了独立 Evaluation Run、证据不足、可比性拒绝和原生单位分离。它们不证明生产团队中的最优抽样比例、真实评价收益或跨团队统一预算阈值。

因此 D11 不预设全球固定百分比或统一 USD 配额。默认策略先使用强制确定性门禁、有限分层抽样、异常触发和有界重试；比例与预算由团队 / 项目在真实运行中校准。
