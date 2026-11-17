# VS-5 · 整体技术方案一致性审查与最小实现切片

> 审查范围：整体系统架构、核心对象模型、生命周期 / 事件模型、跨层契约、核心一致性模型、Multica 底座边界，以及 VS-0 / VS-1 / VS-2 / VS-3 / VS-4 全部纵向技术契约。
> 目标：确认这些设计能否组成一套事实归属唯一、版本可追溯、跨层可恢复、可沿 Multica 原生执行链实现的系统；识别并修正专题之间的遗漏和语义冲突。
> 本文是架构级一致性审查，不是数据库 Schema、API、服务拆分或部署设计。所有“原子”“唯一”“幂等”均描述必须达到的业务语义，不代表当前底座已经实现。

## 1. 审查结论

**VS-0 到 VS-4 按以下四项横向契约衔接；工程先验证 E0–E2 的生产工作链，再接入评价与改进：**

1. 所有受管 Task 必须有明确的执行用途；生产协调 / Worker 与 Evaluation、Benchmark、Improvement 等治理执行不能混用生产执行语义。
2. 各业务来源使用自己的稳定意图身份；Multica Task 创建必须能按来源身份查回，不能把 Task 来源证据、Issue revision 或 (Issue, Agent) pending 唯一约束误当成通用幂等键。
3. Issue、Project、资产、预算、Task / Run、Usage 各有唯一权威写入边界；跨对象流程通过持久化意图、条件写入、幂等消费和对账最终一致，不要求全局事务。
4. 版本、授权和恢复规则必须贯穿从工作发起到结果消费、发布采用和生产效果观察的整条链；迟到结果只能补充其原对象，不能越代推进当前状态。

当前没有发现必须新增第二套 Issue、Task、Run、Runtime、Coordinator 或通用事件总线才能解决的结构性问题。需要补充的是 Multica 现有 Task / Run 执行模型的用途隔离和来源查回能力，以及 AgentPlatform 各业务权威域的最小扩展。

## 2. VS-0 到 VS-4 的横向审查结果

| 审查维度 | 已有契约 | 一致性结论 | 仍需统一的事项 |
|---|---|---|---|
| 工作归属 | Issue 是唯一业务工作归属；Project 维护范围与配置 | 一致 | Issue 的当前 Candidate 指针与不可变 Candidate 实体必须区分 |
| 业务派发身份 | Main Bot、Comment 目标、SOP Node Attempt 分别定义来源身份 | 一致 | Evaluation / Benchmark / Improvement Trial 也必须各自提供来源身份，不能套用生产 Worker 委派身份 |
| 原生执行 | Multica Task / Run / Runtime / Claim / Start / Retry / Reclaim | 一致 | Task Purpose 必须成为可查询、贯穿队列与查询的原生执行属性 |
| Task 幂等 | VS-0 / VS-1 要求按稳定 Intent 查回 | 方向一致，底座未覆盖 | 必须扩展原生派发边界，支持按来源身份唯一创建 / 查回；来源证据字段本身不够 |
| Session / Wakeup | VS-3 已识别治理 Task 污染风险 | 需横向推广 | Benchmark / Improvement Task 同样不能进入生产 Session 恢复和普通 Worker Wakeup |
| Candidate / Acceptance | VS-2 固定 Manifest / Generation / Decision | 一致 | Candidate 实体由交付域维护；Issue / Acceptance Channel 维护当前候选指针和完成资格，避免两个地方各自维护“当前候选” |
| Evaluation / Budget | VS-3 固定目标快照、预算预留、结果消费 | 一致 | Team / Project / Issue 多层预算必须有单一原子预留权威边界；不能分段扣额后再补偿 |
| Benchmark | VS-4 固定 Experiment / Sample / Arm / Trial | 一致 | Trial 必须复用统一 Task Purpose、来源身份、预算和结果消费契约 |
| Release / Adoption | VS-4 分离资产发布与项目采用 | 一致 | Release 归资产维护者；Adoption 归 Project 配置权威域；工作实际使用仍归对应 Work / Run |
| Usage | Multica Task Usage 是原生执行计量事实 | 一致 | 生产视图排除治理用途，团队总资源视图纳入治理用途；累计快照按覆盖 / 更正语义处理 |
| 事件 / 恢复 | 核心一致性模型定义持久化意图、Outbox / Inbox 语义 | 方向一致 | 这是目标语义，不得宣称当前 Wakeup Receipt 已等同完整 Outbox / Inbox |
| 权限 / 版本 | Work Agreement、授权代际、Candidate / Policy / Asset 版本均固定 | 一致 | 每个写入点必须复核当前权限和目标代际；启动时固定的历史版本不能替代当前撤权检查 |

