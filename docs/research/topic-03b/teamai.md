# TeamAI 如何选规则、发布经验，以及保住在途脚本的版本

本轮使用 TeamAI 固定提交 `1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956`，从发布者的工作副本追到接收项目的文件和 Hook 返回值，再查旧工作流执行时打开的文件。实跑使用 Node 24.22.1、Vitest 4.1.12、临时本地 Git 远端和合成订单规则。[固定源码](https://github.com/Tencent/teamai-cli/tree/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956)

## 一条订单规则从评审分支到宿主

实验创建一条团队默认规则和一个有同名覆盖规则的订单项目。默认分支上，项目使用 D1，要求按地区筛选。D2 增加付款时间要求。这里 D1/D2 是规则正文的观测标记；AgentPlatform 上正式的工作决定仍由 Issue 保存。TeamAI 的真实 CLI 完成 init、projects set、pull 与 hook-dispatch。探针逐次断言目标文件内容与返回的 `additionalContext`。[订单探针](../../../prototypes/topic-03b/teamai-rule-handoff.py)

| 操作 | 项目 Claude 规则目录 | TeamAI 为 Codex 返回的 Hook 内容 |
|---|---|---|
| 项目选择 orders，在默认分支取得 D1 | `.claude/rules/orders/export-policy.md` 内容是 D1，共享根的同名副本缺席 | startup 返回 D1，团队默认和 D2 标记缺席 |
| D2 已推至评审分支，项目仍跟随默认分支 | 仍为 D1 | startup 仍返回 D1 |
| 将 D2 快进合并到默认分支，再同步 | 读回 D2 | 新 startup 返回 D2；以 resume 再发同一接口，两种版本的规则标记均缺席 |

手工执行第一版探针时，前一轮 SessionStart 派生的后台同步持有锁，另一个普通 pull 以 0 退出，日志显示该 scope 被跳过，读回的文件仍是 D1。复跑探针等原操作释放锁后重试，并检查本次落地文件。上游有意让可延迟的后台操作跳过已占用的同步范围；前台 Hook 只为特定工具构造上下文，对 resume 跳过重复投递。本实验未启动宿主模型。文件已写、Hook 已返回、本轮请求确实使用该版本是三种可分别取得的回执。[并发同步处理](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/pull.ts#L3878-L3903) · [前台 Hook 的分支](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/hook-handlers.ts#L1130-L1155) · [3A 的真实宿主请求对照](../topic-03a/codex-context.md)

## 底层机制为何这样设计

| 问题 | TeamAI 的实现、原因及本次反例 | AgentPlatform 的采用方式 |
|---|---|---|
| 从哪里取哪一版 | `resolveTeamRef` 将分支、标签或提交解析成实际 commit，检查该提交的团队配置。上游 CLI 试验里，分支跟随远端前移，标签在默认分支更新后仍指原提交；无效引用与抓取失败保留原工作区。可变渠道方便成员跟随团队，实际修订则能解释一次交付。[解析](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/team-ref.ts#L37-L72) · [分支与标签对照](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/__tests__/e2e/pull-team-ref-1183.test.ts#L103-L141) | 每次选择保存来源、发布版本和内容摘要。来源可来自平台维护的内容、外部文档修订或 Git。工作单元固定已选版本，渠道可继续前移。 |
| 哪个范围覆盖哪个 | 成员角色与项目共同提供各资源类型的命名空间。先对 Rule 做知识命名空间与标签筛选，再按直接子级同名关系压住共享根。实跑覆盖标签过滤后共享根仍在、两个活跃命名空间的同名规则都按各自路径交付。Skill / Agent 在同名资源争用单个安装位置时有冲突判定。差异来自宿主如何容纳这些内容。多成员工作区还会按各子配置分别解析再合并路径。[选择](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/resources/desired.ts#L596-L637) · [Rule 根覆盖](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/namespace-resolver.ts#L131-L152) · [单位置冲突](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/namespace-resolver.ts#L83-L107) | 保留可解释的候选列表、选中理由和显式覆盖关系。两条互补规则可并存。对于契约点名的一条验收规则，出现两个互斥版本时，保留冲突供有权者选择，再固定本次版本。范围筛选与项目访问权各自校验。 |
| 成员修改与另一人同时发布 | 新规则按资源类型路由到当前项目的知识命名空间。自托管 self 模式的推送比较来源基础版本、成员内容与上游 tip。同一个目标被同事改过时，原生测试得到退出 2，远端保留同事内容。拉取时上游比对受管副本的既有渲染，能认领的旧副本才清除，成员改过的副本保留并提醒可能同时加载两份。[新规则路径实测](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/__tests__/e2e/push-active-namespaces.test.ts#L1140-L1148) · [并发写入](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/push.ts#L1524-L1543) · [受管副本清理与本地改动](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/resources/rules.ts#L1054-L1065) | 发布时核对修改所依据的版本及当前发布权。宿主回报实际文件摘要和本地改动。相互矛盾的内容保留各自来源，原地复用前由当前契约决定如何处置。 |
| 运行中的脚本如何保住原版 | 工作流文件夹的摘要覆盖排序后的相对路径、执行位和正文。启动时把整个文件夹暂存后改名，按摘要复用，并将定义、子流程、文件夹摘要、团队修订放入 Run。上游原生用例在工作开始后更新再删除源文件夹，运行中命令仍输出原始 `as started`。这样主分支继续发布，旧流程仍有可用材料。[目录摘要与固定](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/workflow/folder.ts#L103-L148) · [启动调用](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/workflow/engine.ts#L1508-L1527) · [实际命令](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/__tests__/workflow-folders.test.ts#L372-L388) | 固定核验脚本及其执行依赖，分别保存新旧尝试的 C1/C2、规则和结果。文件夹快照覆盖其内文件；系统二进制、外部依赖与模型配置另以运行事实记录。 |

## 一条经验如何成为可采用的知识

TeamAI 按置信度、赞成票、参与人数和最短年龄筛出可提案的经验。提升时先在临时工作树生成目标 Rule、Skill 或文档，提交到远端评审分支，再为原 learning 登记 `promoted_to`。固定 Git provider 使用人工创建 PR 的提示。实跑中，评审分支仍在时同一经验退出候选；合并后删除分支仍退出候选；未合并便删分支，经验重新成为候选。上游用主分支或当前评审分支的路径历史判断是否处理过这条提案。这个判断服务于抑制重复提案，正式发布应有自己的版本和授权。[候选筛选](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/maintenance/promote.ts#L34-L105) · [检查评审与主线历史](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/maintenance/promote.ts#L140-L162) · [先发布提案、再加标记](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/maintenance/promotion-publish.ts#L76-L137)

失效有两条实有证据。共享 learning 从来源删除后，pull 的镜像与本地索引都删除了对应条目。代码知识的来源时效通过已识别仓库、来源清单和具体文件内容核对。四个用例分别证明：改无关文件且 HEAD 前移仍是 current、同一文件有未提交改动为 stale、原文件确认删除为 missing、来源清单属于另一个仓库为 unknown。3B 可以把这些状态显示在知识引用上，再由知识的适用范围与有权审核者决定怎样修订。外部产品文档要另取其文档修订、段落依据和删除记录。[镜像与检索断言](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/__tests__/pull-learnings-deletion.test.ts#L116-L126) · [来源文件核对](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/codebase-freshness.ts#L284-L333)

## 复跑与证据层次

先在上述固定 TeamAI checkout 执行 `npm ci`、`npm run build`。在 AgentPlatform 仓库下执行以下命令，脚本会建临时团队远端与业务仓，运行完清理。输出中的两次 commit 由当次合成提交生成。

```bash
python3 prototypes/topic-03b/teamai-rule-handoff.py "$TEAMAI_CHECKOUT"
```

以下命令在 TeamAI 仓库根目录执行。本轮共 10 个测试文件、27 个定向用例通过。带 `e2e` 的组运行已构建的真实 CLI，使用上游隔离的本地团队远端。其余组运行对应 TypeScript 实现；其中规则拉取、索引测试按上游夹具替换了配置、网络等协作者，工作流文件夹用例实际运行本地驱动和命令。Hook 返回值与文件写入的覆盖在上表单列。

```bash
run_cases() {
  node ./node_modules/vitest/vitest.mjs run --pool=threads --maxWorkers=1 --no-file-parallelism "$@"
}
run_cases src/__tests__/workflow-folders.test.ts -t 'keeps the files a run started with after the folder changes and after it is deleted'
run_cases src/__tests__/pull-learnings-deletion.test.ts
run_cases src/__tests__/pull-namespace-override.test.ts -t "suppresses the root rule, in tool dirs|keeps the root rule when the tag channel|withdraws the replaced root rule's copy when|delivers both namespace rules when two active"
run_cases src/__tests__/codebase-freshness.test.ts -t 'marks matching decoded content|marks uncommitted source edits stale|marks a source missing|returns unknown when the manifest belongs'
run_cases src/__tests__/codex-hook-rules.test.ts -t 'adds only the rules of the member|adds them to a subagent Codex starts|resume|adds nothing for a tool that reads its own'
run_cases --config vitest.e2e.config.ts src/__tests__/e2e/ownership-rules-agents-993.test.ts -t "keeps edited still-delivered copies and updates an unedited older one|removes the root rule a namespace rule|keeps a member's own rule and agent at a team resource's path"
run_cases --config vitest.e2e.config.ts src/__tests__/e2e/recall-promote-publish.test.ts -t 'keeps the learning out of the candidates while its review branch is open|keeps the learning out once its review is merged|offers the learning again once its review branch is deleted unmerged'
run_cases --config vitest.e2e.config.ts src/__tests__/e2e/pull-team-ref-1183.test.ts -t 'delivers branch resources, follows its tip|keeps a tag fixed|rejects an invalid ref and a failed fetch|fails a contended or incomplete pinned delivery'
run_cases --config vitest.e2e.config.ts src/__tests__/e2e/push-active-namespaces.test.ts -t 'puts a new rule in the active project'
run_cases --config vitest.e2e.config.ts src/__tests__/e2e/self-mode-push-behind.test.ts -t 'refuses with exit 2 when a teammate changed the namespaced file a root rule is pushed to'
```
