# Multica 与 LoopForge 如何发布、选用和切换执行资产

订单导出要区分三件事。成员可以保存新规则，管理员可以把它发布到指定范围，而运行中的核验节点还可能用着先前的脚本。下面沿两个固定上游的实际写入、选择和执行路径核对这个差异。[Multica 固定提交](https://github.com/multica-ai/multica/tree/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc) · [LoopForge 固定提交](https://github.com/Tencent/LoopForge/tree/97b3cdc2f29a88e8767a8dc6c03bfb8865622653)

## Multica

| 路径 | 源码、测试与本项目选择 |
|---|---|
| 工作区 Skill 编辑与恢复 | 普通 Skill 的管理者是创建者或工作区 owner/admin。写入事务锁定 Skill，旧数据首次修改前补基线，写后对名称、描述、正文及按路径排序的附件计算指纹。保存相同内容跳过新版本。恢复 v1 会替换当前正文和附件，并在内容改变时追加带来源的版本。测试中单文件变更为 v3，恢复 v1 后得到 v4 并移除后来新增的文件。配置与启用范围有各自的记录，删除 Skill 会清掉这份原生历史。AgentPlatform 若需在资产退役后重放某次验证，须单独保留当时选用的版本内容或可读取的不变引用。[编辑权](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/skill.go#L574-L597) · [历史写入](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/skill_version.go#L68-L177) · [恢复与删除实测](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/skill_version_test.go#L47-L138) |
| 已领取的任务如何取到 Skill | 领取时支持精简传输的 Daemon 收到 Skill 引用，准备时先查本机已校验缓存，缺项才以任务、Runtime、来源和 Skill ID 向中心解析。服务端核对任务还处在准备状态，只加载该 Agent 已绑定并启用的条目。DB handler 用例中仅请求一项就仅查询该项，未分配、禁用、跨工作区及错误来源均返回 404，数据库读取错误返回 500。Daemon 回环测试中，普通工作区 Skill 的旧引用在缓存未命中时收到中心当前的新内容与 hash，实际任务接受新版并按新 hash 缓存。插件 Skill 发生同样的 hash 漂移则失败。这样的设计让普通材料的更新可达、下载可复用，插件继续使用批准过的包。对决定验收的 Rule / Script，AgentPlatform 要传不可变版本引用，并在执行前比对实际摘要。[领取](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon.go#L3078-L3097) · [授权与返回值](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon.go#L4506-L4586) · [缓存与解析](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/daemon.go#L7273-L7309) · [两种 hash 的验证](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/daemon.go#L7342-L7368) |
| 发布包和现场安装 | 插件包提供另一种可复用机制。管理路由按 workspace owner/admin 校验，预览展示所选版本要求的 scopes，安装请求携带版本 ID 和授予的 scopes。安装事务内再次核对该版本仍属于本工作区。上传包的同版本冲突，新包发布后，已安装版本及对应脚本仍保持旧版，显式升级才切换。这里的脚本是上游插件面板的脚本。对订单核验可借用“发布可用版本 → 选择具体版本 → 执行实物”的关系，并使用本项目的受管 Script 执行器。[路由与两步安装](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/cmd/server/router.go#L1841-L1885) · [版本与安装复核](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/service/plugin_package.go#L392-L428) · [发布、安装与升级的原始用例](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/plugin_package_test.go#L198-L259) |

历史记录的 content_hash 与运行分发的 bundle hash 使用不同编码。后者计入来源、Skill ID、各文件路径、文件摘要及正文。相同 Skill 的历史行和宿主回执要通过发布包的映射关联，同时保存摘要的对象与算法。宿主侧一次文件写入、将内容真正放进当前模型请求、执行了脚本、核验通过，分别由专题三 A 的相应回执提供。[历史指纹](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/skill_version.go#L164-L180) · [分发包指纹](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/skillbundle/hash.go#L41-L83) · [3A 回执](../../architecture/execution-capabilities.md)

## LoopForge

| 路径 | 源码、实测与本项目选择 |
|---|---|
| 保存和发布 | 项目 SOP 的写入检查项目写权限，发布通用模板还校验平台管理员。保存校验 Revision，改变内容时递增并保留上次 PublishedRevision，发布在事务中锁住目录项，提升 Version 并标记本次发布的 Revision。原生 SQLite 用例分别验证普通和通用模板，无内容变化时重复保存或发布均保持原值。AgentPlatform 可复用编辑冲突检测和发布幂等。[权限](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/httpapi/catalog.go#L1131-L1148) · [发布入口](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/httpapi/catalog.go#L1251-L1271) · [保存与发布](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/repo/catalog.go#L463-L560) |
| 新 Run、原 Run 和显式刷新 | 新 Run 从当前目录读取定义并保存完整快照。原 Run 正常推进时消费自己的快照，RefreshRunSOP 仅在已停止或等待且无活动节点的相应状态接受请求，保留原沙箱和同 ID 节点结果，新增节点置 pending。它调用的 latestWorkflowDefinition 直接读目录当前行。下述反例用刚保存、尚未再次发布的核验脚本证实这一点。[启动读什么](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/run_start.go#L53-L69) · [写入快照](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/run_start.go#L150-L162) · [目录查找](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/workflow_graph.go#L34-L50) · [停止后刷新](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/run_ops.go#L812-L865) |
| Rule 与脚本的解析时点 | Agent 节点按角色绑定查询当前目录中的 Rule、Skill，限制项目或共享范围，再追加绑定本 SOP 的全局规则并按 ID 去重。原生实测过滤外项目私有规则，纳入共享且绑定本 SOP 的规则。脚本节点直接运行图中脚本或命令，普通 Script 节点不会因为给 Agent 配了全局 Rule 就得到那条提示。重试还可局部覆盖节点的 Agent/Executor、制品和重试等绑定，同时抬高快照的 Version，其中不含 Script 正文。一个 SOP 显示的版本号不足以还原该次核验用料。[规则与技能解析](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/assets.go#L78-L117) · [SOP 全局规则](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/assets.go#L163-L192) · [执行脚本](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/node_execute.go#L597-L637) · [局部覆盖的字段](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/run_ops.go#L960-L996) |

### 反例：保存检查脚本后，旧成功会发生什么

在原生引擎和上游内存 SQLite 存储中，先发布只含 `check` 节点的 SOP，脚本内容为 `printf 'check-v1'`。按公开 Start 调用启动第一条 Run 后，使用目录写入接口只保存第二版脚本 `printf 'check-v2'`。两份脚本仅用来标记版本，探针关闭工作进程，向旧节点填入一条明确标识的模拟输出，验证目录与结果归属。[可复跑探针](../../../prototypes/topic-03b/loopforge_saved_revision_test.go)

| 操作 | 实际观察 |
|---|---|
| 发布，再只保存编辑 | 发布 v2、Revision 2。保存后 Revision 3、PublishedRevision 2、Version 仍为 2 |
| 查原 Run，再开新 Run | 原 Run 仍持有 check-v1，新 Run 已取得尚未再次发布的 Revision 3 和 check-v2 |
| 正在运行时请求刷新，然后转为等待状态再显式刷新 | 前一次被拒。后一请求替换图中脚本为 check-v2，同 ID 的原节点仍是 succeeded，输出仍为 旧 Run 在 check-v1 下的模拟结果 |

因此，订单 Issue 确认 D2、项目发布相应资产时，3B 将 Rule、核验 Script 和适用范围按不可变版本交给本次选择。专题二用原 Node Attempt 判断已有结果是否还能满足新标准，受影响的成功需由指定核验器重验。专题三 A 回报实际运行的脚本、候选、制品及检查证据。订单实测中，旧标准对应 four-column-control 在 D1 下的对照。3A 的 C1 与 C2 都使用 D2，C1 在 A2 核验失败。两次核验各自保留其实际候选、版本和输出。

## 复跑

Multica 固定提交的 server 目录使用 Go 1.26.9 和一次性 PostgreSQL 17.5，数据库已迁移至 657。下面是原仓库定向命令。本次资源有限的执行环境用 Go overlay 排除未参测的 `*_test.go`，保留上游用例及依赖的原测试辅助函数，生产文件保持固定提交版本。handler 断言直接进入 handler 并走真实数据库，路由上的角色校验以源码为据，Daemon 测试在回环 HTTP 中由夹具返回新旧 bundle。10 项 handler 和 3 项 Daemon 用例全部通过。三个插件用例覆盖新版发布、同版覆盖和已安装包删除，新版发布用例还回读已安装工作区的页面脚本。

```bash
# 从 Multica/server 运行，先将 DATABASE_URL 指向已创建的一次性测试库。
: "${DATABASE_URL:?set disposable PostgreSQL database URL}"
go run ./cmd/migrate up
go test -count=1 -parallel=1 -run '^(TestSkillVersion(Lifecycle|BaselineForUnversionedSkill|BaselineForUnversionedSkillFileWrites|SkipsPluginSkills)|TestResolveTaskSkillBundles_(LoadsOnlyTheRequestedSkill|RefusesSkillsTheAgentCannotSee|ScopedReadFailureReturns500)|TestPublishingANewVersionDoesNotChangeAnInstalledWorkspace|TestPublishRefusesToOverwriteAnExistingVersion|TestDeletePublishedPackageRefusesWhileInstalled)$' -v ./internal/handler
go test -count=1 -parallel=1 -run '^TestEnsureTaskSkillBundles_(CachesEachSuccessAcrossDispatches|AcceptsServerSideSkillUpdate|RejectsPluginHashDrift)$' -v ./internal/daemon
```

LoopForge 使用 Go 1.26.11 和项目测试库 SQLite。在该上游根目录设置 `AP_REPO` 指向 AgentPlatform 仓库，以 Go overlay 加入反例。作用域与刷新行为的 5 项上游引擎测试、1 项原生发布测试（项目/通用两个分支）、1 项新增反例均通过。这里验证单机 SQLite 的发布与读取语义，生产数据库跨进程并发发布需运行上游的 MySQL 专项。

```bash
export AP_REPO=/absolute/path/to/agentplatform
work=$(mktemp -d)
python3 - "$work/overlay.json" <<'PY'
import json, os, sys
from pathlib import Path
here = Path.cwd()
probe = Path(os.environ["AP_REPO"]) / "prototypes/topic-03b/loopforge_saved_revision_test.go"
Path(sys.argv[1]).write_text(json.dumps({"Replace": {
    str(here / "internal/engine/agentplatform_saved_revision_test.go"): str(probe.resolve())
}}))
PY
go test -count=1 -parallel=1 -run '^TestWorkflowPublishOnlyAfterChanges$' -v ./internal/repo
go test -count=1 -parallel=1 -vet=off -overlay "$work/overlay.json" -run '^Test(AgentPlatformSavedRevisionAndRunningEvidence|GlobalRuleInjectsIntoEveryNodeOfBoundWorkflow|OverlayLatestNodeBindingsRefreshesArtifactContracts|RefreshRunSOPPreservesCompletedNodesAndAddsLatestNodes|RefreshWorkflowForStoppedRunStatuses|FailedRunCanRefreshSOPThenReplayWithContext)$' -v ./internal/engine
```
