"""Automatic lookups, reference normalisation and the tool additions used by the chat (fake LLM, no network)."""
import json

import pytest

import assistant as asst
from analysis_service import AnalysisService
from circuit_store import resolve_circuit
from fake_llm import FakeLLM

CLEAN = 'Validate_add_mul_8_bit_Syn_65nm.v'
BS = chr(92)
CARRY_NET = BS + 'adder_1/intadd_0/n4'


@pytest.fixture(scope='module')
def circuit():
    svc = AnalysisService(FakeLLM(available=False), lambda m: [2] * m['num_gates'])
    ref = resolve_circuit(CLEAN)
    analysis = svc.analyze(ref)
    model, _ = svc.load(ref)
    return ref, model, analysis, asst.CircuitTools(model, analysis)


@pytest.mark.parametrize('question, expected', [
    ('Hello, introduce yourself.', []),
    ('What does this circuit do?', []),
    ('What is G23?', [('get_gate', {'gate_id': 23})]),
    ('What is gate 7 connected to?', [('get_gate', {'gate_id': 7})]),
    ('What drives Result_add[12]?', [('get_net', {'name': 'Result_add[12]'})]),
    (f'What reads {CARRY_NET}?', [('get_net', {'name': CARRY_NET})]),
    ('Show me the bus Result_mul', [('get_bus', {'name': 'Result_mul'})]),
    ('Trace the path from G25 to G5.', [('trace_path', {'from_id': 25, 'to_id': 5, 'max_nodes': None})]),
    ('What is G999?', [('get_gate', {'gate_id': 999})]),
    ('Why is F001 reported?', [('explain_finding', {'finding_id': 'F001'})]),
    ('Are there suspicious or missing connections?', [('list_findings', {'category': None, 'severity': None})]),
    ('What does GraphSAINT predict for G23?', [('get_gate', {'gate_id': 23}),
                                               ('get_neighborhood', {'gate_id': 23, 'hops': 1, 'max_nodes': 20})]),
    ('What does a do?', []),                           # single-letter bus names need a hint word
])
def test_plan_lookups(circuit, question, expected):
    _, model, _, _ = circuit
    assert asst.plan_lookups(question, model) == expected


def test_follow_ups_reuse_the_named_kind(circuit):
    _, model, _, _ = circuit
    history = [[('get_net', {'name': 'Result_add[12]'})], [('get_gate', {'gate_id': 23})]]
    assert asst.plan_lookups('What gates read this net?', model, history) == [('get_net', {'name': 'Result_add[12]'})]
    assert asst.plan_lookups('Is it an adder?', model, history) == [('get_gate', {'gate_id': 23})]
    assert asst.plan_lookups('What does GraphSAINT predict about this region?', model, history) == [
        ('get_gate', {'gate_id': 23}), ('get_neighborhood', {'gate_id': 23, 'hops': 1, 'max_nodes': 20})]
    assert asst.plan_lookups('Are there any issues?', model, history) == [
        ('list_findings', {'category': None, 'severity': None})]   # "there" is not a follow-up
    assert asst.plan_lookups('What is this?', model, []) == []


def test_lookups_are_capped(circuit):
    _, model, _, _ = circuit
    assert len(asst.plan_lookups('Compare G1, G2, G3, G4 and F001 and F002', model)) == asst.MAX_AUTO_LOOKUPS


def test_normalize_refs(circuit):
    _, model, _, _ = circuit
    text = 'See [G:23], [Gate 5], [F:F001], [F1], [N:Result_add], [B:a[4]], [G:control_Result], [N:a[4]] and [G999].'
    assert asst.normalize_refs(text, model) == (
        'See [G23], [G5], [F001], [F001], [B:Result_add], [N:a[4]], control_Result, [N:a[4]] and [G999].')


def test_get_gate_reports_pin_level_connectivity(circuit):
    _, _, _, tools = circuit
    g = tools.call('get_gate', {'gate_id': 23})
    pins = {p['pin']: p for p in g['pins']}
    assert pins['CI']['driven_by'] == ['G24 pin CO'] and pins['A']['driven_by'] == ['primary input b[4]']
    assert pins['CO']['read_by'] == ['G22 pin CI'] and pins['S']['read_by'] == ['G5 pin A']
    assert g['fan_in_gates'] == [24] and g['fan_out_gates'] == [5, 22]
    assert g['predicted_class'] and g['name_heuristic_label'] == 'Adder'


def test_get_net_accepts_bus_names_and_backslash_variants(circuit):
    _, _, _, tools = circuit
    assert tools.call('get_net', {'name': CARRY_NET[1:]})['name'] == CARRY_NET
    assert tools.call('get_net', {'name': ' Result_add[12] '})['name'] == 'Result_add[12]'
    bus = tools.call('get_net', {'name': 'Result_add'})
    assert bus['width'] == 16 and 'is a bus' in bus['note']
    assert 'error' in tools.call('get_net', {'name': 'no_such_net'})


def test_gate_briefs_carry_predictions(circuit):
    _, _, _, tools = circuit
    path = tools.call('trace_path', {'from_id': 25, 'to_id': 5, 'max_nodes': None})
    assert [p['id'] for p in path['path']] == [25, 24, 23, 5]
    assert all('predicted_class' in p for p in path['path'])