## 3. 统一执行用途：Multica Task 的横向扩展

### 3.1 用途与执行角色是两个维度

**Execution Purpose 表示这次执行为哪类业务目的服务；执行角色表示 Agent 在该工作中承担什么职责。二者不能混成一个 Task Type。**

用途最小分类：

| Execution Purpose | 范围 | 是否进入生产工作质量抽样 | 成本归属 |
|---|---|---|---|
| Production | Issue 生产工作，包括 Main Bot 协调、Worker、SOP 节点执行及生产复验 | 按 D11 策略进入 | 生产执行成本 |
| Governance | 为评价、Benchmark、改进实验、校准或资产治理执行的 Task | 默认排除；如需审计须走独立治理策略 | 治理执行成本 |

Governance 需要可查询的子用途，例如 Evaluation、Benchmark、Improvement、Calibration。子用途用于来源归属、策略和统计，不代表分别建设队列或状态机。

Main Bot / Worker / SOP Node 是执行角色或业务关系，不是 Execution Purpose。一个 SOP 节点若实际执行生产工作，仍是 Production；Benchmark 中运行的 Agent 即使扮演 Developer，也仍是 Governance。

### 3.2 Purpose 必须影响哪些原生行为

Execution Purpose 不能只写进 Prompt、Task Summary 或 Task 来源证据。它必须在 Multica 原生 Task 创建后可查询，并贯穿：

1. **Pending 去重与 Coalescing**：治理 Task 不与生产 Task 竞争同一个 (Issue, Agent) pending 槽位，也不能被生产 Comment coalescing 吸收。相同治理来源身份查回唯一主 Task 及其合法 Retry 谱系。
2. **Session 恢复**：普通生产 Main Bot / Worker 的历史 Session 查询必须排除 Governance；治理 Task 使用隔离上下文和独立 Session。治理 Task 的 Retry 沿原生 retry 谱系，不进入生产恢复池。
3. **Issue Wakeup**：普通 Worker Wakeup 默认不消费 Governance Task 的终态。治理结果先由对应 Evaluation / Trial 消费器写入业务结果，再通过明确的业务通知唤醒负责人。
4. **Task 事件消费**：通用 Task 终态事件仍由 Multica 产生；业务消费者按 Purpose + 来源身份路由，不能把治理 Task 当成 Worker 交付。
5. **Usage / 成本视图**：Task Usage 继续归 Multica Task。生产成本视图只纳入 Production；团队总资源视图同时纳入 Production 与 Governance；任何汇总均按 Task 去重。
6. **重试与取消**：沿 Multica 原生 Retry / Cancel / Reclaim；用途和来源在重试谱系中继承，不生成新的业务 Evaluation / Trial 身份。

这是一项对现有 Task / Run 执行语义的扩展，不是第二个队列、Runtime、Daemon 或调度器。普通 Production 的既有 coalescing、Session continuity、Wakeup 和 Usage 行为必须保持兼容。

### 3.3 Task 创建必须同时具备 Purpose 和来源身份

创建或查回原生 Task 时，至少核对：
- Execution Purpose / Governance Sub-purpose；
- 来源业务身份及来源对象版本；
- Issue / Project（适用时）；
- 目标 Agent 和执行授权；
- Work Agreement / Candidate / Experiment 等固定输入版本；
- 执行角色和 Runtime 资格。

Task 来源证据继续作为来源导航和审计引用；稳定业务来源身份负责幂等查回。不能把 Purpose 当作幂等键，也不能把幂等键当作权限证明。

## 4. 统一身份与版本关联模型

不引入一个覆盖所有业务的万能 Intent 对象。每种业务来源继续维护自己的稳定身份；通过统一的引用要求将它们绑定到原生 Task / Run。

