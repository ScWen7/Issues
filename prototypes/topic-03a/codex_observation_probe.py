"""Inspect Codex protocol accounting using a local synthetic Responses endpoint.

Run with Python 3.10+ and codex-cli 0.167.0-alpha.4 on PATH.
The subprocess receives an empty temporary home and no account credentials.
"""
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class ResponsesFixture(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        if self.path != "/v1/responses":
            self.send_error(404)
            return
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        self.server.requests += 1
        number = self.server.requests
        response_id = f"response-fixture-{number}"
        usage = {"input_tokens": 10 * number, "output_tokens": number, "total_tokens": 11 * number}
        events = [
            {"type": "response.created", "response": {"id": response_id}},
            {"type": "response.output_item.done", "item": {
                "type": "message", "role": "assistant", "id": f"msg_{number}",
                "content": [{"type": "output_text", "text": f"fixture-{number}"}],
            }},
            {"type": "response.completed", "response": {"id": response_id, "usage": usage}},
        ]
        body = "".join(f"data: {json.dumps(event)}\n\n" for event in events).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class AppServer:
    def __init__(self, binary, root, env, stderr):
        self.proc = subprocess.Popen(
            [binary, "app-server", "--listen", "stdio://"], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=stderr, cwd=root, env=env, text=True, bufsize=1,
        )
        self.messages = queue.Queue()
        self.seen = []
        self.next_id = 1
        threading.Thread(target=self.read_output, daemon=True).start()

    def read_output(self):
        for line in self.proc.stdout:
            self.messages.put(json.loads(line))

    def send(self, method, params, request_id=None):
        payload = {"method": method, "params": params}
        if request_id is not None:
            payload["id"] = request_id
        self.proc.stdin.write(json.dumps(payload) + "\n")
        self.proc.stdin.flush()

    def wait(self, predicate):
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            try:
                message = self.messages.get(timeout=0.2)
            except queue.Empty:
                if self.proc.poll() is not None:
                    raise RuntimeError(f"App Server exited with {self.proc.returncode}")
                continue
            self.seen.append(message)
            if predicate(message):
                return message
        raise TimeoutError("App Server event timed out")

    def call(self, method, params):
        request_id = self.next_id
        self.next_id += 1
        self.send(method, params, request_id)
        result = self.wait(lambda msg: msg.get("id") == request_id)
        if "error" in result:
            raise RuntimeError(result["error"])
        return result["result"]

    def close(self):
        self.proc.terminate()
        try:
            self.proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()
        self.proc.stdin.close()
        self.proc.stdout.close()


def probe(binary, root, http):
    env = {
        "PATH": os.environ["PATH"], "HOME": str(root), "CODEX_HOME": str(root),
        "NO_PROXY": "127.0.0.1,localhost", "HTTPS_PROXY": "http://127.0.0.1:1",
        "HTTP_PROXY": "http://127.0.0.1:1",
    }
    (root / "config.toml").write_text(f'''model = "gpt-5.1-codex"
model_provider = "fixture"
project_doc_max_bytes = 0
[model_providers.fixture]
name = "fixture"
base_url = "http://127.0.0.1:{http.server_address[1]}/v1"
wire_api = "responses"
requires_openai_auth = false
supports_websockets = false
request_max_retries = 0
stream_max_retries = 0
[analytics]
enabled = false
''')
    with (root / "stderr.log").open("w+") as err:
        server = AppServer(binary, root, env, err)
        try:
            server.call("initialize", {"clientInfo": {"name": "observationfixture", "version": "1"}})
            server.send("initialized", {})
            thread_id = server.call("thread/start", {
                "cwd": str(root), "sandbox": "read-only", "approvalPolicy": "never",
            })["thread"]["id"]
            turns = []
            for number in (1, 2):
                turn_id = server.call("turn/start", {
                    "threadId": thread_id, "input": [{"type": "text", "text": f"test {number}"}],
                })["turn"]["id"]
                done = server.wait(lambda msg: msg.get("method") == "turn/completed"
                                   and msg["params"]["turn"]["id"] == turn_id)
                assert done["params"]["turn"]["status"] == "completed", done
                turns.append(turn_id)
            assert len(set(turns)) == 2
            readings = [(m["params"]["turnId"], m["params"]["tokenUsage"]["last"]["totalTokens"],
                         m["params"]["tokenUsage"]["total"]["totalTokens"])
                        for m in server.seen if m.get("method") == "thread/tokenUsage/updated"]
            assert readings == [(turns[0], 11, 11), (turns[1], 22, 33)], readings
            history = server.call("thread/read", {"threadId": thread_id, "includeTurns": True})["thread"]
            assert [turn["id"] for turn in history["turns"]] == turns
            for turn in history["turns"]:
                assert [item["type"] for item in turn["items"]] == ["userMessage", "agentMessage"]
            print("One thread, two distinct turns, each with userMessage and agentMessage.")
            print("Host usage (last, total): (11, 11), (22, 33).")
            resumed = server.call("thread/resume", {"threadId": thread_id})
            assert resumed["thread"]["id"] == thread_id
            replay = server.wait(lambda msg: msg.get("method") == "thread/tokenUsage/updated"
                                 and msg["params"]["turnId"] == turns[-1])
            assert replay["params"]["tokenUsage"]["total"]["totalTokens"] == 33
            assert http.requests == 2, http.requests
            print("Resume replayed total 33; fixture request count stayed at 2.")
        finally:
            server.close()
    result = subprocess.run(
        [binary, "exec", "resume", "--json", "--skip-git-repo-check", thread_id, "test 3"],
        cwd=root, env=env, capture_output=True, text=True, timeout=25, check=True,
    )
    events = [json.loads(line) for line in result.stdout.splitlines()]
    started = next(event for event in events if event["type"] == "turn.started")
    completed = next(event for event in events if event["type"] == "turn.completed")
    assert set(started) == {"type"}, started
    assert (completed["usage"]["input_tokens"], completed["usage"]["output_tokens"]) == (60, 6)
    assert http.requests == 3, http.requests
    print("exec resume emits turn.started without turn ID; last turn input/output fixture 30/3, displayed 60/6.")


def main():
    binary = shutil.which("codex")
    if not binary:
        raise SystemExit("Requires codex-cli on PATH.")
    print(subprocess.check_output([binary, "--version"], text=True).strip())
    with ThreadingHTTPServer(("127.0.0.1", 0), ResponsesFixture) as http:
        http.requests = 0
        threading.Thread(target=http.serve_forever, daemon=True).start()
        try:
            with tempfile.TemporaryDirectory(prefix="codex-observation-") as folder:
                probe(binary, Path(folder), http)
        finally:
            http.shutdown()


if __name__ == "__main__":
    main()
