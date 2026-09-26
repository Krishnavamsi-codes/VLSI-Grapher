"""
Pin the false-positive baseline: on all 37 unmodified benchmarks every check
(electrical, reachability, structural, carry, bit-slice) must report zero
errors and zero warnings. The only allowed findings are model-based info.
"""
import os

import pytest

import gnn_re_inference
from circuit_checks import run_checks
from conftest import BENCHMARKS, bench_id
from netlist_graph_engine import build_circuit_model

ALLOWED_INFO = {'class_disagrees_with_neighbours', 'low_confidence_prediction', 'singleton_subcircuit'}


def _predictions(name):
    res = gnn_re_inference.lookup_circuit(name)
    if res is None:
        return None, None, None
    return res['metrics']['predictions'], res['metrics']['probabilities'], 'graphsaint'


@pytest.mark.parametrize('path', BENCHMARKS, ids=bench_id)
def test_clean_benchmark_has_no_errors_or_warnings(path):
    name = os.path.basename(path)
    preds, probs, source = _predictions(name)
    result = run_checks(build_circuit_model(path), preds, probs, source)
    stats = result['stats']
    offending = [f for f in result['findings'] if f['severity'] != 'info']
    assert offending == [], offending[:3]
    assert stats['errors'] == 0 and stats['warnings'] == 0
    for f in result['findings']:
        assert f['check'] in ALLOWED_INFO, f
        assert f['model_based'] is True


@pytest.mark.parametrize('path', [p for p in BENCHMARKS if '_1_bit' not in p and '_2_bit' not in p], ids=bench_id)
def test_bit_slice_check_is_not_vacuous(path):
    """Every >=4-bit benchmark has arithmetic buses recognised, each matching the ripple pattern exactly."""
    stats = run_checks(build_circuit_model(path))['stats']
    patterns = stats['arithmetic_bus_patterns']
    assert patterns, 'no arithmetic bus recognised'
    assert all(p['bits_matching_pattern'] == p['bits_with_dependency'] for p in patterns)
    assert any(p['bus'].startswith('Result_add') for p in patterns)
