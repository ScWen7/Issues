# VS-4 · Benchmark、Release、Project Adoption 与生产效果回收技术承载契约

> 本文细化 D7 持续改进内循环中 Improvement Proposal 之后的验证、发布、采用和效果观察。
> 目标：证明候选改进相对明确基线确有改善；将获准候选发布为不可变资产版本；由项目有权成员决定是否采用；继续核对新版本是否真正投递、被使用并改善生产结果。
> TeamAI 源码参考：Tencent/teamai-cli @ 556b5246f2c13ad28b8b79b5b513a78ed8ab9dae。
> 本文定义身份、比较、权威决定和恢复契约，不指定数据库表、API 路径、Git 服务、制品存储或部署拓扑。

## 1. 设计结论

**Benchmark 证明候选相对基线的实验结果；Release 固定获准发布的资产版本；Project Adoption 决定项目在什么范围采用该版本；Production Usage / Outcome 证明后续工作是否真正使用并产生效果。四者不能合并成一个“发布成功”状态。**

这条链有四个独立的权威事实：

1. **Improvement Candidate Revision**：Proposal 中不可变的一份候选改动，固定变更对象、基线、内容摘要、依赖和适用范围。它不是 D6 交付 Candidate。
2. **Benchmark Experiment / Result**：固定实验定义、样本、对照臂、评价器、环境和每次 Trial 结果。
3. **Release**：资产维护者审核通过后发布的不可变资产版本。
4. **Project Adoption**：项目有权成员对具体 Release / 配置版本作出的采用决定，附生效范围、时间和在途工作策略。

随后每个生产 Work / Run 分别记录：选择了什么版本、实际解析到什么版本、是否成功投递 / 注入、宿主是否能证明收到或加载，以及实际结果。

不建设 Benchmark 专用执行队列或发布部署控制面；受管实验仍沿 Multica Task / Run / Runtime，资产发布与项目采用属于各自业务权威域。

## 2. Improvement Candidate Revision：固定可验证的改动

### 2.1 候选修订身份

每个 Proposal 可有多个不可变 Candidate Revision。Revision 至少固定：
- Proposal ID + Revision ID；
- 被修改资产类型与资产 ID；
- 当前基线 Release / 版本及内容摘要；
- 候选内容定位与 Digest；
- 依赖资产及其固定版本；
- 变更清单、变更原因和来源 Finding / Evidence；
- 适用 Team / Project / Work Type 范围；
- 不适用范围、预期收益和风险假设；
- 创建者、创建时间和源操作身份。

候选修订创建后不原地修改。任何内容、依赖、适用范围或目标变化都产生新 Revision。Benchmark 结果必须指向准确的 Revision 和基线，不可被新提交沿用。

### 2.2 变更隔离

候选实验不得覆盖生产默认资产：
- Team 资产候选在隔离分支 / 快照 / 实验命名空间中准备；
- Project 配置候选限定项目实验范围；
- SOP 候选固定 Definition 与所有子流程版本；
- Skill / Role / Rule / Harness 候选固定全部依赖；
- Runtime / Adapter 候选固定宿主、Backend、协议和能力版本；
- Scorer / Rubric 候选固定评价定义及校准样本。

实验环境只能读取被授权的样本和来源；不能为了复现失败而复制其他成员私有 Session、凭证或连接器数据。

### 2.3 一个 Proposal 可以有多个候选

同一 Proposal 的候选可以分别尝试不同修复路径，但每个 Revision 独立验证。若候选 A 的 Benchmark 结果通过，不代表候选 B 或后续修改自动通过。

