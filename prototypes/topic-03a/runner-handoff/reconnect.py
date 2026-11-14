"""Preserve a synthetic A outbox through a stopped worker and verify B's handoff."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.request

from transfer import EXPECTED, host_signature, receive


def sha(content):
    return hashlib.sha256(content).hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, sort_keys=True))


def stop_worker(private, publication):
    private.mkdir()
    report = EXPECTED.with_name("order-export-c1.json").read_bytes()
    (private / "outbox.json").write_bytes(report)
    c = json.loads((publication / "sender.json").read_text())["challenge"]
    save(private / "stopped.json", {"host": host_signature(c), "challenge": c, "pending": sha(report)})


def wait_for(name):
    repo = os.environ["GITHUB_REPOSITORY"]
    run = os.environ["GITHUB_RUN_ID"]
    api = f"https://api.github.com/repos/{repo}/actions/runs/{run}/artifacts"
    deadline = time.monotonic() + 210
    while time.monotonic() < deadline:
        req = urllib.request.Request(api, headers={"Authorization": "Bearer " + os.environ["GH_TOKEN"],
                                                  "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=12) as response:
            candidates = json.load(response)["artifacts"]
        if any(a["name"] == name and not a["expired"] for a in candidates):
            return
        time.sleep(4)
    raise TimeoutError(f"missing current-run artifact: {name}")


def accept(publication, destination):
    receive(publication, require_distinct_boot=True)
    sender = json.loads((publication / "sender.json").read_text())
    save(destination, {"receiver": host_signature(sender["challenge"]), "source": sender["sender"],
                       "current": sha(EXPECTED.read_bytes()), "verdict": "pass"})


def reconnect(private, receipt, destination):
    checkpoint = json.loads((private / "stopped.json").read_text())
    pending = (private / "outbox.json").read_bytes()
    b = json.loads(receipt.read_text())
    a = host_signature(checkpoint["challenge"])
    if not (a == b["source"] == checkpoint["host"] and a != b["receiver"]):
        raise ValueError("expected the original producer VM and a different receiving VM")
    if b["current"] != sha(EXPECTED.read_bytes()) or b["verdict"] != "pass":
        raise ValueError("B has not confirmed the C2 candidate")
    if checkpoint["pending"] != sha(pending) or pending != EXPECTED.with_name("order-export-c1.json").read_bytes():
        raise ValueError("pending C1 evidence changed during A downtime")
    destination.mkdir()
    (destination / "late-c1.json").write_bytes(pending)
    print("Same A kernel resumed after separate B verified C2; original C1 outbox re-emitted", sha(pending))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    for name, args in {"stop": ["private", "publication"], "accept": ["publication", "destination"],
                       "reconnect": ["private", "receipt", "destination"]}.items():
        action = actions.add_parser(name)
        for arg in args:
            action.add_argument(arg, type=Path)
    actions.add_parser("wait").add_argument("name")
    params = vars(parser.parse_args())
    action = params.pop("action")
    {"stop": stop_worker, "wait": wait_for, "accept": accept, "reconnect": reconnect}[action](**params)
