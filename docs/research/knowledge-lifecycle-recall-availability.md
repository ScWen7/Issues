# AgentPlatform · Knowledge 生命周期与 Recall 可用性融合审查

> 状态：产品 / 架构生命周期审查完成  
> 分支：design/system-architecture-convergence  
> 范围：正式知识发布、检索投影可用性、来源影响、权限变化、在途引用和消费反馈之间的关系。  
> 非目标：不定义数据库 Schema、事件总线、索引技术、API、部署和生产代码。

## 1. 结论

现有对象模型已经区分 Knowledge Item / Revision / Release，也指出“可检索”是处理可用状态，不等于正式发布。但这一原则还没有被完整落实为可执行的生命周期边界。

本轮明确五个彼此独立的事实：

1. **Knowledge Revision**：内容与证据的不可变修订。
2. **Knowledge Release**：有权维护者作出的正式发布决定，定义可消费版本、作用域和发布状态。
3. **Recall Projection**：为检索建立的派生索引 / 搜索视图，不拥有知识正文、发布或权限的权威。
4. **Knowledge Eligibility**：在当前时点、对特定接收者和用途，这个 Release 是否仍可被新查询、读取或投递。
5. **Work Consumption**：某项工作实际发现、读取、采用、投递和使用了哪个版本的知识。

**发布成功不等于索引已就绪；索引命中不等于知识仍可消费；历史引用存在不等于今天仍有读取权；投递成功不等于 Agent 已使用。**

## 2. 正式知识与检索投影的双轨生命周期

### 2.1 知识权威轨

| 对象 | 事实 | 关键状态 / 变化 |
|---|---|---|
| Knowledge Item | 稳定的知识主题 / 结论身份 | 活跃、合并、替代、退役 |
| Knowledge Revision | 某一版不可变内容、适用范围和 Evidence 关系 | 草拟、待核验、已核验、驳回、待复核、失效 |
| Knowledge Release | 哪个 Revision 被批准向哪个范围正式提供 | 已发布、暂停投递、撤回、退役 |

Release 是正式发布决定。它不能依赖搜索索引是否构建成功才成立；同样，索引构建成功也不能使草稿或未发布 Revision 变成正式知识。

### 2.2 检索投影轨

Recall Projection 是从正式知识派生出来的查询优化视图，状态至少区分：
- **Pending**：应更新，尚未处理；
- **Building**：正在构建或增量更新；
- **Current**：与当前应服务的知识修订 / 发布状态一致；
- **Stale**：存在已知差异，不能声称结果完整或最新；
- **Unavailable**：索引或检索入口当前不可用；
- **Failed**：最近更新失败，需要重试或人工排查。

这是一种处理 / 投影状态，不是新的 Knowledge Release 状态，也不需要创建新的知识业务资产。可以由既有受管处理与回执记录状态。

### 2.3 两条轨之间的关系

- 发布 Release 后，触发相应检索投影更新；不等待投影更新才确认发布。
- 投影更新失败，不撤销已发布 Release；但查询应明确报告覆盖不完整或不可用。
- 投影中出现未发布、暂停、撤回或退役知识时，权威资格检查必须阻止它进入响应。
- Release 暂停 / 撤回时，先改变权威可消费资格，再异步清理 / 更新投影；不能等待索引删除完成才生效。
- 投影当前只说明检索视图与应服务状态同步，不证明知识正确、适用或来源真实。

## 3. Recall 必须经过权威资格检查

Recall Projection 只能帮助发现候选，不能作为最终授权和可消费状态的依据。

建议的逻辑顺序：

1. 从可信调用上下文确认成员、Agent、Project、Issue / Run 和用途。
2. 依据当前权威成员关系与访问策略确定可见 Team / Project 范围。
3. 从 Recall Projection 发现候选身份；投影可以缩小候选，但不能授予访问权。
4. 对候选身份回查权威 Knowledge Item / Revision / Release。
5. 校验 Release 当前状态、目标受众、派生许可、硬性适用边界和当前接收者读权。
6. 只对通过检查的候选读取安全可披露字段，再排序和返回。
7. 展开 Revision / Evidence 和实际投递前，再次核验当前状态与具体接收者权限。

**投影中不得直接读取并返回未经权威核验的标题、摘要、Claim、Evidence ID 或关系元数据。** 否则旧索引可能泄漏刚撤权的私有内容。

这意味着即使底层采用预过滤检索，响应前仍需要权威复核；预过滤是性能优化，不是安全边界。

## 4. 无命中与检索不完整必须区分

Recall 结果需要表达检索覆盖状态，不能只返回一个空数组。

| 状态 | 含义 | Agent 应如何理解 |
|---|---|---|
| Complete + Hits | 当前可查询范围已完成检索并找到候选 | 可以评估候选适用性 |
| Complete + No Match | 当前范围检索完整，没有找到匹配的正式知识 | 表示 Knowledge Recall 未找到，不代表其他来源没有资料 |
| Partial / Stale | 部分作用域、分区或投影尚未追平 | 不能把未命中解释成知识不存在；可重试或转向来源 / 项目资料 |
| Unavailable / Failed | 当前 Recall 不能可靠完成 | 明确报错或降级，不伪造“无知识” |
| Filtered by Eligibility | 有候选但因当前权限 / Release 状态不能返回 | 不泄漏候选身份；仅在安全范围内说明结果受访问规则限制 |

