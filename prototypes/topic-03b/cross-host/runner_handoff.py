"""Transfer one revoked synthetic C2 dispatch between sequential runners with independent disks."""
import argparse
from contextlib import closing
import os
from pathlib import Path
import secrets
import subprocess
import sys
from uuid import UUID

from order_handoff import ADMISSION, FIXTURES, ORDERS, Run, Study, frozen_contract, read, write
from order_tool import PROJECT, encoded, sha


# Fixed columns only. In the snapshot the old, revoked credential is replaced by an unusable value.
TABLES = {
    "current_node": "issue,node,run",
    "dispatch": "run,issue,node,attempt,candidate,rule,git_commit,agent,task_active,runtime_ok,visible,grant_revision,verifier",
    "delegation": "issue,node,revision,active,action",
    "leases": "run,member,runtime,epoch,contract,token_hash,active",
    "required_artifact": "run,name",
    "supplied": "run,name,bytes,digest",
    "events": "seq,receipt,service,run,outcome,result_hash",
    "host_proof": "receipt,run,call_id,host,session,turn,value_hash",
}
EMPTY = ("consumed", "artifact", "receipt", "artifact_reader")
ORIGIN = Run("original-codex", "order-member-A", "member-runtime-codex", 1, frozen_contract("C2"), {})
BASE = read(FIXTURES / "order-export-c2.json")


def check(condition, message):
    if not condition:
        raise ValueError(message)


def runner(challenge):
    boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    ci = os.environ.get("GITHUB_ACTIONS") == "true"
    return {"github": ci, "run": os.environ["GITHUB_RUN_ID"] if ci else "local",
            "attempt": os.environ["GITHUB_RUN_ATTEMPT"] if ci else "local",
            "job": os.environ["GITHUB_JOB"] if ci else "local",
            "boot_proof": sha((challenge + ":" + boot).encode())}


def snapshot(study):
    with closing(ADMISSION.connect(study.db)) as db:
        db.execute("BEGIN")
        for table in EMPTY:
            check(db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0, "unexpected existing " + table)
        state = {}
        for table, columns in TABLES.items():
            select = columns.replace("token_hash", "'retired'") if table == "leases" else columns
            state[table] = [list(row) for row in db.execute(f"SELECT {select} FROM {table} ORDER BY 1,2")]
        return state


def project_call(native):
    # Exclude host settings, launch paths, task profiles and full model envelopes.
    return {key: native[key] for key in ("thread_id", "turn_id", "call_id", "selected_tool", "arguments",
            "model_requests", "wire_request_sha256", "result", "result_sha256")}


def validate(cp):
    check(set(cp) == {"format", "challenge", "sender", "binding", "state", "calls", "export_exits"} and
          cp["format"] == 1 and cp["binding"] == ORIGIN.binding(), "unexpected checkpoint or predecessor")
    UUID(hex=cp["challenge"])
    state, contract = cp["state"], ORIGIN.contract
    issue, node, run = contract["issue"], contract["node"], ORIGIN.run
    check(set(state) == set(TABLES), "unexpected checkpoint table")
    expected = {
        "current_node": [[issue, node, run]],
        "dispatch": [[run, issue, node, contract["attempt"], "C2", contract["rule"], contract["commit"],
                      ORIGIN.member, 0, 1, 1, 1, contract["verifier_sha256"]]],
        "leases": [[run, ORIGIN.member, ORIGIN.runtime, 1, encoded(contract).decode(), "retired", 0]],
        "delegation": [[issue, node, 1, 1, "submit-report"]],
        "required_artifact": sorted([run, f["name"]] for f in contract["artifacts"]),
        "supplied": sorted([run, f["name"], f["bytes"], f["sha256"]] for f in contract["artifacts"]),
    }
    check(all(state[k] == v for k, v in expected.items()), "revoked dispatch or file references differ from C2")
    check(cp["export_exits"] == {role: value["exit"] for role, value in BASE["checks"].items()},
          "export exit codes differ from frozen fixture")
    calls = cp["calls"]
    check(len(calls) == 2, "expected one held result and one denial")
    events, proofs = [], []
    for seq, (call, status) in enumerate(zip(calls, ("ok", "denied")), 1):
        value, digest = call["result"], call["result_sha256"]
        receipt = value["receipt"]
        expected_value = {"status": status, "receipt": receipt}
        if status == "ok":
            expected_value.update(provider=PROJECT, report={**BASE, "run": run})
        check(value == expected_value and sha(encoded(value)) == digest, "wrong predecessor result")
        check(call["selected_tool"] == "mcp__project_orders.inspect_order" and call["arguments"] == {"candidate": "C2"}
              and call["model_requests"] == 2 and len(call["wire_request_sha256"]) == 2, "invalid native call")
        events.append([seq, receipt, PROJECT, run, status, digest])
        proofs.append([receipt, run, call["call_id"], "codex", call["thread_id"], call["turn_id"], digest])
    check(state["events"] == events and state["host_proof"] == sorted(proofs), "service and host records do not match")


