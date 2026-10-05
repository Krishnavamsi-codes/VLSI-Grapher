"""Design Copilot: structure, structural timing/power/area, optimization candidates, GraphSAINT regions, focus /
follow-up context and the PPA grounding checks. The LLM is always faked: nothing here touches the network."""
import json
import re

import pytest

import assistant as asst
import circuit_checks as cc
import circuit_store
import design_insights as di
from analysis_service import AnalysisService
from circuit_store import resolve_circuit
from fake_llm import FakeLLM

CLEAN = 'Validate_add_mul_8_bit_Syn_65nm.v'
DEMO_CARRY = 'Demo_cut_carry__Validate_add_mul_8_bit_Syn_65nm.v'
EMPTY_HL = {'gate_ids': [], 'nets': [], 'finding_ids': [], 'edges': []}

# 7 gates: U1/U2 are duplicate NAND2s, U4->U5 and U6->U7 are inverter pairs, U6/U7 never reach an output
SYNTH = """module dup (a, b, y1, y2);
  input a, b;
  output y1, y2;
  wire n1, n2, n3, n4, n5;
  NAND2_X1M_A9TH U1 (.A(a), .B(b), .Y(n1));
  NAND2_X0P5M_A9TH U2 (.A(a), .B(b), .Y(n2));
  INV_X0P6M_A9TH U3 (.A(n1), .Y(y1));
  INV_X0P6M_A9TH U4 (.A(n2), .Y(n3));
  INV_X0P6M_A9TH U5 (.A(n3), .Y(y2));
  INV_X0P6M_A9TH U6 (.A(a), .Y(n4));
  INV_X0P6M_A9TH U7 (.A(n4), .Y(n5));
endmodule
"""


def _service():
    return AnalysisService(FakeLLM(available=False), lambda m: [2] * m['num_gates'])


@pytest.fixture(scope='module')
def clean():
    svc = _service()
    ref = resolve_circuit(CLEAN)
    a = svc.analyze(ref)
    model, _ = svc.load(ref)
    ins = svc.insights(ref, a)
    return svc, ref, model, a, ins, asst.CircuitTools(model, a, ins)


@pytest.fixture(scope='module')
def carry():
    svc = _service()
    ref = resolve_circuit(DEMO_CARRY)
    a = svc.analyze(ref)
    model, _ = svc.load(ref)
    ins = svc.insights(ref, a)
    return svc, ref, model, a, ins, asst.CircuitTools(model, a, ins)


@pytest.fixture(scope='module')
def synth():
    svc = _service()
    ref = resolve_circuit(upload_id=circuit_store.save_upload(SYNTH))
    a = svc.analyze(ref)
    return svc, ref, a, svc.insights(ref, a)


def _chat(svc, script):
    fake = FakeLLM(script=script)
    return asst.Assistant(fake, svc), fake


def _reply(text, gates=()):
    return {'reply': text, 'highlights': dict(EMPTY_HL, gate_ids=list(gates))}


# ---------------------------------------------------------------------------
# 1. Circuit understanding
# ---------------------------------------------------------------------------

def test_overview_is_grounded_in_the_netlist(clean):
    _, _, model, a, ins, tools = clean
    out = tools.call('circuit_overview', {})
    s = out['summary']
    assert s.startswith('In simple terms: This is an add-or-multiply unit.')
    assert 'operation selects which answer reaches Result' in s
    assert 'Inputs: a[8], b[8], operation' in s and 'Outputs: Result[16]' in s
    assert 'operation (drives the select pin of 8 multiplexer cell(s)' in s
    assert 'multiplier_1 213 gates (multiplier)' in s and 'adder_1 10 gates (adder)' in s
    assert 'a, b -> adder_1 (adder-like) -> Result_add -> top (select-like) -> output Result' in s
    assert 'Purely combinational' in s
    # block counts add up and control-signal readers are real select pins
    assert sum(b['gates'] for b in ins.structure['blocks']) == model['num_gates']
    op = ins.structure['control_signals'][0]
    sel = [r for r in model['nets']['operation']['readers'] if r.get('pin') == 'S0']
    assert op['net'] == 'operation' and op['select_pins'] == len(sel) == 8
    assert out['cards'][0]['basis'] == 'deterministic'


