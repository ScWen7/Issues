# 同一宿主会话 ID 在另一位成员的本地配置里能恢复什么

同一台 Linux 机器上为 A、B 各建空 HOME、宿主配置目录和工作目录。每步启动新的官方宿主进程，模型服务仅监听回环地址。A 先发送合成的私有 D1 规则和一段私有工作笔记，两个标记都只存在于 A 的会话消息里。接收方显式取得的内容是 D2 要求、C2 固定提交和报告 SHA-256，来自订单导出案例。每次模型请求检查完整 JSON 中这五个标记的位置。[C2 报告](fixtures/order-export-c2.json) · [可复跑探针](../../../prototypes/topic-03a/session-handoff.py)

| 操作 | Codex 0.144.6 / App Server | Claude Code 2.1.325 / CLI | 本步模型请求，每宿主 |
|---|---|---|---:|
| A 新建会话 | 私有 D1 和工作笔记进入首轮 | 同左 | 1 |
| B 使用自己的 HOME 和工作目录，提交 A 的 ID 恢复 | `thread/resume` 返回 `no rollout found for thread id …` | `--resume` 退出 1，报 `No conversation found with session ID …` | 0 |
| B 保持自己的 HOME，改到 A 的原工作目录，再试同一 ID | 同样报告缺少该线程的记录 | 同样报告缺少该会话 | 0 |
| B 创建新会话，显式发送 D2 与 C2 交接信息 | 新 ID 与 A 不同。三个共享字段都出现在 `input[2].content[0].text`，两个私有标记均缺席 | 新 ID 与 A 不同。三个共享字段在 `messages[0].content[4].text`，两个私有标记均缺席 | 1 |
| A 用原 HOME、新进程恢复原 ID，再提交一句无标记的消息 | 返回原 ID，两条 A 私有标记出现在恢复后的请求 | 返回原 ID，两条 A 私有标记出现在恢复后的请求 | 1 |

两宿主各 5 步，共 6 次模型请求。探针逐步断言请求数、恢复诊断、新旧会话 ID 关系以及各标记的存在与缺失。D2 指明导出付款时间且未付款时留空。C2 的提交为 `005e558ad99a6def3f4dbb2c7a1ec56e71553bf7`，报告摘要为 `e9c93051c5b844cf23aa89061eed967c5a2267e846e26b37ece7275f194bd514`。本次传入这两条引用，文件的实际下载和字节校验见[独立接收端实验](workspace-continuity.md#从独立接收端取回-c2)。

**平台处理。** 成员 B 接续工作时，先取有权读取的 Issue 决定、精确候选和制品，再在自己的宿主上建立执行。A 的原 Session ID 可用于定位历史生产者。在本地配置彼此独立、未迁移会话历史的条件下，B 带着该 ID 回到同一工作路径也缺少原始会话。A 日后本机恢复，仍沿原归属记录。这里检验的是本机独立配置和持久化历史，独立虚拟机的交付、权限与断线回报见[第五阶段记录](../03a-source-evidence.md#14-跨主机接续)。成员实体设备、实际账户和既有 IDE 的历史迁移仍需现场验证。

## 复跑

在本项目根目录使用 Python 3.10+、Codex 0.144.6 和 Claude Code 2.1.325 运行。探针复用既有 Responses / Messages 回环响应，每行 JSON 输出一组宿主观察，包括原生 ID、拒绝原因、请求计数和实际标记位置。

```bash
python3 prototypes/topic-03a/session-handoff.py \
  --codex /path/to/codex --claude /path/to/claude
```
