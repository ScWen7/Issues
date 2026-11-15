# Codex 已打开线程中的订单回合

Codex CLI 0.144.6 的同一个 App Server 可以同时保留成员连接和平台连接。成员先完成个人回合，再把受凭据保护的回环 WebSocket 提供给平台。平台独立初始化连接并查询已加载线程。无凭据的握手遭到宿主拒绝。测试使用临时配置、合成身份与本地 Responses 端点，宿主实际执行了项目 MCP 并读取三个工作簿。[宿主协议实验](../../../prototypes/topic-03b/cross-host/codex_existing.py) · [两个客户端的连接](../../../prototypes/topic-03b/cross-host/codex_connection.py)

## 原线程能否承接同一项工作

成员客户端在线程打开时向宿主读取配置来源及版本。平台连接后独立读取当前版本，核对模型和项目 MCP 启动配置的来源，再从指定线程取得实际工具目录。`thread/turns/list` 的 `itemsView=notLoaded` 返回回合 ID 和状态，可与成员授权共享的回合集合核对。模型端点的逐请求对照仅在隔离实验中启用，交接回执只保存标记是否出现。[回合读取粒度](https://github.com/openai/codex/blob/5d1fbf26c43abc65a203928b2e31561cb039e06d/codex-rs/app-server/src/request_processors/thread_processor.rs#L4057-L4087) · [模型、审批和沙盒响应字段](https://github.com/openai/codex/blob/5d1fbf26c43abc65a203928b2e31561cb039e06d/codex-rs/app-server-protocol/src/protocol/v2/thread.rs#L170-L202)

| 第二客户端拿到的依据 | 实际承接订单的线程 | 原个人合成标记出现在订单请求及返回后的下一次请求 |
|---|---|---|
| 已共享唯一的旧回合，配置版本一致，线程只发现项目 MCP | 原线程，新业务回合 | 两次均出现 |
| 已撤回旧回合的共享授权 | 新线程 | 两次均未出现 |
| 授权清单外还有一个已完成的成员回合 | 新线程 | 两个个人标记均未出现 |
| 原线程同时开放项目和个人两个同名工具 | 新线程，只开放项目 MCP | 两次均未出现 |
| 缺少原线程打开时的配置版本回执 | 新线程，取得新的启动响应 | 两次均未出现 |

所有订单业务线程都从宿主原生调用、项目服务返回，追到同一回合下一次模型请求中的结果。请求的模型字段为 `gpt-5.1-codex`，提供方是本地测试端点。业务请求里只有项目 MCP 的 `inspect_order`。Codex 另外开放了一些原生工具，实验逐项记录实际名称。订单服务在执行时仍会校验任务凭证。在发现工具后撤回凭证的对照只得到拒绝。本次临时配置的 `hooks/list` 返回零项、零错误、零警告。该版本按工作目录解析 Hook，从当前清单还原旧线程的历史 Hook 配置需要另外的来源。[按工作目录解析 Hook](https://github.com/openai/codex/blob/5d1fbf26c43abc65a203928b2e31561cb039e06d/codex-rs/app-server/src/request_processors/catalog_processor.rs#L595-L653) · [统一订单与接收器入口](../../../prototypes/topic-03b/cross-host/order_existing.py)

## 两个客户端可以在检查与派发之间插入回合

另一个实际线程只运行诊断。平台核对到一个已共享回合后，成员在同一线程中追加一条合成消息，随后平台才发送诊断文本。该诊断的模型输入包含刚刚追加的合成标记。整个对照只有三个文本回合、零订单指令、零 MCP 调用。若成员可继续从终端或 IDE 写入，事先读取历史无法固定下一次模型请求的上下文。在原控制入口能够保证单一写入窗口时可复用。需要排除未共享历史且无法保证该窗口时，原订单节点应进入新的受管线程。本次正例按顺序控制两位客户端的输入。普通成员 IDE 是否公开同一控制通道，取决于现场部署。[双客户端插入回合实验](../../../prototypes/topic-03b/cross-host/codex_existing.py)