@pytest.mark.parametrize('q, tool', [('Explain the main blocks', 'circuit_overview'),
                                     ('What are the control signals?', 'circuit_overview'),
                                     ('What are the major datapaths?', 'circuit_overview'),
                                     ('Explain multiplier_1', 'get_block')])
def test_understanding_questions_plan_structure_lookups(clean, q, tool):
    assert asst.plan_lookups(q, clean[2])[0][0] == tool


def test_chat_context_carries_structure_and_data_availability(clean):
    svc, ref, *_ = clean
    a, fake = _chat(svc, [_reply('It is an adder and multiplier with a select.')])
    a.chat(None, ref, 'What does this circuit do?')
    ctx = json.loads(fake.calls[0]['instructions'].split('\nContext:\n', 1)[1])
    assert 'Control signals: operation' in ctx['structure']
    assert 'No timing, power or area data' in ctx['data_availability']
    assert 'never give a percentage' in fake.calls[0]['instructions']


def test_get_block_has_a_code_written_summary(clean):
    out = clean[5].call('get_block', {'name': 'multiplier_1'})
    assert out['summary'].startswith('Block multiplier_1: 213 gates')
    assert 'predicts (ML, not a fact)' in out['summary']


# ---------------------------------------------------------------------------
# 2./3. Gate and net lookup through UI focus
# ---------------------------------------------------------------------------

def test_gate_focus_answers_explain_this_gate(clean):
    svc, ref, *_ = clean
    a, _ = _chat(svc, [_reply('G5 is a mux.')])
    r = a.chat(None, ref, 'Explain this gate', focus={'kind': 'gate', 'id': 5})
    assert [(t['tool'], t['arguments']) for t in r['tool_trace']] == [('get_gate', {'gate_id': 5})]
    assert r['subject'] == {'kind': 'gate', 'id': 5} and 5 in r['highlights']['gate_ids']


def test_net_focus_answers_drivers_and_readers(clean):
    svc, ref, *_ = clean
    a, _ = _chat(svc, [_reply('operation is a primary input.')])
    r = a.chat(None, ref, 'What drives this net and what reads it?', focus={'kind': 'net', 'id': 'operation'})
    assert r['tool_trace'][0]['tool'] == 'get_net' and r['tool_trace'][0]['arguments'] == {'name': 'operation'}
    assert r['subject'] == {'kind': 'net', 'id': 'operation'}


# ---------------------------------------------------------------------------
# 4. Follow-up context (I)
# ---------------------------------------------------------------------------

def test_follow_ups_keep_the_same_object(clean):
    svc, ref, *_ = clean
    a, fake = _chat(svc, [_reply('G23 is a full adder.'), _reply('G24 drives it.'),
                          _reply('No, G23 is not on a longest path.'), _reply('No candidate targets G23.')])
    sid, seen = None, []
    for q in ('What is G23?', 'What drives it?', 'Is that on a critical path?', 'How could I optimize it?'):
        r = a.chat(sid, ref, q)
        sid = r['session_id']
        seen.append([(t['tool'], t['arguments']) for t in r['tool_trace']])
        assert r['subject'] == {'kind': 'gate', 'id': 23}
    assert seen == [[('get_gate', {'gate_id': 23})], [('get_gate', {'gate_id': 23})],
                    [('timing_analysis', {'gate_id': 23})],
                    [('optimization_suggestions', {'category': None, 'gate_id': 23})]]
    timing_out = json.loads(fake.calls[2]['input'][-1]['output'])
    assert timing_out['gate']['gate_id'] == 23 and timing_out['gate']['on_longest_path'] is False


