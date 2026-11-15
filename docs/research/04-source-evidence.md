# 专题四 · 成本、质量与自改进研究记录

V0.1 · 探索基线 · 2026-11-15

## 1. 本轮输入

专题四承接：
- [专题三 A：执行平面研究](03a-source-evidence.md)，提供 Run、宿主原生标识、Trace、Usage、Artifact、共享范围和采集覆盖。
- [专题三 B：能力与知识治理](../architecture/03b-capability-governance.md)，提供资产版本、实际投递 / 加载证据、工具来源和跨宿主结果证明。
- [专题二：SOP 工作流](../architecture/02-sop-workflow.md)，提供 Node Attempt、节点内自修正、执行重试、跨节点返工和预算边界。
- [架构总览](../architecture/overview.md)，要求成本来源明确、无重复统计，后台活动不强制业务化，评价与事实分离。

## 2. 已有源码证据

### 2.1 Multica：宿主用量采集和写入落点

固定 Multica fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc 的 Codex / Claude Adapter：
- Codex 过滤其他 Thread；首个匹配快照取 last，后续从 total 变化计算当前执行量；对历史重放、重复快照、终态后用量和多次模型请求有测试。
- Claude 按模型消息 ID 去重；恢复前捕获基线，最终 modelUsage 按模型求差；基线缺失时优先保留流式本轮用量。
- 控制平面按 task / provider / model 覆盖当前用量快照；过程快照跳过加法指标，避免刷新重复累计。
- 当前上游仍需本项目补齐：多个采集源的并发合并、来源冲突、计量覆盖区间、跨系统幂等和更正历史。

