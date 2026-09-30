"""Phase B: grounding, intent, report, chat tools/sessions, LLM client failure modes, key safety.
The LLM is always mocked: nothing here touches the network."""
import json
import os
import re
import threading

import pytest

import assistant as asst
import intent_analyzer as ia
from analysis_service import AnalysisService
from circuit_checks import run_checks
from circuit_store import DATASET_DIR, DEMO_DIR, resolve_circuit
from fake_llm import FakeLLM, make_client, openai_error, sdk_response
from grounding import Grounder
from llm_client import LLMClient, LLMConfig, LLMError
from netlist_graph_engine import build_circuit_model

DEMO_MISWIRE = 'Demo_miswire_bits__Test_add_mul_16_bit_Syn_65nm.v'
DEMO_CARRY = 'Demo_cut_carry__Validate_add_mul_8_bit_Syn_65nm.v'
CLEAN = 'Validate_add_mul_8_bit_Syn_65nm.v'


def _baseline(model):
    return [2] * model['num_gates']


def _service(llm):
    return AnalysisService(llm, _baseline)


# ---------------------------------------------------------------------------
# Strict schemas must satisfy OpenAI strict mode
# ---------------------------------------------------------------------------

def _assert_strict(schema, path='$'):
    t = schema.get('type')
    types = t if isinstance(t, list) else [t]
    if 'object' in types:
        props = schema.get('properties', {})
        assert schema.get('additionalProperties') is False, f'{path}: additionalProperties must be false'
        assert sorted(schema.get('required', [])) == sorted(props), f'{path}: every property must be required'
        for k, v in props.items():
            _assert_strict(v, f'{path}.{k}')
    if 'array' in types:
        _assert_strict(schema['items'], path + '[]')


@pytest.mark.parametrize('schema', [ia.INTENT_SCHEMA, asst.REPORT_SCHEMA, asst.CHAT_SCHEMA,
                                    LLMClient.PROBE_SCHEMA, LLMClient.PROBE_TOOL['parameters']]
                         + [t['parameters'] for t in asst.TOOLS])
def test_schemas_are_strict_compatible(schema):
    _assert_strict(schema)


def test_tools_are_strict_functions():
    for t in asst.TOOLS:
        assert t['type'] == 'function' and t['strict'] is True and t['description']


# ---------------------------------------------------------------------------
# Grounding
# ---------------------------------------------------------------------------

@pytest.fixture(scope='module')
def miswire():
    ref = resolve_circuit(DEMO_MISWIRE)
    return ref, build_circuit_model(ref.path)


def test_grounder_removes_fake_refs(miswire):
    _, model = miswire
    findings = [{'id': 'F001'}]
    g = Grounder(model, findings)
    text = 'Real [G45] [N:b[1]] [F001] [B:Result_add]; fake [G99999] [N:nope] [F999] [B:NotABus].'
    out = g.clean_text(text, 'test')
    assert '[G45]' in out and '[N:b[1]]' in out and '[F001]' in out and '[B:Result_add]' in out
    for fake in ('[G99999]', '[N:nope]', '[F999]', '[B:NotABus]'):
        assert fake not in out
    assert out.count('[unverified]') == 4
    assert {d['ref'] for d in g.dropped} == {'[G99999]', '[N:nope]', '[F999]', '[B:NotABus]'}
    assert g.gates([45, 99999, -1, True], 'x') == [45]
    assert g.suggested_edges([{'from_gate': 1, 'to_gate': 99999, 'to_pin': 'A'},
                              {'from_net': 'b[1]', 'to_gate': 45, 'to_pin': 'A'},
                              {'from_net': 'b[1]', 'to_gate': 45, 'to_pin': 'NOPIN'}], 'x') == \
        [{'from_net': 'b[1]', 'to_gate': 45, 'to_pin': 'A'}]


def _report_with(raw, name=DEMO_MISWIRE):
    fake = FakeLLM(script=[raw])
    svc = _service(FakeLLM(available=False))       # deterministic intent, report LLM separate
    a = asst.Assistant(fake, svc)
    return a.generate_report(resolve_circuit(name)), fake


