> **架构治理说明（2026-11-15）：** 本文记录 TeamAI、Multica 与 LoopForge 的源码和订单实验事实。当前专题三 B V1.1 复用 Multica Agent / Skill / Plugin / Context / Run 基础设施，保留验收资产固定版本、调用级加载证据、历史失权与派生许可撤回的扩展规则。文中独立 Driver、资产存储和投递机制按上游原义理解；融合机制见[专题三 B V1.1](../architecture/03b-capability-governance.md)和[架构治理基线](../architecture/governance-baseline.md)。

# 专题三 B · 发布、选用与执行实证

第五阶段验证原会话与新受管会话的选择。Codex 真实终端由第二客户端接续，Claude Code 已开放的控制流在收到订单后可以接入新工具。双写入与 Hook 改写的实测给出了原线程和结果证据的适用边界。[原会话、Hook 与核验结果](topic-03b/existing-session.md) · [固定源码与收口评审](topic-03b/existing-session-sources.md)

第四阶段把相同订单工具交给 Codex、Claude Code 实际调用，验证同名来源、参数变更、调用前撤权和双向接续。核验链覆盖模型工具请求、真实 XLSX、模型收到的结果及节点单次消费。[跨宿主实验与源码记录](topic-03b/cross-host-handoff.md)

第三阶段将 Role、Skill 和 Playbook 同时用于订单开发与核验，实测预算不足、指引冲突、派发时撤权，以及修订后重新装载和验收。[订单组合、三库源码与复跑](topic-03b/role-composition.md)

第二阶段研究订单文档修订后两个角色实际收到什么、权限变化后如何继续，以及 C1 返工和 C2 修复怎样提炼成团队经验。真实 Codex 的四次请求覆盖两个角色、撤权后的旧线程和同进程的新线程。[第二阶段完整记录与复跑](topic-03b/project-knowledge.md) · [来源与可见性](topic-03b/knowledge-sources.md) · [贡献与复审](topic-03b/knowledge-contribution.md)

第一阶段 · 2026-11-15。案例沿用订单导出的 D1、D2 和 3A 的真实工作簿。D1、D2 是 Issue 的两项模拟业务决定，R1、R2 是表达相应要求的规则，S1、S2 是实际运行的核验脚本。三者各有来源与责任人。[设计](../architecture/03b-capability-governance.md) · [一次完整本地运行的结构化记录](topic-03b/fixtures/order-release.json)

## 先复核 3A

