# D6 · 候选交付与验收契约

> 本文定义 AgentPlatform 中交付如何形成可验收的 Candidate，以及 Evidence、Acceptance Decision、Issue 完成和 PR 工程事实如何协同。
> 对象归属见[核心对象模型](core-object-model.md)；状态见[统一生命周期、状态机与事件模型](lifecycle-state-event-model.md)；并发与恢复见[核心协作一致性与并发控制模型](core-consistency-concurrency.md)。
> Multica 现有交付能力及缺口见[D6 源码取证](../research/d6-delivery-acceptance-evidence.md)。
> 本文是产品级契约，不定义数据库表、API 或部署结构。

## 1. 核心判断

**交付区负责找文件；Candidate 负责固定本次送审组合；Evidence 负责证明；Decision 负责接受；Issue 负责业务完成。**

不能把这些概念折叠成一个“最新交付”或一个“任务成功”状态。

| 对象 | 回答的问题 | 权威事实 |
|---|---|---|
| Artifact | 具体产物是什么、来自哪里、哪个版本？ | 不可变来源版本、生产者、位置 / 摘要 |
| Candidate | 本次究竟把哪些产物作为一个整体送审？ | 固定的 Artifact 版本清单及适用工作约定 |
| Evidence | 哪项要求得到什么事实支持？ | 对具体 Candidate / Artifact / 标准版本的检查记录 |
| Evaluation | 给定证据后，评价器如何判断质量或风险？ | 评价器版本、输入证据、结论与局限 |
| Acceptance Decision | 有权主体接受、部分接受、退回或例外放行什么？ | 决定者、Candidate、标准、范围、理由 |
| Delivery Record | 这次交付和接收过程发生了什么？ | Candidate、Evidence、缺项、决定及交接的汇总 |

Artifact 的上传、Run 成功、PR 合并、Evaluation 通过和 Candidate 被接受，是不同事实。任何一项都不能自动替代其他项。

## 2. Candidate 如何形成

### 2.1 Artifact 先产生，Candidate 由明确提交形成

Run、成员或外部系统可以独立产生 Artifact。多个 Worker 可以并行提交成果；子 Issue 可以有自己的交付。它们都只是可引用的产物，不自动成为父 Issue 当前候选。

当工作约定要求正式送审时，由当前 Issue 负责人、获授权的 Main Bot 或被明确指定的交付整合者选择本次范围，形成 Candidate。选择必须明确，不按文件名、上传时间、Run 完成顺序或“最新链接”自动拼装。

Candidate 可以包含：
- 一个或多个文件附件的固定版本；
- 一个或多个仓库 commit / PR head / patch；
- 构建包、测试报告、截图、部署记录等其他 Artifact；
- 来自多个 Worker 或子 Issue 的成果；
- 必需的来源说明、变更摘要和已知缺项。

每个 Artifact 保留原生产者和来源归属；Candidate 的整合者对“为什么这些产物组成这次送审组合”负责，但不因此成为所有产物的生产者。

### 2.2 Candidate 固定清单

Candidate 创建时固定：
1. 所属 Issue 和交付目的；
2. 适用 Work Agreement / 完成要求版本；
3. Artifact 清单及每项的具体来源版本；
4. 每项 Artifact 的生产者、来源 Run / Member / 子 Issue；
5. 内容定位依据（附件 ID + 内容摘要 / 不可变对象版本；仓库 commit SHA；PR head SHA；其他可回读版本）；
6. 本次送审范围、变更摘要和已知缺项；
7. 本次适用的检查要求 / 验收标准版本。

Candidate 清单一经提交不可原地改组成。新增、删除或替换 Artifact，只要改变本次送审内容，就形成新 Candidate。仅补充解释性说明且不改变送审内容时，可追加到 Delivery Record，不得暗中改变 Candidate manifest。

### 2.3 文件最新版本不等于 Candidate 最新版本

Multica 交付区按规范化文件名和内容类型归组，展示同一文件的上传历史；文件名链接可能解析到最新上传。该能力适合浏览，不足以标识 Candidate。

因此：
- Candidate 必须引用附件 ID 和内容摘要 / 不可变版本，不引用文件名 latest URL 作为唯一身份。
- 同名文件的新上传不会自动替换历史 Candidate 中的附件。
- 普通附件被删除、权限撤回或源仓库不可访问时，Candidate 仍保留原引用与来源事实，但其可取得性标为 Missing / Unavailable，不能静默换成新版本。
- 如果必须保证长期审计和复核，应由交付域采用不可变对象版本或受控快照；仅有附件 ID 不等于字节永久保留。

## 3. Candidate 生命周期与换版

Candidate 生命周期沿用统一状态模型：
- **Submitted**：固定清单已提交，成为当前待处理候选；
- **Under Review**：按本次适用标准检查；
- **Partially Accepted**：明确范围已被接受，仍有必需范围待完成或决定；
- **Accepted**：本候选要求范围已满足，且有效决定覆盖全部必需验收范围；
- **Rejected**：存在未满足项，需要修正或重新提交；
- **Superseded**：被新 Candidate 替代，不再作为当前验收对象；
- **Withdrawn**：提交者或有权主体撤回，保留原因与历史检查。

