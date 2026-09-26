"""Each injected fault is detected at the right gate/net with the right suggested edge."""
import json
import os

import pytest

from circuit_checks import run_checks
from circuit_store import DEMO_DIR, DEMO_MANIFEST, DATASET_DIR
from conftest import BENCHMARKS, bench_id
from fault_injector import FAULT_TYPES, NoEligibleSite, inject
from netlist_graph_engine import build_circuit_model

BASES = ['Test_add_mul_comp_sub_16_bit_Syn_65nm.v', 'Validate_add_mul_8_bit_Syn_65nm.v',
         'Train_add_mul_sub_4_bit_Syn_65nm.v']


def _edge_matches(edge, expected):
    return all(edge.get(k) == v for k, v in expected.items())


def _run(path, fault, seed=0):
    try:
        res = inject(path, fault, seed)
    except NoEligibleSite:
        pytest.skip(f'no eligible {fault} site in {os.path.basename(path)}')
    original = build_circuit_model(path)
    model = build_circuit_model(text=res['text'])
    assert model['num_gates'] == original['num_gates'], 'fault must not change gate count/order'
    assert [g['inst_name'] for g in model['gates']] == [g['inst_name'] for g in original['gates']]
    return res, run_checks(model)


def _check_detection(res, out, require_top=True):
    expected = res['expected_edge']
    hits = [f for f in out['findings'] if f['check'] == res['expected_check']]
    assert hits, f"{res['expected_check']} not reported; got {out['stats']['by_check']}"

    located = [f for f in hits if res['gate_id'] in f['gate_ids'] or res['net'] in f['nets']]
    assert located, f"{res['expected_check']} does not point at gate {res['gate_id']} / net {res['net']}"

    all_edges = [e for f in out['findings'] for e in f['suggested_edges']]
    assert any(_edge_matches(e, expected) for e in all_edges), (expected, all_edges[:5])
    if require_top:
        assert any(f['suggested_edges'] and _edge_matches(f['suggested_edges'][0], expected) for f in located)
    for e in all_edges:
        assert 0 < e['confidence'] <= 1 and e['reason']


@pytest.mark.parametrize('base', BASES, ids=lambda b: b[:26])
@pytest.mark.parametrize('fault', [f for f in FAULT_TYPES if f != 'second_driver'])
def test_fault_detected_with_top_ranked_repair(fault, base):
    res, out = _run(os.path.join(DATASET_DIR, base), fault)
    _check_detection(res, out, require_top=True)


@pytest.mark.parametrize('base', BASES, ids=lambda b: b[:26])
def test_second_driver_offers_both_candidate_repairs(base):
    """Which of two drivers is the intruder is structurally ambiguous: both are offered at 0.5."""
    res, out = _run(os.path.join(DATASET_DIR, base), 'second_driver')
    _check_detection(res, out, require_top=False)
    floating = [f for f in out['findings'] if f['check'] == 'floating_net']
    assert floating and all(e['confidence'] <= 0.5 for f in floating for e in f['suggested_edges'])


def test_cut_carry_also_reports_structural_carry_break():
    res, out = _run(os.path.join(DATASET_DIR, 'Validate_add_mul_8_bit_Syn_65nm.v'), 'cut_carry')
    breaks = [f for f in out['findings'] if f['check'] == 'carry_break' and f['severity'] == 'warning']
    assert breaks and breaks[0]['bus'] == 'Result_add'
    assert res['gate_id'] in breaks[0]['gate_ids']
    assert any(_edge_matches(e, res['expected_edge']) for e in breaks[0]['suggested_edges'])


def test_miswire_is_electrically_clean_but_caught_by_bit_slice_check():
    res, out = _run(os.path.join(DATASET_DIR, 'Test_add_mul_comp_sub_16_bit_Syn_65nm.v'), 'miswire_bits')
    assert not [f for f in out['findings'] if f['category'] in ('electrical', 'reachability')]
    anomalies = [f for f in out['findings'] if f['check'] == 'bit_slice_anomaly' and f['severity'] == 'warning']
    assert len(anomalies) == 1
    partner = res['partner']
    assert any(e.get('to_gate') == partner['gate_id'] and e.get('to_pin') == partner['pin']
               for e in anomalies[0]['suggested_edges'])


def test_findings_have_contract_fields():
    _, out = _run(os.path.join(DATASET_DIR, BASES[0]), 'drop_pin')
    for f in out['findings']:
        assert f['id'].startswith('F') and len(f['id']) == 4
        assert f['category'] in ('electrical', 'structural', 'gnn_suspicion', 'reachability', 'intent')
        assert f['severity'] in ('error', 'warning', 'info')
        for key in ('gate_ids', 'nets', 'pins', 'suggested_edges', 'evidence', 'confidence'):
            assert key in f
    json.dumps(out)   # JSON-serialisable


def test_demo_faults_are_detected():
    with open(DEMO_MANIFEST, encoding='utf-8') as fh:
        manifest = json.load(fh)
    assert len(manifest) == 3
    for name, meta in manifest.items():
        out = run_checks(build_circuit_model(os.path.join(DEMO_DIR, name)))
        assert any(f['check'] == meta['expected_check'] for f in out['findings']), name
        edges = [e for f in out['findings'] for e in f['suggested_edges']]
        assert any(_edge_matches(e, meta['expected_edge']) for e in edges), name


@pytest.mark.slow
@pytest.mark.parametrize('path', BENCHMARKS, ids=bench_id)
@pytest.mark.parametrize('fault', FAULT_TYPES)
def test_full_fault_matrix(fault, path):
    res, out = _run(path, fault)
    _check_detection(res, out, require_top=fault != 'second_driver')
