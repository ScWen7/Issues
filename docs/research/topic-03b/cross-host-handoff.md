# 一次订单核验怎样从 Codex 交给 Claude Code，再反向验证

专题三 B 第四阶段 · 2026-11-15。上一阶段独立运行 Python 核验器。本轮由真实宿主接收模型的工具调用指令，在本机启动项目 MCP 服务并读取工作簿，随后核对工具结果进入同一回合的下一次模型请求。实验把两位成员、授权与项目订单设为合成数据，固定模型回复以便重演。[设计稿](../../architecture/03b-capability-governance.md) · [一次运行的完整回执](fixtures/cross-host-handoff.json)

## 换人时保留什么

同一份 D2 契约固定订单 Issue、核验节点、节点尝试、候选提交、三份工作簿的名称和摘要、核验器版本，以及应连接的服务和工具接口。角色名称为“订单核验”，工作区内却可能有两项名为 inspect_order 的工具。项目服务读取指定候选，个人服务用来检查是否误调。适配器从本次派发身份解析服务连接；模型参数仅含候选 C1 或 C2。成员、Runtime、Run、领取代次及授权由外部签发，不由模型填入。

| 情形 | Codex 0.144.6 | Claude Code 2.1.325 |
|---|---|---|
| 发现两项同名工具 | 先在盘点线程读当前配置，另开业务线程限制项目 MCP 命名空间及工具 | 在原生控制协议中读取服务来源、已连接的命令和参数。严格配置只允许目标工具，显式禁止个人限定名 |
| 模型主动点名个人工具 | 宿主向模型返回 unsupported call，原生回合中没有实际 MCP 调用项 | 宿主报告工具不可用，模型收到错误，未触发该工具的执行 Hook |
| 项目工具缺失，个人工具还在 | 保留缺项，业务回合和模型请求均为零 | 保留缺项，业务提示与模型请求均为零 |
| 项目服务有权执行 | 实际原生调用项记录服务、工具、参数和 call ID。第二次模型请求携带同 ID 的函数输出 | 首次请求触发 tool_use；核对原生工具事件、Hooks，以及第二次请求内同一 tool_use_id 的结果 |
| 刚被发现，工作权限随即收回 | 项目服务收到调用，返回拒绝；原生工具调用项为 failed | 项目服务收到调用，返回拒绝；Claude 记录 PostToolUseFailure |

两种宿主对“个人工具被屏蔽”的回报形式不同。两边的后台服务调用记录均为零。与之相比，中途撤权时项目服务各收到一次调用，均只返回拒绝状态与回执编号。没有订单正文或核验报告进入后续模型输入。[Codex 源码与实测](cross-host-codex.md) · [Claude Code 原生回执与 SDK 源码](cross-host-claude.md)

## 何时必须在宿主前停下

项目别名被指向个人启动目标时，先比较签发时固定的启动配置；另一组对照把声明参数从候选字符串改成整数，普通配置名和工具名保持不变。实际 stdio 握手和 tools/list 回读揭示了接口变化。这两组预检在两个派发方向都阻止了模型请求。Codex 还能从线程状态核对参数结构。当前 Claude 控制状态提供工具名和注解，适配器另比对实际模型请求里的 input_schema。本轮采用本地受管 stdio 与脚本摘要，远端服务的端点身份和成员登录要由实际接入方式核查。[订单派发入口](../../../prototypes/topic-03b/cross-host/order_handoff.py) · [只读订单 MCP](../../../prototypes/topic-03b/cross-host/order_tool.py)

三库实跑解释了这项取舍。TeamAI 的配置迁移会保留成员改过的同名服务。Multica 的任务配置有覆盖顺序，Broker 还在转发时检查凭证。LoopForge 两个不同安装项可共享同一显示名；新增反例对同名匹配返回歧义，使用明确的安装身份后才调到指定端点。TeamAI 21 项、Multica 16 项、LoopForge 10 项定向测试通过，共 47 项，含该新增反例。[固定版本、调用路径和复跑命令](cross-host-sources.md)

