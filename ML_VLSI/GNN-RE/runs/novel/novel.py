"""
GNN-RE-inspired novel model: depth-aware, structure-fingerprinted multi-hop GBDT + module-coherence smoothing.

Novel components (all label-free, computed from the netlist graph only):
  PE  - logic-depth positional encoding: hop distance from each gate to the nearest PI-driven and
        PO-driving gate, raw and normalised by its circuit's depth, plus relative pipeline position.
  ST  - structural fingerprints: degree, triangles, clustering, 2-hop reach, neighbour-degree stats.
  HOP - multi-hop propagated features [A_rw^k X], [A_sym^k X] (SIGN-style) over base + PE + ST.
  SM  - module-coherence smoothing: P <- (1-a) P0 + a * A_rw P, iterated, at inference time.

Model selection uses ONLY training/validation circuits (bit-width cross-validation):
  fold w32 : train on train circuits except 32-bit, early-stop on official val, score 32-bit train circuits
  fold w64 : same with 64-bit
  fold val : train on train circuits except 32-bit, early-stop on 32-bit, score official val circuits
Score = mean over folds of (accuracy + macro-F1) / 2. The test split is touched only by `final`.

  python novel.py cv     --out <dir>             # sweep configs + smoothing on the CV folds
  python novel.py final  --out <dir> --cfg NAME --alpha A --iters T --seeds 5
"""
import argparse
import json
import os
import re
import time

import lightgbm as lgb
import numpy as np
import scipy.sparse as sp
from scipy.sparse.csgraph import connected_components, dijkstra
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support
from sklearn.preprocessing import StandardScaler

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', '..', 'Netlist_to_graph', 'Graphs_datasets', 'Interconnected-Modules')
CLASSES = ['ADD', 'MUL', 'CTRL', 'SUB', 'COMP']


# ------------------------------------------------------------------------------------------------
# data
# ------------------------------------------------------------------------------------------------
def load():
    feats = np.load(os.path.join(DATA, 'feats.npy')).astype(np.float64)
    A = sp.load_npz(os.path.join(DATA, 'adj_full.npz')).astype(np.float64).tocsr()
    role = json.load(open(os.path.join(DATA, 'role.json')))
    cm = {int(k): v for k, v in json.load(open(os.path.join(DATA, 'class_map.json'))).items()}
    y = np.zeros(len(cm), dtype=int)
    for k, v in cm.items():
        y[k] = int(np.argmax(v)) if isinstance(v, list) else int(v)
    circ = np.empty(len(y), dtype=object)
    with open(os.path.join(DATA, 'cell.txt'), encoding='utf-8', errors='replace') as f:
        for line in f:
            nid, rest = line.split(' ', 1)
            circ[int(nid)] = rest.rsplit(' from file ', 1)[1].strip()
    bits = np.array([int(re.search(r'_(\d+)_bit', c).group(1)) for c in circ])
    split = {k: np.array(v) for k, v in role.items()}
    return feats, A, y, circ, bits, split


def norm_adj(A):
    A = A.copy()
    A.setdiag(1.0)
    A.eliminate_zeros()
    d = np.asarray(A.sum(1)).ravel()
    rw = sp.diags(1.0 / d) @ A
    s = sp.diags(1.0 / np.sqrt(d))
    return rw.tocsr(), (s @ A @ s).tocsr()


def depth_pe(A, feats):
    """Hop distance to nearest PI-driven / PO-driving gate, per-circuit normalised."""
    G = A.copy()
    G.setdiag(0)
    G.eliminate_zeros()
    G.data[:] = 1.0
    n_comp, comp = connected_components(G, directed=False)
    out = []
    for col in (0, 1):                         # column 0 = PI flag, column 1 = PO flag (parser order)
        src = np.where(feats[:, col] > 0)[0]
        d = dijkstra(G, directed=False, indices=src, unweighted=True, min_only=True)
        big = ~np.isfinite(d)
        d[big] = np.nan
        cmax = np.zeros(n_comp)
        np.maximum.at(cmax, comp[~big], d[~big])
        dn = d / np.maximum(cmax[comp], 1)
        d = np.nan_to_num(d, nan=-1.0)
        dn = np.nan_to_num(dn, nan=-1.0)
        out += [d, dn, np.log1p(np.maximum(cmax[comp], 0))]
    dpi, dpo = out[0], out[3]
    rel = np.where((dpi >= 0) & (dpo >= 0), dpi / np.maximum(dpi + dpo, 1), -1.0)
    size = np.bincount(comp)[comp]
    return np.column_stack(out + [rel, np.log(size)]), comp


