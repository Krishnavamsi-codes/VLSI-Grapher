"""
Logic-simulation fingerprints for every gate of the Interconnected-Modules netlists (label-free).

For each circuit: parse with ML_VLSI's netlist_graph_engine (cell types + pin connectivity only; instance
and hierarchy names are NEVER used as features because they contain the module name = the label),
simulate 2048 random primary-input vectors bit-parallel, and derive per-gate features:

  signal probability of each output (main / carry), output entropy
  signed correlation with primary inputs: max|r|, mean|r|, mean signed r over |r|>0.05, fraction
  of positive among those, count of strongly correlated PIs (normalised)
  transitive fan-in cone size (#PIs in support, normalised), fan-out cone size (#POs reachable)
  directed logic level from PIs and to POs (raw + normalised by circuit depth)

Output: sim_feats.npy (N x F, aligned with dataset node ids) + sim_feats_meta.json.
Run with the ML_VLSI .venv python (needs netlist_graph_engine).
"""
import json
import os
import re
import sys
import time
from collections import defaultdict, deque

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ML = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, ML)
import netlist_graph_engine as NGE  # noqa: E402

GNNRE = os.path.join(ML, 'GNN-RE')
CIRC = os.path.join(GNNRE, 'Netlist_to_graph', 'Circuits_datasets', 'Interconnected-Modules')
DATA = os.path.join(GNNRE, 'Netlist_to_graph', 'Graphs_datasets', 'Interconnected-Modules')
W = 32                       # 32 x 64 = 2048 random patterns
NPAT = W * 64
rng = np.random.default_rng(12345)
ONES = np.full(W, np.uint64(0xFFFFFFFFFFFFFFFF))


def fam(cell):
    return re.sub(r'_X\w*$', '', cell)


def N(x):
    return ~x


def AND(*a):
    r = a[0]
    for x in a[1:]:
        r = r & x
    return r


def OR(*a):
    r = a[0]
    for x in a[1:]:
        r = r | x
    return r


def XOR(*a):
    r = a[0]
    for x in a[1:]:
        r = r ^ x
    return r


def MAJ(a, b, c):
    return (a & b) | (a & c) | (b & c)


