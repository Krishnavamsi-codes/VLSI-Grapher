"""
Clean rerun of the GNN-RE authors' released GraphSAINT (PyTorch) configuration.

This is a logging / checkpoint-handling wrapper around the UNMODIFIED repository code:
  graphsaint.utils.parse_n_prepare        (data loading, train-only StandardScaler)
  graphsaint.pytorch_version.train.prepare (Minibatch + GraphSAINT model construction)
  Minibatch.set_sampler / shuffle / one_batch / end
  GraphSAINT.train_step / eval_step
  graphsaint.metric.calc_f1

The training loop below mirrors graphsaint/pytorch_version/train.py::train() step for step
(single phase, eval every epoch, save on strictly-better validation Micro-F1, restore best
before the final val/test evaluation). Added on top: explicit seeding, per-epoch logging,
preflight verification, and exporting predictions ONLY from the restored best checkpoint.

Usage (from anywhere):
  python run_baseline.py --exp_dir <dir> [--preflight_only]
"""
import argparse
import csv
import datetime
import hashlib
import json
import os
import platform
import random
import shutil
import subprocess
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
GNNRE = os.path.dirname(HERE)
GS = os.path.join(GNNRE, 'GraphSAINT')
PREFIX = '../Netlist_to_graph/Graphs_datasets/Interconnected-Modules'   # load_data() prepends './'
YML = os.path.join(GNNRE, 'TCAD.yml')
DATA_DIR = os.path.join(GNNRE, 'Netlist_to_graph', 'Graphs_datasets', 'Interconnected-Modules')

CLASS_NAMES = ['ADD', 'MUL', 'CTRL', 'SUB', 'COMP']     # class_map indices 0..4 (README)
EXPECTED = {'nodes': 104727, 'train': 96251, 'val': 1938, 'test': 6538, 'classes': 5,
            'train_circuits': 22, 'val_circuits': 6, 'test_circuits': 9}

cli = argparse.ArgumentParser()
cli.add_argument('--exp_dir', required=True)
cli.add_argument('--preflight_only', action='store_true')
cli.add_argument('--seed', type=int, default=42)
opts = cli.parse_args()
EXP = os.path.abspath(opts.exp_dir)
SEED = opts.seed
for sub in ('logs', 'checkpoints', 'predictions', 'metrics', 'config', 'analysis'):
    os.makedirs(os.path.join(EXP, sub), exist_ok=True)


class Log:
    """Write to a file and the console, flushing every line."""
    def __init__(self, path):
        self.f = open(path, 'a', encoding='utf-8')

    def __call__(self, *parts):
        line = ' '.join(str(p) for p in parts)
        print(line, flush=True)
        self.f.write(line + '\n')
        self.f.flush()


log = Log(os.path.join(EXP, 'logs', 'train.log'))
syslog = Log(os.path.join(EXP, 'logs', 'system.log'))


def P(*parts):
    return os.path.join(EXP, *parts)


def write(path, text):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)


def sh(cmd, cwd=None):
    try:
        return subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True, timeout=60).stdout.strip()
    except Exception as exc:  # noqa: BLE001
        return f'<unavailable: {exc}>'


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def gpu_snapshot(tag):
    syslog(f'[{datetime.datetime.now().isoformat(timespec="seconds")}] {tag}: ' +
           sh('nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu --format=csv,noheader'))


T = {'script_start': time.time()}

# ---- the repo's globals.py parses sys.argv at import time -----------------------------------
os.chdir(GS)
sys.path.insert(0, GS)
sys.argv = ['run_baseline', '--data_prefix', PREFIX, '--train_config', YML, '--gpu', '0', '--dir_log', P('logs')]

# ---- seeding (the repo has no seed mechanism: globals.py has it commented out) --------------
random.seed(SEED)
import numpy as np  # noqa: E402
np.random.seed(SEED)
import torch  # noqa: E402
torch.manual_seed(SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)
write(P('config', 'seed.txt'),
      f'SEED={SEED}\npython random.seed({SEED})\nnumpy.random.seed({SEED})\ntorch.manual_seed({SEED})\n'
      f'torch.cuda.manual_seed_all({SEED})\n'
      'Repository seed mechanism: none (graphsaint/globals.py has its seed lines commented out).\n'
      'Seeds are set once, before data loading / model construction / sampling, and never changed.\n'
      'cuDNN/cuSPARSE determinism is NOT forced (would alter execution); GPU sparse ops may be\n'
      'non-deterministic across runs, so bit-exact reruns are not guaranteed.\n'
      'Sampler RNG: graphsaint/cython_sampler.py (NumPy) uses np.random -> covered by numpy seed.\n')

