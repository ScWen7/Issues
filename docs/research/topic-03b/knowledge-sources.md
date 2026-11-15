# 项目知识从哪里来，开发和核验如何选段

订单产品经理继续维护订单导出约定。开发节点读取共同业务约定和实现说明，独立核验节点读取同一约定与核验说明。交付记录须能定位本轮送入的章节，并查出哪些运行受到来源修订或读权变化的影响。

## TeamAI 如何形成可搜索的知识

| 源码路径 | 设计动机与实测 |
|---|---|
| iWiki 页面 → 导入目录 → 受管理的章节 | 按页 ID 下载，逐页生成 Markdown 和 `iwiki://p/<docid>` 引用。一批下载允许部分成功；导入的受管理章节记录来源、章节键和同步时间。启用审核后，候选先进入队列，通过后才写入目标章节。两项审核测试验证了排队与应用。这样可以在本地维护派生说明并保留编辑流程。本项目另记原文修订、原章节或块 ID 和最后完整核对时间。一次导入的成功数不足以证明缺页已由作者撤回。[读取与写入](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/import-iwiki.ts#L56-L159) · [受管章节](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/iwiki-dual.ts#L176-L235) · [审核测试](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/__tests__/iwiki-review-apply.test.ts#L94-L137) |
| 源文件 → 增量索引 | 索引检查设备、inode、字节长度、mtime 与 ctime；元数据变化时读取内容，以 SHA-256 判断能否复用分词。索引从本次仍被选择的文件重建，再原子替换。测试中等长改写并恢复 mtime 仍更新索引，删除文件的旧条目消失。另一个入口只对最终展示的代码来源锚点检查仓库身份、相对路径与基线摘要，分别报告 current、stale、missing、unknown。这个核对针对代码文件，iWiki 访问权和文档版本仍须从原系统取证。[缓存键与指纹](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/utils/search-index.ts#L487-L506) · [读取与复用](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/utils/search-index.ts#L570-L607) · [整份替换](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/utils/search-index.ts#L1057-L1075) · [逐锚点核对](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/codebase-freshness.ts#L241-L334) |
| 工作流步骤角色 → 专属索引 | 步骤角色取代成员在知识类资源上的角色，活动项目再提供其命名空间。成员自己的角色继续决定 MCP、模型、环境变量等通道。清单声明过但未激活的 wiki 命名空间被剔除，未声明的沿用共享语义。测试在真实 Git worktree 中启动一次冷检索，核验角色的经验只在该副本命中。角色或成员索引重建和源更新会使其他受影响的副本索引失效。这里可借鉴的是岗位材料和能力授权分别求值；外部文档另查该接收者在原系统的权限。[角色与通道](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/resource-namespaces.ts#L26-L68) · [项目与角色合并](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/resource-namespaces.ts#L237-L294) · [副本检索与失效测试](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/__tests__/recall-step-role.test.ts#L100-L172) |
| 可见页面、目录、图 → 排序、摘录 | 代码 wiki 先移除未激活仓库，再对可用页面计算 BM25 和图加权。目录按章节重建，跨仓关系按来源过滤；缺少归属的混合目录项被去掉。实测隐藏仓库的名称、描述、关联文件、整组标题均未从这些旁路返回，同时保留无关的可见边。最后才按深度和预算取命中片段。摘录和排名依赖查询，项目引用因此独立保存原始章节身份、版本和所用文本摘要。[目录与候选集](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/code-knowledge-recall.ts#L305-L410) · [来源图](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/graph-aggregate.ts#L193-L256) · [排序与截取](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/code-knowledge-recall.ts#L636-L745) |

## Multica 在何处检查可见性，旧资料怎样退出索引

任务领取时按照工作区和项目两项标识查询项目，再取资源。Issue、Chat、Autopilot 和快速创建共用同一个解析函数。项目绑定的仓库优先，软引用落空则回退到工作区仓库，数据库读取失败则返回错误以便稍后再领取。交给 Daemon 的内容是项目标题、描述、资源和仓库，宿主侧还会写项目资源清单。项目明确引用的必需业务文档若消失，订单节点应显示缺少该来源并等待重新选取。[领取解析](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/project_resource.go#L965-L1050) · [宿主配置](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/execenv/runtime_config_sections.go#L516-L551)

私有项目的普通成员请求按该成员读取。运行请求从已记录任务取得发起者，缺失时取问责成员，再结合 Agent 所有者；任一主体看不到的私有项目都被过滤。这让管理员发起的任务也受到实际执行主体权限约束。数据库反例中，同一个 Agent 任务在所有者仍是项目成员时读取 Issue 返回 200。移除所有者后，发起管理员仍返回 200，原成员和同一任务都得到 404；测试先读 Issue，再拉搜索变更，避免把结果归因于本地索引清除。[请求主体解析](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/project_access.go#L18-L79) · [权限合并](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/projectaccess/projectaccess.go#L117-L176) · [本轮反例](../../../prototypes/topic-03b/knowledge/multica_knowledge_revocation_test.go)

实体变动后，搜索同步从 PostgreSQL 快照游标拉取增量，以新事务可见性覆盖晚提交。游标落在已清理历史之前会得到 410 并要求重建。授权变动也会重新登记项目、Issue 和评论；下一轮同步针对接收者计算可见性，对刚失权者返回这些实体的删除 ID。客户端先把增删和新游标一起写入存储，然后更新内存检索。反例实测只有原成员失权，文档正文未动，三个实体都收到删除 ID，公开对照 Issue 保留。上游基础用例还覆盖改名、评论更新、软删及 Issue 删除级联。[事务可见性](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/search_index.sql#L74-L98) · [变更扇出](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/db/queries/project_member.sql#L78-L98) · [按读者生成删除项](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/search_index.go#L546-L618) · [客户端消费](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/packages/core/search-index/sync.ts#L291-L314)

撤成员路径先写入成员删除，再通知搜索索引；通知出错只记日志，接口仍返回 204。这个故障分支来自源码，测试覆盖常规通知成功。因而即使本地缓存已有命中，AgentPlatform 在向宿主交付前仍要复核来源当前权限与修订；失权后清除可检索副本也有独立价值。已送达的正文仍可能保留在原宿主历史。后续交付和历史查看各自重新判断接收者资格。[撤权及通知结果](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/project_member.go#L419-L436)

## 订单案例采用的约束

| 变化 | 平台如何处置 |
|---|---|
| 同一文档供两个角色使用 | 先用 Issue、项目、节点尝试绑定接收成员和角色，再取该角色所需章节并核对原文读权。开发接收共同约定及开发说明，独立核验接收共同约定及核验说明。交付记录关联来源、修订、章节或块、片段摘要及宿主轮次。 |
| 普通编辑或章节移动 | 按同一修订读完全部分页后替换索引，比较稳定章节键和正文摘要。正文变化先找使用旧段的运行；未改正文的段可保留相同内容摘要，引用修订按本轮实际选用记录。 |
| 撤回、失权、暂时读不到 | 原系统确认撤回会影响该来源的全部接收者；移除单个成员的读权只影响该主体及受其权限约束的运行。缺页、网络失败或读权服务异常时保留最近一次完整核对时间，将当前选用标为待复核，延后该必需输入。 |
| 从检索到宿主投递之间发生变化 | 排队保存引用，投递时再查成员、项目、源读权、源修订及段摘要。原始入口继续留在产品编辑系统；索引、候选摘要和已知的检索分数都不授予读权。宿主实际收到哪些正文另由当前轮次的输入证据说明。 |

## 定向复跑

TeamAI 在固定提交 `1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956`、Node 24.22.1 上执行。前三个文件 25 项，后四个 17 项，合计 42 项。涉及 Git worktree 和 `process.chdir` 的用例使用 forks。iWiki 测试验证本地生成、审核与受管章节写入，未调用在线 iWiki 服务。

```bash
# 在 Tencent/teamai-cli 根目录
npm ci
node node_modules/vitest/vitest.mjs run --pool=threads --maxWorkers=1 --no-file-parallelism \
  src/__tests__/search-index-incremental.test.ts src/__tests__/resource-namespaces-wiki.test.ts \
  src/__tests__/code-knowledge-recall-wiki-scope.test.ts
node node_modules/vitest/vitest.mjs run --pool=forks --maxWorkers=1 --no-file-parallelism \
  src/__tests__/recall-step-role.test.ts src/__tests__/resource-namespaces-step-role.test.ts \
  src/__tests__/import-iwiki-reconcile.test.ts src/__tests__/iwiki-review-apply.test.ts
```

Multica 使用固定提交 `fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc`、Go 1.26.9、已迁移至 657 的一次性 PostgreSQL 17.5。5 项上游 handler 和 1 项新增失权反例使用真实数据库，另 3 项 projectaccess 单元用例通过。执行环境用 Go overlay 裁去无关测试文件，保留所选用例、上游 fixture 和全部原生产实现。以下为在完整上游测试包中运行同批断言的命令；DATABASE_URL 需指向专用的空白测试库。

```bash
# 在 multica-ai/multica/server 目录
export AP_REPO=/absolute/path/to/AgentPlatform
: "${DATABASE_URL:?set DATABASE_URL to the disposable PostgreSQL database}"
go run ./cmd/migrate up
work=$(mktemp -d)
python3 - "$work/overlay.json" <<'PY'
import json, os, sys
from pathlib import Path
target = Path.cwd() / 'internal/handler/knowledge_revocation_test.go'
test = Path(os.environ['AP_REPO']) / 'prototypes/topic-03b/knowledge/multica_knowledge_revocation_test.go'
Path(sys.argv[1]).write_text(json.dumps({'Replace': {str(target): str(test.resolve())}}))
PY
go test -count=1 -parallel=1 -overlay "$work/overlay.json" \
  -run '^Test(KnowledgeReaderRevokedAfterSnapshot|PrivateProjectRevocationDeletesProjectFromSearchIndex|PrivateProjectSearchIndexManifestLeavesOutHiddenRows|SearchIndexBootstrapThenCatchUp|SearchIndexChangesDeliverLateCommits|SearchIndexChangesExpireAfterPruning)$' -v ./internal/handler
go test -count=1 \
  -run '^Test(ForPrincipals|RunPrincipalsFallsBackToAccountableUser|TasksProjectsBatchesHistoryAndQuickCreateParents)$' -v ./internal/projectaccess
```
