# AgentPlatform · 整体架构一致性审查

> 审查对象：当前架构设计分支中的产品总览、核心对象、生命周期、跨层契约、五层职责、模块边界及 D5 / D6 / D7 专题。
> 审查目的：确认局部专题能否组成一套事实归属一致、职责闭合、可沿现有 Multica 执行链落地的协作平台架构。
> 本文记录审查后的统一架构关系和仍需后续处理的边界，不记录方案讨论过程，也不替代各架构正文。

## 1. 总体结论

当前架构可以收敛为一个完整系统，不需要新增第二套 Issue、Task、Run、Runtime、Coordinator 或通用工作流控制平面。

产品主线是：

**成员围绕 Project / Issue 协作；当前负责人可以亲自推进或委托 Main Bot；Main Bot 在授权内组织 Worker、子 Issue 和 SOP；实际受管执行沿 Multica Run / Runtime；成果形成固定 Candidate 并由接收方核验和决定；真实工作证据进入评价与改进；审核发布的方法由项目决定是否采用，后续生产工作验证效果。**

五层职责和逻辑模块不是两套架构：
- 五层描述系统持续承担的职责；
- A–G 是业务领域模块，H 是横向工作台，I 是来源与宿主适配；
- 中心可以合并部署模块，成员 Runtime 仍在本地；
- 每个事实只由其权威对象或有权主体维护。

正式架构入口见[整体系统架构与模块边界](../architecture/system-architecture.md)。

## 2. 五层职责与模块边界一致

| 职责层 | 对应模块 | 权威事实 | 主要交接 |
|---|---|---|---|
| 工作协作 | A 组织与项目范围、B 工作协作核心 | Project 配置、Project Adoption、Issue、Work Agreement、Decision、负责人和完成状态 | 目标、责任、授权、业务决定 |
| 能力与上下文 | C 方法与上下文、I 来源与宿主适配 | 资产定义与 Release、来源修订、适用范围、实际选择与投递 | 获准的方法、资料和执行输入 |
| 流程编排 | D 流程编排 | SOP Definition、SOP Execution、Node Activation、Node Attempt | 节点就绪、输入候选、结果消费和出口 |
| 执行与回报 | E 执行集成、Multica、I 宿主适配 | 原生 Task / Run、Runtime、Session、Observation、原始 Usage | 实际执行、宿主回执、来源与用量 |
| 度量、评价与改进 | F 交付与证据、G 度量评价与改进 | Artifact、Candidate、Evidence、Delivery Record、Evaluation、Finding、Proposal、Benchmark、效果观察 | 交付消费、评价证据、候选验证结果和改进建议 |

H 工作台读取以上事实并调用相应权威入口，不拥有业务决定权。A 记录 Project Adoption；C 由资产维护者发布不可变 Release；G 提供 Evaluation、Finding、Proposal 和 Benchmark 证据，不直接发布资产或替项目采用。

## 3. 核心对象的事实归属闭合

| 对象 / 事实 | 权威来源 | 不可替代的相邻事实 |
|---|---|---|
| Issue 工作与责任 | Issue、Project Workflow、有效 Work Agreement / Decision | Main Bot Session、SOP 状态和 Run 不能替代 Issue 责任 |
| Main Bot 持续协调 | Issue 当前指派与有效授权代际 | Agent 身份或旧 Session 本身不构成持续授权 |
| 一次性 Worker 委派 | 原 Comment + 目标 Agent 的委派关系 | 评论已保存、Wakeup 已触发不代表 Worker 已接单 |
| SOP 流程 | SOP Execution、Node Activation、Node Attempt | 节点状态不是 Run 状态；SOP 完成不自动完成 Issue |
| 实际执行 | Multica Task / Run 和真实 Runtime 回执 | Claim 不等于 Start；Session 不等于 Run |
| Artifact / Candidate | 具体来源版本和固定送审清单 | 文件 latest 链接、文件名分组不等于 Candidate |
| Evidence / Acceptance Decision | 具体检查对象与标准；Issue 有权主体决定 | Evaluation、PR merge、Run success 不能替代业务验收 |
| Evaluation / Finding | 独立评价器、固定输入和来源证据 | 评价失败不等于生产失败；评分通过不自动验收 |
| Improvement Proposal / Benchmark | 源 Finding、变更基线、候选修订和固定实验定义 | 改进候选修订不是 D6 交付 Candidate |
| Release | 资产维护者发布的不可变资产版本 | Release 不等于 Project Adoption |
| Project Adoption | 项目有权成员作出的项目配置决定 | Adoption 不等于某项工作已实际选择、投递或使用 |
| Usage | 实际生产或治理 Run 的原生计量事实 | 未上报用量保持 unknown，不以估算冒充真实值 |