def structure(A):
    G = A.copy()
    G.setdiag(0)
    G.eliminate_zeros()
    G.data[:] = 1.0
    deg = np.asarray(G.sum(1)).ravel()
    G2 = (G @ G).tocsr()
    tri = np.asarray(G2.multiply(G).sum(1)).ravel() / 2.0
    clus = tri / np.maximum(deg * (deg - 1) / 2.0, 1)
    reach2 = np.diff((G2 + G).tocsr().indptr).astype(float)   # nodes within 2 hops (incl. self via G2 diag)
    nd_mean = (G @ deg) / np.maximum(deg, 1)
    nd_max = np.zeros_like(deg)
    for i in range(G.shape[0]):
        a, b = G.indptr[i], G.indptr[i + 1]
        if b > a:
            nd_max[i] = deg[G.indices[a:b]].max()
    sq = np.asarray(G2.multiply(G2).sum(1)).ravel()            # 2-path multiplicity: array-like regularity
    return np.column_stack([np.log1p(deg), np.log1p(tri), clus, np.log1p(reach2), np.log1p(nd_mean),
                            np.log1p(nd_max), np.log1p(sq)])


def build(cfg, feats, A, split, cache):
    key = json.dumps(cfg, sort_keys=True)
    if key in cache:
        return cache[key]
    tr = split['tr']
    keep = feats[tr].std(0) > 0
    base = [feats[:, keep]]
    if cfg.get('pe'):
        base.append(cache['pe'])
    if cfg.get('st'):
        base.append(cache['st'])
    if cfg.get('sim'):
        base.append(cache['sim'])
    if cfg.get('fn'):
        base.append(cache['fn'])
    X0 = np.hstack(base)
    X0 = StandardScaler().fit(X0[tr]).transform(X0)              # fitted on training nodes only
    rw, sym = cache['rw'], cache['sym']
    blocks, cur = [X0], X0
    for _ in range(cfg['hops']):
        cur = rw @ cur
        blocks.append(cur)
    cur = X0
    for _ in range(cfg['sym']):
        cur = sym @ cur
        blocks.append(cur)
    for M in ((cache['din'], cache['dout']) if cfg.get('dir') else ()):
        cur = X0
        for _ in range(cfg['dir']):                               # direction-aware: fan-in / fan-out only
            cur = M @ cur
            blocks.append(cur)
    X = np.hstack(blocks).astype(np.float32)
    cache[key] = X
    return X


# ------------------------------------------------------------------------------------------------
# model
# ------------------------------------------------------------------------------------------------
def fit_predict(X, y, fit_idx, es_idx, pred_idx, seed, cw_power=1.0):
    counts = np.bincount(y[fit_idx], minlength=5).astype(float)
    cw = (counts.sum() / np.maximum(counts, 1)) ** cw_power
    cw = cw / cw[y[fit_idx]].mean()
    params = dict(objective='multiclass', num_class=5, learning_rate=0.05, num_leaves=63,
                  feature_fraction=0.8, bagging_fraction=0.9, bagging_freq=1, min_data_in_leaf=20,
                  lambda_l2=1.0, seed=seed, num_threads=16, verbose=-1)
    dtr = lgb.Dataset(X[fit_idx], y[fit_idx], weight=cw[y[fit_idx]])
    dva = lgb.Dataset(X[es_idx], y[es_idx], reference=dtr)
    bst = lgb.train(params, dtr, 3000, valid_sets=[dva], callbacks=[lgb.early_stopping(200, verbose=False)])
    return bst.predict(X[pred_idx], num_iteration=bst.best_iteration), bst.best_iteration


def smooth(P_nodes, nodes, rw, alpha, iters):
    """Module-coherence smoothing restricted to the evaluated nodes' graph (circuits are disconnected)."""
    if alpha <= 0 or iters <= 0:
        return P_nodes
    sub = rw[nodes][:, nodes]
    d = np.asarray(sub.sum(1)).ravel()
    sub = sp.diags(1.0 / np.maximum(d, 1e-12)) @ sub
    P0, P = P_nodes, P_nodes
    for _ in range(iters):
        P = (1 - alpha) * P0 + alpha * (sub @ P)
    return P


def score(y_true, P):
    p = P.argmax(1)
    acc, mac = accuracy_score(y_true, p), f1_score(y_true, p, average='macro')
    return acc, mac, (acc + mac) / 2


