# VS-2 · Multica 交付、附件与 PR 完成路径源码取证

> 固定源码基准：multica-ai/multica @ 71683141a764ed3b1620db4bc26a2d0a098f135c（2026-11-17 main）。
> 本文只记录该快照实际证明的机制，不将 AgentPlatform 的 Candidate / Acceptance 设计误写为 Multica 原生能力。

## 1. 结论

Multica 提供附件上传、评论附件关联、交付文件分组与历史版本浏览、Issue revision 条件写入、PR 关联和 PR 自动状态推进。

它没有提供一份不可变的多 Artifact Candidate Manifest，也没有将具名 Acceptance Decision / 验收标准接入所有 Issue 完成入口。

因此 AgentPlatform 应复用 Multica 的来源与执行事实，在其上补齐 Candidate、Evidence Applicability、Acceptance Decision 和统一 Completion Gate 的业务语义。

## 2. 附件与交付文件分组

### 2.1 交付区是文件分组视图

源码：
- [deliverables.ts](https://github.com/multica-ai/multica/blob/71683141a764ed3b1620db4bc26a2d0a098f135c/packages/core/attachments/deliverables.ts)
- [交付详情组件](https://github.com/multica-ai/multica/blob/71683141a764ed3b1620db4bc26a2d0a098f135c/packages/views/issues/components/deliverables/deliverable-details.tsx)

该实现以规范化 Content-Type + Filename 形成文件分组身份，保留每组的版本列表，并以最后上传项作为 latest。详情组件可按附件 ID 选择历史版本；“最新链接”按文件名定位当前 latest。

这能回答“同一个文件名上传过哪些版本”，不能回答“本次验收的组合包含哪些文件、代码修订和报告”。Candidate 不能使用文件分组 key 或 latest URL 作为身份。

### 2.2 上传与评论关联

源码：
- [CreateComment 与附件锁定](https://github.com/multica-ai/multica/blob/71683141a764ed3b1620db4bc26a2d0a098f135c/server/internal/handler/comment.go)
- [附件 SQL](https://github.com/multica-ai/multica/blob/71683141a764ed3b1620db4bc26a2d0a098f135c/server/pkg/db/queries/attachment.sql)

CreateComment 在事务中锁定并核对待关联附件，再创建评论并关联附件。附件锁定查询按 Issue → Comment → Attachment 的顺序，避免并发删除 / 修改造成不一致。

这证明评论与附件关联可以原子提交；不证明评论或附件集合是不可变的验收快照。

### 2.3 附件可被修改或删除

源码：
- [附件删除入口](https://github.com/multica-ai/multica/blob/71683141a764ed3b1620db4bc26a2d0a098f135c/server/internal/handler/file.go)
- [附件查询与删除 SQL](https://github.com/multica-ai/multica/blob/71683141a764ed3b1620db4bc26a2d0a098f135c/server/pkg/db/queries/attachment.sql)

Multica 提供附件删除入口，并允许对评论附件集合进行更新。因此 Attachment ID 可作为历史定位身份，但不能单独证明字节内容永久保留。AgentPlatform 需要固定内容摘要 / 不可变存储版本，并把来源可取得性、内容完整性和当前读权限分开处理。

## 3. Issue revision 是并发保护，不是 Candidate 身份

源码：
- [Issue 更新 Handler](https://github.com/multica-ai/multica/blob/71683141a764ed3b1620db4bc26a2d0a098f135c/server/internal/handler/issue.go)
- [Issue 条件写入 SQL](https://github.com/multica-ai/multica/blob/71683141a764ed3b1620db4bc26a2d0a098f135c/server/pkg/db/queries/issue.sql)

Handler 读取当前 Issue 并验证 expected_revision；SQL 在真正更新行时再次检查 revision。评论、状态和其他字段更新也可能推进 Issue revision。

所以 revision 可以保护基于旧 Issue 快照的写入，但不能标识被验收的 Candidate。无关评论造成 revision 冲突时，客户端可重读后重新验证 Candidate / 标准 / 权限；若候选本身变化则不能仅重试旧 Accept。

## 4. PR 自动完成的实际边界

源码：
- [PR 自动完成决策与入口](https://github.com/multica-ai/multica/blob/71683141a764ed3b1620db4bc26a2d0a098f135c/server/internal/handler/pr_auto_complete.go)
- [PR 自动完成条件 SQL](https://github.com/multica-ai/multica/blob/71683141a764ed3b1620db4bc26a2d0a098f135c/server/pkg/db/queries/pr_automation.sql)

PR 自动完成先读取 Issue 关联 PR 状态并检查配置、Issue 当前状态、Triage 和项目 Workflow；只有全部关联 PR merged 才进入事务。事务 SQL 再核对 Issue 仍处于决策时看到的状态、仍存在关联 PR 且所有关联 PR 在写入时仍已合并。

这提供了 PR 集合变化与并发合并的条件状态写入保护，但没有比较 AgentPlatform Candidate Manifest、验收人、Acceptance Decision 或 Work Agreement 标准版本。

因此 PR 自动完成只能作为 Completion Gate 的一个触发来源；具名验收是本项完成条件时，不得让 PR 路径旁路验收。

## 5. AgentPlatform 的承载决策

| Multica 已有事实 | 可直接复用 | AgentPlatform 补充 |
|---|---|---|
| Attachment ID、文件名、Content-Type、下载权限 | 上传、读取、评论关联、附件来源 | Artifact ID / Digest / 不可变 Locator / Availability |
| 同名文件版本分组 | 浏览历史上传版本 | Candidate Manifest 固定多类型 Artifact 组合 |
| Issue expected_revision | 条件写入 Issue 行 | 独立 Candidate Generation 与当前候选比较 |
| PR identity / state / merge commit | PR 工程状态和 webhook | 固定 PR Head / Merge / CI Artifact 来源，验收时检查适用版本 |
| PR 自动完成事务 | 检查关联 PR 集合并条件推进 Issue 状态 | 统一 Completion Gate，加入 Candidate / Decision / 标准和具名权限 |
| 评论附件事务 | 评论与附件关联原子性 | 不把可编辑评论作为不可变 Candidate Manifest |

## 6. 证据边界

该源码快照证明附件分组、附件关联、revision 条件写入和 PR 自动完成的实现方式。它不证明长期不可变附件存储、跨来源 Artifact Registry、Candidate Manifest、Evidence Applicability、Acceptance Decision 或统一完成门禁已经存在。

VS-2 的这些内容是 AgentPlatform 应补充的产品契约；具体存储、事务和接口承载留待技术设计与并发验证。
