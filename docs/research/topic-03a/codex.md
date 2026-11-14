# Codex 本地协议与执行分段

本次选择与实测二进制匹配的 `openai/codex@fb036d4ebd89f263d34a1f888c279ce85bb383c6`（`rust-v0.167.0-alpha.4`），并读取研究时的 `main@65a5410f72dac1f4b40862c34ef0a8b71b12834a` 做差异复核。两版的 Exec 用量投影、局部 Item ID 和请求 Hook 定义相同，所查用量重放文件的差异仅涉及测试构造。协议会随版本演进，部署时以目标二进制生成的 Schema 和以下探针结果为准。[实测版本](https://github.com/openai/codex/tree/fb036d4ebd89f263d34a1f888c279ce85bb383c6) · [复核版本](https://github.com/openai/codex/tree/65a5410f72dac1f4b40862c34ef0a8b71b12834a)

## 本地主动接入与事后读取

| 入口 | 已有机制 | 本平台用法 |
|---|---|---|
| 通过工作台、IDE 插件或成员命令启动 | App Server 接受 `initialize → initialized → thread/start → turn/start`，通过连接推送 Turn、消息、工具和用量。客户端还能提交输入、中断和响应审批。 | 成员先选 Issue 和共享范围，本地适配器在请求发出前保存关联。一次启动传递同一平台执行标识。原宿主处理交互，采集端仅发布成员选中的事实。 |
| 成员在既有 Codex 终端 / IDE 工作 | 已启用、已获信任的 Hooks 在原宿主进程的生命周期处接收事件。`UserPromptSubmit` 携带提示和 Turn，`PostToolUse` 携带 Turn、工具名、调用 ID、输入与结果，`Stop` 可含最后一条回答。`Pre/PostModelRequest` 观察单次请求尝试，Post 附完成 / 失败 / 取消状态及可能为空的用量。 | 成员显式关联后在本地收集所选字段。使用支持这些 Hook 的版本，维护安装与信任状态。要逐条补齐消息，按授权读取选定 Turn 的历史。Stop 可继续驱动宿主，单次 Stop 回调先记为观察，Turn 终态另取对应事件。 |
| 恢复已有活动线程 | `thread/resume` 可在同一 App Server 中加入已加载线程，也可恢复存储的线程。加入时会返回快照，可能重发最近用量和待处理审批。 | 主动协作需要被授权使用原来的服务连接并明确控制职责。成员单纯选取历史时使用只读路径。新起的 stdio 服务连接自己的子进程；跨独立终端的实时观察需要原宿主已配置 Hook、共享接入端点或集成。 |
| 事后补录 | `thread/read` 读取存储的元数据；`thread/turns/list` 分页读轮次；支持 Item 分页的存储可用 `thread/items/list` 按 Turn 读条目。旧兼容路径 `includeTurns:true` 可一次读全，`ephemeral` 线程按协议仅在内存保留。 | 本地预览摘要和选定条目，缺失的输出或历史按实际显示。仅提交需要的引用或选中内容，完整本地历史与中心 Issue 分开处理。 |

入口依据见 [OpenAI 官方 App Server 文档](https://learn.chatgpt.com/docs/app-server)、[官方 Hooks 文档](https://learn.chatgpt.com/docs/hooks)、[线程读取实现](https://github.com/openai/codex/blob/fb036d4ebd89f263d34a1f888c279ce85bb383c6/codex-rs/app-server/src/request_processors/thread_processor.rs#L3087-L3123)、[Resume 向当前连接重发用量与审批](https://github.com/openai/codex/blob/fb036d4ebd89f263d34a1f888c279ce85bb383c6/codex-rs/app-server/src/request_processors/thread_lifecycle.rs#L1255-L1287)、[Hook 启用与信任检查](https://github.com/openai/codex/blob/fb036d4ebd89f263d34a1f888c279ce85bb383c6/codex-rs/hooks/src/engine/discovery.rs#L907-L929)、[工具 Hook](https://github.com/openai/codex/blob/fb036d4ebd89f263d34a1f888c279ce85bb383c6/codex-rs/hooks/src/events/post_tool_use.rs#L24-L44)、[模型 Hook 数据结构](https://github.com/openai/codex/blob/fb036d4ebd89f263d34a1f888c279ce85bb383c6/codex-rs/hooks/src/events/model_request.rs#L19-L80)。

## 会话、轮次和条目

App Server 的 `sessionId` 由同一会话树内多个线程共享。具体对话有 `thread.id`；子代理的 `parentThreadId` 和分叉的 `forkedFromId` 表示来源。每次 Turn 有自己的 `id` 和状态，`rootTurnId` 表示工作的祖先；开始、完成和历史条目保留这些层次。普通用户与 Agent 消息、命令执行、文件变化、MCP 调用各自有 Item。命令输出与退出码可缺失，文件变化给出路径与 patch 状态，MCP 参数、成功结果、错误各有来源。选中的报告文件另行取得内容或版本摘要，工具退出成功只支持该命令事实。[线程与来源](https://github.com/openai/codex/blob/fb036d4ebd89f263d34a1f888c279ce85bb383c6/codex-rs/app-server-protocol/src/protocol/v2/thread_data.rs#L205-L226) · [Turn](https://github.com/openai/codex/blob/fb036d4ebd89f263d34a1f888c279ce85bb383c6/codex-rs/app-server-protocol/src/protocol/v2/thread_data.rs#L385-L409) · [Item 类型](https://github.com/openai/codex/blob/fb036d4ebd89f263d34a1f888c279ce85bb383c6/codex-rs/app-server-protocol/src/protocol/v2/item.rs#L299-L418) · [Item 关联字段](https://github.com/openai/codex/blob/fb036d4ebd89f263d34a1f888c279ce85bb383c6/codex-rs/app-server-protocol/src/protocol/v2/item.rs#L1404-L1414)

平台以宿主实例命名空间、`threadId + turnId` 标出具体轮次，以 Item ID 关联消息和工具。一个工作段可以连续覆盖多个 Turn；同一 Turn 中只分享几条消息时，保存被选 Item 范围，用量仍停留在宿主可归因的粒度。Hook 带 `session_id + turn_id`，模型 Hook 还可带 `agent_id`；本地适配器通过显式启动关联或已知线程映射把 Hook 对齐到具体 Thread。旧历史可能在重建时生成隐式 Turn ID，应同时保留原文件版本、稳定位置与定位依据，无法稳定定位的记录等待成员认领。分叉时历史会复制，原 Turn 由来源引用，分叉后的新工作单独归集。[Hook 取值](https://github.com/openai/codex/blob/fb036d4ebd89f263d34a1f888c279ce85bb383c6/codex-rs/core/src/hook_runtime.rs#L1139-L1148) · [历史归因与隐式 ID 的处理](https://github.com/openai/codex/blob/fb036d4ebd89f263d34a1f888c279ce85bb383c6/codex-rs/app-server/src/request_processors/token_usage_replay.rs#L60-L98)

## 用量重放和 CLI 投影

1. App Server 的 `thread/tokenUsage/updated` 携带 Thread、Turn 和 `last / total`。本版本正常回报会将当次使用累加进 total，再保存 last；恢复时又可对当前客户端重发相同快照。仅在同一线程、同一计数范围及连续基线间取差，无法确认前值时保留累计快照。分叉继承的基线、计数重置和历史归因回退需要单独处理。[消息定义](https://github.com/openai/codex/blob/fb036d4ebd89f263d34a1f888c279ce85bb383c6/codex-rs/app-server-protocol/src/protocol/v2/thread.rs#L2008-L2027) · [累计更新](https://github.com/openai/codex/blob/fb036d4ebd89f263d34a1f888c279ce85bb383c6/codex-rs/protocol/src/protocol.rs#L2534-L2565) · [恢复时定向回放](https://github.com/openai/codex/blob/fb036d4ebd89f263d34a1f888c279ce85bb383c6/codex-rs/app-server/src/request_processors/token_usage_replay.rs#L32-L58)
2. `codex exec --json` 输出较简。该版本的 `turn.started` 无 Turn ID，`item_N` 在每次启动时从进程局部计数器生成；`turn.completed.usage` 从最新线程 **total** 投影，缺少快照时返回默认值。成员用 `exec resume` 接续工作，客户端若按字段名把它直接加到上一轮，将重复统计。平台优先采 App Server，在仅有 Exec 日志时使用启动关联、已知基线或历史核对，保留未知与观测零值的区别。[CLI 事件](https://github.com/openai/codex/blob/fb036d4ebd89f263d34a1f888c279ce85bb383c6/codex-rs/exec/src/exec_events.rs#L39-L73) · [局部 ID 与累计用量映射](https://github.com/openai/codex/blob/fb036d4ebd89f263d34a1f888c279ce85bb383c6/codex-rs/exec/src/event_processor_with_jsonl_output.rs#L83-L130) · [CLI 完成输出](https://github.com/openai/codex/blob/fb036d4ebd89f263d34a1f888c279ce85bb383c6/codex-rs/exec/src/event_processor_with_jsonl_output.rs#L512-L538)
3. `PostModelRequest` 的尝试可能有用量，但公开 Hook 输入没有每次请求的 response ID。相同 Turn 内的重试可能产生相同 token 数。Hook 和 App Server 都观察到活动时，二者佐证同一执行，在同一计量区间选择一个来源结算。公开 Hook、内部 Codex Cloud `rawResponse/completed` 和账单属于不同接口。Token 计数、带定价版本的估算、外部确认的金额分别保存。[尝试 Hook 字段](https://github.com/openai/codex/blob/fb036d4ebd89f263d34a1f888c279ce85bb383c6/codex-rs/hooks/src/events/model_request.rs#L65-L80) · [内部通知的适用范围](https://github.com/openai/codex/blob/fb036d4ebd89f263d34a1f888c279ce85bb383c6/codex-rs/app-server-protocol/src/protocol/common.rs#L2059-L2065)

## 实跑与复现

在 PATH 安装 `codex-cli 0.167.0-alpha.4` 并准备 Python 3.10+，从仓库根目录执行 `python3 prototypes/topic-03a/codex_observation_probe.py`。脚本启动真实 App Server 和 Exec CLI，使用独立临时用户目录与回环固定响应服务。回复和用量来自测试夹具；本次未调用真实模型、未使用用户凭证，未在真实 IDE 安装 Hooks。[探针](../../../prototypes/topic-03a/codex_observation_probe.py)

| 步骤 | 实际结果 |
|---|---|
| 同一 Thread 连续发起两个 Turn（夹具输入 / 输出分别为 10/1、20/2） | 两个 Turn ID 不同。实时通知的 last/total 为 11/11、22/33。 |
| `thread/read` 读取已存历史 | 两个原始 Turn ID 均能取回，各有一条 userMessage 和一条 agentMessage。 |
| `thread/resume` 恢复原 Thread | 回放第二轮累计 33，回环服务收到的模型请求仍为两次。 |
| 关闭 App Server，使用 `codex exec resume --json` 对同一 Thread 发第三轮 | 第三轮夹具输入 30、输出 3，CLI 报输入 60、输出 6；`turn.started` 仅带事件类型。 |
