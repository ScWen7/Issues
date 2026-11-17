# VS-3 · Evaluation、独立执行与预算预留技术承载契约

> 本文细化 D7、D11 与技术方案准备中的 VS-3。目标是让一次评价拥有独立身份、固定输入、可控预算、独立执行和可恢复结果消费，并接入 Issue / Candidate 主线。
> Multica 源码基准：71683141a764ed3b1620db4bc26a2d0a098f135c。
> 本文定义业务身份、关联、预算和恢复契约，不指定数据库表、API 路径、模型供应商或部署拓扑。

## 1. 设计结论

**Evaluation 是业务评价事实；Evaluation Task / Run 是为完成该评价而发生的独立执行。二者关联但不是同一个对象，也不是被评生产 Run 的子状态。Model-based 评价有一个主 Task；其有限重试沿 Multica 原生 retry 谱系关联，不创建新 Evaluation。Deterministic / Human Review 可以没有 Agent Task。**

- 被评对象保持原身份和原状态：Issue / Production Task / Run / Candidate / SOP Activation / Release。
- Evaluation 固定被评对象版本、输入证据快照、触发策略、Scorer / Rubric 和结论。
- 需要受管 Agent 执行时，创建独立 Multica Task / Run；该 Task 通过 Evaluation 来源身份关联评价，不改变生产 Run。
- 评价结果回到 Evaluation 和原业务目标；只有原目标的有权主体或预先声明的门禁消费它。
- Evaluation / Benchmark / Improvement 的 Task 用量单独识别，不混入生产执行质量口径；原生 Usage 仍归 Multica Task。

不建设评价专用队列、Run 状态机、Runtime 或成本账本。

## 2. Evaluation 与被评生产对象的身份关系

### 2.1 一次 Evaluation 固定一个评价目标快照

Evaluation 至少固定：
- Evaluation ID；
- Target Kind / Target ID；
- Target Version：Run ID、Candidate ID + Generation + Manifest Digest、SOP Activation / Attempt ID、Release ID 等适用的不可变版本；
- 所属 Issue / Project / Team（如目标属于这些范围）；
- Trigger Type：Mandatory Gate、Risk Trigger、Sampling、On-demand；
- Trigger Source / Reason；
- Team Policy、Project Policy、Work Agreement 版本；
- Scorer / Rubric 版本及其配置摘要；
- 输入 Evidence ID 集合、Artifact Locator / Digest、覆盖和缺项；
- 请求者 / 触发主体及其权限来源；
- 评价方法：Deterministic、Trace、Model-based 或 Human Review；
- 预算资格、预留、实际执行引用和最终结论。

Evaluation 不引用“当前最新 Candidate”作为目标。目标版本一经创建固定，后续 Candidate、标准或策略变化不会改写既有 Evaluation。

### 2.2 目标快照不是复制一份无边界数据

Evaluation 固定证据引用和内容摘要，不因评价而复制所有源文件或扩大读取权限：
- 原始 Evidence / Artifact 保持原权限和来源；
- Evaluation 执行时按目标权限重新核对可读取范围；
- 必要输入可以形成受控、最小化的评价快照，记录快照版本和摘要；
- 来源失权或不可取得时，Evaluation 进入 Insufficient Evidence 或 Cancelled，不尝试从其他成员私有 Runtime / 账号绕过权限；
- 敏感输入按来源策略处理，不默认写入模型提示日志或长期 Transcript。

输入快照固定的是“评价器被允许看到什么”，不意味着它有权读取目标 Issue 的所有内容。

### 2.3 Evaluation 不是生产 Run 的子状态

生产 Run 的 Completed / Failed / Cancelled 保持原样。Evaluation 的 Requested / Running / Completed / Failed 等状态独立维护。

生产 Run 成功但 Evaluation 失败：生产仍是成功，评价是 Failed。
生产 Run 失败但 Evaluation 成功：评价可以分析失败原因，不能把生产 Run 改为成功。
Evaluation Not Passed：是评价结论，不是评价执行 Failed，也不自动等于 Candidate Rejected；由预先声明的门禁或业务负责人决定其影响。

## 3. Evaluation 何时需要 Multica Task / Run

