# A 的工作进程中断后，B 如何接续 C2

实验沿用订单导出的两个固定 Git 候选和真实工作簿。A 的 C1 检查结论是返工，尚未送达；C2 的提交、核验报告和三个工作簿已经发布。B 接手时需恢复已发布的 C2，保留 A 独有的草稿，并让晚到的 C1 回到原尝试。[工作副本和业务标准](order-export-workspace.md) · [工作进程与接收探针](../../../prototypes/topic-03a/machine-handoff/handoff.py)

## 实测顺序

| 时点 | 操作与实际观察 |
|---|---|
| A 中断前 | A 把带原 Run、尝试、候选和 D2 的 C1 报告写入磁盘发送队列并执行 fsync，另外保留未提交文件和会话草稿。随后本次测试工作进程收到 SIGKILL，外部执行器取得退出码 137，此时未提交任何回报。 |
| B 接手 | B 等待外部执行器确认 A 退出，再只读取显式发布区。它从 Git bundle 建立独立对象库、按完整提交检出 C2，逐份检查三个 XLSX 的长度、SHA-256 和 ZIP 结构。B 的 checkout、目录和收到的交付内容中均无 A 的未提交文件、会话草稿或发送队列。 |
| B 复核 | B 在独立 checkout 重新运行固定的导出器，生成的东区 XLSX 与已发布文件逐字节相同。中心按第四阶段的接收原型校验 C2 的派发绑定、检查值与具名制品，登记一次 `verify-C2 / pass`。 |
| A 恢复 | 恢复工作进程读取 A 持久目录，重获原发送队列及私有草稿。它在 C2 已确认后送出 C1，并用相同字节再发一次。中心依次记录 `historical` 和 `duplicate`。最终数据库有两份回执，而节点只消费 C2 一次。 |

C2 固定提交为 `005e558ad99a6def3f4dbb2c7a1ec56e71553bf7`。本次复核的东区文件为 5,494 字节，SHA-256 为 `5784c6c9f6660ac89a3bd4188541f5bfaee85b2e21a39b47a55923983380e852`。接收方能按已发布版本重建 C2；A 的未发布材料留在原机，恢复后仍可取回。成员可据此选择补交草稿、重新执行或继续使用已发布候选。[固定 C2 报告](fixtures/order-export-c2.json) · [平台接收断言](../../../prototypes/topic-03a/result-admission/test_admission.py)

**环境与证据。** 两套独立生成的订单样本均已通过，最终版探针复跑得到相同结果。中心、原 A、接收 B、恢复 A 四个执行上下文各有不同的网络、PID、挂载命名空间；四者的主机名与内核启动标识相同。命名空间检查只发布计数。原 A 的进程实际退出。恢复角色在 C2 被中心确认后才读取 A 的持久目录。跨上下文传递使用共享卷上的显式发布区和分类收件目录，成员访问权限另用真实任务身份验证。本案例的 bundle 包含 C1、C2 的可达历史和整份合成订单库，适用于获准读取该仓库的接收者。只获准下载特定工作簿时，使用对应附件的授权下载。检查操作为停用测试进程，真实物理机断电、磁盘故障和广域网策略另用部署环境验证。

**权限如何证实。** B 的独立 HTTP 客户端由共享 Runtime 实验提供任务级凭据。实跑六个固定生产路由，目标 Issue、已发布附件及 B Runtime 的用量查询返回 200；其他私有 Issue、未共享附件及 A Runtime 的用量查询返回 404。独立进程下载的 XLSX 通过长度、SHA-256 与 ZIP 校验。这条链在本机回环 HTTP 上经过生产中间件与 handler，客户端和中心共用网络、PID、挂载命名空间。四个隔离执行环境的文件交接另作一组观测。[B 的独立 HTTP 客户端](../../../prototypes/topic-03a/machine-handoff/identity_read.py)

## 复跑

使用 Linux、Python 3.12、Git，以及[订单实验](order-export-workspace.md#复跑)的 Python 依赖。下面命令完成普通 Linux 工作站上的业务断言。每次使用新目录，SIGKILL 仅结束本次执行的 A 测试工作进程。

```bash
set -eu
probe=prototypes/topic-03a/machine-handoff/handoff.py
suite_dir=$(mktemp -d)
python3 prototypes/topic-03a/order-export/run.py "$suite_dir/order"
python3 "$probe" setup "$suite_dir/state" --order-run "$suite_dir/order"
python3 "$probe" A-stop "$suite_dir/state" || test "$?" -eq 137
python3 "$probe" B-resume "$suite_dir/state"
python3 "$probe" A-reconnect "$suite_dir/state"
python3 "$probe" reconcile "$suite_dir/state"
```

复核本次使用的四套命名空间时，让四个独立执行器只共用实验卷，工作目录使用绝对路径。先运行 setup，再同时启动下列前三项；第四项由原 A 的外部控制脚本执行。前三项使用文件握手，在发布、确认和旧回报实际就位后才继续。若只是同主机的四个普通终端，使用上面的顺序复跑；严格模式会检查网络、PID、挂载三类命名空间各有四个不同标识。

| 执行器 | 命令 |
|---|---|
| 中心 | `python3 "$probe" reconcile "$suite_dir/state" --coordinated --distinct-namespaces` |
| 接收 B | `python3 "$probe" B-resume "$suite_dir/state" --coordinated` |
| A 的恢复执行器 | `python3 "$probe" A-reconnect "$suite_dir/state" --coordinated` |
| 原 A 的外部控制脚本 | 运行下段脚本并确认退出码，再通知 B |

```bash
status=0
python3 "$probe" A-stop "$suite_dir/state" --coordinated || status=$?
test "$status" -eq 137
printf '%s\n' "$status" > "$suite_dir/state/evidence/A-stopped"
```
