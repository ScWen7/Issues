import { query, qodercliAuth } from "@qoder-ai/qoder-agent-sdk";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";

const cliPath = process.env.QODERCLI_PATH;
let cliVersion = null;
if (cliPath) {
  const v = spawnSync(cliPath, ["--version"], { encoding: "utf8" });
  cliVersion = (v.stdout || v.stderr || "").trim().split("\n")[0] || null;
}

const runId = process.env.TEAMAI_RUN_ID || "topic04-qoder-runtime-probe";
const q = query({
  prompt: "Reply with exactly OK. Do not use tools, read files, or modify anything.",
  options: {
    auth: qodercliAuth(),
    env: { ...process.env, QODER_EXPOSE_REQUEST_ID: "true" },
    ...(cliPath ? { pathToQoderCLIExecutable: cliPath } : {}),
    cwd: process.cwd(),
    maxTurns: 1,
    permissionMode: "default"
  }
});

let sessionId = null;
let assistantCount = 0;
let resultCount = 0;
for await (const message of q) {
  if (message.session_id) sessionId = message.session_id;
  if (message.type === "assistant") {
    assistantCount += 1;
    const usage = message.message?.usage ?? {};
    const row = {
      provider: "qoder",
      runtime_entry: "sdk_query",
      runtime_version: cliVersion,
      session_id: sessionId,
      run_id: runId,
      request_id: message.request_id ?? null,
      event_id: message.uuid ?? null,
      message_id: message.message?.id ?? null,
      model: message.message?.model ?? null,
      metric: "credits_consumed",
      unit: "qoder_credit",
      value: Number.isFinite(usage.credits) ? usage.credits : null,
      original_credits: Number.isFinite(usage.original_credits) ? usage.original_credits : null,
      billable: typeof usage.billable === "boolean" ? usage.billable : null,
      credit_status: Number.isFinite(usage.credits) ? "known" : "unknown",
      scope: "model_request",
      observed_at: new Date().toISOString()
    };
    console.log(JSON.stringify(row));
  }
  if (message.type === "result") {
    resultCount += 1;
    const total = message.total_credits;
    const row = {
      provider: "qoder",
      runtime_entry: "sdk_query",
      runtime_version: cliVersion,
      session_id: message.session_id ?? sessionId,
      run_id: runId,
      request_id: message.request_id ?? null,
      event_id: message.uuid ?? null,
      metric: "session_total_credits",
      unit: "qoder_credit",
      value: Number.isFinite(total) ? total : null,
      credit_status: Number.isFinite(total) ? "known" : "unknown",
      scope: "session_snapshot",
      observed_at: new Date().toISOString()
    };
    console.log(JSON.stringify(row));
  }
}
if (assistantCount === 0 || resultCount === 0) {
  console.error(JSON.stringify({ provider: "qoder", status: "incomplete", assistantCount, resultCount }));
  process.exitCode = 2;
}
