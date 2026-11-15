# Multica 底座能力与扩展边界

协作工作以 Multica 的 Issue、负责人、项目工作流、Run、Runtime 与 Usage 为基础。此页说明哪些产品行为可以沿用现有实现，哪些要求依赖扩展。业务定义及适用场景见[架构总览](overview.md)。

## 原生入口与项目配置

| 需要的行为 | 可以直接使用的入口 | 项目配置或补充信息 |
|---|---|---|
| 邀请协助、变更负责人、按步骤交接 | 原 Issue 评论与提及、Assignee 选择器、Project Workflow 和交接预览 | 工作流可配置步骤处理人。需单列人工联系人时可用成员属性。正式接受引用指定成员、当次候选和标准。[指派与交接源码](../research/05-source-evidence.md) |
| 向团队交文件，查同一文件的旧稿 | Issue 评论与交付区按名称和类型归集附件版本，可打开具体上传 | 正式判断引用当时选中的附件或可核对的制品版本。同一最新链接可用于日常协作。[交付区源码](../research/05-source-evidence.md) |
| 准备项目依据和工具 | Issue 描述、父项、相关讨论、项目仓库与本地目录，Agent 已绑定的 Skill 与 Plugin | 有外部资料时按修订、位置与权限引用。团队维护可选能力。验收方法有固定版本要求时记录实际采用的内容。[资产与来源](03b-capability-governance.md) |
| 使用成员的本地工具 | 沿现有 Daemon、Runtime、Provider Backend、Session 和 Run 执行与回报 | 依实际宿主提供的身份、结果和用量显示覆盖。既有本地工作可按选定范围补交。[宿主能力矩阵](execution-capabilities.md) |

## 固定版本的底座盘点

对应 Multica 提交 [fdfbfcd](https://github.com/multica-ai/multica/tree/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc)。各项能力均以所引版本及入口为准。

| 能力 | 该版本的行为 | 产品需要的扩展 |
|---|---|---|
| Script 托管 | [Backend 工厂](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/agent.go#L502-L564)提供编码 Agent 协议；当前订单脚本实测走 TeamAI 命令驱动，见[能力矩阵](execution-capabilities.md)。任意确定性脚本经 Multica Run 执行尚缺对应承载 | 在现有 Run / Daemon 链中适配受管命令，复用 Runtime、工作目录、取消与结果通道。 |
| 本地 Credits 与请求去重 | 服务端 Task Usage 已支持 `credits_micros`；[Daemon 用量结构](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/types.go#L309-L322)尚无 Credits；[当前写入](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/task_usage.sql#L1-L20)按 task / provider / model 覆盖，尚缺请求 / Stage 身份和多源合并规则 | 补齐 Backend → Daemon → Usage 的计量身份、分指标合并与更正。Run 明细已有 Credits，[Issue 摘要与每日看板](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/task_usage.sql#L84-L165)仍需按原生单位汇总并展示覆盖。云端 `qoder_cloud` 支持与本地 Qoder 分开记录 |
| ContextReceipt | 原生准备与投递回执存在；恢复会话还会携带[回执列表之外的历史](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/context_receipt.go#L61-L77)。准备证据和每次模型调用的实际输入分别核验 | 沿原 Run 关联调用、材料版本及原生证据；保留换版前后记录，缺实际观察时标缺项 |
| 验收资产固定版本 | 普通 Skill 缓存缺失时可接受服务端新版，原生删除会清除版本历史，见[固定源码与原生实验](../research/topic-03b/native-assets.md#multica) | 验收 Rule / Script 固定不可变内容引用并核对实际摘要；退役保留获准的历史内容或不变引用 |
| 工作流重入与 SOP 前置 | [步骤守卫](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/issue_workflow_entry.go#L118-L123)仅比较步骤名。[派发与 child_done 研究](../research/topic-02/multica.md)已记录多入口、阶段关闭和业务结果的差异 | 在 Multica 既有写入 / 派发链落实本轮激活、前置条件和结果消费检查；验证 A→B→A、取消子项及旧候选晚到 |
| Run 谱系 | [AgentTaskQueue](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/generated/models.go#L124-L185)已有父执行、委托、重试、重跑及触发证据等关联 | 逐字段核对现有写入方、含义和读取方，再映射 SOP / 评价关系；业务含义不同的轮次保留最小附属关联 |