def test_a_repeated_selection_does_not_override_the_conversation(clean):
    svc, ref, *_ = clean
    a, _ = _chat(svc, [_reply('G5.'), _reply('G23.'), _reply('G24 drives it.')])
    sel = {'kind': 'gate', 'id': 5}
    r = a.chat(None, ref, 'Explain this gate', focus=sel)
    r = a.chat(r['session_id'], ref, 'What is G23?', focus=sel)
    r = a.chat(r['session_id'], ref, 'What drives it?', focus=sel)          # stale selection: "it" = G23
    assert r['tool_trace'][0]['arguments'] == {'gate_id': 23}


# ---------------------------------------------------------------------------
# 5./8. Missing connection and finding explanation
# ---------------------------------------------------------------------------

def test_how_do_i_fix_this_uses_the_computed_repair(carry):
    svc, ref, model, a, *_ = carry
    f001 = next(f for f in a['findings'] if f['id'] == 'F001')
    assert f001['check'] == 'missing_pin'
    asst_, _ = _chat(svc, [_reply('Connect G24 pin CO to G23 pin CI, as the checks suggest.')])
    r = asst_.chat(None, ref, 'How do I fix this?', focus={'kind': 'finding', 'id': 'F001'})
    assert r['tool_trace'][0] == {'tool': 'explain_finding', 'arguments': {'finding_id': 'F001'}, 'ok': True,
                                  'output_chars': r['tool_trace'][0]['output_chars'], 'auto': True}
    edges = r['highlights']['suggested_edges']
    assert edges and edges[0]['from_gate'] == 24 and edges[0]['to_gate'] == 23 and edges[0]['to_pin'] == 'CI'


def test_explain_this_finding_does_not_list_everything(carry):
    plan = asst.plan_lookups('Explain this finding', carry[2], [], ('finding', 'F003'))
    assert plan == [('explain_finding', {'finding_id': 'F003'})]


# ---------------------------------------------------------------------------
# 6. Path tracing / structural timing
# ---------------------------------------------------------------------------

def test_longest_paths_are_real_chains_with_correct_levels(clean):
    *_, model, a, ins, tools = clean
    ctx = cc._Ctx(model)
    t = ins.timing
    for p in t['paths']:
        assert p['levels'] == len(p['gates'])
        assert all(v in ctx.succ[u] for u, v in zip(p['gates'], p['gates'][1:]))
        assert not ctx.pred[p['gates'][0]]                    # starts at a gate fed only by inputs
    assert t['paths'][0]['levels'] == t['max_depth'] == max(ins.level_in)
    assert set(t['paths'][0]['gates']) <= ins.critical
    # every gate on the longest path has the maximal through-length; G23 does not
    assert ins.gate_timing(23)['longest_path_through_gate'] < t['max_depth']
    chain = t['carry_chains'][0]
    for u, v in zip(chain['gates'], chain['gates'][1:]):
        co = model['gate_pins'][u]['CO']
        assert model['gate_pins'][v]['CI'] == co


def test_trace_path_still_works(clean):
    out = clean[5].call('trace_path', {'from_id': 25, 'to_id': 5, 'max_nodes': None})
    assert [p['id'] for p in out['path']] == [25, 24, 23, 5]


# ---------------------------------------------------------------------------
# 7./19. GraphSAINT region explanation: ML prediction vs deterministic fact
# ---------------------------------------------------------------------------

def test_region_separates_ml_prediction_from_netlist_facts(carry):
    svc, ref, model, a, ins, tools = carry
    out = tools.call('explain_region', {'gate_id': 23, 'module': None})
    lines = out['summary'].split('\n')
    assert any(l.startswith('ML PREDICTION (GraphSAINT, not a circuit fact)') for l in lines)
    assert any('F001 (missing_pin, error)' in l and l.startswith('STRUCTURAL FACT') for l in lines)
    assert {c['basis'] for c in out['cards']} == {'ml_prediction', 'deterministic'}
    assert 23 in out['gate_ids'] and out['predicted_class'] == cc.CLASS_NAMES[a['predictions'][23]]
    # module numbering is the one the UI uses (/api/infer -> extract_subcircuit_boundaries)
    assert out['module'] == ins.module_of[23]
    assert 23 in ins.subcircuits[out['module'] - 1]['gate_ids']


