"""Replay the order fixture's fixed Git commit and XLSX across two HTTP clients."""
import argparse
from contextlib import contextmanager
from functools import partial
from hashlib import sha256
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
from urllib.request import urlopen
from zipfile import ZipFile


class QuietFiles(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@contextmanager
def serve(directory):
    handler = partial(QuietFiles, directory=directory)
    with ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
        worker = threading.Thread(target=server.serve_forever)
        worker.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}"
        finally:
            server.shutdown()
            worker.join()


def git(directory, *args, required=True):
    result = subprocess.run(
        ["git", "-C", str(directory), *args],
        capture_output=True, text=True, check=required,
    )
    return result


def update_remote(sender, remote, revision, branch):
    git(sender, "push", "--quiet", remote.as_uri(), revision + ":refs/heads/" + branch)
    git(remote, "update-server-info")


def size_and_digest(data):
    return len(data), sha256(data).hexdigest()


def receive_workbook(url, record, destination):
    # This consumer receives only a URL and the immutable expected size/digest.
    # The valid accepted file is retained when a later transfer disagrees.
    with urlopen(url, timeout=5) as response:
        data = response.read()
    if size_and_digest(data) != (record["bytes"], record["sha256"]):
        raise ValueError("received bytes do not match the report")
    with ZipFile(BytesIO(data)) as book:
        if book.testzip() is not None or "xl/workbook.xml" not in book.namelist():
            raise ValueError("invalid XLSX container")
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as temp:
        temp.write(data)
        path = Path(temp.name)
    try:
        os.replace(path, destination)
    finally:
        path.unlink(missing_ok=True)


def probe(order_run, scratch):
    summary = json.loads((order_run / "summary.json").read_text())
    report_bytes = (order_run / "C2/report.json").read_bytes()
    report = json.loads(report_bytes)
    binding = json.loads((order_run / "C2/binding.json").read_text())
    c1, c2 = summary["C1"]["commit"], binding["commit"]
    assert c1 != c2 and c2 == report["commit"] == summary["C2"]["commit"]
    assert all(binding[field] == report[field] for field in ("run", "node", "attempt", "candidate", "rule", "issue"))
    assert sha256(report_bytes).hexdigest() == summary["C2"]["report_sha256"]
    artifact = next(row for row in report["artifacts"] if row["name"] == "east.xlsx")
    workbook = (order_run / "C2/east.xlsx").read_bytes()
    assert size_and_digest(workbook) == (artifact["bytes"], artifact["sha256"])

    public = scratch / "published"
    public.mkdir()
    remote, sender, receiver = public / "source.git", scratch / "sender", scratch / "receiver"
    git(scratch, "clone", "--quiet", "--no-local", str(order_run / "source"), str(sender))
    git(scratch, "init", "--bare", "--quiet", "--initial-branch=main", str(remote))
    update_remote(sender, remote, c1, "main")
    with serve(public) as endpoint:
        # B's Git object store is hydrated over HTTP, with no file remote or shared objects.
        git(scratch, "clone", "--quiet", endpoint + "/source.git", str(receiver))
        assert git(receiver, "rev-parse", "HEAD").stdout.strip() == c1
        assert not (receiver / ".git/objects/info/alternates").exists()
        git(receiver, "fetch", "--quiet", "origin")
        assert git(receiver, "cat-file", "-e", c2 + "^{commit}", required=False).returncode != 0

        update_remote(sender, remote, c2, "candidate-c2")
        git(receiver, "fetch", "--quiet", "origin")
        git(receiver, "checkout", "--quiet", "--detach", c2)
        assert git(receiver, "rev-parse", "HEAD").stdout.strip() == c2

        offered = public / artifact["sha256"]
        offered.write_bytes(workbook)
        url = endpoint + "/" + offered.name
        destination = scratch / "accepted-east.xlsx"
        receive_workbook(url, artifact, destination)

        git(sender, "checkout", "--quiet", "--detach", c1)
        (sender / "late-c1.txt").write_text("Follow-up to C1 only.\n")
        git(sender, "add", "late-c1.txt")
        git(sender, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.test",
            "commit", "--quiet", "-m", "late C1 follow-up")
        late = git(sender, "rev-parse", "HEAD").stdout.strip()
        update_remote(sender, remote, late, "main")
        git(receiver, "fetch", "--quiet", "origin")
        assert git(receiver, "rev-parse", "origin/main").stdout.strip() == late
        assert git(receiver, "rev-parse", "HEAD").stdout.strip() == c2
        assert not (receiver / "late-c1.txt").exists()

        # Flip a byte without changing length, so only the content check can reject it.
        damaged = bytearray(workbook)
        damaged[len(damaged) // 2] ^= 1
        offered.write_bytes(damaged)
        try:
            receive_workbook(url, artifact, destination)
        except ValueError as error:
            assert str(error) == "received bytes do not match the report"
        else:
            raise AssertionError("damaged workbook was accepted")
        assert size_and_digest(destination.read_bytes()) == (artifact["bytes"], artifact["sha256"])
    return {
        "before_publication": "C2 absent after fetch", "detached_commit": c2,
        "late_C1": "origin/main advanced; checkout remained C2",
        "artifact": artifact["name"], "verified_bytes": artifact["bytes"],
        "sha256": artifact["sha256"], "same_size_corruption": "rejected; accepted file preserved",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("order_run", type=Path, help="output directory of the order export fixture")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="order-handoff-") as scratch:
        print(json.dumps(probe(args.order_run.resolve(), Path(scratch)), indent=2))