def test_report_drops_hallucinated_refs_and_invented_items():
    raw = {'summary': 'Adder bit issue at [G45] and [G99999] on [N:nope] ([F001], [F999]) in [B:Fake].',
           'health': 'ok',
           'items': [
               {'title': 'Swapped bits', 'severity': 'info', 'certainty': 'fact', 'what': 'see [G45] [G77777]',
                'where': '[B:Result_add]', 'why_it_matters': 'x', 'fix': 'reconnect [N:b[1]] not [N:ghost]',
                'verilog_suggestion': 'U68 (.A(b[1]));', 'finding_ids': ['F001', 'F999'], 'gate_ids': [45, 123456]},
               {'title': 'Invented problem', 'severity': 'error', 'certainty': 'fact', 'what': 'made up',
                'where': '', 'why_it_matters': '', 'fix': '', 'verilog_suggestion': None,
                'finding_ids': ['F777'], 'gate_ids': [1]}],
           'clean_confirmation': ''}
    rep, _ = _report_with(raw)
    dropped = {d['ref'] for d in rep['dropped_refs']}
    assert {'[G99999]', '[N:nope]', '[F999]', '[B:Fake]', '[G77777]', '[N:ghost]', 'F999', 'F777', 'G123456'} <= dropped
    assert any('Invented problem' in d for d in dropped)
    assert len(rep['items']) == 1
    item = rep['items'][0]
    # server-enforced fields: health, severity, certainty from the real finding (F001 = structural warning)
    assert rep['health'] == 'warnings' and rep['llm_health'] == 'ok'
    assert item['severity'] == 'warning' and item['certainty'] == 'likely'
    assert item['finding_ids'] == ['F001'] and item['gate_ids'] == [45]
    assert item['verilog_suggestion'].startswith('// Suggestion, not applied')
    for e in item['suggested_edges']:                       # only edges backed by F001, all valid
        assert e.get('to_gate') is not None and e['to_gate'] < 863
    assert '99999' not in json.dumps(rep['items']) and 'ghost' not in json.dumps(rep['items'])


def test_clean_report_is_ok_and_invents_nothing():
    raw = {'summary': 'An 8-bit adder feeding an 8x8 multiplier behind an output select; no problems found.',
           'health': 'ok', 'items': [], 'clean_confirmation': ''}
    rep, fake = _report_with(raw, CLEAN)
    assert rep['health'] == 'ok' and rep['items'] == []
    assert rep['clean_confirmation'].startswith('No connection problems found')
    assert 'floating_net' in rep['clean_confirmation']
    ctx = json.loads(fake.calls[0]['input'][0]['content'])
    assert ctx['health'] == 'ok' and ctx['counts']['errors'] == 0 and ctx['findings'] == []
    assert ctx['checks_passed'] and ctx['intent']['intended_function']


def test_findings_flow_into_report_context():
    raw = {'summary': 's', 'health': 'errors', 'items': [], 'clean_confirmation': ''}
    rep, fake = _report_with(raw, DEMO_CARRY)
    ctx = json.loads(fake.calls[0]['input'][0]['content'])
    checks = {f['check'] for f in ctx['findings']}
    assert {'missing_pin', 'carry_out_unread', 'carry_break'} <= checks
    f001 = next(f for f in ctx['findings'] if f['id'] == 'F001')
    assert f001['certainty'] == 'fact' and f001['suggested_edges']
    assert rep['health'] == 'errors'


# ---------------------------------------------------------------------------
# What the LLM is allowed to see
# ---------------------------------------------------------------------------

