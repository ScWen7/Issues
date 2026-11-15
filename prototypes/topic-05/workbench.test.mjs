// Replays the HTML's DOM event handlers with Node's built-ins. Browser layout and backend permissions require separate checks.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";

const html = readFileSync(new URL("./workbench.html", import.meta.url), "utf8");
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];

function openWorkbench() {
  const nodes = new Map();
  function node(id) {
    if (!nodes.has(id)) nodes.set(id, {
      innerHTML: "", listeners: {}, focus() {},
      addEventListener(event, fn) { this.listeners[event] = fn; }
    });
    return nodes.get(id);
  }
  const document = node("document");
  document.getElementById = node;
  document.querySelector = node;
  const engine = vm.createContext({ document, window: { scrollTo() {} } });
  vm.runInContext(script, engine);

  function body() { return node("main").innerHTML + node("aside").innerHTML; }
  function tag(action) { return body().match(new RegExp('<button[^>]+data-action="' + action + '"[^>]*>'))?.[0]; }
  function can(action) {
    const rendered = tag(action);
    return Boolean(rendered && !rendered.includes(" disabled"));
  }
  function click(action) {
    assert.ok(can(action), "action should be enabled: " + action);
    document.listeners.click({ target: { closest: () => ({ dataset: { action }, disabled: false }) } });
  }
  function replay(action) {
    document.listeners.click({ target: { closest: () => ({ dataset: { action }, disabled: false }) } });
  }
  function role(value) { node("role").listeners.change({ target: { value } }); }
  function reason(value) {
    document.listeners.change({ target: { id: "return-reason", value } });
    assert.equal(node('[data-action="return"]').disabled, false);
    // A browser updates the button property directly. Refresh the same role to inspect a full render.
    role("lin");
  }
  function reset() { node("reset").listeners.click(); }
  return {body, tag, can, click, replay, role, reason, reset};
}

function loadC2(work) {
  work.click("order");
  work.click("repair");
  work.click("full");
}

test("C1 failure and C2 partial evidence stay separate from synthetic acceptance inputs", () => {
  const w = openWorkbench();
  w.click("order");
  assert.match(w.body(), /B-201/);
  assert.equal(w.can("accept"), false);
  w.click("repair");
  assert.match(w.body(), /尚缺 A1、A4、A5 与 A6/);
  assert.match(w.body(), /Leader 牵头补证，丙协调独立验证/);
  assert.match(w.body(), /林在 A6 核对当前候选和获准 UAT/);
  assert.equal(w.can("accept"), false);
  assert.match(w.body(), /fixtures\/order-export-c2.json/);
  w.click("full");
  assert.match(w.body(), /独立审查与 UAT 均指向 C2/);
  assert.equal(w.can("accept"), true);
  w.click("C1");
  w.replay("accept");
  assert.match(w.body(), /等待林验收/);
});

test("personal inbox reopens the same Issue; reading an old or current notification never accepts it", () => {
  const w = openWorkbench();
  loadC2(w);
  w.click("project");
  w.role("bing");
  assert.equal(w.tag("notice-review"), undefined);
  w.replay("notice-review");
  assert.match(w.body(), /我的通知 · 丙/);
  w.role("lin");
  w.click("notice-failure");
  assert.match(w.body(), /历史 C1，当前工作已进入 C2/);
  assert.equal(w.can("accept"), false);
  w.click("C2");
  assert.equal(w.can("accept"), true);
  w.click("project");
  w.click("notice-review");
  assert.match(w.body(), /打开通知已记为已读/);
  assert.match(w.body(), /等待林验收/);
  w.click("project");
  assert.match(w.body(), /data-action="notice-review"[^>]*><strong>C2 交付验收<\/strong><span[^>]*>已读/);
  w.click("notice-review");
  for (const person of ["bing", "jia"]) {
    w.role(person);
    assert.equal(w.can("accept"), false);
    w.replay("accept"); w.replay("return");
    assert.match(w.body(), /等待林验收/);
  }
  w.role("lin");
  w.click("accept"); w.replay("accept");
  assert.equal(w.tag("accept"), undefined);
  assert.match(w.body(), /林已按 D2 接受 C2/);
});

