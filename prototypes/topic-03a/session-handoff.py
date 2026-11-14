"""Test session identity across isolated local profiles with the real Codex and Claude binaries."""

import argparse
from contextlib import contextmanager
import hashlib
from http.server import ThreadingHTTPServer
from io import BytesIO
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading


HERE = Path(__file__).resolve().parent
PRIVATE_RULE = 'ap5-private-D1-original-order-columns'
PRIVATE_NOTE = 'ap5-private-A-working-notes-unshared'
CURRENT_RULE = 'D2: include payment_time in the export and leave it blank for unpaid orders.'


def load_fixture(filename, name):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


codex = load_fixture('codex-context-probe.py', 'codex_context')
claude = load_fixture('claude-context-probe.py', 'claude_context')


@contextmanager
def endpoint(handler, route):
    # Examine the actual request delivered to the loopback model, including history and instructions.
    class Recorder(handler):
        def do_POST(self):
            if self.path.split('?')[0] != route:
                self.send_error(404)
                return
            body = self.rfile.read(int(self.headers['Content-Length']))
            self.server.payloads.append(json.loads(body))
            stream = self.rfile
            try:
                self.rfile = BytesIO(body)
                super().do_POST()
            finally:
                self.rfile = stream

    with ThreadingHTTPServer(('127.0.0.1', 0), Recorder) as server:
        server.payloads = []
        server.inputs = []
        server.requests = 0 if handler is codex.CapturingEndpoint else []
        server.ask_mcp = False
        server.ask_tool = None
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            yield server
        finally:
            server.shutdown()


def selected_materials():
    raw = (HERE.parents[1] / 'docs/research/topic-03a/fixtures/order-export-c2.json').read_bytes()
    report = json.loads(raw)
    assert (report['rule'], report['candidate'], report['verdict']) == ('D2', 'C2', 'pass')
    return {'current_rule': CURRENT_RULE, 'candidate': 'C2@' + report['commit'],
            'report_sha256': hashlib.sha256(raw).hexdigest()}


def run_scenarios(server, invoke, shared):
    markers = {'private_rule': PRIVATE_RULE, 'private_note': PRIVATE_NOTE, **shared}
    rows = []

    def step(label, owner, prompt, expected, prior=None, same_cwd=False, rejection=False):
        before = len(server.payloads)
        session, error = invoke(owner, prompt, prior, same_cwd, rejection)
        payloads = server.payloads[before:]
        assert len(payloads) == (0 if rejection else 1), (label, len(payloads), error)
        if rejection:
            assert session is None and error, (label, session, error)
        else:
            assert session and not error, (label, error)
        observation = {name: claude.locations(payloads[0], value) if payloads else []
                       for name, value in markers.items()}
        assert {name for name, paths in observation.items() if paths} == set(expected), (label, observation)
        rows.append({'step': label, 'session': session, 'error': error, 'model_requests': len(payloads),
                     'request_marker_locations': observation})
        return session

    a = step('A_start', 'A', PRIVATE_RULE + '\n' + PRIVATE_NOTE, ['private_rule', 'private_note'])
    step('B_resume_A', 'B', 'Continue.', [], prior=a, rejection=True)
    # Holding the cwd constant checks whether the project path alone makes the previous profile resumable.
    step('B_resume_A_same_cwd', 'B', 'Continue.', [], prior=a, same_cwd=True, rejection=True)
    b = step('B_new_with_shared_selection', 'B', json.dumps(shared), shared)
    assert a != b, (a, b)
    resumed = step('A_resume_A', 'A', 'Continue the original investigation.',
                   ['private_rule', 'private_note'], prior=a)
    assert resumed == a, (a, resumed)
    return rows


def profiles(root):
    for member in ('A', 'B'):
        (root / member / 'home').mkdir(parents=True)
        (root / member / 'project').mkdir()