| 来源场景 | 稳定业务身份 | 必须固定的版本 | 原生 Task / Run 关系 |
|---|---|---|---|
| Main Bot 首次激活 | Issue 指派 / 持续授权转换 ID + 授权代际 + 目标 Agent | Work Agreement / Delegation 版本 | 一个 Production 主 Task 及原生 Retry 谱系；后续唤醒沿原生 Wakeup |
| Worker 委派 | Comment ID + Target Agent + 目标解析版本 | Comment 输入、目标解析和授权判定 | 每个目标独立绑定 Production Task，兼容合并须保存覆盖依据 |
| SOP 节点执行 | SOP Execution + Node Activation + Node Attempt + 本次调用 ID | SOP Definition、Work Agreement、输入 Candidate / Artifact、授权代际 | 一个或多个 Production Task / Run，分别保留真实执行谱系 |
| Evaluation | Evaluation ID + 固定目标版本 + 触发身份 | Policy、Work Agreement、Scorer / Rubric、Evidence Snapshot | Governance Task；Retry 归同一 Evaluation |
| Benchmark Trial | Experiment Revision + Sample ID + Arm + Trial ID | Candidate / Baseline Revision、样本、Judge、环境 | Governance Task；Retry 归同一 Trial |
| Improvement / Calibration | 对应 Proposal / Calibration 记录 + 本次执行身份 | 候选修订、基线、样本、Scorer / Rubric | Governance Task；不进入生产工作消费路径 |

所有业务关联遵循同一最低要求：
- 业务来源可以查回实际 Task / Run；
- Task 可以反查其业务来源、Purpose 和输入版本；
- 来源身份重复提交只查回原业务操作与主 Task；主 Task 的合法 Retry 子项通过原生谱系查回，每个子项保留独立执行事实；
- 来源已失效时不得创建新执行；
- 证据不足或出现多个互不相属的主 Task 候选时保持 Unknown 并对账；同一主 Task 的合法 Retry 子项按谱系识别。

## 5. 权威事实与写入边界总表

| 权威域 / 对象 | 唯一维护的事实 | 原子写入边界 | 其他模块的使用方式 |
|---|---|---|---|
| Issue（Multica 原生工作域） | 当前 Assignee、Issue 状态、业务完成状态、Issue 当前 Candidate / Acceptance Channel 指针及其完成资格 | 同一 Issue 的条件写入；指派 / 授权转换与首次激活意图必须同一权威提交 | Project Workflow、SOP、Delivery、Evaluation 读取并按当前版本消费 |
| Work Agreement / Delegation | 目标、范围、人工总责、Main Bot 授权、保留决定和授权代际 | 所属 Issue 的版本化授权写入边界 | 每次派发、结果消费和业务决定时复核当前有效代际 |
| Comment 委派来源 | 原评论、固定目标解析版本、每个目标的委派意图与状态 | 评论与附件原生保存；目标级意图可从固定解析版本恢复 | 逐目标绑定原生 Task；不以 Comment 已保存推断已接单 |
| SOP Execution / Node Activation / Attempt | 受托流程、节点激活轮次、尝试、结果消费和出口 | SOP 权威写入边界 | 通过原生 Task / Run 引用执行，不复制执行状态 |
| Multica Task / Run | Task Purpose、来源身份、排队、Claim、Start、终态、Retry 谱系、Runtime 回执 | Multica 原生 Task / Run 写入边界 | AgentPlatform 只绑定和消费，不复制执行控制面 |
| Artifact / Candidate | 不可变 Artifact Locator / Digest；不可变 Candidate Manifest / Generation | 交付域登记不可变对象；Issue 写入当前 Candidate 指针时复核预期 Generation | Evidence / Acceptance 引用确切版本 |
| Evidence / Acceptance Decision | 不可改写检查事实；有权主体对当前 Candidate 的追加式决定 | Evidence 追加写入；Acceptance 与当前 Candidate / 标准 / 权限在 Issue 完成权威边界核对 | Completion Gate 读取有效决定，不自行重算或覆盖 |
| Team / Project Evaluation Policy | 强制门禁、风险 / 抽样策略、预算周期和允许的评价器 | 对应 Team / Project 配置版本写入 | 每份 Evaluation / Experiment 固定采用版本 |
| Evaluation / Finding | 固定目标评价、结果、Finding 与证据引用 | Evaluation / 结果消费的幂等写入边界 | 回到原 Issue / SOP / Asset；跨工作 Proposal 由维护者分诊 |
| Budget Reservation | 单次、Issue、Project、Team 各范围的预留、结算、释放和更正 | **一个逻辑预算权威边界内全范围原子预留**；不能部分扣额 | Evaluation / Benchmark 通过预留资格启动，不直接改写各级 Policy |
| Improvement Proposal / Candidate Revision | 提案分诊、改进目标、不可变候选修订及来源 | Proposal / Revision 权威写入边界 | Benchmark 固定引用，不直接发布 |
| Benchmark Experiment / Trial / Result | 固定实验定义、样本、Arm、Trial、可比性和结果 | Experiment / Trial / Result 各自幂等写入边界 | Trial 使用 Governance Task；结果只支持审核 |
| Asset Release | 资产维护者发布的不可变资产版本和依赖 | 资产发布权威边界 | Project Adoption 只能引用已发布且未撤回版本 |
| Project Adoption | 项目对具体 Release / 配置版本的采用决定、范围和在途策略 | Project + Asset + Scope 的条件写入；决定追加并推进 Adoption Generation | 新 Work 固定采用版本，不推断在途工作已加载 |
| Actual Usage / Observation | Work / Run 实际选择、投递、加载、使用及生产效果证据 | Work / Run 的消费回执与观察记录分别追加 | 不反向改写 Release、Adoption 或历史 Run |
| Usage | 每个 Multica Task 的原生单位累计快照与来源更正 | Multica Task Usage 写入；平台归集先按原生计量身份去重 | 按 Purpose 生成生产、治理和团队总量视图 |

