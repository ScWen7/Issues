# CodeBuddy 的 0.69 Credits 在 Multica 工作台如何显示

2026-11-15 使用 Node 24.22.1，回放 CodeBuddy CLI 2.181.0 已归档的三条观测，并执行固定 Multica 版本的前端计算函数。**如果接口已经提供正确的 Run 明细，执行日志和运行时间线可以按供应商显示 0.69 Credits。** 从本地 Backend 写到该明细、从服务端汇总到项目每日看板仍需分别接入。

## 输入与实际执行范围

本轮回读 [Mac 探针归档 JSONL](../../../artifacts/topic-04/mac-20261115-0350/codebuddy-receipt.jsonl)，文件 SHA-256 为 `3fb235e4f8756d7a0c18bfc403df6694ece17c9ab2b70c2e0902b506da6a6613`。其三行依次为同一 Run / Session / Request 的 Stage、Turn 快照和 Result 快照，各记录 0.69。它们是原生消息中获准字段的投影。脚本检查身份、单位和观测范围，再把投影交给仓库原有的 [reconcileCodeBuddyTurn](../../../prototypes/topic-04/cost-ledger.mjs)。一次输入和三次重放都得到一个 Stage，快照与该 Stage 同额。未出现真实 Stage 修订。

将归并所得 0.69 换算为 690000 micros，构造**接口明细夹具**。在 Multica 固定提交 `fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc` 的原文件上直接运行 `summarizeTaskUsage`、`summarizeTaskUsageAcross`、`formatSpend` 和 `buildRunTimeline`。脚本校验所读三个上游 TypeScript 文件的 SHA-256，用空的自定义费率、确定性的供应商标签替代浏览器环境。页面测试、翻译渲染、数据库写入均不在这次执行范围。[用量归并源码](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/packages/views/runtimes/utils.ts#L1044-L1114) · [时间线计算](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/packages/views/issues/components/issue-run-timeline.ts#L145-L207) · [实际界面调用位置](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/packages/views/issues/components/execution-log-section.tsx#L248-L261)

## 运行结果

| 输入 | 上游函数实测输出 | 工作台怎么使用 |
|---|---|---|
| Mac 回执三条，分别重放一次和三次 | 两种输入的归并结果均为一个 Stage、0.69 Credits。基于该明细的单 Run 和单 Run 的 Issue 执行日志汇总均显示 `codebuddy 0.69 Credits` | 可复用已有原生单位展示。重复观测在进入 Run 明细前处理；前端对传入的每一行求和 |
| 以上明细，另加一条 **合成** Qoder Cloud 2 Credits | 多 Run 汇总显示 `codebuddy 0.69 Credits + qoder_cloud 2 Credits`，时间线也返回这两个供应商及各自金额 | 两种 Credits 独立展示。合成值只用于验证分组，本地 Qoder 请求用量仍为未知 |
| **合成** 同一 CodeBuddy 范围，三个终态 Run 分别显式上报 0 Credits、只报 24 个输入 Token、无上报 | 显式零显示 `codebuddy 0 Credits`。只有 Token 的行保留 24 个 Token，Credits 映射为空；未定价模型在空费率配置下的金额标签为 `$0.00`。无上报的 Run 返回 null | 显式零可作计量依据。Token-only 应显示 Token 数并标示费用未知；来源或费率缺失时，禁止将标签中的零作为实付或免费证据 |
| 同上三个 Run 合计 | 时间线 `pricedCount = 2`，按实际 Credits 键计数只有 1 个 Run。合计显示 `codebuddy 0 Credits`；仅含缺报 Run 的汇总返回 null | 在这个全部适用 CodeBuddy Credits 的对照组中，已知小计为 0、覆盖 **1/3**。呈现缺报数量须检查预期覆盖范围与每次明细。原时间线计数统计有任意用量明细的 Run |

[费用标签的固定实现](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/packages/views/runtimes/utils.ts#L163-L195) · [Issue 运行窗口的标签与空态](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/packages/views/issues/components/issue-runs-dialog.tsx#L250-L276)

## 尚待贯通的位置

- **写入。** 本地 CodeBuddy Backend 的系统事件分支尚缺 Stage / Credits 解析，Daemon 的 TaskUsageEntry 尚缺 Credits 字段。服务端上报载荷已支持显式零与缺失；当前 upsert 以 task / provider / model 覆盖整行。上述夹具直接提供归并后的明细，实际旧快照、仅报 Token 及补报 Credits 的写入次序仍要由专题四验证。[Backend 系统事件分支](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/codebuddy.go#L246-L280) · [结果用量解析](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/codebuddy.go#L655-L724) · [Daemon](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/types.go#L309-L322) · [服务端零值处理](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon.go#L5489-L5527)
- **读取。** Issue 的每 Run 明细查询会返回 credits_micros，前端可从这些明细汇总。同一文件中，GetIssueUsageSummary 的服务端汇总及 ListDashboardUsageDaily 的每日汇总均未计算 Credits；前者的 metered_task_count 统计有任意用量行的适用终态 Run。专题四还需让实际 Stage 经 Daemon 落入 Usage 后，在同范围核对明细、按单位的 Issue 汇总和每日看板。[写入和明细](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/task_usage.sql#L1-L53) · [Issue 与每日汇总](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/task_usage.sql#L84-L166)

## 复跑

在本仓库根目录，以 Node 24.22.x 执行。参数指向上述固定提交的 Multica 本地工作副本；脚本只读取上游源码和本仓库回执，无需浏览器、npm 安装或商业账号。

```sh
node prototypes/topic-05/codebuddy-display-replay.mjs /path/to/multica
```

[复跑脚本及断言](../../../prototypes/topic-05/codebuddy-display-replay.mjs)
