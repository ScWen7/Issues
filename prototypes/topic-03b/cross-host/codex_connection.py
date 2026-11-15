"""Attach a second authenticated client to the explicitly shared loopback App Server."""
from contextlib import ExitStack, contextmanager
from hashlib import sha256
import json
import os
import re
import secrets
import subprocess
import threading
import time
from queue import Queue

from websockets.exceptions import InvalidStatus
from websockets.sync.client import connect


class SocketClient:
    def __init__(self, socket, name):
        self.socket = socket
        self.sequence = 0
        self.seen = []
        self.call("initialize", {"clientInfo": {"name": name, "version": "1"},
                                 "capabilities": {"experimentalApi": True}})
        socket.send(json.dumps({"method": "initialized", "params": {}}))

    def call(self, method, params):
        self.sequence += 1
        self.socket.send(json.dumps({"id": self.sequence, "method": method, "params": params}))
        message = self.wait(lambda m: m.get("id") == self.sequence)
        if "error" in message:
            raise RuntimeError(message["error"])
        return message["result"]

    def wait(self, predicate):
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            message = json.loads(self.socket.recv(timeout=max(0, deadline - time.monotonic())))
            self.seen.append(message)
            if predicate(message):
                return message
        raise TimeoutError("App Server response timed out")


@contextmanager
def shared_endpoint(binary, home, work):
    env = {"PATH": os.environ["PATH"], "HOME": str(home), "CODEX_HOME": str(home),
           "NO_PROXY": "127.0.0.1,localhost", "HTTP_PROXY": "http://127.0.0.1:1",
           "HTTPS_PROXY": "http://127.0.0.1:1", "NO_COLOR": "1"}
    token = secrets.token_urlsafe(32)
    # The member host chooses an OS-assigned port and accepts only its ephemeral bearer.
    args = [binary, "app-server", "--listen", "ws://127.0.0.1:0", "--ws-auth", "capability-token",
            "--ws-token-sha256", sha256(token.encode()).hexdigest()]
    with ExitStack() as stack:
        daemon = subprocess.Popen(args, env=env, cwd=work, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                  stderr=subprocess.PIPE, text=True)
        def stop():
            daemon.terminate()
            try:
                daemon.wait(timeout=3)
            except subprocess.TimeoutExpired:
                daemon.kill()
                daemon.wait()
            daemon.stderr.close()
        stack.callback(stop)
        address = Queue()
        def read_banner():
            for line in daemon.stderr:
                match = re.search(r"ws://127\.0\.0\.1:(\d+)", line)
                if match and int(match.group(1)) > 0:
                    address.put(match.group(0))
        threading.Thread(target=read_banner, daemon=True).start()
        url = address.get(timeout=10)
        try:
            with connect(url, proxy=None, open_timeout=3):
                raise AssertionError("socket accepted an unauthenticated client")
        except InvalidStatus as error:
            assert error.response.status_code in (401, 403), error.response.status_code
        yield url, token


@contextmanager
def connected_clients(binary, home, work):
    with shared_endpoint(binary, home, work) as (url, token), ExitStack() as stack:
        def open_client(name):
            ws = stack.enter_context(connect(url, additional_headers={"Authorization": "Bearer " + token},
                                             proxy=None, open_timeout=3, max_size=8 * 1024 * 1024))
            return SocketClient(ws, name)
        yield open_client("member-order-fixture"), lambda: open_client("platform-order-fixture")
