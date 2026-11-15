# Codex 中谁真正调用了订单核验工具

固定宿主为 Codex CLI 0.144.6。成员配置中，项目服务 `project_orders` 和个人服务 `personal_orders` 都提供 `inspect_order`。两者使用本轮独立的本地 stdio 服务进程，工作目录与 Codex 配置临时生成。先从真实 App Server 查看成员有哪些工具，再创建受本次订单契约约束的业务线程。[宿主探针](../../../prototypes/topic-03b/cross-host/codex_tool.py) · [只读核验服务](../../../prototypes/topic-03b/cross-host/order_tool.py)

## 从成员目录到业务线程

1. 测试适配器创建一个只用于盘点的线程，逐页调用 `mcpServerStatus/list`。项目与个人两个服务都出现时，可从各自的 `tools` 找到相同叶名称。Codex 处理带 threadId 的查询时，会取出该线程的 MCP 运行配置，把各个 server 的工具分别返回。这让工作台能核对当前成员和当前线程各自实际可用的能力。[读取线程的 MCP 配置](https://github.com/openai/codex/blob/5d1fbf26c43abc65a203928b2e31561cb039e06d/codex-rs/app-server/src/request_processors/mcp_processor.rs#L233-L253) · [按服务返回原生工具记录](https://github.com/openai/codex/blob/5d1fbf26c43abc65a203928b2e31561cb039e06d/codex-rs/app-server/src/request_processors/mcp_processor.rs#L359-L369)
2. 实验先核对指定服务、工具名、声明的参数结构，再用 `thread/start.config` 创建业务线程，明确禁用个人服务，仅启用项目服务的 `inspect_order`。此线程回读显示项目中有该工具，个人服务的工具表为空。两个实际模型请求的 MCP 工具定义也都只出现 `mcp__project_orders` 下的 `inspect_order`。Codex 自带的其他工具单独存在，最终回读的回合项目只有用户输入、一次项目 MCP 调用和回复。[线程配置入口](https://github.com/openai/codex/blob/5d1fbf26c43abc65a203928b2e31561cb039e06d/codex-rs/app-server-protocol/src/protocol/v2/thread.rs#L74-L95)
3. 工作回合第一次发往本机 Responses 端点时，测试模型要求调用项目命名空间的工具，参数只有已绑定候选。Codex 的 MCP handler 使用已解析工具绑定的服务名与工具名，加上模型提供的参数、宿主调用 ID 执行调用。实际核验读取获准工作簿，核对 A2、A3。工具服务根据调度端签发的身份复核成员、Runtime、领取代次、候选和当前许可。[宿主分派工具调用](https://github.com/openai/codex/blob/5d1fbf26c43abc65a203928b2e31561cb039e06d/codex-rs/core/src/tools/handlers/mcp.rs#L121-L162)
4. 工具返回后，端点收到同一回合的第二次请求，其中包含上一条工具调用及相同 call_id 的 `function_call_output`。探针解析宿主包装，逐字核对 MCP 正文和业务 JSON；再比对原生完成通知、`thread/read` 和服务账本。回环模型输出按固定顺序生成。工具的进程、文件读取、协议消息和回流由真实运行提供。[回合原生成功与失败记录](https://github.com/openai/codex/blob/5d1fbf26c43abc65a203928b2e31561cb039e06d/codex-rs/core/src/mcp_tool_call.rs#L915-L950)

## 订单对照

| 条件 | 原生回合和模型请求 | 业务证据 |
|---|---|---|
| 两个服务都有同名工具，C2 合约有效 | 业务线程只向模型提供项目 MCP 工具，同一回合前后共 2 次请求，原生调用状态 completed | 服务记一次项目核验，返回 C2 的 A2、A3 通过报告。 |
| 模型主动请求业务线程已屏蔽的个人同名工具 | 端点首次仍要求调用个人命名空间，第二次收到同 call_id 的 `unsupported call`。整轮正常结束，回读只有输入与回复 | 项目和个人两个服务的调用账本均为零。此例验证了工作线程实际限制的 MCP 调用范围。 |
| 同样配置，改为 C1 | 同一回合共 2 次请求，原生工具调用 completed | A2 失败、A3 通过，候选判返工。工具处理成功与业务核验结论各有字段。 |
| 第一次模型请求已到，在返回调用指令前收回授权 | 回合仍正常结束并发出 2 次请求，原生 MCP 项目为 failed。第二次请求实际收到拒绝正文 | 服务只返回拒绝状态和这次回执编号，保存拒绝事件，未读取工作簿。 |
| 只有个人同名工具 | 盘点成功，未启动业务回合，0 次模型请求 | 工具服务没有收到业务调用。 |
| 项目同名工具仍存在，声明的参数与约定不同 | 原生盘点读到实际 inputSchema，业务回合和模型请求均为 0 | 普通同名工具及参数漂移分别有可追溯的停工原因。 |

另外，若成员配置把项目别名本身绑定到另一启动目标，统一派发器先对照已签发的项目服务启动记录，整项在进入宿主前停止。这个对照定位在平台的绑定检查。

本例的 MCP 返回含只读标注，宿主保持 `approvalPolicy=on-request`。Codex 在认定该类 MCP 操作是否提示成员确认时会读取这项标注；服务在每次实际调用时另查任务身份。日常成员配置中的其他 Hook、插件、工具和远端认证需要按相应接入方式采证。[Codex 对只读标注的处理](https://github.com/openai/codex/blob/5d1fbf26c43abc65a203928b2e31561cb039e06d/codex-rs/core/src/mcp_tool_call.rs#L2163-L2180)

## 复跑

从本仓库根目录运行统一订单实验，使用 Python 3.11+、Git、XlsxWriter 3.2.9、openpyxl 3.1.5，以及 Codex CLI 0.144.6 和 Claude Code 2.1.325。主入口生成成员工具配置、真实 XLSX、只读任务授权和回执；CLI 参数指定两个可执行文件。[跨宿主订单入口](../../../prototypes/topic-03b/cross-host/order_handoff.py)

```bash
work=$(mktemp -d)
python3 prototypes/topic-03b/cross-host/order_handoff.py "$work/results" \
  --codex /absolute/path/to/codex --claude /absolute/path/to/claude
```
