"""Gate order must stay aligned with predictions_all_nodes.csv on every benchmark."""
import os

import numpy as np
import pytest

from conftest import BENCHMARKS, CSV_PATH, bench_id
from netlist_graph_engine import build_circuit_graph, build_circuit_model, parse_verilog_netlist


@pytest.fixture(scope='module')
def csv_by_circuit():
    if not os.path.exists(CSV_PATH):
        pytest.skip('predictions_all_nodes.csv not present (gitignored artifact)')
    import pandas as pd
    df = pd.read_csv(CSV_PATH)
    return {c: g.sort_values('node_id') for c, g in df.groupby('circuit_file')}


def test_all_37_benchmarks_present():
    assert len(BENCHMARKS) == 37


@pytest.mark.parametrize('path', BENCHMARKS, ids=bench_id)
def test_gate_order_matches_csv(path, csv_by_circuit):
    name = os.path.basename(path)
    parsed = parse_verilog_netlist(path)
    csv = csv_by_circuit[name]
    assert [g['inst_name'].strip() for g in parsed['gates']] == csv['cell_name'].tolist()
    # labels from the instance-name heuristic agree with the CSV's true_class
    _, _, _, labels = build_circuit_graph(parsed)
    assert labels.tolist() == csv['true_class'].astype(int).tolist()


@pytest.mark.parametrize('path', BENCHMARKS, ids=bench_id)
def test_circuit_model_keeps_legacy_outputs(path):
    nodes, edges, feats, labels = build_circuit_graph(parse_verilog_netlist(path))
    m = build_circuit_model(path)
    assert m['nodes'] == nodes
    assert m['edges'] == edges
    assert np.array_equal(m['features'], feats)
    assert np.array_equal(m['labels'], labels)
    assert m['num_gates'] == len(nodes)
