# Codex 上下文换版与恢复实测

订单导出验证要依据 D2 的付款时间列和 A2 权限规则。探针将两版规则写成两个唯一标记，文件自动加载对照只在 Agent 配置文件中写入标记，成员输入和固定模型回复均不含标记。另有一组显式补发对照，刻意在当轮输入加入 D2。回环 Responses 服务检查真实 Codex 进程发来的 input，保存消息顺序和片段类型，脚本只打印命中的标记。显式选择 Skill 的场景同样把第三个标记只写在 SKILL.md 正文。模拟模型没有判断业务是否通过。[Codex 官方的指令发现说明](https://learn.chatgpt.com/docs/agent-configuration/agents-md)

## 版本、输入与结果

固定宿主为 0.144.6（官方 npm 包，SHA-512 与 registry 发布值一致）和 0.167.0-alpha.4。前者与 Multica 固定版本登记的 Codex 加载探针版本一致。Multica 的元指令写在工作目录 AGENTS.md，Codex HOME 的用户级 AGENTS.md 是另一个投递通道；每个组合都使用独立临时目录和配置。项目文件这一列调用固定 Multica 的真实 InjectRuntimeConfig，将其生成的文件直接交给 Codex。[旧版源码](https://github.com/openai/codex/tree/5d1fbf26c43abc65a203928b2e31561cb039e06d) · [新版源码](https://github.com/openai/codex/tree/fb036d4ebd89f263d34a1f888c279ce85bb383c6) · [Multica 写入入口与实际路径](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/execenv/runtime_config.go#L161-L192) · [上游探针版本表](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/context_receipt.go#L94-L120)

| 同一组测试输入 | 0.144.6 项目 AGENTS.md | 0.144.6 HOME | 0.167.0-alpha.4 HOME |
|---|---|---|---|
| 新线程加载 D2 | 本轮模型请求含 D2 | D2 | D2 |
| 新线程先加载 D1 | D1 | D1 | D1 |
| 文件替换为 D2，在同一活动线程继续下一轮 | 仍仅 D1 | 仍仅 D1 | D1 历史后出现 D2 替换通知 |
| 对已加载线程调用 thread/resume，再开新轮 | 仍仅 D1 | 仍仅 D1 | D1 历史后有 D2 替换通知 |
| 关闭 App Server，起新进程恢复原线程，再开新轮 | D1 历史后有 D2 替换通知 | 同左 | 同左 |
| 删除规则文件，再次跨进程恢复原线程 | D1、D2 历史后出现移除通知 | 同左 | 同左 |
| 新线程，文件缺失 | 请求没有 D1、D2 | 同左 | 同左 |
| 另一条热线程先加载 D1，磁盘更新 D2，下一轮调用者显式提交“本轮契约 D2” | 请求同时有 D1 历史与独立的 D2 输入，文件刷新证据缺失 | 同左 | D1 历史、D2 文件替换通知、显式 D2 输入三者均可定位 |

0.144.6 的 AgentsMdManager 按执行环境选择缓存项目指令，选择未变时直接返回。渲染器在比较新旧快照后，按需发出替换或移除通知。0.167.0-alpha.4 的 HOME provider 会重新读用户指令；这一版项目文件另有读取权限分支。项目选择和信任级别都可能影响该通道。这里记录的是测试过的具体版本和通道。[旧版缓存条件](https://github.com/openai/codex/blob/5d1fbf26c43abc65a203928b2e31561cb039e06d/codex-rs/core/src/agents_md_manager.rs#L10-L46) · [旧版历史与新指令的差量](https://github.com/openai/codex/blob/5d1fbf26c43abc65a203928b2e31561cb039e06d/codex-rs/core/src/context/world_state/agents_md.rs#L42-L80) · [新版用户指令与项目缓存](https://github.com/openai/codex/blob/fb036d4ebd89f263d34a1f888c279ce85bb383c6/codex-rs/core/src/agents_md_manager.rs#L83-L144) · [新版 HOME 文件读取与警告](https://github.com/openai/codex/blob/fb036d4ebd89f263d34a1f888c279ce85bb383c6/codex-rs/codex-home/src/instructions/mod.rs#L40-L109) · [新版项目文件权限](https://github.com/openai/codex/blob/fb036d4ebd89f263d34a1f888c279ce85bb383c6/codex-rs/core/src/agents_md.rs#L58-L110)

0.167.0-alpha.4 的项目文件通道在当前容器另测 read-only、workspace-write。两次均在 thread/start 读取工作区指令时由文件沙盒返回 NETLINK_ROUTE 操作受限，均未产生模型请求。三个成功组合分别执行 11 个 turn、12 个本地模型协议请求。目标机器上应复跑同一 project 模式，补齐这个版本的项目文件证据。0.144.6 的受限 read-only 模式已完成该项目路径的上下游贯通。

**设计结论。** 把回执关联到 issue、run、实际 thread / turn、宿主版本、通道、期望材料版本及本轮证据。工作目录已写 D2、版本表命中 verified、本轮模型输入实际仍只有 D1，可以同时成立。重要契约换版后，在已受支持的入口显式提交当前差异并取得本轮可用证据，或在可恢复条件下创建新连接、重新装载同一工作上下文；仍缺当前材料时，等待补齐再判该轮结果。只允许上报可见记录时，如实保留“本轮加载未知”。本次抓取完整合成输入仅用于隔离实验；产品可用获授权的版本 / 摘要和通道回执核对，保留探针条件及覆盖差异。

## Skill、MCP 与发起主体

- 新线程首轮请求没有测试 Skill 的正文标记。skills/list 返回该技能为 enabled，并找到准确路径。下一轮在 turn/start 传入显式 skill 输入后，模型请求出现对应正文。前者是可发现，后者是正文已进入本次请求。后续轮次会带回已有历史，不能凭历史正文另计一次当轮调用。探针只确认这次显式注入，业务产物按 D2 和 A2 单独核验。[显式选择与内容拼装](https://github.com/openai/codex/blob/5d1fbf26c43abc65a203928b2e31561cb039e06d/codex-rs/core/src/session/turn.rs#L584-L625)
- 为每个组合配置一个合成只读 MCP 查询。Codex 实际启动它，服务端日志观测到 initialize 和 tools/list。App Server 的工具目录返回 inspect_report，此时服务端 tools/call 计数为 0。0.167 的线程状态还报告 connected；0.144.6 的该字段无值。此时可确认有过连接、发现过工具。
- 随后测试客户端通过 mcpServer/tool/call 显式调用一次，真实 MCP 进程返回 synthetic-candidate-C2，计数升为 1。再单独开一轮，模拟模型回应带有特定 call_id 的工具调用；真实 Codex 进程调用同一个 MCP，服务端计数升为 2，回环服务在下一条模型请求看到了同一 call_id 的 function_call_output 和 C2 标记。前一次是客户端发起，后一次是测试模型响应驱动的宿主行为。原始上下文、目录、成功结果、谁发起以及结果是否送回模型，各有对应证据。[客户端调用的实现](https://github.com/openai/codex/blob/fb036d4ebd89f263d34a1f888c279ce85bb383c6/codex-rs/app-server/src/request_processors/mcp_processor.rs#L738-L758) · [状态及工具发现字段](https://github.com/openai/codex/blob/fb036d4ebd89f263d34a1f888c279ce85bb383c6/codex-rs/app-server-protocol/src/protocol/v2/mcp.rs#L50-L106)

## 复跑

在已有 Git、Python 3.10+、目标版本 codex 的机器，仓库根目录执行以下命令。脚本和第二阶段的 codex_observation_probe.py 放在同一目录；子进程使用独立临时 HOME，只连接本机模拟模型端点与本机 MCP。要观察完整上游写入链，把 AP_CONTEXT_MATERIALIZER 指到编译好的 InjectRuntimeConfig 测试工具，否则 project 使用语义相同的合成规则文件。

```bash
codex --version
AP_CONTEXT_MATERIALIZER=/absolute/path/to/materialize python3 prototypes/topic-03a/codex-context-probe.py project
python3 prototypes/topic-03a/codex-context-probe.py home
```

已测三组按精确的版本和通道运行回归断言。0.167.0-alpha.4 的项目通道及其他未测组合进入探索模式。热继续和同进程恢复分别打印本次请求里 D1、D2 和替换通知出现的次序；显式补发另行报告文件刷新标记是否出现。探索可接受保留旧版或已替换这两种结果，出现新的历史组合则记录待复核项并继续后续场景。协议成功、显式输入实际到达和工具回报仍有独立断言。模型输入中的原始文本可证明该请求包含材料；模型是否采用它、调用结果是否正确、成员是否接受交付，各自依据实际验证。