def folds(y, bits, split):
    tr, va = split['tr'], split['va']
    w32, w64 = tr[bits[tr] == 32], tr[bits[tr] == 64]
    return {
        'w32': (tr[bits[tr] != 32], va, w32),
        'w64': (tr[bits[tr] != 64], va, w64),
        'val': (tr[bits[tr] != 32], w32, va),
    }


CONFIGS = {
    'base_h3s3': {'hops': 3, 'sym': 3},
    'pe_h3s3': {'hops': 3, 'sym': 3, 'pe': 1},
    'st_h3s3': {'hops': 3, 'sym': 3, 'st': 1},
    'pest_h3s3': {'hops': 3, 'sym': 3, 'pe': 1, 'st': 1},
    'pest_h4s3': {'hops': 4, 'sym': 3, 'pe': 1, 'st': 1},
    'pest_h6s3': {'hops': 6, 'sym': 3, 'pe': 1, 'st': 1},
    'sim_h3s3': {'hops': 3, 'sym': 3, 'sim': 1},
    'pestsim_h3s3': {'hops': 3, 'sym': 3, 'pe': 1, 'st': 1, 'sim': 1},
    'pestsim_h2s2': {'hops': 2, 'sym': 2, 'pe': 1, 'st': 1, 'sim': 1},
    'pestsim_h1s1': {'hops': 1, 'sym': 1, 'pe': 1, 'st': 1, 'sim': 1},
    # round 3: Boolean-influence / input-bus features (sim2.py) and direction-aware propagation
    'fn_h2s2': {'hops': 2, 'sym': 2, 'pe': 1, 'st': 1, 'sim': 1, 'fn': 1},
    'dir_h2s2': {'hops': 2, 'sym': 2, 'pe': 1, 'st': 1, 'sim': 1, 'dir': 2},
    'fndir_h2s2': {'hops': 2, 'sym': 2, 'pe': 1, 'st': 1, 'sim': 1, 'fn': 1, 'dir': 2},
    'fndir1_h2s2': {'hops': 2, 'sym': 2, 'pe': 1, 'st': 1, 'sim': 1, 'fn': 1, 'dir': 1},
    'fndir3_h2s2': {'hops': 2, 'sym': 2, 'pe': 1, 'st': 1, 'sim': 1, 'fn': 1, 'dir': 3},
    'fndir_h1s1': {'hops': 1, 'sym': 1, 'pe': 1, 'st': 1, 'sim': 1, 'fn': 1, 'dir': 2},
    'fndir_h3s3': {'hops': 3, 'sym': 3, 'pe': 1, 'st': 1, 'sim': 1, 'fn': 1, 'dir': 2},
}
SMOOTH = [(0.0, 0)] + [(a, t) for a in (0.2, 0.4, 0.6, 0.8) for t in (2, 5, 10)]


def prepare_cache(feats, A):
    t = time.time()
    rw, sym = norm_adj(A)
    pe, comp = depth_pe(A, feats)
    st = structure(A)
    print(f'graph features built in {time.time() - t:.1f}s; PE {pe.shape}, ST {st.shape}', flush=True)
    sim = np.load(os.path.join(HERE, 'sim_feats.npy')).astype(np.float64)   # from sim.py (label-free)
    c = {'rw': rw, 'sym': sym, 'pe': pe, 'st': st, 'comp': comp, 'sim': sim}
    if os.path.exists(os.path.join(HERE, 'sim2_feats.npy')):                  # from sim2.py (label-free)
        c['fn'] = np.load(os.path.join(HERE, 'sim2_feats.npy')).astype(np.float64)
        e = np.load(os.path.join(HERE, 'sim2_edges.npy'))
        n = A.shape[0]
        D = sp.csr_matrix((np.ones(len(e)), (e[:, 1], e[:, 0])), shape=(n, n))   # row i <- its drivers
        D.data[:] = 1.0
        for name, M in (('din', D), ('dout', D.T.tocsr())):
            d = np.asarray(M.sum(1)).ravel()
            c[name] = (sp.diags(1.0 / np.maximum(d, 1)) @ M).tocsr()
    return c