### 5.1 Candidate 当前指针与 Candidate 实体分离

Candidate Manifest 是交付域的不可变实体；Issue / Acceptance Channel 只维护“当前送审候选是哪一个、当前 Generation 是多少、完成资格如何判定”。

不允许 Delivery 域和 Issue 域各自维护两个可独立修改的“当前 Candidate”。Candidate 替换必须通过 Issue 权威入口条件写入当前指针；验收和 Issue Done 在同一业务竞争边界重新核对指针、Generation、标准、权限和有效 Decision。

### 5.2 Release 与 Adoption 分离

资产维护者对 Release 的发布 / 撤回负责；项目有权成员对 Project Adoption 负责。Project 当前配置是当前采用的权威投影，历史 Adoption 决定追加保留。C / Asset 域不得因 Release 发布自动修改项目默认；A / Project 域不得修改 Release 内容。

## 6. 跨对象事务、预算与恢复边界

### 6.1 不做全局事务

VS-0 到 VS-4 不要求 Issue、Multica Task、Artifact、Evaluation、Budget、Release 和 Project Adoption 共享一个全局事务。它们分别在自己的权威边界写入，跨域通过稳定来源身份、可恢复待办、条件写入、幂等消费和对账接续。

### 6.2 必须具备的本地原子边界

1. **Issue 授权 / 指派**：Issue 当前指派、授权代际和首次激活意图必须一起生效；之后 Task 派发可异步恢复。
2. **Task 创建 / 查回**：同一业务来源身份只建立一个兼容的主 Task。来源身份与主 Task 创建在 Multica 原生写入边界共同可查回；原生 Retry 可创建继承同一来源的子 Task，以 retry 谱系区分各次执行。同一派发请求重送返回主 Task 及其已存在的 Retry 链，同一次 Retry 的重送按原生重试关系查回子项。
3. **Candidate / Acceptance / Done**：Candidate 实体先固定；Issue 当前候选指针更新、Acceptance 生效、Issue 完成资格在 Issue 权威边界按预期 Candidate / Generation 条件竞争。若 Acceptance 与 Done 分次发生，Done 再次核对。
4. **Evaluation / Finding 消费**：同一 Task 终态重放只能生成一份有效结果和对应 Finding；通知失败只重投通知。
5. **Budget Reservation**：单次、Issue、Project、Team 所有适用额度一次性预留成功或全部不占用。预留和 Evaluation / Experiment 的稳定身份绑定，重复请求查回原预留。
6. **Benchmark Trial**：Experiment / Sample / Arm / Trial 身份先固定；Trial 与 Governance Task 绑定可查回；重复终态只消费一次。
7. **Release**：发布身份、候选 Digest、依赖和审核决定必须共同可查回；发布响应丢失不能重复产生不同 Release。
8. **Project Adoption**：Project + Asset + Scope 的当前 Generation 条件写入与 Adoption 决定共同生效；重复提交查回原决定。
9. **Actual Usage / Observation**：实际使用证据追加，不回写或覆盖 Release、Adoption 或历史 Run。

E0 的集成方案必须能承接上述 Issue 权威提交。扩展事实可直接登记在 Multica 的 Issue 事务内；若由外部域保存，则先固定不可变版本，再由 Issue 权威入口原子生效相关引用、代际、指派和可恢复意图。外部记录的准备成功不使委托或候选生效。先分别写外部状态、再调用普通 Issue 更新的多次独立提交，缺少这里要求的原子生效点。

