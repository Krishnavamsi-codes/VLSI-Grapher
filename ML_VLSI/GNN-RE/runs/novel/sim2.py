"""
Round 3 label-free features: Boolean influence profiles + input-bus structure + directed gate edges.

For every gate output f and primary input x_j, influence I_j = P[f(x) != f(x xor e_j)] over 512 random vectors
(re-simulate the whole circuit once per flipped PI). An adder sum bit has I = 1 on its own a_i/b_i bits; a
multiplier partial product has I ~ 0.5 on one bit of each operand; deeper multiplier bits are sensitive to
many PIs at moderate levels. Features summarise the profile, plus which PI buses (a, b, c, d - the port
letter before '[') the gate depends on and how its sensitive bits line up by bit index.

Only cell types, pin connectivity, PI/PO port bus letters and bit indices are used. Instance, hierarchy and
internal net names are NEVER used (they contain the module name = the label).

Also writes the directed gate->gate edge list (driver node id, sink node id) for direction-aware propagation.

Output: sim2_feats.npy (N x F), sim2_edges.npy (E x 2), sim2_feats_meta.json.
Run with the ML_VLSI .venv python (needs netlist_graph_engine).
"""
import json
import os
import re
import time
import zlib
from collections import defaultdict, deque

import numpy as np

import sim as S   # reuses FUNCS / fam / const_value and the netlist engine import

W = 8                        # 8 x 64 = 512 patterns per flip
NPAT = W * 64
rng = np.random.default_rng(777)
FEATS = ['inf_sum_norm', 'inf_sum_log', 'inf_max', 'inf_2nd', 'n_full_norm', 'n_full_log', 'n_half_norm',
         'inf_entropy', 'inf_support_norm', 'xor_ratio',
         'bus_dep', 'bus_dep_frac', 'bus_top_share', 'full_bus_count', 'full_aligned',
         'bit_mean_norm', 'bit_span_norm', 'bit_max_norm',
         'c_inf_sum_norm', 'c_inf_max', 'c_n_full_norm', 'c_bus_dep_frac']


def bus_bit(net):
    m = re.match(r'^\\?([A-Za-z_]\w*?)\s*\[(\d+)\]$', str(net).strip())
    return (m.group(1), int(m.group(2))) if m else (str(net).strip(), 0)


def compile_circuit(path):
    m = S.NGE.build_circuit_model(path=path)
    gates, gpins, gdirs = m['gates'], m['gate_pins'], m['gate_dirs']
    n = len(gates)
    pis = list(dict.fromkeys(m['primary_inputs']))
    driver, ins, outs = {}, [[] for _ in range(n)], [[] for _ in range(n)]
    for i in range(n):
        for pin, net in gpins[i].items():
            if net is None:
                continue
            if gdirs[i].get(pin) == 'output':
                outs[i].append((pin, net))
                driver[net] = i
            else:
                ins[i].append((pin, net))
    seq = {i for i in range(n) if S.fam(gates[i]['cell_type']) in S.SEQ}
    deps, users = [set() for _ in range(n)], defaultdict(list)
    edges = set()
    for i in range(n):
        for _, net in ins[i]:
            d = driver.get(net)
            if d is not None and d != i:
                edges.add((d, i))
                if i not in seq and d not in seq:
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
    done = set(order)
    order += [i for i in range(n) if i not in seq and i not in done]
    fixed = {}                                   # constants, undriven nets, FF outputs: fixed random/const
    for i in seq:
        for _, net in outs[i]:
            fixed[net] = rng.integers(0, 2**63, size=W, dtype=np.uint64)
    for i in order:
        for _, net in ins[i]:
            if net in pis or net in driver or net in fixed:
                continue
            c = S.const_value(net)
            fixed[net] = c[:W] if c is not None else rng.integers(0, 2**63, size=W, dtype=np.uint64)
    prog = []
    for i in order:
        fn = S.FUNCS.get(S.fam(gates[i]['cell_type']))
        prog.append((i, fn, ins[i], outs[i]))
    return dict(n=n, pis=pis, prog=prog, fixed=fixed, outs=outs, edges=sorted(edges),
                names=[g['inst_name'] for g in gates])


def evaluate(c, pi_vals):
    val = dict(c['fixed'])
    val.update(pi_vals)
    gout = {}
    for i, fn, ins, outs in c['prog']:
        pv = {pin: val[net] if net in val else 0 for pin, net in ins}
        res = None
        if fn is not None:
            try:
                res = fn(pv)
            except (KeyError, TypeError):
                res = None
        if res is None:                          # unknown cell: deterministic per-gate pseudo-random output
            res = {pin: np.full(W, np.uint64(zlib.crc32(f"{i}{pin}".encode()))) for pin, _ in outs}
        o = []
        for pin, net in outs:
            v = res.get(pin, res.get('Y', next(iter(res.values()))))
            val[net] = v
            o.append((pin, v))
        gout[i] = o
    return gout


def main_carry(o):
    d = dict(o)
    mp = 'S' if 'S' in d else (o[0][0] if o else None)
    cp = 'CO' if 'CO' in d else mp
    return mp, cp


def popcnt_rows(x):
    return np.unpackbits(x.view(np.uint8)).sum()


