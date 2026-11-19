# AgentPlatform · C1 / C2 Evaluation → Issue → Knowledge / Harness 闭环验证

> 状态：确定性跨域契约实验通过；生产 Evaluation Run 尚未接入  
> 分支：design/system-architecture-convergence  
> 实验入口：`prototypes/topic-04/order-evaluation-closure.mjs`  
> 回归：23 / 23 通过 · [GitHub Actions](https://github.com/ScWen7/Issues/actions/runs/44466281176)  
> 样本：Topic 3A C1 / C2 固定报告；Topic 3B 已有知识贡献与复审账本  
> 非目标：不创建真实 Multica Run、不调用模型裁判、不发布知识或 Harness、不改变历史 Issue / Candidate 决定。

## 1. 本轮要回答的问题

上一轮五域审查发现，A / B / C / D 已有多项真实案例，但 E 尚未完整证明如何把评价结果交回 Issue，并将跨工作问题分流给知识维护者或 Harness 维护者。

本实验沿用已有 C1 / C2，不另造业务样本，验证以下边界：

1. E 是否能引用 D 已有的 Run / Candidate / Artifact / Evidence，形成独立评价记录？
2. 评价缺项是否会变成 Inconclusive，而不是误判低分？
3. E 发现的问题如何回到 B，而不越权修改 Issue、Candidate 或原 Run？
4. 既有 A 知识贡献是否能被 E 准确关联，并尊重它当前已退役的状态？
5. 哪些情况下才应形成 C 的 Harness 改进候选？
6. 同一 Finding 同时涉及 A 与 C 时，如何形成两条独立治理路径？

## 2. 样本事实：C1 / C2

两个报告来自同一个 Issue、同一 D2 规则和同一核验器版本，分别对应不同候选与 Run。

| 事实 | C1 | C2 |
|---|---|---|
| Candidate / Run | C1 / verify-C1 | C2 / verify-C2 |
| 候选代码 Commit | `6880625de52ceb834e3e60b07cd8748c4ad79058` | `005e558ad99a6def3f4dbb2c7a1ec56e71553bf7` |
| D2 A2 权限范围 | 失败 | 通过 |
| D2 A3 工作簿正确性 | 通过 | 通过 |
| 东区导出结果 | 错误包含西区订单 B-201 | 仅 A-101、A-102 |
| 核验器 SHA-256 | `f7edf54a17140b44e6fa0d070e1eef4be39c50bfa99f509fa560445a8bfd8f9c` | 相同 |
| 报告 SHA-256 | `da022445c03fa787af994101f47cd8cfb777913f882a6b7aa32116a3493afcb1` | `e9c93051c5b844cf23aa89061eed967c5a2267e846e26b37ece7275f194bd514` |
| 原核验结论 | rework | pass |

来源：[C1 固定报告](topic-03a/fixtures/order-export-c1.json) · [C2 固定报告](topic-03a/fixtures/order-export-c2.json) · [实际运行与工作簿核验](topic-03a/order-export-workspace.md)。

这两份报告已证明“进程成功结束”与“候选符合标准”是不同事实：C1、C2 的核验进程都退出 0，但 C1 的 A2 失败，C2 的 A2 / A3 均通过。

## 3. E：独立评价如何形成

### 3.1 评价输入与身份

实验把报告摘要、Candidate、源 Run、核验器版本、角色检查和 Artifact 摘要固定为评价输入。E 的记录引用原 Run，但使用不同的评价 Run 身份：

- `verify-C1` → `evaluation:verify-C1`
- `verify-C2` → `evaluation:verify-C2`

这里的 `evaluation:...` 是本原型中的逻辑身份，用来验证对象分离；**本实验没有向 Multica 创建真实 Evaluation Run**。真实执行仍需由后续平台运行入口创建独立 Multica Task / Run，并保存 Scorer Release 与输入快照。

### 3.2 评价维度

本次确定性 Scorer 采用两个可核验维度：

| 维度 | 权重 | 判断依据 |
|---|---:|---|
| Authorization Scope / A2 | 0.7 | 东区、西区、跨区、只读四种角色是否满足各自权限边界 |
| Workbook Correctness / A3 | 0.3 | 工作簿结构、金额、时间等检查及只读角色未生成文件 |

权重仅是实验夹具，不是已发布团队 Rubric。更重要的是：**A2 是硬性权限要求，不能被 A3 的高分抵消。** 综合分数只用于测试评价记录，不能替代维度结论或业务验收。

| 评价结果 | C1 | C2 |
|---|---:|---:|
| A2 | 0 | 1 |
| A3 | 1 | 1 |
| 确定性加权分 | 0.3 | 1.0 |
| Finding | 高严重度权限范围缺陷 | 无 |
| E 事后评价门禁 | advisory-only | advisory-only |

### 3.3 评价与 Finding

C1 的 Finding 只陈述可直接观察的事实：

> 东区导出工作簿包含不属于东区白名单的订单 B-201。

它引用 C1 报告摘要、东区工作簿摘要和核验器版本。根因状态保持 `unknown`：证据能证明候选输出违反 A2，但不能单凭结果确定究竟是实现、上下文、授权配置还是其他环节导致。

C2 的 A2 / A3 都通过，因此不制造负向 Finding。不能为了让 E 看起来有工作而强行生成知识或 Harness 改进。

### 3.4 事后评价不是门禁

C1 / C2 原有的 D2 核验器已给出 rework / pass，这属于原 SOP / 核验链的结果。E 的独立事后评价默认 advisory-only。只有项目 / SOP 明确声明门禁，且源 Run、Scorer 版本和门禁声明匹配，才可产生门禁结果。

本实验未声明新的 E 门禁，因此 E 的评分不覆盖原核验结论，也不改变 Candidate 或 Issue 状态。

## 4. B：Issue 负责人如何消费 Finding

B 仍然是唯一业务决定权威。原型要求决策者角色为 `issue_accountable_member`，并且必须显式选择动作。

| 样本 | 原型中的显式 B 决定 | 不会发生什么 |
|---|---|---|
| C1 | `return_for_rework`，引用 E 的 Finding | E 不直接修改 Issue；原 Run 与 Evaluation 不被改写 |
| C2 | `forward_to_business_acceptance`，把候选交给 Issue 验收责任人 | E 不把 Candidate 自动标记 Accepted，不把 Issue 标记 Done |

这两个 B 决定是本次契约测试中显式输入的模拟决策，不冒充历史实验已经保存的人工 Decision。已有 Topic 3A 记录证明 C1 应返工、C2 核验通过并可由 SOP 消费；人工接受仍沿 Issue 原有决定入口。

关键规则：
- Evaluation Completed 不等于 Candidate Accepted；
- Evaluation Failed 不等于被评 Run Failed；
- E 的 Finding 不自动把 Issue 置为 Blocked / Done；
- B 的业务决定引用 Finding 和 Evidence，但不改写原始执行事实。

## 5. A：关联已有 Knowledge 贡献，不重复造资产

Topic 3B 已经使用 C1 / C2 的同一组报告形成过团队经验提案：

- Proposal：`b506b31bbe5da5e1ee898bee7edbe51996d10b441c61d4cc46cdaae72dfbdea5`
- 首次发布的团队文案：**“验证区域订单导出时，用普通区域账号和跨区账号分别导出。核对每份工作簿的订单集合，并单独验证付款时间列。”**
- 该提案的证据账本同时引用了 C1 / C2 的精确报告摘要。
- 当前贡献夹具的最终状态为 **retired**，原因链包含来源撤回与证据对失效。

来源：[项目知识与团队贡献夹具](topic-03b/fixtures/project-knowledge.json) · [贡献、复审、撤权与退役实证](topic-03b/knowledge-contribution.md)。

本次 E 评价可以按两份精确报告摘要关联这个既有贡献，但不能把“历史上曾发布”当成“当前仍可用”。原型核对后得到：
- 已存在同证据的 Knowledge Proposal；
- 当前状态为 retired；
- 后续动作是交 A 的知识维护者复核；
- 不自动创建新的 Knowledge Release，不恢复旧版本，不绕过来源授权与独立复审。

这证明 E 应优先引用已有 A 资产与治理历史，而不是每次评价结束都新建一条知识。

## 6. C：什么时候形成 Harness 改进

本次真实样本**没有证明 Harness 存在缺陷**：

- C1 的 A2 失败被同一核验器正确发现；
- C2 使用同一 D2 规则和同一核验器通过；
- 两份报告中的核验器 SHA-256 相同。

因此不能仅因为 C1 返工就创建 Harness Revision。当前直接处理是 B 在原 Issue 返工；跨工作可复用经验已由 A 的知识贡献机制处理，但当前已退役，需 A 复核。

原型另有一项明确标注为**合成路由测试**：当同一 Finding 的证据分别支持“团队知识缺失”和“Harness 验证方法缺陷”两个根因假设时，路由器会向 A、C 生成两个独立的待分诊路径。它们：
- 引用同一个 Finding，但各有独立维护者；
- 分别形成 Knowledge Revision 候选和 Harness Revision 候选；
- 不共享发布决定；
- 不自动创建 Release 或改变 Project Adoption。

这只是验证双路分流契约，不是 C1 / C2 的实证结论。

## 7. 本轮自动化回归

<badge color="success">23 / 23 通过</badge>

[GitHub Actions 实际执行记录](https://github.com/ScWen7/Issues/actions/runs/44466281176)

覆盖内容：
1. C1 / C2 报告摘要与输入绑定；
2. C1 生成有证据的 A2 Finding，C2 不产生虚构 Finding；
3. 评价缺证据时返回 Inconclusive；
4. 评价默认 advisory-only，门禁要求精确 Run 与 Scorer 版本；
5. B 只能由 Issue Accountable Member 作决定；
6. B 的决定不改写源 Run、Evaluation 或自动完成 Issue；
7. E 可关联 A 已有贡献，并尊重其 retired 状态；
8. 同一 Finding 的 A / C 分流保持独立；
9. 无证据 Finding 不得进入知识或 Harness 发布路径。

复跑：

```bash
node --test \
  prototypes/topic-04/evaluation.test.mjs \
  prototypes/topic-04/order-evaluation-closure.test.mjs
```

## 8. 本轮形成的架构结论

| 结论 | 状态 |
|---|---|
| E 的 Evaluation 必须引用原业务 Run，但使用独立评价执行身份 | 契约通过；真实 Multica Evaluation Run 未实测 |
| 评价缺项必须 Inconclusive，不能以低分代替证据不足 | 契约通过 |
| 事后评价默认 advisory-only，门禁必须显式声明并匹配版本 | 契约通过 |
| B 消费 Finding 并决定返工 / 交验收，E 不越权修改 Issue | 契约通过；本次 B 决定是模拟输入 |
| A 复用已有知识贡献身份与复审历史，不重复建资产 | 与 Topic 3B 真实治理账本关联通过 |
| 当前 C1 / C2 证据不足以支持 Harness 缺陷归因 | 基于同核验器正确检出 A2 的证据判断 |
| 同一 Finding 可分流 A / C，但两者分别提案、验证、发布 | 合成路由契约通过 |
| Evaluation → B → A / C 的生产持久化闭环 | 尚未验证 |

## 9. 下一步真实验证缺口

本轮已经证明产品责任边界可以表达和自动回归，但尚未证明真实产品集成。下一步只需补齐以下真实承载，而不是重新设计五域：

1. 用真实 Scorer Release 对终态业务 Run 创建独立 Multica Evaluation Run，保留原 Run 不变；
2. 将 Evaluation 输入快照、证据引用和 Finding 持久关联到原 Issue；
3. 由真实 Issue Accountable Member 消费 Finding，记录返工或提交验收决定；
4. 对 A 已有 retired 贡献执行真实维护者复核，不因 E 评价通过而自动恢复；
5. 只有出现独立证据证明 Harness 缺陷时，才由 C 维护者建立 Harness 候选并执行回归；
6. 后续真实生产工作验证改进效果，不能用本轮同一确定性 Scorer 自证。

**本轮结论：E 应是证据驱动的评价与分诊能力，不是另一个验收人、资产发布者或自动改进代理。它把结果交给 B，由 B 决定当前工作；跨工作知识与 Harness 改进分别回到 A、C 的既有治理生命周期。**

## 10. 与既有 VS-3 技术承载契约的对照

本轮不重新设计 Evaluation 的技术承载。真实执行要求沿用[VS-3 · Evaluation、独立执行与预算预留技术承载契约](../architecture/vs3-evaluation-technical-contract.md)。本原型与 VS-3 的关系如下：

| VS-3 要求 | 本轮覆盖 | 当前状态 |
|---|---|---|
| Evaluation 与源 Run 分离 | 原型使用不同 sourceRunId / evaluationRunId，回归验证源 Run 不被改写 | 契约模拟通过；尚未创建真实 Multica Evaluation Task / Run |
| 固定 Target Version / Evidence Snapshot | C1 / C2 报告 SHA、Candidate、Artifact 摘要和核验器 SHA 固定并校验 | 样本级证据绑定通过；完整 Evaluation Target Snapshot 尚未持久化 |
| Scorer / Rubric 版本 | 固定 order-export-review-v1，并检查门禁必须匹配源 Run 与 Scorer 版本 | 契约模拟通过；尚非 C 发布的正式 Scorer Release |
| Trigger / Policy / Work Agreement | 本轮未创建 Evaluation Policy 或触发身份 | 未覆盖 |
| 预算预留与结算 | 本轮无真实 Evaluation Task，也未占用 Multica 预算 | 未覆盖 |
| 独立 Multica 主 Task 与 Retry 谱系 | 原型只有逻辑 evaluation Run 标识 | 未覆盖，必须在 VS-3 真实纵向切片验证 |
| Governance Purpose 隔离 | 本轮未运行真实 Task / Session / Worker Wakeup | 未覆盖 |
| Evaluation / Finding 幂等持久化 | 原型函数和 Node 测试验证重复输入边界，未接持久存储 | 逻辑契约部分通过；真实写入与响应丢失恢复未覆盖 |
| Finding 回到原 Issue | 通过显式 B 决策函数验证责任人与不越权规则 | 契约模拟通过；未写入真实 Issue Decision |
| A / C 分流 | 关联既有 A 贡献账本；双路分流为合成路由测试 | A 历史引用通过；C 真实缺陷仍无证据，真实维护者分诊未覆盖 |

因此本轮 23 / 23 不是 VS-3 完成，也不替代 VS-3 故障注入。它只关闭了五域之间最重要的产品语义和决策边界。

### 10.1 下一项纵向实跑应复用现有 VS-3 顺序

真实集成时按 VS-3 已定义的顺序执行，不再增加第二套任务系统：
1. 选取终态 C1 或 C2 的真实 Multica Run / Candidate，固定 Target Version、报告和制品 Evidence、D2 核验器及 Scorer Release。
2. 通过 Evaluation Policy 触发，生成稳定 Evaluation ID；完成适用预算范围的原子预留。
3. 通过现有 Multica 创建独立 Governance Purpose Task，Task 来源指向 Evaluation ID，Evaluation 反向绑定唯一主 Task；合法 Retry 沿原生谱系查回。
4. 用真实成员 Runtime 执行一次 Scorer；观察 Claim、Start、宿主实际启动、终态和原生 Usage。不得用本轮逻辑 evaluationRunId 冒充真实 Run。
5. 消费 Task 终态，核对 Target / Policy / Scorer / Evidence Snapshot，幂等写入 Evaluation 与 Finding。
6. 将 Finding 通知回原 Issue，由真实 Accountable Member 作返工或交验收决定；不由 E 自动改 Issue 状态。
7. A / C 维护者分别处理其候选；对 A 的 retired 贡献先按当前来源许可复核，对 C 只有出现独立 Harness 缺陷证据才建立候选。
8. 注入重复触发、Task 创建响应丢失、结果回写响应丢失、权限撤回、预算不足和合法 Retry，验证无重复 Evaluation / 主 Task / Finding。

上述步骤与 [VS-3 第 10–12 节](../architecture/vs3-evaluation-technical-contract.md)的首个纵向范围、故障注入和完成标准一致。真实 Multica 数据库、成员凭据和 Runtime 需要在集成环境提供；在它们可用前，不宣称生产闭环完成。