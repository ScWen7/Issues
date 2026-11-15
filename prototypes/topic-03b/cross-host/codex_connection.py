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
        self.pending_notifications = []
        self.call("initialize", {"clientInfo": {"name": name, "version": "1"},
                                 "capabilities": {"experimentalApi": True}})
        socket.send(json.dumps({"method": "initialized", "params": {}}))

    def receive(self, deadline):
        message = json.loads(self.socket.recv(timeout=max(0, deadline - time.monotonic())))
        self.seen.append(message)
        return message

    def call(self, method, params):
        self.sequence += 1
        self.socket.send(json.dumps({"id": self.sequence, "method": method, "params": params}))
        deadline = time.monotonic() + 20
        while True:
            message = self.receive(deadline)
            if message.get("id") == self.sequence and "method" not in message:
                if "error" in message:
                    raise RuntimeError(message["error"])
                return message["result"]
            self.pending_notifications.append(message)

    def wait(self, predicate):
        # A turn can finish before its RPC response is read. Keep that native event.
        for index, message in enumerate(self.pending_notifications):
            if predicate(message):
                return self.pending_notifications.pop(index)
        deadline = time.monotonic() + 20
        while True:
            message = self.receive(deadline)
            if predicate(message):
                return message
            self.pending_notifications.append(message)


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
