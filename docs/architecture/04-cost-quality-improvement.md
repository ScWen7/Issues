# 专题四 · 成本、质量与自改进

V0.1 · 探索基线 · 2026-11-15

## 1. 目标

让平台回答四个问题：一次工作实际消耗了什么；这些消耗应归到哪个 Run / Issue / SOP 节点；执行结果质量如何且评价依据是什么；哪些重复问题值得改进、改动是否真的改善结果。

专题四不建立第二套工作状态或 Run。Issue、Run、Node Attempt、SOP 实例和资产版本沿用前序专题；专题四读取执行事实，产生计量、评价、Benchmark 和改进证据。

## 2. 共同原则

- 先保存原始观察，再形成计量结论。原生请求、宿主快照、工具调用、服务回执、账单行和人工说明保留来源、发生时间、接收时间、覆盖范围及摘要。
- 事实、推断和未知分开。供应商报告的 Token、宿主估算、账单实付、仅知 Token、未知费用不能压成一个“真实成本”字段。
- 多路观察不等于多次执行。同一原生请求可被 Hook、Daemon、OTel 和转录导入同时观察；观察可并存，计量单元只能结算一次。
- 归属依赖实际执行身份。Run 是成本的原始归属单位。Issue、父子 Issue、SOP、节点尝试、Squad 和项目是引用及汇总视图，按底层计量单元去重。
- 评价不改写执行事实。执行成功、质量评分、SOP 门禁和业务验收是不同结论。
- 改进不自动改变在途工作。建议先形成候选改动，经回归和审核后由专题三发布新版本；新实例显式选择新版本。

## 3. 成本账本

### 3.1 两层记录

**Observation（观察）**保存原始事实：来源系统、宿主与账号命名空间、Session / Thread / Turn / Prompt / Message / Tool Call 等原生标识、事件种类、阶段、模型 / Provider、指标、单位、区间、发生与接收时间、原始摘要和采集覆盖。

**Usage Entry（计量条目）**是经过归属、去重、口径判断后的结算记录：计量单元身份、生产 Run、执行成员、Provider / Model、指标与数量、计费口径、来源证据、覆盖状态、当前版本及更正链。

一条 Observation 可以不产生 Usage Entry；多个 Observation 可以共同证明一条 Usage Entry。禁止把“收到一个事件”直接等同于“新增一次费用”。

### 3.2 原生计量单位与异构宿主

账本统一的是记录结构和归属规则，不是强迫所有宿主使用同一种单位。每条计量都必须携带 `provider`、`metric`、`unit`、`value`、来源命名空间、原生事件身份和计量覆盖范围。单位至少区分：

| 宿主 | 原生单位 | Runtime 可观测入口 | 归属边界 |
|---|---|---|---|
| Codex | input / output / cached tokens | App Server Thread / Turn / Usage；CLI JSON 投影 | 累计快照先确定基线和独占区间 |
| Claude Code | tokens、请求级 usage | Hooks、SDK 消息、OTel request_id / message UUID | 按请求 / 消息身份去重，区分累计与增量 |
| Qoder | Qoder Credits | 本地 Qoder Agent SDK Assistant 消息 `message.usage.credits`；Result 的 `total_credits` 仅作会话累计快照 | 受管 SDK Runtime 产生的请求用量可绑定 Run；缺字段保持 unknown。不能据此声称能读取任意已打开 IDE 会话 |
| CodeBuddy Code | CodeBuddy Credits | 本地 CLI `--output-format stream-json` 的 `system/usage_update` | 以 `session_id + requestId + stage.id` upsert；snapshot 替代 stage 汇总，不能相加。IDE 未暴露则 unknown |
