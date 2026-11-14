# TeamAI 如何感知成员的本地工作

固定版本为 [Tencent/teamai-cli `1bc2ce1`](https://github.com/Tencent/teamai-cli/commit/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956)。本阶段从远端取得 `main`，比专题二引用的 `556b524` 多四次提交。以下根据该版本的工作流引擎、宿主适配包、Hook、转录解析和费用账本追踪。TeamAI 的 workflow run 在本项目对应 SOP Execution。

## Skill Driver 知道一次步骤如何交接

成员在编码会话里调用 `workflow start --driver skill`，按 `next` 打印的动作工作，选择宿主可并行启动子 Agent、串行启动、提供工作树，或由当前会话亲自做。命令步骤由独立 Runner 启动和等待。提示词步骤把当前 attempt 的任务、目录、结果格式、回报命令写进 `brief.md`。协调会话确认派发，子 Agent 或当前会话写自己的 `result.json` 并调用 `report --attempt`。驱动知道它向哪个 attempt 要过回报、收到什么结果。四种能力配置都声明 `tokens: false`、`max_turns: false`，因为宿主没有把子 Agent 的用量和轮数交给这条协议。[驱动入口](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/workflow/drivers/skill/skill-driver.ts#L35-L86) · [宿主声明和原因](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/workflow/drivers/skill/host-profiles.ts#L19-L57) · [子任务说明](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/workflow/drivers/skill/child-brief.ts#L96-L143)

协议日志记录 `start/next/ack/report`、调用人相对协调会话的身份、attempt、返回状态和已发出的动作。正常 prompt 回报携带 attempt、revision、driver、结果；结算后重发返回 `repeated`，报告途中恢复则继续发送已保存的结果。上游测试让两个子步骤分别在独立会话和协调者自己的 Session 里回报。由此可见，`ack` 记录“调用方确认派发”，步骤归属依赖 attempt，子调用是否真的执行过某条命令还要查宿主事件。[协议日志](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/workflow/drivers/skill/journal.ts#L19-L48) · [结算与重放](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/workflow/drivers/skill/transitions.ts#L1158-L1205) · [两种回报会话](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/__tests__/workflow-skill-driver.test.ts#L524-L555)

## AgentObservation 描述执行配置，Hook 和转录提供活动记录

`AgentObservation.v=1` 描述一次步骤执行时的 Agent 定义、工具与版本、请求和报告的模型与推理力度、团队资源版本、项目 commit 和 dirty 状态。Local Driver 可在启动前探测 CLI 版本、读取项目状态和投递记录。引擎有依据时把自己准备的工作副本数据覆盖到回报中，并在结算时填入定义名、TeamAI 版本与 driver；Session、用量、费用作为其他字段单独保存。配置指纹只比较版本、定义、工具、模型、力度和团队资源；需要模型及本地无变更的团队版本，所处项目和 driver 不参与计算。相同指纹可以来自两次不同工作。[字段与输入来源](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/agent-observation.ts#L59-L94) · [启动探测](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/agent-observation.ts#L148-L193) · [工作副本核对](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/workflow/protocol.ts#L425-L487) · [指纹](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/agent-observation.ts#L243-L303) · [步骤结算](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/workflow/engine.ts#L3117-L3148)

已配置的宿主通过 `SessionStart / UserPromptSubmit / PostToolUse / Stop` 调入本地 CLI。事件进入 dispatcher，各 handler 分别提取活动。项目内的 SessionStart 在后台 pull 之前记录投递基线、原生 Session ID 和已提供的绝对转录路径；同 Session 恢复可追加 capture，压缩、TeamAI 标识的 workflow/judge 启动跳过普通 capture。Stop 更新可读到的工作副本结束状态，最后一次为准。若不同 capture 的工具或模型配置矛盾，Session 级标签保留缺失状态。两个 capture 代表两次观测，跟成员在哪一轮开始另一个 Issue 是两个问题。[Hook 注册](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/builtin-hooks.ts#L463-L472) · [分派与抓取顺序](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/hook-dispatch-cli.ts#L639-L677) · [启动与排除条件](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/session-flow/captures.ts#L111-L154) · [Stop](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/session-flow/captures.ts#L177-L207) · [标签合并](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/session-flow/captures.ts#L458-L487)

PostToolUse 可以记录调用的工具名，技能 handler 还能把一次 Skill 工具或读取 SKILL.md 的动作与安装记录对应；UserPromptSubmit 中提到某技能则另行记录。要取得消息正文、工具参数及结果，转录适配器读取本机对应文件：Codex 按 `call_id` 对照工具调用与输出，Claude 格式解析文本、`tool_use` 与 `tool_result`。归一化时存在取舍，例如 Codex 消息映射会跳过 developer 消息，直接消费归一化正文会丢失部分原始标识。上游的 session push 选择会话、按配置脱敏后归档整份可读转录。本项目需要在上传前选择具体轮次、消息和工具字段。[活动事件](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/dashboard-collector.ts#L1090-L1128) · [技能调用和提及](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/hook-handlers.ts#L583-L599) · [提及](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/hook-handlers.ts#L642-L651) · [Codex 转录](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/packages/tool-core/src/formats/codex.ts#L715-L785) · [Claude 转录](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/packages/tool-core/src/formats/claude-code.ts#L222-L285) · [共享实现](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/session-flow/session-cmd.ts#L509-L538)

## 活动去重、费用归集与来源

| 对象 | 上游怎么做 | 对本项目的含义 |
|---|---|---|
| 活动时间线 | 看板以 Session、事件类型、内容特征、两个不同工具名和两秒窗折叠重复 Hook；同工具重复保留 | 适合修正看板显示。独立开工、声明成本、分配 Issue 使用更强的原生标识。[折叠规则](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/dashboard-collector.ts#L1778-L1845) |
| Claude 请求 | 同一 API 回复会重复出现在多个内容块；按 `message.id` 优先、`requestId` 次选去重。主转录和子 Agent 转录共用集合；可识别的 advisor 调用另记 | 主 Session 汇总与已采集的子请求可能重叠。需要保留请求明细和父子关系。[请求解析](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/packages/tool-core/src/formats/claude-jsonl.ts#L46-L103) |
| Codex 请求 | 新格式用 `token_usage_record.response_id` 识别并过滤 fork 中复制的父线程记录；旧格式根据累计值的变化选取当次增量。区分 session 累计及单文件累计，按格式处理缓存输入 | Session 的累计量适合对账。没有执行段起止基线或原生请求的量，保留未归属。[用量范围](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/packages/tool-core/src/formats/codex-rollout.ts#L27-L66) · [逐次读取](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/packages/tool-core/src/formats/codex-rollout.ts#L86-L129) |
| 本地费用账本 | Stop 解析转录。键为 `SHA256(scope + NUL + request.key)`，scope 优先取转录路径，另有工具和 Session 兜底；HTTP Local Agent 明确关闭本路径的重复用量读取。费用优先使用工具报告，其次取版本化目录估价，未知为空 | 拷贝转录后原路径作用域改变。平台需要跨观察者的原生请求身份、观察来源和单独的价格依据；宿主估算金额还须与实际账单区分。[停止读取](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/dashboard-collector.ts#L1208-L1229) · [账本键](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/dashboard-collector.ts#L209-L252) · [双入口处理](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/local-agent.ts#L6138-L6171) · [价格来源](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/token-usage/pricing.ts#L36-L69) |
| 制品 | 子 Agent 的 `changed` 是其列出的路径。对于已准备的工作区，TeamAI 检查 attempt、拒收调用方填写的 `changes/read`，自行 finish 工作区、登记证据后结算 | 案例中的“改了导出权限”先保留为执行者说明；采集到的提交或文件、真实验证结果和候选可逐项关联。[声明字段](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/workflow/drivers/skill/child-brief.ts#L13-L35) · [工作区确认](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/workflow/protocol.ts#L960-L994) |

## 本次运行

固定提交下使用 Node 24.22.1 与 Vitest 4.1.12。运行上游 Skill Driver、AgentObservation、session captures、session sharing 以及用量解析测试，同时通过构建后的 TeamAI CLI 验证命令步骤。相关宿主输入来自测试夹具；TeamAI 部分的范围是本地协议、转录解析及账本，与真实模型服务和供应商账单分开。

上游六个测试文件共 148 项通过、1 项跳过。跳过项是 OpenCode SQLite 读取，环境中没有该夹具使用的 `sqlite3` 可执行文件。构建后的 Skill Driver CLI 命令步骤测试 3 项通过。两次额外实验直接调用该提交的 `parseHookEvent / readLocalRequestRecords` 和 `settleObservation`，均通过。[CLI 案例](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/__tests__/e2e/workflow-skill-commands.test.ts#L98-L136) · [跳过条件](https://github.com/Tencent/teamai-cli/blob/1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956/src/__tests__/token-usage.test.ts#L363-L383)

1. 在相同 Session 和 Claude 消息 ID 下，把两块内容写入文件，其中报告单次费用为 0.01 美元。首次 Stop 记一笔 10,000 微美元，重复 Stop 仍是一笔；把同一文件逐字节拷贝到另一路径后用同一 Session 再 Stop，账本变成两笔，共 20,000 微美元。由此复现路径作用域的局限。
2. 工具、模型、团队版本和定义保持相同，更换项目 commit，并把 driver 从 local 换成 skill。两个结算对象内容不同，64 位十六进制指纹相同。指纹适合比较执行配置。

上游复跑命令（在该提交的仓库根目录执行）。测试套件为每个文件新建临时 home，去掉宿主的 `XDG_DATA_HOME` 覆盖可使 Muse 夹具按其默认位置读取。

```bash
npm ci
npm run build
env -u XDG_DATA_HOME npx vitest run --maxWorkers=1 \
  src/__tests__/{agent-observation,session-captures,token-usage,workflow-skill-driver,session-share}.test.ts \
  packages/tool-core/src/formats/codex-rollout.test.ts
npx vitest run --maxWorkers=1 --config vitest.e2e.config.ts \
  src/__tests__/e2e/workflow-skill-commands.test.ts
```

<details>
<summary>复现两项额外实验的测试输入与断言</summary>

在同一检出目录将以下文件保存为 `src/__tests__/phase2-observation-probe.test.ts`，执行 `npx vitest run --maxWorkers=1 src/__tests__/phase2-observation-probe.test.ts`。测试套件隔离临时目录与本机账本。

```ts
import { test, expect } from 'vitest';
import { mkdtemp, writeFile, copyFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { parseHookEvent, readLocalRequestRecords } from '../dashboard-collector.js';
import { settleObservation } from '../agent-observation.js';

test('two content blocks, repeated stop, then another path for the same host response', async () => {
  const dir = await mkdtemp(path.join(tmpdir(),'two-observers-'));
  const a = path.join(dir, 'primary.jsonl');
  const b = path.join(dir, 'copy.jsonl');
  const line = {type:'assistant', timestamp: new Date().toISOString(), costUSD: 0.01, message:{id:'msg_example',model:'fixture',usage:{input_tokens:12,output_tokens:3},content:[{type:'text',text:'first'}]}};
  await writeFile(a, [JSON.stringify(line), JSON.stringify({...line,message:{...line.message,content:[{type:'text',text:'continued'}]}})].join('\n')+'\n');
  await copyFile(a,b);
  const stop = (file:string) => parseHookEvent(JSON.stringify({hook_event_name:'Stop',session_id:'same-host-session',transcript_path:file}),'claude');
  const size = async () => { const records=[...(await readLocalRequestRecords()).values()];return [records.length, records.reduce((n,r)=>n+(r.costMicros??0),0)];};
  for (const [file, expected] of [[a,[1,10000]],[a,[1,10000]],[b,[2,20000]]] as const){await stop(file);expect(await size()).toEqual(expected);}
});

test('distinct step passes in different project commits and drivers share a harness fingerprint',()=>{
  const obs=(driver:string, commit:string)=>settleObservation({driver:{kind:driver},tool:'claude',agent:{model:{reported:'fixture'},team:{revision:'a'.repeat(40),localChanges:false},project:{commit,dirty:false}}},'coder');
  const a=obs('local','b'.repeat(40)); const b=obs('skill','d'.repeat(40));
  expect(a?.fingerprint).toMatch(/^[a-f0-9]{64}$/);
  expect(a?.fingerprint).toEqual(b?.fingerprint);expect(a).not.toEqual(b);
});
```

</details>