同一 Issue 可以保留多份历史 Candidate；同一交付目的 / 验收通道在同一时点只能有一个当前 Submitted / Under Review Candidate。新 Candidate 替代旧候选时，旧候选转为 Superseded，历史 Evidence 和 Decision 仍归属旧候选。

换版不等于覆盖：
- 生产者继续上传新文件，只新增 Artifact；
- 有权整合者明确选定新组合，才形成新 Candidate；
- 新 Candidate 不继承旧 Candidate 的 Accepted 状态；
- 旧 Evidence 只有在检查对象和影响范围证明未受变化影响时，才可被新 Candidate 显式引用复用，并记录复用理由；不能把旧 Evidence 的目标版本改成新 Candidate。

## 4. Evidence 与检查结果

### 4.1 Evidence 是事实记录

Evidence 必须说明它支持什么判断，至少引用：
- Candidate ID 或具体 Artifact 版本；
- 被验证的要求 / 验收条目；
- 适用标准版本；
- 执行主体和身份；
- 检查方法、环境、工具 / 版本、输入及时间（适用时）；
- 原始报告、日志、测试结果或可回读来源；
- 结论：通过、不通过、未验证或有理由的不适用；
- 覆盖范围与局限。

Evidence 可以由成员、Worker、受管测试、独立 Reviewer 或外部系统产生。来源强度必须如实标明：成员自述不是宿主回执，宿主回执不是独立测试，Evaluation 不是原始证据，验收决定也不是测试证据。

### 4.2 一个 Candidate 可以逐步补充 Evidence

同一 Candidate 的 Evidence 可以增量补充，但每份记录不可改写其检查对象、标准版本和原始结论。报告迟到时仍归属原 Candidate。

标准变化后：
- 旧 Evidence 保留原标准版本；
- 若新标准与旧标准实质等价，接收方可显式声明复用；
- 若标准新增要求、环境变化或范围扩大，缺少的部分必须重新检查；
- 不能只因旧报告标记 Passed 就推断新标准也通过。

### 4.3 Evaluation 不替代验收

Evaluation 可以对 Run、Candidate、流程或资产进行质量、风险和趋势判断。它必须固定评价器版本与输入证据。Evaluation 通过只提供参考或满足某个明确门禁，不自动接受 Candidate；只有工作约定明确授权自动验收，并且评价器和证据满足该约定时，才可作为决策依据之一，仍需生成可追溯的 Acceptance Decision。

## 5. Acceptance Decision

### 5.1 决定必须固定对象和权限

Acceptance Decision 至少固定：
- 决定者及其在该 Issue 上的验收权限；
- Candidate ID；
- 适用 Work Agreement / 标准版本；
- 决定结果及范围；
- 支持决定的 Evidence；
- 缺项、限制、例外理由和后续责任；
- 决定时间及其是否被后续决定取代。

决定是不可变历史事实。撤销或纠正旧决定必须追加新的决定，说明被替代的决定及原因，不能直接改写历史。

### 5.2 四类决定结果

| 决定 | 含义 | 对 Candidate / Issue 的影响 |
|---|---|---|
| Accept | 全部必需范围符合当前标准 | Candidate 可 Accepted；Issue 仍需检查其他完成条件 |
| Partial Accept | 指定部分 / 用途符合标准，其他部分仍未接受 | Candidate 为 Partially Accepted；明确剩余范围、负责人和后续动作 |
| Reject / Request Changes | 指定要求未满足或证据不足 | Candidate 为 Rejected；按工作约定修正或重新提交 |
| Exception Accept | 有权主体对明确要求作范围受限的例外放行 | 仅对声明范围和用途生效；记录豁免要求、风险、理由、批准权限与期限 / 条件 |

Exception Accept 不得伪装成 Evidence 通过，也不能默认豁免安全、合规或其他不可豁免的强制要求。若没有被授权的例外机制，必须拒绝例外请求并交回有权主体。

### 5.3 部分接受不是整体完成

部分接受必须指出：
- 已接受的交付部分 / 使用范围；
- 尚未接受的部分和缺失证据；
- 剩余责任人和下一步；
- 是否允许已接受部分被其他工作引用；
- 是否影响 Issue 的整体完成条件。

只有工作约定明确允许按部分范围完成，且所有必需范围均已接受或有效例外处理，Issue 才能完成。否则 Issue 保持进行中 / 审查中，不能因某个子项或部分产物被接受而整体 Done。

## 6. 换版、验收与完成的并发规则

Candidate、Acceptance Decision 和 Issue 完成均归 Issue 权威写入边界。所有入口（手动、批量、Project Workflow、SOP 出口、PR 自动推进）必须服从同一完成条件。

