# 换宿主后，怎样认出订单核验工具

订单核验员要检查 C2 的三份工作簿。成员已有一个同名的 `inspect_order`，它连接个人服务。接手任务的成员还可能使用另一个宿主。三个项目分别在安装配置、任务派发和工具调用的位置处理同名问题。以下判断采用固定提交的实现、选定的上游测试和一个两服务反例。

## TeamAI 怎样保留成员已有的服务

TeamAI 先把团队定义渲染成宿主实际使用的配置，再按该工具、该服务的管理记录和历史渲染值判断所有权。成员配置碰巧使用同一名称时，写入器保留该项并报告跳过。Claude 的项目本地配置用主工作树的规范化路径寻址，同一仓库的附加工作树可以看到同一组服务。这样，一个工作树执行同步或卸载时，能够识别另一个工作树留下的团队条目，也能保存成员后续的编辑。[工作树定位](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/mcp-reconcile.ts#L389-L419) · [历史配置比对](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/mcp-reconcile.ts#L1549-L1608) · [保留已被占用的配置项](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/mcp-reconcile.ts#L3892-L3909)

实际运行四个 Claude 配置端到端用例，调用编译后的 TeamAI CLI 操作临时 Git 仓库。一个用例先修改项目 `.mcp.json` 内的团队条目 `plain-api`，再切换团队的安装位置并执行 `pull`。磁盘上出现两份同名条目：项目文件保留成员修改，Claude 的项目本地配置保存团队版本。再次执行 `pull --force`，成员修改仍在。另一个用例核对主工作树与附加工作树的同步以及重复同步后的文件字节。这里的直接证据是配置文件、CLI 输出和 Git 状态。宿主实际把哪个服务发给模型，由宿主回合另行取证。[同名条目的两份实际配置](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/__tests__/e2e/claude-mcp-local-915.test.ts#L323-L343) · [主工作树与附加工作树](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/__tests__/e2e/claude-mcp-local-915.test.ts#L228-L249)

追加复跑 7 个配置合并用例及 10 个本地 Agent 所有权用例。Cursor 的个人端点先用了团队名称，协调器报告跳过并保留原地址。另一个用例在 OpenClaw 的共享配置里放入同名个人服务，再故意损坏管理记录，安装命令回报失败，个人地址仍在。维护配置时可以通过保留原值保护成员，对订单派发则还要把“项目工具缺席”反映到节点状态。[个人端点与同名团队配置](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/__tests__/mcp-reconcile.test.ts#L256-L275) · [跨范围的所有权记录](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/__tests__/local-agent-mcp-owners.test.ts#L233-L268)

## Multica 在哪一层决定覆盖和授权

服务端只将显式绑定并启用的工作区服务交给 Agent。同名时，Agent 配置覆盖工作区绑定，本任务的有效 overlay 又覆盖 Agent 配置。daemon 以成员运行时已有的服务为底，再叠加派发配置；其他本地服务可与本任务的服务同时存在。派发配置为 null 时保留宿主原生继承。显式配置交给 Claude 时使用严格 MCP 配置，交给 Codex 时准备独立的受管 TOML。这解释了为什么同一份“已配置”清单不足以确定模型最终看到什么。[工作区绑定与优先级](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/workspace_mcp.go#L18-L48) · [任务 overlay 装配](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon.go#L3018-L3043) · [本地配置合并](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/runtime_mcp_test.go#L186-L222) · [Claude 启动](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/claude.go#L1163-L1185) · [Codex 启动](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/pkg/agent/codex.go#L626-L656)

这里有两个不同的失败处理。通用任务 overlay 无效时，派发方可记录错误并沿用基础配置。Remote MCP broker 准备已批准工具时比对工具名与 schema 摘要；处理调用时再检查工具是否获准，并为带凭证的连接重新解析当前凭证。实际运行 9 个 overlay 单测和 7 个 daemon/broker 顶层用例。撤权用例启动 HTTP 上游，让代理在转发前收到凭证已撤回的结果；请求返回错误，上游收件计数为零。订单的必需工具适合采用后一种处理：若只剩同名个人服务，就记录缺少项目服务并中止本次任务。[失败回退用例](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/mcp_overlay_test.go#L149-L163) · [批准的 schema](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/remote_mcp_broker.go#L169-L183) · [调用授权和转发顺序](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/remote_mcp_broker.go#L268-L309) · [撤回凭证用例](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/remote_mcp_broker_test.go#L119-L141)

## LoopForge 怎样区分别名与安装身份

角色装配先按项目和成员筛选服务。脚本调用入口再从已绑定服务查找 ID、市场 ID、展示名和别名；若命中多个安装项，返回包含候选安装身份的歧义错误。HTTP 服务要求个人授权头时，检查发生在转发前。角色可看见的服务仍然可能同名，因此顺序取第一条会把两个独立安装混在一起。[角色范围](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/assets.go#L118-L160) · [别名来源](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/runtime/mcp_call.go#L196-L219) · [唯一匹配规则](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/runtime/mcp_call.go#L336-L371) · [转发前检查](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/runtime/mcp_call.go#L427-L455)

新增的反例在 LoopForge 原包内调用脚本配置生成器及 CLI 入口。两个独立 HTTP 服务都叫 `Orders`，都接受 `inspect_order({"candidate":"C2"})`，各自记录真实的 `tools/call`。三次操作的累计调用如下。两个安装都被绑定是刻意设置的对照，它能隔离“选对端点”与“允许参与任务”这两个判断。[可复跑的两服务反例](../../../prototypes/topic-03b/cross-host/loopforge_order_alias_test.go)

| CLI 的服务参数 | 退出码 | 项目服务调用数 | 个人服务调用数 | 结果 |
|---|---:|---:|---:|---|
| `Orders` | 1 | 0 | 0 | 列出歧义 |
| `project-install` | 0 | 1 | 0 | 项目服务回执 |
| `member-install` | 0 | 1 | 1 | 个人服务回执 |

同批还运行了 9 个上游用例，覆盖作用域、绑定的 HTTP 调用、错误分类、schema 读取与 runner 恢复。恢复路径在变更状态之前验证冻结的非池化 runner，并在实际派发时复核它是否在线、是否支持该 Agent 的 provider。资源池任务另有重新绑定机制。对订单项目，成员 B 接手时应保留原 Issue、节点、订单版本和验收规则，为 B 重新签发执行身份与工具权限；旧成员的历史调用按原 Run 交付，由平台当前节点决定是否接纳。[重试与重连](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/runner_dispatch.go#L493-L530) · [runner 不存在、离线和能力不匹配的用例](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/runner_cases_test.go#L100-L133)

## 用于订单接手的设计判断

| 时点 | 订单任务固定或复核的事实 |
|---|---|
| 选服务 | 以项目服务标识、版本、工具名及 schema 摘要固定所需能力。个人端点可以保留在成员自己的配置中。 |
| 发起回合 | 比对启动目标与服务实际声明，检查宿主最终送出的项目工具及参数。项目工具缺失、别名指向其他服务、schema 改变分别留下处置记录。 |
| 开始读取 | 服务按签发的本次 Run、成员、宿主、授权代次和候选复核，再检查输入制品。模型传入业务参数；凭证及有效身份由受信的调用侧绑定。 |
| 结果入账 | 用宿主调用 ID、服务回执、结果摘要和 Run 关联，再核对当前 Issue 节点及制品摘要。旧回执仍属于原调用；重投已有结果只形成一次接纳。 |

三份上游代码分别证明配置保留、任务覆盖、唯一端点匹配和部分调用时授权。这些测试没有调用真实模型。项目自己的双宿主实验另外测量回合内的发现、调用、回执及结果接纳；本机签发的两个成员身份和 SQLite 授权库是实验设施。生产的成员登录、设备认证和跨机接手需要相应的身份服务与独立机器参与验证。[订单实验入口](../../../prototypes/topic-03b/cross-host/order_handoff.py)

## 复跑

在上述提交分别检出三个仓库。TeamAI 按锁文件安装依赖并构建 CLI。在仓库根目录运行以下本轮选用的端到端用例。Vitest 输出 4 个通过，其余 7 个按名称过滤。

```bash
node node_modules/vitest/vitest.mjs run --pool=forks --maxWorkers=1 --no-file-parallelism \
  --config vitest.e2e.config.ts src/__tests__/e2e/claude-mcp-local-915.test.ts \
  -t 'a pull in the main checkout|leaves the team.s tracked|turning the option on keeps in .mcp.json|uninstall removes exactly'
```

两组 TeamAI 单元测试可单独执行。第二组在清理时切换进程工作目录，采用独立进程运行。

```bash
node node_modules/vitest/vitest.mjs run --pool=threads --maxWorkers=1 --no-file-parallelism \
  src/__tests__/mcp-reconcile.test.ts \
  -t 'does not overwrite a user-owned server|skips a server whose|is idempotent|keeps a member edit|does not adopt an entry|unreadable ownership record'
node node_modules/vitest/vitest.mjs run --pool=forks --maxWorkers=1 --no-file-parallelism \
  src/__tests__/local-agent-mcp-owners.test.ts \
  -t 'keeps a member edit|does not adopt an entry|unreadable ownership record'
```

在 Multica 的 `server/` 运行两组。第一条只编译被测的 overlay 实现与其测试文件；第二条从 daemon 包选择命名用例。本次为控制编译内存，通过 Go overlay 略去其他测试源文件，保留整个 daemon 实现与所选用例的测试依赖。

```bash
go test -p=1 -parallel=1 -count=1 -vet=off -v ./internal/handler/mcp_overlay.go ./internal/handler/mcp_overlay_test.go
go test -p=1 -parallel=1 -count=1 -vet=off -v ./internal/daemon \
  -run '^Test(ListRuntimeLocalMcpServersCodexRedactsDetails|MergeRuntimeAndAgentMcpConfigClaudeCombinesAndAgentWins|MergeRuntimeAndAgentMcpConfigCodexNormalizesHeaders|MergeRuntimeAndAgentMcpConfigNullKeepsNativeInheritance|RemoteMCPProviderMatrixAndConfigMerge|RemoteMCPProxyRechecksCredentialBeforeUpstreamCall|RemoteMCPProxyFiltersToolsAndInjectsCredential)$'
```

在 LoopForge 根目录，将 `AP_REPO` 设为本项目检出的绝对路径。Go overlay 把新增用例加入原测试包，复用上游 CLI 入口、配置生成器与 HTTP 客户端。命令运行 10 个顶层测试。

```bash
work=$(mktemp -d)
python3 - "$AP_REPO" "$work/overlay.json" <<'PY'
import json, sys
from pathlib import Path
source = Path(sys.argv[1]) / "prototypes/topic-03b/cross-host/loopforge_order_alias_test.go"
target = Path.cwd() / "internal/runtime/order_alias_test.go"
Path(sys.argv[2]).write_text(json.dumps({"Replace": {str(target): str(source.resolve())}}))
PY
go test -p=1 -parallel=1 -count=1 -vet=off -v -overlay "$work/overlay.json" \
  -run '^Test(OrderAliasNeedsUniqueService|MCPCallAliasesMatchURLAndInstallID|MCPCallCLIInvokesBoundHTTPServer|MCPCallRequiresPersonalCredentialAtCallTime|MCPCallConfigServersCarriesIdentityEnvironmentAndWorkingDirectory|ResolveAssetsEnforcesProjectAndPersonalScope|GenericCatalogAssetsIgnoreStoredCrossProjectCollisions|RunnerCallbacksPathsBindingsAndReconnect|CallToolErrors|ListToolsPreservesSchema)$' \
  ./internal/runtime ./internal/engine ./internal/mcpclient
```
