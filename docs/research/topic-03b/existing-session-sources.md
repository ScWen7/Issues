# 成员原会话能提供哪些依据

订单节点需要同一份 D2 契约、C2 候选和项目核验工具。成员已在自己的终端工作时，能看到历史、能向正在运行的宿主发指令、获准为当前节点签发调用，分别需要依据。本页核对固定版本的源码和上游测试。跨机结果另见[两台运行机的核验记录](cross-host-handoff.md)。

## Codex 0.144.6

- **接回原线程。** 默认 stdio 通道连接自己启动的进程。该版本还提供本机 Unix socket，原宿主须已提供可用通道。向同一 App Server 提交 `thread/resume` 后，服务先在自己的线程管理器查找已加载线程，另有从存储恢复的分支。若原客户端仍订阅该线程，重新加入时请求的模型、提供方等覆盖项与活动配置不符，宿主记警告并沿用活动配置。只有无订阅者、空闲且未运行时才尝试关闭并冷恢复。适配器应记录实际走的入口和响应，再决定能否在原线程开始订单回合。[官方传输说明](https://github.com/openai/codex/blob/5d1fbf26c43abc65a203928b2e31561cb039e06d/codex-rs/app-server/README.md#L24-L42) · [已加载线程与存储恢复](https://github.com/openai/codex/blob/5d1fbf26c43abc65a203928b2e31561cb039e06d/codex-rs/app-server/src/request_processors/thread_processor.rs#L3024-L3064) · [模型和提供方对照](https://github.com/openai/codex/blob/5d1fbf26c43abc65a203928b2e31561cb039e06d/codex-rs/app-server/src/request_processors/thread_processor.rs#L26-L48) · [覆盖项在何种条件下生效](https://github.com/openai/codex/blob/5d1fbf26c43abc65a203928b2e31561cb039e06d/codex-rs/app-server/src/request_processors/thread_processor.rs#L3081-L3123)
- **当前配置与实际输入。** `config/read` 可以按工作目录返回配置字段来源和可选的配置层。查询 MCP 状态时传 `threadId`，宿主使用该线程的运行配置和上下文。两种读数分别回答“配置来自哪里”和“在这个线程发现什么”。要判定目标回合使用哪个模型、收到哪个工具定义，仍需本轮可观察的请求或响应；仅有配置时保留配置证据的范围。[字段来源](https://github.com/openai/codex/blob/5d1fbf26c43abc65a203928b2e31561cb039e06d/codex-rs/app-server-protocol/src/protocol/v2/config.rs#L350-L369) · [按线程取得 MCP 运行环境](https://github.com/openai/codex/blob/5d1fbf26c43abc65a203928b2e31561cb039e06d/codex-rs/app-server/src/request_processors/mcp_processor.rs#L234-L253)
- **Hook 的效果。** 宿主把 Hook 的来源、内容摘要、启用和信任状态写入清单，再按启用及信任策略挑选实际处理器。前置 Hook 能阻止调用或改参数；多个前置 Hook 改参数时按最后完成的处理器取值。后置命令事件带线程、回合、模型、实际工具名、工具调用 ID、输入和工具响应。平台可以用这些标识核对 Hook 和服务回执，接收结果时再检查候选、访问权和当前派发。[登记与选用](https://github.com/openai/codex/blob/5d1fbf26c43abc65a203928b2e31561cb039e06d/codex-rs/hooks/src/engine/discovery.rs#L506-L536) · [前置决定](https://github.com/openai/codex/blob/5d1fbf26c43abc65a203928b2e31561cb039e06d/codex-rs/hooks/src/events/pre_tool_use.rs#L38-L44) · [多次改写](https://github.com/openai/codex/blob/5d1fbf26c43abc65a203928b2e31561cb039e06d/codex-rs/hooks/src/events/pre_tool_use.rs#L144-L162) · [后置事件实际输入](https://github.com/openai/codex/blob/5d1fbf26c43abc65a203928b2e31561cb039e06d/codex-rs/hooks/src/events/post_tool_use.rs#L145-L161)

## Claude Code 2.1.325

公开源码为绑定这一版 CLI 的 Python Agent SDK 0.2.182。以下区分 SDK 如何启动和控制子进程、CLI 实际回报，以及已有成员终端是否给平台提供同一个控制通道。[CLI 版本](https://github.com/anthropics/claude-agent-sdk-python/blob/4720d367f7db9d5df8a166c74d7f36a538ac8c34/src/claude_agent_sdk/_cli_version.py#L1-L3)

- **恢复或观测。** SDK 的普通 subprocess transport 自己开子进程和管道，并可传入 `--resume`。读取历史则从 JSONL 的父消息链重建对话，保留并行工具的调用和返回。持有会话 ID 可以按授权读取持久历史或恢复对话。要向一个正在运行的成员终端派发，还需该终端提供已授权的控制入口。通过新进程恢复时，记录该进程及新的执行段；原会话历史含接收者已失权的内容时，使用新会话只交付当前可读材料。[子进程与管道](https://github.com/anthropics/claude-agent-sdk-python/blob/4720d367f7db9d5df8a166c74d7f36a538ac8c34/src/claude_agent_sdk/_internal/transport/subprocess_cli.py#L828-L840) · [恢复参数](https://github.com/anthropics/claude-agent-sdk-python/blob/4720d367f7db9d5df8a166c74d7f36a538ac8c34/src/claude_agent_sdk/_internal/transport/subprocess_cli.py#L590-L600) · [历史读取](https://github.com/anthropics/claude-agent-sdk-python/blob/4720d367f7db9d5df8a166c74d7f36a538ac8c34/src/claude_agent_sdk/_internal/sessions.py#L1284-L1306)
- **模型与来源。** SDK 的 setting_sources 描述用户、项目、本地配置，以及默认加载或显式隔离方式。`mcp_status` 的 scope、config、握手信息为可选项，它们描述连接来源；服务工具条目只有名称、描述和注解等字段。调用控制协议的 `set_model` 是变更指令。宿主解析助手响应时单独读取该条消息的 model。绑定工作契约时保存要求、实际观测值和来源，允许字段未知。回环端点的 model 只能证明该测试请求或响应中使用的标识。[设置来源](https://github.com/anthropics/claude-agent-sdk-python/blob/4720d367f7db9d5df8a166c74d7f36a538ac8c34/src/claude_agent_sdk/types.py#L2721-L2731) · [MCP 状态字段](https://github.com/anthropics/claude-agent-sdk-python/blob/4720d367f7db9d5df8a166c74d7f36a538ac8c34/src/claude_agent_sdk/types.py#L969-L1015) · [模型切换请求](https://github.com/anthropics/claude-agent-sdk-python/blob/4720d367f7db9d5df8a166c74d7f36a538ac8c34/src/claude_agent_sdk/_internal/query.py#L834-L841) · [响应模型](https://github.com/anthropics/claude-agent-sdk-python/blob/4720d367f7db9d5df8a166c74d7f36a538ac8c34/src/claude_agent_sdk/_internal/message_parser.py#L209-L221)
- **Hook 与工具返回。** Hook 带 session_id 和可能存在的 prompt_id，工具前置、后置、失败事件再带 tool_use_id。SDK 前置回调允许改输入或给出权限决定，后置回调允许替换发给模型的 MCP 输出。即使服务完成读取，后置 Hook 仍可能改变模型取得的正文。因此订单回执应分别记录服务返回与后续模型输入的摘要。有差异时保留两份观察及来源，再按原契约核对哪份报告可消费。一个 Hook 回调可以只产生记录；如果它还触发独立外部动作，须另取该动作回执再归属。[会话与 prompt](https://github.com/anthropics/claude-agent-sdk-python/blob/4720d367f7db9d5df8a166c74d7f36a538ac8c34/src/claude_agent_sdk/types.py#L309-L322) · [工具事件](https://github.com/anthropics/claude-agent-sdk-python/blob/4720d367f7db9d5df8a166c74d7f36a538ac8c34/src/claude_agent_sdk/types.py#L350-L380) · [改写输入或输出](https://github.com/anthropics/claude-agent-sdk-python/blob/4720d367f7db9d5df8a166c74d7f36a538ac8c34/src/claude_agent_sdk/types.py#L513-L538)

## 对照 3B 的设计范围

| 设计输入 | 现有依据与收口判断 |
|---|---|
| Harness、Role、Skill、Rules、Principles、Playbook 与发布分发 | 订单开发和核验已经使用分角色组合、固定发布、冲突处置和具名交付。原则按其发布范围说明效力；需要强制核验的条款须指明业务依据与验收项。模型配置可以发布可选模型、端点和协议，凭据留在执行环境。TeamAI 的实际用例覆盖协议分组、默认模型和不兼容声明。模型使用、Hook 作用及 MCP 来源需看本轮宿主回执。[角色组合实测](role-composition.md) · [原则在能力中的位置](composition-teamai.md) · [模型声明与凭据占位](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/models/profile.ts#L67-L82) · [模型路由用例](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/__tests__/model-profile.test.ts#L638-L705) |
| Project Wiki、事实、历史决定、Learnings、代码图与知识贡献 | 项目章节已验证来源、版本、权限、角色选段和派生发布。TeamAI 的代码 Wiki、目录和图检索已查到固定源码及范围过滤测试。代码关系作为可选证据时，需要保留仓库、提交、位置、关联依据和当前读权。订单现场以私有代码图参与检索、仓库换版或失权后如何影响结果，仍属于接入验收。[订单知识与贡献](project-knowledge.md) · [代码图范围过滤与用例](knowledge-sources.md) |
| 上下文装配、SOP、验收与指向后续专题的证据 | 当前节点固定 D2、候选和必需工具，沿用原 Issue、Run 与结果消费。已有阶段支持版本变化、材料超额、权限缩小、新宿主独立核验和报告晚到。原宿主接续还应明确原线程控制权、实际回合和 Hook 改动后取得的结果。真实组织账号、成员 IDE 产品入口及供应商计费分别按对应现场条件验证。[项目设计](../../architecture/03b-capability-governance.md) · [3A 按入口区分的能力](../../architecture/execution-capabilities.md) |

宿主工具调用、实际模型输入和可复用会话的证据范围见[原会话实验](existing-session.md)。

## 本轮独立复核

在上述固定 TeamAI 与 Anthropic SDK 版本分别运行，TeamAI 4 项模型路由测试通过，另外 26 项按名称过滤。SDK 6 项 Hook 消息解析及类型测试通过，另外 157 项按名称过滤。它们覆盖协议表示与配置选择；实际成员宿主行为以对应回合、服务和节点回执为准。

```bash
# Tencent/teamai-cli
node node_modules/vitest/vitest.mjs run --pool=threads --maxWorkers=1 --no-file-parallelism \
  src/__tests__/model-profile.test.ts \
  -t 'resolves model groups|puts a chosen default model|makes one three-protocol model|rejects.*(fields|groups) and repeated model IDs'

# anthropics/claude-agent-sdk-python
python -m pytest -q tests/test_types.py tests/test_message_parser.py \
  -k 'base_hook_input_prompt_id_and_effort or mcp_status_response_wraps_servers or parse_hook_event_message'
```