Evaluation 的执行方式由方法决定，不是所有评价都启动 Agent。

| 方法 | 是否需要 Multica Task / Run | 典型用途 | 结果如何进入 Evaluation |
|---|---|---|---|
| Deterministic | 通常不需要模型 Task；可由现有 CI / 检查入口产生证据 | 退出码、测试结果、manifest、必需字段、权限和结构契约 | 引用原始检查 Evidence；若检查本身受管执行则引用对应 Task |
| Trace | 只有需要受管分析或额外采集时才需要；读取已授权的原始 Trace 不必再跑 Agent | 工具调用顺序、重试、节点覆盖、交接和执行效率 | 引用 Trace Evidence；分析 Run 如有则独立关联 |
| Model-based | 需要真实 Agent 运行时，使用独立 Multica Task / Run | 需求覆盖、语义质量、根因归纳、方案完整性 | 评价 Task 完成后校验结构化结果并写入 Evaluation |
| Human Review | 不需要 Agent Task | 业务取舍、风险接受、例外批准、主观体验 | 有权成员提交独立 Review / Decision 事实 |

一个业务问题可以需要多个方法，但每种方法的证据和结论分别记录；不得把确定性检查通过、模型评价通过和人工决定压缩成一个不透明分数。

**首个 VS-3 切片优先采用 Deterministic / Trace 评价，再接入一次真实 Model-based Evaluation Run。** 不要求第一版建设复杂的多评委编排。

## 4. Model-based Evaluation Run 的 Task 关联

### 4.1 独立 Task，不复用生产 Task

需要模型执行时，沿 Multica 原生派发创建新的 Task：
- Task 使用实际获准执行评价的 Agent 和 Runtime；
- Task 有自己的 Task ID、Claim / Start / 终态、Session、Trace 和 Usage；
- Task 明确属于原 Issue（若评价目标属于 Issue），以便沿用 Issue 访问、运行权限和原生 Usage 查询；
- Task 的直接触发证据指向 Evaluation ID，使用自由文本 evidence kind 标记 evaluation，ref 指向 Evaluation ID；
- Evaluation 记录主 Task ID；Task 记录 Evaluation 来源引用，形成双向可核对关系；Multica 自动重试产生的子 Task 继承该来源身份，归入同一 Evaluation 执行尝试链；
- Task 必须带有明确的治理用途标识（Evaluation Purpose / Execution Lane），不能只靠 prompt 或 trigger summary 猜测；
- Target Production Task / Run 通过 Evaluation 记录关联，不将其伪装成 parent_task_id、retry_of_task_id 或 rerun_of_task_id；
- Evaluation Task 即使归属同一 Issue，也不能与普通生产 Task 共用 pending coalescing 槽位、Session 恢复池或普通 Worker Wakeup 消费路径。

Multica 的 parent_task_id、retry / rerun 字段具有既定执行谱系语义。评价不是生产任务的重试或委派，不得滥用这些字段表达“被评对象”。

### 4.2 为什么评价 Task 可以归属原 Issue

若评价目标是某个 Issue 的 Candidate / Run，评价 Task 可以使用同一个 issue_id，以沿用 Multica 现有权限和 Task / Usage 归集能力；但业务分类必须明确：
- Evaluation 是治理活动；
- 原生产 Task / Run 是生产执行；
- Evaluation Task 是评价执行。

Issue 下 Task Usage 的原生汇总仍会包含该评价 Task，这是底座按 Issue 聚合的事实；AgentPlatform 的生产成本视图必须按 Task 的业务来源 / 角色分开归集，不得把评价费用算作生产 Run 成本。团队总资源统计则应同时纳入两者。

### 4.3 Governance Purpose 必须贯穿 Multica 原生执行语义

源码复核发现，普通 Issue Task 的 pending 唯一约束按 Issue / Agent 竞争；Comment 路径还会将新输入 coalesce 到同一 Agent 的 pending Task。普通 Session 恢复会选择同 Agent / Issue 的最近终态 Session（目前显式排除 Triage）。Issue Wakeup 也可能按事件类型捕获同 Issue Task 的终态；Issue Usage 查询会聚合该 Issue 下所有 Task。