import graphsaint.globals as G  # noqa: E402
from graphsaint.utils import parse_n_prepare  # noqa: E402
from graphsaint.metric import calc_f1  # noqa: E402
from graphsaint.pytorch_version.train import prepare  # noqa: E402
from graphsaint.pytorch_version.utils import to_numpy  # noqa: E402
import scipy.sparse as sp  # noqa: E402
import sklearn  # noqa: E402
import yaml  # noqa: E402
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,  # noqa: E402
                             precision_recall_fscore_support)
from sklearn.preprocessing import StandardScaler  # noqa: E402

device = 'cuda' if G.args_global.gpu >= 0 and torch.cuda.is_available() else 'cpu'

# =============================================================================================
# CONFIG / ENVIRONMENT
# =============================================================================================
shutil.copyfile(YML, P('config', 'TCAD.yml'))
shutil.copyfile(os.path.abspath(__file__), P('config', 'run_baseline.py'))
with open(YML) as f:
    tcad = yaml.safe_load(f)

gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none'
gpu_mem = (f'{torch.cuda.get_device_properties(0).total_memory / 2**30:.2f} GiB'
           if torch.cuda.is_available() else 'n/a')
ram = sh('powershell -NoProfile -Command "[math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory/1GB,1)"')
cpu = sh('powershell -NoProfile -Command "(Get-CimInstance Win32_Processor).Name"') or platform.processor()
commits = {
    'GraphSAINT (upstream clone)': sh('git rev-parse HEAD', cwd=GS),
    'GNN-RE (authors repo)': sh('git rev-parse HEAD', cwd=GNNRE),
    'ML_VLSI (top-level project)': sh('git rev-parse HEAD', cwd=os.path.dirname(GNNRE)),
}
env = [
    f'Python: {sys.version.split()[0]} ({sys.executable})',
    f'PyTorch: {torch.__version__}',
    f'CUDA (torch build): {torch.version.cuda}',
    f'CUDA available: {torch.cuda.is_available()}',
    f'cuDNN: {torch.backends.cudnn.version()}',
    f'GPU: {gpu_name}',
    f'GPU memory: {gpu_mem}',
    f'NVIDIA driver: {sh("nvidia-smi --query-gpu=driver_version --format=csv,noheader")}',
    f'Device used for training and evaluation: {device}',
    f'CPU: {cpu}',
    f'RAM (GB): {ram}',
    f'OS: {platform.platform()}',
    f'NumPy: {np.__version__}   SciPy: {sp.__name__ and __import__("scipy").__version__}   scikit-learn: {sklearn.__version__}',
] + [f'Git commit, {k}: {v}' for k, v in commits.items()]
write(P('config', 'environment.txt'), '\n'.join(env) + '\n')
for line in env:
    syslog(line)
gpu_snapshot('start')

gs_lines = []
for name, path in (('GraphSAINT', GS), ('GNN-RE', GNNRE), ('ML_VLSI', os.path.dirname(GNNRE))):
    gs_lines += [f'===== {name} ({path}) =====', '$ git status', sh('git status', cwd=path),
                 '$ git log --oneline -5', sh('git log --oneline -5', cwd=path), '']
gs_lines += ['===== Pre-existing local modifications to GraphSAINT (execution-only, NOT made by this run) =====',
             sh('git diff', cwd=GS),
             'graphsaint/cython_sampler.py and graphsaint/norm_aggr.py are untracked NumPy drop-ins for the',
             'Cython extensions (not compiled on this Windows machine). Audited earlier as algorithmically',
             'identical to cython_sampler.pyx RW / norm_aggr.pyx.']
write(P('config', 'git_status.txt'), '\n'.join(gs_lines) + '\n')

# =============================================================================================
# DATA LOADING (repository code)
# =============================================================================================
t0 = time.time()
train_params, train_phases, train_data, arch_gcn = parse_n_prepare(G.args_global)
if 'eval_val_every' not in train_params:
    train_params['eval_val_every'] = G.EVAL_VAL_EVERY_EP
T['data_loading'] = time.time() - t0
adj_full, adj_train, feat_full, class_arr, role = train_data

# ---- dataset verification (independent of the training code where possible) ---------------
raw_full = sp.load_npz(os.path.join(DATA_DIR, 'adj_full.npz'))
raw_train = sp.load_npz(os.path.join(DATA_DIR, 'adj_train.npz'))
raw_feats = np.load(os.path.join(DATA_DIR, 'feats.npy'))
with open(os.path.join(DATA_DIR, 'role.json')) as f:
    raw_role = json.load(f)
with open(os.path.join(DATA_DIR, 'class_map.json')) as f:
    raw_cm = {int(k): v for k, v in json.load(f).items()}
y_all = np.zeros(len(raw_cm), dtype=int)
for k, v in raw_cm.items():
    y_all[k] = int(np.argmax(v)) if isinstance(v, list) else int(v)

