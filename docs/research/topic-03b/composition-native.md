# Multica 与 LoopForge 怎样把角色、能力和节点要求交给宿主

订单核验者拿到一条“五列导出”的决定，同时还能发现名为“订单核验”的 Skill。如果宿主里又有一份“四列导出”的旧规则，平台需要知道两份规则是否同时进入了输入，Skill 是只出现在目录中、读过正文，还是已经执行过检查。这几件事在两个上游走不同的代码路径。

## Multica

| 源码与实跑 | 对订单节点的启发 |
|---|---|
| 领取任务时，服务端依据任务的 Agent ID 取关联 Skill。按 Daemon 能力发送引用或兼容旧版的完整条目，读取所需集合失败会驳回领取。Daemon 写入 Agent 身份及其自定义指令，把每次运行会变化的项目工作流、代表谁操作等放进当轮消息。上游解释，这样能复用稳定提示前缀，同时让当前操作拿到正确的条件。[领取](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/daemon.go#L3070-L3110) · [身份指令](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/execenv/runtime_config_sections.go#L78-L101) · [每轮材料](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/prompt.go#L52-L80) | 岗位说明可以复用，本次的 D2、节点职责和交付条件绑定此次工作。岗位上的能力清单也要与实际接收者、宿主和本轮选版对应。 |
| 项目接管状态规则时，Daemon 省略内建状态清单，引导 Agent 使用当前项目工作流给出的命令。原生测试对照了没有工作流、普通成员、有工作流的 Squad Leader。项目指令替换了内建的状态做法，Leader 的派发职责仍在。[分支](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/execenv/runtime_config_sections.go#L340-L351) · [对照](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/execenv/runtime_config_project_workflow_test.go#L20-L96) | 已知来源、适用范围及替代关系时，组装器可在发送前消除该处冲突。一次状态规则替代无需丢弃整个角色。 |
| Skill 目录用实际分配的路径名。即使两个显示名归一化为同一个目录名，目录与正文位置仍能对应。带有 `disable-model-invocation` 的 Skill 可以落盘，同时从模型可调用清单中省略。文件回执还校验配套文件，测试中等长改写附件会改变摘要，缺一份声明的附件就拿不到完整包摘要。[目录生成](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/execenv/skill_visibility.go#L9-L82) · [落盘对照](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/execenv/skill_visibility_test.go#L253-L297) · [包回执](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/execenv/receipt_test.go#L9-L45) | 可按需先送入口和用途。资产记录用稳定身份和摘要，宿主清单写实际可定位的名称。只有文件回执时报告“已准备”；正文加载和脚本实际运行各取相应回执。 |
| 远程 MCP 经 Broker 接入。启动时发现上游工具，比对已批准的名称和参数结构。必需工具失踪或结构漂移时启动失败，可选连接出错时返回诊断并继续。请求到来还会检查工具是否获批，在转发前重新解析凭据。对照中未批准的工具及已撤销的凭据都没有触发上游调用。[启动](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/remote_mcp_broker.go#L55-L105) · [转发前检查](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/daemon/remote_mcp_broker.go#L268-L309) | 角色或 Playbook 提到某项工具，只能成为选用理由。平台仍需依据任务权限判断可否调用，并将实际工具结果关联本轮核验。 |

实跑使用 Go 1.26.9。11 项环境准备测试与 6 项 Daemon 测试全部通过。Daemon 测试使用上游回环 MCP 服务与凭据夹具，覆盖真实 Broker 路径。本轮为控制编译资源，仅对 Daemon 测试包使用 overlay 省略未参测的测试文件。完整上游工作副本可直接从 `server` 目录执行下面两条。

```bash
go test -count=1 -parallel=1 -v -run '^Test(SeedUserCodexSkillsYieldsToWorkspaceSkill|RuntimeSkillPoliciesYieldToWorkspaceSkills|BriefWithProjectWorkflowDropsBuiltInStatusRules|BriefWithProjectWorkflowKeepsSquadLeaderDispatchRule|BriefWithoutProjectWorkflowKeepsBuiltInStatusRules|RenderedSkillListsHideDisableModelInvocationSkills|SkillListingNamesMatchDirectoriesOnBatchSlugCollision|BatchSlugAllocationCountsHiddenSkills|WriteContextFilesHydratesDisableModelInvocationSkillButDoesNotAdvertiseIt|SkillReceiptIncludesWrittenSupportingFiles|PlatformSkillHintsRequireBuiltinIdentity)$' ./internal/daemon/execenv
go test -count=1 -parallel=1 -v -run '^TestRemoteMCP(StartupAcceptsAnApprovedToolSet|StartupRefusesWhenAnApprovedToolIsMissing|StartupRefusesWhenAnApprovedSchemaDrifted|StartupDegradesAnOptionalConnectionInsteadOfFailingTheTask|ProxyRejectsUnapprovedToolWithoutCallingUpstream|ProxyRechecksCredentialBeforeUpstreamCall)$' ./internal/daemon
```

## LoopForge

**节点任务书与宿主配置分开组装。** 角色节点以角色说明、该节点交付物、角色配置的门禁和重试策略生成任务书，再加入 Run 输入、上游结果和人工补充。上游专门测试了审批节点的 `TaskPrompt` 不进入角色节点。普通执行还补上本节点制品契约；命中原生会话恢复分支时，代码将当轮任务书替换为接续提示及可用的反馈，再按需要加提交门禁的指令。由此，对已换版标准的接续应检查当轮实际输入。[任务书](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/prompt.go#L194-L219) · [输入与上下游](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/prompt.go#L24-L93) · [执行与恢复](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/node_execute.go#L706-L737)

**系统文件里的 Rule 和 Skill 走不同路径。** 引擎从角色绑定解析项目适用的 Rule、Skill 与 MCP，又补入适用于当前 SOP 的全局 Rule。相同规则 ID 去重。运行层按优先级降序把规则全文写进系统文件，并把 Skill 的名称、用途、入口文件和相对根目录列在后面。Skill 正文及配套文件保存在独立目录，供宿主按入口取用。这样的结构让多个节点复用同一能力包，同时保留每个角色自己的绑定。[角色资源](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/assets.go#L78-L143) · [全局规则](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/assets.go#L163-L191) · [Skill 目录和正文](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/runtime/materialize.go#L113-L158) · [Rule 排序](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/runtime/materialize.go#L204-L225)

**订单反例。** 给同一个核验角色绑定两条相反的规则，D2 的优先级为 9，要求导出五列；历史规则的优先级为 1，要求导出四列。调用上游 Codex 配置生成路径成功。读回同一份 `agent-system.md`，五列和四列两段正文各出现一次，顺序与优先级一致。订单核验 Skill 的名称进入目录，核验方法的正文只出现在角色绑定的 `SKILL.md` 中。本对照到实际文件为止，没有启动 Codex。对 AgentPlatform 而言，优先级适合排阅读顺序。影响验收结果的相反要求应查有效 Issue 决定与正式替代关系，欠缺依据时再交已有决定权的人处理。[订单反例](../../../prototypes/topic-03b/composition/loopforge_composition_test.go)

**预算和裁决属于不同机制。** 在 CodeBuddy 上游用例里，任务书超过 96 KiB 会从命令行移入系统文件，原文仍然保留。该上限保护进程参数传递；Role、Skill 和 Playbook 共同受限时，仍需明确哪些内容占用了本次输入额度。另一个真实引擎用例把人工门禁排在配置首位，实际运行先冻结制品、执行命令检查，然后等待人工批准。HTTP 的 Run 批准沿用项目写权限检查，引擎要求节点正在等待批准，随后记录决定制品。AgentPlatform 可复用显式门禁和证据顺序；业务标准变更仍由该 Issue 现有决定权处理，普通建议由执行者按范围取舍。[参数阈值](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/runtime/provider.go#L97-L109) · [写文件用例](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/runtime/runtime_test.go#L2221-L2239) · [门禁与制品对照](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/engine_test.go#L2464-L2519) · [项目权限](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/httpapi/project_write_access.go#L15-L58) · [批准决定](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/engine/run_ops.go#L140-L178)

实跑使用 Go 1.26.11。在固定版本的 LoopForge 根目录设置 `AP_REPO` 指向本项目，以下 11 个上游测试和 1 个新增反例均通过。引擎用例使用测试 SQLite、模拟 Agent 执行器和实际命令检查；超长参数用例使用上游可观测的沙箱替身。

```bash
export AP_REPO=/absolute/path/to/AgentPlatform
work=$(mktemp -d)
python3 - "$work/overlay.json" <<'PY'
import json, os, sys
from pathlib import Path
target = Path.cwd() / 'internal/runtime/order_composition_test.go'
probe = Path(os.environ['AP_REPO']) / 'prototypes/topic-03b/composition/loopforge_composition_test.go'
Path(sys.argv[1]).write_text(json.dumps({'Replace': {str(target): str(probe.resolve())}}))
PY
go test -p=1 -count=1 -parallel=1 -vet=off -overlay "$work/overlay.json" -v -run '^Test(OrderRulesAndSkillAtMaterialization|RoleMCPServerVisible|RunContextReachesRolesAndNodeTaskPromptDoesNot|RolePromptCompilesTaskbook|AutomaticGatesAndArtifactsCompleteBeforeManualApproval|GateOnFailureIsConfiguredNotInferred|MaterializeAgentRulesSortsWritesAndLinks|MaterializeSelectedSkillsListsInvocationNameAndRoot|MaterializeUploadedSkillMdOverridesPayloadContent)$' ./internal/engine ./internal/runtime
go test -p=1 -count=1 -parallel=1 -v -run '^Test(OversizedPromptMovesOffArgvIntoSystemFile|ApproveWithHumanContextReachesDownstream|ProjectContentWritesRequireMembership)$' ./internal/runtime ./internal/engine ./internal/httpapi
```