# Standard (ARM Artisan-style) cell semantics; trailing N on a pin = active-low input.
FUNCS = {
    'ADDF': lambda p: {'S': XOR(p['A'], p['B'], p['CI']), 'CO': MAJ(p['A'], p['B'], p['CI'])},
    'ADDH': lambda p: {'S': XOR(p['A'], p['B']), 'CO': AND(p['A'], p['B'])},
    'AND2': lambda p: {'Y': AND(p['A'], p['B'])},
    'AND3': lambda p: {'Y': AND(p['A'], p['B'], p['C'])},
    'AO1B2': lambda p: {'Y': OR(N(p['A0N']), AND(p['B0'], p['B1']))},
    'AO21': lambda p: {'Y': OR(AND(p['A0'], p['A1']), p['B0'])},
    'AO21B': lambda p: {'Y': OR(AND(p['A0'], p['A1']), N(p['B0N']))},
    'AO22': lambda p: {'Y': OR(AND(p['A0'], p['A1']), AND(p['B0'], p['B1']))},
    'AOI21': lambda p: {'Y': N(OR(AND(p['A0'], p['A1']), p['B0']))},
    'AOI211': lambda p: {'Y': N(OR(AND(p['A0'], p['A1']), p['B0'], p['C0']))},
    'AOI21B': lambda p: {'Y': N(OR(AND(p['A0'], p['A1']), N(p['B0N'])))},
    'AOI22': lambda p: {'Y': N(OR(AND(p['A0'], p['A1']), AND(p['B0'], p['B1'])))},
    'AOI221': lambda p: {'Y': N(OR(AND(p['A0'], p['A1']), AND(p['B0'], p['B1']), p['C0']))},
    'AOI222': lambda p: {'Y': N(OR(AND(p['A0'], p['A1']), AND(p['B0'], p['B1']), AND(p['C0'], p['C1'])))},
    'AOI2XB1': lambda p: {'Y': N(OR(AND(p['A0'], N(p['A1N'])), p['B0']))},
    'AOI31': lambda p: {'Y': N(OR(AND(p['A0'], p['A1'], p['A2']), p['B0']))},
    'AOI32': lambda p: {'Y': N(OR(AND(p['A0'], p['A1'], p['A2']), AND(p['B0'], p['B1'])))},
    'BUF': lambda p: {'Y': p['A']},
    'BUFH': lambda p: {'Y': p['A']},
    'INV': lambda p: {'Y': N(p['A'])},
    'MX2': lambda p: {'Y': OR(AND(N(p['S0']), p['A']), AND(p['S0'], p['B']))},
    'MXT2': lambda p: {'Y': OR(AND(N(p['S0']), p['A']), AND(p['S0'], p['B']))},
    'MXIT2': lambda p: {'Y': N(OR(AND(N(p['S0']), p['A']), AND(p['S0'], p['B'])))},
    'NAND2': lambda p: {'Y': N(AND(p['A'], p['B']))},
    'NAND2B': lambda p: {'Y': N(AND(N(p['AN']), p['B']))},
    'NAND2XB': lambda p: {'Y': N(AND(p['A'], N(p['BN'])))},
    'NAND3': lambda p: {'Y': N(AND(p['A'], p['B'], p['C']))},
    'NAND3B': lambda p: {'Y': N(AND(N(p['AN']), p['B'], p['C']))},
    'NAND4': lambda p: {'Y': N(AND(p['A'], p['B'], p['C'], p['D']))},
    'NAND4B': lambda p: {'Y': N(AND(N(p['AN']), p['B'], p['C'], p['D']))},
    'NAND4XXXB': lambda p: {'Y': N(AND(p['A'], p['B'], p['C'], N(p['DN'])))},
    'NOR2': lambda p: {'Y': N(OR(p['A'], p['B']))},
    'NOR2B': lambda p: {'Y': N(OR(N(p['AN']), p['B']))},
    'NOR2XB': lambda p: {'Y': N(OR(p['A'], N(p['BN'])))},
    'NOR3': lambda p: {'Y': N(OR(p['A'], p['B'], p['C']))},
    'OA21': lambda p: {'Y': AND(OR(p['A0'], p['A1']), p['B0'])},
    'OA22': lambda p: {'Y': AND(OR(p['A0'], p['A1']), OR(p['B0'], p['B1']))},
    'OAI21': lambda p: {'Y': N(AND(OR(p['A0'], p['A1']), p['B0']))},
    'OAI211': lambda p: {'Y': N(AND(OR(p['A0'], p['A1']), p['B0'], p['C0']))},
    'OAI21B': lambda p: {'Y': N(AND(OR(p['A0'], p['A1']), N(p['B0N'])))},
    'OAI22': lambda p: {'Y': N(AND(OR(p['A0'], p['A1']), OR(p['B0'], p['B1'])))},
    'OAI221': lambda p: {'Y': N(AND(OR(p['A0'], p['A1']), OR(p['B0'], p['B1']), p['C0']))},
    'OAI222': lambda p: {'Y': N(AND(OR(p['A0'], p['A1']), OR(p['B0'], p['B1']), OR(p['C0'], p['C1'])))},
    'OAI2XB1': lambda p: {'Y': N(AND(OR(p['A0'], N(p['A1N'])), p['B0']))},
    'OR2': lambda p: {'Y': OR(p['A'], p['B'])},
    'OR3': lambda p: {'Y': OR(p['A'], p['B'], p['C'])},
    'OR4': lambda p: {'Y': OR(p['A'], p['B'], p['C'], p['D'])},
    'XNOR2': lambda p: {'Y': N(XOR(p['A'], p['B']))},
    'XNOR3': lambda p: {'Y': N(XOR(p['A'], p['B'], p['C']))},
    'XOR2': lambda p: {'Y': XOR(p['A'], p['B'])},
    'XOR3': lambda p: {'Y': XOR(p['A'], p['B'], p['C'])},
}
SEQ = {'DFFQ'}
FEATS = ['p_main', 'p_carry', 'p_mean', 'entropy', 'corr_max', 'corr_mean_abs', 'corr_signed_mean',
         'corr_pos_frac', 'corr_strong_frac', 'support_frac', 'support_log', 'fanout_po_frac',
         'level_in', 'level_in_norm', 'level_out', 'level_out_norm', 'unknown_cell']


def popcount(a):
    return np.unpackbits(a.view(np.uint8)).sum()


