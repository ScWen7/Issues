# TeamAI 把哪个角色的 Skill 交给哪次工作

固定版本为 Tencent/teamai-cli `1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956`。本轮沿实际的角色解析、分发、工作副本准备、正文读取和使用记录追到输出，并用同一份订单工程运行打包后的 CLI。

## 两份同名指引与两份异名指引

团队共享 `order-check`。开发版要求导出付款时间，核验版要求比对各角色可见的订单。开发命名空间还保留一项旧方法 `fast-export`，其中要求省略付款时间。四次调用均在相同的项目目录完成，每次从宿主的 `.claude/skills` 回读实际文件。

| 这次订阅 | 目录中实际得到的内容 |
|---|---|
| 成员未选角色 | `order-check` 是共享版，SHA-256 前八位 `ff97f4b5`。 |
| 只选开发 | 变为开发版 `6dd9d6e0`。`fast-export` 同时落盘。两个不同名称分别要求保留和省略同一列，pull 正常完成。 |
| 同时选开发与核验 | 输出指出 `skills/dev/order-check` 与 `skills/qa/order-check` 冲突，本次保留旧 Skill。进程退出码为 0。磁盘仍是上一轮的开发版 `6dd9d6e0`，旧方法也仍在。 |
| 改为只选核验 | 换成核验版 `dc5f17ee`，此前开发专用的 `fast-export` 被清理。 |

