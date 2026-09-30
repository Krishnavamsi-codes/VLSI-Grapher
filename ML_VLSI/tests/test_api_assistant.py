"""HTTP routes of the assistant (LLM mocked): availability, errors, size limits, key safety."""
import http.client
import json
import threading

import pytest

from fake_llm import FakeLLM, make_client, openai_error

DEMO = 'Demo_cut_carry__Validate_add_mul_8_bit_Syn_65nm.v'
KEY = 'sk-test-SECRETKEY-abcdef0123456789'


def _start(llm):
    import web_dashboard
    srv = web_dashboard.make_server('127.0.0.1', 0, llm=llm, probe=False)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def _req(srv, method, path, body=None):
    conn = http.client.HTTPConnection('127.0.0.1', srv.server_address[1], timeout=120)
    conn.request(method, path, body=json.dumps(body).encode() if body is not None else None,
                 headers={'Content-Type': 'application/json'} if body is not None else {})
    r = conn.getresponse()
    raw = r.read()
    conn.close()
    return r.status, raw, json.loads(raw)


@pytest.fixture()
def unavailable_server():
    client, logs = make_client([openai_error('auth', KEY)], key=KEY)
    client.probe()                                   # fails -> unavailable with a reason
    srv = _start(client)
    yield srv, logs
    srv.shutdown()
    srv.server_close()


def test_status_and_analyze_work_without_llm(unavailable_server, capsys):
    srv, logs = unavailable_server
    status, raw, st = _req(srv, 'GET', '/api/assistant/status')
    assert status == 200 and st['available'] is False and 'rejected the API key' in st['reason']
    assert st['model'] == 'gpt-6-sol' and KEY.encode() not in raw

    status, raw, a = _req(srv, 'POST', '/api/analyze', {'circuit_name': DEMO})
    assert status == 200 and a['llm_available'] is False
    assert a['intent']['source'] == 'deterministic'
    assert {f['check'] for f in a['findings']} >= {'missing_pin', 'carry_out_unread', 'carry_break'}
    assert all('certainty' in f for f in a['findings'])
    assert 'predictions' not in a and 'evidence' not in a

    status, raw, r = _req(srv, 'POST', '/api/assistant/report', {'circuit_name': DEMO})
    assert status == 503 and r['error_code'] == 'ASSISTANT_UNAVAILABLE' and 'Assistant unavailable' in r['reason']
    status, raw2, c = _req(srv, 'POST', '/api/assistant/chat', {'circuit_name': DEMO, 'message': 'hi'})
    assert status == 503 and c['error_code'] == 'ASSISTANT_UNAVAILABLE'

    out = capsys.readouterr()
    for blob in (raw, raw2):
        assert KEY.encode() not in blob
    assert KEY not in out.out + out.err + '\n'.join(logs)


REPORT = {'summary': 'Carry link broken at [G23] ([F001]).', 'health': 'errors', 'items': [
    {'title': 'Carry input unconnected', 'severity': 'error', 'certainty': 'fact',
     'what': 'CI of [G23] is unconnected', 'where': 'adder_1 bit 3', 'why_it_matters': 'sum bits 3..7 wrong',
     'fix': 'connect [G24] CO to [G23] CI', 'verilog_suggestion': 'ADDF_X1M_A9TH U5 (.CI(n5) ...);',
     'finding_ids': ['F001', 'F002', 'F003'], 'gate_ids': [23, 24]}], 'clean_confirmation': ''}
CHAT = {'reply': 'Connect [G24].CO to [G23].CI ([F001]).',
        'highlights': {'gate_ids': [23], 'nets': [], 'finding_ids': ['F001'], 'edges': []}}


def _intent_from_evidence(kw):
    """A schema-conformant intent answer built from the deterministic hypothesis in the payload."""
    hyp = json.loads(kw['input'][0]['content'])['deterministic_hypothesis']
    return {'intended_function': hyp['intended_function'], 'summary_for_layman': 'An adder and a multiplier.',
            'blocks': hyp['blocks'], 'dataflow': hyp['dataflow'], 'expected_connections': hyp['expected_connections'],
            'unchecked_rules': [], 'confidence': 0.8, 'reasoning': 'cone signatures'}