node_circuit = {}
with open(os.path.join(DATA_DIR, 'cell.txt'), encoding='utf-8', errors='replace') as f:
    for line in f:
        nid, rest = line.split(' ', 1)
        node_circuit[int(nid)] = rest.rsplit(' from file ', 1)[1].strip()

tr, va, te = (np.array(raw_role[k]) for k in ('tr', 'va', 'te'))
split_of = {}
for name, ids in (('train', tr), ('val', va), ('test', te)):
    for n in ids:
        split_of.setdefault(int(n), []).append(name)
multi = [n for n, s in split_of.items() if len(s) > 1]
circ_split = {}
for n, c in node_circuit.items():
    circ_split.setdefault(c, set()).update(split_of.get(n, ['NONE']))
mixed_circuits = [c for c, s in circ_split.items() if len(s) > 1]
circ_by = {s: sorted(c for c, ss in circ_split.items() if ss == {s}) for s in ('train', 'val', 'test')}
prefix_bad = [c for s, cs in circ_by.items() for c in cs
              if not c.startswith({'train': 'Train_', 'val': 'Validate_', 'test': 'Test_'}[s])]

asym_full = (raw_full != raw_full.T).nnz
asym_train = (raw_train != raw_train.T).nnz
tr_set = set(tr.tolist())
rt, ct = raw_train.nonzero()
train_edges_non_train = int(sum((r not in tr_set) or (c not in tr_set) for r, c in zip(rt, ct)))
self_loops = int(raw_full.diagonal().astype(bool).sum())

measured = {'nodes': raw_feats.shape[0], 'train': len(tr), 'val': len(va), 'test': len(te),
            'classes': len(np.unique(y_all)), 'train_circuits': len(circ_by['train']),
            'val_circuits': len(circ_by['val']), 'test_circuits': len(circ_by['test'])}
ds = [
    'DATASET VERIFICATION (Interconnected-Modules, read directly from the files)',
    f'Data dir: {DATA_DIR}',
    f'Number of nodes: {raw_feats.shape[0]}',
    f'adj_full: shape {raw_full.shape}, stored nonzeros {raw_full.nnz} (each undirected edge stored twice; '
    f'{self_loops} self-loops) -> undirected edges incl. self-loops ~ {(raw_full.nnz + self_loops) // 2}',
    f'adj_train: stored nonzeros {raw_train.nnz}',
    f'Number of features: {raw_feats.shape[1]}',
    f'Number of classes: {measured["classes"]}  (label counts all nodes: {np.bincount(y_all).tolist()})',
    f'Train nodes: {len(tr)}   Validation nodes: {len(va)}   Test nodes: {len(te)}   Sum: {len(tr) + len(va) + len(te)}',
    f'Train circuits ({len(circ_by["train"])}): {circ_by["train"]}',
    f'Validation circuits ({len(circ_by["val"])}): {circ_by["val"]}',
    f'Test circuits ({len(circ_by["test"])}): {circ_by["test"]}',
    f'Total circuits: {len(circ_split)}',
    f'Class counts  train {np.bincount(y_all[tr], minlength=5).tolist()}  val {np.bincount(y_all[va], minlength=5).tolist()}'
    f'  test {np.bincount(y_all[te], minlength=5).tolist()}  (order {CLASS_NAMES})',
    f'Nodes in more than one split: {len(multi)}',
    f'Circuits whose nodes span more than one split: {len(mixed_circuits)} {mixed_circuits[:5]}',
    f'Circuits whose filename prefix disagrees with their split: {prefix_bad}',
    f'SHA-256 feats.npy: {sha256(os.path.join(DATA_DIR, "feats.npy"))}',
    f'SHA-256 role.json: {sha256(os.path.join(DATA_DIR, "role.json"))}',
    f'SHA-256 class_map.json: {sha256(os.path.join(DATA_DIR, "class_map.json"))}',
    f'SHA-256 adj_full.npz: {sha256(os.path.join(DATA_DIR, "adj_full.npz"))}',
    f'SHA-256 adj_train.npz: {sha256(os.path.join(DATA_DIR, "adj_train.npz"))}',
    '',
    'Expected vs measured:',
] + [f'  {k}: expected {v}, measured {measured[k]}, {"OK" if measured[k] == v else "MISMATCH"}'
     for k, v in EXPECTED.items()]
write(P('metrics', 'dataset_verification.txt'), '\n'.join(ds) + '\n')

problems = [k for k, v in EXPECTED.items() if measured[k] != v]
if multi or mixed_circuits or prefix_bad:
    problems.append('split contamination')

