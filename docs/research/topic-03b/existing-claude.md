# 已打开的 Claude Code 会话能否接续订单核验

成员先在 Claude Code 提交一条带随机标记的合成消息，等该轮正常结束，再派发订单。适配器在同一条已连接的控制通道上读取 MCP 状态，核对前一轮实际使用的模型、启动配置与成员允许带入新工作的历史。各场景使用 Claude Code 2.1.325、固定返回的本地 Messages 端点、真实 stdio 服务，以及三份 C2 工作簿。当前实测覆盖适配器从启动起就能观察的既有 CLI 会话。对任意已打开的桌面或 IDE 会话，仍需单独验证控制通道、历史覆盖和配置来源。[实验代码](../../../prototypes/topic-03b/cross-host/claude_existing.py) · [订单运行入口](../../../prototypes/topic-03b/cross-host/order_existing.py)

| 派发时的情形 | 订单提示进入哪个会话 | 实际核验与结果 |
|---|---|---|
| 旧轮已授权，模型、项目服务和 Hook 设置可核对 | 原 Session，新 prompt ID；两次业务模型请求均保留旧轮标记 | 发现项目和个人同名工具，模型只获得项目工具。项目服务读取三份 XLSX，A2、A3 均通过 |
| 派发前撤回旧轮的历史使用授权 | 原 Session 的业务模型请求为零。新建严格配置的会话，两个业务请求均无旧标记 | 新会话用同一订单契约调用项目服务，旧轮不进入新模型输入 |
| 成员配置多出一个未经此次派发批准的 Hook | 额外的 UserPromptSubmit 命令已在旧轮落下一条本地记录。实际设置摘要与批准配置不同，订单进入新会话 | 额外命令的业务记录为零。新会话的项目工具正常完成核验 |
| 原 Session 可复用，首个订单模型请求后收回该 Run 的工具权限 | 订单仍在原 Session 的新 prompt 中 | 收到 PreToolUse 和 PostToolUseFailure，服务返回 denied 与回执号。第二次请求收到同一拒绝结果，节点消费为零 |
| 已执行的项目工具返回后，PostToolUse 对展示结果增加一个字段 | 独立的受控反例会话 | 服务成功读取 XLSX，原生工具结果和后续模型输入均带有改写。两者的摘要相同，均与服务回执不同。接收方在签发宿主执行证据时拒绝该返回，订单暂未消费 |

## 什么能证明这是原会话的另一段工作

预热轮的原生 system/init 和实际模型请求均报告相同模型。接单前适配器还会通过 mcp_status 复核项目服务的连接范围、启动目标、服务自报身份和工具名。两轮各有自己的 UserPromptSubmit 与 Stop，在同一轮内两者指向相同的 prompt ID。探针分别检查业务首包和带 tool_result 的后续包是否包含旧轮标记。允许复用时，两次命中且工作 prompt ID 不同于旧轮。转入新会话时，两次均未命中，且原会话没有订单模型请求。团队回执只记录 ID、摘要、命中结果与配置来源，这里对历史授权的变更使用实验授予表模拟。[SDK 的控制协议入口](https://github.com/anthropics/claude-agent-sdk-python/blob/4720d367f7db9d5df8a166c74d7f36a538ac8c34/src/claude_agent_sdk/_internal/query.py#L813-L819) · [宿主和模型证据](../../../prototypes/topic-03b/cross-host/claude_existing.py)

本实验能从启动时的明确参数和隔离的配置目录追溯 Hook 来源，随后读取实际配置文件摘要，并以宿主发出的事件确认哪些命令确实运行过。mcp_status 给出连接的服务与工具。若现场仅能读取 MCP 清单，Hook 全集、旧历史的授权和未知命令的副作用仍待确认。[配置加载路径](https://github.com/anthropics/claude-agent-sdk-python/blob/4720d367f7db9d5df8a166c74d7f36a538ac8c34/src/claude_agent_sdk/_internal/transport/subprocess_cli.py#L619-L685)

## 同一个工具调用怎样认账

普通预热只有一次模型请求，核验轮有两次。PreToolUse、PostToolUse 或 PostToolUseFailure 分别给出该工作 prompt 和同一 tool_use_id，对应项目服务账本中的一次调用。审计 Hook 的运行不会增加订单工具调用数。是否实际通过核验，另查服务返回、模型收到的 tool_result、报告摘要以及原节点消费记录。撤权对照中，两个工具 Hook 均真实运行，服务仍在读取工作簿前拒绝了操作。[服务端授权](../../../prototypes/topic-03b/cross-host/order_tool.py) · [接收与节点消费](../../../prototypes/topic-03b/cross-host/order_handoff.py)

改写对照使用 Claude Code 支持的 updatedMCPToolOutput。该命令保留订单报告、原回执 ID 和通过结论，只增加一个合成展示字段。工具服务独立记录原返回的摘要。PostToolUse 的输入与服务原摘要匹配，而宿主输出的 tool_result 和下一次模型请求都匹配改写后的摘要。相同的 Run、调用 ID、回执 ID 和业务结论仍不足以证明模型所见的字节与服务返回一致。沿用原来的结果接收器，摘要差异使这次执行无法取得用于提交的宿主凭据。反例的额外测试命令只在该隔离会话启用。[SDK 的 PostToolUse 输出类型](https://github.com/anthropics/claude-agent-sdk-python/blob/4720d367f7db9d5df8a166c74d7f36a538ac8c34/src/claude_agent_sdk/types.py#L523-L538) · [SDK 回调测试](https://github.com/anthropics/claude-agent-sdk-python/blob/4720d367f7db9d5df8a166c74d7f36a538ac8c34/tests/test_tool_callbacks.py#L867-L879)