def test_region_question_plans_and_chips(carry):
    svc, ref, model, a, ins, _ = carry
    m = ins.module_of[23]
    asst_, _ = _chat(svc, [_reply(f'GraphSAINT predicts [M{m}] is a Multiplier region; [M9999] is not real.')])
    r = asst_.chat(None, ref, f'Why is Module #{m} suspicious?')
    assert r['tool_trace'][0]['arguments'] == {'gate_id': None, 'module': m}
    assert f'[M{m}]' in r['reply'] and '[M9999]' not in r['reply']
    assert str(m) in r['ref_gates']['modules'] and 23 in r['ref_gates']['modules'][str(m)]
    assert any(c['basis'] == 'ml_prediction' for c in r['evidence'])


def test_prediction_stated_as_fact_is_labelled(clean):
    svc, ref, model, a, *_ = clean
    pred = cc.CLASS_NAMES[a['predictions'][23]]
    label = model['nodes'][23]['class_name']
    assert pred != label                                   # GraphSAINT disagrees with the name label here
    wrong = next(c for c in cc.CLASS_NAMES if c not in (pred, label))
    asst_, _ = _chat(svc, [_reply(f'G23 is a {pred}. G23 is a {wrong}. GraphSAINT predicts G23 is a {pred}.')])
    r = asst_.chat(None, ref, 'What is G23?')
    assert f'G23] is a {pred} (GraphSAINT prediction, not a verified fact).' in r['reply']
    assert wrong not in r['reply']
    assert f'GraphSAINT predicts [G23] is a {pred}.' in r['reply']


def test_upload_has_no_graphsaint_capability(synth):
    _, _, a, ins = synth
    caps = ins.capabilities()
    assert a['prediction_source'] == 'baseline' and caps['graphsaint']['supported'] is False
    assert 'baseline' in caps['graphsaint']['note']


# ---------------------------------------------------------------------------
# 9. Invalid ids
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('tool, args', [('timing_analysis', {'gate_id': 99999}),
                                        ('area_analysis', {'block': 'no_such_block'}),
                                        ('explain_region', {'gate_id': None, 'module': 99999}),
                                        ('explain_region', {'gate_id': -1, 'module': None}),
                                        ('optimization_suggestions', {'category': 'speed', 'gate_id': None}),
                                        ('optimization_suggestions', {'category': None, 'gate_id': 99999})])
def test_new_tools_reject_invalid_ids(clean, tool, args):
    assert 'error' in clean[5].call(tool, args)


@pytest.mark.parametrize('focus', [{'kind': 'gate', 'id': 99999}, {'kind': 'gate', 'id': True},
                                   {'kind': 'net', 'id': 'no_such_net'}, {'kind': 'finding', 'id': 'F999'},
                                   {'kind': 'module', 'id': 0}, {'kind': 'bogus', 'id': 1}, 'G5', None])
def test_invalid_focus_is_ignored(clean, focus):
    _, _, model, a, ins, _ = clean
    assert asst.Assistant.validate_focus(focus, model, a, ins) is None


def test_invalid_focus_in_chat_falls_back_to_the_question(clean):
    svc, ref, *_ = clean
    a, _ = _chat(svc, [_reply('Hi.')])
    r = a.chat(None, ref, 'Explain this gate', focus={'kind': 'gate', 'id': 99999})
    assert r['tool_trace'] == [] and r['subject'] is None


# ---------------------------------------------------------------------------
# 10. Uploaded circuit (synthetic, with known redundancy)
# ---------------------------------------------------------------------------

def test_uploaded_circuit_insights_match_known_structure(synth):
    _, _, a, ins = synth
    assert ins.area['duplicate_groups'][0]['gates'] == [0, 1]            # U1 / U2
    assert ins.area['inverter_pairs'] == [[3, 4], [5, 6]]               # U4->U5, U6->U7
    assert ins.area['logic_without_output_path'] == [5, 6]             # U6, U7
    assert ins.max_depth == 3 and ins.timing['paths'][0]['gates'] == [1, 3, 4]
    areas = [o for o in ins.optimizations if o['category'] == 'area']
    dup = next(o for o in areas if 'duplicate' in o['target'])
    assert dup['type'] == 'deterministic' and dup['confidence'] == 'high' and dup['gate_ids'] == [0, 1]
    dead = next(o for o in areas if 'never reach' in o['target'])
    assert dead['gate_ids'] == [5, 6] and dead['type'] == 'deterministic'


