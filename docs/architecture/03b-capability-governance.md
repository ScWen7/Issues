# 专题三 B：TeamAI 团队能力与知识治理融合

版本：V1.0 · Multica 基座治理修订 · 2026-11-15

本专题吸收 TeamAI 的资源组织、作用域、版本、检索、分发、Skill Driver 和 AgentObservation 机制，并融合进 Multica 已有 Agent / Skill / Plugin / Context / Run / Runtime 体系。

本专题不建设第二套 Agent 注册、Skill 执行、上下文投递或 Run 管理系统。治理规则见[架构治理基线](governance-baseline.md)。

既有 TeamAI / Multica / LoopForge 源码研究和订单实验保留为证据：[3B 源码与订单实验](../research/03b-source-evidence.md) · [跨宿主工具与接续](../research/topic-03b/cross-host-handoff.md) · [项目知识](../research/topic-03b/project-knowledge.md)。

## 1. 能力治理的目标

让团队能持续回答：

- 某项 Agent 能力由谁维护，适用于哪个团队、项目和工作类型？
- 当前有哪些可用 Role、Skill、Rule、Playbook、MCP 工具和 Knowledge？
- 一次工作为什么选择这些资产，实际投递了哪个版本？
- 宿主是否收到、发现、加载或调用了这些资产？
- 资产修订、撤回或权限变化后，哪些新工作受影响？
- 真实执行中的问题如何反馈成可审核的资产改进？

这些问题属于能力与知识治理；Issue 和 Run 的事实仍来自 Multica。

## 2. 复用 Multica 的资产和执行基础设施

| 能力 | Multica 已有基础 | TeamAI 增量融合 |
|---|---|---|
| Agent | Agent 定义、Provider、模型、运行配置、Agent 选择 | Role 组合、团队规范、职责与输出契约 |
| Skill | Skill 发现、准备、分发和宿主加载通道 | 团队 / 项目作用域、版本治理、来源和适用条件 |
| Plugin / MCP | 插件与工具配置、连接和工具调用 | 项目可信来源、允许范围、工具来源核验和授权策略 |
| Context | Agent brief、项目说明、上下文准备、ContextReceipt | Knowledge 检索、章节引用、选择理由、材料预算与实际使用证据 |
| Run / Session | Multica 执行和宿主会话 | Skill Driver 以现有执行单元推进步骤，不创建第二套 Run |
| Trace / Result | 宿主消息、工具活动、终态和结果 | AgentObservation 补充来源、请求身份、共享范围和覆盖缺口 |

只有 Multica 的现有资产结构无法表达的治理信息，才以最小元数据或扩展方式补充。

## 3. 资产分类与边界

- **Role**：说明承担者的职责、目标、权限边界和交付要求。优先作为 Multica Agent 配置的治理视图或组合模板，不创建第二种 Agent 执行实体。
- **Skill**：可被宿主发现和调用的专业能力。沿用 Multica 已有 Skill 机制，补充发布者、作用域、版本、来源和适用条件。
- **Rule / Principles**：团队或项目必须遵守的约束。需声明适用范围、强制级别、冲突处理和实际投递通道。
- **Playbook**：指导 Agent 如何分析和推进某类工作的可选方法，不是固定 SOP，也不拥有派发权。
- **MCP / Tool**：实际可调用的外部能力。目录可见、连接成功、工具被发现、调用发起、服务执行和结果返回是不同事实。
- **Knowledge**：具有来源、适用范围、版本和有效性的可检索知识。知识不能替代 Issue 当前工作决定。
- **SOP**：属于专题二，资产治理负责其发布和版本，运行承载仍由 Multica Issue / Run。
- **Script**：固定版本的受管命令资产，运行仍沿用 Multica Script / Run 执行能力。

## 4. 发布、版本和作用域

资产治理按以下规则组织：

1. 每份资产有明确所有者、类型、来源、适用范围、版本、内容摘要和发布状态。
2. 作用域至少区分团队、项目和个人；更窄范围的资产不能静默覆盖更高层强制规则。
3. 发布版本不可变。修订形成新版本，明确替代关系和兼容条件。
4. 项目覆盖必须明确声明覆盖哪个团队默认；同名资产不能仅凭名称推断来源或优先级。
5. 资产撤回或权限变化时，阻止后续新投递；在途执行依据其固定版本和已发生的副作用决定是否暂停或换版。
6. 已发布版本的历史引用保留；历史可追溯不代表当前仍有权读取原文。
7. 同一内容的重复发布应幂等；同一版本标识出现不同内容必须报冲突，不静默覆盖。

## 5. 一次工作如何选择和投递能力

资产选择应围绕 Multica 当前 Issue / Run 的实际工作范围：