证据与复跑：[3A 研究第 11 节](03a-source-evidence.md#11-第二阶段宿主协议与本地观察)。

### 2.2 TeamAI：独立评价与自改进

固定 TeamAI 556b5246f2c13ad28b8b79b5b513a78ed8ab9dae：
- 符合条件的已结算 pass 会启动独立评分 Run；评分读取具体 Run / Step / Pass 与 scorer 版本，原业务 Run 保持成功，不把评分结论混入原执行状态。
- Benchmark 先生成实验定义，再执行评分并汇总；可比性检查会核对样本摘要、rubric、工具、模型、effort 和评分方式。
- 自改进从可复现且未被回归题覆盖的失败提取输入，达到阈值后在专有分支生成改动并交付 PR；默认提示要求为失败新增回归题。
- 评分与改进 Agent 仍有自己的成本；PR 不等于已经发布，更不等于线上效果已改善。

证据：[TeamAI 分册 T7 / T8](topic-02/teamai.md)。

### 2.3 LoopForge：从终态执行轨迹到改进建议

固定 LoopForge 97b3cdc2f29a88e8767a8dc6c03bfb8865622653：
- 终态 Run 才能启动评测；后端提取节点尝试、返工、工具重复、错误、耗时和制品。
- 模型生成维度评价，后端按维度权重重新计算总分。
- 建议通过独立 API 由使用者选定建议 ID，再逐项应用到受支持的项目 Workflow 或 Agent；通用模板先取得项目副本。
- 上游测试验证了终态门槛、事实提取、加权评分和建议写回。但建议写回后仍需新样本验证效果，不能将“应用成功”当成“改进有效”。

证据：[LoopForge 分册第 9 点](topic-02/loopforge.md)。

### 2.4 专题三 B 的最新复验归属修订

专题三 B 后续交叉审查明确了一个成本归集边界：会话切换发生在实际开工前，且原派发仍有效时，可以沿用原 Run；但 Hook 改写结果发生在宿主已返回并退出后，重新执行必须签发后继 Run，关联原 Run 的拒收证据，同时可保留原 Node Attempt、候选和规则版本。该修订已进入当前分支所合并的 3B 资料与真实回执。专题四必须将原 Run 的失败执行成本与后继 Run 的复验成本分别记录，再由节点尝试视图汇总，不能因它们属于同一尝试而合并为一次执行。

证据：[3B Hook 复验归属修订](topic-03b/existing-session.md#hook-复验的-run-归属修订) · [后继 Run 原始回执](topic-03b/fixtures/hook-reverification.json)。

### 2.5 Qoder 与 CodeBuddy Credits 的本地 Runtime 协议

**Qoder Agent SDK：** 官方 TypeScript / Python SDK 的本地 CLI message stream 暴露请求级 Credits。每条 Assistant message 的 `message.usage.credits` 是该模型请求实际扣除优惠后的 Credits；`original_credits` 和 `billable` 可选。Result 的 `total_credits` 与按模型 `modelUsage[].credits` 是从当前 CLI Session 开始的累计值，不能与请求级 Credits 再相加。Credits 字段是可选的，旧版 CLI / SDK 或服务不可用时缺失不能解释为 0。Java SDK 当前没有这些 Credits 类型字段。

**重要运行边界：** Qoder Agent SDK 的 `query()` 会启动并驱动本地 qodercli 子进程；它适用于由平台 Runtime 通过 SDK 托管启动的本地 Qoder CLI。它不等于能旁路读取成员任意已打开的 Qoder IDE / 终端会话。若不能经 SDK 接管，也没有其他实际暴露 Credits 的宿主事件，则保持 unknown。只读取 `/usage` 的账号额度快照不算执行消耗。

**CodeBuddy Code：** 官方 CLI 的 `--output-format stream-json` 提供逐轮 `system/usage_update`。每次模型调用或受支持的生成工具完成后可产生 stage 事件；轮次结束前会产生 snapshot，随后 result 的 `_meta["codebuddy.ai/turnUsage"]` 与 snapshot 相同。按 `session_id + requestId + stage.id` upsert 同一 stage；stage 修正覆盖旧值，不能累计 `delta`、`total` 和 snapshot。优先使用终态 snapshot；`stage.credits` 未出现时保持 unknown，不用 token 数填补。该能力适用于平台通过 stream-json 驱动的 CodeBuddy CLI；若成员只使用 IDE 且未向 Runtime 暴露这些字段，则保持 unknown。

**项目边界：** 不调用企业 API、账户 Usage 页面或账单接口；不抓取账号余额或扣费页面。平台只消费本地 Runtime 原生消息流，Credits 单位按宿主分开。Run 绑定由平台启动时的执行上下文提供；若只拿到 session / request / stage 但无法绑定 Run，则保留宿主范围观察，不猜 Issue 归属。

官方依据：[Qoder Agent SDK Cost and usage](https://docs.qoder.com/cli/sdk/cost-usage) · [Qoder SDK TypeScript references](https://docs.qoder.com/cli/sdk/references-typescript) · [CodeBuddy Stream-JSON Per-Turn Usage Events](https://www.codebuddy.ai/docs/cli/stream-json-turn-usage) · [Qoder Hooks](https://docs.qoder.com/cli/hooks) · [CodeBuddy Hooks](https://www.codebuddy.ai/docs/cli/hooks)。


## 3. 第一批关键验证假设

| 编号 | 假设 | 失败时的设计影响 |
|---|---|---|
| C1 | 同一原生请求被 Hook、Daemon、OTel、转录回放多路观察时，可保留多份证据但只生成一份计量 | 需要显式的跨源匹配状态和人工核对，不能自动金额合并 |
| C2 | Codex 累计快照与 Claude 按消息累计用量可以统一映射为带区间的 Usage Entry，同时保留宿主原口径 | 无法证明独占区间时，保留 Token-only / partial，不做差额猜测 |
| C3 | 迟到的更可信证据能更正当前计量，同时完整保留旧值及更正链 | 使用 append-only 修订，不覆盖原始 Observation |
| C4 | SOP 节点、父子 Issue、Squad、项目汇总可由 Run 去重得到，不需要各层独立记账 | 若 Run 归属不完整，先补归属回执，不在汇总层补猜 |
| C5 | Qoder / CodeBuddy Runtime 原生 Credits 事件可按宿主事件身份去重并关联 Run | 无稳定事件身份时保留原始观察，不推断幂等身份 |
| C6 | Runtime 只上报成员级 Credits 时，不将其伪分配给具体 Run；Runtime 不上报时保持 unknown | 仅保留可证明的观察范围，禁止通过账户 API 或周期余额补数 |
| C7 | 不同宿主 Credits 保持独立单位，不通过外部账户接口补数或换算现金 | 只展示原生 Credits 与 unknown，不输出推测金额 |
| Q1 | 事后评分使用独立评价执行记录，不能改写原 Run 的状态和业务验收 | 评分只能作为独立反馈，不接入门禁 |
| Q2 | Benchmark 只有在样本、标准、模型 / 工具和评分配置可比时才给出胜负结论 | 显示不可比及原因，不产出误导性排名 |
| I1 | 改进提案可以从失败事实追到候选资产修改、回归题和发布版本 | 无证据闭环的建议只保留为人工笔记 |
| I2 | 资产发布后必须通过新实例和后续样本验证，不能用提案分数宣称线上改善 | 效果未验证时状态保持“待观察” |

## 4. 首轮验证场景

- 多路观察同一请求、同源重复回放、跨源部分重叠、无原生 ID 的弱关联。
- 累计快照首基线缺失、计数重置、乱序、跨模型、跨 Issue 交错、终态后晚到用量。
- Provider usage、费率估算、供应商账单、Token-only 和未知费用并列。
- 节点内自修正多个 Run、执行错误重试、跨节点返工，验证同一 Run 不因多个上层引用重复。
- 独立评分 Run、Benchmark Run、索引 / 知识后台 Run 的成本单独归集。
- 终态事实抽取、模型评价、人工评价、门禁与业务验收相互隔离。
- 固定 Benchmark 下的候选对比；样本、rubric、模型、工具、effort 变化时拒绝直接比较。
- 改进建议被拒绝、部分应用、候选回归失败、审核通过发布、发布后效果未改善等分支。

## 5. 异构 Credits 适配与验证

原型实现两种本地 Runtime 解析器：Qoder Agent SDK Assistant message 读取请求级 `usage.credits`，Result `total_credits` 单独作为会话累计快照；CodeBuddy `usage_update` 解析 stage 与 terminal snapshot，按 `session_id + requestId + stage.id` 覆盖更新。新增 8 项协议回归后，成本账本与评价总计 32 项测试在 Node 24.22.2 通过。[Runtime SDK / stream-json CI #14](https://github.com/ScWen7/Issues/actions/runs/43672399496)。记录保留宿主事件 ID、成员、Session / Turn、Run、Credits 数值与观察时间。显式 Run 绑定才归入 Run；没有 Credits 字段生成 `unknown`，不读取企业 API、账户 Usage 页面或账单补数。

测试覆盖两类 Runtime Credits 的单位隔离、显式 Run 绑定、无用量上报时保持 unknown，以及不从订阅额度、账户余额或 Token 数推算 Credits。上述 32 项 CI 使用官方字段构造的确定性协议夹具；安装版 Runtime 的本机实测另见第 6 节，IDE 会话旁路和宿主升级兼容继续按现场验证。Qoder SDK 方式需要平台 Runtime 启动 / 恢复由 SDK 管理的 qodercli；CodeBuddy 需要由 Runtime 启动 `--output-format stream-json` 的 CLI。成员仅打开 IDE 且未通过上述 Runtime 托管时，不宣称已采集 Credits，保持 unknown。

## 6. 真实 Runtime 验证包（4.1.2）

目标环境由成员提供：Qoder CLI 1.1.88、CodeBuddy Code CLI 2.181.0。已新增本机探针和回执说明：
- [目标版本本机验证步骤与回执要求](topic-04/runtime-validation-1.1.88-2.181.0.md)
- [Qoder Agent SDK 探针](../../prototypes/topic-04/qoder-sdk-runtime-probe.mjs)
- [CodeBuddy stream-json 探针](../../prototypes/topic-04/codebuddy-stream-runtime-probe.mjs)

官方版本证据：CodeBuddy v2.181.0 Release Notes 明确列出 CLI v2.181.0，并说明新增 stream-JSON per-turn usage，包含稳定 stage identity 和 Credits 结算；因此本次版本是目标功能版本，不只是“可能支持”。[v2.181.0 Release Notes](https://www.workbuddy.ai/docs/cli/release-notes/v2.181.0)。Qoder Agent SDK 官方文档提供请求级 `message.message.usage.credits` 和 Session 累计 `result.total_credits`，并说明 Credits 字段可选、缺失不可视为 0。[Qoder SDK Cost and Usage](https://docs.qoder.com/cli/sdk/cost-usage) · [TypeScript SDK Options](https://docs.qoder.com/cli/sdk/references-typescript)。

探针只执行无工具的只读提示，按白名单保存 Credits、Session / Request / Stage 身份、版本和状态，不保存 Prompt / 回复正文、源代码、工具参数、账号凭据或账户额度。Qoder 探针显式支持 `QODERCLI_PATH`，以便将 SDK 绑定到成员声明的 qodercli 二进制；若无独立 qodercli，SDK 自动管理版本必须单独记录。CodeBuddy 探针启动 `--output-format stream-json`，只留存 `usage_update` 与终态摘要。

当前状态：**2026-11-15 本机 Mac 实测已归档**。Qoder 1.1.88 仅取得 Session 累计快照且 SDK 超时，判为 PARTIAL；CodeBuddy 2.181.0 取得 Stage 和一致的终态快照，判为 PASS；新增 Copilot 1.0.107 取得两轮累计用量及恢复后的标识对照，逐请求 Credits 保持 unknown，判为 PARTIAL。真实回执、离线重放、缺失字段对照分别记录。[实测结果](topic-04/runtime-validation-1.1.88-2.181.0.md#8-本机-mac-实测记录2026-11-15) · [白名单回执与验证明细](../../artifacts/topic-04/mac-20261115-0350/validation.json)。

## 7. 成本账本原型首轮结果

已在分支中加入确定性 Node 原型，覆盖多观察源去重、命名空间隔离、同等可信来源冲突、较高可信来源优先、Run 归属冲突、缺失原生标识、累计快照差额、基线缺失 / 模型变化 / 计数重置 / 乱序，以及 Run 汇总排重。成本账本 11 项用例通过；随后与评价原型合并运行的远端 Node 24 CI 共 20 项用例全部通过。[成本账本独立 CI #4](https://github.com/ScWen7/Issues/actions/runs/43670463148) · [成本 + 评价 CI #6](https://github.com/ScWen7/Issues/actions/runs/43670657657)。

该原型仅验证确定性归集规则，不代表最终账本 Schema。后续还需增加 Observation 更正链、跨采集器身份映射、计量覆盖区间、供应商费率 / 账单对账和平台后台成本类型。

## 8. 评价与 Benchmark 原型首轮结果

新增独立评价原型：只对终态业务 Run 启动评价，评价记录引用原 Run、由独立 evaluation Run 承载；缺失证据返回 inconclusive 而不是低分；加权维度分必须带证据；事后评价默认 advisory-only，只有 SOP 明确声明门禁且 Run 与 scorer 版本匹配时才允许形成门禁结果。

Benchmark 可比性原型要求样本集摘要、rubric、工具链、模型、effort、评分器版本、聚合方式、环境摘要和重复次数全部一致。改进评估只有在可比时才计算质量提升和成本变化；达到阈值只生成 candidate-for-review，不自动批准或发布。首次 CI 发现浮点输出精度断言过严，已将展示差值规范到六位小数，阈值判断仍使用未舍入原值。修正后成本与评价共 20 项回归在 Node 24.22.2 全部通过。[远端 CI #6](https://github.com/ScWen7/Issues/actions/runs/43670657657)。此前 27 项测试包含后来明确不采用的企业 API / 账户用量适配。按 Runtime-only 边界移除这些路径并重写测试后，当前有效版本为 24 项回归全部通过，覆盖 Qoder / CodeBuddy Runtime Credits 上报、显式 Run 绑定、未上报保持 unknown、单位隔离，以及成本与评价基线。[Runtime-only CI #12](https://github.com/ScWen7/Issues/actions/runs/43671634747)。

当前原型仍不实现评分任务调度、模型裁判调用、完整样本存储、人工审批 UI 或资产发布；它验证的是记录隔离、比较资格和决策边界。

## 9. 证据边界

现有上游测试和 3A 回环探针证明部分协议与算法行为，不证明真实供应商账单完整性、所有宿主成本覆盖或生产团队中的改进收益。第一轮原型将使用可复现的合成 Observation 和已有真实宿主协议记录；账单对账与真实项目发布后观察另列现场验收。

## 10. 三类 Runtime 的 Mac 真实回执与官方协议复核（2026-11-15）

本节以远端归档提交 `2694789f8f02c2ae8213980bc24fb74153a6ef38` 为输入。真实环境、白名单 JSONL、进程状态、离线重放与 SHA-256 清单位于 [mac-20261115-0350 归档目录](../../artifacts/topic-04/mac-20261115-0350/)；汇总判定见 [validation.json](../../artifacts/topic-04/mac-20261115-0350/validation.json)。

### 10.1 字段存在性与单次 / 累计口径

| Runtime / 版本 | 官方协议字段 | 本机实际观察 | 可计量结论 |
|---|---|---|---|
| Qoder CLI 1.1.88；SDK 1.0.59 | Assistant `message.message.usage.credits` 是单次模型请求；Result `total_credits` / `modelUsage[].credits` 是 Session 累计。字段可选。 | 没有 Assistant message；只有 Result `total_credits=0` Session snapshot。SDK 180 秒超时，退出码 -15。 | Session snapshot 的 0 只证明快照值为 0；单次请求 Credits = unknown。不能把 Session snapshot 当单次消耗。 |
| CodeBuddy CLI 2.181.0 | `system/usage_update` 的 stage 带 `stage.id`、`stage.credits`；snapshot 与 Result 内 `turnUsage` 相同；`total` 是当前 Turn 快照。 | 一条真实 model stage = 0.69 Credits；Turn snapshot = 0.69；Result snapshot = 0.69。 | 该 Turn 的真实 Stage 消耗为 0.69；两份 snapshot 是同一事实的重复呈现，不相加。 |
| GitHub Copilot CLI 1.0.107 | 官方 SDK 的 `assistant.usage` 提供单次调用 Token 与 premium multiplier；`session.usage_checkpoint.totalNanoAiu` / `session.usage.getMetrics` 提供 Session 累计 AI credit。 | 两次 invocation 共用一个 Session。累计 nano-AIU 为 7,324,050,000 → 7,637,870,000；premium request cost 为 1 → 2。 | 差值 313,820,000 nano-AIU 仅是连续 Session snapshot 的派生差；没有直接的逐请求 nano-AIU 事件，逐请求 Credits = unknown。 |

Qoder 版本核对补充：本机 qodercli 与目标版本均为 1.1.88；Agent SDK 包为 1.0.59，SDK 默认声明管理的 CLI 版本为 1.1.83，但测试通过 `QODERCLI_PATH` 显式指定本机 1.1.88，因此不是 SDK 自动下载版本的验证。Qoder 官方文档说明顶层 `request_id` 默认不提供，需通过 `QODER_EXPOSE_REQUEST_ID=true` 启用。首轮 Qoder 回执探针曾把 `message.uuid` 投影到 `request_id`，字段命名不准确：该值应解释为 SDK 消息事件 UUID；首轮真实 request_id 未取得。已在提交 `6c5b34a` 修正探针：显式启用 `QODER_EXPOSE_REQUEST_ID=true`，分别输出 `request_id` 与 `event_id`。2026-11-15 在同一 Mac 以提交 `a99d9df` 的修正版重跑，取得独立的新回执：event_id 有值，request_id 仍为 null，Assistant 用量事件为零，Session 累计快照为 0，判定仍为 PARTIAL。探针报告 incomplete，Node 进程在 180 秒后由采集器终止。新旧回执分别保存，旧回执字节与 SHA-256 保持原值；消息事件 UUID 只按消息身份使用。[修正版重跑记录](topic-04/runtime-validation-1.1.88-2.181.0.md#82-qoder-修正版探针的-mac-重跑2026-11-15) · [新验证明细](../../artifacts/topic-04/mac-qoder-fixed-20261115-0432/validation.json)。

### 10.2 事件身份、重复上报与修订

- **CodeBuddy：** 原生 requestId 表示用户 Turn；`stage.id` 表示模型或生成工具 Stage 的稳定身份；外层 frame `uuid` 是投递身份，不是计量身份。按 `(session_id, requestId, stage.id)` upsert。真实回执离线重放三次，仍归并为 0.69；Turn snapshot 和 Result 中相同的 snapshot 不得重复结算。本次没有真实 Stage 修订事件，Stage 更正覆盖由 13 项离线协议测试验证。
- **Copilot：** 官方事件信封有 UUID event ID；本机两个 checkpoint 离线重放三次后仍只有两个唯一 checkpoint。两个 invocation 的 `turnId` 都是 `0`，说明 turnId 是会话内部序号，恢复 / 多入口下不能单独作为唯一键。第二次 invocation 有 `interactionId` 与 `apiCallId`，第一次的 API call ID 未被初始投影保留。result 终态帧在本次 JSONL 投影中没有 event ID，不能用于 checkpoint 去重。
- **Qoder：** 首轮和修正版重跑均没有 Assistant 请求用量事件，请求级重复上报行为保持未观察；Result Session snapshot 单独保存。旧回执中误标为 request_id 的值按事件 UUID 解读；修正版已拆分两个字段，实际 request_id 仍为 null。新快照按 event_id 离线重放三次后只保留一个事件，此项只验证快照事件去重。

### 10.3 Run / Session / Turn 的关联结论

三类回执中的 `run_id` 均由探针 / 平台在启动时显式注入，是平台执行绑定，不是宿主原生 ID。Session ID 是宿主原生会话身份。CodeBuddy 的 requestId 关联一轮，stage.id 关联轮内实际计量阶段；Copilot 的 turnId 可重复，需叠加 event ID、interactionId / apiCallId 等原生身份；Qoder 本次只取得 Session ID 与 SDK 消息事件 UUID，没有真实 request_id。

Copilot 本机测试在同一 Session 中执行两个不同 Run，直接证明 Session 与 Run 不能建模为一对一。正确关系是：一个 Run 绑定一次平台发起的 Runtime invocation / 执行段；多个 invocation / Run 可以落在同一宿主 Session。归属需由启动绑定和原生事件共同证明，不能仅凭 Session ID 反推 Run。Run 绑定缺失时保留 Session 级 Observation，不伪分配给 Issue 或 Node Attempt。

### 10.4 归档与边界

- CodeBuddy 0.69 是本机 Runtime 明确上报的单次 Stage Credits；Qoder 请求级 Credits 与 Copilot 逐请求 nano-AIU 均保持 unknown。
- 不调用企业 API、账户 Usage 页面或账单接口；不使用订阅余额、Token 或时长推算 Credits。
- nano-AIU、Premium Request cost、Token、Qoder Credits、CodeBuddy Credits 是不同单位，不做无依据换算。
- 真实 Runtime 入口通过不等于 IDE 任意会话可旁路观测；本轮只证明探针启动的受管本地 CLI / SDK 入口。

官方协议来源：
- [Qoder Agent SDK Cost and usage](https://docs.qoder.com/cli/sdk/cost-usage) · [Qoder TypeScript SDK references](https://docs.qoder.com/cli/sdk/references-typescript)
- [CodeBuddy CLI v2.181.0 Release Notes](https://www.codebuddy.cn/docs/cli/release-notes/v2.181.0) · [CodeBuddy Stream-JSON Per-Turn Usage Events](https://www.codebuddy.cn/docs/cli/stream-json-turn-usage)
- [GitHub Copilot SDK Usage and billing](https://docs.github.com/en/copilot/how-tos/copilot-sdk/features/usage-and-billing) · [GitHub Copilot Streaming session events](https://docs.github.com/en/copilot/how-tos/copilot-sdk/features/streaming-events)

### 10.5 Qoder SDK Query 生命周期复核

8.2 的 Qoder 修正版探针收到 Result 后仍等待异步流自然结束，180 秒后被采集器终止；该探针没有显式调用 Query 的 `q.close()`。Qoder 官方 Cost and usage 示例在完成用量读取后调用 `q.close()`，TypeScript SDK Reference 也提供 Query Session 的主动结束能力。因此，先前的超时不能直接归因为 CLI / SDK 执行失败。已在 `3d18c51` 修正探针：Result 到达后结束迭代，并在 `finally` 显式 `q.close()`。此修正等待 Mac 真实重跑，现阶段只将超时原因标为 `probe_lifecycle_unverified`；请求 Credits 仍为 unknown。

官方依据：[Qoder Cost and usage](https://docs.qoder.com/cli/sdk/cost-usage) · [Qoder TypeScript SDK references](https://docs.qoder.com/cli/sdk/references-typescript)。