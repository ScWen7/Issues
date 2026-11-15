# 专题四 · 成本、质量与自改进

V0.1 · 探索基线 · 2026-11-15

## 1. 目标

让平台回答四个问题：一次工作实际消耗了什么；这些消耗应归到哪个 Run / Issue / SOP 节点；执行结果质量如何且评价依据是什么；哪些重复问题值得改进、改动是否真的改善结果。

专题四不建立第二套工作状态或 Run。Issue、Run、Node Attempt、SOP 实例和资产版本沿用前序专题；专题四读取执行事实，产生计量、评价、Benchmark 和改进证据。

## 2. 共同原则

- 先保存原始观察，再形成计量结论。原生请求、宿主快照、工具调用、服务回执、账单行和人工说明保留来源、发生时间、接收时间、覆盖范围及摘要。
- 事实、推断和未知分开。供应商报告的 Token、宿主估算、账单实付、仅知 Token、未知费用不能压成一个“真实成本”字段。
- 多路观察不等于多次执行。同一原生请求可被 Hook、Daemon、OTel 和转录导入同时观察；观察可并存，计量单元只能结算一次。
- 归属依赖实际执行身份。Run 是成本的原始归属单位。Issue、父子 Issue、SOP、节点尝试、Squad 和项目是引用及汇总视图，按底层计量单元去重。
- 评价不改写执行事实。执行成功、质量评分、SOP 门禁和业务验收是不同结论。
- 改进不自动改变在途工作。建议先形成候选改动，经回归和审核后由专题三发布新版本；新实例显式选择新版本。

## 3. 成本账本

### 3.1 两层记录

**Observation（观察）**保存原始事实：来源系统、宿主与账号命名空间、Session / Thread / Turn / Prompt / Message / Tool Call 等原生标识、事件种类、阶段、模型 / Provider、指标、单位、区间、发生与接收时间、原始摘要和采集覆盖。

**Usage Entry（计量条目）**是经过归属、去重、口径判断后的结算记录：计量单元身份、生产 Run、执行成员、Provider / Model、指标与数量、计费口径、来源证据、覆盖状态、当前版本及更正链。

一条 Observation 可以不产生 Usage Entry；多个 Observation 可以共同证明一条 Usage Entry。禁止把“收到一个事件”直接等同于“新增一次费用”。

### 3.2 原生计量单位与异构宿主

账本统一的是记录结构和归属规则，不是强迫所有宿主使用同一种单位。每条计量都必须携带 `provider`、`metric`、`unit`、`value`、来源命名空间、原生事件身份和计量覆盖范围。单位至少区分：

| 宿主 | 原生单位 | Runtime 可观测入口 | 归属边界 |
|---|---|---|---|
| Codex | input / output / cached tokens | App Server Thread / Turn / Usage；CLI JSON 投影 | 累计快照先确定基线和独占区间 |
| Claude Code | tokens、请求级 usage | Hooks、SDK 消息、OTel request_id / message UUID | 按请求 / 消息身份去重，区分累计与增量 |
| Qoder | Qoder Credits | 本地 Qoder Agent SDK Assistant 消息 `message.usage.credits`；Result 的 `total_credits` 仅作会话累计快照 | 受管 SDK Runtime 产生的请求用量可绑定 Run；缺字段保持 unknown。不能据此声称能读取任意已打开 IDE 会话 |
| CodeBuddy Code | CodeBuddy Credits | 本地 CLI `--output-format stream-json` 的 `system/usage_update` | 以 `session_id + requestId + stage.id` upsert；snapshot 替代 stage 汇总，不能相加。IDE 未暴露则 unknown |
| GitHub Copilot CLI | nano-AIU、Premium Request cost、tokens（各自独立） | CLI JSON 事件流的 `session.usage_checkpoint`；官方 SDK 另有 `assistant.usage` 与 `session.usage.getMetrics` | checkpoint 是 Session 累计快照；本次 CLI 实测未取得逐请求 nano-AIU。Turn ID 可能在恢复后重用，不能单独去重；以原生事件 ID / API Call ID 和显式 Run 启动绑定关联 |

### 3.3 Mac 真实 Runtime 回执核验（2026-11-15）