因此，仅设置 Task 来源证据为 evaluation 不足以实现隔离。Multica 适配必须在现有 Task / Run 中提供统一可查询的 Execution Purpose，并以 Governance 子用途区分 Evaluation、Benchmark、Improvement 和 Calibration；所有治理用途共同满足以下隔离要求：
- Governance Task 不被普通生产 Task 的 pending 唯一约束 / Comment coalescing 合并；同一 Evaluation ID 仍有唯一 Task 绑定，Benchmark Trial 和 Improvement 执行也使用各自来源身份查回；
- Governance Task 使用隔离上下文和新 Session，且被普通 Main Bot / Worker 的 Session 恢复查询排除；
- 普通 Issue Wakeup 默认不把 Governance Task 终态当作 Worker 结果；Evaluation / Trial 结果成功消费后，才通过对应业务通知唤醒负责人；
- Task 原生事件和 Usage 仍保留在 Multica；AgentPlatform 的生产成本视图按 Purpose / 来源身份排除治理 Task，团队治理总成本仍纳入；
- 普通生产 Task 的 coalescing、Session continuity、Wakeup 和 Usage 语义保持不变。

这是复用 Multica 控制面的必要适配，不是第二套执行队列。统一用途边界由[VS-5 整体技术一致性审查](vs5-overall-technical-consistency-review.md)定义。具体源码证据见[VS-3 Multica Runtime 隔离取证](../research/vs3-evaluation-multica-runtime-evidence.md)。

### 4.4 不用 Agent 身份伪装 Scorer 身份

评价执行记录必须分别固定：
- Scorer / Rubric 的发布者与版本；
- 实际执行评价的 Agent ID；
- Runtime / Backend / Model / Effort（可观察时）；
- 评价请求者和有权触发主体；
- 实际 Task / Run。

执行 Agent 只是运行评价程序的主体，不自动拥有修改 Rubric、批准结果或发布资产的权力。

## 5. Evaluation 的逻辑生命周期

Evaluation 状态与 Multica Task 状态分别维护：

| Evaluation 状态 | 含义 | 对应执行关系 |
|---|---|---|
| Requested | 已按策略获准，固定目标与输入，等待预算、权限复核或执行资源 | 尚可没有 Task |
| Running | 评价已开始处理；确定性 / 人工方法也可按自身记录推进 | Model-based 时必须关联唯一 Task / Run |
| Completed | 评价器按契约成功产出结论和 Findings（可以是 Not Passed） | 对应执行成功，或确定性 / 人工方法完成 |
| Insufficient Evidence | 目标输入、授权、覆盖或来源不足，不能形成可靠结论 | 可以没有 Task；若执行中发现缺项，Task 仍按真实终态记录 |
| Failed | 评价执行本身失败或输出契约无效，未形成有效结论 | 对应 Task / Run 失败或结果校验失败 |
| Cancelled | 请求被撤回、授权失效或有权主体取消 | 如 Task 已启动，另核对 Multica 取消请求和真实终态 |

评价结论与执行状态分开：
- Completed + Not Passed 是有效评价结果；
- Failed 是评价活动失败，不是质量不通过；
- Insufficient Evidence 是无法判断，不是低分；
- Cancelled 不代表已启动 Task 已停止。

Task Queued / Claimed / Running / Completed 等执行状态直接读取 Multica，不复制成第二套执行状态机。Evaluation 可显示主 Task 和其 retry 谱系的聚合进度，但不能自行声称 Task 已启动。

## 6. Evaluation 身份与幂等

### 6.1 触发身份

同一评价请求的稳定身份由以下内容构成：
- Target Kind / ID / Version；
- Trigger Type + Trigger Source Identity；
- Team / Project Policy 版本；
- Work Agreement 版本；
- Scorer / Rubric 版本；
- Evidence Snapshot Digest；
- Evaluation Method / 配置版本。

对 Sampling，还要包含稳定抽样选择结果 / 样本批次身份；对 On-demand，包含请求操作身份；对 Mandatory Gate，包含门禁定义与目标轮次。

### 6.2 重复触发