def test_uploaded_circuit_chat(synth):
    svc, ref, *_ = synth
    a, _ = _chat(svc, [_reply('Merging [G0] and [G1] could save one gate.')])
    r = a.chat(None, ref, 'Where could I reduce area?')
    assert r['tool_trace'][0]['tool'] == 'optimization_suggestions'
    assert any(c.get('target', '').startswith('duplicate NAND2') for c in r['evidence'])


# ---------------------------------------------------------------------------
# 11.-14. Timing / power / area / optimization questions
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('q, tool', [('What is the critical path?', 'timing_analysis'),
                                     ('Which gates are on the longest path?', 'timing_analysis'),
                                     ('Where are the likely timing bottlenecks?', 'timing_analysis'),
                                     ('Which signals have high fan-out?', 'timing_analysis'),
                                     ('What could increase propagation delay?', 'timing_analysis'),
                                     ('What regions may consume more power?', 'power_analysis'),
                                     ('Where should I investigate switching activity?', 'power_analysis'),
                                     ('Which blocks are largest?', 'area_analysis'),
                                     ('Where is logic most concentrated?', 'area_analysis'),
                                     ('Is there duplicated logic?', 'area_analysis'),
                                     ('How could I improve performance?', 'optimization_suggestions'),
                                     ('What should I investigate for PPA?', 'optimization_suggestions')])
def test_ppa_questions_plan_the_right_tool(clean, q, tool):
    assert asst.plan_lookups(q, clean[2])[0][0] == tool


def test_timing_power_area_summaries_say_structural_only(clean):
    tools = clean[5]
    t = tools.call('timing_analysis', {'gate_id': None})
    p = tools.call('power_analysis', {})
    ar = tools.call('area_analysis', {'block': None})
    assert 'no delay data' in t['summary'] and 'Maximum logic depth: 19 gate levels' in t['summary']
    assert 'no switching activity or power data' in p['summary']
    assert 'Result selects between Result_add, Result_mul' in p['summary']
    assert 'no cell area data' in ar['summary'] and 'block multiplier_1: 213 gates (89%)' in ar['summary']
    for out in (t, p, ar):
        assert 'No timing, power or area data' in out['data_availability']
        assert not re.search(r'\d\s*(ns|ps|MHz|GHz|mW|uW|um2)\b', out['summary'])


def test_optimization_candidates_have_all_fields(clean):
    ins = clean[4]
    assert {o['category'] for o in ins.optimizations} == {'performance', 'power', 'area'}
    for o in ins.optimizations:
        assert all(o[k] for k in ('target', 'reason', 'evidence', 'impact', 'confidence', 'type'))
        assert o['confidence'] in ('high', 'medium', 'low')
        assert o['type'] in ('deterministic', 'structural heuristic')
        assert 'will ' not in o['impact'].lower()
        assert all(0 <= g < ins.n for g in o['gate_ids'])
    lp = ins.optimizations[0]
    assert lp['category'] == 'performance' and lp['gate_ids'] == ins.timing['paths'][0]['gates']


def test_optimization_for_a_gate_on_the_longest_path(clean):
    tools, ins = clean[5], clean[4]
    g = ins.timing['paths'][0]['gates'][3]
    out = tools.call('optimization_suggestions', {'category': None, 'gate_id': g})
    assert out['count'] >= 1 and 'is ON a longest (critical) path' in out['summary']
    off = tools.call('optimization_suggestions', {'category': 'area', 'gate_id': 23})
    assert off['count'] == 0 and off['summary'].startswith('No optimization candidate')