Project Adoption 是 Project 配置中的决定记录，不是新建一套资产管理系统。改进候选修订属于 Improvement Proposal 的固定内容，不是跨领域通用 Candidate 对象。

## 4. D5、D6、D7 已连接成一条业务闭环

### 4.1 D5：工作可靠派发、执行和接续

- Issue 首次激活、Comment 目标级委派和 SOP Node Attempt 使用各自的业务来源身份。
- 来源与 Multica Task 的绑定可查回；无法证明时保持 Unknown 并对账。
- Multica 原生 Task / Run、Claim、Start、Retry、Rerun 和 Wakeup 按其原生语义使用。
- Run 终态后由原业务接收方消费，不能因通知丢失重跑生产。

权威设计：[跨层派发、执行绑定与结果消费契约](../architecture/d5-cross-layer-recovery-contract.md)。

### 4.2 D6：成果形成可核验的 Candidate

- Artifact 是具体来源版本；Candidate 是固定送审组合。
- Evidence 绑定 Candidate、要求和标准版本。
- Acceptance Decision 由有权主体对具体 Candidate 和范围作出。
- 部分接受、例外放行、候选换版和 Issue 完成遵循同一并发条件。
- PR merge 是工程事实，不自动成为业务验收。

权威设计：[候选交付与验收契约](../architecture/d6-delivery-acceptance-contract.md)。

### 4.3 D7：从真实工作形成持续改进

- L1 当前工作自修正，不必创建改进提案。
- L2 对具体 Run / Candidate / 流程进行独立评价。
- L3 对具有跨工作价值的问题形成 Improvement Proposal，固定改进候选修订、基线和适用范围。
- Benchmark 在固定样本、标准、评价器、环境和计量覆盖下验证候选。
- 资产维护者发布 Release；项目有权成员另行决定 Project Adoption。
- 后续工作记录实际选择、投递和使用，再从真实生产结果观察质量、返工、人工介入和可知成本。
- 退化时可以暂停扩大采用或回退项目默认，历史 Run、Evidence、Decision、Release 和 Adoption 记录不被覆盖。

权威设计：[持续改进内循环契约](../architecture/d7-continuous-improvement-loop.md)。

## 5. 端到端的闭环关系

~~~mermaid
flowchart TB
  Work["Project / Issue / Project Adoption · 目标、责任、授权"]
  Method["资产定义与 Release"]
  Context["本项实际选择与获准上下文"]
  Coordination["成员或 Main Bot · 动态组织"]
  SOP["按需委托 SOP"]
  Run["Multica · Task / Run / Runtime"]
  Artifact["Artifact · 实际产物"]
  Candidate["Candidate · 固定送审组合"]
  Evidence["Evidence · 检查事实"]
  Decision["Acceptance Decision · 业务验收"]
  Evaluation["Evaluation / Finding"]
  Proposal["Improvement Proposal · 改进候选修订"]
  Benchmark["Benchmark · 固定样本对照"]
  Release["资产维护者发布 Release"]
  Adoption["项目有权成员作出 Project Adoption"]
  Usage["后续工作实际选择、投递与使用"]
  Outcome["真实质量、返工、人工介入与原生用量"]

  Work --> Coordination
  Method --> Context
  Context --> Coordination
  Coordination --> SOP
  Coordination --> Run
  SOP --> Run
  Run --> Artifact
  Artifact --> Candidate
  Candidate --> Evidence
  Evidence --> Decision
  Decision --> Work
  Candidate --> Evaluation
  Run --> Evaluation
  Evaluation --> Finding["Finding"]
  Finding --> Proposal
  Proposal --> Benchmark
  Benchmark --> Release
  Benchmark -->|项目流程 / 分工配置候选| Adoption
  Release --> Adoption
  Adoption --> Usage
  Usage --> Outcome
  Outcome --> Evaluation