@pytest.fixture()
def fake_server():
    responses = {'circuit_intent': _intent_from_evidence, 'circuit_report': REPORT, 'chat_reply': CHAT}

    def dispatch(kw):
        r = responses[kw['schema_name']]
        return r(kw) if callable(r) else r
    fake = FakeLLM(default=dispatch)
    fake.responses = responses
    srv = _start(fake)
    yield srv, fake
    srv.shutdown()
    srv.server_close()


def test_report_and_chat_routes(fake_server):
    srv, fake = fake_server
    status, _, rep = _req(srv, 'POST', '/api/assistant/report', {'circuit_name': DEMO})
    assert status == 200 and rep['health'] == 'errors' and rep['cached'] is False
    item = rep['items'][0]
    assert item['certainty'] == 'fact' and item['severity'] == 'error'
    assert {'from_gate': 24, 'from_pin': 'CO', 'to_gate': 23, 'to_pin': 'CI'}.items() <= item['suggested_edges'][0].items()
    assert item['verilog_suggestion'].startswith('// Suggestion, not applied')
    status, _, rep2 = _req(srv, 'POST', '/api/assistant/report', {'circuit_name': DEMO})
    report_calls = [c for c in fake.calls if c['schema_name'] == 'circuit_report']
    assert rep2['cached'] is True and len(report_calls) == 1       # cached per (circuit, sha, model)

    status, _, c = _req(srv, 'POST', '/api/assistant/chat', {'circuit_name': DEMO, 'message': 'how do I fix F001?'})
    assert status == 200 and c['session_id'] and c['highlights']['gate_ids'] == [23, 24]   # reply cites G24 too
    assert c['highlights']['suggested_edges']
    status, _, c2 = _req(srv, 'POST', '/api/assistant/chat',
                         {'circuit_name': DEMO, 'message': 'and then?', 'session_id': c['session_id']})
    assert c2['session_id'] == c['session_id']
    history = [m for m in fake.calls[-1]['input'] if isinstance(m, dict) and m.get('role') == 'user']
    assert [m['content'] for m in history] == ['how do I fix F001?', 'and then?']


@pytest.mark.parametrize('body, status, code', [
    ({'circuit_name': DEMO, 'message': ''}, 400, 'INVALID_MESSAGE'),
    ({'circuit_name': DEMO, 'message': 'x' * 2001}, 413, 'MESSAGE_TOO_LONG'),
    ({'circuit_name': DEMO, 'message': 'hi', 'session_id': 'x' * 65}, 400, 'INVALID_SESSION'),
    ({'circuit_name': '../.env', 'message': 'hi'}, 400, 'INVALID_CIRCUIT_NAME'),
    ({'upload_id': '../../.env', 'message': 'hi'}, 400, 'INVALID_UPLOAD_ID'),
])
def test_chat_validation(fake_server, body, status, code):
    srv, _ = fake_server
    st, _, r = _req(srv, 'POST', '/api/assistant/chat', body)
    assert st == status and r['error_code'] == code


@pytest.mark.parametrize('path', ['/api/analyze', '/api/assistant/report'])
def test_new_routes_reject_traversal(fake_server, path):
    srv, _ = fake_server
    st, _, r = _req(srv, 'POST', path, {'circuit_name': '..\\..\\.env'})
    assert st == 400 and r['error_code'] == 'INVALID_CIRCUIT_NAME'


def test_llm_error_during_report_is_502_without_key(fake_server):
    from llm_client import LLMError
    srv, fake = fake_server
    fake.responses['circuit_report'] = LLMError('OpenAI rejected the request: <redacted>', kind='bad_request')
    st, raw, r = _req(srv, 'POST', '/api/assistant/report', {'circuit_name': DEMO, 'regenerate': True})
    assert st == 502 and r['error_code'] == 'ASSISTANT_ERROR' and KEY.encode() not in raw
