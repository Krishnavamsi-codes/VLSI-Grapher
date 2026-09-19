"""
gnn_re_inference.py  -  Tier 1 GNN-RE Inference Bridge
=======================================================
Loads the real stored GNN-RE predictions produced by the trained GraphSAINT
checkpoint (saved_model_2026-09-04 15-42-03.pkl) from two pre-computed CSVs:

    predictions_all_nodes.csv       - every node in every circuit (train/val/test)
    predictions_test_per_gate.csv   - test-only nodes, includes per-class probabilities

The module is intentionally standalone: it does NOT import any GraphSAINT code,
does NOT call argparse, and does NOT require PyTorch at startup.

Public API
----------
    lookup_circuit(circuit_name)
        Returns a dict with real GNN-RE metrics and per-gate predictions for the
        requested circuit.  Used by the /api/infer backend route.

    available_circuits()
        Returns the list of circuit filenames present in the CSV.
"""

import os
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, confusion_matrix

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_GRAPHSAINT_DIR = os.path.join(_HERE, "GNN-RE", "GraphSAINT")

_ALL_NODES_CSV   = os.path.join(_GRAPHSAINT_DIR, "predictions_all_nodes.csv")
_TEST_GATES_CSV  = os.path.join(_GRAPHSAINT_DIR, "predictions_test_per_gate.csv")

# Class definitions - must match the trained model's label encoding
CLASS_NAMES  = ["Adder", "Multiplier", "Control Logic", "Subtractor", "Comparator"]
CLASS_COLORS = ["#3B82F6", "#10B981", "#F59E0B", "#A855F7", "#06B6D4"]
NUM_CLASSES  = 5

# ---------------------------------------------------------------------------
# Load CSVs once at module import time
# ---------------------------------------------------------------------------
def _load_predictions():
    if not os.path.exists(_ALL_NODES_CSV):
        print("[gnn_re_inference] WARNING: CSV not found at", _ALL_NODES_CSV)
        return {}

    all_df = pd.read_csv(_ALL_NODES_CSV)

    # Load per-class probabilities for test circuits if available
    prob_map = {}
    if os.path.exists(_TEST_GATES_CSV):
        test_df = pd.read_csv(_TEST_GATES_CSV)
        prob_cols = [c for c in test_df.columns if c.startswith("prob_")]
        if prob_cols:
            for circ, grp in test_df.groupby("circuit_file"):
                pm = {}
                for _, row in grp.iterrows():
                    pm[row["cell_name"]] = [float(row[c]) for c in prob_cols]
                prob_map[circ] = pm

    lookup = {}
    for circuit_file, grp in all_df.groupby("circuit_file"):
        grp = grp.sort_values("node_id").reset_index(drop=True)
        cell_names   = grp["cell_name"].tolist()
        true_classes = grp["true_class"].astype(int).tolist()
        pred_classes = grp["pred_class"].astype(int).tolist()
        roles        = grp["role"].tolist()

        probs = None
        if circuit_file in prob_map:
            pm = prob_map[circuit_file]
            probs = [pm.get(cn, [0.0] * NUM_CLASSES) for cn in cell_names]

        lookup[circuit_file] = {
            "true_class":    true_classes,
            "pred_class":    pred_classes,
            "cell_names":    cell_names,
            "role":          roles,
            "probabilities": probs,
        }

    print("[gnn_re_inference] Loaded real GNN-RE predictions for", len(lookup), "circuits.")
    return lookup


# The single in-memory lookup built once at import time
CIRCUIT_LOOKUP = _load_predictions()


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def available_circuits():
    return sorted(CIRCUIT_LOOKUP.keys())


def lookup_circuit(circuit_name):
    """
    Return real GNN-RE results for circuit_name.

    Returns dict with keys: metrics, source, n_gates
    Returns None if circuit not in CSV.
    """
    if circuit_name not in CIRCUIT_LOOKUP:
        return None

    entry = CIRCUIT_LOOKUP[circuit_name]
    y_true = np.array(entry["true_class"], dtype=int)
    y_pred = np.array(entry["pred_class"], dtype=int)
    n = len(y_true)

    if n == 0:
        return None

    acc    = float(accuracy_score(y_true, y_pred))
    f1_mic = float(f1_score(y_true, y_pred, average="micro",     zero_division=0))
    f1_mac = float(f1_score(y_true, y_pred, average="macro",     zero_division=0))
    prec   = float(f1_score(y_true, y_pred, average="macro",     zero_division=0))
    rec    = float(f1_score(y_true, y_pred, average="weighted",  zero_division=0))

    conf = confusion_matrix(y_true, y_pred, labels=list(range(NUM_CLASSES)))

    probs = entry["probabilities"]
    if probs is None:
        probs = []
        for p in y_pred.tolist():
            row = [0.0] * NUM_CLASSES
            row[p] = 1.0
            probs.append(row)

    return {
        "metrics": {
            "accuracy":         acc,
            "f1_micro":         f1_mic,
            "f1_macro":         f1_mac,
            "precision":        prec,
            "recall":           rec,
            "predictions":      y_pred.tolist(),
            "probabilities":    probs,
            "confusion_matrix": conf.tolist(),
        },
        "source":  "csv_lookup",
        "n_gates": n,
    }


def build_colored_nodes(nodes, circuit_name):
    """
    Re-color node list using real GNN-RE predicted classes.
    nodes: list of dicts from build_circuit_graph()
    Returns updated node list (shallow copies, originals not mutated).
    """
    if circuit_name not in CIRCUIT_LOOKUP:
        return nodes

    pred_classes = CIRCUIT_LOOKUP[circuit_name]["pred_class"]
    updated = []
    for node in nodes:
        nid = node["id"]
        if nid < len(pred_classes):
            pc = pred_classes[nid]
            node = dict(node)
            node["pred_class"] = pc
            node["color"]      = CLASS_COLORS[pc] if pc < NUM_CLASSES else "#64748b"
            node["class_name"] = CLASS_NAMES[pc]  if pc < NUM_CLASSES else "Unknown"
        updated.append(node)
    return updated
