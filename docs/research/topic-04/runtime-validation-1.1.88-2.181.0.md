# 专题四 · 真实 Runtime 验证包

目标版本：Qoder CLI / SDK 环境 1.1.88；CodeBuddy Code CLI 2.181.0  
验证阶段：4.1.2 · 本机真实进程回环  
采集边界：只读取本机 Runtime stdout / SDK message stream；不调用企业 API、账户 Usage 页面或账单接口。

## 0. 获取验证包

在成员机器上：

```bash
git clone --branch research/topic-04-cost-quality-improvement https://github.com/ScWen7/Issues.git
cd Issues
```

如果已经有仓库副本，切换到该研究分支并拉取最新提交。

## 1. 验证原则

本轮不修改成员现有 IDE / CLI 配置，不注入 API Key，不读取账号额度，不采集 Prompt、模型回复正文、源代码、工具参数或工具结果正文。

测试通过独立临时目录和只读提示完成。采集器只保留白名单字段及 Credits 计量元数据。真实 CLI 版本、SDK 实际启动的 qodercli 版本必须分别记录，不能把 IDE 版本当作 CLI 版本。

若本机 Runtime 没有输出 Credits 字段，结果为 `unknown`，这是有效的能力验证结果，不是测试失败，也不能用 Token、运行时长、余额差或模型档位补算。

## 2. 环境确认

在 macOS / Linux 终端执行：

```bash
REPO_ROOT="$PWD"
mkdir -p /tmp/teamai-topic04-runtime
cd /tmp/teamai-topic04-runtime

{
  echo "date=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "os=$(uname -srm)"
  echo "node=$(node --version 2>/dev/null || true)"
  echo "npm=$(npm --version 2>/dev/null || true)"
  echo "qoder=$(qoder --version 2>&1 | head -1)"
  echo "qodercli_path=$(command -v qodercli || true)"
  echo "qodercli=$(qodercli --version 2>&1 | head -1 || true)"
  echo "codebuddy_path=$(command -v codebuddy || command -v cbc || true)"
  echo "codebuddy=$(codebuddy --version 2>&1 | head -1 || cbc --version 2>&1 | head -1 || true)"
} > environment.txt
```

预期核对：
- Qoder 报告版本为 `1.1.88`。若 `qoder` 与 `qodercli` 版本不同，两个都记录。
- CodeBuddy CLI 报告版本为 `2.181.0`。
- 不要为了测试升级或覆盖现有 CLI。
- Qoder SDK 通过 `pathToQoderCLIExecutable` 指向被测 qodercli，避免 SDK 自动下载 / 选择另一个 CLI。若本机找不到独立 qodercli 可执行文件，不要猜测路径；先提交环境回执，SDK 自动管理的版本必须单独标注。

## 3. Qoder 1.1.88：Agent SDK 本地消息流

### 2.1 准备独立探针

```bash
mkdir qoder-probe && cd qoder-probe
npm init -y
npm install @qoder-ai/qoder-agent-sdk
```

安装后保留 `package-lock.json`，回执中记录实际 SDK 包版本：

```bash
npm ls @qoder-ai/qoder-agent-sdk --depth=0
```

运行仓库中的 `prototypes/topic-04/qoder-sdk-runtime-probe.mjs`。若本机有独立 qodercli，指定其真实绝对路径：

```bash
export QODERCLI_PATH="$(command -v qodercli)"
```

运行：

```bash
cp "$REPO_ROOT/prototypes/topic-04/qoder-sdk-runtime-probe.mjs" .
node qoder-sdk-runtime-probe.mjs > qoder-receipt.jsonl
```

探针使用现有 Qoder CLI 登录态，通过 `qodercliAuth()` 认证；不读取账号配额。提示内容为只需返回 OK 的无工具任务。探针将请求级 Assistant usage 与 Result session snapshot 分开输出，并记录 SDK 实际使用的 CLI 路径和版本。

### 2.2 必须核验

