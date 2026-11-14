"""Exercise six fixed read operations with B's disposable Multica task identity."""
import argparse
from hashlib import sha256
from http.client import HTTPConnection
from io import BytesIO
import json
import os
from pathlib import Path
from zipfile import ZipFile
from urllib.parse import urlsplit


def namespaces():
    return {name: sha256(os.readlink("/proc/self/ns/" + name).encode()).hexdigest()[:16]
            for name in ("net", "pid", "mnt")}


def verify(directory):
    request = json.loads((directory / "b-request.json").read_bytes())
    url = urlsplit(request["base_url"])
    if url.scheme != "http" or url.hostname != "127.0.0.1" or not url.port or url.path not in ("", "/"):
        raise ValueError("expected loopback test server")
    routes = {
        "target": ("/api/issues/{target}", 200),
        "private_issue": ("/api/issues/{private_issue}", 404),
        "published": ("/api/attachments/{published}/download", 200),
        "unshared": ("/api/attachments/{unshared}/download", 404),
        "runtime_a": ("/api/runtimes/{runtime_a}/usage", 404),
        "runtime_b": ("/api/runtimes/{runtime_b}/usage", 200),
    }
    result = {}
    for name, (template, expected) in routes.items():
        peer = HTTPConnection(url.hostname, url.port, timeout=15)
        try:
            peer.request("GET", template.format_map(request), headers={
                "Authorization": "Bearer " + request["token"], "X-Workspace-ID": request["workspace"]})
            response = peer.getresponse()
            data = response.read()
        finally:
            peer.close()
        result[name] = response.status
        if response.status != expected:
            raise AssertionError(f"{name}: HTTP {response.status}, expected {expected}")
        if name == "published":
            result["size"] = len(data)
            result["sha256"] = sha256(data).hexdigest()
            assert (len(data), result["sha256"]) == (request["size"], request["sha256"])
            with ZipFile(BytesIO(data)) as book:
                assert book.testzip() is None and "xl/workbook.xml" in book.namelist()
    result["different_namespace"] = {key: value != request["namespaces"][key]
                                     for key, value in namespaces().items()}
    with (directory / "b-result.tmp").open("x") as out:
        json.dump(result, out, sort_keys=True)
    (directory / "b-result.tmp").replace(directory / "b-result.json")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    print(json.dumps(verify(parser.parse_args().directory), indent=2))