def test_llm_payload_has_no_file_names_headers_or_netlist_text():
    ref = resolve_circuit(DEMO_MISWIRE)
    with open(ref.path, encoding='utf-8') as f:
        raw_text = f.read()
    header_lines = [l[2:].strip() for l in raw_text.splitlines() if l.startswith('//') and len(l) > 20]
    intent = {'intended_function': 'x', 'summary_for_layman': 'x', 'blocks': [], 'dataflow': [],
              'expected_connections': [], 'unchecked_rules': [], 'confidence': 0.5, 'reasoning': 'x'}
    report = {'summary': 's', 'health': 'warnings', 'items': [], 'clean_confirmation': ''}
    answer = {'reply': 'ok', 'highlights': {'gate_ids': [], 'nets': [], 'finding_ids': [], 'edges': []}}
    fake = FakeLLM(script=[intent, report, [('get_gate', {'gate_id': 45})], answer])
    svc = _service(fake)
    a = asst.Assistant(fake, svc)
    a.generate_report(ref)
    a.chat(None, ref, 'what is wrong?')
    payload = fake.payload_text()
    assert len(fake.calls) == 4
    for forbidden in ['Demo_', 'demo_faults', 'miswire', 'Swapped operand', 'fault_injector', 'DEMO FAULT',
                      '_Syn_65nm', 'Test_add_mul', 'endmodule', '.A(', 'wire ', 'input [0:15]']:
        assert forbidden not in payload, forbidden
    for line in header_lines:
        assert line[:40] not in payload
    assert 'add_mul_16_bit' in payload                  # the original module name is allowed
    assert 'circuit under analysis' in payload


# ---------------------------------------------------------------------------
# Intent
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('name, expect', [
    ('Validate_add_mul_8_bit_Syn_65nm.v', ['8-bit adder', '8x8 multiplier', 'select']),
    ('Train_add_mul_comp_sub_4_bit_Syn_65nm.v', ['subtractor', 'comparator', 'adder', 'multiplier']),
    ('Validate_add_mul_mix_8_bit_Syn_65nm.v', ['multiplier', 'adder']),
])
def test_deterministic_intent_on_benchmarks(name, expect):
    ref = resolve_circuit(name)
    res = _service(FakeLLM(available=False)).analyze(ref)
    it = res['intent']
    assert it['source'] == 'deterministic' and 0 < it['confidence'] <= 0.6
    for word in expect:
        assert word in it['intended_function'].lower(), it['intended_function']
    assert all(t['status'] in ('pass', 'not_checkable') for t in it['template_results'])
    if 'mix' in name:
        assert {(d['from_block'], d['to_block']) for d in it['dataflow']} >= {('adder_1', 'multiplier_1'),
                                                                                ('adder_2', 'multiplier_1')}


def test_llm_intent_invalid_templates_and_names_are_dropped(miswire):
    ref, model = miswire
    raw = {'intended_function': '16-bit adder feeding a 16x16 multiplier with output select',
           'summary_for_layman': 'Adds and multiplies [B:Result_add] [B:Bogus].',
           'blocks': [{'name': 'adder_1', 'role': 'adder', 'width': 16, 'input_buses': ['a', 'b', 'zz'],
                       'output_buses': ['Result_add'], 'hier_prefixes': ['adder_1', 'ghost_9'], 'evidence': 'x'}],
           'dataflow': [{'from_block': 'adder_1', 'to_block': 'nope', 'via_bus': 'Result_add'}],
           'expected_connections': [
               {'template': 'adder_triangular', 'params': {'out_bus': 'Result_add', 'in_buses': ['a', 'b'],
                                                           'block_prefix': None, 'minuend': None, 'subtrahend': None}},
               {'template': 'adder_triangular', 'params': {'out_bus': 'NoSuchBus', 'in_buses': ['a'],
                                                           'block_prefix': None, 'minuend': None, 'subtrahend': None}},
               {'template': 'carry_chain', 'params': {'out_bus': None, 'in_buses': [], 'block_prefix': 'not_a_block',
                                                      'minuend': None, 'subtrahend': None}},
               {'template': 'subtractor_inverted', 'params': {'out_bus': 'Result_add', 'in_buses': [],
                                                              'block_prefix': None, 'minuend': 'a', 'subtrahend': 'q'}}],
           'unchecked_rules': ['the select picks the adder when operation=0'], 'confidence': 0.99,
           'reasoning': 'cones [G45] [G99999]'}
    fake = FakeLLM(script=[raw])
    res = _service(fake).analyze(ref)
    it = res['intent']
    assert it['source'] == 'llm' and it['confidence'] == 0.95            # capped
    assert [t['params']['out_bus'] for t in it['expected_connections']] == ['Result_add']
    reasons = ' '.join(d['reason'] for d in it['dropped_templates'])
    assert 'NoSuchBus' in reasons and 'not_a_block' in reasons and 'subtrahend' in reasons
    dropped = {d['ref'] for d in it['dropped_refs']}
    assert {'B:zz', 'prefix:ghost_9', '[B:Bogus]', '[G99999]'} <= dropped
    assert it['blocks'][0]['input_buses'] == ['a', 'b'] and it['blocks'][0]['hier_prefixes'] == ['adder_1']
    assert it['dataflow'] == []
    # the valid template ran and links the existing structural finding
    tr = it['template_results'][0]
    assert tr['template'] == 'adder_triangular' and tr['status'] == 'fail' and tr['finding_ids'] == ['F001']


