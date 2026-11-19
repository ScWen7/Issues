# VS-2 · Candidate、Artifact、Evidence 与 Acceptance 的技术承载契约

> 本文细化 [D6 候选交付与验收契约](d6-delivery-acceptance-contract.md)及[技术方案准备与最小纵向切片](technical-solution-readiness.md)中的 VS-2。
> Multica 源码基准：71683141a764ed3b1620db4bc26a2d0a098f135c。
> 本文定义逻辑写入契约和事务边界，不指定数据库表、API 路径或存储产品。

## 1. 设计结论

**Artifact 固定来源版本；Candidate 固定一次送审组合；Evidence 固定检查事实；Acceptance Decision 固定有权决定；Issue 完成是另一项业务状态转换。**

VS-2 需要建立两条关联但独立的版本链：
1. 产物版本链：Artifact → 不可变 Locator / Digest → Candidate Manifest。
2. 验收决定链：Candidate Generation → Evidence Applicability → Acceptance Decision → Issue Completion。

不能用文件名、latest URL、Issue revision、PR 当前状态、Run 成功或未固定顺序的附件集合替代 Candidate 身份。

所有入口必须在同一个 Issue 业务权威边界上竞争 Candidate 替换、验收决定和完成资格。工作台、SOP、手动操作和 PR 自动推进只提交命令，不各自实现一套验收判断。

## 2. Artifact：来源版本必须不可变定位

### 2.1 Artifact 是版本引用，不是可变文件名

Artifact 至少固定：
- Artifact ID 与所属工作区 / 来源范围；
- 类型与来源类型；
- 生产者、来源 Issue / Run / Node Attempt / 外部系统；
- 不可变 Locator；
- 内容 Digest（适用时）；
- 来源创建时间和首次取得时间；
- 当前可取得性与最近核验时间；
- 原来源读权和可分享范围。

| Artifact 来源 | 不可变定位 | 不可作为唯一定位 |
|---|---|---|
| Multica 附件 | Attachment ID + 内容 Digest；若存储提供版本 ID，则同时固定对象版本 | 文件名、签名下载 URL、latest URL |
| Git 仓库 | Repository identity + Commit SHA；必要时固定子路径和文件摘要 | Branch、HEAD、PR 页面 URL |
| PR | Provider + Repository + PR identity + 被评 Head SHA；合并后可另记 Merge Commit SHA | PR number 单独使用、当前 PR Head |
| CI / 测试报告 | Provider + Workflow / Job / Run identity + 被检查 Commit SHA + 报告摘要 | 最近一次成功 CI |
| 构建包 / 镜像 | Package / Image identity + immutable digest + 构建来源 | tag、latest、可变版本别名 |
| 外部资料 | 来源系统 ID + 修订 / 版本 ID + 内容摘要或可信版本标识 | 仅有可变网页 URL |

如果来源系统无法提供稳定版本，必须记录版本不可证明，不能伪装成不可变 Artifact。该 Artifact 可以用于临时协作，但不能单独支撑要求长期可复核的验收。

### 2.2 Digest 与可取得性是两个维度

Digest 证明重新取得的内容是否相同，不保证内容仍然存在；URL 可访问也不证明返回的是原内容。

因此分开记录：
- **Identity / Version**：原来是什么内容；
- **Availability**：现在能否按权限取得；
- **Integrity**：取得后是否与固定 Digest 一致；
- **Authorization**：当前接收者是否仍有权读取。

来源删除、权限撤回或存储对象过期时，不修改 Artifact Locator / Digest；将可取得性标记为 Unavailable / Revoked / Missing 等有来源依据的状态；Candidate 仍引用原 Artifact，历史验收不被静默替换。需要重新交付时产生新 Artifact 和新 Candidate。若当前门禁要求复核而原内容不可取，不能仅凭历史 Passed 推断当前仍可验证。

若产品要求长期审计，技术方案必须提供受控不可变快照或保留策略。是否复制附件字节、对象存储版本锁定或采用其他机制留待存储设计，不在本阶段选型。

### 2.3 Artifact 登记幂等

同一来源版本重复登记，应根据来源身份与版本定位查回原 Artifact；不能因为同一文件多次提交就生成语义重复的来源版本。内容相同但来源不同的两个 Artifact 可以分别存在，内容相同不代表生产者、权限、来源和责任相同。

