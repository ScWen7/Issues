# 从两个 Git 工作副本核对订单导出 C1 与 C2

固定样本的 D1 指定 XLSX。D2 增加付款时间列，未付款留空，以 Asia/Shanghai 展示。A2 检查操作资格及订单可见范围，A3 检查文件可以打开、金额与时间正确。本次用三个合成订单、四种角色、两个实际提交构造案例，导出与核验分别使用 XlsxWriter 和 openpyxl。样本约定见[订单导出案例](../topic-05/collaboration-scenario.md#模拟约定)。

## 工作副本、脚本与输出怎么关联

在临时 Git 仓库提交 C1，用 detached worktree 检出。只修正东区角色的数据范围，再提交 C2 并建立第二个 worktree。C1 的 HEAD 是 `6880625de52ceb834e3e60b07cd8748c4ad79058`，C2 是它的子提交 `005e558ad99a6def3f4dbb2c7a1ec56e71553bf7`。在各自工作目录启动导出进程，输出写入尝试专属目录。核验前后两个代码工作树均保持干净，两个目录同名的 east.xlsx 均可独立复查。

核验脚本保存在候选代码以外，两次使用相同的 SHA-256。它逐角色重开工作簿，读取全部订单行并和独立的预期值比较。预期时区值是手写本地时间，金额按十进制比较。报告引用验证 Issue、节点、Run、尝试、候选提交和 D2，并给每个实际文件记录相对名称、字节数和完整摘要。退出码记录在各运行观察中；可交给下游的节点结论与报告摘要另存。[工作副本实验](../../../prototypes/topic-03a/order-export/run.py) · [生成 XLSX 的候选代码](../../../prototypes/topic-03a/order-export/exporter.py) · [核验脚本](../../../prototypes/topic-03a/order-export/verify.py)

| 角色 | 此轮允许操作及可见订单 | C1 实测 | C2 实测 |
|---|---|---|---|
| 东区导出员 | 可导出 A-101、A-102 | 多出西区的 B-201，A2 失败 | 只有 A-101、A-102 |
| 西区导出员 | 可导出 B-201 | 仅一条，符合预期 | 同左 |
| 跨区导出员 | 可导出以上三条 | 三条均在 | 同左 |
| 只读查看员 | 无导出资格 | 命令退出 3，未生成工作簿 | 同左 |

A-101 的实付金额是 128.35，付款时间从 UTC 的 2026-11-14 16:15 跨日到上海时间 2026-11-15 00:15。未付款的 A-102 实付 0.00，付款单元格为空。西区 B-201 实付 6.08，付款时间为上海时间 2026-11-15 01:30。A3 同时检查表头、工作表、金额、订单创建时间、状态和付款时间。角色解释固定在本次夹具，真实系统的身份解析和订单数据来源另有集成范围。

| 尝试 | 核验进程 | A2 / A3 | 节点结论 | 东区 XLSX SHA-256 |
|---|---|---|---|---|
| C1 / verify-C1 / 1 | 退出 0，报告落盘 | 失败 / 通过 | rework | `1a7ff30a4350a1dd8506b89ce285cf8b92769baf652eb17133a66b3073536ec9` |
| C2 / verify-C2 / 2 | 退出 0，报告落盘 | 通过 / 通过 | pass | `5784c6c9f6660ac89a3bd4188541f5bfaee85b2e21a39b47a55923983380e852` |

C1 和 C2 的报告 SHA-256 分别为 `da022445c03fa787af994101f47cd8cfb777913f882a6b7aa32116a3493afcb1` 和 `e9c93051c5b844cf23aa89061eed967c5a2267e846e26b37ece7275f194bd514`。使用相同软件版本在第二个空目录重新建库，两个提交、两个报告和工作簿摘要均可复现。C1 的东区文件与允许看全量的跨区文件字节相同，但两次交付的可见范围不同；按字节去重可以节省存储，下载授权仍要回到具体 Issue、交付与角色。[C1 原始报告](fixtures/order-export-c1.json) · [C2 原始报告](fixtures/order-export-c2.json)

## 反例和实际命令驱动

五组反例分别把 C2 东区文件替换为截断的工作簿、删除付款时间列、让金额少 0.01、让付款时间少八小时、给未付款记录写入付款时间。每次单独运行核验进程，均退出 0、报告 A3 失败、节点结论 rework。另一次清空验证输入，核验进程退出 1，报告缺失。该结果给受管执行器三项独立检查：进程如何结束、具名报告能否解析、候选满足哪些标准。有权的验收人再依据当前候选和适用标准作业务接受决定。

将相同 XLSX 交给固定版本 TeamAI 的真实 `workflow start --driver local`。两个 command 节点分别重算 C1/C2 报告，并在 stdout 提交受声明约束的 verdict。工作流中两个后续节点按这个输出走对应分支，各自留下实际文件标记。CLI 的工作流结果为 succeeded，C1 分支接收到 rework，C2 分支接收到 pass，两份报告与直接运行的字节逐一相等。实验只从本地读取候选文件，未调用模型。下游条件决定这条验证流程如何继续，节点是否成功运行与其业务检查值可分别展示。[TeamAI 生成本地执行环境并启动命令](https://github.com/Tencent/teamai-cli/blob/556b5246f2c13ad28b8b79b5b513a78ed8ab9dae/src/workflow/drivers/local/local-driver.ts#L1097-L1127) · [由退出码与 stdout 生成回报](https://github.com/Tencent/teamai-cli/blob/556b5246f2c13ad28b8b79b5b513a78ed8ab9dae/src/workflow/protocol.ts#L1023-L1043) · [关联尝试与修订](https://github.com/Tencent/teamai-cli/blob/556b5246f2c13ad28b8b79b5b513a78ed8ab9dae/src/workflow/drivers/local/local-driver.ts#L387-L397) · [CLI 对照探针](../../../prototypes/topic-03a/order-export/teamai_probe.py)

## 复跑

实测环境为 Python 3.12.14、XlsxWriter 3.2.9、openpyxl 3.1.5、Git 2.52.0。时区转换使用系统 Asia/Shanghai 时区数据库。选择全新输出目录，实验保留两个工作副本、六个实际导出样例、两个报告及 summary.json，便于直接打开或交给下一层。脚本中的订单与角色均为合成数据。

```bash
python3 -m pip install XlsxWriter==3.2.9 openpyxl==3.1.5
python3 prototypes/topic-03a/order-export/run.py /tmp/ap-order-run-01
git -C /tmp/ap-order-run-01/source worktree list
sha256sum /tmp/ap-order-run-01/C1/report.json /tmp/ap-order-run-01/C2/report.json
```

上游驱动补测使用 Node 24.22.1 和已完成 `npm ci`、`npm run build` 的 TeamAI 固定提交。探针创建本机临时项目和独立成员目录，用真实 CLI 初始化、加载工作流、运行两个核验节点和两个条件节点。

```bash
python3 prototypes/topic-03a/order-export/teamai_probe.py "$TEAMAI_CHECKOUT" /tmp/ap-order-run-01
```

本阶段报告覆盖 D2 下的 A2 与 A3。分页和筛选、5,000 / 5,001 条数量边界、页面操作以及真实 UAT 对应 A1、A4、A5、A6，仍按专题一的交付标准执行。