def test_llm_failure_falls_back_to_deterministic_intent(miswire):
    ref, _ = miswire
    fake = FakeLLM(script=[LLMError('The model refused: nope', kind='refusal')])
    it = _service(fake).analyze(ref)['intent']
    assert it['source'] == 'deterministic' and 'refused' in it['llm_error']


def test_obfuscated_names_cap_confidence():
    text = open(os.path.join(DATASET_DIR, CLEAN), encoding='utf-8').read()
    mapping = {}
    # rename every escaped (hierarchical) identifier consistently, e.g. \adder_1/intadd_0/U5 -> \z17
    text = re.sub(r'\\\S+', lambda m: mapping.setdefault(m.group(0), f'\\z{len(mapping)}'), text)
    text = text.replace('Result_add', 'w_q').replace('Result_mul', 'w_r').replace('module add_mul_8_bit', 'module top')
    model = build_circuit_model(text=text)
    ev = ia.collect_evidence(model, run_checks(model), None, None, 'upload', [])
    assert ev['names_look_obfuscated']
    det = ia.deterministic_intent(ev)
    assert det['confidence'] <= 0.35 and 'structural guess' in det['summary_for_layman']
    raw = dict(det, confidence=0.9, reasoning='x', unchecked_rules=[])
    raw = {k: raw[k] for k in ia.INTENT_SCHEMA['required']}
    assert ia._validate_intent(raw, model, ev)['confidence'] == 0.4


# ---------------------------------------------------------------------------
# Chat: tools, limits, sessions
# ---------------------------------------------------------------------------

ANSWER = {'reply': 'Fix it by reconnecting [G45] ([F001]). Fake [G424242].',
          'highlights': {'gate_ids': [45, 999999], 'nets': ['b[1]', 'nonet'], 'finding_ids': ['F001', 'F404'],
                         'edges': [{'from_gate': 0, 'to_gate': 1}, {'from_gate': 45, 'to_gate': 99999}]}}


def _chat_assistant(script):
    fake = FakeLLM(script=script)
    svc = _service(FakeLLM(available=False))
    return asst.Assistant(fake, svc), fake


def test_chat_highlights_are_validated():
    a, _ = _chat_assistant([ANSWER])
    r = a.chat(None, resolve_circuit(DEMO_MISWIRE), 'how do I fix F001?')
    h = r['highlights']
    assert h['gate_ids'] == [45] and h['nets'] == ['b[1]'] and h['finding_ids'] == ['F001']
    assert all(e['to_gate'] != 99999 for e in h['edges'])
    assert h['suggested_edges'] and all(e['to_gate'] in (45, 77) for e in h['suggested_edges'])
    assert '[G424242]' not in r['reply'] and '[unverified]' in r['reply']
    dropped = {d['ref'] for d in r['dropped_refs']}
    assert {'[G424242]', 'G999999', 'N:nonet', 'F404'} <= dropped
    assert 'b[1]' in r['ref_gates']['nets']


