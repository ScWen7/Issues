# 架构治理 V1.1 交叉审查修订记录

日期：2026-11-15

本轮以 `research/topic-04-cost-quality-improvement` 的 `73b73fda61bc0078cfc65299f74c2fa57c13c274` 为设计基线，依据两份交叉审查修订架构文档。固定源码主要采用 Multica `fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc`；早期专题研究保留各自提交及实验记录。本轮交付为产品机制与文档修订。

## 修订结果

| 审查问题 | 修订后的约定 | 维护位置 |
|---|---|---|
| 复用底座时把扩展能力标为原生已有 | Script 托管、本地 Credits 通路、请求 / Stage 去重、逐调用证据和验收资产锁版明确列为扩展；Qoder 目标 ACP 字段仍按入口实测 | [治理盘点](../architecture/governance-baseline.md#固定版本的底座盘点)、[3A](../architecture/03a-execution-plane.md)、[能力矩阵](../architecture/execution-capabilities.md) |
| 取消预设 Grant / Binding 对象时弱化已识别控制缺口 | 保留受托范围前置、本轮激活、结果消费、人工门禁与出口幂等；在原 Issue 写入 / 派发链落实，同一范围防重复，各就绪节点可并行 | [专题一](../architecture/01-unified-work-lifecycle.md)、[专题二](../architecture/02-sop-workflow.md) |
| 原生谱系字段被忽略，或被误当作完整 SOP 关系 | 复用语义相同的父执行、委托、重试、人工重跑与触发证据；业务轮次不足处保留最小关联。审计 / 成本字段和实际授权分开 | [术语](../../CONTEXT.md)、[专题二](../architecture/02-sop-workflow.md)、[专题四](../architecture/04-cost-quality-improvement.md) |
| 新投递停下后，旧 Session 仍重带失权正文 | 继续 / 恢复前核对历史授权；含失权材料时用现有新会话入口重建获准上下文，必需项缺失则等待 | [3A 会话规则](../architecture/03a-execution-plane.md#已有会话的控制与授权)、[3B 来源规则](../architecture/03b-capability-governance.md#来源刷新选取与历史重带) |
| 验收 Skill 内容漂移、删除历史及派生知识授权规则遗漏 | 固定实际内容与摘要，退役保留获准历史；单来源撤回暂停组合经验，同字节恢复仍经当前代次授权和独立复审 | [3B](../architecture/03b-capability-governance.md) |
| 改进先正式发布再 Benchmark | 固定候选在实验范围验证，达标后审核发布；正式业务选择已发布版本，发布后另作真实效果观察 | [治理基线](../architecture/governance-baseline.md#6-成本质量与-rsi-的关系)、[专题四](../architecture/04-cost-quality-improvement.md) |
| 成本归集、后台开销与改进目标覆盖不足 | 按实际 Run / 计量单元去重，分开业务执行和评价 / Benchmark / 知识活动，分清原生费用、估算、Token-only 和未知，恢复内外环和三类改进 | [专题四](../architecture/04-cost-quality-improvement.md) |
| 共享契约、案例、决策效力和审查表弱化 | 恢复三项共享业务契约、订单各专题推演与反例，区分用户方向输入和架构决策，每专题附六问表；修复相关章节链接 | [总览](../architecture/overview.md)、[README](../../README.md)与各专题 |

## 证据使用与验证

源码核对覆盖 Backend 工厂、Daemon 用量结构、Task Usage 写入与 Issue 汇总、工作流步骤守卫、ContextReceipt、原生 Skill 行为和 Run 谱系。研究中的源码事实、原型结果、真实宿主回执继续按原版本和来源引用。

首次修订（`69af2c3`）的文档核验结果：

- 56 份 Markdown 的 431 个相对文件 / 章节链接检查通过，未发现悬空目标。
- `git diff --check` 通过；新增审查记录另作差异空白检查。
- 交叉复核覆盖版本与术语、候选 Benchmark 发布顺序、工作激活 / 节点尝试 / 实际 Run、节点消费和成本归属，未发现待修订的实质冲突。
- 修订位于独立工作副本；原工作区的工作流修改与实验归档保持原样。

真实 Multica 的 Script 托管、SOP 多入口前置和激活检查、扩展后的 Credits 上报、调用级证据及组织权限 / 发布链列在各专题的集成验收中。既有宿主、原型及服务端测试结果保留其原始记录，本轮未重跑这些实验。

## 保留的决策事项

Multica 底座方向继续作为当前架构基线。本次交叉审查记录的是当时的工作对象提案。后续产品决定见[设计基线表](../architecture/overview.md#设计基线与决策效力)。已有字段的具体存储映射、Script 的 Backend / 受管命令承载方式及部署选型进入后续实现设计，按本轮明确的行为验收。

## 复核 V1.1 后的补正

本次从 [V1.0 到 V1.1 的 15 份文件差异](https://github.com/ScWen7/Issues/compare/73b73fda61bc0078cfc65299f74c2fa57c13c274...69af2c3cf3bf5be29361abff147be2ddc6739797)出发，将上表八项修订与用户设计输入、固定源码、历史反例和各专题现行正文交叉核对。该提交收录了合并修订表，分支中未见两份原始审查稿，逐项结论以可查材料为限。

| 复核中发现的遗漏 | 采用的规则及验收落点 |
|---|---|
| 同一节点的多个 Run、同一候选的旧尝试、制品被多个后继引用 | 每次执行安排去重。核对生产尝试、接收节点和所需输入，旧尝试晚到留在历史，合法后继分别消费。[节点消费](../architecture/02-sop-workflow.md#6-实际候选制品与报告消费) |
| 子项关闭条件及交接后的漏派窗口 | `child_done` 依父项配置与阶段条件通知当前负责人。状态和负责人已交接、下步动作尚未投递时，从原交接恢复仍有效的执行或成员通知。[出口交接](../architecture/02-sop-workflow.md#9-版本与-project-workflow-出口) |
| 把一次宿主进程退出等同于 Run 结束 | 活跃 Run 内的原生恢复可有两次宿主调用。原任务已终结后另派复验，才签发后继 Run。[固定版本恢复判据](../research/03a-source-evidence.md#75-恢复拒绝与新会话重试的真实条件) |
| 已有 Usage 行被当作 Credits 全覆盖，迟到报告可擦除已知值 | 按计量单位及来源更正。已有 Run 明细、Issue 摘要与每日看板的实际字段分别核对。纳入显式零、缺项、重放、缓存与推理 Token、工具和 Runtime 资源口径。[专题四计量反例](../architecture/04-cost-quality-improvement.md#8-交叉审查反例与验收) |
| 陈旧基准仍可发布，可选方法冲突会停整个节点 | 重放核对原发布内容及来源，基准已变则重审。可选方法冲突时省略并记录，必需要求冲突才阻塞。厘清工作区 Skill 与 Plugin 的版本能力，补回代码知识图谱的来源及读权。[资产治理](../architecture/03b-capability-governance.md) |
| 部分采用后沿用原组合的 Benchmark，工作流改进一律按 SOP 发布 | 按拟采用的实际依赖组合复用匹配证据，缺项补受影响回归。SOP 沿资产链发布，项目工作流和团队分工回到有权的 Multica 项目或 Issue 采用。[根因与三层改进](../architecture/04-cost-quality-improvement.md#52-根因与三层改进) |

[项目说明](../../AGENTS.md)、[审查入口](../../README.md)、术语及研究索引同步到本次复核状态。截至该次复核，专题一至四已有设计，专题五仅界定范围。

本次从审查提交重跑 17 项 [SOP 状态模型用例](../../prototypes/topic-02/state-model.test.mjs)、32 项 [成本](../../prototypes/topic-04/cost-ledger.test.mjs)与[评价](../../prototypes/topic-04/evaluation.test.mjs)用例，以及 5 项[单来源撤权回归](../../prototypes/topic-03b/knowledge/test_contribution.py)，合计 54 项通过。上述用例覆盖已有原型。新增的中断窗口、迟到回报、Credits 全链、真实组织权限与发布并发仍在对应专题的集成验收中。Qoder、CodeBuddy 和 Copilot 的宿主状态沿用各自的原始回执。

本次核验覆盖分支全部 56 份 Markdown 的 471 个相对链接，其中 112 个指向具体章节。目标路径、章节及本次变更的空白检查均通过。
