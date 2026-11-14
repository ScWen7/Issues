"""Cross-runner integration for six fixed, synthetic Multica task reads."""
import argparse
import base64
import hashlib
from http.client import HTTPConnection
from io import BytesIO
import json
import os
from pathlib import Path
import time
import urllib.request
from urllib.parse import urlencode, urlsplit
from uuid import UUID
from zipfile import ZipFile

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa


ROUTES = {
    "target": ("/api/issues/{}", 200),
    "private_issue": ("/api/issues/{}", 404),
    "published": ("/api/attachments/{}/download", 200),
    "unshared": ("/api/attachments/{}/download", 404),
    "runtime_a": ("/api/runtimes/{}/usage", 404),
    "runtime_b": ("/api/runtimes/{}/usage", 200),
}
PAD = padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
ROOT = Path(__file__).resolve().parents[3]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def save(path, data):
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)


def wait(path, timeout=475):
    deadline = time.monotonic() + timeout
    while not path.is_file():
        if time.monotonic() > deadline:
            raise TimeoutError(f"missing {path.name}")
        time.sleep(1)
    return path.read_bytes()


def boot(challenge):
    return digest((challenge + ":" + Path("/proc/sys/kernel/random/boot_id").read_text().strip()).encode())


def namespaces():
    return {n: digest(os.readlink("/proc/self/ns/" + n).encode())[:16] for n in ("net", "pid", "mnt")}


