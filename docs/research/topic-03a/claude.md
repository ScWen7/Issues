# Claude Code 的本地接入、分段与计量

研究基线为官方 Python Agent SDK 0.2.182，固定提交 `4720d367f7db9d5df8a166c74d7f36a538ac8c34`，以及该版本发布包内的 Claude Code 2.1.325。实现追到子进程参数拼装、控制协议回调、消息解析、会话主链和子代理历史读取。CLI 的行为另用发布二进制实跑。官方在线协议文档核对日期为 2026-11-15（北京时间）。[SDK 版本](https://github.com/anthropics/claude-agent-sdk-python/blob/4720d367f7db9d5df8a166c74d7f36a538ac8c34/pyproject.toml#L5-L12) · [绑定的 CLI 版本](https://github.com/anthropics/claude-agent-sdk-python/blob/4720d367f7db9d5df8a166c74d7f36a538ac8c34/src/claude_agent_sdk/_cli_version.py#L1-L3)

## 三个入口及其作用

| 工作入口 | 宿主怎样提供数据 | AgentPlatform 的使用方式 |
|---|---|---|
| 中心派发或成员从平台入口启动 | SDK 默认启动本地 Claude CLI，使用双向 stream-json。启动时注册 hook 回调，SDK 在控制通道内分派，消息流返回 assistant、工具调用、工具结果和 result。 | 创建或接续已分配的 Run，记录输入 UUID、会话 ID 和结果。发送下一条输入、执行工具、修改权限沿用执行契约与宿主原有授权。 |
| 成员在自己的 Claude Code 里选择 Issue | 配置生效的 Hooks 接收本次宿主事件。UserPromptSubmit 提供用户提交的文本，工具前后事件提供调用 ID，Stop 含最后一条助手文本并可带仍在运行的后台任务。可选 OpenTelemetry 导出提供请求级用量。 | 本地选择 Issue 和共享类别后，从选定的 prompt 开始观察。钩子只记录授权选中的事实，正常返回；向模型注入说明、改变工具参数和终止执行是独立操作。缺失的开始、停止及遥测分别记录覆盖情况。 |
| 结束后关联 | `get_session_messages(session_id, directory=...)` 解析 JSONL，沿 `parentUuid` 重建当前对话主链、补回并行工具调用/结果，并筛出可见消息。子代理使用独立读取接口，父工具 ID 来自元数据，缺失时为空。 | 成员预览并勾选具体消息、工具活动和制品。记录原始宿主 ID、来源和导入时间。项目目录显式传入。压缩摘要标作摘要，筛选出的历史视图不用于证明运行全过程。 |

受控启动通过子进程获取事件，独立终端由宿主主动发回事件，二者拥有不同操作权。2.1.325 的 `claude attach --help` 和 `claude logs --help` 分别说明后台会话的终端连接与近期终端输出。接入层采用 Hooks、OTel 和 SDK 的结构化契约。运行中启用或改动 hook 时，按实际收到的第一个事件登记覆盖起点。[SDK 启动与连接](https://github.com/anthropics/claude-agent-sdk-python/blob/4720d367f7db9d5df8a166c74d7f36a538ac8c34/src/claude_agent_sdk/client.py#L155-L171) · [输出模式](https://github.com/anthropics/claude-agent-sdk-python/blob/4720d367f7db9d5df8a166c74d7f36a538ac8c34/src/claude_agent_sdk/_internal/transport/subprocess_cli.py#L520-L531) · [输入模式](https://github.com/anthropics/claude-agent-sdk-python/blob/4720d367f7db9d5df8a166c74d7f36a538ac8c34/src/claude_agent_sdk/_internal/transport/subprocess_cli.py#L739-L751) · [回调注册](https://github.com/anthropics/claude-agent-sdk-python/blob/4720d367f7db9d5df8a166c74d7f36a538ac8c34/src/claude_agent_sdk/_internal/query.py#L314-L350) · [Hooks](https://code.claude.com/docs/en/hooks) · [配置生效范围](https://code.claude.com/docs/en/settings) · [可见历史](https://github.com/anthropics/claude-agent-sdk-python/blob/4720d367f7db9d5df8a166c74d7f36a538ac8c34/src/claude_agent_sdk/_internal/sessions.py#L1248-L1312) · [子代理及元数据缺失](https://github.com/anthropics/claude-agent-sdk-python/blob/4720d367f7db9d5df8a166c74d7f36a538ac8c34/src/claude_agent_sdk/_internal/sessions.py#L1556-L1585)

## 哪些标识能跨入口关联

| 标识与作用域 | 用法 |
|---|---|
| Session ID | 标识同一段可延续的对话历史。启动与恢复可共用它。一个 Session 可服务多个 Issue。 |
| Hook `prompt_id` 与 OTel `prompt.id` | 关联同一用户提交触发的活动。第一个用户输入前可缺失。主代理/子代理工具事件还保留实际的 `agent_id`。 |
| SDK 输入消息 UUID、结果的 `user_message_uuids` | 受控启动以新的顶级 UUID 标记每条输入，从结果列表确认本轮处理了哪些输入。运行中追加的输入可并入同一轮。列表至多 64 项，旧版本、纯字符串输入及某些错误可能缺失；工作范围切换遇到混合轮先记录共同执行范围与归属待定项。 |
| SDK assistant `uuid`、API `message.id` | 前者可指向同一份持久化消息；后者标识模型响应，同一响应产生多个工具消息时共用一个 `msg_…`。工具结果消息即使 wire role 为 user，也要按内容块和作者来源区分工具输出、成员输入和系统注入。 |
| MessageDisplay `turn_id`、`message_id`、`index` | 将上屏文本分批拼接，`final` 标记该消息展示结束。展示 ID 和 API、落盘消息 ID 属不同空间。只有工具调用、没有可展示文本的回复不触发该事件；只采集展示数据会漏掉工具活动。 |
| `tool_use_id`、`parent_tool_use_id` | 关联同一工具调用的前置、成功或失败和消息结果。子代理另保留 agent ID、父工具 ID；旧历史缺 sidecar 时保留未知关系。 |
| OTel `request_id`、`message.uuid`、`event.sequence` | 在字段可用时，通过 assistant_response 的 request_id 与最终持久化消息 UUID，把 API 请求用量连到会话与 prompt。一个响应可有多条消息。event.sequence 仅在单个 Claude 进程内递增；进程重启从零开始。 |

结果中的 `origin` 说明该轮由哪类输入启动；后台通知或单个结果都可能覆盖后续插入的成员消息。跨观察源的可靠关联依赖同域稳定标识或宿主给出的显式映射。正文相同、时间相近仅供成员核对。原始记录包含多类信息时，逐项选择共享，提示正文、工具参数/输出、模型用量、制品内容分别授权。[Hook 入参及工具事件](https://github.com/anthropics/claude-agent-sdk-python/blob/4720d367f7db9d5df8a166c74d7f36a538ac8c34/src/claude_agent_sdk/types.py#L309-L390) · [助手消息关联](https://github.com/anthropics/claude-agent-sdk-python/blob/4720d367f7db9d5df8a166c74d7f36a538ac8c34/src/claude_agent_sdk/types.py#L1385-L1422) · [结果的合并输入与限制](https://github.com/anthropics/claude-agent-sdk-python/blob/4720d367f7db9d5df8a166c74d7f36a538ac8c34/src/claude_agent_sdk/types.py#L1750-L1786) · [展示 ID 与覆盖范围](https://code.claude.com/docs/en/hooks#messagedisplay-input) · [OTel 关联属性](https://code.claude.com/docs/en/monitoring-usage#event-correlation-attributes)

## 怎样避免重复计费

1. **优先记请求明细。** 获准的 OTel `api_request` 带 request_id 时，以提供方及连接作用域内的请求 ID 去重，记录模型、输入、输出、缓存读写和估价。保留 query_source 以辨认主循环、压缩、子代理等。仅有 SDK 数据时，以 API message ID 对同一步多条 assistant 帧去重。两种 ID 的互认依赖可追溯的关联事件。
2. **把口径写进每笔记录。** streaming-input 的 result.usage 覆盖本轮主代理。total_cost_usd 和 modelUsage 累计计算，还包含子代理。assistant.usage 的输出计数可处于流起始占位状态。按能证明的范围使用请求明细或结果总数，同范围的两者仅对账。
3. **续接与分支记录起始计数。** CLI 2.1.277 起，正常退出后 resume/fork 能继承历史累计金额，新段只归集确定覆盖该段的变化量。/clear、/reset、/new 开启新计数范围，崩溃结尾可能回报零。跨范围、含私有段、起点未知或未取到目标终值时，保留已知主计数和未归属部分。按成员订阅与客户端价表得出的估价，与供应商结算金额分别展示。

例如上游进程两次结果依次为 0.00009、0.00018 美元，如工作范围恰在两轮之间切换，两轮各增加 0.00009；若中间夹着无授权的私人轮，累计变化本身不足以证明新 Issue 应承担整段差额。勾选共享一条消息也不产生新的费用。[Anthropic 成本作用域与版本差异](https://code.claude.com/docs/en/agent-sdk/cost-tracking) · [OTel 请求用量](https://code.claude.com/docs/en/monitoring-usage#api-request-event) · [解析消息与 API ID](https://github.com/anthropics/claude-agent-sdk-python/blob/4720d367f7db9d5df8a166c74d7f36a538ac8c34/src/claude_agent_sdk/_internal/message_parser.py#L177-L223) · [解析结果](https://github.com/anthropics/claude-agent-sdk-python/blob/4720d367f7db9d5df8a166c74d7f36a538ac8c34/src/claude_agent_sdk/_internal/message_parser.py#L311-L342)

## 实跑记录

- 在固定 SDK 源码检出目录执行 `python -m pytest -q tests/test_message_parser.py tests/test_sessions.py`，216 项通过。覆盖消息解析、合并输入 UUID、并行工具历史重建和子代理元数据。除 pytest 依赖弃用提示外无失败。[消息解析测试](https://github.com/anthropics/claude-agent-sdk-python/blob/4720d367f7db9d5df8a166c74d7f36a538ac8c34/tests/test_message_parser.py#L939-L989) · [恢复并行结果](https://github.com/anthropics/claude-agent-sdk-python/blob/4720d367f7db9d5df8a166c74d7f36a538ac8c34/tests/test_sessions.py#L1309-L1340) · [父子关系读取](https://github.com/anthropics/claude-agent-sdk-python/blob/4720d367f7db9d5df8a166c74d7f36a538ac8c34/tests/test_sessions.py#L2240-L2307)
- 本项目离线探测使用真实 CLI、临时项目、回环 Messages SSE 服务和本地 OTLP HTTP/JSON 接收器。运行三次 CLI、四次模拟模型响应，七组断言通过。两次 startup/resume 的 Session 相同，prompt_id 各异；同一层的 hooks 共享 prompt_id；两轮展示消息 ID、SDK 帧 UUID、API message ID 均不同。SDK 帧 UUID 与落盘助手记录成功关联。每轮返回 10 个输入、4 个输出 token，assistant 帧的输出占位均为 0，结果填入 4。新旧两轮的累计估价为 0.00009、0.00018 美元。本地接收器实际收到了四条带不同 request_id 的 api_request，总计 16 个输出 token；startup 与 resume 两轮都通过 assistant_response 的 request_id、prompt.id、message.uuid 对回各自的 hook 与落盘消息，无须上传正文。
- 第三个 CLI 进程使用独立 Session，执行真实 Read 工具并读取临时文件，前置 hook、成功 hook 和结果消息具有同一 tool_use_id。这证明宿主确实读取了该文件。把文件交付到 Issue 还需成员选择并由平台核对候选、内容摘要和可访问性。成员手工说明可作为有署名的报告保留；宿主数据导入保留其来源；平台验明哪些字段便记录哪些事实。模型答案与计量输入来自 fixture，此次只验证本地 OTel 导出、记录关联和 CLI 执行，供应商实际计费及交互式 IDE 接入仍待真机场景。
- 复跑环境为 POSIX、Python 以及官方发布二进制。在仓库根目录可使用临时依赖目录执行以下命令。脚本只用 Python 标准库，创建独立 Claude 配置、模拟凭据和临时材料，完成后自动清理运行数据。

```bash
python -m pip install --no-deps --target /tmp/agentplatform-claude-sdk claude-agent-sdk==0.2.182
python prototypes/topic-03a/claude-local-probe.py /tmp/agentplatform-claude-sdk/claude_agent_sdk/_bundled/claude
```