def summarise(I, bus_of, bit_of, nbus, maxbit):
    """I: (#PI,) influence vector of one output."""
    npi = len(I)
    tot = I.sum()
    srt = np.sort(I)[::-1]
    full = I > 0.9
    half = (I > 0.3) & (I <= 0.9)
    sup = I > 0.01
    p = I / tot if tot > 0 else np.zeros_like(I)
    ent = -(p[p > 0] * np.log(p[p > 0])).sum() / np.log(max(npi, 2))
    buses = set(bus_of[sup])
    if tot > 0:
        bus_inf = defaultdict(float)
        for j in np.where(sup)[0]:
            bus_inf[bus_of[j]] += I[j]
        top_share = max(bus_inf.values(), default=0.0) / tot
    else:
        top_share = 0.0
    fb = bus_of[full]
    fbits = bit_of[full]
    aligned = 0.0
    if full.sum() >= 2:                          # sensitive bits from different buses at the same index
        aligned = float(len(set(fbits)) < full.sum() and len(set(fb)) > 1)
    bits = bit_of[sup]
    bm = (I[sup] * bits).sum() / max(I[sup].sum(), 1e-9) / max(maxbit, 1) if sup.any() else -1
    span = (bits.max() - bits.min()) / max(maxbit, 1) if sup.any() else -1
    bmax = bits.max() / max(maxbit, 1) if sup.any() else -1
    return [tot / max(npi, 1), np.log1p(tot), srt[0] if npi else 0, srt[1] if npi > 1 else 0,
            full.sum() / max(npi, 1), np.log1p(full.sum()), half.sum() / max(npi, 1), ent,
            sup.sum() / max(npi, 1), tot / max(sup.sum(), 1),
            len(buses), len(buses) / max(nbus, 1), top_share, len(set(fb)), aligned, bm, span, bmax]


def features(path):
    c = compile_circuit(path)
    pis, n = c['pis'], c['n']
    bb = [bus_bit(p) for p in pis]
    bus_names = sorted(set(b for b, _ in bb))
    bus_of = np.array([bus_names.index(b) for b, _ in bb])
    bit_of = np.array([k for _, k in bb])
    maxbit = bit_of.max() if len(bit_of) else 1
    base = {p: rng.integers(0, 2**63, size=W, dtype=np.uint64) | (rng.integers(0, 2, size=W, dtype=np.uint64) << np.uint64(63))
            for p in pis}
    g0 = evaluate(c, base)
    gi = sorted(g0)
    mp_cp = {i: main_carry(g0[i]) for i in gi}
    Im = np.zeros((n, len(pis)), np.float32)
    Ic = np.zeros((n, len(pis)), np.float32)
    for j, p in enumerate(pis):
        flip = dict(base)
        flip[p] = ~base[p]
        g1 = evaluate(c, flip)
        for i in gi:
            d0, d1 = dict(g0[i]), dict(g1[i])
            mp, cp = mp_cp[i]
            if mp is None:
                continue
            Im[i, j] = popcnt_rows(d0[mp] ^ d1[mp]) / NPAT
            Ic[i, j] = popcnt_rows(d0[cp] ^ d1[cp]) / NPAT
    F = np.zeros((n, len(FEATS)), np.float32)
    for i in range(n):
        a = summarise(Im[i], bus_of, bit_of, len(bus_names), maxbit)
        b = summarise(Ic[i], bus_of, bit_of, len(bus_names), maxbit)
        F[i] = a + [b[0], b[2], b[4], b[11]]
    return c['names'], F, c['edges'], dict(gates=n, pis=len(pis), buses=bus_names)


def main():
    node_of = {}
    with open(os.path.join(S.DATA, 'cell.txt'), encoding='utf-8', errors='replace') as f:
        for line in f:
            nid, rest = line.split(' ', 1)
            inst, fname = rest.rsplit(' from file ', 1)
            node_of[(fname.strip(), inst.strip())] = int(nid)
    out = np.full((len(node_of), len(FEATS)), np.nan, np.float32)
    edges, meta = [], {}
    files = sorted(f for f in os.listdir(S.CIRC) if f.endswith('.v'))
    for fname in files:
        t = time.time()
        names, F, e, stats = features(os.path.join(S.CIRC, fname))
        ids = [node_of.get((fname, nm)) for nm in names]
        hit = 0
        for nid, row in zip(ids, F):
            if nid is not None:
                out[nid] = row
                hit += 1
        edges += [(ids[a], ids[b]) for a, b in e if ids[a] is not None and ids[b] is not None]
        stats.update(matched=hit, seconds=round(time.time() - t, 1))
        meta[fname] = stats
        print(fname, stats, flush=True)
    missing = int(np.isnan(out[:, 0]).sum())
    print('nodes without features:', missing, ' directed edges:', len(edges))
    np.save(os.path.join(S.HERE, 'sim2_feats.npy'), np.nan_to_num(out, nan=-1.0))
    np.save(os.path.join(S.HERE, 'sim2_edges.npy'), np.array(edges, dtype=np.int64))
    json.dump({'features': FEATS, 'per_circuit': meta, 'missing_nodes': missing, 'patterns': NPAT,
               'edges': len(edges)}, open(os.path.join(S.HERE, 'sim2_feats_meta.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