test("return requires a current candidate, authorized reviewer and reason; replay cannot complete the rejected round", () => {
  const w = openWorkbench();
  loadC2(w);
  assert.equal(w.can("return"), false);
  w.replay("return");
  assert.match(w.body(), /等待林验收/);
  w.reason("uat");
  w.click("return");
  assert.match(w.body(), /林 · C2 \/ D2 \/ A1–A6/);
  assert.match(w.body(), /当前负责人<\/dt><dd>交付 Squad/);
  assert.match(w.body(), /A6：演练 UAT 使用的候选与 C2 不符/);
  assert.equal(w.tag("accept"), undefined);
  w.replay("accept"); w.replay("return");
  assert.match(w.body(), /C2 本轮已退回/);
  w.click("project"); w.click("notice-review");
  assert.equal(w.tag("accept"), undefined);
  w.click("project"); w.role("jia");
  w.click("notice-returned");
  assert.match(w.body(), /演练退回决定/);
});

for (const [reason, criterion, finding, prior] of [
  ["uat", "A6 交付", "UAT 使用的候选与 C2 不符", "独立审查与 UAT 均指向 C2"],
  ["spec", "A5 交互", "失败重试表现有缺口", "空结果、加载、失败重试与重复点击均已逐项核对"]
]) {
  test("returned candidate flags the disputed criterion and retains its submitted evidence: " + criterion, () => {
    const w = openWorkbench();
    loadC2(w);
    w.reason(reason);
    w.click("return");
    const row = w.body().split('<div class="check">').find(block => block.startsWith("<strong>" + criterion + "</strong>"));
    assert.ok(row.includes(finding));
    assert.match(row, /人工有异议 · 待补验/);
    assert.ok(row.includes('<summary>退回前提交的演练材料</summary><p>' + prior));
    assert.equal(row.includes('<span class="status ok">演练证据</span>'), false);
    w.click("C1");
    assert.equal(w.body().includes("人工有异议 · 待补验"), false);
    w.click("C2");
    assert.ok(w.body().includes("人工有异议 · 待补验"));
  });
}

test("lightweight issue tracks the two business submissions and retains its acceptor", () => {
  const w = openWorkbench();
  w.click("light"); w.click("createLight");
  assert.match(w.body(), /1 \/ 2/);
  w.role("bing");
  assert.equal(w.can("acceptLight"), false);
  w.replay("acceptLight");
  assert.match(w.body(), /1 \/ 2/);
  w.role("lin"); w.click("acceptLight");
  assert.match(w.body(), /2 \/ 2/);
  w.reset();
  assert.equal(w.tag("createLight"), undefined);
  w.click("light");
  assert.match(w.body(), /0 \/ 2/);
});

test("shared Leader capacity, lost connection and incomplete upstream delivery have different explanations", () => {
  const w = openWorkbench();
  w.click("capacity");
  assert.match(w.body(), /订单批量导出<\/strong>/);
  assert.match(w.body(), /等待同一 Leader Runtime 释放容量/);
  assert.match(w.body(), /等待前置结果/);
  w.click("offline");
  assert.match(w.body(), /甲、乙已获准的其他机器/);
  assert.match(w.body(), /在途 Run 与副作用/);
  w.click("capacity");
  assert.match(w.body(), /唯一 Leader 槽位/);
});

test("the static fallback identifies the acceptance gap when scripts cannot run", () => {
  const fallback = html.match(/<noscript>([\s\S]*?)<\/noscript>/)[1];
  assert.match(fallback, /A2 权限失败/);
  assert.match(fallback, /A2 与 A3 内容检查均通过/);
  assert.match(fallback, /A6 候选关联的 UAT/);
});