## 两次交接，各消费一次

1. **Codex → Claude Code。** A 已用 Codex 读过 C2，延迟投递该报告。在后续调用前撤回 A 的权限，项目服务返回拒绝。控制者将同一工作契约交给 B，签发新 Run、身份与代次。B 用 Claude Code 真实重读三份工作簿。试图把 A 的原回报挂到 B 名下时，宿主调用凭据与派发不匹配；A 按自己的身份迟到投递时，接收方查到授权已撤回。B 的报告首次收到为 current，重发为 duplicate。当前尝试只消费一次，关联三份制品。
2. **Claude Code → Codex。** 另一组独立场景从 B 的 Claude Code 开始，项目调用因中途撤权被拒，随后 A 以新签发的 Codex Run 完成相同 C2 核验。首次消费一次，重发仍为 duplicate。两组各有独立的节点账本。
3. **C1 缺陷对照。** 两种宿主都实际调用了同一核验器，A3 付款时间通过，A2 因东区工作簿混入西区订单失败。节点可以消费这份有效报告，处理结论是返工。工具成功、报告接纳、候选通过和业务验收因而可以分别追溯。
4. **绑定负向对照。** 服务对错误候选、其他成员、旧代次、替换凭证、模型额外填写的 Run 均返回拒绝。将 C1 的东区工作簿替换进 C2 的副本时，实际制品摘要不符，服务不给出 C2 核验报告。已接替后重放旧前任的交接命令，当前所有者检查阻止了再次接管。

两个独立的 C2 案例和 C1 对照合计 15 个场景。6 个场景在首个业务模型请求前停止。余下 9 个工作回合向本地模型端点发出 18 次请求，其中 7 次原生调用真正到达项目服务；另 2 个回合是主动点名已屏蔽个人服务的对照。这里统计的服务调用来自这 15 个场景，额外的服务直接测试单独列入 authority_controls。每次实际执行均按“原生 call ID → 服务回执 → 字节摘要 → 同回合的第二次模型请求”逐项核对。[完整回执](fixtures/cross-host-handoff.json)

## 复跑与证据范围

实验运行两个官方 CLI 二进制、实际 MCP 子进程、真实 XLSX 及原来的 3A SQLite 结果接收器。两个成员在同一机器上使用隔离的配置目录、独立任务凭证和不同 Run，模型端点固定生成工具指令。工作权限、接管与结果接收共享本次实验的 SQLite 事务；宿主调用回执独立保存，再按当前授权接收。成员日常已打开的 IDE 会话、真实组织账号、远程订单系统、多机网络故障与正式人工验收留给现场集成。

从仓库根目录执行。Python 3.11+、Git、XlsxWriter 3.2.9 和 openpyxl 3.1.5 用于生成与核查工作簿。Codex 为 0.144.6，Claude Code 为官方 Python SDK 0.2.182 随附的 Linux x86-64 二进制。CI 固定并校验两个发布包或可执行文件的 SHA-256。

```bash
work=$(mktemp -d)
python3 -m venv "$work/venv"
"$work/venv/bin/pip" install XlsxWriter==3.2.9 openpyxl==3.1.5
"$work/venv/bin/pip" install --only-binary=:all: --no-deps --target "$work/sdk" claude-agent-sdk==0.2.182
"$work/venv/bin/python" prototypes/topic-03b/cross-host/order_handoff.py "$work/evidence" \
  --codex /absolute/path/to/codex --claude "$work/sdk/claude_agent_sdk/_bundled/claude"
```

summary.json 的 forward、reverse 和 C1_control 各自保留派发绑定、实际工具事件、原生请求回执和节点接收结论。重复执行会产生新的宿主 ID、服务回执和请求摘要；候选、验收结论与消费次数由断言固定。CI 只上传经过筛选的研究摘要。[持续集成配置](../../../.github/workflows/asset-release-research.yml)
