# 从一次区域订单导出返工到团队测试经验

C1 已写出可打开的东区工作簿，付款时间列也通过检查，但东区普通账号拿到了西区订单。C2 保留相同验证器、D2 规则和跨区对照，东区结果排除了西区订单。团队可以从中提炼出一条测试经验：为区域账号和跨区账号分别校验订单集合，另外检查付款时间列。项目审阅者可以点回两份原报告核对依据，团队读者只收到批准的测试方法。[C1 报告](../topic-03a/fixtures/order-export-c1.json) · [C2 报告](../topic-03a/fixtures/order-export-c2.json) · [本实验探针](../../../prototypes/topic-03b/knowledge/contribution.py)

## 两套上游怎样处理改进建议

| 实际路径 | 设计原因及本项目的取舍 |
| --- | --- |
| TeamAI 记录 Session 中打开的召回条目，或接收采纳判断。对同一根 Session 和文档领取一次计分权，投票文件繁忙时保留待写记录。提升候选还要满足配置的置信度、正票、用户数和条目年龄。 | 团队可以依据多人使用信号挑选值得审核的条目。一次打开、多次重试、多人投票各有自己的含义。订单导出的事实来自对两份具名报告的核验，票数只用于排序。[采纳与重试](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/recall-adoption.ts#L536-L581) · [候选资格](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/maintenance/promote.ts#L50-L116) |
| TeamAI 在临时 worktree 写入改写稿，推送专用审核分支，随后在经验条目写入 `promoted_to`。候选筛选检查默认分支和现存审核分支的文件历史。分支被拒绝推送时不写标记，未合并分支删除后可重新提出，已合并条目改名后仍可去重。工作流允许改写失败时使用原文。 | 审核分支将提交与合并分开，Git 历史帮助处理重试和改名。跨项目推广还要审核“具体哪段文字可以给哪些人”。我们分别记录提案、驳回、受众授权、团队发布与退役。含订单号的草稿始终停在项目内。[分支发布与标记](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/maintenance/promotion-publish.ts#L57-L141) · [历史比对](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/maintenance/promote.ts#L138-L160) · [改写回退](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/workflows/teamai-promote-learning/WORKFLOW.yaml#L78-L99) |
| LoopForge 对已结束的 Run 汇总节点重作次数、用量、工具统计及裁剪后的事件，再把事实和可编辑目录交给评测。服务端归一化建议，按配置的维度权重计算评分。登录用户选择成功评测中的建议 ID 后，服务逐条处理并记录应用状态；已应用条目跳过。 | 过程事实、模型提出的改进、管理员实际采用的变更可以独立核对。探针同样分别记录订单验证事实、成员提案和团队发布决定。模型评语或分数本身不足以解释东区具体哪项失败。[事实提取](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/runeval/facts.go#L13-L113) · [评测结果解析](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/runeval/prompt.go#L40-L96) · [逐条应用](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/httpapi/run_eval.go#L225-L295) |
| LoopForge 只实现一组已知修改动作，例如更新节点重试参数、增删 Agent gate、追加指令。通用 SOP 经评测应用时会建项目内的未共享草稿副本，并复用已有副本。应用后的配置先写库，再保存评测条目的应用状态。 | 这一机制可让项目试用改进并定位改了哪些字段。跨项目认可的团队经验还需要独立发布、撤回、重新审核。上游的“已应用”来自一次配置写入；跨进程并发、目标与评测记录写入间的故障恢复也要另外验证。[支持的动作](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/runeval/apply.go#L10-L38) · [写入目标与项目副本](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/httpapi/run_eval.go#L275-L368) |

### 上游实跑

在以上两个固定提交的仓库根目录分别执行。TeamAI 使用 `npm ci`、`npm run build` 准备好的 CLI、临时本机 bare Git 远端以及测试自带的 AI 命令替身。完整审核 E2E **14/14** 通过，包括拒绝推送、开放审核、合并后改名、未合并删除后重提。两组单元测试合计 **34/34** 通过，包含投票繁忙或标记丢失时重试去重。[E2E 对照](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/__tests__/e2e/recall-promote-publish.test.ts#L179-L253) · [采纳重试断言](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/__tests__/recall-adoption-retry.test.ts#L29-L105)

```bash
node ./node_modules/vitest/vitest.mjs run --pool=threads --maxWorkers=1 --no-file-parallelism --config vitest.e2e.config.ts src/__tests__/e2e/recall-promote-publish.test.ts
node ./node_modules/vitest/vitest.mjs run --pool=threads --maxWorkers=1 --no-file-parallelism src/__tests__/maintenance-promote.test.ts src/__tests__/recall-adoption-retry.test.ts
```

LoopForge 两个 Go 包中选取的 **5/5 个顶层测试**通过。原生 HTTP 测试发送评测请求、轮询成功状态、选择建议 ID 应用，并从仓库回读 `maxAttempts = 3`。模型回复由测试注入。另有对照覆盖进行中的评测返回 409、匿名应用返回 401 以及项目副本逻辑。[写入后回读](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/httpapi/run_eval_test.go#L42-L99) · [克隆](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/httpapi/run_eval_cases_test.go#L16-L76) · [冲突与匿名访问](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/httpapi/run_eval_cases_test.go#L400-L461)

```bash
go test -p 1 -parallel 1 -count=1 -v -run 'Test(BuildFactsDetectsReworkAndToolStorm|ApplyRecommendationBranches|RunEvalScoresAndAppliesNodePatch|RunEvalCloneAndApplyBranches|RunEvalRecoveryAndApplyConflicts)$' ./internal/runeval ./internal/httpapi
```

## AgentPlatform 贡献与复审实验

| 操作 | 实际执行的检查 |
| --- | --- |
| 固定证据 | 读取 3A 的 C1 和 C2 报告原始字节，按仓库固定 SHA-256 校验。两次 Run 对应同一 Issue、节点、D2 规则和验证器，提交及尝试次数不同。对照 `/checks/east/A2`、订单集合、跨区账号以及 A3 付款时间列，再确认 C1 返工与 C2 通过。 |
| 重复与退回 | 以目标团队、主题、Issue、节点、两次宿主验证 Run 和检查位置组成稳定提案键。第二个观察者重复提交返回同一条目。审阅者驳回含项目订单号的第 1 稿并留理由；重复提交保留驳回结果。作者改写第 2 稿，旧稿的发布请求被拒。 |
| 跨范围发布 | 项目读取权、每一份证据的对外提炼权、独立团队发布权分别检查。只管 C1、只能管来源、只有团队发布权、只有项目范围授权、作者自审均有拒绝对照。项目管理人签发绑定目标受众、正文摘要、稿号和两份证据各自的摘要及变更代次的授权。独立发布者读取两份原始报告后发布。 |
| 阅读与派发 | 普通团队成员收到条目标识、团队、版本号和批准的正文。项目路径、报告摘要、订单号及审核账本均不进入该投影。团队成员读取报告或审核账本遭拒，项目审阅者可以沿 Run 和定位复查报告。派发到同一实验 Run 两次只固定一份正文摘要。 |
| 团队提炼授权撤回 | 撤销某个人的原报告读取权只影响此人。撤销对整个团队的提炼授权会立即停发。即使来源和正文都没变，来源管理人也要等审阅流程重新打开才可授权。重新授权只记录许可，完成独立团队复审后才恢复派发。 |
| 同字节恢复 | 每份来源分别维护单调变更代次，内容变化、明确撤回和恢复各记一次。重复上报同一个摘要或重复上报已撤回，代次保持。实验中 C1 从初始第 1 代修改并恢复到第 3 代，又在审阅者查看前撤回并恢复到第 5 代。三代摘要完全相同，C2 始终停在第 1 代。两次恢复均处于待复审，沿用旧授权发布均被拒。来源管理人授权当前代、审阅者核验当前证据并确认后，同一团队 v1 才恢复派发。 |
| 证据改版 | 给 C1 追加一个换行，报告摘要改变，首次发布的条目立即停发。第 6 代证据仍支持同一正文，单独授权和独立复审后恢复团队 v1，新增复审凭据。已派发的版本及正文摘要始终保留。 |
| 证据矛盾与退役 | 在实验副本中将 C1 结论改为通过，重审被证据对照拒绝；撤回 C1 后原报告读取和新派发均被拒。审阅者记录理由并退役。即使恢复原始字节，条目仍为退役。历史账本保留首次驳回、来源摘要、授权与发布事实。 |

发布示例正文为“验证区域订单导出时，用普通区域账号和跨区账号分别导出。核对每份工作簿的订单集合，并单独验证付款时间列。”第 2 稿首次发布产生团队资产 v1。正文和受众相同、证据重新审核时仍使用 v1。每份复审凭据保留当前的来源标识、内容摘要和代次。同一来源在撤回后恢复原文，与重复上报当前原文可以据此区分。未来改写正文需要新资产版本。这里对证据采用整份报告摘要，即使只改了无关空白也触发复审，适合两份体量很小的验证报告。若复用到长文档，需另行定义段落定位和变更判定。

在 AgentPlatform 仓库根目录执行。使用 Python 标准库，结果逐条列出 **45 个经过执行的正反向检查**、首次团队可见投影、历史派发回执及项目专属审核账本。重复执行得到逐字节相同的 JSON。独立负对照在输入目录的 C1 报告后添加一个换行，程序在读取阶段拒绝了与仓库固定摘要不符的输入。实验中的后续换版则通过受控的来源管理操作注入，不改动 3A 文件。[复跑入口](../../../prototypes/topic-03b/knowledge/contribution.py)

```bash
python3 prototypes/topic-03b/knowledge/contribution.py --fixtures docs/research/topic-03a/fixtures --output /tmp/knowledge-contribution.json
```

整个输出面向项目审阅者；提供给团队的字段仅取 `team_projection_at_first_publication` 的视图。身份、授权、派发和审核记录均在单次 Python 进程中运行。真实组织权限同步、持久事务、并发去重和已离线成员的本机副本撤回，留待产品实现与集成测试。
