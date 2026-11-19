# D6 · Candidate、交付版本与验收竞争的源码取证

> Multica 取证基准：`fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc`；此前已对照主干快照 `ff41e7a77010fcac63f9d1e7244161fe99b6b69e` 核验关键文件一致。
> 本文区分 Multica 原生事实与 AgentPlatform 应补足的产品语义；不把设计对象误写成底座已有表或 API。

## 1. 结论先行

Multica 已有比较成熟的**文件交付呈现与历史版本浏览**，但它不是完整的 Candidate / Acceptance 管理系统。

原生机制：
- 评论附件是交付区的主要文件来源；Issue 描述附件是输入资料，不作为产出交付。
- 同名且同规范化内容类型的上传被归为同一个文件的不同版本；历史版本按附件 ID 定位，列表和打开默认使用最新上传。
- 带附件的评论创建、附件锁定和附件关联在同一数据库事务内；评论附件集合后续也能编辑，并可按权限删除普通附件。
- Issue 更新支持 `expected_revision`，SQL 在实际更新行上重新核对修订号。
- PR 自动推进是独立的 Issue 状态入口；事务 SQL 再检查 Issue 原状态和所有关联 PR 当前是否合并，避免 PR 状态判断与写入之间的竞态。
- 但 PR 自动推进不核对验收人、Candidate 附件组合或验收标准；普通状态更新也不要求请求携带正在验收的候选。

AgentPlatform 需要补足：
- Candidate 是不可变的**交付组合**，不是文件名分组，也不是某一个附件。
- Evidence 必须绑定被检查的具体 Candidate / Artifact 版本、标准版本和实际检查环境。
- Acceptance Decision 必须绑定具体 Candidate、适用 Work Agreement / 标准版本、决定者、权限、决定范围及依据。
- 换版、验收和 Issue 完成需要在 Issue 权威写入边界按当前候选与标准条件竞争；PR 合并只能提供一个工程事实，不能替代业务验收。
- 历史决定不能因最新链接变化、附件删除或新候选提交而被改写；引用失效要明确标记，不能静默替换为“最新”。

## 2. Multica 交付区：同名文件版本，不等于候选版本

### 2.1 交付区分组规则

`packages/core/attachments/deliverables.ts` 定义：
- 只有评论中上传的附件计入 Issue 交付；Issue 描述附件是输入，不计为产出。
- 以规范化 content type + filename 作为文件分组 key。
- 相同文件名和类型的再次上传视为同一文件的新版本。
- 按上传时间和 UUIDv7 排序，保留版本列表；latest 指向最新上传。
- 删除的评论不再贡献文件；完整附件库存与时间线叠加，处理历史来源和 tombstone。