1. 是否成功启动本地 qodercli，并完成 SDK 初始化。
2. 是否收到 `assistant` 消息。
3. `message.message.usage.credits` 是否存在且为数字。
4. `original_credits` 与 `billable` 是否存在；缺失就记 null，不补值。
5. 是否收到 `result.total_credits`，并明确标记为 Session 累计快照。
6. Assistant 请求 Credits 与 Result 累计 Credits 不得相加。
7. 同一 CLI Session 若做第二轮验证，第二个 Result 累计值只能作为新的快照；按请求 UUID 归集的请求级 Credits 才是增量明细。
8. 若 SDK 实际启动的 qodercli 不是 1.1.88，记录真实版本。不能把此结果算作 1.1.88 兼容性通过。

### 2.3 Qoder 判定

- **PASS**：被测 qodercli 确认是 1.1.88，Assistant message 实际提供数值 Credits、稳定消息身份；Result 累计快照可单独识别。
- **PARTIAL**：CLI 版本正确但只提供 Result 累计值，或请求级 Credits 字段缺失。
- **UNKNOWN**：SDK 无法启动、鉴权失败、字段不存在或消息流无法取得。
- **NOT_TARGET_VERSION**：SDK 启动了其他版本 CLI。保留数据，但不作为 1.1.88 结论。

## 4. CodeBuddy 2.181.0：Stream-JSON 本地 stdout

### 3.1 运行探针

在项目临时目录执行，不要使用真实业务仓库：

```bash
mkdir -p /tmp/teamai-topic04-codebuddy
cd /tmp/teamai-topic04-codebuddy
node "$REPO_ROOT/prototypes/topic-04/codebuddy-stream-runtime-probe.mjs"
```

探针执行：
```bash
codebuddy -p "Reply with exactly OK. Do not use tools, read files, or modify anything." --output-format stream-json --max-turns 1
```

它只将白名单用量事件写入 `codebuddy-receipt.jsonl`，不会保存 Prompt、回复正文或其他 stdout 帧。stderr 仅保留是否有错误及退出码，不保留原始诊断内容。

### 3.2 必须核验

1. CLI 版本是否确认为 2.181.0。
2. 是否出现 `system / usage_update`。
3. `_meta["codebuddy.ai/turnUsage"]` 是否存在，且 `version=1`、`scope=turn`。
4. 是否收到 `kind=stage`，记录 `session_id`、`requestId`、`stage.id`、`stage.source`、`stage.credits`。
5. 是否收到 `kind=snapshot`，并检查 `total.creditStatus` 与 `total.credits`。
6. 终态 `result._meta["codebuddy.ai/turnUsage"]` 是否与前一 snapshot 一致。
7. 同一 stage 的更新必须覆盖旧值；`delta`、`total`、snapshot 不得再叠加。
8. `result.usage` 是 Token 累计；`total_cost_usd` 是 USD 字段，均不得当作 Credits。
9. 若单轮只产生一个模型 stage，记录其原始 Credits；不为制造多 stage 而调用高成本任务。

### 3.3 CodeBuddy 判定

- **PASS**：版本 2.181.0 输出 stage 与 terminal snapshot，身份完整、Credits 数值可读且终态结果一致。
- **PARTIAL**：输出 usage_update，但 Credits 为 partial / unknown，或只有部分 stage 提供 Credits。
- **UNKNOWN**：没有 usage_update、Credits 字段缺失或 CLI 无法启动。
- **NOT_TARGET_VERSION**：实际 CLI 不是 2.181.0。

## 5. IDE 与受管 CLI 的边界验证

本轮探针启动的是受管 CLI Runtime，不代表已经能旁路观察成员任意打开的 IDE 会话。

如果要验证 IDE 原生会话：
1. 保持现有 IDE 会话不变，不通过 SDK / CLI 另起会话。
2. 只检查该 IDE / Host 已公开的本地事件、Hook 或 Runtime callback 是否真实包含 Credits 数值。
3. 如果只有 Session ID、模型名、Token、工具事件而没有 Credits，回执写 `credits_status=unknown`。
4. 不读取账户 Usage 页面，不抓取网络请求，不分析本地账号数据库或私有缓存。
5. 记录 IDE 版本、Host 入口、事件类型和缺失字段名；不记录业务 Prompt 或代码内容。

## 6. 回执格式

每个宿主单独提交一份 JSONL。至少包含：

