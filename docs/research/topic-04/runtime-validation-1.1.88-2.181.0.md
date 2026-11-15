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
node prototypes/topic-04/qoder-sdk-runtime-probe.mjs > qoder-receipt.jsonl
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
node prototypes/topic-04/codebuddy-stream-runtime-probe.mjs
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