def make_key(work):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    (work / "private.pem").write_bytes(key.private_bytes(serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    (work / "public.pem").write_bytes(key.public_key().public_bytes(serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo))


def read_key(work):
    return Fernet((work / "session.key").read_bytes())


def seal(key, path, value):
    save(path, key.encrypt(json.dumps(value).encode()))


def unseal(key, path):
    return json.loads(key.decrypt(wait(path)))


def requests_for(context):
    headers = {"Authorization": "Bearer " + context["token"], "X-Workspace-ID": str(UUID(context["workspace"]))}
    return [{"name": name, "method": "GET", "path": template.format(UUID(context[name])), "headers": headers}
            for name, (template, _) in ROUTES.items()]


def center(private):
    work = Path(os.environ["AP_NATIVE_STAGE"])
    context = json.loads((private / "b-request.json").read_bytes())
    url = urlsplit(context.pop("base_url"))
    if url.scheme != "http" or url.hostname != "127.0.0.1" or not url.port:
        raise ValueError("expected loopback fixture")
    context["challenge"] = os.urandom(16).hex()
    context["sender"] = boot(context["challenge"])
    key_bytes = Fernet.generate_key()
    key = Fernet(key_bytes)
    pub = serialization.load_pem_public_key((work / "public.pem").read_bytes())
    offer = {"wrapped": base64.b64encode(pub.encrypt(key_bytes, PAD)).decode(),
             "context": key.encrypt(json.dumps(context).encode()).decode()}
    save(work / "offer.json", json.dumps(offer).encode())

    # Reject any additional method, path, ID or header before making a call.
    # The production native handlers make the access decisions on each request.
    requests = unseal(key, work / "reads.sealed")
    if requests != requests_for(context):
        raise ValueError("the receiver requested a different set of fixture reads")
    results = {}
    for item in requests:
        conn = HTTPConnection("127.0.0.1", url.port, timeout=15)
        try:
            conn.request(item["method"], item["path"], headers=item["headers"])
            res = conn.getresponse()
            body = res.read(1024 * 1024)
            results[item["name"]] = {"status": res.status, "body": base64.b64encode(body).decode()}
        finally:
            conn.close()
    seal(key, work / "responses.sealed", results)
    ack = unseal(key, work / "receipt.sealed")
    if ack["challenge"] != context["challenge"] or ack["sender"] != context["sender"]:
        raise ValueError("wrong exchange")
    if os.environ.get("GITHUB_ACTIONS") == "true" and ack["receiver"] == context["sender"]:
        raise ValueError("expected independent VM boots")
    save(private / "b-result.json", json.dumps(ack).encode())


def make_reads(work):
    private = serialization.load_pem_private_key((work / "private.pem").read_bytes(), None)
    offer = json.loads((work / "offer.json").read_bytes())
    key_bytes = private.decrypt(base64.b64decode(offer["wrapped"]), PAD)
    (work / "session.key").write_bytes(key_bytes)
    key = Fernet(key_bytes)
    context = json.loads(key.decrypt(offer["context"].encode()))
    seal(key, work / "local-context.sealed", context)
    seal(key, work / "reads.sealed", requests_for(context))


def accept(work):
    key = read_key(work)
    context = unseal(key, work / "local-context.sealed")
    responses = unseal(key, work / "responses.sealed")
    own_boot = boot(context["challenge"])
    distinct = own_boot != context["sender"]
    if os.environ.get("GITHUB_ACTIONS") == "true" and not distinct:
        raise ValueError("VM boot IDs matched")
    if set(responses) != set(ROUTES):
        raise ValueError("incomplete response set")
    ack = {"challenge": context["challenge"], "sender": context["sender"], "receiver": own_boot,
           "different_namespace": {n: x != context["namespaces"][n] for n, x in namespaces().items()}}
    bodies = {}
    for name, (_, expected) in ROUTES.items():
        ack[name] = responses[name]["status"]
        if ack[name] != expected:
            raise ValueError(f"{name}: expected {expected}, got {ack[name]}")
        bodies[name] = base64.b64decode(responses[name]["body"], validate=True)
    if json.loads(bodies["target"])["id"] != context["target"]:
        raise ValueError("wrong Issue")
    report = (ROOT / "docs/research/topic-03a/fixtures/order-export-c2.json").read_text().strip()
    candidate = json.loads(report)
    if (candidate["candidate"], candidate["verdict"], candidate["A2"], candidate["A3"]) != ("C2", "pass", True, True):
        raise ValueError("unexpected C2 report")
    expected = next(x for x in candidate["artifacts"] if x["name"] == "east.xlsx")
    book = bodies["published"]
    ack["sha256"], ack["size"] = digest(book), len(book)
    if (ack["sha256"], ack["size"]) != (expected["sha256"], expected["bytes"]):
        raise ValueError("workbook differs from C2 on receiver")
    with ZipFile(BytesIO(book)) as archive:
        if archive.testzip() or "xl/workbook.xml" not in archive.namelist():
            raise ValueError("invalid workbook")
    ack["current_report"] = report
    seal(key, work / "receipt.sealed", ack)
    print(json.dumps({"distinct_boots": distinct, "status": {name: ack[name] for name in ROUTES},
                      "workbook_bytes": len(book), "sha256": ack["sha256"], "report": candidate["verdict"]}))


def wait_artifact(name):
    token = os.environ["GH_TOKEN"]
    url = "https://api.github.com/repos/{}/actions/runs/{}/artifacts?".format(
        os.environ["GITHUB_REPOSITORY"], os.environ["GITHUB_RUN_ID"]) + urlencode({"name": name, "per_page": 100})
    deadline = time.monotonic() + 35 * 60
    while time.monotonic() < deadline:
        request = urllib.request.Request(url, headers={"Authorization": "Bearer " + token,
                                                      "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(request, timeout=30) as res:
            found = json.load(res)["artifacts"]
        if any(item["name"] == name and not item["expired"] for item in found):
            return
        time.sleep(6)
    raise TimeoutError("missing current-run artifact " + name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("role", choices=["key", "reads", "accept", "wait-file", "wait-artifact"])
    parser.add_argument("argument")
    args = parser.parse_args()
    if args.role == "wait-artifact":
        wait_artifact(args.argument)
    else:
        os.umask(0o077)
        {"key": make_key, "reads": make_reads, "accept": accept, "wait-file": lambda path: wait(path, timeout=35 * 60)}[args.role](Path(args.argument))