| 字段 | 要求 |
|---|---|
| `provider` | qoder / codebuddy |
| `ide_version` / `cli_version` | 分开记录 |
| `runtime_entry` | sdk_query / stream_json_cli / ide_hook |
| `runtime_version` | SDK 包版本或实际 CLI 版本 |
| `session_id` | 可脱敏但同一回执内保持稳定 |
| `request_id` / `message_id` / `stage_id` | 宿主原生 ID；不存在就 null |
| `metric` / `unit` | credits_consumed / qoder_credit 或 codebuddy_credit |
| `value` | 数字或 null；禁止把缺失写成 0 |
| `scope` | model_request / turn_stage / turn_snapshot / session_snapshot |
| `credit_status` | known / partial / unknown |
| `run_id` | 本轮探针 Run 标识 |
| `exit_code` | Runtime 退出码 |
| `observed_at` | UTC 时间 |
| `evidence_file_sha256` | 原始脱敏回执文件摘要 |

另提交 `environment.txt`、`npm ls` 输出（Qoder）和回执文件 SHA-256。不要提交 access token、API Key、账号邮箱、完整 CLI 环境变量、Prompt、回复正文、工具参数或源代码。

## 7. 通过标准与下一步

4.1.2 不以“命令运行成功”为通过。必须拿到真实 Runtime stdout / SDK 消息、原生身份、Credits 字段及其 scope。

- 两个宿主都 PASS：进入 Run 归属、重连回放和重复事件端到端验证。
- 任一宿主 PARTIAL / UNKNOWN：将对应字段能力标记为版本级缺口；账本保留 unknown，不做猜测。
- SDK 启动版本与用户声明版本不一致：单独记录，不混入目标版本结果。
- 本机探针通过只证明受管 CLI 入口；IDE 原生入口必须另有独立证据。

## 8. 本机 Mac 实测记录（2026-11-15）

测试代码固定为研究分支提交 `2bf9322e721390b537d6a7ba5d617d0c169a6d7e`。环境为 macOS 15.3.2，采集环境报告的 Darwin 架构为 x86_64，Node 24.15.0、npm 11.12.1。Qoder SDK 实装版本为 1.0.59，通过 `QODERCLI_PATH` 显式指定已核对为 1.1.88 的本机 qodercli。Copilot 使用本机 CLI JSON 事件流及原生 `--usage-output-file`，未另装 SDK。

| Runtime | 判定 | 真实观察 |
|---|---|---|
| Qoder / qodercli 1.1.88 | PARTIAL | 无 Assistant 用量事件；收到一份带 Session、结果事件 ID 与 Run 绑定的累计快照，原生值为 0。请求级 Credits 保持 null / unknown。SDK 180 秒未结束后由采集器终止，退出记录为 -15。 |
| CodeBuddy CLI 2.181.0 | PASS | 一条 Stage 为 0.69 Credits；Turn Snapshot 与 Result Snapshot 均为 0.69。Session、Request、Stage 和 Run 标识完整，进程退出 0。 |
| GitHub Copilot CLI 1.0.107 | PARTIAL | 同一 Session 的两次执行分别成功退出。原生累计 totalNanoAiu 从 7,324,050,000 增至 7,637,870,000，连续快照差值为 313,820,000 nano-AIU；totalPremiumRequestCost 从 1 增至 2。原生逐请求 Credits 未直接取得，继续保留 unknown；差值明确记作累计快照计算结果。 |

**重放与缺项。** CodeBuddy 的本次真实回执离线重放三次仍为 0.69。本轮只有一条原生 Stage，实际修订未出现；同 Stage 覆盖更新和缺失 Credits 保留 unknown 的对照来自离线模型测试，13 项定向测试全部通过。Qoder 没有请求级用量事件，请求级重放记为未观察。Copilot 两份原生 checkpoint 重放三次仍只保留两个检查点，最新累计量保持 7,637,870,000；原生字段缺失时保留 null，显式的 0 单独保留。

**Copilot 标识观察。** 恢复 Session 后，第二次执行的原生 turnId 再次为 `0`，两次采用不同 Run 和原生事件 ID。第二次另取得 interactionId 与 apiCallId，原生 result 确认了 Session ID。首次投影未保留调用 ID，该采集缺项在验证明细中单列。归集按原生事件及执行绑定区分，避免仅以 Session + turnId 合并两次工作。nano-AIU、Premium Request 计量与 Token 分别保留原生单位。