def artifacts(source, dest):
    for entry in ORIGIN.contract["artifacts"]:
        path = source / entry["name"]
        check(path.is_file() and not path.is_symlink(), "missing workbook")
        data = path.read_bytes()
        check(len(data) == entry["bytes"] and sha(data) == entry["sha256"], "workbook differs from frozen C2")
        (dest / path.name).write_bytes(data)


def send(args):
    orders = args.work / "orders"
    subprocess.run([sys.executable, ORDERS / "run.py", orders], check=True, stdout=subprocess.DEVNULL)
    study = Study(args.work / "origin", orders, args.codex, None)
    old = study.issue(ORIGIN.run, "codex", 1)
    held = study.invoke(old, "codex", "sender-held-report")
    denied = study.invoke(old, "codex", "sender-revoked", revoke_in_flight=True)
    check(study.submit(old, denied) == "no verified tool result", "denial was accepted")
    challenge = secrets.token_hex(16)
    checkpoint = {"format": 1, "challenge": challenge, "sender": runner(challenge), "binding": old.binding(),
                  "state": snapshot(study), "calls": [project_call(held), project_call(denied)],
                  "export_exits": read(orders / "C2/export-exits.json")}
    validate(checkpoint)
    args.transfer.mkdir()
    artifacts(orders / "C2", args.transfer)
    write(args.transfer / "checkpoint.json", checkpoint)
    print("sender checkpoint", sha((args.transfer / "checkpoint.json").read_bytes()))


def receive(args):
    check({p.name for p in args.transfer.iterdir()} == {"checkpoint.json", *ADMISSION.FILES}, "unexpected transfer files")
    path = args.transfer / "checkpoint.json"
    check(path.is_file() and not path.is_symlink() and sha(path.read_bytes()) == args.transfer_sha256,
          "checkpoint differs from sender job output")
    cp = read(path)
    validate(cp)
    origin, here = cp["sender"], runner(cp["challenge"])
    check(all(origin[k] == here[k] for k in ("github", "run", "attempt")), "different workflow invocation")
    distinct = origin["boot_proof"] != here["boot_proof"]
    if here["github"]:
        check(distinct and origin["job"] != here["job"], "need two independent runner boots and jobs")
    orders = args.work / "orders"
    dest = orders / "C2"
    dest.mkdir(parents=True)
    artifacts(args.transfer, dest)
    write(dest / "export-exits.json", cp["export_exits"])
    study = Study(args.work / "receiver", orders, None, args.claude)
    with closing(ADMISSION.connect(study.db)) as db, db:
        for table, columns in TABLES.items():
            placeholders = ",".join("?" for _ in columns.split(","))
            db.executemany(f"INSERT INTO {table}({columns}) VALUES({placeholders})", cp["state"][table])
    check(snapshot(study) == cp["state"], "restored ledger differs")
    run, member, runtime, epoch, *_ = cp["state"]["leases"][0]
    old = Run(run, member, runtime, epoch, ORIGIN.contract, {})
    new = study.issue("replacement-claude", "claude", 2, prior=old)
    actual = study.invoke(new, "claude", "receiver-authorized-order-tool")
    check(actual["session_id"] not in {call["thread_id"] for call in cp["calls"]}, "receiver session reused")
    held = cp["calls"][0]
    for target, proof, decision in [(new, held, "no verified tool result"), (old, held, "access withdrawn"),
                                    (new, actual, "current"), (new, actual, "duplicate")]:
        check(study.submit(target, proof) == decision, "incorrect result admission: " + decision)
    summary = {"transport": "offline sanitized checkpoint", "sender": origin, "receiver": here,
               "checkpoint_sha256": args.transfer_sha256, "distinct_boots": distinct,
               "hosts": {"sender": "codex-cli 0.144.6", "receiver": "Claude Code 2.1.325"},
               "old_binding": old.binding(), "new_binding": new.binding(), "sender_calls": cp["calls"],
               "receiver_observations": study.summary(), "accepted_result": study.accepted_result(new, actual)}
    write(args.summary, summary)
    print("receiver", study.counts(), "distinct runner boots:", distinct)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    roles = parser.add_subparsers(dest="role", required=True)
    sender, receiver = roles.add_parser("sender"), roles.add_parser("receiver")
    for role in (sender, receiver):
        role.add_argument("--work", type=Path, required=True, help="fresh local work directory")
        role.add_argument("--transfer", type=Path, required=True, help="four-file handoff directory")
    sender.add_argument("--codex", required=True)
    receiver.add_argument("--claude", required=True)
    receiver.add_argument("--transfer-sha256", required=True, help="checkpoint.json digest from sender job output")
    receiver.add_argument("--summary", type=Path, required=True)
    options = parser.parse_args()
    options.work.mkdir()
    if options.role == "sender":
        send(options)
    else:
        receive(options)