# ---------------------------------------------------------------------------
# 15.-18. Hallucination rejection in chat replies
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('bad, kind', [
    ('G23 drives G100.', 'connection'),
    ('The critical path delay is 2.4 ns, so it runs at 400 MHz.', 'timing'),
    ('The longest path has 42 gate levels.', 'timing'),
    ('The multiplier consumes 3.2 mW of dynamic power.', 'power'),
    ('Operand isolation will reduce power by 35%.', 'power'),
    ('multiplier_1 occupies 1200 um2.', 'area'),
    ('multiplier_1 contains 500 gates.', 'area'),
    ('Merging the gates makes the circuit 2x faster.', 'performance'),
])
def test_hallucinated_claims_are_removed(clean, bad, kind):
    svc, ref, *_ = clean
    good = 'Only structural indicators are available.'
    a, _ = _chat(svc, [_reply(f'{bad} {good}')])
    r = a.chat(None, ref, 'Tell me about timing, power and area.')
    assert r['reply'] == good
    assert any(d['ref'].startswith('claim:') for d in r['dropped_refs'])


def test_true_structural_claims_survive(clean):
    svc, ref, *_ = clean
    text = ('The longest path has 19 gate levels. multiplier_1 contains 213 gates. operation drives 16 loads. '
            'Buffering could reduce delay.')
    a, _ = _chat(svc, [_reply(text)])
    r = a.chat(None, ref, 'What could hurt timing?')
    assert r['reply'] == text and not r['dropped_refs']


def test_definite_improvement_wording_is_softened(clean):
    svc, ref, *_ = clean
    a, _ = _chat(svc, [_reply('Buffering the net will reduce delay.')])
    assert a.chat(None, ref, 'How could I improve performance?')['reply'] == 'Buffering the net could reduce delay.'


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

def test_insights_route_and_focus_validation():
    import threading
    import urllib.request
    import urllib.error
    import web_dashboard
    srv = web_dashboard.make_server('127.0.0.1', 0, llm=FakeLLM(default=_reply('ok')), probe=False)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{srv.server_address[1]}'

    def post(path, body):
        req = urllib.request.Request(base + path, data=json.dumps(body).encode(), method='POST',
                                     headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())
    try:
        st, ins = post('/api/insights', {'circuit_name': CLEAN})
        assert st == 200 and ins['timing']['max_depth'] == 19 and ins['data_availability']['gate_delays'] is False
        assert ins['capabilities']['graphsaint']['supported'] is True and ins['optimizations']
        st, _ = post('/api/insights', {'circuit_name': '../../.env'})
        assert st in (400, 404)
        st, body = post('/api/assistant/chat', {'circuit_name': CLEAN, 'message': 'Explain this gate',
                                                'focus': 'G5'})
        assert st == 400 and body['error_code'] == 'INVALID_FOCUS'
        st, body = post('/api/assistant/chat', {'circuit_name': CLEAN, 'message': 'Explain this gate',
                                                'focus': {'kind': 'gate', 'id': 5}})
        assert st == 200 and body['tool_trace'][0]['arguments'] == {'gate_id': 5}
    finally:
        srv.shutdown()


# ---------------------------------------------------------------------------
# Cell BOM, datasheets, liberty data and BOM-based PPA recommendations
# ---------------------------------------------------------------------------
import cell_datasheet  # noqa: E402
from collections import Counter  # noqa: E402

MINI_LIB = """
library (mini65) {
  leakage_power_unit : "1nW";
  capacitive_load_unit (1, pf);
  cell (NAND2_X1M_A9TH) { area : 1.44; cell_leakage_power : 2.5;
    pin (A) { direction : input; capacitance : 0.0012; }
    pin (B) { direction : input; capacitance : 0.0013; }
    pin (Y) { direction : output; max_capacitance : 0.08; } }
  cell (NAND2_X0P5M_A9TH) { area : 1.08; cell_leakage_power : 1.25;
    pin (A) { direction : input; capacitance : 0.0008; } }
  cell (INV_X0P6M_A9TH) { area : 0.72; cell_leakage_power : 0.9; }
}
"""