**归档材料。** 环境信息、三份 JSONL 回执、原生用量的白名单投影、进程状态、Qoder package-lock.json、验证结果和 SHA-256 清单均已保存。完整压缩包仅包含这些材料。原生回合与离线重放使用独立记录；本轮没有再次运行 Qoder 或 CodeBuddy 来补 Copilot 数据。

- [完整材料 ZIP](../../../artifacts/topic-04/mac-20261115-0350-with-copilot.zip)
- [验证明细](../../../artifacts/topic-04/mac-20261115-0350/validation.json) · [SHA-256 清单](../../../artifacts/topic-04/mac-20261115-0350/SHA256SUMS.txt)
- [Qoder 回执](../../../artifacts/topic-04/mac-20261115-0350/qoder-receipt.jsonl) · [CodeBuddy 回执](../../../artifacts/topic-04/mac-20261115-0350/codebuddy-receipt.jsonl) · [Copilot 回执](../../../artifacts/topic-04/mac-20261115-0350/copilot-receipt.jsonl)


### 8.1 官方协议字段复核与回执身份更正

对照 2026-11-15 可访问的官方协议文档，补充以下结论：

**Qoder。** 官方 TypeScript SDK 类型定义中，Assistant 消息的 `message.message.usage.credits`、`original_credits`、`billable` 是可选的单次模型请求字段；Result 的 `total_credits` 与 `modelUsage[model].credits` 是当前 CLI Session 累计值。顶层 `request_id` 默认不暴露，需在 SDK options.env 中设置 `QODER_EXPOSE_REQUEST_ID='true'`。首轮探针没有启用该选项，并把 `message.uuid` 写入回执的 `request_id` 列；这是投影字段误命名，不是原生 request_id。首轮应解释为：SDK 消息事件 UUID 已观察，原生 request_id 未观察，Assistant 请求级 Credits 未观察。现存 JSONL 作为原始归档保留，不追改原始回执或其 SHA-256。已在提交 `6c5b34a` 修正探针：启用 `QODER_EXPOSE_REQUEST_ID=true`，分开输出 `event_id=message.uuid` 与 `request_id=message.request_id ?? null`。修正版已在目标 Mac 重新执行，新回执的 request_id 仍为 null、请求级 Credits 仍未观察，具体结果见第 8.2 节。

**CodeBuddy。** 官方 v2.181.0 Release Notes 明确说明 stream-JSON per-turn usage 完善并提供稳定 Stage identity。官方协议明确：frame `uuid` 是投递身份；`requestId` 是用户 Turn 身份；`stage.id` 是计量 Stage 稳定身份；同一 Stage 后续修订覆盖原值；Turn snapshot 与 Result 内 `turnUsage` 是同一份快照。真实 0.69 Stage 与两份 0.69 snapshot 一致，符合该口径。

**GitHub Copilot。** 官方 SDK 文档将 `assistant.usage` 定义为单次 API 调用 Token 与 premium multiplier，将 `session.usage_checkpoint.totalNanoAiu` / `session.usage.getMetrics` 定义为 Session 累计 AI credit。当前 CLI 实测只取得累计 checkpoint，没有直接的逐请求 nano-AIU。两个独立 Run 在同一 Session 中都观察到 `turnId=0`，所以 turnId 不能单独作为全局 Turn 唯一键；第二次的 `interactionId` / `apiCallId` 可作更细关联，但第一次缺少这些投影字段。

**归档环境差异。** 早先本节将架构写为 arm64，与归档 `environment.txt` 的 `Darwin 24.3.0 x86_64` 不一致；现按实际采集输出修正为 x86_64（仅陈述采集环境报告，不推断物理 CPU 架构）。