同一稳定身份重复到达：
- 返回原 Evaluation；
- 若预算已预留，不能再次预留；
- 若 Task 已创建，查回原 Task；
- 若结果已完成，返回原结论，不重跑；
- 若处于 Requested / Running，接续原状态，不另建评价。

不能用“相同 Issue + 相同 Scorer”作为唯一身份，因为同一 Issue 可以有多个 Candidate、多个标准版本和多个合法评价目的。

### 6.3 何时允许新 Evaluation

只有下列情况可以形成新身份：
- Target Candidate / Run / SOP Activation 发生实质版本变化；
- Evidence Snapshot 变化且请求者要求重新评价；
- Scorer / Rubric 新版本明确要求重评；
- Policy 版本变化并且策略明确要求新一轮评价；
- 有权成员明确发起复核，并提供原因与新请求身份。

旧 Evaluation 和旧 Task / Usage 不覆盖、不重置。单纯网络重试、Webhook 重放、按钮重复点击不创建新评价。

## 7. 预算预留与结算

### 7.1 预留的是可控制资源，不是假想 USD

Evaluation 预算由 D11 的四个范围共同约束：单次 Evaluation、Issue / Candidate、Project 周期、Team 周期。

启动前核对并预留：
- 评价 Task 数量；
- 最大执行时长 / 超时窗口；
- 并发槽位；
- 输入证据量 / 上下文上限（可测量时）；
- Provider / Model 原生单位额度（仅当执行链可设置并可信核验时）；
- 允许的人审数量（适用时）。

不同 Runtime 的 Credits、Tokens、请求数和 USD 不换算成统一单位。若某 Runtime 不支持在启动前设置或可靠约束 Credits 上限，就不预留虚构 Credits；用 Task 数、并发和时间限制控制，执行后原生 Usage 缺失仍为 Unknown。

### 7.2 预留必须全范围原子成功

一次 Evaluation 同时消耗单次、Issue、Project 和 Team 的可用额度。逻辑上必须做到：
1. 计算所有适用预算范围和本次所需资源；
2. 在同一个预算权威写入边界核对策略版本、周期、已用额度和在途预留；
3. 全部可用才一次性预留；
4. 任一范围不足则不部分占用，不创建 Task；
5. 记录预留与 Evaluation 身份，重复请求查回原预留。

若未来实际存储无法在同一事务内覆盖这些范围，必须提供等价的原子额度协调机制；不能先扣 Team 再扣 Project，失败时留下无法恢复的半笔预留。

### 7.3 预留与实际使用分开记账

预算预留是运行前的资源资格，不是实际成本。实际消耗来自 Evaluation Task 的 Multica Usage：
- Task 创建成功后计入实际评价 Task 数；
- Task 启动后，按已观测时长 / 并发事实核算；
- Task 终态后读取 Task Usage，按 Provider / Model / 原生单位结算；
- Usage 迟到或更正时更新该来源快照，不将累计快照重复相加；
- 未使用的预留释放；
- Task 已启动后失败或取消，已发生消耗仍计入；
- 无法确认是否启动时保持 Unknown / Reserved，不擅自释放并让预算被重复使用。

Multica task_usage 按 (task_id, provider, model) upsert；更新值覆盖旧快照而非累加。AgentPlatform 结算必须尊重这一语义。生产 Task 与 Evaluation Task 各自归属自己的 Usage；总账按 Task 去重后汇总。

### 7.4 预算等待与释放

- Requested 等待预算：不创建 Task、不消耗执行额度；周期变化后按策略重新核验。
- 预留后尚未创建 Task：失败 / 撤回时释放预留。
- Task 创建成功但响应丢失：先按 Evaluation ID 查回 Task；不能释放后再创建另一个。
- Task Queued 但尚未 Claim：取消是否可行按 Multica 原生 Task 取消语义；确认取消后释放尚未消耗的执行额度。
- Task Claimed / Running：请求取消不等于停止；保留预留直到原生终态或可靠处置结果。
- Task 终态：按已知 Usage 结算，释放未使用额度；Usage 缺失则金额 / Credits 保持 Unknown，但已知 Task 数与执行时间仍可核算。
- Mandatory Gate 预算不足：保持等待或转有权人工 / 等价检查，不静默放行。
- Sampling 预算不足：停止新增样本，不影响已完成生产工作。