在多 Team / Project 范围查询时，可以部分成功：一个范围 Current，另一个范围 Unavailable。必须标明各范围覆盖情况，不能把部分命中包装为完整结果。

如果投影不可用：
- 可以对已知明确 ID 的 Knowledge Item / Revision 走权威直接读取；
- 可以重试投影或采用受控的直接候选枚举（如有）；
- 不允许静默把旧投影当成最新；
- 不允许把不可用解释成 Complete + No Match。

## 5. 来源变化如何影响知识和 Release

来源变化是影响信号，不是自动失效判决。

### 5.1 变化处理链

1. Source Connection / Source Revision 发现变化、删除、撤回、权限变化或派生许可变化。
2. 根据 Evidence Anchor / Evidence 关系识别受影响 Knowledge Revision / Release。
3. 生成影响待处理状态，明确影响的是哪些结论和哪些证据。
4. 根据事实类型、来源权威性、风险和撤回范围决定：
   - 只更新证据定位 / 检索投影；
   - 标记 Revision 待复核，但 Release 暂时继续可用；
   - 对高风险且关键依据已撤回的结论暂停 Release 新投递；
   - 创建新 Revision，重新核验和发布；
   - 退役不再成立的知识。
5. 投影更新与 Release 状态变化分别处理。
6. 已有 Work / Run 引用保留历史事实，并根据在途工作风险策略重新确认是否继续使用。

### 5.2 不同变化不能混为一谈

| 变化 | 默认影响 | 不能直接推断 |
|---|---|---|
| 来源新增内容 | 可产生新 Evidence / 新候选 | 旧结论失效 |
| 来源正文变化 | 标记依赖证据受影响，进入复核判断 | 所有引用该来源的知识都失效 |
| 来源删除 / 撤回 | 停止新访问；按依赖关系和撤回范围评估派生知识 | 所有历史证据都被抹除 |
| 来源读权收缩 | 阻止失权主体新读取 / 投递原文；检查派生许可和目标受众授权 | 团队派生文案必然立即失效 |
| 派生许可撤回 | 对受影响派生结论暂停新投递 / 展开并复核 | 与该来源无关的结论也受影响 |
| 代码 Commit 改变 | 触发代码认知刷新和相关知识影响分析 | 业务规则自动失效 |
| Evidence Anchor 定位失效 | 标记定位不可用，寻找新锚点或人工复核 | 结论本身必然错误 |

## 6. 权限变化与知识发布状态必须分离

以下状态属于不同权威事实：
- Team 成员资格；
- Project 成员资格；
- Knowledge Release 是否发布 / 暂停 / 撤回；
- 来源当前读权；
- 来源派生许可；
- 目标受众授权；
- Evidence 原文是否可展开；
- 当前 Issue / Delegation 是否允许该用途。

它们不能被合并为一个简单的 active 布尔值。

例如：
- 成员退出 Team，不影响其他成员消费已发布 Team Knowledge；
- 成员退出 Project，不影响其仍有权消费的 Team Knowledge；
- 团队知识 Release 暂停，不代表 Project Knowledge 自动暂停；
- Evidence 原文不可读，不必然禁止消费已获授权的派生知识正文；
- 派生许可撤回可能影响一条 Team Knowledge，即使成员仍是 Team 成员；
- Project Adoption 不能覆盖 Release 暂停或成员失权。

## 7. 在途 Work / Run 引用的处理

Work / Run Asset Pin 固定的是当时实际采用的 Knowledge Revision / Release 身份，不是永久读取许可。

| 事实 | 历史审计 | 新读取 / 新投递 |
|---|---|---|
| 已固定的 Revision / Release 身份 | 保留 | 仍需检查当前资格 |
| 当时投递的正文摘要 / ContextReceipt | 保留 | 不自动重放旧正文 |
| 成员当前 Team / Project 权限 | 记录当时事实 | 按当前权限重新检查 |
| Release 当前状态 | 记录历史状态变化 | 暂停 / 撤回后停止新的投递 |
| 来源派生许可 | 记录当时授权与变化 | 撤回后按影响范围暂停后续派生消费 |
| 已经进入宿主历史的内容 | 保留实际共享事实 | 不声称可远程删除；新线程 / 新投递必须重新核验 |

对在途工作：
- 低风险参考知识变化可以提示负责人重新确认；
- 作为高风险验收依据、强制工作约束或关键业务事实的知识若暂停，应阻止后续新投递，并要求有权负责人决定是否重新取材或调整 Work Agreement；
- 不静默将 Pin 从旧 Revision 改成新 Revision；
- 不能因为历史 Pin 存在就绕过当前权限或 Release 状态。