# ---- feature verification -------------------------------------------------------------------
const_cols = [i for i in range(raw_feats.shape[1]) if raw_feats[:, i].std() == 0]
scaler_nodes = np.array(sorted(set(adj_train.nonzero()[0])))         # exactly what load_data() uses
ref = StandardScaler().fit(raw_feats[scaler_nodes]).transform(raw_feats)
scaler_match = float(np.abs(ref - feat_full).max())
scaler_nodes_outside_train = int(len(set(scaler_nodes.tolist()) - tr_set))
ft = feat_full[tr]
fv = [
    'FEATURE VERIFICATION',
    f'Raw feature matrix shape: {raw_feats.shape}, dtype {raw_feats.dtype}',
    f'Feature count: {raw_feats.shape[1]} (paper Table II: 33; repo column 2 = KEY)',
    f'Constant columns (raw, all nodes): {len(const_cols)} -> {const_cols}',
    f'KEY column (2) unique values: {np.unique(raw_feats[:, 2]).tolist()}',
    'Scaling: graphsaint.utils.load_data fits StandardScaler on nodes that appear in adj_train',
    f'  scaler-fit nodes: {len(scaler_nodes)} (train nodes: {len(tr)}; scaler nodes outside train split: '
    f'{scaler_nodes_outside_train}; train nodes not used for fitting (no train edge): {len(tr_set) - len(scaler_nodes)})',
    f'  max |independent train-only scaler - training input| = {scaler_match:.3e}',
    f'Scaled training-node stats: mean of column means {ft.mean(0).mean():.3e}, '
    f'column std range (non-constant) [{np.delete(ft.std(0), const_cols).min():.4f}, {np.delete(ft.std(0), const_cols).max():.4f}]',
    f'Scaled constant columns are exactly zero: {bool(np.all(feat_full[:, const_cols] == 0))}',
]
write(P('metrics', 'feature_verification.txt'), '\n'.join(fv) + '\n')
if scaler_nodes_outside_train or scaler_match > 1e-4:
    problems.append('scaler not fitted on training nodes only')

gv = [
    'GRAPH VERIFICATION',
    f'adj_full symmetric (undirected): {asym_full == 0} (asymmetric entries: {asym_full})',
    f'adj_train symmetric: {asym_train == 0} (asymmetric entries: {asym_train})',
    f'adj_full nonzeros: {raw_full.nnz}   adj_train nonzeros: {raw_train.nnz}',
    f'Self-loops in adj_full: {self_loops} (parser adds one for gates driving a primary output)',
    f'adj_train entries touching a non-train node: {train_edges_non_train}',
    f'Train/val/test masks disjoint: {len(multi) == 0}',
    f'All nodes assigned to a split: {len(split_of) == raw_feats.shape[0]}',
]
write(P('metrics', 'graph_verification.txt'), '\n'.join(gv) + '\n')
if asym_full or train_edges_non_train or len(split_of) != raw_feats.shape[0]:
    problems.append('graph verification failed')

# =============================================================================================
# MODEL + MINIBATCH (repository code)
# =============================================================================================
t0 = time.time()
model, minibatch, minibatch_eval, model_eval = prepare(train_data, train_params, arch_gcn)
if not G.args_global.cpu_eval:            # same as train(): GPU eval re-uses the training objects
    minibatch_eval = minibatch
T['model_init'] = time.time() - t0

phase = train_phases[0]
assert len(train_phases) == 1, 'TCAD.yml has a single phase'
t0 = time.time()
minibatch.set_sampler(phase)                 # first statement of the repo's phase loop
T['sampler_presample_and_norm'] = time.time() - t0
num_batches = minibatch.num_training_batches()