## 8. 执行结果消费与 Finding 回写

### 8.1 评价 Task 完成不等于 Evaluation 完成

Task Completed 事件只触发结果消费。消费者必须：
1. 根据 Task 来源证据查回唯一 Evaluation；
2. 读取原生 Task / Run 终态和完整结果；
3. 核对 Evaluation 仍处于可消费状态；
4. 核对 Target Version、Policy、Scorer / Rubric 和 Evidence Snapshot 仍与启动时一致；
5. 校验输出结构、引用证据和允许的结论范围；
6. 以 Evaluation ID + Result Version 幂等写入结果与 Findings；
7. 释放 / 结算预算；
8. 通知原目标的有权接收者。

若结果回写响应丢失，重试只查回已保存结果，不重复创建 Findings 或触发后继动作。

### 8.2 结果必须带证据定位

每个 Finding 至少引用 Evaluation ID、Target Version、Requirement / Rubric Dimension、支持它的 Evidence / Trace / Artifact 定位、事实与模型推断的区分、影响范围、置信局限和建议动作。

模型给出但没有来源支持的内容只能标为 Hypothesis / Unverified，不能伪装成生产事实。

### 8.3 Finding 回到原业务主线

- Issue / Candidate 评价：Finding 作为原 Issue 的评价结果呈现，交给当前负责人 / 有权维护者。
- SOP / Node 评价：Finding 归原 Activation / Attempt，由当前 SOP 受托者消费；越出授权范围时交回 Issue。
- Asset / Release 评价：Finding 归该资产版本及其维护者。
- 只有跨工作价值经维护者分诊后，才创建 Improvement Proposal。
- Evaluation 不直接改写 Candidate、Acceptance Decision、SOP Definition、Skill、Release 或 Project Adoption。

若评价是事先声明的 Mandatory Gate，门禁消费者按 Work Agreement 处理 Completed / Not Passed / Insufficient Evidence / Failed；门禁失败处理规则在开始工作前已固定，不能事后由评价器临时决定。

## 9. 故障恢复与并发场景

| 故障 / 竞争 | 必须保留的事实 | 恢复规则 |
|---|---|---|
| 同一触发事件并发到达 | 同一 Evaluation Identity | 只产生一个 Evaluation 与一份预算预留 |
| 预算预留成功、Task 创建前进程退出 | Evaluation Requested + Reservation | 恢复者按 Evaluation ID 继续派发，不重复预留 |
| Task 创建成功、响应丢失 | Task 带 Evaluation 来源身份 | 查回同一个 Task，补写 Evaluation Task ID |
| 两个恢复者同时创建 Task | 同一 Evaluation ID | 原生派发边界按稳定来源身份幂等；若不能证明唯一结果则 Unknown 并对账，不盲目重建 |
| Task 排队期间预算策略变更 | 启动时固定 Policy Version | 依启动契约复核；策略撤回 / 安全停用可阻止新启动，但不能改写历史 |
| Task Claim 后 Runtime 断联 | 原 Task / Claim / Run | 使用 Multica 原生 Reclaim / Lost 恢复，不创建新 Evaluation |
| Evaluation Task 失败 | 生产 Run / Candidate 不变 | Evaluation Failed；仅瞬时基础设施故障且剩余预算允许时有限重试 |
| Task Completed，结果回写失败 | 原 Task 已终态 | 重试结果消费，不重跑评价 |
| Finding 写入成功、通知失败 | Finding 已存在 | 补投通知，不重复写 Finding |
| Target Candidate 已被替代 | Evaluation 仍引用旧 Candidate | 结果归旧候选；不得自动影响新候选或当前门禁 |
| Work Agreement / 授权撤销 | 原评价目标和权限版本 | 停止新的读取 / 执行；已产生结果保留并标明撤权时点 |
| Usage 多次上报或更正 | 同一 Task / Provider / Model 来源 | 以最新可信快照覆盖，不重复累加 |
| Usage 未上报 | Run 真实存在，原生计量缺失 | 保留 Task 数 / 时间；Token / Credits / USD 为 Unknown |

