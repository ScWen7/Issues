"""Local stdio MCP and durable authority fixture for one read-only order tool."""
import hashlib
import json
from pathlib import Path
from copy import deepcopy
import sqlite3
import sys
from uuid import uuid4

HERE = Path(__file__).resolve().parent
VERIFIER = HERE.parents[1] / "topic-03a/order-export/verify.py"
TOOL = "inspect_order"
PROJECT = "orders/inspect-workbook@2"
PERSONAL = "personal/inspect-workbook@1"
SCHEMA = {
    "name": TOOL, "description": "Inspect the bound order candidate workbooks, returning the D2 verification report.",
    "annotations": {"readOnlyHint": True},
    "inputSchema": {"type": "object", "properties": {"candidate": {"type": "string", "enum": ["C1", "C2"]}},
                    "required": ["candidate"], "additionalProperties": False},
}
TABLES = """
CREATE TABLE leases(run TEXT PRIMARY KEY, member TEXT NOT NULL, runtime TEXT NOT NULL, epoch INTEGER NOT NULL,
                    contract TEXT NOT NULL, token_hash TEXT NOT NULL, active INTEGER NOT NULL);
CREATE TABLE events(seq INTEGER PRIMARY KEY, receipt TEXT UNIQUE NOT NULL, service TEXT NOT NULL, run TEXT NOT NULL,
                    outcome TEXT NOT NULL, result_hash TEXT NOT NULL);
"""


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def inspect(profile, args):
    """An issued local profile stands in for the transport's authenticated task identity."""
    service, run = profile["service"], profile["run"]
    receipt = uuid4().hex
    with sqlite3.connect(profile["authority"], timeout=5) as conn:
        # Serialize this small fixture's read with revocation. The journal only carries evidence.
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT member,runtime,epoch,contract,token_hash,active FROM leases WHERE run=?", (run,)).fetchone()
        allowed = (service == PROJECT and row and row[5] and
                   tuple(row[:3]) == (profile["member"], profile["runtime"], profile["epoch"])
                   and row[4] == sha(profile["token"].encode()))
        outcome = "denied"
        result = {"status": outcome, "receipt": receipt}
        if allowed:
            contract = json.loads(row[3])
            allowed = (args == {"candidate": contract["candidate"]} and contract["provider"] == service
                       and sha(Path(__file__).read_bytes()) == contract["service_sha256"]
                       and sha(VERIFIER.read_bytes()) == contract["verifier_sha256"])
            if allowed:
                result = inspect_bound(profile, contract, receipt)
                outcome = result["status"]
        conn.execute("INSERT INTO events(receipt,service,run,outcome,result_hash) VALUES(?,?,?,?,?)",
                     (receipt, service, run, outcome, sha(encoded(result))))
    return result


def inspect_bound(profile, contract, receipt):
    from importlib.util import module_from_spec, spec_from_file_location
    spec = spec_from_file_location("order_verifier", VERIFIER)
    verifier = module_from_spec(spec)
    spec.loader.exec_module(verifier)
    directory = Path(profile["artifacts"]) / contract["candidate"]
    # The fixture uses immutable, generated inputs. Verify the bytes actually read by the oracle.
    binding = {k: contract[k] for k in ("issue", "node", "attempt", "candidate", "rule", "commit")}
    report = verifier.inspect(directory, {**binding, "run": profile["run"]})
    if report["artifacts"] != contract["artifacts"]:
        return {"status": "invalid_artifacts", "receipt": receipt}
    return {"status": "ok", "receipt": receipt, "provider": PROJECT, "report": report}


def serve(profile_path):
    profile = json.loads(profile_path.read_bytes())
    definition = deepcopy(SCHEMA)
    if profile.get("interface") == "incompatible":
        definition["inputSchema"]["properties"]["candidate"] = {"type": "integer"}
    for line in sys.stdin:
        message = json.loads(line)
        if "id" not in message:
            continue
        method = message["method"]
        if method == "initialize":
            result = {"protocolVersion": message["params"]["protocolVersion"], "capabilities": {"tools": {}},
                      "serverInfo": {"name": profile["service"], "version": "1"}}
        elif method == "tools/list":
            result = {"tools": [definition]}
        elif method == "tools/call" and message["params"]["name"] == TOOL:
            value = inspect(profile, message["params"].get("arguments", {}))
            result = {"content": [{"type": "text", "text": encoded(value).decode()}], "isError": value["status"] != "ok"}
        elif method == "ping":
            result = {}
        else:
            print(json.dumps({"jsonrpc": "2.0", "id": message["id"], "error": {"code": -32601, "message": "unknown method"}}), flush=True)
            continue
        print(json.dumps({"jsonrpc": "2.0", "id": message["id"], "result": result}), flush=True)


if __name__ == "__main__":
    serve(Path(sys.argv[1]))