# ---- GraphSAINT verification ----------------------------------------------------------------
sampler = minibatch.graph_sampler
subg_nodes = minibatch.subgraphs_remaining_nodes[0]
indptr = minibatch.subgraphs_remaining_indptr[0]
indices = minibatch.subgraphs_remaining_indices[0]
eidx = minibatch.subgraphs_remaining_edge_index[0]
sub_adj = raw_train[subg_nodes][:, subg_nodes]
induced_ok = (sub_adj.nnz == len(indices))
eidx_ok = bool(np.all(adj_train.indices[eidx] == subg_nodes[indices]))
nl = to_numpy(minibatch.norm_loss_train) if torch.is_tensor(minibatch.norm_loss_train) else minibatch.norm_loss_train
gsv = [
    'GRAPHSAINT VERIFICATION (live objects after Minibatch.set_sampler)',
    f'TCAD.yml phase: {phase}',
    f'TCAD.yml params: {tcad["params"][0]}',
    f'Sampler method: {minibatch.method_sample}  class {type(sampler).__name__} -> backend {type(sampler.cy_sampler).__module__}.{type(sampler.cy_sampler).__name__}',
    f'Root nodes (size_root): {sampler.cy_sampler.size_root}',
    f'Walk length (size_depth): {sampler.cy_sampler.size_depth}',
    f'Sample coverage: {minibatch.sample_coverage}',
    f'Subgraph node budget per batch (num_root*depth): {minibatch.size_subg_budget}; batches/epoch: {num_batches}',
    f'Sampler node pool == role["tr"]: {np.array_equal(np.sort(sampler.cy_sampler.node_train), np.sort(tr))}',
    'Root sampling: node_train[np.random.randint(0, n, size_root)] -> uniform WITH replacement (source: graphsaint/cython_sampler.py)',
    f'Example subgraph: {len(subg_nodes)} nodes, {len(indices)} edges; all nodes in train split: {set(subg_nodes.tolist()) <= tr_set}',
    f'Induced subgraph check (edge count equals adj_train restricted to sampled nodes): {induced_ok}',
    f'Edge-index mapping into adj_train consistent: {eidx_ok}',
    f'norm_loss_train: zero on val {float(np.abs(nl[va]).sum()) == 0}, zero on test {float(np.abs(nl[te]).sum()) == 0}, '
    f'train min/max {nl[tr].min():.3e}/{nl[tr].max():.3e}',
    f'norm_aggr_train: {np.count_nonzero(minibatch.norm_aggr_train)} nonzero of {minibatch.norm_aggr_train.size} (GraphSAINT alpha)',
    f'Training loss uses only sampled train nodes (sampler pool = train) and labels of those nodes.',
    f'Pre-sampling time: {T["sampler_presample_and_norm"]:.1f}s',
]
write(P('metrics', 'graphsaint_verification.txt'), '\n'.join(gsv) + '\n')
if not (induced_ok and eidx_ok and set(subg_nodes.tolist()) <= tr_set) or minibatch.method_sample != 'rw':
    problems.append('GraphSAINT verification failed')

# ---- architecture ---------------------------------------------------------------------------
n_params = sum(p.numel() for p in model.parameters())
n_train = sum(p.numel() for p in model.parameters() if p.requires_grad)
layer_rows = []
for i, agg in enumerate(model.aggregators):
    layer_rows.append({'layer': i + 1, 'class': type(agg).__name__, 'order': model.order_layer[i],
                       'input_dim': model.dims_weight[i][0], 'weight_out_dim': model.dims_weight[i][1],
                       'output_dim': model.dims_feat[i + 1], 'heads': getattr(agg, 'mulhead', 1),
                       'aggregation': model.aggr_layer[i], 'activation': model.act_layer[i], 'bias_mode': model.bias_layer[i],
                       'params': sum(p.numel() for p in agg.parameters())})
layer_rows.append({'layer': len(model.aggregators) + 1, 'class': type(model.classifier).__name__ + ' (classifier)',
                   'order': 0, 'input_dim': model.dims_feat[-1], 'weight_out_dim': model.num_classes,
                   'output_dim': model.num_classes, 'heads': 1, 'aggregation': 'n/a', 'activation': 'I (softmax in loss)',
                   'bias_mode': 'bias', 'params': sum(p.numel() for p in model.classifier.parameters())})
arch_txt = [
    'MODEL ARCHITECTURE (instantiated object, not inferred from TCAD.yml)',
    f'TCAD.yml network: {tcad["network"][0]}',
    f'aggregator_cls: {model.aggregator_cls.__name__}   mulhead: {model.mulhead}',
    f'order_layer {model.order_layer}  dims_feat {model.dims_feat}  dims_weight {model.dims_weight}',
    'Forward: conv_layers -> F.normalize(p=2, dim=1) -> classifier -> softmax (in loss / predict)',
    f'Loss: {"sigmoid BCE" if model.sigmoid_loss else "softmax cross-entropy weighted by GraphSAINT norm_loss"}',
    f'Optimizer: {type(model.optimizer).__name__} lr={model.optimizer.param_groups[0]["lr"]}  '
    f'weight_decay(unused by optimizer)={model.weight_decay}  dropout={model.dropout}  grad-clip-norm=5',
    '',
    '| Layer | Class | Order | Input | Weight out | Output | Heads | Aggr | Act | Params |',
    '|---|---|---|---|---|---|---|---|---|---|',
] + [f'| {r["layer"]} | {r["class"]} | {r["order"]} | {r["input_dim"]} | {r["weight_out_dim"]} | {r["output_dim"]} | '
     f'{r["heads"]} | {r["aggregation"]} | {r["activation"]} | {r["params"]} |' for r in layer_rows] + [
    '',
    f'Total parameters: {n_params}   Trainable: {n_train}',
    '',
    'Full module print:',
    str(model),
]
write(P('metrics', 'model_architecture.txt'), '\n'.join(arch_txt) + '\n')
with open(P('metrics', 'model_architecture.json'), 'w') as f:
    json.dump({'layers': layer_rows, 'total_params': n_params, 'trainable_params': n_train}, f, indent=2)