| 先发生的事实 | 后到请求 | 处理 |
|---|---|---|
| C1 被 C2 替代 | 基于 C1 的接受请求 | 拒绝其作为当前候选接受；保留 C1 的历史记录 |
| C1 接受先生效 | 随后提交 C2 | 接受仍归 C1；C2 成为新的待处理候选，不继承接受 |
| 验收与换版并发 | 两者争用当前候选 | 在权威写入点串行化；失败方读取当前 Candidate 后重新确认 |
| 标准版本更新 | 旧标准下的接受迟到 | 决定归旧标准；若当前完成要求新标准，不得据此完成 |
| PR 全部合并 | Candidate 尚未接受且要求具名验收 | PR 自动推进不得绕过验收门槛 |
| Candidate 已接受 | 新增未合并 PR 或必需工程检查变化 | 重新核对当前完成条件；不静默沿用旧 PR 集合 |
| Candidate 部分接受 | 请求 Issue Done | 仅当工作约定允许部分完成且剩余必需范围已处理时才允许 |
| Issue 已 Done | 提交新 Candidate | 不自动改写已完成事实；按显式重开或新 Issue 规则处理 |

**换版先发生**：旧 Candidate 的验收请求不能接受当前候选，也不能完成 Issue。

**接受先发生**：决定有效于当时的 Candidate；后续 Candidate 不继承该决定。若 Issue 已 Done，新增交付走显式重开或新 Issue。

### 6.1 Issue revision 的作用与限制

expected_revision 是并发写入保护，不是 Candidate 身份，也不是 Acceptance Decision。验收请求必须显式固定 Candidate ID 和标准版本；服务端在决定生效时核对：
- Candidate 仍是本交付目的的当前候选；
- 候选 manifest 与送审时一致；
- 标准版本仍适用；
- 决定者当前具有验收权限；
- 必需 Evidence 已可取得且覆盖要求；
- Candidate 尚未被撤回或替代。

如果仅有无关评论导致 Issue revision 变化，可以重新读取后复核以上条件，再在新 revision 上重试；如果候选、标准、权限或证据发生实质变化，必须要求决定者重新确认。

## 7. 多生产者与交付汇总

多个 Worker / 子 Issue 可以并行生产 Artifact；每份产物保留自己的生产者、Run、Issue / Sub-Issue 来源和版本。

Candidate 整合者不自动继承生产者身份，也不能仅凭子 Issue Done 就推断父 Issue 已接受其成果。父 Issue 必须按自身 Work Agreement：
1. 选择实际需要的子项产物版本；
2. 将它们组合进本次 Candidate；
3. 核对来源、可读权限和适用版本；
4. 组织本 Issue 所需的检查和验收；
5. 记录本次消费了哪些子项结果。

如果多个 Worker 修改同一交付物，必须先确定集成后的 Artifact 版本（例如一个明确 commit / build / 文件版本），再形成 Candidate。不能把多个相互冲突的分支结果直接拼成一个 Accepted Candidate。

## 8. PR 与工程状态的关系

PR / CI 是工程来源与证据：
- PR head SHA 是代码候选的一个输入版本；
- merge commit / target branch commit 是合并后的工程事实；
- CI 结果绑定其实际检查的 commit SHA、workflow / job、环境和时间；
- PR 全部合并只满足工作约定中声明的工程条件，不代表产品或业务验收；
- PR 自动完成只可作为 Issue 状态推进入口之一，必须在权威写入时再次核对当前 Candidate、验收决定和全部完成条件。

若工作约定未要求具名验收，可按轻量完成规则处理；若要求具名验收，PR 自动完成不得绕过该要求。合并后又新增 PR、目标分支变化或候选换版时，按当前完成条件重新判断。

## 9. D6 收敛后的对象边界

- **Artifact**：产物和具体来源版本。
- **Candidate**：一次固定的送审组合。
- **Evidence**：针对具体要求、候选和标准的可核查事实。
- **Evaluation**：基于证据的评价结论。
- **Acceptance Decision**：有权主体对具体 Candidate 和范围作出的决定。
- **Delivery Record**：汇总交付、证据、缺项、决定和交接过程。
- **Issue**：唯一业务工作权威，维护当前候选、有效决定、责任与完成状态。

这些对象有明确关系，但不应把它们合并成一个万能 Delivery 状态对象。

## 10. 进入技术设计前的待验证事项

1. Candidate manifest 的权威保存位置及与 Issue 当前候选的条件写入边界。
2. 附件内容摘要、不可变存储版本和长期可取保证；普通附件删除后的候选可用性处理。
3. PR head、merge commit、CI run、构建产物和附件如何统一引用为 Artifact。
4. Evidence 的逐项要求映射、标准版本和复用判定。
5. 部分接受、例外放行、撤回和显式重开如何映射到 Issue 完成条件。
6. PR 自动完成如何接入 Candidate / Acceptance Gate，并保持所有 PR 状态的并发复核。
7. 并发验证覆盖：换版先、验收先、标准变更、PR 新增 / 取消、重复决定、迟到报告、附件删除和权限撤回。

本阶段只确定产品契约。数据库结构、API、事件载荷和迁移方案留待后续技术设计。