## 10. 首个 VS-3 纵向验证范围

首个切片不做完整评价平台，只证明以下真实链路：

1. 对一个已完成的生产 Run 或固定 Candidate，按已声明的 Evaluation Policy 触发一次评价；
2. 生成唯一 Evaluation ID，固定 Target Version、Policy、Scorer / Rubric 和输入 Evidence；
3. 通过预算资格检查，完成单次 / Issue / Project / Team 预算预留；
4. 若为 Model-based，创建一个独立 Multica Task，Task 来源指向 Evaluation ID，Evaluation 反向保存 Task ID；
5. 在成员真实 Runtime 中完成 Claim / Start / 终态；
6. 读取实际 Task Usage，缺失单位保持 Unknown；
7. 结果消费校验固定输入和输出契约，写入 Evaluation 与 Finding；
8. Finding 回到原 Issue / Candidate，不改变生产 Run 和 Acceptance Decision；
9. 重放同一触发、Task 完成事件和结果回写，不重复创建 Evaluation、Task、预算预留或 Finding。

首轮建议先用一个现有可用 Agent / Runtime 和一个固定 Scorer；不要求引入独立专用 Evaluator Agent 或新服务。

## 11. 必须执行的故障注入

- 同一 Evaluation Trigger 并发提交；
- 单次预算足够但 Project / Team 预算不足；
- 预算预留后进程退出；
- Task 创建后丢失响应；
- 两个恢复者并发查回 / 创建；
- Runtime 离线、Claim 过期和 Start 响应丢失；
- 评价 Task Failed 与生产 Task Succeeded 并存；
- 评价 Task Completed 后结果回写超时；
- Finding 已写入但通知失败；
- Candidate 换版后旧 Evaluation 迟到；
- Policy / Rubric 变更后拒绝把旧结论用于新版本；
- Credits / Token 部分上报、累计快照更正和完全缺失；
- 评价请求者或目标资料权限撤回；
- 预算耗尽时 Mandatory Gate 与 Sampling 的不同处理。

每个场景都记录 Evaluation ID、目标版本、Policy / Scorer 版本、Reservation、Multica Task / Run、原生 Usage、Finding ID 和最终消费结果。

## 12. VS-3 完成标准

1. Evaluation 与生产 Run 是独立业务事实，彼此引用但状态不互相覆盖。
2. 一份 Evaluation 固定唯一目标版本、策略版本、Scorer / Rubric 和输入快照。
3. Deterministic / Trace / Model-based / Human Review 按需选择；不是所有评价都强制创建 Agent Task。
4. Model-based Evaluation 使用独立 Multica Task / Run，主 Task 来源指向 Evaluation，原生 retry 子 Task 继承来源并保留真实 retry 谱系；不滥用 parent / rerun 字段。
5. Evaluation 与 Task 双向可核对，创建和查回幂等；Governance Purpose 隔离 pending coalescing、Session 恢复和普通 Worker Wakeup。
6. 单次、Issue、Project、Team 预算全范围原子预留；不能部分扣额。
7. 可观测的 Run 数、时长、并发与原生单位分别记账；未知 Credits / Token / USD 保持 Unknown。
8. Task Usage 的累计快照和更正按覆盖语义处理，不重复累加。
9. Evaluation Task 失败不改变生产 Run；结果回写失败只重试消费，不重跑生产或评价。
10. Finding 有证据定位并回到原目标；跨工作 Proposal 仍需维护者分诊。
11. 重复触发、响应丢失、迟到结果、权限撤销和预算耗尽均有明确恢复行为。
12. 全部受管评价执行复用 Multica Task / Run / Runtime，不建设第二套执行控制面。

## 13. 下一步

VS-3 契约收敛后，进入 VS-4：将 Improvement Proposal 的候选修订、Benchmark 实验定义与样本、Release 发布审核、Project Adoption 和后续生产实际使用证据连成完整技术链。

VS-3 仍未确定具体数据库表、API、预算锁实现、模型调用协议和 UI。它们应在 VS-0 / VS-1 的来源身份与恢复机制、VS-2 的权威写入边界，以及本契约的预算原子性要求下统一设计。