# ---- preflight summary ----------------------------------------------------------------------
pre = f"""==================================================
GNN-RE BASELINE RERUN PREFLIGHT
==================================================
Dataset: Interconnected-Modules ({DATA_DIR})
Nodes: {measured['nodes']}
Train: {measured['train']}
Validation: {measured['val']}
Test: {measured['test']}
Features: {raw_feats.shape[1]}
Classes: {measured['classes']}

Sampler: {minibatch.method_sample}
Walk length: {sampler.cy_sampler.size_depth}
Root nodes: {sampler.cy_sampler.size_root}
Coverage: {minibatch.sample_coverage}

Architecture: {model.aggregator_cls.__name__} x{len(model.aggregators)} + classifier
Attention heads: {model.mulhead}
Hidden dimension: {tcad['network'][0]['dim']}
Arch: {tcad['network'][0]['arch']}

Optimizer: {type(model.optimizer).__name__}
Learning rate: {model.optimizer.param_groups[0]['lr']}
Dropout: {model.dropout}
Epochs: {phase['end']}

Seed: {SEED}
Device: {device} ({gpu_name})

TCAD.yml:
{YML}  (sha256 {sha256(YML)})

Git commit:
GNN-RE {commits['GNN-RE (authors repo)']} | GraphSAINT {commits['GraphSAINT (upstream clone)']}
Problems found: {problems if problems else 'none'}
=================================================="""
log(pre)
write(P('logs', 'preflight.txt'), pre + '\n')

released = (tcad['network'][0] == {'dim': 256, 'aggr': 'concat', 'loss': 'softmax', 'arch': '1-1-0', 'act': 'relu',
                                    'attention': 8, 'bias': 'norm'}
            and tcad['params'][0] == {'lr': 0.01, 'dropout': 0.1, 'weight_decay': 0.0, 'sample_coverage': 50}
            and phase == {'end': 2000, 'sampler': 'rw', 'depth': 2, 'num_root': 3000})
log(f'Is this the authors\' released configuration without algorithmic modifications? {"YES" if released and not problems else "NO"}')
if problems or not released:
    log('STOPPING before training:', problems or 'TCAD.yml differs from the released configuration')
    sys.exit(2)
if opts.preflight_only:
    log('Preflight only: not training.')
    sys.exit(0)

# =============================================================================================
# TRAINING (mirrors graphsaint/pytorch_version/train.py::train)
# =============================================================================================
ckpt = P('checkpoints', 'best_model.pkl')
ckpt_meta = P('checkpoints', 'best_model_meta.json')
f1mic_best, ep_best, best_meta = 0, -1, None
time_train = 0.0
history = []
last = None
eval_val_every = train_params['eval_val_every']
end_ep = int(phase['end'])
T['train_start'] = time.time()
log(f'Training start: {datetime.datetime.now().isoformat(timespec="seconds")}  batches/epoch={num_batches}  eval_val_every={eval_val_every}')
try:
    for e in range(0, end_ep):
        t_ep = time.time()
        minibatch.shuffle()
        losses = []
        time_train_ep = 0.0
        while not minibatch.end():
            t1 = time.time()
            loss_train, preds_train, labels_train = model.train_step(*minibatch.one_batch(mode='train'))
            time_train_ep += time.time() - t1
            losses.append(float(loss_train))
        rec = {'epoch': e + 1, 'train_loss': float(np.mean(losses)), 'batches': len(losses)}
        if (e + 1) % eval_val_every == 0:
            # == evaluate_full_batch(model, minibatch, mode='val') plus accuracy from the same predictions
            loss_val, preds_v, labels_v = model.eval_step(*minibatch.one_batch(mode='val'))
            nv = minibatch.node_val
            f1mic_val, f1mac_val = calc_f1(to_numpy(labels_v[nv]), to_numpy(preds_v[nv]), model.sigmoid_loss)
            acc_val = accuracy_score(to_numpy(labels_v[nv]).argmax(1), to_numpy(preds_v[nv]).argmax(1))
            rec.update(val_loss=float(loss_val), val_acc=float(acc_val), val_micro=float(f1mic_val), val_macro=float(f1mac_val))
            best = f1mic_val > f1mic_best
            if best:
                f1mic_best, ep_best = f1mic_val, e
                torch.save(model.state_dict(), ckpt)
                best_meta = {'best_epoch': e + 1, 'best_epoch_index0': e, 'val_micro': float(f1mic_val),
                             'val_acc': float(acc_val), 'val_macro': float(f1mac_val), 'val_loss': float(loss_val),
                             'saved_at': datetime.datetime.now().isoformat(timespec='seconds'),
                             'train_seconds_so_far': time_train + time_train_ep, 'checkpoint': ckpt}
                with open(ckpt_meta, 'w') as f:
                    json.dump(best_meta, f, indent=2)
            rec['best'] = bool(best)
        time_train += time_train_ep
        rec.update(lr=model.optimizer.param_groups[0]['lr'], epoch_time=time.time() - t_ep,
                   train_step_time=time_train_ep, total_time=time.time() - T['train_start'])
        history.append(rec)
        last = rec
        log(f"Epoch {e + 1:04d}/{end_ep} | Train Loss: {rec['train_loss']:.4f} | Val Loss: {rec.get('val_loss', float('nan')):.4f} | "
            f"Val Accuracy: {rec.get('val_acc', float('nan')):.4f} | Val Micro-F1: {rec.get('val_micro', float('nan')):.4f} | "
            f"Val Macro-F1: {rec.get('val_macro', float('nan')):.4f} | LR: {rec['lr']:g} | Epoch Time: {rec['epoch_time']:.2f}s | "
            f"Total Time: {rec['total_time']:.1f}s | BEST: {'YES' if rec.get('best') else 'NO'}")
        if (e + 1) % 100 == 0:
            gpu_snapshot(f'epoch {e + 1}')
            with open(P('metrics', 'training_history.json'), 'w') as f:
                json.dump(history, f)