def test_bom_counts_are_exact(clean):
    *_, model, a, ins, tools = clean
    rows = ins.bom['rows']
    assert sum(r['count'] for r in rows) == model['num_gates'] == ins.bom['totals']['instances']
    assert {r['cell']: r['count'] for r in rows} == dict(Counter(g['cell_type'] for g in model['gates']))
    assert ins.bom['library_loaded'] is False and ins.bom['totals'].get('area') is None
    assert all(r['area_each'] is None for r in rows)                   # never invented without a liberty file


@pytest.mark.parametrize('cell, fn', [
    ('AOI21_X1M_A9TH', 'Y = !((A0 & A1) | B0)'), ('OAI22_X1M_A9TH', 'Y = !((A0 | A1) & (B0 | B1))'),
    ('NAND2B_X1P4M_A9TH', 'Y = !(!A & B)'), ('NOR2XB_X1M_A9TH', 'Y = !(A | !B)'), ('AO21B_X1M_A9TH', 'Y = (A0 & A1) | !B0'),
    ('INV_X0P6M_A9TH', 'Y = !A'), ('ADDF_X1M_A9TH', 'S = A ^ B ^ CI; CO = majority(A, B, CI)  (full adder)')])
def test_datasheet_function_from_naming_convention(cell, fn):
    ds = cell_datasheet.datasheet(cell)
    assert ds['function'] == fn and ds['function_source'].startswith('naming convention')
    assert ds['pins_source'] == 'cell_library.json' and ds['area'] is None


def test_unknown_mux_variant_function_is_not_guessed():
    assert cell_datasheet.datasheet('MXT2_X0P5M_A9TH')['function'] is None
    assert cell_datasheet.drive_strength('INV_X0P5B_A9TH') == 0.5


def test_liberty_parser_and_library_backed_bom(synth):
    lib = cell_datasheet.parse_liberty(MINI_LIB)
    assert lib['library'] == 'mini65' and lib['units']['leakage_power'] == '1nW'
    nand = lib['cells']['NAND2_X1M_A9TH']
    assert nand['area'] == 1.44 and nand['leakage_power'] == 2.5 and nand['pins']['A']['capacitance'] == 0.0012
    lib['files'] = ['mini.lib']
    svc, ref, a, _ = synth
    model, _ = svc.load(ref)
    ins = di.compute(model, a, liberty=lib)
    t = ins.bom['totals']
    assert t['area'] == pytest.approx(1.44 + 1.08 + 5 * 0.72) and t['leakage_power'] == pytest.approx(2.5 + 1.25 + 5 * 0.9)
    assert ins.data_availability()['cell_area'] is True
    top = next(o for o in ins.optimizations if 'area contributors' in o['target'])
    assert top['type'] == 'deterministic' and top['target'].endswith('INV_X0P6M_A9TH, NAND2_X1M_A9TH, NAND2_X0P5M_A9TH')
    assert ins.capabilities()['bom']['mode'] == 'liberty'


def test_library_area_may_be_quoted_but_invented_area_is_removed(synth):
    lib = dict(cell_datasheet.parse_liberty(MINI_LIB), files=['mini.lib'])
    svc, ref, a, _ = synth
    model, _ = svc.load(ref)
    ins = di.compute(model, a, liberty=lib)
    from grounding import Grounder
    g = Grounder(model, a['findings'])
    facts = {'ppa_values': ins.ppa_values()}
    text = f"Total cell area is {ins.bom['totals']['area']} um2. The NAND2 uses 9.9 um2. It runs at 2 GHz."
    out = g.check_metrics(text, 'x', facts)
    assert out == f"Total cell area is {ins.bom['totals']['area']} um2."


def test_bom_recommendations_for_drive_strength(clean):
    ins = clean[4]
    weak = ins.bom['weak_drive_high_fanout']
    assert weak and all(w['drive'] < 1 and w['fanout'] >= di.HIGH_FANOUT_MIN for w in weak)
    for w in weak:
        assert ins.gate_fanout(w['gate']) == w['fanout'] and ins.ctx.cell[w['gate']] == w['cell']
    rec = next(o for o in ins.optimizations if 'weak-drive' in o['target'])
    assert rec['category'] == 'performance' and set(rec['gate_ids']) == {w['gate'] for w in weak}