def to_bits(a):
    return np.unpackbits(a.view(np.uint8)).astype(np.float32)


def const_value(net):
    s = str(net).replace(' ', '').lower()
    if s.endswith("'b0") or s in ('1\'b0', 'logic0', 'gnd'):
        return np.zeros(W, np.uint64)
    if s.endswith("'b1") or s in ('1\'b1', 'logic1', 'vdd'):
        return ONES.copy()
    return None


def simulate(path):
    m = NGE.build_circuit_model(path=path)
    gates, gpins, gdirs = m['gates'], m['gate_pins'], m['gate_dirs']
    n = len(gates)
    pis = list(dict.fromkeys(m['primary_inputs']))
    pos = set(m['primary_outputs'])
    driver = {}                                     # net -> gate index
    ins = [[] for _ in range(n)]
    outs = [[] for _ in range(n)]
    for i in range(n):
        for pin, net in gpins[i].items():
            if net is None:
                continue
            if gdirs[i].get(pin) == 'output':
                outs[i].append((pin, net))
                driver[net] = i
            else:
                ins[i].append((pin, net))
    val = {}
    for net in pis:
        val[net] = rng.integers(0, 2**63, size=W, dtype=np.uint64) | (rng.integers(0, 2, size=W, dtype=np.uint64) << np.uint64(63))
    pi_index = {net: k for k, net in enumerate(pis)}
    seq = [i for i in range(n) if fam(gates[i]['cell_type']) in SEQ]
    for i in seq:                                   # flip-flop outputs = pseudo primary inputs
        for _, net in outs[i]:
            val[net] = rng.integers(0, 2**63, size=W, dtype=np.uint64)
    # topological order over combinational gates
    deps = [set() for _ in range(n)]
    users = defaultdict(list)
    for i in range(n):
        if i in seq:
            continue
        for _, net in ins[i]:
            d = driver.get(net)
            if d is not None and d not in seq and d != i:
                deps[i].add(d)
                users[d].append(i)
    indeg = [len(d) for d in deps]
    q = deque(i for i in range(n) if indeg[i] == 0 and i not in seq)
    order = []
    while q:
        i = q.popleft()
        order.append(i)
        for u in users[i]:
            indeg[u] -= 1
            if indeg[u] == 0:
                q.append(u)
    loops = [i for i in range(n) if i not in seq and i not in set(order)]
    order += loops
    nwords = (len(pis) + 63) // 64 or 1
    support = {net: (1 << pi_index[net]) for net in pis}
    level = {net: 0 for net in pis}
    unknown = np.zeros(n)
    g_support = [0] * n
    g_level = np.zeros(n)
    g_out_vals = [None] * n
    for i in order:
        f = fam(gates[i]['cell_type'])
        pv, sup, lv = {}, 0, 0
        for pin, net in ins[i]:
            v = val.get(net)
            if v is None:
                v = const_value(net)
            if v is None:                           # undriven / loop-broken net -> random
                v = rng.integers(0, 2**63, size=W, dtype=np.uint64)
                val[net] = v
            pv[pin] = v
            sup |= support.get(net, 0)
            lv = max(lv, level.get(net, 0))
        fn = FUNCS.get(f)
        if fn is not None:
            try:
                res = fn(pv)
            except KeyError:
                res, unknown[i] = None, 1
        else:
            res, unknown[i] = None, 1
        if res is None:
            res = {pin: rng.integers(0, 2**63, size=W, dtype=np.uint64) for pin, _ in outs[i]}
        g_out_vals[i] = []
        for pin, net in outs[i]:
            v = res.get(pin, res.get('Y', next(iter(res.values()))))
            val[net] = v
            support[net] = sup
            level[net] = lv + 1
            g_out_vals[i].append((pin, v))
        g_support[i] = sup
        g_level[i] = lv + 1
    for i in seq:
        g_out_vals[i] = [(pin, val[net]) for pin, net in outs[i]]
        g_support[i] = 0
        g_level[i] = 0
    # reverse: PO reachability and level to PO
    po_list = [net for net in pos if net in driver]
    po_idx = {net: k for k, net in enumerate(po_list)}
    rsup = [0] * n
    rlev = np.zeros(n)
    for i in reversed(order):
        r, l = 0, 0
        for _, net in outs[i]:
            if net in po_idx:
                r |= 1 << po_idx[net]
                l = max(l, 1)
        for u in users[i]:
            r |= rsup[u]
            l = max(l, rlev[u] + 1 if rsup[u] else 0)
        rsup[i], rlev[i] = r, l
    # correlations with primary inputs
    PI = np.stack([to_bits(val[net]) for net in pis]) if pis else np.zeros((1, NPAT), np.float32)
    PI = PI - PI.mean(1, keepdims=True)
    PI /= np.maximum(PI.std(1, keepdims=True), 1e-6)
    feats = np.zeros((n, len(FEATS)), np.float32)
    main = np.zeros((n, NPAT), np.float32)
    for i in range(n):
        vals = g_out_vals[i] or [('Y', np.zeros(W, np.uint64))]
        ps = {pin: popcount(v) / NPAT for pin, v in vals}
        mpin = 'S' if 'S' in ps else next(iter(ps))
        cpin = 'CO' if 'CO' in ps else mpin
        pm = float(np.mean(list(ps.values())))
        feats[i, 0], feats[i, 1], feats[i, 2] = ps[mpin], ps[cpin], pm
        feats[i, 3] = -(pm * np.log2(pm + 1e-12) + (1 - pm) * np.log2(1 - pm + 1e-12))
        main[i] = to_bits(dict(vals)[cpin])            # carry output if present, else the only output
    G = main - main.mean(1, keepdims=True)
    G /= np.maximum(G.std(1, keepdims=True), 1e-6)
    for s in range(0, n, 4096):
        R = (G[s:s + 4096] @ PI.T) / NPAT          # (chunk, #PI) Pearson correlations
        A = np.abs(R)
        strong = A > 0.05
        feats[s:s + 4096, 4] = A.max(1)
        feats[s:s + 4096, 5] = A.mean(1)
        cnt = strong.sum(1)
        feats[s:s + 4096, 6] = np.where(cnt > 0, (R * strong).sum(1) / np.maximum(cnt, 1), 0)
        feats[s:s + 4096, 7] = np.where(cnt > 0, ((R > 0.05).sum(1)) / np.maximum(cnt, 1), 0.5)
        feats[s:s + 4096, 8] = (A > 0.1).sum(1) / max(len(pis), 1)
    nsup = np.array([bin(x).count('1') for x in g_support], float)
    feats[:, 9] = nsup / max(len(pis), 1)
    feats[:, 10] = np.log1p(nsup)
    feats[:, 11] = np.array([bin(x).count('1') for x in rsup], float) / max(len(po_list), 1)
    feats[:, 12] = g_level
    feats[:, 13] = g_level / max(g_level.max(), 1)
    feats[:, 14] = rlev
    feats[:, 15] = rlev / max(rlev.max(), 1)
    feats[:, 16] = unknown
    names = [g['inst_name'] for g in gates]
    stats = {'gates': n, 'pis': len(pis), 'pos': len(po_list), 'seq': len(seq), 'loop_gates': len(loops),
             'unknown_cells': int(unknown.sum())}
    return names, feats, stats