def test_tool_loop_stops_at_six_calls_and_truncates():
    calls = [('list_findings', {'category': None, 'severity': None}), ('get_neighborhood', {'gate_id': 45, 'hops': 2, 'max_nodes': 50})]
    a, fake = _chat_assistant([calls, calls, calls, calls, ANSWER])
    r = a.chat(None, resolve_circuit(DEMO_MISWIRE), 'show me everything')
    executed = [t for t in r['tool_trace'] if t['ok']]
    assert len(executed) == 6 and len(r['tool_trace']) == 8
    assert all(t['output_chars'] <= asst.TOOL_OUTPUT_CHARS for t in r['tool_trace'])
    assert fake.calls[-1]['tool_choice'] == 'none'
    outputs = [i for i in fake.calls[-1]['input'] if isinstance(i, dict) and i.get('type') == 'function_call_output']
    assert any('tool call limit' in o['output'] for o in outputs)


def test_tools_reject_invalid_ids(miswire):
    ref, model = miswire
    analysis = _service(FakeLLM(available=False)).analyze(ref)
    t = asst.CircuitTools(model, analysis)
    for name, args in [('get_gate', {'gate_id': 10**6}), ('get_gate', {'gate_id': -1}),
                       ('get_neighborhood', {'gate_id': 10**6, 'hops': 2, 'max_nodes': None}),
                       ('get_net', {'name': 'nope'}), ('trace_path', {'from_id': 0, 'to_id': 10**6, 'max_nodes': None}),
                       ('get_block', {'name': 'nope'}), ('get_bus', {'name': 'nope'}),
                       ('explain_finding', {'finding_id': 'F999'}), ('no_such_tool', {}),
                       ('get_gate', {'wrong_arg': 1})]:
        out = t.call(name, args)
        assert 'error' in out, (name, out)
    assert len(t.call('get_neighborhood', {'gate_id': 45, 'hops': 5, 'max_nodes': 500})['nodes']) <= 50
    path = t.call('trace_path', {'from_id': 45, 'to_id': 77, 'max_nodes': None})
    assert 'error' in path or path['length'] >= 2
    big = asst._truncate({'x': 'y' * 10000})
    assert len(big) <= asst.TOOL_OUTPUT_CHARS and big.endswith('[truncated to 4000 characters]')


def test_session_ttl_and_lru():
    now = [1000.0]
    store = asst.SessionStore(max_sessions=3, ttl=60, max_turns=2, clock=lambda: now[0])
    s1 = store.get(None, 'c1')
    store.add_turn(s1, 'q1', 'a1')
    store.add_turn(s1, 'q2', 'a2')
    store.add_turn(s1, 'q3', 'a3')
    assert [t[0] for t in s1['turns']] == ['q2', 'q3']                 # last N turns kept
    assert store.get(s1['id'], 'c1') is s1
    assert store.get(s1['id'], 'other-circuit')['turns'] == []         # new circuit -> fresh history
    ids = [store.get(None, 'c')['id'] for _ in range(4)]
    assert len(store) == 3 and s1['id'] not in [k for k in store._s]   # LRU evicted the oldest
    now[0] += 61
    fresh = store.get(ids[-1], 'c')
    assert fresh['id'] != ids[-1] and len(store) == 1                  # TTL expired everything


def test_concurrent_chats_are_thread_safe():
    fake = FakeLLM(default=ANSWER)
    a = asst.Assistant(fake, _service(FakeLLM(available=False)))
    ref = resolve_circuit(DEMO_MISWIRE)
    a.service.analyze(ref)
    errors, results = [], []

    def worker(i):
        try:
            results.append(a.chat('shared-session' if i % 2 else None, ref, f'q{i}'))
        except Exception as exc:   # pragma: no cover
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(24)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert not errors and len(results) == 24
    assert len(a.sessions) <= asst.MAX_SESSIONS
    for s in a.sessions._s.values():
        assert len(s['turns']) <= asst.MAX_TURNS