except BaseException as exc:  # noqa: BLE001  (includes KeyboardInterrupt)
    write(P('logs', 'error.log'),
          f'Training failed at epoch {len(history) + 1}\nException: {exc!r}\n\n{traceback.format_exc()}\n'
          f'Last successful epoch: {last["epoch"] if last else None}\nLast metrics: {json.dumps(last)}\n'
          f'Best checkpoint available: {os.path.exists(ckpt)} {json.dumps(best_meta)}\n'
          'No automatic restart was attempted.\n')
    with open(P('metrics', 'training_history.json'), 'w') as f:
        json.dump(history, f)
    log('TRAINING FAILED - see logs/error.log')
    raise
T['train_end'] = time.time()
T['training'] = T['train_end'] - T['train_start']
with open(P('metrics', 'training_history.json'), 'w') as f:
    json.dump(history, f)
log(f'Optimization finished. Final training epoch: {len(history)}. Best epoch: {ep_best + 1}, val Micro-F1 {f1mic_best:.6f}')
gpu_snapshot('end of training')

# =============================================================================================
# RESTORE BEST CHECKPOINT, THEN AND ONLY THEN EVALUATE
# =============================================================================================
t0 = time.time()
assert ep_best >= 0 and os.path.exists(ckpt), 'no best checkpoint was saved'
with open(ckpt_meta) as f:
    meta_disk = json.load(f)
model.load_state_dict(torch.load(ckpt))                     # same as train(): model.load_state_dict(torch.load(path_saver))
integrity = [f'Checkpoint loaded: {ckpt}',
             f'Recorded best epoch (in memory): {ep_best + 1}; in checkpoint metadata: {meta_disk["best_epoch"]}; match: {meta_disk["best_epoch"] == ep_best + 1}']


def full_eval():
    loss, preds, labels = model.eval_step(*minibatch_eval.one_batch(mode='valtest'))
    return float(loss), to_numpy(preds), to_numpy(labels)


loss1, probs1, labels1 = full_eval()
mode_after = model.training
dropout_modules = [m for m in model.modules() if isinstance(m, torch.nn.Dropout)]
loss2, probs2, labels2 = full_eval()
pred1, pred2 = probs1.argmax(1), probs2.argmax(1)
nv, nt = minibatch_eval.node_val, minibatch_eval.node_test
val_micro_reload = f1_score(labels1[nv].argmax(1), pred1[nv], average='micro')
integrity += [
    f'Model in eval mode after eval_step (model.training == False): {not mode_after}',
    f'Dropout modules: {len(dropout_modules)}, all inactive in eval mode: {not any(m.training for m in dropout_modules)}',
    'Gradients disabled: eval_step wraps the forward pass in torch.no_grad() (repository code)',
    f'Determinism: predictions run1 == run2 on all nodes: {bool(np.array_equal(pred1, pred2))}; '
    f'max |prob1 - prob2| = {float(np.abs(probs1 - probs2).max()):.3e}',
    f'Validation Micro-F1 after reload: {val_micro_reload:.6f}; recorded at best epoch: {meta_disk["val_micro"]:.6f}; '
    f'difference {val_micro_reload - meta_disk["val_micro"]:+.2e}',
]
write(P('metrics', 'checkpoint_integrity.txt'), '\n'.join(integrity) + '\n')
for line in integrity:
    log(line)

y_true, y_pred = labels1[nt].argmax(1), pred1[nt]
f1mic_repo, f1mac_repo = calc_f1(labels1[nt], probs1[nt], False)
acc = accuracy_score(y_true, y_pred)
mic = f1_score(y_true, y_pred, average='micro')
mac = f1_score(y_true, y_pred, average='macro')
pr, rc, f1c, sup = precision_recall_fscore_support(y_true, y_pred, labels=range(5), zero_division=0)
cm = confusion_matrix(y_true, y_pred, labels=range(5))
errors = int(len(y_true) - np.trace(cm))
T['final_eval'] = time.time() - t0

