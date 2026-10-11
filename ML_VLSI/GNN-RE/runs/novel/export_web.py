"""
Export the selected round-3 model's predictions for every node, in the same CSV layout as GraphSAINT's
predictions_all_nodes.csv / predictions_test_per_gate.csv, so the web dashboard can show it.

Retrains exactly the final model (cfg fndir_h1s1, 5 seeds, train circuits, early-stopped on validation) and
predicts all nodes. Asserts the test probabilities match final_fndir_h1s1/test_probs_raw.npy, so the exported
test predictions are the ones reported in RESULTS.md. Train-node predictions are in-sample (as for GraphSAINT).

  python export_web.py
"""
import os

import numpy as np
import pandas as pd

import novel as NV

CFG, SEEDS = 'fndir_h1s1', 5
OUT = os.path.join(NV.HERE, 'final_' + CFG)
GS = os.path.join(NV.HERE, '..', '..', 'GraphSAINT')
PROB_COLS = ['prob_0_adder', 'prob_1_multiplier', 'prob_2_control', 'prob_3_subtractor', 'prob_4_comparator']


def main():
    feats, A, y, circ, bits, split = NV.load()
    cache = NV.prepare_cache(feats, A)
    X = NV.build(NV.CONFIGS[CFG], feats, A, split, cache)
    allnodes = np.arange(len(y))
    P = np.mean([NV.fit_predict(X, y, split['tr'], split['va'], allnodes, seed=s)[0] for s in range(SEEDS)], 0)
    te = split['te']
    ref = np.load(os.path.join(OUT, 'test_probs_raw.npy'))
    assert np.array_equal(np.load(os.path.join(OUT, 'test_node_ids.npy')), te)
    diff = np.abs(P[te] - ref).max()
    same = int((P[te].argmax(1) == ref.argmax(1)).sum())
    print(f'test probs max |diff| vs final run: {diff:.2e}; identical argmax on {same}/{len(te)} test gates')
    assert same == len(te), 'retrained model does not reproduce the reported test predictions'
    P[te] = ref                                              # export exactly the reported test probabilities
    pred = P.argmax(1)

    gs = pd.read_csv(os.path.join(GS, 'predictions_all_nodes.csv')).sort_values('node_id')
    assert (gs['node_id'].values == allnodes).all() and (gs['true_class'].values == y).all()
    df = gs[['node_id', 'cell_name', 'circuit_file', 'role', 'true_class']].copy()
    df['pred_class'] = pred
    df['is_correct'] = df['pred_class'] == df['true_class']
    df.to_csv(os.path.join(OUT, 'predictions_all_nodes.csv'), index=False)

    t = df[df['role'] == 'te'].drop(columns='role').copy()
    for k, c in enumerate(PROB_COLS):
        t[c] = P[t['node_id'].values, k]
    t.to_csv(os.path.join(OUT, 'predictions_test_per_gate.csv'), index=False)
    for r in ('tr', 'va', 'te'):
        m = df['role'] == r
        print(r, f"acc {df.loc[m, 'is_correct'].mean():.4f}  n={m.sum()}")


if __name__ == '__main__':
    main()