本机实测材料与逐字段核验见[专题四真实 Runtime 记录](../research/topic-04/runtime-validation-1.1.88-2.181.0.md#8-本机-mac-实测记录2026-11-15)。真实回执与进程状态见 [validation.json](../../artifacts/topic-04/mac-20261115-0350/validation.json)。

- **Qoder CLI 1.1.88 / Agent SDK 1.0.59：PARTIAL。** 实际 SDK 显式绑定 qodercli 1.1.88，未使用 SDK 声明的托管 CLI 1.1.83。SDK 在 180 秒后被采集器终止，没有 Assistant message；只收到 Result 的 Session 累计快照 `total_credits=0`。该 0 是明确观察到的 Session 快照，不代表本次请求消耗为 0；请求级 Credits 为 unknown。特别更正：现存 Qoder JSONL 投影把 SDK 消息的 `uuid` 写进 `request_id`，但它是消息事件身份，不是官方定义的 request_id；该次采集没有真正取得 request_id。官方支持通过 `QODER_EXPOSE_REQUEST_ID=true` 暴露顶层 request_id，下一轮探针需修正后重测。
- **CodeBuddy CLI 2.181.0：PASS（受管 CLI 入口）。** 真实 stage 的 `stage.credits=0.69`，身份为 Session + requestId + stage.id；Turn snapshot 和 Result snapshot 均为 0.69，是同一事实的终态副本，不得再次相加。真实回执离线三次重放仍为 0.69；但本轮只观察到一个 stage，未实测真实 stage 修订事件。修订覆盖行为目前由 13 项离线协议回归支持。
- **GitHub Copilot CLI 1.0.107：PARTIAL。** 两次独立 Runtime invocation 共享同一 Session，原生 `turnId` 均为 `0`；第二次观察到 `interactionId` 和 `apiCallId`，第一次的调用身份未被投影留存。两次 Session checkpoint 的 `totalNanoAiu` 从 7,324,050,000 增至 7,637,870,000，差值 313,820,000 是两个累计快照的派生差，不是 Runtime 直接提供的单次 Credits。逐请求 nano-AIU 保持 unknown；`totalPremiumRequestCost` 是另一种计量，不与 nano-AIU 或 Token 混用。

**Run / Session / Turn 关联规则由实测进一步明确：** Run ID 是平台启动时注入的执行绑定，不是这些宿主的原生 ID；Session ID 是宿主身份；Turn / Request / Stage / API Call 是 Session 内更细的执行身份。一个 Session 可以承载多个平台 Run，因此不能把 Session 与 Run 设为一对一。Copilot 的 turnId 重用证明 `session_id + turn_id` 仍不足以跨恢复唯一标识；应优先用原生 event ID、requestId / apiCallId / stage.id，并保留显式 Runtime invocation → Run 绑定。无法证明绑定时只保留 Session 范围 Observation，不归入具体 Run。

**重复上报边界：** CodeBuddy stage 以 `session_id + requestId + stage.id` upsert；同一终态 snapshot 与 result 内嵌 snapshot 是同一事实。Copilot checkpoint 以 Session + 原生 event ID 识别，离线重放三次后仍为两个 checkpoint；result 终态帧在本次投影中没有 event ID，不能用它充当计量身份。Qoder 没有请求级事件，不能宣称已验证请求重放幂等。

官方协议核对：
- [Qoder Agent SDK Cost and usage](https://docs.qoder.com/cli/sdk/cost-usage) · [Qoder TypeScript SDK references](https://docs.qoder.com/cli/sdk/references-typescript)：明确区分请求级 `message.message.usage.credits` 与 Session 累计 `result.total_credits`；字段可选、缺失不可视为 0；`request_id` 默认不暴露，可通过环境变量显式启用。
- [CodeBuddy CLI v2.181.0 Release Notes](https://www.codebuddy.cn/docs/cli/release-notes/v2.181.0) · [Stream-JSON Per-Turn Usage Events](https://www.codebuddy.cn/docs/cli/stream-json-turn-usage)：目标版本明确包含逐轮用量与稳定 Stage identity；官方定义 frame UUID 是投递身份，计量去重使用 requestId + stage.id。
- [GitHub Copilot SDK Usage and billing](https://docs.github.com/en/copilot/how-tos/copilot-sdk/features/usage-and-billing) · [Streaming session events](https://docs.github.com/en/copilot/how-tos/copilot-sdk/features/streaming-events)：官方区分逐 API 调用的 `assistant.usage` 与 Session 累计 `session.usage.getMetrics` / `session.usage_checkpoint`；`totalNanoAiu` 是 Session 累计量，不能直接当作本次 CLI invocation 消耗。

本机归档材料：[Mac 真实回执与验证明细](../../artifacts/topic-04/mac-20261115-0350/validation.json)。