with open(P('predictions', 'test_predictions.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['node_id', 'circuit_id', 'true_label', 'true_class', 'predicted_label', 'predicted_class', 'correct']
               + [f'prob_{i}_{n}' for i, n in enumerate(CLASS_NAMES)])
    for n in nt:
        t_, p_ = int(labels1[n].argmax()), int(pred1[n])
        w.writerow([int(n), node_circuit.get(int(n), ''), t_, CLASS_NAMES[t_], p_, CLASS_NAMES[p_], int(t_ == p_)]
                   + [f'{v:.6f}' for v in probs1[n]])

with open(P('metrics', 'confusion_matrix.csv'), 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['true\\pred'] + CLASS_NAMES)
    for i, n in enumerate(CLASS_NAMES):
        w.writerow([n] + cm[i].tolist())
with open(P('metrics', 'per_class_metrics.csv'), 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['class', 'precision', 'recall', 'f1', 'support'])
    for i, n in enumerate(CLASS_NAMES):
        w.writerow([n, f'{pr[i] * 100:.2f}', f'{rc[i] * 100:.2f}', f'{f1c[i] * 100:.2f}', int(sup[i])])

durations = [h['epoch_time'] for h in history]
final = {
    'experiment_dir': EXP, 'seed': SEED, 'device': device, 'gpu': gpu_name,
    'best_epoch': ep_best + 1, 'final_training_epoch': len(history),
    'best_val_micro': float(f1mic_best), 'best_val_acc': meta_disk['val_acc'], 'best_val_macro': meta_disk['val_macro'],
    'test_accuracy': float(acc), 'test_micro_f1': float(mic), 'test_macro_f1': float(mac),
    'test_micro_f1_repo_calc_f1': float(f1mic_repo), 'test_macro_f1_repo_calc_f1': float(f1mac_repo),
    'test_nodes': int(len(y_true)), 'test_errors': errors, 'test_error_pct': errors / len(y_true) * 100,
    'per_class': {n: {'precision': float(pr[i]), 'recall': float(rc[i]), 'f1': float(f1c[i]), 'support': int(sup[i])}
                  for i, n in enumerate(CLASS_NAMES)},
    'confusion_matrix': cm.tolist(), 'class_order': CLASS_NAMES,
    'timing_seconds': {'data_loading': T['data_loading'], 'model_init': T['model_init'],
                       'sampler_presample_and_norm': T['sampler_presample_and_norm'],
                       'training_wall': T['training'], 'training_step_time_only': time_train,
                       'avg_epoch': float(np.mean(durations)), 'time_to_best_epoch': history[ep_best]['total_time'],
                       'final_eval': T['final_eval']},
    'train_start': datetime.datetime.fromtimestamp(T['train_start']).isoformat(timespec='seconds'),
    'train_end': datetime.datetime.fromtimestamp(T['train_end']).isoformat(timespec='seconds'),
    'checkpoint': ckpt, 'predictions': P('predictions', 'test_predictions.csv'),
}
with open(P('metrics', 'final_metrics.json'), 'w') as f:
    json.dump(final, f, indent=2)
write(P('metrics', 'best_checkpoint.txt'),
      f'Best epoch: {ep_best + 1}\nBest validation Micro-F1: {f1mic_best:.6f}\nBest validation accuracy: {meta_disk["val_acc"]:.6f}\n'
      f'Best validation Macro-F1: {meta_disk["val_macro"]:.6f}\nCheckpoint path: {ckpt}\nFinal training epoch: {len(history)}\n'
      f'Checkpoint saved at: {meta_disk["saved_at"]}\n')
txt = [f'Test nodes: {len(y_true)}', f'Accuracy: {acc * 100:.2f}%', f'Micro-F1: {mic * 100:.2f}%',
       f'Macro-F1: {mac * 100:.2f}%', f'(repo calc_f1 cross-check: micro {f1mic_repo * 100:.2f}%, macro {f1mac_repo * 100:.2f}%)',
       f'Errors: {errors} ({errors / len(y_true) * 100:.2f}%)', '', 'Per class (P / R / F1 / support):'] + \
      [f'  {n}: {pr[i] * 100:.2f} / {rc[i] * 100:.2f} / {f1c[i] * 100:.2f} / {int(sup[i])}' for i, n in enumerate(CLASS_NAMES)]
write(P('metrics', 'final_metrics.txt'), '\n'.join(txt) + '\n')
for line in txt:
    log(line)
log(f'Training wall time: {T["training"]:.1f}s; final eval {T["final_eval"]:.1f}s')
gpu_snapshot('end')
log('DONE')
