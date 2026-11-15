# Claude Code 如何在两项同名工具里执行订单核验

本次使用官方 Python Agent SDK 0.2.182 随包的 Claude Code 2.1.325，运行真实 CLI、JSON 控制协议、stdio MCP、工具 Hooks 和受控模型端点。模型端点固定生成一条工具请求和一条最终确认，便于观察宿主是否真的按选择调用。工具服务读取 C2 的真实 XLSX，依据固定 D2 核验器生成结果。[版本绑定](https://github.com/anthropics/claude-agent-sdk-python/blob/4720d367f7db9d5df8a166c74d7f36a538ac8c34/src/claude_agent_sdk/_cli_version.py#L1-L3) · [宿主探针](../../../prototypes/topic-03b/cross-host/claude_tool.py) · [订单工具](../../../prototypes/topic-03b/cross-host/order_tool.py)

## 先问宿主连上了谁

项目给出的服务名是 `project_orders`，成员已有的服务名是 `personal_orders`，两边都发布 `inspect_order`。本例还在成员工作目录的 `.mcp.json` 把同名项目别名指向个人服务。适配器以 `--strict-mcp-config` 加载本次选中的配置文件，保留两项独立服务做对照。Claude 实际回报 `project_orders` 的配置范围为 `dynamic`，其 stdio 命令和参数与项目签发的启动目标一致，服务握手名称为 `orders/inspect-workbook@2`。宿主同时连上独立的个人服务。这个情形验证的是严格配置入口。普通成员用自己的桌面配置直接启动 Claude 时，仍需按该入口的实际能力取证。[外部服务配置](https://github.com/anthropics/claude-agent-sdk-python/blob/4720d367f7db9d5df8a166c74d7f36a538ac8c34/src/claude_agent_sdk/_internal/transport/subprocess_cli.py#L619-L650)

控制协议先执行 `initialize`，再读取 `mcp_status`。服务状态回报包含服务名、握手信息、配置来源、启动目标及已发现的工具名。该版本实测的工具条目只含名称与注解。调用形参结构可以从 MCP 的 `tools/list` 取回，并与模型首包中该工具的 `input_schema` 各自核对。SDK 在这些位置保留不同信息，适配器据此分别记录“服务已连接”“某一工具可发现”“本轮可用的工具符合工作契约”。[控制请求](https://github.com/anthropics/claude-agent-sdk-python/blob/4720d367f7db9d5df8a166c74d7f36a538ac8c34/src/claude_agent_sdk/_internal/query.py#L813-L815) · [服务状态与工具条目](https://github.com/anthropics/claude-agent-sdk-python/blob/4720d367f7db9d5df8a166c74d7f36a538ac8c34/src/claude_agent_sdk/types.py#L969-L1015)

## 四个实际对照

| 场景 | 模型请求 | 实际服务调用与宿主结果 |
|---|---:|---|
| 项目及个人服务均已连接，调用项目工具 | 2 | 控制面发现两项工具，首个 Messages 请求只列出项目限定名。第一个响应提出 `tool_use`，真实项目服务读取工作簿返回 C2 的 A2、A3 均通过。宿主产生 `PreToolUse` 和 `PostToolUse`。下一模型请求收到同一 ID 的 `tool_result`。 |
| 同样的环境，模型故意点名个人工具 | 2 | 宿主返回 `No such tool available`。两边服务的调用账本都没有新增记录，工具前后 Hook 均无记录。模型在第二次请求中收到宿主拒绝。 |
| 工作目录保留把项目别名指向个人服务的配置，本次签发清单只剩个人服务 | 0 | 原生控制面仅见个人工具，适配器在发送工作指令前返回缺项。没有订单核验调用。 |
| 首个 Messages 请求已看到项目工具，工具执行前撤回本轮授权 | 2 | 项目服务收到一次调用。其授权账本返回 `denied` 和新回执 ID，省去工作簿检查和报告内容。宿主产生 `PreToolUse`、`PostToolUseFailure`，第二次请求收到相同拒绝结果。 |

工作进程显式允许项目限定名、显式禁用个人限定名，并关闭权限询问。两者的连接仍可在原生控制面读取。第二个实验专门让受控模型发出被禁的名称，用服务是否真的收到 `tools/call` 证实宿主处置。项目执行权另由工具服务在每次调用时查询，撤权实验由此发生在已发现工具和实际读取候选之间。[允许与禁用参数](https://github.com/anthropics/claude-agent-sdk-python/blob/4720d367f7db9d5df8a166c74d7f36a538ac8c34/src/claude_agent_sdk/_internal/transport/subprocess_cli.py#L552-L566) · [前后置工具事件](https://github.com/anthropics/claude-agent-sdk-python/blob/4720d367f7db9d5df8a166c74d7f36a538ac8c34/src/claude_agent_sdk/types.py#L350-L381)

一次外部工作 Run 在本例产生一个独立 Claude 会话、一个用户 prompt 和两次模型请求。工作开始与结束 Hook 的 `prompt_id` 相同，工具调用与两个对应的宿主输出帧、模型后续请求通过 `tool_use_id` 关联。模型输入可能在工具内容后加入独立的系统提醒；探针核对真实结果正文摘要及其在 `tool_result` 内的位置。项目服务的独立回执 ID 还可与审计行比对。这个实验证明指定宿主和服务的交付及访问过程。外部模型自由挑选工具的成功率、持久使用中的真实成员桌面环境和正式租户安装条件留作现场验证。

## 复跑

主入口会准备订单候选和每个受托运行的临时配置，复跑两种宿主之间的接续。API 流量由本机端点接收，服务配置、授权凭据与未筛选请求留在本地临时目录。[订单总入口](../../../prototypes/topic-03b/cross-host/order_handoff.py)

Linux x86-64 的独立环境可从固定 SDK 发布包装入 CLI，核对二进制后传给主入口。

```bash
work=$(mktemp -d)
python3 -m pip install --only-binary=:all: --no-deps --target "$work/claude-sdk" claude-agent-sdk==0.2.182
claude="$work/claude-sdk/claude_agent_sdk/_bundled/claude"
echo "0dc4f4a9a165fc60746d7ae8489712e5fc352f1e7ad4eb22e7141bd0812eb0cf  $claude" | sha256sum -c -
"$claude" --version
```