~~~

该图是职责和事实关系，不代表每项 Issue 都必须经过 SOP、Evaluation 或 Benchmark。简单工作可以在交付和业务决定后结束；只有显式质量门、抽样策略或维护者复盘才触发评价；只有具备跨工作价值的发现才进入 L3。

## 6. 一致性审查后的统一边界

1. **一个业务协作核心**：Issue 是工作归属，Main Bot 是 Issue 上的受托协调角色，不另建全局协调层。
2. **一个受管执行控制面**：沿用 Multica Task / Run / Runtime / Daemon；SOP、Evaluation 和 Benchmark 复用该执行链。
3. **一个交付验收模型**：Artifact、Candidate、Evidence、Delivery Record 和 Acceptance Decision 各自表达不同事实。
4. **一条改进治理链**：Evaluation / Finding → Proposal → Benchmark → Release → Project Adoption → 实际 Usage → 效果观察。
5. **权限与版本贯穿全链**：来源读取、执行授权、结果消费、发布和采用均由各自有权主体决定；旧版本和迟到结果不得越代推进。
6. **工作台只呈现与路由**：不复制业务状态、不直接写其他模块底层存储、不在 UI 中重实现业务规则。
7. **资料能力独立可选**：团队 Wiki、项目资料、代码 Wiki 作为来源与上下文扩展，不成为协作主线的必经基础设施。

## 7. 尚未收敛但不阻碍整体架构的事项

| 后续专题 | 尚需解决的问题 | 为什么不阻碍当前整体架构 |
|---|---|---|
| D11 评价触发与资源预算 | 运行后的抽样比例、预算额度和停止阈值需按真实数据校准 | 已定义必需门禁、风险触发、分层抽样、预算层级、重试幂等和防递归；剩余是运行校准，不是架构缺口 |
| D5 工程实现 | 稳定派发身份、Task 查回、结果消费和故障注入 | D5 已明确业务身份、责任和恢复契约；剩余是底座扩展和工程验证 |
| D6 工程实现 | Candidate manifest、不可变 Artifact 可取性、验收与 PR 自动完成竞争 | D6 已明确产品对象、版本和决定语义；剩余是技术承载与并发验证 |
| 多来源成本采集 | 宿主请求身份、Credits / Token 覆盖、迟到更正 | 已明确真实来源与 unknown 原则；适配覆盖可逐宿主演进 |
| 部署与运行形态 | 哪些模块合并部署、存储和扩展边界 | 逻辑职责和权威事实已明确，可在技术方案阶段按负载与维护成本决定 |

## 8. 架构审查结论

当前架构的核心对象、权威事实、生命周期、模块依赖和跨层业务链可以互相解释，D5 / D6 / D7 已经组成从工作发起到持续改进的闭环，D11 已补齐评价触发和资源治理规则。当前没有需要通过增加新领域对象或第二套控制平面才能解决的结构性断点。

下一阶段应从“继续增加架构概念”转向“技术方案准备与实现前置验证”：优先收敛 D5 派发绑定、D6 Candidate / Decision 的权威写入边界，并按 D11 已定义的评价策略选择最小纵向切片。D11 的抽样比例和预算数值由后续真实运行校准，不再扩展新的架构概念。部署、数据库和 API 设计应在这些契约约束下分别展开。