从远端读取的收口提交为 `1192a9f`。其中已经修复返工报告先到、附件晚到时漏记附件的问题。现有 15 项结果接收回归覆盖当前和历史尝试的补件、错误摘要、撤权、重复及并发消费。另有 38 项工作流、观察与上下文模型回归。两组合计 53 项在本次独立核对和首轮 3B 远端作业均通过。主设计已区分“未确认投递”和“确认写入、当轮加载未知”。旧代续租、登记 Waiting 及 Start 前失败回报的服务端竞争仍按 3A 的部署验证项追踪，3B 使用现有派发绑定和回执。[3A 修订](https://github.com/ScWen7/Issues/commit/1192a9f517f0e84fb7732c3ef0bce54eb99f5db8) · [本轮远端日志](https://github.com/ScWen7/Issues/actions/runs/43657070360/job/132637846645)

## 三库实跑了什么

| 上游及固定版本 | 本轮操作 | 改变设计的一项观察 |
|---|---|---|
| TeamAI `1bc2ce1` | 10 个测试文件中选取 27 项，含 12 项真实 CLI 端到端；另从临时裸远端实跑项目覆盖、评审分支、合并、pull、startup 与 resume Hook | 源码支持两个活跃命名空间同时交付同名 Rule。实测 pull 可在同步锁占用时以 0 退出而仍保留 D1。项目覆盖须有指向关系，落地版本须有回读。[TeamAI 源码、命令与反例](topic-03b/teamai.md) |
| Multica `fdfbfcd` | PostgreSQL 17.5 上运行 10 个 handler 用例；再跑 3 个 Daemon 用例，覆盖权限、版本、插件安装与原生缓存 | 有 Skill 编辑历史的普通工作区，在缓存未命中时仍可接受中心新内容。插件包的已安装版本会保留旧脚本。影响验收的材料须按所选执行版本读回。[Multica 源码与实跑](topic-03b/native-assets.md#multica) |
| LoopForge `97b3cdc` | 运行 1 个发布、5 个引擎原生测试，另建 1 个实际保存、启动、停止、刷新并读回结果的反例 | 已发布 v2 后只保存 rev3，新 Run 已读到 rev3；旧 Run 刷新后同 ID 节点可携带旧成功。创建新实例时从发布引用选择，并检查哪些旧证据覆盖已换版标准。[LoopForge 实验](topic-03b/native-assets.md#loopforge) |

## 一次有前后顺序的订单实验

1. **发布和选择。** 实验使用合成项目、成员和固定的授权映射。团队成员 standards 发布 team/v1，订单项目成员 order-owner 发布 orders/v2，记录其明确替代 team/v1。未经授权的 author 发布被拒。project-maintainer 重送相同版本得到首发记录。已在途的原实例仍引用 team/v1，有权控制者为 D2 交给后继实例，另一个项目仍取 team/v1。
2. **实际宿主输入。** 在同一 Codex 0.144.6 App Server 线程上发出三个真实回合，各自进入本地 Responses 端点。第一次请求含 R1。磁盘换为 R2，第二次请求仍只含历史 R1，这个回执未满足本次核验契约。第三次由控制者显式补发 R2，请求内同时保留历史 R1 和当前输入的完整 R2。每轮发起前已核对该步的 Issue、实例、Run、尝试和预期摘要；每次实际请求均保存 thread/turn、出现位置及输入摘要。实验检查当轮实际收到什么，核验器另查工作簿内容。[真实 Codex 探针](../../prototypes/topic-03b/observe_rule.py)
3. **执行与消费。** 得到 R2 当轮回执后，受管脚本夹具使用选中脚本的原始字节，在独立目录运行 S2。C2 的五列工作簿通过 A2、A3，报告与 3A 固定报告逐字节相同。控制平面沿用 3A 的实际接收原型，按固定候选、Grant、当前尝试和独立取得的附件核验。冒用 S1 摘要的回报返回 verifier mismatch。正确报告两次分别返回 current 和 duplicate，数据库只消费一次。
4. **换标准的对照。** 从 C2 的各角色工作簿移除第五列，保留相同订单与金额。对同一组四列文件，S1 在 D1 下通过；S2 在 D2 下判 A2 通过、A3 失败、进入返工。这个样本单列为 four-column-control；历史 C1 与 C2 的固定报告仍属原来的 D2 验证。

| 接收的材料 | 选择的 Rule SHA-256 前缀 | 实际执行的 Script SHA-256 前缀 | 内容核验 |
|---|---|---|---|
| 四列对照、D1 | `ddbf3c79` | `6581116c` | A2、A3 通过 |
| 同一份四列对照、D2 | `c94cddce` | `f7edf54a` | A2 通过，A3 失败 |
| 固定五列 C2、D2 | `c94cddce` | `f7edf54a` | A2、A3 通过，接收原型只消费一次 |

另有 14 项负向检查，覆盖越权发布、未声明替代、同版异内容、陈旧发布前提、在途改版、跨项目选用、越权读、当轮仅有旧规则、错核验器、材料损坏、失去读权、撤回、隐式降级与上级版本变化。选版目录和权限是单进程设计夹具；真实 CLI、回环模型请求、独立 Python 核验进程、真实 XLSX 和 3A 的 SQLite 接收原型承担各自的实测。外部文档同步、多人生产鉴权及交错发布事务留给相应阶段。[运行器](../../prototypes/topic-03b/order_release.py) · [资产选版原型](../../prototypes/topic-03b/asset_release.py)

## 复跑

从仓库根目录运行。使用 Python 3.11+、Git、XlsxWriter 3.2.9、openpyxl 3.1.5 和官方 Codex CLI 0.144.6。探针使用独立临时 HOME 和本机模型夹具。将输出写入新目录，只保存本次合成候选和回执。

```bash
work=$(mktemp -d)
python3 -m venv "$work/venv"
"$work/venv/bin/pip" install XlsxWriter==3.2.9 openpyxl==3.1.5
"$work/venv/bin/python" prototypes/topic-03b/order_release.py "$work/evidence" --codex /absolute/path/to/codex
```

查看 evidence/summary.json 中的 selections、observed_turns、results 和 checks。正式回归也可在仓库 Actions 中手动运行 AgentPlatform asset release research。新的宿主 ID 和原始请求摘要会随每次运行生成，材料摘要、出现位置的语义、报告和消费次数有固定断言。[远端通过记录](https://github.com/ScWen7/Issues/actions/runs/43657070360) · [工作流](../../.github/workflows/asset-release-research.yml)
