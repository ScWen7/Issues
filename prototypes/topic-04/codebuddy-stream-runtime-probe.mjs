import { spawn, spawnSync } from "node:child_process";
import { createInterface } from "node:readline";
import { createWriteStream } from "node:fs";

const command = process.env.CODEBUDDY_BIN || "codebuddy";
const versionResult = spawnSync(command, ["--version"], { encoding: "utf8" });
const cliVersion = (versionResult.stdout || versionResult.stderr || "").trim().split("\n")[0] || null;
const runId = process.env.TEAMAI_RUN_ID || "topic04-codebuddy-runtime-probe";
const output = createWriteStream("codebuddy-receipt.jsonl", { flags: "w" });

const child = spawn(command, [
  "-p",
  "Reply with exactly OK. Do not use tools, read files, or modify anything.",
  "--output-format", "stream-json",
  "--max-turns", "1"
], { stdio: ["ignore", "pipe", "pipe"] });

const rl = createInterface({ input: child.stdout });
let usageEvents = 0;
let resultEvents = 0;
let sessionId = null;
let stderrSeen = false;

rl.on("line", (line) => {
  let frame;
  try { frame = JSON.parse(line); } catch { return; }

  if (frame.session_id) sessionId = frame.session_id;
  const meta = frame._meta?.["codebuddy.ai/turnUsage"];
  if (frame.type === "system" && frame.subtype === "usage_update" && meta) {
    usageEvents += 1;
    const stage = meta.stage ?? null;
    const total = meta.total ?? null;
    output.write(JSON.stringify({
      provider: "codebuddy",
      runtime_entry: "stream_json_cli",
      cli_version: cliVersion,
      run_id: runId,
      session_id: frame.session_id ?? sessionId,
      request_id: meta.requestId ?? frame._requestId ?? null,
      frame_uuid: frame.uuid ?? null,
      metric: meta.kind === "snapshot" ? "turn_total_credits" : "credits_consumed",
      unit: "codebuddy_credit",
      value: meta.kind === "snapshot"
        ? (Number.isFinite(total?.credits) ? total.credits : null)
        : (Number.isFinite(stage?.credits) ? stage.credits : null),
      credit_status: total?.creditStatus ?? (Number.isFinite(stage?.credits) ? "known" : "unknown"),
      scope: meta.kind === "snapshot" ? "turn_snapshot" : "turn_stage",
      stage_id: stage?.id ?? null,
      stage_source: stage?.source ?? null,
      model: stage?.model ?? null,
      observed_at: new Date().toISOString()
    }) + "\n");
  }

  if (frame.type === "result") {
    resultEvents += 1;
    const resultMeta = frame._meta?.["codebuddy.ai/turnUsage"];
    output.write(JSON.stringify({
      provider: "codebuddy",
      runtime_entry: "stream_json_cli",
      cli_version: cliVersion,
      run_id: runId,
      session_id: frame.session_id ?? sessionId,
      request_id: resultMeta?.requestId ?? frame._requestId ?? null,
      metric: "turn_total_credits",
      unit: "codebuddy_credit",
      value: Number.isFinite(resultMeta?.total?.credits) ? resultMeta.total.credits : null,
      credit_status: resultMeta?.total?.creditStatus ?? "unknown",
      scope: "result_snapshot",
      observed_at: new Date().toISOString()
    }) + "\n");
  }
});

child.stderr.on("data", () => { stderrSeen = true; });
child.on("close", (code) => {
  output.end();
  console.log(JSON.stringify({
    provider: "codebuddy",
    cli_version: cliVersion,
    exit_code: code,
    usage_event_count: usageEvents,
    result_event_count: resultEvents,
    stderr_seen: stderrSeen,
    receipt_file: "codebuddy-receipt.jsonl",
    status: code === 0 && resultEvents > 0 ? "process_completed" : "process_failed"
  }));
  if (code !== 0 || resultEvents === 0) process.exitCode = 2;
});