def test_get_bom_tool_and_datasheet(clean):
    tools = clean[5]
    out = tools.call('get_bom', {'cell': None})
    assert out['summary'].startswith('CELL BOM: 239 instances') and 'No liberty file loaded' in out['summary']
    assert any(c['kind'] == 'optimization' for c in out['cards'])
    ds = tools.call('get_bom', {'cell': 'NAND2_X0P5M_A9TH'})
    assert ds['summary'].startswith('DATASHEET NAND2_X0P5M_A9TH') and 'Y = !(A & B)' in ds['summary']
    assert 'not available (no liberty data' in ds['summary']
    assert 'error' in tools.call('get_bom', {'cell': 'FAKE_X1_CELL'})


@pytest.mark.parametrize('q, args', [('Show the cell BOM', {'cell': None}),
                                     ('What is the datasheet of NAND2_X0P5M_A9TH?', {'cell': 'NAND2_X0P5M_A9TH'}),
                                     ('Which cells have weak drive strength?', {'cell': None}),
                                     ('Give PPA recommendations based on the bill of materials', {'cell': None})])
def test_bom_questions_plan_get_bom(clean, q, args):
    assert asst.plan_lookups(q, clean[2])[0] == ('get_bom', args)


def test_bom_csv_route():
    import threading
    import urllib.request
    import web_dashboard
    srv = web_dashboard.make_server('127.0.0.1', 0, llm=FakeLLM(available=False), probe=False)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        url = f'http://127.0.0.1:{srv.server_address[1]}/api/bom.csv?circuit_name={CLEAN}'
        with urllib.request.urlopen(url, timeout=60) as r:
            assert r.headers['Content-Type'].startswith('text/csv')
            lines = r.read().decode().strip().splitlines()
        from netlist_graph_engine import build_circuit_model
        cells = {g['cell_type'] for g in build_circuit_model(resolve_circuit(CLEAN).path)['gates']}
        assert lines[0].startswith('cell,family,description') and len(lines) - 1 == len(cells)
    finally:
        srv.shutdown()


def test_wrong_cell_counts_are_removed(clean):
    svc, ref, model, a, ins, _ = clean
    counts = {r['cell']: r['count'] for r in ins.bom['rows']}
    inv = counts['INV_X0P7M_A9TH']
    good = f"- NOR2_X0P5M_A9TH: {counts['NOR2_X0P5M_A9TH']} instances, drive strength is X0.5"
    bad = f"- INV_X0P7M_A9TH: {inv + 7} instances, drive strength is X0.7"
    a_, _ = _chat(svc, [_reply(f'The cells with weak drive strength are:\n{good}\n{bad}')])
    r = a_.chat(None, ref, 'Which cells have weak drive strength?')
    assert good in r['reply'] and bad not in r['reply']
    assert any('wrong cell count' in d['ref'] for d in r['dropped_refs'])


def test_bom_recommendations_are_tagged_and_summary_lists_weak_cells(clean):
    ins, tools = clean[4], clean[5]
    bom_recs = [o for o in ins.optimizations if o.get('source') == 'bom']
    assert bom_recs and all('ripple' not in o['target'] for o in bom_recs)
    out = tools.call('get_bom', {'cell': None})
    assert {c['id'] for c in out['cards'] if c['kind'] == 'optimization'} == {o['id'] for o in bom_recs}
    weak_line = next(l for l in out['summary'].split('\n') if l.startswith('Cell types with drive below X1'))
    assert f"NOR2_X0P5M_A9TH {next(r['count'] for r in ins.bom['rows'] if r['cell'] == 'NOR2_X0P5M_A9TH')}" in weak_line


def test_bom_question_does_not_pull_every_ppa_tool(clean):
    plan = asst.plan_lookups('Give power, performance and area recommendations based on the cell BOM', clean[2])
    assert plan == [('get_bom', {'cell': None})]