所有能改变正式责任、指派、当前候选或完成资格的原生入口，都须接入同一权威校验：包含 UI / CLI / API 的单项与批量更新、Project Workflow 及自动完成路径。采用受控入口时，原生路径也必须经过公共校验或受相应写入限制，保留可旁路的原生写入不满足本契约。标题、描述及联系人属性按[工作约定的来源规则](cross-layer-contracts.md#31-正式工作约定与责任引用)保持识别、背景或投影用途，普通编辑沿原权限进行，执行目标由正式约定决定。

### 6.3 预算原子性与全局事务的关系

“全范围原子预留”仅要求预算权威域内对本次 Reservation 的全部适用额度作出一个全成或全败的决定，不要求把 Task 创建、Issue 更新或 Runtime 启动放进同一事务。

建议先记录 Evaluation / Experiment 的 Requested 身份，再由预算权威边界原子预留；预留成功后才创建或查回 Governance Task。Task 创建成功但响应丢失时先查回原 Task，不能释放预算后再创建另一 Task。Task 未创建且可证明失败时释放预留；已 Claim / Started 或执行状态未知时，在确认原生终态 / 处置前保留相应占用。实际 Usage 结算与预留释放分开记录。

如果 Team / Project / Issue 预算目前分属不同存储，必须先设计一个等价的原子额度协调边界；不能将多次独立扣额和补偿事务称为原子预留。

### 6.4 Outbox / Inbox 是语义，不是假设已存在的组件

核心一致性模型中的 Outbox / Inbox 描述可恢复投递和幂等消费要求。Multica Wakeup Receipt 是合并式协调信号，不等于永久业务事件日志，也不自动证明完整 Outbox / Inbox 已实现。

具体实现可复用现有权威记录、可扫描待办、Wakeup、事件回执和对账机制。只有当源码与实验能证明同一事务写入、重放和查回行为时，才可称为实现了对应语义。

## 7. 权限、版本与迟到结果的统一规则

每次跨层动作必须同时检查两种时间事实：

- **历史适用性**：动作最初依据哪个 Work Agreement、授权代际、Candidate、Policy、Experiment、Release 或 Adoption 版本创建；
- **当前可执行性**：现在是否仍有权读取输入、继续派发、写入当前状态或推进后继。

启动时固定的历史版本用于解释“当时执行了什么”，不构成永久授权。撤权、候选替代、标准升级、Release 撤回或 Adoption 回退后：
- 已发生事实保留在原对象；
- 未发生的后续动作重新核对当前授权和目标版本；
- 旧 Task / Run 的迟到结果只归原授权代际 / Candidate / Trial；
- 只有接收方确认它仍适用，才可作为当前工作参考；
- 不能以 Agent 身份未变、Issue ID 未变或 Session 仍存在推断旧授权继续有效。

Fencing 的目标是阻止旧执行覆盖当前权威事实。对于无法由中心原子拒绝的本地文件和外部副作用，必须采用工作副本隔离、分支隔离、进程确认或人工核验；停止请求本身不是旧执行已失去写入能力的证据。

## 8. Multica 底座复用与扩展清单

Multica 源码复核固定基准：71683141a764ed3b1620db4bc26a2d0a098f135c。VS-2、VS-3、VS-4 的上游专项研究分别固定在各自文档所列提交；D5 早期取证使用的旧提交不可自动视为当前基准，进入工程实现前必须对照当前目标分支重新核验相关路径。

| 能力 | 复用现有能力 | 必须补充 / 验证 |
|---|---|---|
| Issue / Project / Comment / PR | 原生对象、权限、工作流、评论与 PR 关联 | Issue 授权变更与首次激活意图的可恢复写入；统一 Completion Gate 接入所有完成入口 |
| 原生指派及 Workflow 交接入口 | 单项、批量和自动交接已有写入路径 | 指派、正式委托代际与首次激活在同一 Issue 权威提交生效；各路径接入公共校验或受控入口，验证旁路写入受约束 |
| Issue 标题 / 描述与上下文准备 | 原生编辑和描述取材 | 标题用于识别，描述作背景 / 变更建议；派发及继续执行投递正式 Work Agreement 正文、版本和授权代际，描述编辑不静默替换执行目标 |
| 通用 `actor` 属性 | 联系人字段和展示信息 | 正式总责及验收人读取 Work Agreement；属性修改只影响联系人 / 展示，不改变正式责任或权限 |
| Task / Run / Runtime / Daemon | 原生队列、Claim / Start / Retry / Reclaim、Run 事实 | 稳定来源身份唯一查回；Task Purpose / Governance Sub-purpose 可查询并贯穿执行语义 |
| Pending 去重 / Comment coalescing | 保留 Production 现有行为 | Governance Task 不与 Production 竞争槽位或被吸收 |
| Session continuity | 保留生产 Main Bot / Worker 的原生恢复 | 普通生产恢复排除治理用途 Session；治理执行独立上下文 |
| Issue Wakeup / Task events | 保留原生事件和唤醒机制 | 普通 Worker 消费路径排除治理 Task；结果写回后发出明确业务通知 |
| Artifact / Attachment | 复用附件上传、下载、评论关联、Git / PR / CI 来源 | 不可变 Locator / Digest、可取得性、完整性和权限分离；Candidate Manifest 固定组合 |
| Issue revision / 条件写入 | 复用原生 expected_revision 和事务入口 | Candidate Generation / Acceptance Channel 独立；Completion Gate 条件统一 |
| Task Usage | 原生 Task 级 Provider / Model / Token / USD / Credits 事实 | Purpose 分类视图、多源指标覆盖与更正；治理成本与生产成本分开 |
| Project config | 原生 Project 成员、工作流和配置 | Adoption 决定 / Generation / 范围 / 在途策略的权威记录与并发核对 |
| Wakeup Receipt / 事件投递 | 复用协调唤醒 | 明确哪些是合并信号、哪些是持久业务意图、哪些是结果消费回执；不得混为一个事件账本 |

### 8.1 禁止重复建设

- 第二套 Issue / Project / Comment / Assignee；
- 第二套通用 Task Queue、Run、Runtime、Daemon 或 Coordinator Pool；
- Evaluation / Benchmark 专用执行队列或 Runtime；
- 与 Multica 原生 Task Usage 并行的第二本实际执行成本账；
- 由工作台维护的第二套 Issue / Candidate / Evaluation 状态机；
- 用一个通用 Intent、Candidate 或 Event 对象取代各自业务来源和权威事实。

### 8.2 源码基准与证据边界

| 专题 / 研究 | 固定源码基准 | 本轮如何使用 |
|---|---|---|
| D5 早期派发与回唤研究 | Multica fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc；另有 0f3e15f1d9dca781155e2fe475161f8c5e499b44 对照 | 保留原研究结论和各自源码链接；不能当成 VS-0 / VS-1 当前 Task 创建路径已在 7168314 上全部复核 |
| VS-0 / VS-1、VS-2、VS-3、VS-5 跨层复核 | Multica 71683141a764ed3b1620db4bc26a2d0a098f135c | 作为当前 Task、附件 / PR、Session、Wakeup、Usage 等共性边界的统一复核基准 |
| VS-4 Benchmark 机制研究 | TeamAI 556b5246f2c13ad28b8b79b5b513a78ed8ab9dae | 只用于 Benchmark Plan、Trial、配对可比性和自改进阈值机制参考，不代表 AgentPlatform 发布 / 采用机制已由上游提供 |

进入 E0 时，以实际目标 Multica 分支核对主 Task 来源查回、Retry 谱系及生产派发相关路径；Governance 的 coalescing、Session、Wakeup 和 Usage 隔离在 E3 启用前完成专项核验。各阶段保留所用提交与取证路径，旧研究继续按其固定版本解释。

## 9. 实施依赖与最小工程切片

### 9.1 工程依赖与启用顺序

先交付 E0–E2 的生产工作链；治理执行在 E3 隔离验收后启用。

| 顺序 | 工程切片 | 包含内容 | 通过标准 | 后继 |
|---|---|---|---|---|
| E0 · 来源查回与生产兼容 | 稳定来源身份、唯一主 Task、Retry 谱系及 Purpose 基础表达 | 固定来源种类和原生查回关系，验证已有生产派发；明确历史 Task 的兼容映射，保留 Governance 扩展入口 | 重送查回同一主 Task，合法 Retry 可追溯，Production 回归通过 | E1 |
| E1 · 授权、派发与消费 | Work Agreement 修订 / 授权代际、Main Bot 首次激活、Comment 目标委派、受控结果消费 | 沿 Issue 权威入口确认责任与授权；Task 异步创建 / 查回；消费记录按原委派和代际条件提交 | 区分中心 Start 与宿主启动；派发和消费响应丢失可恢复；重复消费及旧代际回报按契约处理 | E2 |
| E2 · 交付验收闭环 | Artifact、Candidate Manifest / Generation、Evidence、Acceptance、Completion Gate | 首批一个默认验收通道，支持 Accept / Reject；说明追加到原 Issue，统一各完成入口 | 候选 / 接受 / Done 竞争、无关 revision、PR 集合变化、附件失效和视图重建通过 | 首条生产工作链验收，再进入 E3 |
| E3 · 治理隔离、评价与预算 | Governance Task 隔离、Evaluation、适用范围的 Reservation、Finding | 先完成 pending / Session / Wakeup / Usage 隔离验收，再开放评价派发；预留、结算与结果消费可查回 | 治理执行与生产分离；适用预算全成全败；固定 Policy、合法 Retry 与幂等 Finding 通过 | E4 |
| E4 · 改进验证与采用 | Proposal Revision、Benchmark / Trial、Release、Adoption、Actual Usage | 首批一个 Skill 资产、固定样本及一个项目；资产发布与项目采用分别决定 | 可比性、权限、采用并发、在途版本、退化回退和生产效果可追溯 | 按实际需要扩大资产类型与项目范围 |

E0–E2 仅开放 Production 派发；Governance 入口在 E3 隔离通过后开放。E0 设计来源表达时考虑第 4 节各类来源及 Retry 关系，实际接入和验收按所属阶段进行。

### 9.2 第一条真实端到端切片

E0 到 E2 完成后，用一个 Project、一类真实研发 Issue、一个协调 Agent、一个 Worker 和一种 Artifact 验证：

Issue → Main Bot → Worker → Multica Task / Run → Artifact → Candidate → Evidence → Acceptance Decision → Issue Completion。

首批按一个默认 Acceptance Channel 完成 Accept / Reject；部分接受、例外放行和并行验收通道保留 D6 的规则，启用时增加对应验收。第一条链的交付范围止于 Issue 完成。

E3 首批在单项目试点，先配置单次上限与项目周期额度；已有的 Team 底线或 Issue 限额也必须参与同一次原子预留。额度单位选用实际可观察、可控制的指标，缺失 Credits 保持 Unknown。完整四范围预算语义仍按 D11 / VS3 定义，新增启用范围时补相应并发与周期验收。

E4 再验证固定样本对照、发布、项目采用和真实效果；首批采用方式与观察窗口由试点项目明确。完整治理能力按试点结果逐步启用。

### 9.3 当前工程切片的前置条件

每个切片进入 Schema / API / 部署设计前，先落实该切片需要的契约与证据：

| 阶段 | 前置决定与验收输入 |
|---|---|
| E0 | 目标 Multica 提交、扩展代码维护位置、上游同步 / 升级策略；证明第 6.2 节的 Issue 原子提交可实现，并列明原生写入入口的接入 / 限制；主 Task 来源、Retry 及历史 Task 兼容方案；生产回归与故障注入范围 |
| E1 | Work Agreement 创建 / 修订 / 撤销、授权代际、人工总责与 Acceptor 的正式引用；正式正文与背景描述分开投递；受控派发和消费操作及服务端校验；原生指派、描述和属性入口的映射及旁路验收 |
| E2 | Candidate 业务内容摘要、不可变 Artifact 定位、交付注记的权威来源、Evidence 适用性、Completion Gate 条件竞争与重建验证 |
| E3 | Governance 隔离各入口的源码差异和回归；固定 Policy 的开工复核；实际启用预算范围的原子预留、释放及迟到 Usage 更正 |
| E4 | 候选 / 实验与发布的固定身份、项目采用权限及条件写入、真实使用证据与观察窗口 |

[工作约定与委托](cross-layer-contracts.md)维护授权规则；[派发绑定](vs0-vs1-dispatch-binding-contract.md)与[D5 结果消费](d5-cross-layer-recovery-contract.md#6-结果消费契约)维护执行衔接。具体事务实现按权威提交点证明，进程和存储布局在相应工程设计中决定。复用 Multica 所需的源码扩展、迁移和维护成本须在方案中列明。

### 9.4 后续 SOP 运行时切片

E2 验收后，项目需要受托流程时单独安排 SOP 运行时切片：固定 SOP Definition、持久化 Execution / Activation / Attempt、就绪推进、Task 绑定、结果消费和出口回交。先选择实际要使用的节点类型；使用受管 Script 前完成对应 Backend 适配。验收覆盖重入、输入换版、取消、消费重放和出口交还。

SOP 运行时的排期由项目需要决定，首个 E4 使用 Skill 即可验证改进闭环。后续选用 SOP 资产做运行对照时，先取得该运行时切片的验收结果。

## 10. 一致性审查后的未决事项

以下事项不再作为架构概念开放讨论，而作为工程设计 / 验证输入：

| 未决事项 | 必须取得的证据 | 当前处理 |
|---|---|---|
| 当前 Multica 分支对来源身份和 Purpose 的最小扩展方式 | 主 Task / Retry 查回、历史兼容和生产回归；治理隔离另有专项实验 | 来源与生产兼容为 E0 前置；治理隔离为 E3 启用前置 |
| 多层预算的原子 Reservation | 并发扣额、失败回滚、响应丢失和周期切换测试 | E3 前置 |
| Artifact 长期可取性 | 存储版本、删除、权限撤回和 Digest 回读验证 | E2 前置 |
| PR 自动完成所有入口接入 Completion Gate | 手动、批量、Workflow、Webhook 并发回归 | E2 前置 |
| 宿主 Loaded / Used 的真实覆盖 | Codex、Claude Code、Qoder、CodeBuddy 等实际回执 | 按宿主逐步覆盖；缺失保持 Unknown |
| Benchmark 样本规模与观察窗口 | 实际工作分层、可比配对、样本量和误差 | E4 运行校准 |
| 部署、数据库和 API 具体方案 | 负载、维护成本、事务能力、故障域和宿主约束 | 进入工程设计后再决定 |

## 11. VS-5 完成判定

VS-5 架构一致性审查达到以下条件：
1. VS-0 到 VS-4 的身份、版本、权限、状态和恢复关系可以在同一对象模型中解释；
2. Task Purpose 作为横向执行属性覆盖 Production 与 Governance，不为评价或 Benchmark 建立第二执行系统；
3. 每类业务事实有唯一权威写入者和明确的本地原子边界；
4. 跨对象流程不依赖全局事务，能通过持久化意图、幂等查回、结果消费和对账恢复；
5. Issue 当前 Candidate 指针与不可变 Candidate 实体、Release 与 Project Adoption、Adoption 与实际使用分别归属；
6. 预算、Usage、生产成本和治理成本口径一致；
7. Multica 复用项、扩展项和禁止重复建设项明确；
8. 实施依赖与首个真实纵向切片可按 E0 → E4 顺序推进；
9. 尚未有真实源码 / 实验依据的能力明确标记为待验证，不伪装成现有底座能力。

**审查结论：架构层面的横向边界已收敛，可以进入 E0 的详细技术设计；不代表已经完成工程实现，也不代表可以同时铺开所有模块。**

## 12. 当前工程阶段

当前推进 **E0 · 来源查回与生产兼容设计**。设计入口为 [E0 来源身份与生产兼容设计](e0-source-identity-production-compatibility.md)，源码审查见[Multica 派发来源审查](../research/e0-multica-dispatch-source-audit.md)。

已对照 Multica `main` @ `b70c8b96d0c638e73802336063abfe3734f69f65` 完成关键路径复核。确认普通 Agent 指派在 Issue 写入后异步 enqueue，Agent 派发分支忽略 enqueue 错误；现有 `trigger_evidence_kind/ref_id` 只承担来源导航；当前 pending 索引按 Issue、Agent、Comment Thread 及特定 deferred 状态保护队列槽位，不能替代业务来源身份；合法 Retry 必须与主 Task 唯一性分开处理。

E0 的最小扩展方向已收敛：业务来源侧先保存可恢复的来源转换 / 目标身份；原生 Task 创建边界写入主来源身份并提供幂等查回；来源侧与 Task 侧双向关联；pending 冲突只有在证明输入、授权和覆盖范围兼容时才能复用已有 Task。具体字段与事务实现仍待实际集成目标分支复核。

源码审查还明确了两个必须纳入 E0 的兼容边界：Issue 更新与 Agent Task enqueue 分属先后事务，异步 Activity 不能充当派发意图；普通 One-shot 是 AgentPlatform 授权模式，不是 Multica Assignee 的天然语义，受管 Issue 的后续 Wakeup / Comment / 状态触发必须核对授权模式。

当前仍需完成：
1. 确定实际集成 Multica 仓库 / 分支及扩展维护方式；
2. 对该目标 SHA 复核 Issue 写入、Task 创建、Retry、Comment coalescing 和历史兼容；
3. 形成最小迁移 / 回滚方案及真实故障注入验收步骤。

E0 尚未达到工程修改准入，不进入 Schema / API 实现。治理执行隔离仍在 E3 启用前实施与验收。