官方资料：[Qoder Cost and usage](https://docs.qoder.com/cli/sdk/cost-usage) · [Qoder TypeScript references](https://docs.qoder.com/cli/sdk/references-typescript) · [CodeBuddy v2.181.0 Release Notes](https://www.codebuddy.cn/docs/cli/release-notes/v2.181.0) · [CodeBuddy Stream-JSON usage_update](https://www.codebuddy.cn/docs/cli/stream-json-turn-usage) · [Copilot Usage and billing](https://docs.github.com/en/copilot/how-tos/copilot-sdk/features/usage-and-billing) · [Copilot Streaming events](https://docs.github.com/en/copilot/how-tos/copilot-sdk/features/streaming-events)。

### 8.2 Qoder 修正版探针的 Mac 重跑（2026-11-15）

使用提交 `a99d9df5080d4a1e28f0f51be27ada550db15f69` 的探针副本，复制后逐字节核对源码。qoder 与独立 qodercli 均为 1.1.88，SDK 保持 1.0.59；继续通过 `QODERCLI_PATH` 选择本机 CLI，并在 SDK options.env 启用 `QODER_EXPOSE_REQUEST_ID=true`。本轮采用独立临时目录、新 Run 标识和新 Session，未重跑其他宿主。

| 检查 | 新回执结果 |
|---|---|
| 身份映射 | event_id 有值，request_id 为 null；两字段分开保存 |
| 请求级用量 | Assistant 事件 0 条，请求 Credits 为 null / unknown |
| Session 快照 | Result 事件 1 条，原生 total_credits 为 0，单独记为 Session 累计快照 |
| 结束状态 | 探针输出 incomplete，assistantCount=0、resultCount=1；Node 进程 180 秒未退出，由采集器终止，退出码 -15 |
| 重放 | 新快照按 event_id 离线重放三次，唯一事件数为 1；请求级重放仍为未观察 |
| 总判定 | PARTIAL：已核对字段映射修复，原生请求身份与请求级 Credits 仍未取得 |

新回执 SHA-256 为 `581cefbb868896d47bd15efcdcd429d7416d1274e9a4d0754dc9e3dcae1168c3`。首轮原始回执仍为 `26f33310429c2ee3ca9ca204456f8cfa9dbf56fe26c87a26976b95bed24f46c4`，已与原归档逐字节核对。stderr 只保留出现标志及探针自身的白名单 incomplete 计数；原始诊断、Prompt 和模型回复正文未进入材料。

[本轮完整材料 ZIP](../../../artifacts/topic-04/mac-qoder-fixed-20261115-0432.zip) · [新回执](../../../artifacts/topic-04/mac-qoder-fixed-20261115-0432/qoder-receipt.jsonl) · [进程状态](../../../artifacts/topic-04/mac-qoder-fixed-20261115-0432/qoder-process.json) · [验证明细](../../../artifacts/topic-04/mac-qoder-fixed-20261115-0432/validation.json) · [SHA-256 清单](../../../artifacts/topic-04/mac-qoder-fixed-20261115-0432/SHA256SUMS.txt)

### 8.3 Qoder Query 生命周期修正与下一轮验证

官方 SDK 的 Cost and usage 示例在读取完用量后显式调用 `q.close()`；TypeScript References 说明 `query()` 返回可控制的 Query，且 `options.abortController` 可主动结束 Session。8.2 回执在 Result 已到达后仍运行至外部 180 秒超时，当前探针没有关闭 Query，因此进程超时不能作为 Qoder CLI 任务执行失败的证据。官方文档：[Cost and usage](https://docs.qoder.com/cli/sdk/cost-usage) · [TypeScript SDK references](https://docs.qoder.com/cli/sdk/references-typescript)。

已在提交 `3d18c51e6e459b6f7f4ebf609f46a521642781f6` 修正探针：收到 Result 后立即结束事件迭代，并在 `finally` 中调用 `q.close()`。保留 `QODER_EXPOSE_REQUEST_ID=true`，继续分别采集 `request_id` 与 `event_id`。该修正尚未在 Mac 真实执行，因此 8.2 的 PARTIAL 结论仍有效，但超时原因暂定为 `probe_lifecycle_unverified`，不得宣称为 CLI / SDK Runtime 故障。

下一次真实复验只需运行该修正版，不更改 CLI / SDK 版本，不扩大任务权限。判定分支：
- Result 后正常退出，且出现 Assistant message：核对请求级 `usage.credits`、顶层 `request_id`、`event_id`，再做请求回执三次离线重放。
- Result 后正常退出，但仍无 Assistant message：记录为 SDK / CLI 消息流字段缺失或协议兼容问题；请求 Credits 继续 unknown。
- 仍超时：检查 q.close() 是否执行、CLI 子进程是否退出，并保留安全诊断分类；不得只凭外层超时判 Runtime 失败。
- 没有 Result：单独检查初始化、鉴权、请求执行和错误类别；不得将缺失 Credits 解释为 0。