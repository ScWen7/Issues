# Claude Code 的规则加载、运行中更新、Skill 与 MCP 回执

使用官方 Python Agent SDK 0.2.182 随包发布的 Claude Code 2.1.325，在临时项目中跑真实 CLI、真实 Hooks、项目 Skill 和本地 stdio MCP 服务。模拟 Messages 服务接收 CLI 的实际 HTTP 请求，只保存合成标记所属字段。基础组包括 9 个 CLI 进程、11 个用户回合、13 个回环模型请求。另加 Multica 原生文件生成的串联组后，复跑共 10 个进程、12 个回合、14 个模型请求。订单导出规则 D1 只要求订单 ID，D2 增加付款时间。每个版本有仅出现在该规则中的标记，显式补充实验另在输入中携带 D2。[SDK 固定版本](https://github.com/anthropics/claude-agent-sdk-python/blob/4720d367f7db9d5df8a166c74d7f36a538ac8c34/pyproject.toml#L5-L12) · [随包 CLI 版本](https://github.com/anthropics/claude-agent-sdk-python/blob/4720d367f7db9d5df8a166c74d7f36a538ac8c34/src/claude_agent_sdk/_cli_version.py#L1-L3)

## 同一项目文件的四种结果

探针按期望文件字节计算 SHA-256，单独记录目标路径的 InstructionsLoaded、实际请求中合成规则标记的位置以及候选输出的字段。标记以外的真实消息、其他项目配置和成员目录均在实验数据之外。

| 场景 | 磁盘 | 文件加载事件 | 模拟端实际收到的请求 |
|---|---|---|---|
| 新会话开工，期望 D2 | 摘要匹配 D2 | Project / session_start | D2 位于消息内容，D1 缺席 |
| 新会话建立 D1，退出后以同一 Session ID 恢复，恢复前已写 D2 | 先 D1，后与 D2 匹配 | 两次启动各有 Project / session_start | 首次仅 D1。恢复请求同时含历史单元中的 D1 与较新单元中的 D2 |
| 期望 D2、目录实际仍为 D1 | 摘要与期望不同 | 仍有 Project / session_start | 只有 D1。该事件给出文件路径及加载原因，缺少宿主原生内容摘要 |
| 期望 D2、目录无 CLAUDE.md | 文件缺失 | 没有该路径事件 | D1、D2 均缺失 |

宿主的 InstructionsLoaded 提供作用域、文件路径和加载原因。平台可把本地交付摘要、文件变更时间及调用身份与事件对应；若读盘点与加载之间存在变更，应保留内容版本待核对。探针通过模拟端点举证标记进入哪一次请求。生产环境优先收集局部摘要和宿主声明的证据，只在授权的可观测通道上确认请求内容。[InstructionsLoaded 字段](https://code.claude.com/docs/en/hooks#instructionsloaded-input) · [项目指令如何加载](https://code.claude.com/docs/en/memory#how-claude-md-files-load)

### 同一个进程继续开着怎么办

在同一进程、同一 Session 的 stream-json 输入中连续发三轮。第一轮加载 D1。第一轮 result 之后立即把文件改为 D2，第二轮普通输入随即发出。文件摘要匹配 D2，第二轮没有新的文件加载事件，请求只含历史 D1。第三轮直接用当前输入补充 D2，端点在新输入的消息单元读到 D2，过去的 D1 继续保留，仍然没有新的文件加载事件。该实验覆盖立即执行下一轮，其他文件监听延时、交互式客户端和压缩后重载有各自触发条件。

平台面对运行中的决定更新，应记录 D2 从何时生效、采用哪个通道投递，补充输入与原文件分开留证。若当前 Run 已开始可能受影响的工具动作，沿当前控制者决定是否补充、等待或重新执行。直接补充成功时，可给“新输入包含 D2”回执；历史 D1 的存在及其所属回合一并保留。源输入中看见 D2 后仍应验证当前候选是否有实际付款时间以及 A2 权限结果。此次模拟模型始终返回仅含 order_id 的合成列清单，独立字段检查在全部回合均发现缺少 payment_time；模型自主遵循、真实 A2 及真实业务交付另行核验。[SDK 的恢复参数组装](https://github.com/anthropics/claude-agent-sdk-python/blob/4720d367f7db9d5df8a166c74d7f36a538ac8c34/src/claude_agent_sdk/_internal/transport/subprocess_cli.py#L589-L600) · [流式输入](https://github.com/anthropics/claude-agent-sdk-python/blob/4720d367f7db9d5df8a166c74d7f36a538ac8c34/src/claude_agent_sdk/_internal/transport/subprocess_cli.py#L739-L751)

### 串联 Multica 原生文件生成

附加组删除受控项目原有 CLAUDE.md，调用固定版本 Multica 的 `execenv.InjectRuntimeConfig` 将带 D2 标记的 AgentInstructions 写入项目，再启动真实 Claude CLI。探针在这个合成文件上记录 SHA-256，本次为 `55ded205902c995ab41e733f8d4261004b033e7bd751ff33158cb6e8676b5ab0`。目标路径触发 Project / session_start，模型请求的用户消息内容出现 D2，D1 缺席。该组由上游函数实际生成资源，文件记录采用其最终字节的摘要；手工模板预期哈希字段留空。验证范围从 Multica 的材料生成函数到 Claude 的模型请求，队列领取和 Daemon 平台授权另有独立研究。[原生文件生成入口](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/execenv/runtime_config.go#L161-L195) · [目标文件路径](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/execenv/runtime_config.go#L197-L212)

## Skill 的发现与调用

1. 写入临时项目的 `.claude/skills/order-evidence/SKILL.md`，让描述和正文使用不同标记。新会话的模型请求包含描述，正文缺席，也没有 Skill 调用事件。
2. 模拟模型在第一条响应选择该 Skill。真实 CLI 触发 PreToolUse、PostToolUse，同一次工具调用 ID 为 `toolu_order_skill`，工具参数指定 `order-evidence`。之后的模型请求出现正文标记。工具、版本、调用来源和注入时点因而可以分别记录。
3. SDK 的技能设置可以选择可发现的技能并生成工具允许项、配置来源。探针以项目配置来源启用本地 Skill。成员的其他配置来源、生效策略和不同版本要在生产回执中单列。[技能发现及调用](https://code.claude.com/docs/en/skills#skill-content-lifecycle) · [SDK 的配置选择](https://github.com/anthropics/claude-agent-sdk-python/blob/4720d367f7db9d5df8a166c74d7f36a538ac8c34/src/claude_agent_sdk/types.py#L2721-L2749) · [生成有效工具与配置来源](https://github.com/anthropics/claude-agent-sdk-python/blob/4720d367f7db9d5df8a166c74d7f36a538ac8c34/src/claude_agent_sdk/_internal/transport/subprocess_cli.py#L479-L517)

## MCP 配置、连接与调用

探针使用临时 MCP JSON、严格配置和一个只读的本地 stdio 服务。关闭延迟工具发现，以核验模型请求里列出的工具声明；保留该模式作为实验前提。

| 场景 | MCP 服务看到的协议动作 | Claude 侧记录 |
|---|---|---|
| 提供可用服务，模型直接输出 | initialize、tools/list | 模型请求工具清单包含 `mcp__context_fixture__check_order`；没有工具调用及结果 |
| 使用同一配置，模拟模型发起工具调用 | initialize、tools/list、tools/call | 工具的前后 Hook 均给出 `toolu_order_mcp`；工具返回的独有标记进入下一次请求 |

Multica 的 Claude 后端把任务的 MCP 配置写入临时文件并传给 CLI，特定调用可选择严格模式。其 ContextReceipt 构造时列出 MCP 配置名，把已物化 Skill 记录为 file / unverified。文件加载既有探测的 Claude 版本为 2.1.220，此处真实 CLI 为 2.1.325。归入本项目的应是本次独立取得的宿主回执，各阶段分别确认“配置指向目标服务”“发现工具”“实际调用”和“读到结果”。[Multica MCP 配置](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/claude.go#L74-L88) · [严格模式](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/claude.go#L1163-L1184) · [探测版本表](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/context_receipt.go#L93-L125) · [MCP 配置列表](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/context_receipt.go#L151-L165) · [Skill 回执](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/context_receipt.go#L228-L256)

## 复跑

POSIX、Python 3.10+、官方 Claude Code 2.1.325。脚本使用 Python 标准库，创建临时 HOME、项目和只连本机的模拟模型服务。已安装对应 CLI 的机器直接传入绝对路径即可。以下命令以 SDK 发布包装入独立目录。

```bash
python3 -m pip install --no-deps --target /tmp/agentplatform-claude-3a claude-agent-sdk==0.2.182
python3 prototypes/topic-03a/claude-context-probe.py /tmp/agentplatform-claude-3a/claude_agent_sdk/_bundled/claude
```

如已构建本阶段的原生材料生成探针，设置环境变量 `AP_CONTEXT_MATERIALIZER=/absolute/path/to/materialize` 执行同一命令，可追加串联场景。

输出各场景的布尔结果、目标文件 Hook、工具调用 ID、本地 MCP 方法名、版本标记在请求内的位置。请求数组索引受宿主版本和其他消息影响，断言只比较标记属于哪个消息单元、先后次序及是否缺失。