def codex_probe(binary, root, shared):
    profiles(root)
    with endpoint(codex.CapturingEndpoint, '/v1/responses') as server:
        for member in ('A', 'B'):
            (root / member / 'home/config.toml').write_text(f'''model = "gpt-5.1-codex"
model_provider = "fixture"
project_doc_max_bytes = 0
[model_providers.fixture]
name = "fixture"
base_url = "http://127.0.0.1:{server.server_port}/v1"
wire_api = "responses"
requires_openai_auth = false
supports_websockets = false
request_max_retries = 0
stream_max_retries = 0
[analytics]
enabled = false
''')

        def invoke(member, prompt, prior, same_cwd, rejection):
            project = root / ('A' if same_cwd else member) / 'project'
            with codex.client(binary, root / member / 'home', project) as rpc:
                if prior:
                    try:
                        thread = rpc.call('thread/resume', {'threadId': prior})['thread']['id']
                    except RuntimeError as exc:
                        error = exc.args[0]
                        if (rejection and isinstance(error, dict) and prior in error['message']
                                and 'no rollout found' in error['message'].lower()):
                            return None, error['message']
                        raise
                else:
                    thread = rpc.call('thread/start', {'cwd': str(project), 'sandbox': 'read-only',
                                                       'approvalPolicy': 'on-request'})['thread']['id']
                assert not rejection, ('unexpected resume', thread)
                turn = rpc.call('turn/start', {'threadId': thread, 'input': [{'type': 'text', 'text': prompt}]})
                done = rpc.wait(lambda m: m.get('method') == 'turn/completed' and
                                 m['params']['turn']['id'] == turn['turn']['id'])
                assert done['params']['turn']['status'] == 'completed', done
                return thread, None

        return run_scenarios(server, invoke, shared)


def claude_probe(binary, root, shared):
    profiles(root)
    with endpoint(claude.ModelFixture, '/v1/messages') as server:
        def invoke(member, prompt, prior, same_cwd, rejection):
            home = str(root / member / 'home')
            project = root / ('A' if same_cwd else member) / 'project'
            env = {'HOME': home, 'CLAUDE_CONFIG_DIR': home, 'PATH': os.environ['PATH'],
                   'ANTHROPIC_BASE_URL': f'http://127.0.0.1:{server.server_port}',
                   'ANTHROPIC_API_KEY': 'test-local-only', 'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC': '1',
                   'CLAUDE_CODE_DISABLE_BACKGROUND_TASKS': '1', 'DISABLE_AUTOUPDATER': '1', 'NO_COLOR': '1'}
            cmd = [binary, '-p', '--model', 'claude-sonnet-4-6', '--setting-sources', '',
                   '--output-format', 'json', '--tools=']
            if prior:
                cmd.extend(['--resume', prior])
            result = subprocess.run([*cmd, prompt], env=env, cwd=project, capture_output=True, text=True, timeout=45)
            if rejection:
                diagnostic = result.stderr + '\n' + result.stdout
                assert result.returncode != 0 and prior in diagnostic and 'no conversation found' in diagnostic.lower(), diagnostic
                return None, {'exit_code': result.returncode, 'reason': 'no_conversation_found', 'requested_session': prior}
            assert result.returncode == 0, result.stderr
            reply = json.loads(result.stdout)
            assert reply['subtype'] == 'success' and not reply['is_error'], reply
            return reply['session_id'], None

        return run_scenarios(server, invoke, shared)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--codex', required=True, type=Path)
    parser.add_argument('--claude', required=True, type=Path)
    args = parser.parse_args()
    shared = selected_materials()
    with tempfile.TemporaryDirectory(prefix='ap-session-handoff-') as temp:
        for flag, expected, run in [(args.codex, 'codex-cli 0.144.6', codex_probe),
                                    (args.claude, '2.1.325 (Claude Code)', claude_probe)]:
            binary = str(flag.resolve())
            version = subprocess.check_output([binary, '--version'], text=True).strip()
            assert version == expected, (version, expected)
            rows = run(binary, Path(temp) / run.__name__, shared)
            print(json.dumps({'version': version, 'shared': shared, 'observations': rows}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
