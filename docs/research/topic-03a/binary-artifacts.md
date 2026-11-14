# 订单导出 XLSX 如何交付到 Issue

用 C2 的实际东区工作簿检验两条现成通道。文件由订单导出脚本在 C2 工作副本内生成，包含有权查看的已付款和未付款订单，读取器已核过金额、付款时间、空值和时区。它的长度为 5,494 字节，完整 SHA-256 为 `5784c6c9f6660ac89a3bd4188541f5bfaee85b2e21a39b47a55923983380e852`。[生成与独立核验](order-export-workspace.md)

| 实际走的通道 | 接收端得到的内容 | 证据支持的用途 |
|---|---|---|
| LoopForge 固定 Runner 的普通具名输出，真实 `collectTaskOutputs`、`Client.Complete` 和本机 HTTP 接收方 | 发出前与源文件逐字节一致。JSON 解码后为 9,406 字节，SHA-256 为 `4497d33760aad79be8d02f2865f808167540fa33e0f248c61dc230d6fc4ae1fc`，ZIP 目录读取失败。同请求中的 UTF-8 中文摘要完整保留 | 此通道可传输核验报告这样的文本。XLSX 使用能保持原始字节的附件通道 |
| Multica 固定生产附件上传、下载、认证中间件，PostgreSQL 17.5 与本地存储 | 使用夹具任务身份，通过 HTTP multipart 上传并下载，返回 200，Issue 和上传 Agent 匹配。下载的 5,494 字节与源文件逐字节相同。用相同内容再上传一次，服务端生成另一个附件 ID | 可以复用其二进制传输与可见性机制。受托回报还要核对派发关联、候选和摘要，并处理同一逻辑交付的重放 |

**源码中的原因。** LoopForge Runner 读取具名文件后放进 `map[string]string`。普通完成请求以 JSON 编码；XLSX 的压缩内容并非 UTF-8 文本，转换中的字节变化发生在 HTTP 接收方解码之前。测量覆盖普通节点输出路径，LoopForge 的预览另有原始字节上传入口。Multica 按原始字节写存储，并为每次上传创建附件身份，上传时核对所选 Issue；代理下载重新解析附件及访问关系，再传回内容。[LoopForge 采集](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/runner/outputs.go#L84-L128) · [JSON 请求](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/runner/client.go#L55-L84) · [普通输出和预览](https://github.com/Tencent/LoopForge/blob/97b3cdc2f29a88e8767a8dc6c03bfb8865622653/internal/runner/client.go#L289-L316) · [Multica 上传与 Issue 归属](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/file.go#L441-L498) · [附件授权下载](https://github.com/multica-ai/multica/blob/fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc/server/internal/handler/file.go#L884-L955)

**平台设计。** 产出时对实际交付字节计算摘要，接收后比较长度与摘要，再登记为可供节点消费的具名制品。原文件、核验报告和预览分别关联同一次尝试。一个附件身份可被一次授权交付引用，网络重试可复用已确认的引用。即使两份文件内容相同，下载权限也仍取自各自的 Issue、授权和接收者。C1 的错误东区文件就与获准查看两区的文件逐字节相同。

## 复跑

按[订单实验](order-export-workspace.md#复跑)生成 XLSX。LoopForge 使用固定提交 `97b3cdc` 和 Go 1.26.11，Multica 使用固定提交 `fdfbfcd` 和 Go 1.26.9，后者的 DATABASE_URL 指向已迁移的一次性 PostgreSQL。构建器在 Go overlay 中编译上游实现和本次用例。LoopForge 用例仅编译当前测量所需测试文件。两次复跑分别调用下列命令，可用 `--go` 指定不同的 Go 可执行文件。

```bash
python3 prototypes/topic-03a/artifact-transport/run.py loopforge "$LOOPFORGE_CHECKOUT" /tmp/ap-order-run-01/C2/east.xlsx
python3 prototypes/topic-03a/artifact-transport/run.py multica "$MULTICA_CHECKOUT" /tmp/ap-order-run-01/C2/east.xlsx
```

[Runner 报文对照](../../../prototypes/topic-03a/artifact-transport/loopforge/workbook_test.go) · [Issue 附件往返用例](../../../prototypes/topic-03a/artifact-transport/multica/workbook_test.go)