源码：[deliverables.ts](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/packages/core/attachments/deliverables.ts#L1-L155)

详情页的版本切换器使用附件 ID 定位具体版本；复制链接则以文件名生成“最新版本”链接，而不是固定版本链接：

- [版本切换器](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/packages/views/issues/components/deliverables/deliverable-details.tsx#L119-L169)
- [复制最新链接](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/packages/views/issues/components/deliverables/deliverable-details.tsx#L90-L115)

因此，交付区可以回答“这个文件上传过哪些版本”，但不能回答“本次验收的完整候选由哪些文件 / 仓库修订共同组成”。文件名分组可能把不同工作目的、不同候选、不同生产轮次的文件归到一起。

### 2.2 上传、关联与编辑

带附件发评论时，Multica 在同一事务中：
1. 锁定未关联附件；
2. 创建评论；
3. 锁定并验证附件是否仍属于可用范围；
4. 将附件关联到评论；
5. 提交事务。

附件已被其他操作删除或不可用时，整笔评论附件提交冲突，不会出现“评论已可见但附件关联缺失”的半成品。

- [评论与附件原子提交](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/comment.go#L1845-L1930)

但评论不是不可变交付记录。后续可编辑评论正文和附件集合；严格内容编辑、附件集合替换及取消由旧评论触发的待派任务可在同一事务处理。具备权限的主体也可以删除普通附件。

- [评论附件集合编辑](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/comment.go#L3470-L3550)
- [普通附件删除](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/file.go#L1487-L1527)
- [附件下载权限](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/file.go#L884-L921)

这意味着附件 ID 是历史定位身份，但不天然保证其字节内容永久可取。Candidate 若要成为可审计验收对象，必须固定附件 ID 和内容摘要 / 不可变存储版本，并明确删除或来源失效后的状态；不能仅保留文件名或 latest URL。

## 3. Issue 条件写入：保护修订，不自动保护验收对象

单项 `PUT /api/issues/:id` 支持 `expected_revision`：
- Handler 对已读 Issue 修订先做检查；
- SQL 在真正更新目标行时再次比较修订号；
- 普通评论也会推进 Issue revision；
- 状态选择器等一般写入并不自动携带用户当时查看的 Candidate 和验收标准。

- [Handler revision 检查](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/issue.go#L4035-L4085)
- [SQL 最终条件](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/issue.sql#L290-L325)

`expected_revision` 能防止基于旧 Issue 快照的覆盖，但它不是验收语义本身。若一次无关评论增加 revision，验收提交可能发生 revision conflict；重新读取后，只要 Candidate、标准、权限和必需证据未变，可以在新 revision 上复核同一决定。反之，即使 revision 未变，若接受请求没有明确固定 Candidate / 标准，也无法证明接受的是用户实际查看的交付组合。

## 4. PR 自动完成：有条件状态推进，不是业务验收

固定版本的 PR 自动推进路径：
1. 读取 Issue 关联的 GitHub 与自托管 PR 状态；
2. 检查工作区自动完成目标、Issue 级禁用开关、Issue 是否终态 / Triage、目标状态是否属于项目工作流；
3. 只有关联 PR 全部 merged 才进入写入；
4. 在事务中调用条件 SQL；
5. SQL 再次核对 Issue 仍处于决策时看到的状态、至少存在一个关联 PR，且所有关联 PR 在写入时仍全部 merged；
6. 两个 PR merge 竞争只移动一次；判断与写入之间新增未合并 PR 时，不完成 Issue。

- [决策和入口](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/pr_auto_complete.go#L173-L242)
- [事务写入与事件](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/pr_auto_complete.go#L243-L318)
- [SQL 原子条件](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/pr_automation.sql#L58-L96)
- [PR 关联竞争测试](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/pr_auto_complete_race_test.go#L26-L51)

**它只证明工程 PR 条件满足，不证明当前 Candidate 已被业务接受。** 写入 SQL 不比较验收人、附件组合、Acceptance Decision 或 Work Agreement 标准。若 AgentPlatform 的 Issue 完成条件要求具名验收，PR 自动完成必须服从该门槛，不能绕过它。

## 5. 从 Multica 原生事实推导 AgentPlatform 的 Candidate

Candidate 不应是“交付区最新文件集合”，也不应把每次上传都自动升级成一个可验收候选。

一次 Candidate 必须由提交者或受托交付方明确提交，并固定：
- 所属 Issue 与交付目的 / 工作约定版本；
- 本次交付包含的 Artifact 清单及每个 Artifact 的具体版本；
- 文件附件 ID + 内容摘要 / 不可变存储版本，或仓库 commit / PR head SHA，或其他可定位的来源版本；
- 每个 Artifact 的生产者、来源 Run / Member、产生时间及可取得性；
- 本次送审范围、变更摘要和已知缺项；
- 适用的检查要求 / 验收标准版本。

Candidate 创建后不可原地改组成。增加、替换、撤回其中一份 Artifact，若改变送审组合，就形成新的 Candidate。原 Candidate 和已有 Evidence / Decision 仍保留，不能用最新文件链接覆盖。

一个 Issue 可有多份历史 Candidate，但同一验收通道 / 交付目的在同一时点只能有一个 current submitted Candidate；并行生产可以产生 Artifact 或候选草稿，不代表自动替换当前送审版本。

## 6. Evidence 与 Evaluation 的边界

Evidence 是可核查事实，不是结论性评价。对检查结果至少固定：
- 被检查 Candidate ID 和 Artifact 版本；
- 检查标准 / Work Agreement 版本；
- 执行者与执行身份（Member、Agent、独立 Reviewer 或受管检查）；
- Run / 环境 / 工具版本、测试输入和时间（适用时）；
- 每项要求的通过、不通过、未验证或有理由的不适用；
- 原始报告、日志、测试结果或可回读来源；
- 对哪些范围有效、哪些范围未覆盖。

同一 Candidate 的 Evidence 可以增量补充；不能因新 Evidence 到达而改写原检查结果。标准变化时，旧 Evidence 保留原标准版本，接收方判断是否需要重验。Candidate 换版后，旧 Evidence 默认仍指向旧 Candidate；仅当检查对象和影响范围证明不受变化影响时，才可显式复用。

Evaluation 可以汇总质量、风险或趋势，但不能替代 Evidence，也不能替代有权主体的 Acceptance Decision。

## 7. 验收决定与换版竞争

Acceptance Decision 必须绑定：
- 决定者及其在该 Issue 上的当前验收权限；
- 被接受的 Candidate ID；
- 适用 Work Agreement / 标准版本；
- 决定范围（整体接受、限定用途 / 范围接受、退回或例外放行）；
- 必需 Evidence 与例外理由；
- 决定时间和有效状态。

并发规则：

| 先发生的事实 | 后到请求 | 必须结果 |
|---|---|---|
| Candidate C1 被 C2 替代 | 验收人基于 C1 提交接受 | 拒绝作为当前候选接受；C1 的决定历史不删除 |
| C1 接受决定先生效 | 随后提交 C2 | C1 决定仍有效于 C1；C2 成为新的待处理候选，不能继承 C1 的接受 |
| 验收请求与 Candidate 替代同时提交 | 两者竞争 Issue 权威写入 | 以同一权威写入边界串行化；失败方重读当前 Candidate 后重新确认 |
| Issue 标准版本变化 | 旧 Candidate 的验收请求迟到 | 按旧标准保留历史决定；当前完成条件若要求新标准，则不得用旧决定完成 |
| PR 全部合并，但 Candidate 未被具名接受 | PR 自动完成事件到达 | 若工作约定要求验收，禁止仅凭 PR merge 将 Issue 完成 |
| Candidate 已接受，随后关联 PR 新增或状态变化 | 完成请求 / PR 自动推进 | 按当前完成约定重新核对仍必需的工程条件；不静默沿用过期的 PR 集合 |
| 已完成 Issue 出现新交付 | 新候选提交 | 不自动改写已完成事实；按显式重开规则或新 Issue 处理 |

**换版先发生**：旧候选验收不能改变当前候选或完成 Issue。

**接受先发生**：决定归属旧候选；后续新候选不能继承接受。若 Issue 已完成，新增交付必须走显式重开或后续 Issue。

## 8. D6 当前结论与实现前置

已收敛的产品规则：
1. Artifact 是来源版本；Candidate 是固定组合；Evidence 是事实依据；Delivery Record 汇总交付与处置；Decision 是有权主体的业务决定。
2. 文件分组与最新链接只用于浏览，不是 Candidate 身份。
3. 每个 Candidate、Evidence、Decision 都固定对象与版本；旧记录不可被新版本覆盖。
4. 候选替代、验收和 Issue 完成必须按当前 Candidate、标准和权限竞争。
5. PR merge 是工程事实；是否完成 Issue 仍取决于本项工作约定。
6. 部分接受和例外放行必须明确范围、用途、理由及未接受部分，不能用全局 Accepted 布尔值表达。
7. 多个生产方可以并行交付；汇总送审由有权提交方明确选择 Candidate 组合，不能按文件名或时间自动拼接。

仍需进入技术设计 / 验证的内容：
- Candidate / Decision 的权威写入是否放在 Issue 交付域，及其与 Issue revision 的条件写入边界；
- 文件内容摘要 / 不可变存储版本的获取与长期可取保证；
- 仓库修订、PR head、构建产物和附件之间的 Artifact 类型与定位规则；
- Evidence 的逐项要求映射与标准版本管理；
- 部分接受、例外放行、撤回和显式重开如何与 Issue 当前状态衔接；
- PR 自动完成如何读取当前 Candidate / Acceptance Gate，避免旁路完成；
- 并发测试覆盖换版先、验收先、标准变更、PR 新增 / 取消、重复提交和迟到报告。

本轮只收敛产品级契约，不设计数据库表和 API。