def run_cv(out, only=None, cv_seeds=1):
    feats, A, y, circ, bits, split = load()
    cache = prepare_cache(feats, A)
    F = folds(y, bits, split)
    log = open(os.path.join(out, 'cv_log.tsv'), 'a')
    results = {}
    for name, cfg in CONFIGS.items():
        if only and name not in only:
            continue
        X = build(cfg, feats, A, split, cache)
        fold_P = {}
        for fn, (fit, es, ev) in F.items():
            t = time.time()
            runs = [fit_predict(X, y, fit, es, ev, seed=s) for s in range(cv_seeds)]
            P, it = np.mean([r[0] for r in runs], 0), [r[1] for r in runs]
            fold_P[fn] = (ev, P)
            print(f'{name} {fn}: iters {it} {score(y[ev], P)} ({time.time() - t:.0f}s)', flush=True)
        for a, t_ in SMOOTH:
            s = [score(y[ev], smooth(P, ev, cache['rw'], a, t_)) for ev, P in fold_P.values()]
            mean = float(np.mean([v[2] for v in s]))
            results[f'{name}|a={a}|t={t_}'] = {'mean_score': mean, 'folds': {k: v for k, v in zip(F, s)}}
            log.write(f'{name}\t{a}\t{t_}\t{mean:.5f}\t' + '\t'.join(f'{v[0]:.4f}/{v[1]:.4f}' for v in s) + '\n')
            log.flush()
        best = max((k for k in results if k.startswith(name + '|')), key=lambda k: results[k]['mean_score'])
        print(f'== {name}: no-smooth {results[name + "|a=0.0|t=0"]["mean_score"]:.5f}  best {best} '
              f'{results[best]["mean_score"]:.5f}', flush=True)
    json.dump(results, open(os.path.join(out, 'cv_results.json'), 'w'), indent=1)
    ranked = sorted(results.items(), key=lambda kv: -kv[1]['mean_score'])
    print('TOP 10 (CV only, test untouched):')
    for k, v in ranked[:10]:
        print(f'  {v["mean_score"]:.5f}  {k}')


def run_final(out, cfg_name, alpha, iters, seeds):
    feats, A, y, circ, bits, split = load()
    cache = prepare_cache(feats, A)
    X = build(CONFIGS[cfg_name], feats, A, split, cache)
    tr, va, te = split['tr'], split['va'], split['te']
    Ps, iters_used = [], []
    for s in range(seeds):
        P, it = fit_predict(X, y, tr, va, np.concatenate([va, te]), seed=s)
        Ps.append(P)
        iters_used.append(it)
        print(f'seed {s}: best_iter {it}', flush=True)
    P = np.mean(Ps, 0)
    Pva, Pte = P[:len(va)], P[len(va):]
    res = {'config': CONFIGS[cfg_name], 'cfg_name': cfg_name, 'alpha': alpha, 'iters': iters, 'seeds': seeds,
           'best_iterations': iters_used}
    for tag, a, t in (('raw', 0, 0), ('smoothed', alpha, iters)):
        Sva, Ste = smooth(Pva, va, cache['rw'], a, t), smooth(Pte, te, cache['rw'], a, t)
        pt = Ste.argmax(1)
        pr, rc, f1c, sup = precision_recall_fscore_support(y[te], pt, labels=range(5), zero_division=0)
        res[tag] = {
            'val': dict(zip(('accuracy', 'macro_f1', 'score'), score(y[va], Sva))),
            'test': {'accuracy': accuracy_score(y[te], pt), 'micro_f1': f1_score(y[te], pt, average='micro'),
                     'macro_f1': f1_score(y[te], pt, average='macro'), 'errors': int((pt != y[te]).sum()),
                     'per_class': {c: {'precision': pr[i], 'recall': rc[i], 'f1': f1c[i], 'support': int(sup[i])}
                                   for i, c in enumerate(CLASSES)},
                     'confusion_matrix': confusion_matrix(y[te], pt, labels=range(5)).tolist()},
        }
        np.save(os.path.join(out, f'test_probs_{tag}.npy'), Ste)
    json.dump(res, open(os.path.join(out, 'final_metrics.json'), 'w'), indent=2, default=float)
    np.save(os.path.join(out, 'test_node_ids.npy'), te)
    print(json.dumps({k: res[k]['test'] if isinstance(res[k], dict) and 'test' in res[k] else res[k]
                      for k in ('raw', 'smoothed')}, indent=1, default=float))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['cv', 'final'])
    ap.add_argument('--out', required=True)
    ap.add_argument('--cfg')
    ap.add_argument('--alpha', type=float, default=0.0)
    ap.add_argument('--iters', type=int, default=0)
    ap.add_argument('--seeds', type=int, default=5)
    ap.add_argument('--only', nargs='*')
    ap.add_argument('--cv_seeds', type=int, default=1)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    if a.mode == 'cv':
        run_cv(a.out, a.only, a.cv_seeds)
    else:
        run_final(a.out, a.cfg, a.alpha, a.iters, a.seeds)