# ---------------------------------------------------------------------------
# LLM client: request shape, failure modes, key safety
# ---------------------------------------------------------------------------

KEY = 'sk-test-SECRETKEY-abcdef0123456789'


def test_probe_success_and_request_shape():
    call = {'call_id': 'c1', 'name': 'add_numbers', 'arguments': {'a': 2, 'b': 3}}
    client, logs = make_client([sdk_response(calls=[call]), sdk_response(text='{"sum": 5}')])
    assert client.probe() and client.status()['available']
    first = client._sdk.calls[0]
    assert first['text']['format'] == {'type': 'json_schema', 'name': 'probe', 'schema': LLMClient.PROBE_SCHEMA,
                                       'strict': True}
    assert first['tools'][0]['strict'] is True and first['tool_choice'] == 'required'
    assert first['store'] is False and first['include'] == ['reasoning.encrypted_content']
    assert first['reasoning'] == {'effort': 'low'}
    second = client._sdk.calls[1]
    assert {'type': 'function_call_output', 'call_id': 'c1', 'output': '{"result": 5}'} in second['input']
    assert any('cost_usd=' in l and 'latency_ms=' in l for l in logs)


@pytest.mark.parametrize('script, expected, attempts', [
    ([openai_error('auth', KEY)], 'rejected the API key', 1),
    ([openai_error('notfound')], "Model 'gpt-6-sol' was not found", 1),
    ([openai_error('rate'), openai_error('rate')], 'rate limit', 2),
    ([openai_error('quota')], 'no credits remaining', 1),
    ([openai_error('server'), openai_error('server')], 'server error', 2),
    ([openai_error('timeout')], 'timed out after 60 s', 1),
    ([openai_error('connection'), openai_error('connection')], 'Could not connect', 2),
    ([openai_error('bad', KEY)], 'rejected the request', 1),
    ([sdk_response(refusal='I cannot help with that')], 'The model refused', 1),
    ([sdk_response(text='{"sum": 1', status='incomplete', incomplete_reason='max_output_tokens')],
     'incomplete (max_output_tokens)', 1),
    ([sdk_response(calls=[{'call_id': 'c', 'name': 'add_numbers', 'arguments': {'a': 1, 'b': 1}}]),
      sdk_response(text='not json')], 'does not match the required JSON schema', 2),
])
def test_unavailable_paths_give_clear_messages(script, expected, attempts):
    client, logs = make_client(script, key=KEY)
    assert client.probe() is False
    st = client.status()
    assert not st['available'] and expected in st['reason'], st['reason']
    assert len(client._sdk.calls) == attempts
    blob = json.dumps(st) + '\n'.join(logs) + repr(client.config)
    assert KEY not in blob


def test_missing_key_or_model():
    client = LLMClient(config=LLMConfig(api_key='', model='gpt-6-sol'), sdk_client=None, log=lambda *_: None)
    assert client.probe() is False and 'OPENAI_API_KEY is not set' in client.status()['reason']
    client = LLMClient(config=LLMConfig(api_key=KEY, model=''), sdk_client=object(), log=lambda *_: None)
    assert client.probe() is False and 'OPENAI_MODEL is not set' in client.status()['reason']


def test_load_config_reads_env_file(tmp_path, monkeypatch):
    for k in ('OPENAI_API_KEY', 'OPENAI_MODEL', 'OPENAI_REASONING_EFFORT_REPORT', 'OPENAI_REASONING_EFFORT_CHAT'):
        monkeypatch.delenv(k, raising=False)
    env = tmp_path / '.env'
    env.write_text(f'OPENAI_API_KEY={KEY}\nOPENAI_MODEL=gpt-6-luna\nOPENAI_REASONING_EFFORT_REPORT=high\n')
    import llm_client
    cfg = llm_client.load_config(str(env))
    assert cfg.model == 'gpt-6-luna' and cfg.effort_report == 'high' and cfg.effort_chat == 'low'
    assert cfg.prices == llm_client.PRICES['gpt-6-luna']
    assert KEY not in repr(cfg) and KEY not in str(cfg)