def main():
    node_of = {}
    with open(os.path.join(DATA, 'cell.txt'), encoding='utf-8', errors='replace') as f:
        for line in f:
            nid, rest = line.split(' ', 1)
            inst, fname = rest.rsplit(' from file ', 1)
            node_of[(fname.strip(), inst.strip())] = int(nid)
    out = np.full((len(node_of), len(FEATS)), np.nan, np.float32)
    meta = {}
    for fname in sorted(os.listdir(CIRC)):
        if not fname.endswith('.v'):
            continue
        t = time.time()
        names, feats, stats = simulate(os.path.join(CIRC, fname))
        hit = 0
        for nm, row in zip(names, feats):
            nid = node_of.get((fname, nm))
            if nid is not None:
                out[nid] = row
                hit += 1
        stats.update(matched=hit, seconds=round(time.time() - t, 1))
        meta[fname] = stats
        print(fname, stats, flush=True)
    missing = int(np.isnan(out[:, 0]).sum())
    print('nodes without simulation features:', missing)
    np.save(os.path.join(HERE, 'sim_feats.npy'), np.nan_to_num(out, nan=-1.0))
    json.dump({'features': FEATS, 'per_circuit': meta, 'missing_nodes': missing, 'patterns': NPAT},
              open(os.path.join(HERE, 'sim_feats_meta.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