Proposal 的状态是治理视图，不替代 Revision、Benchmark、Release 或 Project Adoption 的具体状态。审核时明确完成范围：资产变更在要求的 Release 发布后可完成；项目配置变更在相应 Project Adoption 生效后完成；混合提案逐项满足批准范围后完成。统一进度按[Proposal 生命周期](lifecycle-state-event-model.md#92-improvement-proposal)记录，不强制项目配置经过资产发布，也不从提案完成推断项目已采用资产或生产效果已改善。

## 3. Benchmark Experiment：固定实验定义和可比边界

### 3.1 实验定义固定内容

Benchmark Experiment 至少固定：
- Benchmark ID；
- Proposal ID、Candidate Revision ID 和 Baseline Release / Revision ID；
- 任务样本集 ID + 不可变版本 / Digest；
- 每个样本的输入、上下文和起始代码 / 文件 / 数据版本；
- 任务成功标准、必需确定性检查和禁止条件；
- Scorer / Rubric / Judge 版本、参数、权重与聚合方式；
- 实验臂（Baseline / Candidate 及必要的控制臂）；
- Runtime、Backend、Model、Effort、工具、权限和执行环境；
- 重复次数、并发策略、超时、重试上限和随机种子（适用时）；
- 质量硬门槛、允许退化范围、成本 / 效率目标；
- 计量单位和各臂的 Usage 覆盖要求；
- 实验创建者、批准者、创建时间和预算身份。

定义一经启动即固定。样本、Scorer、环境、候选或基线变化，必须形成新的 Experiment Revision / Experiment ID；不能将旧结果拼接成同一轮实验。

### 3.2 样本集必须有来源和代表性

每个 Benchmark Sample 至少固定：
- Sample ID、来源 Issue / Run / Finding；
- 输入与必要上下文的快照 / Digest；
- 目标工作类型、难度 / 风险分层；
- 期望结果、确定性检查和判定标准；
- 样本纳入原因、已知偏差和敏感数据授权；
- 去重 / 覆盖关系及最近核验时间。

失败回归样本与代表性正常样本都要保留。只挑选候选已知擅长的样本，或只使用提案自身失败样本，不足以证明广泛改善。样本不足时结论为 Inconclusive，不用低样本均值宣称成功。

样本更新形成新版本。新样本集上的结果不能覆盖旧样本集上的历史结果。

### 3.3 对照臂与执行隔离

每个实验臂对同一组样本执行相同任务输入。原则上使用新鲜、相互隔离的工作副本，防止某一臂留下的文件、Session、缓存或工具状态影响另一臂。

实验臂可以有不同的目标资产版本；除此之外的条件应尽量固定。若候选本身改变 Runtime / Model / Tool，需将其列为明确实验变量，并把结论限定为“整套组合的效果”，不能声称是某一个 Skill 的独立收益。

Baseline 和 Candidate 的样本配对关系固定。每个 Trial 绑定：
- Benchmark ID / Experiment Revision；
- Sample ID；
- Arm / Asset Revision；
- 独立 Multica Task / Run；
- 实际使用的资产版本与环境回执；
- 结果、Evidence、Usage 和异常。

一个 Trial 的失败、未运行、取消或结果缺失不能从报告中静默删除，应按预先声明的规则计入未通过、缺失或不可比较。

### 3.4 比较前先判断是否可比

比较必须先执行可比性判定，再计算改善幅度。

至少检查：
- Sample ID 和输入 / 上下文 Digest 相同；
- Baseline / Candidate 的实验定义一致；
- Scorer / Rubric / Judge 版本相同；
- Judge Tool、Model、Effort、批量 / 单独评分方式相同（若影响判定）；
- Runtime / Backend / Model / 工具链相同，或差异已被明确声明为实验变量；
- 确定性检查版本和环境符合要求；
- 两臂的运行、失败、超时和缺失结果均被纳入；
- Usage 覆盖范围足以支持相应成本结论。

TeamAI 的比较实现提供了重要参照：任务 sourceHash 不同的配对被排除；两侧都使用模型裁判时，Rubric、Tool、Model、Effort 或批量方式变化也会排除该配对。AgentPlatform 采用同一原则：**不可比的配对必须显示排除数量和原因，不能当成零差异，也不能混进改善统计。**

环境不同不一定使所有质量比较都无效，但必须声明可比范围；成本比较尤其需要同一计量单位和可证明覆盖。缺失 Usage 不代表零成本。

### 3.5 多维门槛，不允许单一总分掩盖失败

Benchmark 结果按预先声明的门槛输出：
- 任务完成率 / 目标达成；
- 必需确定性检查通过率；
- 失败样本与严重 Finding；
- 返工、重试、人工介入和恢复表现；
- 时延、吞吐、等待和并发；
- Provider / Model 原生 Token、Credits、请求数、费用及覆盖率；
- 权限、隐私、安全和越权事件；
- 评价器一致性、校准与证据充分性。

硬门槛先判定：安全 / 权限 / 必需验收失败不能由其他维度的高分抵消。成本或耗时改善不能抵消质量退化；质量改善不能以放宽 Rubric 或缩小检查范围取得。

实验结论至少分为：
- **Passed**：样本和覆盖足够，所有硬门槛满足，预设改善目标达到；
- **Failed**：候选违反硬门槛或发生超出阈值的退化；
- **Inconclusive**：样本、可比配对、证据或 Usage 覆盖不足；
- **Execution Failed**：实验执行未能按定义完成，不能把它解释成候选质量失败。

上述是 Benchmark Result 的结论，Experiment 的执行状态另行记录。执行状态 Completed 可对应 Result = Passed、Failed 或 Inconclusive；执行状态 Failed 对应 Result = Execution Failed。质量判定 Failed 不触发实验故障恢复或自动重跑，具体生命周期见[统一状态模型](lifecycle-state-event-model.md#93-benchmark-experiment-与-trial)。

## 4. Benchmark 执行与结果恢复

### 4.1 沿 Multica 原生执行

每个 Trial 使用独立 Multica Task / Run，并标记统一 Execution Purpose = Governance、子用途 = Benchmark。Task 来源指向 Experiment + Trial 身份；保留 Baseline / Candidate、Sample、Arm 等归属。

- Benchmark 不创建新的 Runtime / Daemon / Task 队列；
- Baseline 与 Candidate Trial 不共享可变工作目录或 Session；
- Benchmark Task 遵循与 Evaluation 相同的治理用途隔离：不进入普通生产 coalescing、Main Bot Session 恢复或 Worker Wakeup；
- 所有 Trial 的真实 Usage 归原生 Task；治理成本与生产成本分开；
- 同一 Trial 的重复派发按稳定 Trial Intent 查回同一个 Task；
- 自动 retry 沿原生 retry 谱系，结果归原 Trial，不重复计为一个新样本。

### 4.2 实验结果消费

Trial Task 终态后，结果消费者：
1. 按 Task 来源查回唯一 Experiment / Trial；
2. 读取原生 Task / Run 终态、输出、Artifact 和 Usage；
3. 核对实验定义、样本、Arm 和目标 Revision 未发生漂移；
4. 校验输出结构、必需检查和证据引用；
5. 幂等写入 Trial Result；
6. 只有所有预定 Trial 已终结或按实验规则明确处理缺失项后，才生成 Benchmark Result；
7. 计算配对可比性、排除原因、硬门槛和聚合结果；
8. 通知 Proposal 负责人 / 维护者。

Task 完成不等于 Trial Result 已消费；所有通知失败只重发通知，不重跑 Trial。结果回写响应丢失时按 Trial ID 查回。

### 4.3 中止与恢复

- 实验中止是 Benchmark 的治理决定，不等于每个 Task 已停止；
- 对已启动 Trial 发出 Multica 原生取消请求，并逐一核对真实终态；
- 无法确认已停止的 Trial 保持 Unknown / In-flight，不释放其实际执行资源预留；
- 恢复时读取原 Experiment / Trial 状态，已完成 Trial 不重跑，未创建 Task 的 Trial 可继续；
- 目标 Candidate / Baseline 被撤回时，实验按既定策略中止或完成隔离中的当前 Trial，但不能将结果用于已替代版本；
- 结果消费失败重试消费，不重复执行已经成功的 Trial。

## 5. Release：不可变资产发布

### 5.1 发布身份

Release 至少固定：
- Release ID；
- 资产 ID / 类型 / 命名空间；
- Candidate Revision ID + 内容 Digest；
- 父 / 基线 Release；
- 全部依赖资产及其 Release / Digest；
- 适用范围、兼容宿主 / 版本和不适用范围；
- 支持它的 Benchmark Experiment / Result；
- 发布说明、限制、迁移说明和回滚目标；
- 资产维护者、审核人、审核权限证明；
- 发布操作身份与时间。

Release 一经发布不可原地修改。修复、补丁或依赖变化必须产生新 Release。发布记录不是“某个 Git 分支当前指向什么”，而是可解析、可验证的不可变资产快照。

### 5.2 Release Gate

发布前核对：
- 候选 Revision 与 Benchmark 目标完全一致；
- Benchmark 为 Passed，或有明确授权的例外审核（不可豁免硬门槛除外）；
- 样本、可比配对、执行覆盖和 Usage 覆盖足以支持发布说明；
- 依赖、权限、来源授权、兼容范围和风险说明完整；
- 审核人具备当前资产发布权限；
- 回滚目标仍可取得且兼容；
- 没有已生效的候选撤回、审核撤权或安全阻断。

审核请求可以提前存在，但权限必须在发布生效时复核。Benchmark 通过不自动发布；执行 Benchmark 的 Agent 不因执行身份而拥有发布权。

### 5.3 不同资产类型的发布边界

- Team Skill / SOP / Role / Rule / Harness：由对应资产维护者发布新 Release；
- Project Workflow / 分工 / 业务配置：属于 Project 配置决定，不冒充团队资产 Release；
- Runtime / Adapter：由执行集成维护者发布适配版本，固定支持的宿主 / 协议版本；
- Scorer / Rubric：由评价资产维护者发布，后续 Evaluation 固定新版本；
- Knowledge：由知识维护者发布来源 / 内容修订，并按其来源治理规则声明适用范围。

一个 Proposal 同时涉及多个资产时，分别发布各自 Release；不能用一个 Release ID 模糊覆盖不同维护者和权限边界。

## 6. Project Adoption：项目独立决定采用

### 6.1 Adoption 不是 Release 的状态

Project Adoption 至少固定：
- Adoption ID；
- Project ID；
- Asset ID / 类型；
- 被采用的 Release ID / Digest，或 Project Workflow 配置修订；
- Adoption Scope：项目默认、指定工作类型、指定 Agent / Runtime 或明确 Issue 范围；
- 采用方式：Default / Opt-in / Pinned / Pilot；
- 生效时间与停止条件；
- 在途工作策略：保持旧版本、显式迁移或停止；
- 项目有权成员、权限证明、理由和时间；
- 被替代的 Adoption 决定（如有）。

Release 可存在但没有任何 Project Adoption。一个 Release 可被多个项目采用；不同项目可以采用不同 Release。

### 6.2 Adoption 写入与并发

同一 Project + Asset + Scope 的当前采用指针具有单一权威写入边界。

命令必须携带预期 Adoption Generation / 当前 Release：
- 只有具备 Project 权限的成员可以提交；
- 目标 Release 必须仍可取得、未被撤回 / 安全禁用，且兼容当前 Project 范围；
- 在写入时重新核对权限、兼容性和预期当前值；
- 成功后追加 Adoption 决定并更新当前采用投影；
- 重复提交同一操作身份查回原 Adoption；
- 并发修改时拒绝旧 Generation 覆盖新决定。

回滚不是删除或修改旧 Adoption，而是新增一条 Adoption 决定，将项目默认指回此前仍获准的 Release，并说明触发 Finding / 退化证据。

### 6.3 在途工作不自动漂移

工作启动时固定它采用的资产版本清单：
- 新 Adoption 默认只影响生效后新启动的工作；
- 在途 Issue / SOP Execution / Node Attempt 继续使用其已固定版本；
- 若安全问题要求强制停止旧版本，须由相应有权维护者作出明确撤回 / 禁用决定；
- 迁移在途工作必须显式创建迁移决定，核对上下文兼容、重新输入 / 验证和负责人授权；
- 不能只修改 Project 默认指针，就声称所有正在运行的 Agent 已加载新版本。

## 7. Actual Usage：证明实际采用与使用

### 7.1 采用、选择、投递和使用是不同层级

每次 Work / Run 对资产版本的消费，尽可能记录以下阶段：

| 阶段 | 事实含义 | 可接受的证据 |
|---|---|---|
| Adopted | 项目当前决定采用某版本 | 权威 Project Adoption |
| Selected | 本次 Work / Run 解析选择了某版本 | Work Agreement / Run 输入清单 / 解析结果 |
| Delivered | 版本内容成功送到执行环境或宿主 | Adapter 投递回执、内容 Digest、目标 Runtime |
| Loaded / Observed | 宿主明确证明已加载 / 观察到该版本 | 宿主原生回执、受控探针或可验证运行时快照 |
| Used | 有证据证明本次执行实际消费了该版本 | 带有 Task / Run 身份及资产 Digest 的宿主消费 / 调用回执、可核验的资产调用记录或明确指向该版本消费行为的执行 Trace |

Task / Run 与资产 Digest 的关联只定位本次选择的版本，本身属于 Selected 依据；Used 还需上述实际消费证据。并非所有宿主都能证明 Loaded / Used。只能证明 Selected 或 Delivered 时，不得将其宣传为已实际使用；记录宿主、版本、观察方法、时间、覆盖范围和证据强度，缺失保持 Unknown。

### 7.2 资产使用清单

Work / Run 的实际使用清单至少记录：
- Asset ID、Release ID / Digest；
- 选择来源：Team 默认、Project Adoption、Issue 显式 Pin、人工覆盖；
- 解析时间和适用范围；
- 投递目标 Runtime / Host / Adapter 及其版本；
- 投递结果、回执 ID 和 Digest（若有）；
- Loaded / Used 的证据等级；
- 未投递、被覆盖、冲突或无法观察的原因。

同一 Run 可能同时使用多个 Skill、SOP、Rule、Knowledge 和 Runtime Adapter。每项独立记录，不用一个“项目版本”代替完整资产清单。

### 7.3 效果观察必须回到生产工作

发布后效果观察使用后续真实生产工作，不使用生成候选的同一批 Benchmark Trial 冒充生产效果。

Observation Cohort 固定：
- Project / Work Type / 风险层级；
- 使用 Release 的 Adoption 范围和时间窗；
- 实际 Selected / Delivered / Loaded / Used 的版本证据；
- 可比的基线工作或历史窗口；
- 质量、返工、重试、人工介入、时延、恢复和原生 Usage 指标；
- 未使用、混用版本和未知用量的排除 / 单列规则；
- 观察窗口、最低样本要求和停止条件。

如果采用组实际没有加载候选版本，或样本工作类型明显不同，不能将结果归因于该 Release。Observation 证据不足时保持 Pending Observation / Inconclusive。

## 8. 生产效果判定与回退

### 8.1 效果状态

| 状态 | 含义 |
|---|---|
| Pending Observation | Release 已采用，但生产样本 / 时间窗不足 |
| Improving | 在可比生产样本中满足预设改善方向，尚未达到最终观察要求 |
| Stable | 达到预设观察窗口、样本量和质量 / 成本门槛 |
| Regressed | 出现超过阈值的质量、安全、返工或运行退化 |
| Inconclusive | 样本、使用证据、可比性或计量覆盖不足 |
| Stopped | 观察被有权主体终止，保留终止原因 |

Benchmark Passed 只能支持进入 Release 审核，不能直接把生产效果设为 Stable。

### 8.2 回退与撤回

发生退化或安全问题时：
1. 维护者 / 项目有权成员确认影响范围与严重度；
2. 必要时暂停新增 Adoption 或禁用 Release；
3. 通过新的 Adoption 决定将项目默认指回先前获准版本；
4. 对在途工作按风险决定继续、显式迁移或停止；
5. 记录受影响的 Run / Issue、资产版本和回退证据；
6. 新 Finding / Proposal 记录根因和后续改进。

回退是新的业务决定，不删除原 Release、原 Adoption、历史 Work 的资产 Pin 或 Usage 记录。已经发生的执行仍归属当时实际使用的版本。

## 9. 故障、竞争与恢复

| 故障 / 竞争 | 必须保留的事实 | 恢复规则 |
|---|---|---|
| 候选修改后沿用旧 Benchmark | Candidate Revision Digest 已变化 | 拒绝沿用，创建新 Experiment |
| 同一 Sample 的 Baseline / Candidate 输入不同 | 两侧输入摘要 | 排除配对并说明 task_changed，不伪造改善 |
| Scorer / Judge 版本变化 | 两侧判定器版本 | 不可比配对单列；必要时统一重评 |
| Trial 创建成功、响应丢失 | Trial Intent 与 Task 来源 | 查回原 Task，不重复创建 Trial |
| Benchmark 中途进程退出 | Experiment 与每个 Trial 状态 | 已完成不重跑，未创建继续，未知执行先对账 |
| Benchmark 汇总成功、通知失败 | 不可变 Result ID | 补投通知，不重复执行或汇总 |
| Release 发布成功、响应丢失 | Release ID / Digest | 查回原 Release，不重复发布 |
| 发布审核人权限撤销 | 当前权限事实 | 发布写入拒绝生效 |
| Adoption 写入成功、响应丢失 | Adoption ID / Generation | 查回原决定，不重复切换 |
| 两个成员并发更改项目默认 | Adoption Generation | 后提交者重读，不覆盖较新的采用决定 |
| Release 发布但项目未采用 | Release 事实 | 不自动改变项目默认 |
| Adoption 已生效但投递失败 | Adoption 与 Delivery 回执分别存在 | 保持已采用但未投递，修复适配后重试投递 |
| Runtime 声称加载失败 | 真实目标 Runtime 与回执 | 标记未加载 / Unknown，不记作 Used |
| 生产工作仍使用旧 Pin | Work 固定版本 | 保留旧版本事实；迁移须显式授权 |
| 生产观察发现退化 | Observation / Finding | 暂停扩大采用，创建新 Adoption 回退决定 |
| 回退后迟到的旧 Observation | 原 Release / Cohort | 归原版本历史，不覆盖当前 Adoption |

## 10. 首个 VS-4 纵向验证范围

首个切片不建设完整资产市场或通用部署平台，只证明一条真实链：

1. 从一个已分诊 Improvement Proposal 建立 Candidate Revision，固定基线和变更内容；
2. 选择一组有来源、获准使用且可复现的 Benchmark Sample；
3. 固定 Experiment、Baseline / Candidate 两臂、Scorer、环境、重复次数和成功门槛；
4. 通过 D11 预算资格后，为 Trial 创建独立 Multica Task / Run；
5. 在隔离环境中执行两臂，读取真实 Task 终态、Evidence 和原生 Usage；
6. 对样本 / Judge / 环境逐对检查可比性，输出 Passed / Failed / Inconclusive / Execution Failed；
7. 由资产维护者审核并发布不可变 Release；
8. 由项目有权成员显式创建 Project Adoption，限定范围和在途工作策略；
9. 至少选择一个后续生产 Issue，记录其实际选择、投递和宿主可观察的 Loaded / Used 版本；
10. 在预设观察窗口内回收真实生产结果；证据不足保持 Pending Observation；
11. 故障注入：候选变化、Trial 响应丢失、发布响应丢失、Adoption 并发、投递失败、回退和旧版本在途工作。

首个切片可以只验证一种资产类型（建议 SOP 或 Skill）和一个 Project，不要求所有资产类型同时实现。

## 11. VS-4 完成标准

1. Proposal 内 Candidate Revision 固定基线、候选内容、依赖和适用范围，不等同于 D6 Candidate。
2. Benchmark Experiment 固定样本、输入、两臂、评价器、环境、重复次数、预算和成功门槛。
3. 每个 Trial 使用隔离的 Multica Task / Run，能查回来源、样本、实验臂和 Usage。
4. 不可比配对显式排除并说明原因；缺失样本和失败 Trial 不被静默丢弃。
5. 多维硬门槛不可由总分抵消；样本不足 / 计量不足返回 Inconclusive。
6. Release 由资产维护者审核并追加发布，不可变且依赖可定位。
7. Project Adoption 由项目有权成员单独决定，具备范围、Generation、生效时间和在途工作策略。
8. Release、Adoption、Selected、Delivered、Loaded / Observed、Used 分别记录，不能互相冒充。
9. 后续生产效果来自实际使用候选版本的生产工作，并有可比基线、观察窗口和最低样本要求。
10. 回退通过新的 Adoption / 撤回决定完成，历史 Release、Usage 和在途版本不被覆盖。
11. Benchmark / Improvement Task 的执行、Usage 和恢复复用 Multica，并遵循统一 Governance Purpose 隔离，不建立第二套控制面。
12. 同一操作重放、进程中断、响应丢失、并发 Adoption、投递失败和迟到观察均可恢复且不重复产生业务副作用。

Benchmark Trial 的治理用途、来源身份、预算和结果消费必须与 Evaluation 共用 Multica 原生执行隔离语义，不单独设计 Benchmark Task 类型或队列；统一规则见[VS-5 整体技术方案一致性审查](vs5-overall-technical-consistency-review.md)。

## 12. VS-4 收敛后的整体技术审查

VS-0 / VS-1 解决业务意图如何可靠绑定原生 Task；VS-2 解决产物、候选、证据和验收如何固定与竞争；VS-3 解决评价如何独立执行、计量和回写；VS-4 解决改进如何通过可比实验、审核发布、项目采用和生产效果回收。

纵向契约的横向关系已汇总到 [VS5](vs5-overall-technical-consistency-review.md)。当前从 E0 的来源查回与生产兼容设计开始；本契约在 E4 接入，先完成 E0–E2 的生产工作链和 E3 的治理隔离、评价与预算验收。首批资产及范围按 VS5 工程顺序确定。
