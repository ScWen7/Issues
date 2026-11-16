# Multica 底座能力与扩展边界

协作工作以 Multica 的 Issue、负责人、项目工作流、Run、Runtime 与 Usage 为基础。此页按首期交付顺序对照固定版本的实现、项目配置和 AgentPlatform 所需的扩展。业务定义及适用场景见[架构总览](overview.md)。跨层输入、授权、执行和结果交接的目标语义见[跨层业务契约与协作协议](cross-layer-contracts.md)。

## 原生入口与项目配置

| 谁在什么情况下行动 | Multica 可直接沿用 | 项目约定或配置 | AgentPlatform 要补到什么程度 |
|---|---|---|---|
| 成员从项目或个人待办接下工作 | 从项目列表或「我的 Issue」可以打开原项，从提及通知可以定位原评论。Issue 描述、父项和项目仓库可提供依据。 | 负责人在原项写清目标和完成条件。已有适用的项目规则或资料可直接引用。 | 普通工作可按上述入口开始。项目要求统一选版时，再按本次分工和接收者读权提供适用版本，并让接手者能找到所用依据。[项目与个人入口](../research/05-source-evidence.md#项目待办与跨项接续) · [方法选用](03b-capability-governance.md#5-一次工作如何选择和投递能力) |
| 执行者交回成果，下一位成员取用 | 原评论保留提交者。同名同类型的附件按版本归集，可按附件 ID 打开具体上传。代码可在原评论引用可取回的提交，或交回补丁和对应基准。 | 结论本身足以交付时，成员直接署名说明。有检查要求时，说明检查对象、结果和缺项。 | 在原 Issue 让接手者能从本次交付定位相应版本与检查。需采用上游结果时，使用方注明实际采用哪一版。材料只在原机或缺外部读权时，指出可补交的人，让已可用的部分先行。[交付与接手](05-unified-workbench.md#交付与接手) · [版本与来源](../research/05-source-evidence.md#交付换版与验收写入) |
| 当前负责人请人决定，或把整项工作转给下一人 | 评论可提及决定人。原指派或已配置的 Project Workflow 可移交责任。私有项目的成员读取按项目权限检查，固定版的单项成员指派校验同工作区身份。 | 请求答复时保留当前指派。项目采用步骤交接时可配置接手者。 | 私有项目转交时，在指派生效处核对目标成员能打开原 Issue。返回旧通知或项目列表时，按已生效的责任、交付和决定呈现下一步。[项目访问与指派覆盖](../research/05-source-evidence.md#项目访问与执行资格) · [工作台回读](05-unified-workbench.md#从项目和个人工作找到下一步) |
| 成员在原讨论用 `@Agent` 请求一次协助 | 原线程按路由和调用资格派发，普通 Run 可回报结果。Agent 可用已绑定的 Skill、Plugin 及获准 Runtime。 | 请求写明希望它解决的问题和返回位置。当前负责人接收答复或产物。 | 从请求定位本次答复或实际 Run。只有入队回执时显示排队，实际开工和结果按回报呈现。若只需答复，能在原讨论读到结论即可。[评论与派发](../research/05-source-evidence.md#指派评论协助与交接) |
| 成员委托现有 Agent 持续协调 | 普通 Agent 指派、Worker Run、子 Issue、Issue Wakeup 和原交付区可以承载分工及结果。 | 成员保留业务总责，在原 Issue 明确本项特有的授权及保留决定，需要单列总责人时可用成员属性。 | 接续时能辨认当前有效委托、原分工、已采用的版本及剩余问题。改派后的旧回报归原分工，由现任负责人判断能否复用。[Main Bot 的持续协调](01-unified-work-lifecycle.md#53-main-bot-怎样持续协调) |
| 本项完成条件要求具名验收 | 原交付区可按版本查看，原工作流可把待验收事项交给指定成员，PR 自动完成可按 Issue 关闭。 | 工作约定指定谁可接受、适用标准和收尾方式。 | 在原 Issue 将接受或退回关联到当次候选和标准。每个仍启用的成功完成入口都须核对有效决定。候选换版后，验收人可定位改动并决定当前版本。[完成条件](01-unified-work-lifecycle.md#62-状态推进与负责人交接) · [原生写入覆盖](../research/05-source-evidence.md#交付换版与验收写入) |
| 负责人委托 SOP 处理一段工作 | Issue 保留业务责任。受管 Agent 经原 Run 链派发，人工决定留在 Issue。 | 选定已发布的 SOP 版本、受托范围、输入和交还条件。 | 按 LoopForge 的依赖、检查和定向返工机制，记录本轮节点采用的输入和产物，出口回到委托它的 Issue。节点需要步骤驱动或受管脚本时才需对应宿主支持。[节点与交还](02-sop-workflow.md#3-一次-sop-如何运行) · [执行能力](execution-capabilities.md) |

接手只需一条署名结论时，原评论就能承载整份交付。结果由多个文件或修订组成时，接手者要能从同一处找到本次选交的组合。需要验收时，决定也要指向这一组合。[首期协作范围](overview.md#首期协作范围)

## 固定版本的底座盘点

对应 Multica 提交 [fdfbfcd](https://github.com/multica-ai/multica/tree/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc)。各项能力均以所引版本及入口为准。

| 能力 | 该版本的行为 | 产品需要的扩展 |
|---|---|---|
| Script 托管 | [Backend 工厂](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/agent.go#L502-L564)提供编码 Agent 协议；已有确定性命令实验使用 TeamAI 命令驱动，参见[实际覆盖](execution-capabilities.md)。在此版本中，将通用脚本作为 Multica Run 派发仍需适配 | 在现有 Run / Daemon 链中适配受管命令，复用 Runtime、工作目录、取消与结果通道。 |
| 本地 Credits 与请求去重 | 服务端 Task Usage 已支持 `credits_micros`；[Daemon 用量结构](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/types.go#L309-L322)尚无 Credits；[当前写入](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/task_usage.sql#L1-L20)按 task / provider / model 覆盖，尚缺请求 / Stage 身份和多源合并规则 | 补齐 Backend → Daemon → Usage 的计量身份、分指标合并与更正。Run 明细已有 Credits，[Issue 摘要与每日看板](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/task_usage.sql#L84-L165)仍需按原生单位汇总并展示覆盖。云端 `qoder_cloud` 支持与本地 Qoder 分开记录 |
| ContextReceipt | 原生准备与投递回执存在；恢复会话还会携带[回执列表之外的历史](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/context_receipt.go#L61-L77)。准备证据和每次模型调用的实际输入分别核验 | 沿原 Run 关联调用、材料版本及原生证据；保留换版前后记录，缺实际观察时标缺项 |
| 验收资产固定版本 | 普通 Skill 缓存缺失时可接受服务端新版，原生删除会清除版本历史，见[固定源码与原生实验](../research/topic-03b/native-assets.md#multica) | 验收 Rule / Script 固定不可变内容引用并核对实际摘要；退役保留获准的历史内容或不变引用 |
| 工作流重入与 SOP 前置 | [步骤守卫](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/issue_workflow_entry.go#L118-L123)仅比较步骤名。[派发与 child_done 研究](../research/topic-02/multica.md)已记录多入口、阶段关闭和业务结果的差异 | 在 Multica 既有写入 / 派发链落实本轮激活、前置条件和结果消费检查；区分同名步骤的不同进入轮次、子项取消与交付合格，以及当前结果与迟到结果 |
| Issue 指派与协调 | Multica 支持将 Issue 指派给成员、Agent 或 Squad。指派给 Squad 时由其 Leader 按小队名册委派工作。普通 Agent 有独立的派发入口。[指派分支](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/issue_trigger.go#L80-L96) · [小队协议](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/squad_briefing.go#L34-L63) | AgentPlatform 新 Issue 的指派对象为成员或 Agent。持续协调委托沿普通 Agent 入口执行。读取上游已有 Squad 指派或 Leader Run 时，按原记录解释责任、执行者及来源。 |
| 普通 Agent 回唤 | 同 Issue 可按具体 Worker Run 登记完成、失败与取消，登记时检查已终结的源 Run。原生回执支持合并，调度和领取复核相应权限。[订阅与过滤](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/docs/engineering/issue-wakeups.md#L99-L109) · [事务与入队](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/docs/engineering/issue-wakeups.md#L201-L235) | 按原委派找到实际 Run，恢复后核对当前授权、候选和已消费结果。跨 Issue 的条件、阻塞原因与业务决定各回到原记录确认。[回唤核查](../research/mainbot-lifecycle-and-progress.md#82-普通-agent-的原生回唤) |
| Run 谱系 | [AgentTaskQueue](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/generated/models.go#L124-L185)已有父执行、委托、重试、重跑及触发证据等关联 | 逐字段核对现有写入方、含义和读取方，再映射 SOP / 评价关系；业务含义不同的轮次保留最小附属关联 |


## 一致性与并发能力覆盖

[核心协作一致性与并发控制模型](core-consistency-concurrency.md)定义目标语义。下表区分固定版本已知行为与尚未取得充分证据的实现能力，不能把设计要求视为 Multica 已经实现。

| 一致性能力 | 当前可确认的依据 | 设计覆盖与待核实边界 |
|---|---|---|
| Issue / Project 条件写入 | 单项 Issue 更新支持可选的 `expected_revision`，在目标行写入时复核。看板移动委托到单项更新，批量操作逐项写，PR 自动推进有独立的条件写入。[已核对入口](../research/05-source-evidence.md#交付换版与验收写入) | 有版本验收约定时，各成功完成入口需核对当前候选、标准和有效决定。Project 及其他字段的具体并发策略仍按对应写入入口核对 |
| SOP 节点代际隔离 | 固定版本步骤守卫仅比较步骤名，见上文源码 | 尚不能仅靠原生步骤守卫隔离同名步骤重入；需要在派发与结果消费链补足激活身份和当前代际校验 |
| 派发幂等与重复投递 | 原生队列、领取和重试 / 重跑关系已存在 | 各入口重复提交、超时重发、并发领取是否统一返回原安排 / Run，需按 Agent 指派、评论、Workflow、手动及恢复入口分别核对 |
| Outbox / Inbox 与动作恢复 | Issue Wakeup 在源事务内记录匹配回执，派发与入队一起提交。重复通知可合并，已处理回执有保留期。[回执保留语义](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/docs/engineering/issue-wakeups.md#L363-L373) | 此结论限于已登记的回唤。委派、交付消费及其他跨层写入的恢复，要按各自的权威来源和操作身份核对 |
| Runtime 租约与旧执行隔离 | Daemon、Runtime 和 Run 具备领取、执行、取消及回报链路 | 租约过期、Daemon 失联、旧进程仍存活时的 fencing 和写入隔离覆盖尚未确认；停止请求不能替代实际终态 |
| Artifact / Candidate 版本引用 | 带附件的评论同事务发表，原交付区按附件 ID 定位历史上传，最新文件链接按文件名解析。原评论可更改附件集合，普通附件可被删除。[交付与换版源码](../research/05-source-evidence.md#交付换版与验收写入) | 在原 Issue 固定本次候选的附件 ID 或仓库修订，将检查、决定和后继取用关联到各自实际版本。验收与请求完成在写入时按[候选并发规则](core-consistency-concurrency.md#63-candidate-与验收竞争)核对 |
| 结果消费与迟到回执 | Run 谱系和 SOP 结果消费已有专题研究 | 迟到结果能否被可靠限制在原节点激活、旧候选或旧工作约定，需核对所有结果写入方 |
| Usage 更正与重复上报 | Task Usage 有原生写入和累计口径 | 多来源请求身份、重复事件去重、分指标更正和迟到快照的并发合并仍有明确扩展需求 |

本表中“尚未确认”表示缺少足以支持产品承诺的源码或现场证据，不等于断言上游一定不支持。后续研究须记录具体版本、入口、写入方、并发条件、实际回执和结果；只有核实后才能将状态改为已覆盖。
