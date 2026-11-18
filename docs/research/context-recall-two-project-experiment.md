# AgentPlatform · Knowledge Recall 双项目隔离实验报告

> 状态：契约级实验通过；真实 Recall Provider 与宿主消费尚未验收  
> 分支：design/system-architecture-convergence  
> 实验实现：`prototypes/context-recall/`  
> CI：[Context Recall contract experiment · 20 / 20 通过](https://github.com/ScWen7/Issues/actions/runs/44351904497)  
> 本报告不构成技术选型或生产实现方案。

## 1. 实验目的与边界

本实验将上一轮确定的 Team Knowledge / Project Knowledge / Project Sources / Project Code Knowledge / Harness 边界转成可执行的最小双项目验收。

实验不是实现一个生产 Recall 引擎。它使用确定性候选 Provider 和极简词法匹配，验证候选结果在进入排序与输出之前，是否按知识作用域和当前接收者权限过滤；同时检查来源检索、代码检索和 Harness 解析是否保持独立。

**本实验能证明业务契约在给定候选集上的行为，不证明语义召回质量、索引新鲜度、真实来源系统鉴权或 Agent 实际使用。**

## 2. 最小双项目语料

| ID | 类型 | 作用域 / 权威 | 内容用途 |
|---|---|---|---|
| T1 | Team Knowledge | Team: engineering | 从 C1 / C2 派生的通用区域数据导出验证方法 |
| A1 | Project Knowledge | Project A | 项目 A 区域账号订单授权规则，含私有标识 |
| A-S1 | Project Source | Project A | 私有 C1 / C2 原始报告 |
| B1 | Project Knowledge | Project B | 组织树授权规则 |
| B-S1 | Project Source | Project B | 项目 B 自己的 PRD |
| A-C1 | Code Knowledge | Project A | 项目 A 代码认知 |
| B-C1 | Code Knowledge | Project B | 项目 B 模块与调用关系 |
| H1 | Harness | Team 发布、Project Adoption 决定是否启用 | 一条需显式采用的强制检查规则 |

T1 仅保留经批准的通用测试方法，不包含项目 A 的订单号、私有报告标识和审核账本。T1 的 Evidence 身份仍可追溯，但 Project B 普通成员没有读取原始证据的权限。

A1、A-S1、A-C1 只属于 Project A；B1、B-S1、B-C1 只属于 Project B。

## 3. 实验模型

实验脚本提供五条彼此独立的路径：

1. **Knowledge Recall**：只读取正式 Team / Project Knowledge 候选。
2. **Project Source Search**：只查当前成员有权访问的项目原始来源。
3. **Code Retrieval**：只查当前项目代码认知。
4. **Harness Resolution**：检查团队发布、项目采用和当前成员范围，不按语义相关性决定是否生效。
5. **确定性工作上下文**：本实验不模拟 Issue / Work Agreement；其业务原则仍是按稳定对象身份直接读取。

Knowledge Recall 先按 Team / Project 作用域过滤，再做词法候选排序，最后才序列化返回字段。Evidence 原文读权独立检查。项目原始来源和代码认知不进入 Knowledge Recall 的候选集。

这只是用于验证过滤次序和结果边界的契约夹具。词法匹配不是 AgentPlatform 的检索算法建议。

## 4. 执行结果

<badge color="success">CI 20 / 20 通过</badge>

GitHub Actions 在 Ubuntu 24.04 上执行 Python 标准库脚本，无外部模型、数据库或搜索服务依赖。

| 测试 | 结果 |
|---|---|
| Project A 可发现 T1 + A1 | 通过 |
| Project B 可发现 T1 + B1 | 通过 |
| Project B 不返回 A1 | 通过 |
| 无项目 / 团队授权主体无私有知识结果 | 通过 |
| Project B 的组织树查询只命中 B1 | 通过 |
| 无命中查询返回空知识候选 | 通过 |
| B 的返回元数据不包含 A1、A-S1、C1 / C2、私有标识 | 通过 |
| T1 的团队派生正文不包含项目私有内容 | 通过 |
| T1 可见但其原始 Evidence 不向 B 开放 | 通过 |
| B 的 Source Search 只返回 B-S1 | 通过 |
| B 的 Code Retrieval 只返回 B-C1 | 通过 |
| A-S1 / B-S1 不混入 Knowledge Recall | 通过 |
| H1 不作为 Knowledge Recall 结果 | 通过 |
| 未采用 H1 时 Capability Resolution 不返回它 | 通过 |
| B 显式采用 H1 后能力解析返回 H1 | 通过 |
| Team 成员资格撤销后 T1 不再被召回 | 通过 |
| Team 派生授权暂停后 T1 停止新召回，B1 仍可见 | 通过 |
| Project B 的项目知识不受 Team 成员资格变化影响 | 通过 |
| 未授权 A1 候选不会被序列化 | 通过 |
| 所有断言均满足 | 通过 |

### 4.1 关键观察

| 查询主体 | Knowledge Recall 返回 | 其他独立 Provider |
|---|---|---|
| Project A：区域导出权限 | A1、T1 | 按需读取 A-S1 / A-C1 |
| Project B：区域数据导出 | T1、B1 | B-S1、B-C1 |
| 非项目成员：订单导出权限 | 空 | 不返回 Project A 私有来源 |
| Project B：组织树授权 | B1 | 需要时读取 B-S1 |
| Project B：无关主题 | 空 | 空知识结果不代表其他来源不存在 |

最关键的观察不是“B 能同时看到 T1 和 B1”，而是：
- T1 的正文可在团队授权范围内复用；
- T1 的原始项目证据仍然不可见；
- B1 的项目特定授权规则保留自己的权威；
- A1 和 A-S1 没有通过标题、摘要、Evidence ID 或其他结果元数据泄漏；
- Harness 的强制性由采用状态解析，不由知识召回排序决定。

## 5. 对产品设计的验证结论

### 5.1 支持的设计判断

1. **Knowledge Recall 的候选域应限于正式知识。** Project Sources、代码认知、Issue 和 Harness 不应因可被 Agent 读取就全部混入同一知识候选集合。
2. **权限过滤必须早于结果序列化。** 不能先生成包含私有标题、摘要、关系或 Evidence ID 的结果，再只隐藏正文。
3. **Team Knowledge 正文与原始 Evidence 可有不同可见范围。** 经过授权发布的派生结论可以被团队消费，但不自动授予原始项目报告的读权。
4. **Project Knowledge 仍限定当前项目。** Team Knowledge 可以被多个项目消费，但不会覆盖项目自己的业务规则。
5. **知识召回、来源检索、代码检索和 Harness 采用解析应分开。** 统一入口不等于统一语料或统一排序。
6. **撤权只影响后续资格和投递。** 历史上已送达的内容应保留真实共享记录，不能声称宿主历史被远程清除。

### 5.2 不能据此宣称的能力

本实验没有验证：
- BM25 / 向量 / 混合检索的语义质量；
- 同义词、中文切词、复杂查询和多跳知识关联；
- 大规模候选下的排序、去重和延迟；
- 真实飞书、Git 或知识来源系统的实时权限；
- 并发撤权与检索请求之间的竞态；
- 真实 Codex、Claude Code、Qoder、CodeBuddy 收到的知识正文；
- Agent 是否在推理、工具调用或交付中实际使用 T1；
- 使用 T1 是否改善了 Project B 的结果。

## 6. 当前验收状态

| 层次 | 状态 | 证据 |
|---|---|---|
| Team / Project 作用域过滤规则 | <badge color="success">契约通过</badge> | 本轮 20 项检查 |
| 私有结果元数据隔离 | <badge color="success">契约通过</badge> | 返回结果序列化负向断言 |
| Team 派生文案与原始证据分权 | <badge color="success">契约通过</badge> | 本轮模拟 + Topic 3B 贡献实验 |
| Project Source / Code / Harness 分流 | <badge color="success">契约通过</badge> | 独立 Provider 夹具 |
| Recall 实际检索质量 | <badge color="warning">未验证</badge> | 当前是确定性词法夹具 |
| 真实来源 Connector 授权 | <badge color="warning">未验证</badge> | 现有 Topic 3B 为受控来源与权限时钟 |
| 真实 Agent 宿主投递 | <badge color="warning">未验证</badge> | 尚未接入 Recall Provider |
| Agent 实际使用与结果影响 | <badge color="warning">未验证</badge> | 没有知识引用与产物因果证据 |

## 7. 下一步实验

下一轮不应马上实现生产 Recall，也不应先选择搜索引擎。先把本实验的确定性候选 Provider 替换为一个可观察的真实知识检索入口，并保持同一套双项目验收语料与断言。

优先顺序：

1. 用真实 Team / Project Knowledge 数据源建立 T1、A1、B1，保留稳定 Item / Revision / Release 身份。
2. 通过真实 Recall 入口执行 A、B、非成员、项目特定和无命中查询。
3. 对返回结果做完整元数据泄漏扫描，而不仅是正文检查。
4. 展开 T1 的 Evidence，确认 Project B 能读获准派生文案、不能读 Project A 原始报告。
5. 将 B 的 Source Search / Read 和 Code Retrieval 作为独立动作调用。
6. 把实际选用的 T1、B1 和来源修订投递到真实 Agent 宿主，观察请求输入。
7. 再检查工具调用、决策和产物是否能证明 Used；无法观察的状态保持 Unknown。
8. 最后做成员撤权、派生许可撤回和来源修订变化的在途工作对照。

真实 Recall Provider 尚不存在或未接入时，不把本轮契约夹具升级成生产能力，也不以本轮 20 / 20 代替真实产品验收。

## 8. 可复跑入口

从仓库根目录运行：

```bash
python3 prototypes/context-recall/two_project_contract.py
```

CI 工作流：`.github/workflows/context-recall-contract.yml`

研究输入：
- [双场景端到端验收](context-contract-two-scenario-acceptance.md)
- [Recall 与多来源工作上下文边界](context-recall-source-boundaries.md)
- [C1 / C2 项目知识贡献与复审](topic-03b/knowledge-contribution.md)
- [项目知识与真实宿主输入](topic-03b/project-knowledge.md)
- [项目知识来源与权限](topic-03b/knowledge-sources.md)
