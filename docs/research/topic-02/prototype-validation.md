# 专题二原型验证记录

日期：2026-11-14  
设计基线：专题二 V0.3  
验证方式：Node.js 内置 `node:test` 的确定性状态转换模型  
测试文件：[state-model.test.mjs](../../prototypes/topic-02/state-model.test.mjs)

## 结论

<badge>17 / 17 PASS</badge>

本轮将 V0.3 的核心约束抽象成小型状态模型，执行 17 项确定性测试，全部通过。测试覆盖三入口派发去重、DAG 就绪门禁、Grant 撤销和扩权、子 Issue 跨轮次迟到回报、`child_done` 唤醒语义、并行结果、SOP 出口与人工验收、工作流交接幂等、控制权代次、重启恢复及跨 Runtime 代码候选重建。

这次验证确认：**按 V0.3 规定的控制绑定、授权版本、节点激活、委托轮次和出口 Result ID 组织状态，设计层面的预期结果一致。**

## 测试清单

| ID | 场景 | 结果 |
|---|---|---|
| D-01 | Leader、Project Workflow、成员手动入口同时触发，只生成一份派发和一个 Run | PASS |
| D-02 | DAG 未就绪时三个入口均被拦截 | PASS |
| G-01 | Grant 撤销后阻止新派发和队列领取 | PASS |
| G-02 | 扩大授权范围必须递增 Grant 版本并同步控制绑定版本 | PASS |
| G-03 | Run 入队后、Runtime Start 前撤销授权，阻止 Start | PASS |
| G-04 | 在途 Run 撤权后请求停止，并保留未知外部副作用供对账 | PASS |
| R-01 | C1 迟到交付不能推进 C2 当前委托轮次 | PASS |
| R-02 | `child_done` 只唤醒父流程，无 Delivery Record 时不放行 | PASS |
| R-03 | 同一轮的并行分支结果可分别入账 | PASS |
| W-01 | SOP 通过但 UAT Decision 缺失，Project Workflow 保持当前阶段 | PASS |
| W-02 | 旧候选的 Decision 不能满足新候选出口 | PASS |
| W-03 | 同一 SOP Result ID 重放只应用一次，并返回原交接回执 | PASS |
| W-04 | Project Workflow revision 已变化时，旧 revision 的交接请求冲突 | PASS |
| W-05 | 工作流完成交接后，旧 SOP 控制代次的派发请求被拒绝 | PASS |
| X-01 | 中心重启后恢复同一 SOP 实例、Run ID 和制品引用 | PASS |
| X-02 | 两个 Script Run 与一个等待中的 Human Gate 在恢复后保持同一实例关系 | PASS |
| X-03 | 跨 Runtime 根据基准、补丁、锁文件和候选摘要重建相同代码候选 | PASS |

## 运行方式

在仓库根目录执行：

```bash
node --test prototypes/topic-02/state-model.test.mjs
```

本轮执行结果：

```text
tests 17
pass 17
fail 0
```

## 验证范围与下一步

本测试是**设计级确定性状态模型**，用于检查规则组合、版本条件和重放语义。三入口并发场景以同一状态模型中的交错调用验证幂等键与唯一安排；它没有模拟 PostgreSQL 多事务竞争，也没有接入真实 Multica Daemon、SOP Runner 或本地 Runtime。

因此，以下项目仍属于真实平台原型验收：

1. PostgreSQL 事务与唯一约束在并发请求下只生成一个 Dispatch Control Binding 和一份派发安排。
2. Grant 撤销与队列 claim / Runtime Start 并发时，授权版本校验和停止回执正确。
3. 外部副作用在断线后的对账与幂等恢复。
4. 子 Issue C1 → 重开 → C2 的真实事件顺序、旧回报归档与 Delivery Record 消费。
5. SOP Result ID、Workflow revision、状态变更、控制绑定代次及 outbox 在同一事务中的一致性。
6. 两个真实成员 Runtime 的 worktree / patch 接续与候选摘要一致性。

这些项目是专题 3A 原型的具体验收项；本次 17 项测试结果不替代真实多进程、多数据库和多机集成测试。