## 8. 事件与处理责任：沿用现有对象，不新增平行生命周期

| 触发事实 | 权威来源 | 后续处理 |
|---|---|---|
| Knowledge Revision 核验完成 / Release 发布 | Knowledge Governance | 更新应服务的 Recall Projection |
| Release 暂停 / 撤回 / 退役 | Knowledge Release | 立即影响候选资格；异步清理投影 |
| Team / Project 成员变化 | Membership / Policy | 影响该主体后续 Recall / Read / 投递 |
| Source Revision 变化 | Source Item / Revision | 计算受影响 Evidence / Knowledge |
| Source Connection 断开 / 来源删除 | Source Connection / Source Revision | 评估来源可用性、派生授权和知识状态 |
| 派生许可变化 | 来源授权 / 派生许可记录 | 影响目标 Team Knowledge 的后续可消费资格 |
| Evidence Anchor 失效 | Source Revision / Evidence Anchor | 更新证据可用性，触发复核 |
| Knowledge Feedback / Evaluation Finding | Knowledge Feedback / Finding | 由知识维护者决定是否形成新 Revision |
| Recall Projection 更新成功 / 失败 | 既有处理执行回执 | 更新投影覆盖状态，不改变 Release 发布事实 |

这些变化可由现有来源处理、知识治理、权限和执行能力观察、处理和对账。不是为每种变化创建一套新的业务事件对象、Recall Run 或通用任务系统。

## 9. 业务事实与派生运行状态的权威表

| 事实 | 权威 |
|---|---|
| 知识内容与修订 | Knowledge Revision |
| 正式发布资格与目标范围 | Knowledge Release |
| 当前成员 / 项目访问权 | Team / Project Membership 与 Policy |
| 来源原文和当前来源修订 | 原来源系统 + Source Item / Revision |
| 来源派生许可 | 对应来源授权 / 派生许可事实 |
| Evidence 定位和证据状态 | Evidence / Evidence Anchor 及来源修订事实 |
| Recall Projection 当前 / 陈旧 / 失败状态 | 检索处理回执和投影覆盖信息（派生运行状态） |
| 某次工作实际采用版本 | Work / Run Asset Pin |
| 实际准备 / 投递 | ContextReceipt |
| 实际加载 / 使用 | AgentObservation / Asset Usage Observation |
| 业务是否继续当前工作 | Issue / Work Agreement / 有权 Decision |

## 10. 与 Knowledge Consumption Contract 的关系

Knowledge Consumption Contract 定义单次查询、读取、Evidence 展开、选择、投递和反馈行为；本报告补齐这些行为依赖的生命周期与状态权威。

两者共同约束：
- 只有当前有权且正式可消费的 Release 能进入 Recall 结果；
- Recall Projection 不是知识权威；
- 无命中与检索不完整必须区分；
- 来源变化触发影响分析，不自动判定知识失效；
- Release 暂停 / 撤回优先影响新投递，索引清理可以异步；
- Work Pin 固定历史版本但不授予永久读取权；
- 实际投递和使用分别举证。

## 11. 尚待真实验证

- 发布到 Recall Projection 的延迟和部分失败是否能被准确呈现；
- 多 Team / Project 范围部分可用时，Recall 能否给出可靠覆盖状态；
- 并发撤权、Release 暂停与 Recall / Read / 投递的竞态；
- 关键 Evidence 撤回后，哪些知识 Release 应自动暂停，哪些只进入待复核；
- 在途 Work / Run 如何判断继续、重新取材或阻断；
- 投影陈旧时，权威回查和直接读取的降级是否可用；
- 大规模增量更新后是否仍能保证结果版本和 Evidence 关系一致。

这些问题在真实 Provider 可用后验证，不在本轮提前决定索引或事件技术。

## 12. 最终结论

**知识是权威业务资产；Release 是正式发布决定；Recall Projection 是可重建的检索运行视图；Eligibility 是当前接收者的可消费资格；Work Pin 是某项工作当时采用的版本事实。**

它们不能合并成一个状态，也不能由某一层代替另一层。

这套分离使 AgentPlatform 能在索引延迟、来源修订、权限撤回和在途工作变化时，既不把未发布知识当成正式知识，也不因搜索故障误报知识不存在，更不让旧索引或历史 Pin 绕过当前授权。


## 13. 契约回归测试补充

双项目契约脚本已扩展投影状态检查，区分：
- Release 已暂停但 Recall Projection 仍陈旧：旧索引候选不得返回；
- Projection Unavailable：不得伪装为 Complete + No Match；
- Projection Stale：无命中只能报告 Partial / Stale；
- Projection Current 且无候选：才可报告 Complete + No Match；
- 投影处理状态变化不改变 Release 的权威发布状态。

本次 CI 对应提交：2a1b28ffe113e1bd70cfd902a7ec4e4bb428b5b8。测试结果以该提交的 GitHub Actions 实际执行记录为准。此脚本仍是确定性契约模拟，不证明生产索引和真实权限竞态。