1. 从 Issue 取得目标、当前决定、项目和责任角色。
2. 读取已发布 SOP / Playbook 或节点要求；确定必需与可选材料。
3. 在成员有权访问的资产范围内检索候选，应用团队底线、项目覆盖和角色适用条件。
4. 记录选中版本、来源、摘要、选择理由及省略原因。
5. 将选定材料交给 Multica 现有 Context / Skill / Plugin 投递路径。
6. 通过 ContextReceipt 和宿主原生证据核对：已准备、已写入、可发现、实际进入当前输入、被调用，不能混为一个“已加载”状态。
7. 资产撤权、修订或投递失败时，按缺项和影响范围阻止相关工作，不以同名个人资产或旧缓存静默替代。

资产治理不自行创建 Run。每次实际宿主调用和加载证据应关联 Multica 的原生 Run / Session / Turn / Request。

## 6. Skill Driver 与 Multica Run 的关系

TeamAI Skill Driver 的价值是让当前 Agent 按约定领取、确认、执行和回报工作步骤。融合时：

- Driver 作为 Multica Run / Session 内的步骤协议或宿主工具能力运行。
- next / ack / report 等步骤状态只表达 Driver 对步骤交接的记录，不另建平台 Run 或成员工作状态。
- 子代理由宿主原生机制或 Multica 已有 Agent 协作能力承载。
- Driver 不自行分配 Runtime、不绕过 Multica 权限，也不直接完成 Issue。
- Driver 回报关联原 Run、Issue、SOP 节点和资产版本；重复回报按稳定步骤身份幂等处理。
- 如果某宿主无法在当前会话或子代理中承载 Driver，应记录能力缺失并选择已支持路径，不伪造支持能力。

## 7. AgentObservation 与执行事实

AgentObservation 是对已有执行事实的增强视图，不是第二套执行账本。

建议记录或引用：
- 来源：Multica Backend、Hook、OTel、转录、文件观察或成员自述；
- 原生身份：Session、Thread、Turn、Request、Message、Tool Call、API Call；
- Multica 身份：Run、Runtime、成员、Issue；
- 发生与接收时间、采集范围、共享授权和数据摘要；
- 事件类型：Prompt、Assistant、Tool、Result、Usage、Context、Stop 等；
- 可信等级：宿主原生记录、平台确认、采集器推断或成员自述；
- 缺失和覆盖边界。

同一事件被多个观察源捕获时保留多份 Observation，但映射到同一原生事件和计量单元。无法证明归属时保留为未归属观察，不自动挂到最近的 Run。

## 8. 工具来源与跨宿主授权

项目工具必须能证明来源，不以名称相同或参数相同作为可信依据。

- 发布时固定工具来源、服务身份、接口契约、适用范围和版本摘要。
- 投递时复核成员、Issue、Run、项目权限及工具授权。
- 宿主侧核对实际发现的服务与工具；调用时核对原生调用身份和当前授权。
- 服务回执、模型收到的结果和节点消费的报告分别留证。
- 权限撤销后拒绝新的调用；在途调用按 Multica 原有取消和副作用核对机制处理。
- 接替成员使用自己的 Runtime、凭证和新 Run；不继承前成员的私有会话或凭证。

## 9. 知识来源与有效性

知识管理补足 TeamAI 的知识机制，但不建立第二套项目事实系统：

- 权威产品 / 项目文档仍由其原系统维护；平台登记来源、修订、章节或块身份和摘要。
- 检索结果必须携带来源、版本、适用范围和权限。
- 选入宿主的材料与 Issue 当前决定分别管理；知识不能覆盖当前 Decision。
- 来源更新后识别受影响的新投递和历史使用，不静默替换在途版本。
- 来源失效、撤回或权限变化时停止新投递，并显示缺项；已发布的脱敏 / 派生知识需遵守来源授权。
- 从执行中提炼的经验先成为候选，审核通过后才发布为正式知识或能力资产。

## 10. 与其他专题的交接

- 专题一提供 Issue、责任、工作约定和 Decision。
- 专题二提供 SOP 版本、节点要求、输入输出契约和门禁。
- 专题三 A 提供 Multica 实际投递、宿主调用、ContextReceipt、Trace 和 Result。
- 专题四提供 Evaluation、Findings、改进建议和 Benchmark 效果证据。
- 专题五提供资产选择、来源、加载状态、权限和改进入口的产品呈现。

## 11. 验收标准

1. Role / Skill / Rule / Playbook / Knowledge 能声明所有者、作用域、版本、来源和适用条件。
2. 资产选择能追溯到 Multica Issue / Run，不创建第二套工作对象。
3. 实际投递沿 Multica Context / Skill / Plugin 路径，能够区分准备、写入、发现、加载和调用。
4. 同名个人工具不能冒充项目发布工具；撤权后不能继续新调用。
5. Skill Driver 使用既有 Run / Session，步骤回报可幂等，不建立第二套 Run。
6. 多源 AgentObservation 不重复创建执行或计量事实。
7. 知识修订和撤回能识别受影响的投递，历史证据保留来源和授权边界。