def test_tool_summaries_state_facts_in_plain_words(circuit):
    _, _, _, tools = circuit
    s = tools.call('get_gate', {'gate_id': 23})['summary'].splitlines()
    assert s[0].startswith('G23: instance adder_1/intadd_0/U5, cell type ADDF_X1M_A9TH, block adder_1/intadd_0.')
    assert f'- input pin CI: G24 pin CO -> G23 pin CI (net {BS}adder_1/intadd_0/n5)' in s
    assert f'- output pin CO: G23 pin CO -> G22 pin CI (net {BS}adder_1/intadd_0/n4)' in s
    assert '- output pin S: G23 pin S -> G5 pin A (net Result_add[12])' in s
    assert '- fan-in (gates that feed G23): G24' in s and '- fan-out (gates that G23 feeds): G5, G22' in s
    assert any('instance-name label: Adder' in l and 'disagrees with the label' in l for l in s)
    assert tools.call('get_net', {'name': 'Result_add[12]'})['summary'].splitlines()[1:] == [
        '- G23 pin S -> G5 pin A',
        '- driver: G23 pin S (instance adder_1/intadd_0/U5, cell ADDF_X1M_A9TH, block adder_1/intadd_0)',
        '- reader: G5 pin A (instance U22, cell MX2_X0P5M_A9TH, block top)',
        '- bit of bus Result_add, significance 3 (0 = least significant)']
    fwd = tools.call('trace_path', {'from_id': 25, 'to_id': 5, 'max_nodes': None})['summary']
    back = tools.call('trace_path', {'from_id': 5, 'to_id': 25, 'max_nodes': None})['summary']
    assert 'G25 -> G24 -> G23 -> G5' in fwd and 'other way' not in fwd
    assert 'G25 -> G24 -> G23 -> G5' in back and 'No path from G5 to G25' in back
    hood = tools.call('get_neighborhood', {'gate_id': 23, 'hops': 1, 'max_nodes': 20})['summary']
    assert '- G23 (center): ' in hood and 'a prediction, not a fact' in hood
    assert 'not wiring faults' in tools.call('list_findings', {'category': None, 'severity': None})['summary']


def test_report_fix_states_the_suggested_edge_not_the_llm_wording():
    svc = AnalysisService(FakeLLM(available=False), lambda m: [2] * m['num_gates'])
    raw = {'summary': 'Carry input missing at [G23].', 'health': 'errors', 'clean_confirmation': '',
           'items': [{'title': 'Missing pin', 'severity': 'error', 'certainty': 'fact', 'what': 'CI unconnected',
                      'where': '[G23]', 'why_it_matters': 'x',
                      'fix': 'Reconnect it through [N:ghost].\n// Suggestion, not applied\n// Connect CI to Result_add[12]',
                      'verilog_suggestion': None, 'finding_ids': ['F001'], 'gate_ids': [23]}]}
    a = asst.Assistant(FakeLLM(script=[raw]), svc)
    rep = a.generate_report(resolve_circuit('Demo_cut_carry__Validate_add_mul_8_bit_Syn_65nm.v'))
    assert rep['items'][0]['fix'] == ('Repair computed by the connectivity checks (a suggestion; not applied '
                                       'automatically): connect G24 pin CO to G23 pin CI.')
    assert '[N:ghost]' in {d['ref'] for d in rep['dropped_refs']}          # the LLM wording is still audited


def test_chat_uses_auto_lookups_and_drops_irrelevant_findings(circuit):
    ref, _, _, _ = circuit
    answer = {'reply': 'G23 is [G:23]; its S output feeds [G5].',
              'highlights': {'gate_ids': [23, 5, 5], 'nets': [], 'finding_ids': ['F001'],
                             'edges': [{'from_gate': 23, 'to_gate': 5}, {'from_gate': 23, 'to_gate': 5}]}}
    fake = FakeLLM(script=[answer])
    a = asst.Assistant(fake, AnalysisService(FakeLLM(available=False), lambda m: [2] * m['num_gates']))
    r = a.chat(None, ref, 'What is G23 connected to?')
    assert r['tool_trace'] == [{'tool': 'get_gate', 'arguments': {'gate_id': 23}, 'ok': True,
                                'output_chars': r['tool_trace'][0]['output_chars'], 'auto': True}]
    items = fake.calls[0]['input']
    assert items[-2]['type'] == 'function_call' and items[-2]['name'] == 'get_gate'
    assert json.loads(items[-1]['output'])['id'] == 23
    assert r['reply'] == '[G23] is [G23]; its S output feeds [G5].'          # plain valid ids become refs
    assert r['highlights']['finding_ids'] == []                       # F001 is not about G23
    assert r['highlights']['gate_ids'] == [23, 5]
    assert r['highlights']['edges'] == [{'from_gate': 23, 'to_gate': 5}]   # duplicates removed
    # the follow-up reuses the gate looked up in the previous turn
    fake.script.append({'reply': 'It is an adder cell.', 'highlights': answer['highlights']})
    r2 = a.chat(r['session_id'], ref, 'Is it an adder?')
    assert r2['highlights']['gate_ids'][0] == 23                    # the looked-up gate is always highlighted
    assert [(t['tool'], t['arguments']) for t in r2['tool_trace']] == [('get_gate', {'gate_id': 23})]


def test_chat_context_has_predictions_and_buses(circuit):
    ref, _, _, _ = circuit
    fake = FakeLLM(script=[{'reply': 'Hi.', 'highlights': {'gate_ids': [], 'nets': [], 'finding_ids': [], 'edges': []}}])
    a = asst.Assistant(fake, AnalysisService(FakeLLM(available=False), lambda m: [2] * m['num_gates']))
    a.chat(None, ref, 'Hello')
    ctx = json.loads(fake.calls[0]['instructions'].split('\nContext:\n', 1)[1])
    assert ctx['predictions']['source'] and ctx['predictions']['counts']
    assert {b['name'] for b in ctx['buses']} >= {'a', 'b', 'Result', 'Result_add', 'Result_mul'}
    assert ctx['circuit']['gate_ids'] == 'G0..G238'
