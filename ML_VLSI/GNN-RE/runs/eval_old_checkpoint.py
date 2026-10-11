"""Inference-only: evaluate the ORIGINAL run's best-val checkpoint (Sep 4) with the unmodified repo code,
and compare against the old predictions CSV that the dashboard used (96.27%)."""
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GS = os.path.join(os.path.dirname(HERE), 'GraphSAINT')
OUT = sys.argv[1]
os.chdir(GS)
sys.path.insert(0, GS)
sys.argv = ['x', '--data_prefix', '../Netlist_to_graph/Graphs_datasets/Interconnected-Modules',
            '--train_config', '../TCAD.yml', '--gpu', '0']
import numpy as np  # noqa: E402
import torch  # noqa: E402
import graphsaint.globals as G  # noqa: E402
from graphsaint.utils import parse_n_prepare  # noqa: E402
from graphsaint.pytorch_version.train import prepare  # noqa: E402
from graphsaint.pytorch_version.utils import to_numpy  # noqa: E402
from sklearn.metrics import accuracy_score, f1_score  # noqa: E402

CKPT = os.path.join(GS, 'pytorch_models', 'saved_model_2026-09-04 15-42-03.pkl')
train_params, train_phases, train_data, arch_gcn = parse_n_prepare(G.args_global)
model, minibatch, _, _ = prepare(train_data, train_params, arch_gcn)
model.load_state_dict(torch.load(CKPT))
loss, preds, labels = model.eval_step(*minibatch.one_batch(mode='valtest'))
preds, labels = to_numpy(preds), to_numpy(labels)
res = {'checkpoint': CKPT, 'checkpoint_mtime': os.path.getmtime(CKPT)}
for name, idx in (('val', minibatch.node_val), ('test', minibatch.node_test)):
    t, p = labels[idx].argmax(1), preds[idx].argmax(1)
    res[name] = {'accuracy': accuracy_score(t, p), 'micro': f1_score(t, p, average='micro'),
                 'macro': f1_score(t, p, average='macro'), 'errors': int((t != p).sum())}
old = {int(r['node_id']): int(r['pred_class']) for r in csv.DictReader(open('predictions_test_per_gate.csv'))}
new = {int(n): int(preds[n].argmax()) for n in minibatch.node_test}
res['old_csv_vs_old_checkpoint_disagreements'] = sum(old[n] != new[n] for n in new)
with open(OUT, 'w') as f:
    json.dump(res, f, indent=2)
print(json.dumps(res, indent=2))
