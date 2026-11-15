# 专题二原型验证记录

日期：2026-11-14  
验证方式：Node.js 内置 `node:test` 的确定性状态转换模型  
测试文件：[state-model.test.mjs](../../../prototypes/topic-02/state-model.test.mjs)

## 结论

**结果：17 / 17 PASS**

模型使用 Grant、控制绑定和代次等测试数据，覆盖多入口派发、撤权、子项重开、迟到回报、流程交接、恢复和跨 Runtime 候选引用。

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

复跑结果：

```text
tests 17
pass 17
fail 0
```

## 实验覆盖

本测试是**设计级确定性状态模型**，用于检查规则组合、版本条件和重放语义。三入口并发场景以同一状态模型中的交错调用验证幂等键与唯一安排；它没有模拟 PostgreSQL 多事务竞争，也没有接入真实 Multica Daemon、SOP Runner 或本地 Runtime。

产品的工作流和结果消费规则见[SOP 与项目工作流](../../architecture/02-sop-workflow.md)。