## 3. Candidate Manifest：固定送审组合

### 3.1 创建时固定内容

Candidate Manifest 至少包括：
- Candidate ID；
- Issue ID 与交付目的 / Acceptance Channel；
- Candidate Generation（该通道内单调变化的候选代际）；
- Work Agreement / 要求版本；
- Artifact 条目清单；
- 每个条目的 Artifact ID、不可变 Locator、Digest、生产者和来源；
- 本次送审范围、说明与已知缺项；
- 适用 Acceptance Standard / Rubric 版本；
- 提交者、提交时间和来源操作身份；
- 规范化 Manifest Digest。

Manifest Digest 覆盖本次送审的业务内容：Issue / Acceptance Channel、Work Agreement / 要求版本、Artifact 条目及各自来源版本、送审范围、说明与已知缺项、Acceptance Standard / Rubric 版本。明确条目排序、字段规范化和摘要算法版本；Candidate ID、Generation、提交者、提交时间和来源操作身份作为提交元数据单独保存，不参与内容摘要。Digest 标识送审内容，sourceIntent 标识一次提交操作；相同内容可以在不同轮次形成不同 Candidate。Artifact 条目、验收范围、标准或工作约定等业务内容变化形成新 Candidate。

Candidate 创建后不可原地修改 Manifest。解释性补充按 [D6 的交付注记规则](d6-delivery-acceptance-contract.md#22-candidate-固定清单)追加到原 Issue，Delivery Record 从来源记录聚合。

### 3.2 多生产者组合由整合者明确提交

Worker、子 Issue 和成员可以独立产生 Artifact。它们不会自动组成父 Issue Candidate。

当前有权提交者明确选择哪些产物进入本次候选、每项产物的确切版本、哪些产物被排除、各来源生产者与授权，以及是否已完成必要集成。整合者对组合负责，不取代原生产者身份。不能把同名文件或各 Worker 最新一次上传自动拼成候选。

### 3.3 Candidate Generation 与 Issue revision 分离

Candidate Generation 是某个 Issue + Acceptance Channel 下的候选竞争代际，只在候选替换或当前候选指针变化时推进。

Issue revision 可能因评论、描述、优先级等无关操作变化；它只保护 Issue 自身条件写入，不是候选版本。

Candidate 替换请求必须携带预期的当前 Candidate ID / Generation；服务端在权威写入时再次核对。若仅 Issue revision 变化但当前 Candidate 未变，可以重读后重试；若 Candidate 已被替代，必须按新候选重新提交或明确合并，不能覆盖。

同一 Issue 可以有多个 Acceptance Channel（例如代码交付与文档交付），每个通道各自维护当前候选和决定范围。首期如无明确并行验收需求，可以每个 Issue 只启用一个默认通道；不要因此把 Candidate Generation 与全局 Issue revision 混为一谈。

## 4. Evidence：检查事实与适用关系

### 4.1 Evidence 本身不可改写

Evidence 至少固定 Evidence ID、Candidate ID 或 Artifact ID + 精确版本、Requirement / 条目及标准版本、检查主体、方法 / 工具 / 环境 / 输入（适用时）、原始报告或可回读来源、结论、覆盖范围、局限、产生时间、来源可信度和授权依据。

结论包括 Passed、Failed、Not Verified、Not Applicable。修正错误报告时追加新的 Evidence 并引用被更正记录；不覆盖原结论。

### 4.2 Evidence Applicability 是独立判断

Evidence 对原 Candidate 的引用不变。若新 Candidate 需要复用旧 Evidence，必须创建明确的适用性记录，说明原 Evidence 与目标 Candidate、Requirement / 标准版本、Artifact 版本是否相同、变更影响分析及复用理由、决定者 / 规则和时间，以及仍未覆盖的范围。

只有在检查对象、要求、环境和影响范围足以证明未受变化影响时才允许复用。Evidence Applicability 不是把旧 Evidence 的 Candidate ID 改成新 ID。

默认规则：候选换版后旧 Evidence 不自动适用于新候选。无法证明时重新检查。

### 4.3 Evaluation 不自动成为 Evidence

模型评价可以产生 Evaluation 和 Finding。若某项评价被工作约定指定为验收门禁，需要将其作为明确的检查结果 / Evidence 引用，并保留评价器版本、输入快照、覆盖和局限；它仍不取代有权 Acceptance Decision。

## 5. Acceptance Decision：追加式业务决定

### 5.1 决定内容

Acceptance Decision 必须固定 Decision ID、Issue、Acceptance Channel、Candidate ID + Generation + Manifest Digest、Work Agreement / Acceptance Standard 版本、决定者及当时权限证明、决定结果与接受范围、支持的 Evidence / Applicability、未满足项 / 例外理由 / 风险、来源操作身份和被替代 / 撤销的先前 Decision（如有）。

Decision 是追加式历史事实。纠正、撤销或重新决定时产生新 Decision，引用被替代决定和原因。不得修改旧决定使它看起来从未发生。

### 5.2 决定类型

| 结果 | 必需条件 | Candidate 语义 |
|---|---|---|
| Accept | 全部必需要求有适用 Evidence 支持，决定者具备权限 | 当前 Candidate 可标记 Accepted |
| Partial Accept | 明确接受范围、用途、限制和剩余责任 | Candidate 为 Partially Accepted；剩余范围仍待处理 |
| Reject / Request Changes | 指明未满足要求或证据不足 | Candidate 为 Rejected；生产方按授权修正或提交新候选 |
| Exception Accept | 明确允许例外的权限、不可豁免检查排除、风险理由、期限 / 条件 | 只对声明范围生效，不把失败 Evidence 改成 Passed |

Decision 不能自动扩大到其他 Candidate、其他 Acceptance Channel 或其他 Issue。

### 5.3 权限在决定生效时复核

决定者提交时有权限，不代表异步审核期间权限一直有效。Acceptance 命令在生效边界核对当前 Issue 状态、决定者当前验收角色 / 权限、权限覆盖范围、Work Agreement / 标准版本，以及是否已有撤权、候选替代或冲突决定。

无法证明权限时拒绝生效，保留请求及拒绝原因；不能按创建请求时的旧权限追溯授权。

## 6. 权威写入与并发竞争

### 6.1 单一竞争边界

Candidate 替换、Acceptance Decision 生效和 Issue 完成资格，必须在同一 Issue 权威写入边界按 Acceptance Channel 串行化。

该边界沿 Multica Issue 的原子权威提交落实；受控交付域可以准备不可变 Candidate / Evidence 并提交命令，当前候选指针、Generation、有效 Decision 和完成资格仍在同一 Issue / Channel 权威边界核验。每次命令携带预期 Candidate / Generation / Standard；写入时再次校验当前候选、权限、Evidence 和完成条件，业务决定与待处理下游动作共同可查回。PR、手动、SOP、批量和其他原生完成入口均须经过该校验；具体集成方案须满足 [VS5 原子边界及原生入口约束](vs5-overall-technical-consistency-review.md#62-必须具备的本地原子边界)。

本阶段不决定锁、CAS 字段或事务实现；后续技术设计需要以 Multica 的实际事务能力证明可实现。

### 6.2 逻辑命令契约

**SubmitCandidate(issue, channel, expectedCurrent, manifest, sourceIntent)**

- 验证提交者权限、来源 Artifact 可取得性 / 完整性和 Work Agreement；
- 先按 sourceIntent 查回原提交结果；重送的业务内容须与原请求一致，返回原 Candidate 时保持当前候选指针不变；
- 对新的 sourceIntent，先检查 expectedCurrent / Generation，再与该通道当前 Submitted / Under Review 候选比较业务内容摘要；内容相同则记录本次操作返回该当前候选，保持代际不变；
- 其余合法的新送审形成新的 Candidate ID 和 Generation；内容与历史候选相同，或当前候选已退回 / 撤回时，保留相同内容的来源引用，原候选的处置历史和决定保持原归属；
- 新候选登记、当前指针、Generation 及来源操作结果在权威入口原子提交；
- 旧候选转为 Superseded 的派生状态，历史 Evidence / Decision 不变；
- 同一 sourceIntent 重送查回原 Candidate。

仅补充 Evidence 时沿 `RecordEvidence` 处理，当前候选可继续核验；成员明确要求退回后的重新送审或恢复历史内容时，使用新的 sourceIntent。新候选复用旧证据须记录 Evidence Applicability，不继承旧 Acceptance Decision。已完成 Issue 的再次送审先按 D6 的重开或后续 Issue 规则处理。

**RecordEvidence(candidate, requirement, standard, result, source)**

- 验证 Evidence 指向的 Candidate / Artifact / 标准版本；
- Evidence 追加保存；
- 重复来源回执幂等；
- 迟到结果归原 Candidate，不自动推进当前候选。

**DecideAcceptance(candidate, generation, standard, decision, actor, evidenceSet)**

- 核对候选仍为当前候选；
- 核对 Manifest Digest、标准、权限和 Evidence 适用性；
- 追加 Decision；
- 更新 Candidate 当前状态投影；
- 如有待办通知 / 后继动作，写入可恢复意图；
- 若候选已替代或权限变化，拒绝并要求重读 / 重新确认。

**CompleteIssue(issue, expectedCandidate, expectedGeneration, requiredDecisions, completionConditions)**

- 重新读取当前工作约定、候选、Decision、Evidence、Issue 状态和所有额外完成条件；
- 具名验收要求必须有覆盖当前候选与标准的有效 Decision；
- 部分接受仅在工作约定允许且所有剩余必需范围已处理时才可完成；
- PR / CI 条件如被声明为必需，核对其固定来源版本和当前状态；
- 满足后在同一权威边界完成 Issue；否则返回具体缺项。

### 6.3 关键竞争结果

| 并发顺序 | 唯一有效结果 |
|---|---|
| Candidate C1 被 C2 替代先提交，随后 C1 Accept | C1 Accept 被拒绝；C2 是当前候选 |
| C1 Accept 先提交，随后 C2 替代 | Decision 有效归 C1；C2 新候选不继承接受 |
| C1 Accept 与 C2 替代同时提交 | 按权威边界串行化；后执行方必须基于新当前状态重新校验 |
| Issue 无关评论先增加 revision，Acceptance 后提交 | 重读后若 Candidate / 标准 / 权限未变，可在新 revision 上重试 |
| Acceptance 先提交，Issue Done 还未提交时 C2 替代 | Done 命令重新校验时发现当前候选已变，不得以 C1 Decision 完成 Issue |
| Issue Done 先提交，随后 C2 提交 | 不自动改写 Done；C2 必须走显式重开或新 Issue |
| 标准升级与旧标准 Accept 竞争 | 旧 Decision 只能归旧标准；当前完成条件要求新标准时不能完成 |
| 权限撤销与 Accept 竞争 | 以决定权威写入时的当前权限为准；撤权先生效则拒绝 |
| PR 全部合并但 Acceptance 缺失 | 若工作约定要求 Acceptance，PR 自动推进不得完成 Issue |
| PR 新增 / 取消与 Done 竞争 | Done 时重新读取当前 PR 必需集合并核对，不使用旧页面快照 |

## 7. PR、CI 与所有完成入口

Multica PR 自动完成当前具备独立的原生条件写入：重新检查关联 PR 是否全部 merged、Issue 当前状态及项目流程目标。但它不核对 AgentPlatform 的 Candidate、具名验收或标准版本。

因此 AgentPlatform 的集成必须将 PR 自动推进视为一个触发来源，不是一条旁路：
1. PR Webhook 到达后取得受影响 Issue；
2. 读取当前 PR 集合和固定 head / merge / CI 来源；
3. 调用统一 Completion Gate；
4. Gate 读取当前 Candidate、Acceptance Decision 和 Work Agreement；
5. 只有全部条件满足才允许 Issue 完成；
6. PR 关联集合或 Issue 状态在竞争期间变化时，按权威条件写入重新判断；
7. 通知失败只补投通知，不重复业务完成转换。

手动完成、批量完成、Project Workflow、SOP 出口与 PR 自动完成均使用同一完成资格规则。入口可不同，完成条件不能不同。

## 8. Delivery Record 与历史可追溯

Delivery Record 是可重建的交付过程视图，聚合 Artifact 生产与可取得性、Candidate 提交 / 替代 / 撤回、Evidence 与 Applicability、Acceptance Decision、Issue 完成或重开、接收方消费、交接，以及带 Candidate 引用的原 Issue 交付注记。注记的权威来源、署名和追加规则见 [D6](d6-delivery-acceptance-contract.md#22-candidate-固定清单)；同一注记操作重送查回原记录。

它不另建一套 Candidate / Decision 状态，也不成为权威写入入口。历史事实按原对象引用，不因当前候选指针变化而重写。

## 9. 故障恢复与验收场景

| 故障 / 竞争 | 必须保留的权威事实 | 恢复方式 |
|---|---|---|
| Artifact 登记后来源上传响应丢失 | 来源 ID、版本 Locator、Digest | 按来源版本查回原 Artifact |
| Candidate 已提交，返回响应丢失 | Manifest Digest、Source Intent、Candidate ID | 重送查回同一 Candidate |
| C2 已替代 C1，成员再次送审 C1 的内容 | 新 sourceIntent、预期 C2 / Generation、C1 的内容摘要 | 创建 C3 并推进代际，引用 C1 的内容来源；C1 / C2 的历史决定保持原归属 |
| 候选被退回后补齐证据并明确再次送审 | 新 sourceIntent、原候选、补充 Evidence | 创建新候选并记录证据适用性，不因摘要相同取回已退回候选 |
| 当前 Submitted / Under Review 候选收到相同内容的新提交 | 当前 Candidate / Generation、相同业务摘要 | 返回当前候选并保存该次操作结果，不推进代际；旧操作重放仍查回自己的原结果 |
| Candidate 创建成功但当前指针未确认 | Candidate 与当前通道状态可核对 | 读取权威指针；补完成仍有效的转换，不重复创建 |
| Candidate C2 已替代 C1，旧检查迟到 | Evidence 仍指向 C1 | 保存历史结果，不推进 C2 |
| Acceptance 已生效，响应丢失 | 不可变 Decision ID 和目标 Candidate | 查回原 Decision，不重复接受或发通知 |
| Acceptance 写入前权限撤销 | 当前权限与撤权事实 | 拒绝生效，要求新有权主体决定 |
| Acceptance 生效后 Issue 完成失败 | Decision 已生效，Issue 未完成 | 重试 Completion Gate；不重写 Decision |
| Issue 完成已提交，通知失败 | Issue 完成事实已生效 | 补投通知 / 重建投影 |
| 附件删除或来源失权 | Artifact 原 Locator / Digest 和可取得性变化 | 标记不可取；不替换旧 Artifact，必要时新交付 |
| PR 全部合并后新增未合并 PR | 当前 PR 集合与状态 | Completion Gate 拒绝或等待，后续事件再评估 |
| Issue Done 后收到旧 Acceptance / PR 事件 | 原 Decision / 事件来源 | 归历史对象，不反向覆盖新业务状态 |

首轮验证必须覆盖 Candidate / Accept 竞争、Accept / Done 竞争、无关 revision 变化、PR 集合变化、权限撤销、附件删除、重复提交与响应丢失。

## 10. VS-2 完成标准

- Artifact 使用来源类型匹配的不可变 Locator；无法证明版本时明确 Unknown / Mutable。
- Digest、可取得性、完整性和读取权限分开判断。
- Candidate Manifest 固定 Work Agreement、Artifact 版本、送审范围、标准和 Digest。
- Candidate Generation 独立于 Issue revision。
- 多 Worker 产物由有权整合者明确组合，不自动拼接 latest。
- Evidence 不可改写；复用到新 Candidate 必须有独立 Applicability 依据。
- Acceptance Decision 追加保存并绑定 Candidate / Generation / Standard / Actor / Evidence。
- Candidate 替代、Acceptance 和 Issue Done 由同一权威竞争边界协调。
- 手动、批量、SOP、Project Workflow 和 PR 自动入口服从统一 Completion Gate。
- 响应丢失可查回原 Artifact / Candidate / Decision / Issue 结果，不重复产生副作用。
- 历史候选、证据和决定不被新版本覆盖；来源失效可见。

## 11. 后续技术设计前置

VS-2 收敛后，仍需确定 Artifact 快照与对象保留的具体存储能力、不可变交付记录与 Issue 原子提交的具体承载、Candidate Generation / Source Intent 的唯一约束与并发写入实现、Acceptance 权限复核来源、PR / CI Provider 适配、Evidence Applicability 的审核权限，以及统一 Completion Gate 与现有 PR 自动完成代码的接入方式。

这些是接口、存储和迁移设计工作；不要求新增第二套 Issue 状态机或执行控制面。