**冲突发生在具体位置。** 扫描器先按可用命名空间选候选，解析器按资源名分组。一个活跃版本可完整替代共享同名版本。两个活跃命名空间竞争同名位置时，pull 跳过这一类 Skill 的更新和清理，并在内部分发结果中记录失败。文件名不同的两份方法各有自己的位置，两者都能落盘。订单节点若涉及验收条件，组装时还要核对方法对“导出的列集合”提出的具体要求。项目可保留旧文件用于追溯，这轮工作所用版本需有自身的选版和交付记录。[分发选择](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/resources/desired.ts#L341-L365) · [同名分组与替换](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/namespace-resolver.ts#L73-L110) · [冲突处置](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/pull.ts#L2748-L2764) · [本轮 CLI 对照](../../../prototypes/topic-03b/composition/teamai_pull_probe.py)

## 步骤角色怎样生效

上表切换的是成员订阅。工作流还支持独立的步骤角色。在该步骤的副本中，Skill、知识、文档等取步骤角色的范围，MCP、模型、环境变量等仍取成员自己的通道。未声明的步骤角色会报错。这样同一个核验步骤可以取得一致的知识，同时沿用执行者已有的操作条件。当前 Skill Driver 缺少为副本装配角色的能力时，预检将这类执行引向支持它的本地驱动。[角色与通道](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/resource-namespaces.ts#L26-L68) · [驱动预检](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/workflow/drivers/skill/preflight.ts#L51-L65)

本地驱动在调用宿主适配器前先准备这次租约的实际工作副本。原生测试中，第一步已经用核验角色执行，模拟的第二次准备遭遇同步锁。即使副本看起来仍是同一角色，第二步也停在 `role_unavailable`，只记录到第一步的适配器调用。同批测试还检查外部驱动自报的角色证据与工作副本记录不一致时采用实际装配记录。这些用例使用真实工作目录和测试工具适配器。AgentPlatform 可复用“开工前读取本次准备结果”的机制，让平台已有的 Issue、节点和尝试持有这份回执。[开工顺序](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/workflow/drivers/local/local-driver.ts#L1274-L1289) · [准备失败诊断](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/workflow/place/role-copy.ts#L229-L245) · [预备记录与锁对照](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/__tests__/workflow-worktree-role.test.ts#L168-L253)

## 方法正文、预算与回执

| 读取或执行入口 | 上游实际行为 | 对订单案例的意义 |
|---|---|---|
| 经验分类与方法正文 | 内置经验提升工作流把操作手册归入 Skill，把强制约束归入 Rule。内置 wiki Skill 自己的正文也列出准确性原则，并按需引用后续阶段。 | 在 AgentPlatform，Playbook 可以提供一种实现或检查路线。只有业务决定、验收条件或获准发布的规则能改变当前节点的硬要求。发布载体的名称不足以确定每段文字的权威。[经验分类](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/workflows/teamai-promote-learning/WORKFLOW.yaml#L13-L23) · [Skill 中的原则](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/skill-data/wiki/SKILL.md#L197-L212) |
| `skill get wiki` 与 `--full` | 默认输出内置 Skill 正文，full 继续附上 references、templates。在本次安装路径，实测默认 18,623 字节，展开后 132,697 字节。正文中安装路径的占位符在输出时替换，绝对长度随安装位置变化。 | 先提供方法入口、作用和本轮所需片段，展开补充文档另占本轮预算。需要完整执行的硬要求保留完整含义。[正文与附件](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/skill-content.ts#L411-L455) |
| `recall ordercheck --depth …` | 同一个项目三次检索，route 只返回目录标记，context 命中正文开头，lookup 同时返回首尾标记。源码中 route 提前返回目录的前 800 个 JS 字符单元，context 取匹配点附近约 300 个字符单元。context 与 lookup 的累计成本按字符长度除以 3.5 估算，首个结果有单独的放行条件。 | 深度控制适合逐步查资料。AgentPlatform 要约束当轮交付的整体大小，还需计入实际选定的角色说明、Skill、Playbook 和工作契约；模型的真实用量单列。[检索路径](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/code-knowledge-recall.ts#L640-L659) · [摘要与估算](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/code-knowledge-recall.ts#L682-L717) |
| 工作流用量和 Skill 使用 | 工作流引擎可依据已报告用量累计步骤消耗，超过预算则停止。Skill 使用观察另外收集宿主技能调用、特定文件读取或已安装技能的提示词提及，并按会话回合去重。原生测试对照了 Codex 同轮先提及再读取只计一次。 | 选进计划、宿主收到正文、工具被调用、验证器检查到效果各存对应凭据；统计使用时引用同一个 Run。提及和读取共用的计数单独作为使用信号。[执行用量控制](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/workflow/engine.ts#L1191-L1202) · [使用信号](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/skill-use.ts#L1-L16) · [原生去重用例](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/__tests__/skill-use.test.ts#L477-L518) |

## 复跑

在固定提交的 TeamAI 仓库准备 Node 24、Git 和 Python 3。前两组共选 4 个完整原生测试文件，101 项单元和预检测试、10 项真实 CLI 端到端测试通过。第三组单独运行工作副本测试的 5 个指定用例，5 项通过，同文件其余 9 项未选。最后一条从临时项目发起四次实际 pull、两次 Skill 展开和三次分深度检索。生成的订单配置、临时 Git 仓库及产物都由探针自行管理。

```bash
npm ci
npm run build
node node_modules/vitest/vitest.mjs run --pool=forks --maxWorkers=1 --no-file-parallelism \
  src/__tests__/skill-use.test.ts src/__tests__/workflow-skill-preflight.test.ts
node node_modules/vitest/vitest.mjs run --pool=forks --maxWorkers=1 --no-file-parallelism --config vitest.e2e.config.ts \
  src/__tests__/e2e/shared-skill-wins-1577.test.ts src/__tests__/e2e/skill-serving-cli.test.ts
node node_modules/vitest/vitest.mjs run --pool=forks --maxWorkers=1 --no-file-parallelism \
  src/__tests__/workflow-worktree-role.test.ts -t 'is held from the skill driver|records for each for_each|starts its session in a copy|fails a step whose preparation|gives a Codex session'
python3 /absolute/path/to/AgentPlatform/prototypes/topic-03b/composition/teamai_pull_probe.py "$PWD"
```
