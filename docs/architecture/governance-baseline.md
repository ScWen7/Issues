# Multica 底座能力与扩展边界

协作工作以 Multica 的 Issue、负责人、项目工作流、Run、Runtime 与 Usage 为基础。此页说明哪些产品行为可以沿用现有实现，哪些要求依赖扩展。业务定义及适用场景见[架构总览](overview.md)；跨层输入、授权、执行和结果交接的目标语义见[跨层业务契约与协作协议](cross-layer-contracts.md)。本页只记录固定版本底座的实际覆盖和扩展边界。

## 原生入口与项目配置

| 需要的行为 | 可以直接使用的入口 | 项目配置或补充信息 |
|---|---|---|
| 邀请协助、变更负责人、按步骤交接 | 原 Issue 评论与提及、Assignee 选择器、Project Workflow 和交接预览 | 工作流可配置步骤处理人。需单列人工联系人时可用成员属性。正式接受引用指定成员、当次候选和标准。[指派与交接源码](../research/05-source-evidence.md) |
| 按具体版本交付和接手 | 在 Issue 评论上传文件，交付区按名称和类型归集版本，按附件 ID 打开具体上传。Issue 描述中的附件归为输入资料 | 在所选版本旁呈现工程基准、已交检查及来源、提交者说明的待补内容。有可核对的生产 Run 时提供原记录入口。换版后，原检查仍指向当时的附件。[交付区源码](../research/05-source-evidence.md#做决定看结果与处理异常) · [接手操作](05-unified-workbench.md) |
| 准备项目依据和工具 | Issue 描述、父项、相关讨论、项目仓库与本地目录，Agent 已绑定的 Skill 与 Plugin | 有外部资料时按修订、位置与权限引用。团队维护可选能力。验收方法有固定版本要求时记录实际采用的内容。[资产与来源](03b-capability-governance.md) |
| 使用成员的本地工具 | 沿现有 Daemon、Runtime、Provider Backend、Session 和 Run 执行与回报 | 依实际宿主提供的身份、结果和用量显示覆盖。既有本地工作可按选定范围补交。[宿主能力矩阵](execution-capabilities.md) |

## 固定版本的底座盘点

对应 Multica 提交 [fdfbfcd](https://github.com/multica-ai/multica/tree/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc)。各项能力均以所引版本及入口为准。

| 能力 | 该版本的行为 | 产品需要的扩展 |
|---|---|---|
| Script 托管 | [Backend 工厂](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/agent.go#L502-L564)提供编码 Agent 协议；已有确定性命令实验使用 TeamAI 命令驱动，参见[实际覆盖](execution-capabilities.md)。在此版本中，将通用脚本作为 Multica Run 派发仍需适配 | 在现有 Run / Daemon 链中适配受管命令，复用 Runtime、工作目录、取消与结果通道。 |
| 本地 Credits 与请求去重 | 服务端 Task Usage 已支持 `credits_micros`；[Daemon 用量结构](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/types.go#L309-L322)尚无 Credits；[当前写入](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/task_usage.sql#L1-L20)按 task / provider / model 覆盖，尚缺请求 / Stage 身份和多源合并规则 | 补齐 Backend → Daemon → Usage 的计量身份、分指标合并与更正。Run 明细已有 Credits，[Issue 摘要与每日看板](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/task_usage.sql#L84-L165)仍需按原生单位汇总并展示覆盖。云端 `qoder_cloud` 支持与本地 Qoder 分开记录 |
| ContextReceipt | 原生准备与投递回执存在；恢复会话还会携带[回执列表之外的历史](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/context_receipt.go#L61-L77)。准备证据和每次模型调用的实际输入分别核验 | 沿原 Run 关联调用、材料版本及原生证据；保留换版前后记录，缺实际观察时标缺项 |
| 验收资产固定版本 | 普通 Skill 缓存缺失时可接受服务端新版，原生删除会清除版本历史，见[固定源码与原生实验](../research/topic-03b/native-assets.md#multica) | 验收 Rule / Script 固定不可变内容引用并核对实际摘要；退役保留获准的历史内容或不变引用 |
| 工作流重入与 SOP 前置 | [步骤守卫](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/issue_workflow_entry.go#L118-L123)仅比较步骤名。[派发与 child_done 研究](../research/topic-02/multica.md)已记录多入口、阶段关闭和业务结果的差异 | 在 Multica 既有写入 / 派发链落实本轮激活、前置条件和结果消费检查；区分同名步骤的不同进入轮次、子项取消与交付合格，以及当前结果与迟到结果 |
| Run 谱系 | [AgentTaskQueue](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/generated/models.go#L124-L185)已有父执行、委托、重试、重跑及触发证据等关联 | 逐字段核对现有写入方、含义和读取方，再映射 SOP / 评价关系；业务含义不同的轮次保留最小附属关联 |


## 一致性与并发能力覆盖

[核心协作一致性与并发控制模型](core-consistency-concurrency.md)定义目标语义。下表区分固定版本已知行为与尚未取得充分证据的实现能力，不能把设计要求视为 Multica 已经实现。

| 一致性能力 | 当前可确认的依据 | 设计覆盖与待核实边界 |
|---|---|---|
| Issue / Project 条件写入 | 已有原生 Issue、指派和 Project Workflow 写入入口 | 尚未完成所有关键字段并发写入的原子条件、版本冲突和覆盖策略核查；不能假设所有入口已具备统一乐观并发控制 |
| SOP 节点代际隔离 | 固定版本步骤守卫仅比较步骤名，见上文源码 | 尚不能仅靠原生步骤守卫隔离同名步骤重入；需要在派发与结果消费链补足激活身份和当前代际校验 |
| 派发幂等与重复投递 | 原生队列、领取和重试 / 重跑关系已存在 | 各入口重复提交、超时重发、并发领取是否统一返回原安排 / Run，需按 Leader、评论、Workflow、手动及恢复入口分别核对 |
| Outbox / Inbox 与动作恢复 | 当前设计要求状态变化后的下游动作可恢复 | 固定版本是否具备等价持久化待办、接收去重、投递回执和重建能力尚未确认；不得宣称 Exactly-once |
| Runtime 租约与旧执行隔离 | Daemon、Runtime 和 Run 具备领取、执行、取消及回报链路 | 租约过期、Daemon 失联、旧进程仍存活时的 fencing 和写入隔离覆盖尚未确认；停止请求不能替代实际终态 |
| Artifact / Candidate 版本引用 | 评论附件可按附件 ID 打开具体版本 | 已知可固定附件引用；Candidate 组合、标准版本、接受与换版竞争的原子性仍需设计映射 |
| 结果消费与迟到回执 | Run 谱系和 SOP 结果消费已有专题研究 | 迟到结果能否被可靠限制在原节点激活、旧候选或旧工作约定，需核对所有结果写入方 |
| Usage 更正与重复上报 | Task Usage 有原生写入和累计口径 | 多来源请求身份、重复事件去重、分指标更正和迟到快照的并发合并仍有明确扩展需求 |

本表中“尚未确认”表示缺少足以支持产品承诺的源码或现场证据，不等于断言上游一定不支持。后续研究须记录具体版本、入口、写入方、并发条件、实际回执和结果；只有核实后才能将状态改为已覆盖。
