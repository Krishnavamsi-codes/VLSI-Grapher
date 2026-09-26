"""
circuit_checks.py - Deterministic connectivity checks on a netlist model.

Input : the dict produced by netlist_graph_engine.build_circuit_model()
        (+ optional per-gate predictions / probabilities for model-based checks)
Output: {'findings': [...], 'stats': {...}}

Every finding carries concrete evidence (gate ids, nets, pins). Categories:
    electrical     facts about the netlist wiring (confidence 1.0)
    reachability   gates with no path from any PI / to any PO
    structural     components, carry chains, bit-slice dependency patterns
    gnn_suspicion  model-based hints (low confidence, labelled model_based)
    intent         reserved for intent-aware checks (intent_analyzer)

All checks are O(N+E) except the PI-support cones, which cost
O((N+E) * B/64) with B = number of primary-input bits (Python-int bitsets).
"""

import difflib
import threading
import time
from collections import OrderedDict, defaultdict, deque

from gnn_engine import extract_subcircuit_boundaries

SEVERITY_ORDER = {'error': 0, 'warning': 1, 'info': 2}
CATEGORY_ORDER = {'electrical': 0, 'reachability': 1, 'structural': 2, 'intent': 3, 'gnn_suspicion': 4}
GROUP_THRESHOLD = 25          # more findings than this per (check, block) are merged
MAX_SAMPLE = 50               # gate/net samples kept in merged findings
LOW_PROB_THRESHOLD = 0.6
NEIGHBOUR_MAJORITY = 0.75
MIN_BUS_WIDTH = 4             # bit-slice analysis only on buses at least this wide
ADDER_CELL_PREFIXES = ('ADDF', 'ADDH')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _Ctx:
    """Derived adjacency for one model."""

    def __init__(self, model):
        self.m = model
        n = model['num_gates']
        self.n = n
        self.inst = [g['inst_name'].lstrip('\\').strip() for g in model['gates']]
        self.cell = [g['cell_type'] for g in model['gates']]
        self.in_nets = [[] for _ in range(n)]
        self.out_nets = [[] for _ in range(n)]
        for g in range(n):
            for pin, net in model['gate_pins'][g].items():
                (self.out_nets if model['gate_dirs'][g][pin] == 'output' else self.in_nets)[g].append((pin, net))
        self.succ = [set() for _ in range(n)]
        self.pred = [set() for _ in range(n)]
        for net, e in model['nets'].items():
            drv = [d['gate_id'] for d in e['drivers'] if 'gate_id' in d]
            rdr = [r['gate_id'] for r in e['readers'] if 'gate_id' in r]
            for d in drv:
                for r in rdr:
                    if d != r:
                        self.succ[d].add(r)
                        self.pred[r].add(d)
        self.sinks = []       # places that need a connection
        self.sources = []     # connections available to be used
        self.triangular = []  # (bus, operand) pairs recognised as arithmetic ripple patterns

    def label(self, g):
        return f'{self.inst[g]} ({self.cell[g]})'


def _finding(check, category, severity, evidence, gate_ids=(), nets=(), pins=(),
             suggested_edges=(), confidence=1.0, **extra):
    f = {
        'id': None,
        'check': check,
        'category': category,
        'severity': severity,
        'gate_ids': sorted(set(int(g) for g in gate_ids)),
        'nets': list(dict.fromkeys(nets)),
        'pins': list(pins),
        'suggested_edges': list(suggested_edges),
        'evidence': evidence,
        'confidence': confidence,
        'model_based': category == 'gnn_suspicion',
    }
    f.update(extra)
    return f


def _net_driven(entry):
    return bool(entry['drivers'])


def _net_read(entry):
    return bool(entry['readers'])


# ---------------------------------------------------------------------------
# Electrical checks
# ---------------------------------------------------------------------------

def _check_electrical(ctx):
    m, out = ctx.m, []

    for mp in m['missing_pins']:
        g, pin = mp['gate_id'], mp['pin']
        how = 'explicitly left empty' if mp['explicit_empty'] else 'not connected to any net'
        if mp['direction'] == 'input':
            f = _finding('missing_pin', 'electrical', 'error',
                         f'Input pin {pin} of {ctx.label(g)} is {how}.',
                         gate_ids=[g], pins=[{'gate_id': g, 'pin': pin}])
            ctx.sinks.append({'kind': 'pin', 'gate_id': g, 'pin': pin, 'net': None, 'finding': f})
        else:
            f = _finding('missing_pin', 'electrical', 'warning',
                         f'Output pin {pin} of {ctx.label(g)} is {how}; the gate drives nothing on that pin.',
                         gate_ids=[g], pins=[{'gate_id': g, 'pin': pin}])
        out.append(f)

    po_set = set(m['primary_outputs'])
    for net, e in m['nets'].items():
        drivers, readers = e['drivers'], e['readers']
        gate_readers = [r for r in readers if 'gate_id' in r]
        gate_drivers = [d for d in drivers if 'gate_id' in d]

        if not drivers and gate_readers:
            f = _finding('floating_net', 'electrical', 'error',
                         f'Net {net} is read by {len(gate_readers)} gate pin(s) '
                         f'({", ".join(ctx.inst[r["gate_id"]] + "." + r["pin"] for r in gate_readers[:4])}) '
                         f'but nothing drives it.',
                         gate_ids=[r['gate_id'] for r in gate_readers], nets=[net],
                         pins=[{'gate_id': r['gate_id'], 'pin': r['pin']} for r in gate_readers])
            out.append(f)
            for r in gate_readers:
                ctx.sinks.append({'kind': 'pin', 'gate_id': r['gate_id'], 'pin': r['pin'], 'net': net, 'finding': f})

        if len(drivers) > 1:
            desc = ', '.join(ctx.label(d['gate_id']) + '.' + d['pin'] if 'gate_id' in d
                             else ('primary input ' + d['pi'] if 'pi' in d else str(d)) for d in drivers[:4])
            f = _finding('multi_driver', 'electrical', 'error',
                         f'Net {net} has {len(drivers)} drivers: {desc}.',
                         gate_ids=[d['gate_id'] for d in gate_drivers], nets=[net],
                         pins=[{'gate_id': d['gate_id'], 'pin': d['pin']} for d in gate_drivers])
            out.append(f)
            for d in gate_drivers:
                ctx.sources.append({'kind': 'gate', 'gate_id': d['gate_id'], 'pin': d['pin'], 'net': net,
                                    'penalty': 1.0, 'finding': f})

        if gate_drivers and not readers and net not in po_set:
            for d in gate_drivers:
                g, pin = d['gate_id'], d['pin']
                is_carry = pin == 'CO' and ctx.cell[g].startswith(ADDER_CELL_PREFIXES)
                check = 'carry_out_unread' if is_carry else 'dangling_output'
                what = 'Carry-out' if is_carry else 'Output'
                f = _finding(check, 'electrical', 'warning',
                             f'{what} {pin} of {ctx.label(g)} drives net {net}, which no gate or primary output reads.',
                             gate_ids=[g], nets=[net], pins=[{'gate_id': g, 'pin': pin}])
                out.append(f)
                ctx.sources.append({'kind': 'gate', 'gate_id': g, 'pin': pin, 'net': net, 'penalty': 0.0, 'finding': f})

        if any('const' in d for d in drivers) and gate_readers:
            out.append(_finding('const_input', 'electrical', 'info',
                                f'Net {net} is tied to constant {net if net[0].isdigit() else "value"} '
                                f'and read by {len(gate_readers)} gate pin(s).',
                                gate_ids=[r['gate_id'] for r in gate_readers], nets=[net],
                                pins=[{'gate_id': r['gate_id'], 'pin': r['pin']} for r in gate_readers]))

    for po in m['primary_outputs']:
        e = _lookup_net(m, po)
        if e is None or not e['drivers']:
            f = _finding('undriven_po', 'electrical', 'error',
                         f'Primary output {po} is not driven by any gate or input.', nets=[po])
            out.append(f)
            ctx.sinks.append({'kind': 'po', 'po': po, 'finding': f})

    for pi in m['primary_inputs']:
        e = _lookup_net(m, pi)
        if e is not None and not e['readers']:
            f = _finding('unused_pi', 'electrical', 'warning',
                         f'Primary input {pi} is never read by any gate or output.', nets=[pi])
            out.append(f)
            ctx.sources.append({'kind': 'pi', 'net': pi, 'penalty': 0.0, 'finding': f})

    for cell in m['unknown_cells']:
        gids = [g for g in range(ctx.n) if ctx.cell[g] == cell]
        out.append(_finding('unknown_cell', 'electrical', 'info',
                            f'Cell type {cell} ({len(gids)} instance(s)) is not in cell_library.json; pin '
                            f'directions use the fallback rule and pin completeness is not checked.',
                            gate_ids=gids[:MAX_SAMPLE], count=len(gids)))
    return out


def _lookup_net(model, name):
    e = model['nets'].get(name)
    if e is not None:
        return e
    for entry in model['nets'].values():
        if name in entry['aliases']:
            return entry
    return None


# ---------------------------------------------------------------------------
# Reachability
# ---------------------------------------------------------------------------

def _regions(ctx, gate_set):
    """Split a gate set into weakly-connected regions (within the set)."""
    seen, regions = set(), []
    for start in sorted(gate_set):
        if start in seen:
            continue
        comp, q = [], deque([start])
        seen.add(start)
        while q:
            g = q.popleft()
            comp.append(g)
            for h in ctx.succ[g] | ctx.pred[g]:
                if h in gate_set and h not in seen:
                    seen.add(h)
                    q.append(h)
        regions.append(sorted(comp))
    return regions


def _check_reachability(ctx):
    m, out = ctx.m, []
    nets = m['nets']
    po_set = set(m['primary_outputs'])

    # Forward from primary inputs / constants / input-less cells (tie cells)
    fwd = set()
    q = deque()
    for g in range(ctx.n):
        if not ctx.in_nets[g] or any(any('pi' in d or 'const' in d or 'assign' in d for d in nets[net]['drivers'])
                                     for _, net in ctx.in_nets[g]):
            fwd.add(g)
            q.append(g)
    while q:
        g = q.popleft()
        for h in ctx.succ[g]:
            if h not in fwd:
                fwd.add(h)
                q.append(h)

    # Backward from gates that drive a primary output (or an expression assign)
    bwd = set()
    for g in range(ctx.n):
        for _, net in ctx.out_nets[g]:
            e = nets[net]
            if net in po_set or any('po' in r or 'assign' in r for r in e['readers']) \
                    or any(a in po_set for a in e['aliases']):
                bwd.add(g)
                q.append(g)
                break
    while q:
        g = q.popleft()
        for h in ctx.pred[g]:
            if h not in bwd:
                bwd.add(h)
                q.append(h)

    for region in _regions(ctx, set(range(ctx.n)) - fwd):
        region_set = set(region)
        floating = sorted({net for g in region for _, net in ctx.in_nets[g] if not nets[net]['drivers']})
        explained = bool(floating)
        sample = ', '.join(ctx.inst[g] for g in region[:5])
        out.append(_finding(
            'unreachable_from_pi', 'reachability', 'info' if explained else 'warning',
            f'{len(region)} gate(s) ({sample}{"..." if len(region) > 5 else ""}) have no path from any '
            f'primary input' + (f'; they are fed by undriven net(s) {", ".join(floating[:4])}.' if explained
                                else '; they only feed each other (possible combinational loop).'),
            gate_ids=region[:MAX_SAMPLE], nets=floating[:MAX_SAMPLE], size=len(region),
            consequence_of_nets=floating[:MAX_SAMPLE]))
        del region_set

    for region in _regions(ctx, set(range(ctx.n)) - bwd):
        dangling = sorted({net for g in region for _, net in ctx.out_nets[g]
                           if not nets[net]['readers'] and net not in po_set})
        explained = bool(dangling)
        sample = ', '.join(ctx.inst[g] for g in region[:5])
        out.append(_finding(
            'no_path_to_po', 'reachability', 'info' if explained else 'warning',
            f'{len(region)} gate(s) ({sample}{"..." if len(region) > 5 else ""}) have no path to any '
            f'primary output' + (f'; their logic ends in unread net(s) {", ".join(dangling[:4])}.' if explained
                                 else '.'),
            gate_ids=region[:MAX_SAMPLE], nets=dangling[:MAX_SAMPLE], size=len(region),
            consequence_of_nets=dangling[:MAX_SAMPLE]))
    return out


# ---------------------------------------------------------------------------
# Structural: components, loops, PI-support cones, bit-slice / carry patterns
# ---------------------------------------------------------------------------

def _check_components(ctx):
    m = ctx.m
    parent = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for g in range(ctx.n):
        find(('g', g))
    for net, e in m['nets'].items():
        members = []
        for d in e['drivers']:
            if 'gate_id' in d:
                members.append(('g', d['gate_id']))
            elif 'pi' in d:
                members.append(('pi', d['pi']))
        for r in e['readers']:
            if 'gate_id' in r:
                members.append(('g', r['gate_id']))
            elif 'po' in r:
                members.append(('po', r['po']))
        for a in members[1:]:
            union(members[0], a)

    comps = defaultdict(lambda: {'gates': [], 'pi': 0, 'po': 0})
    for key in list(parent):
        c = comps[find(key)]
        if key[0] == 'g':
            c['gates'].append(key[1])
        else:
            c[key[0]] += 1
    with_gates = sorted((c for c in comps.values() if c['gates']), key=lambda c: -len(c['gates']))
    out = []
    for c in with_gates[1:]:
        gates = sorted(c['gates'])
        out.append(_finding(
            'isolated_component', 'structural', 'warning',
            f'{len(gates)} gate(s) ({", ".join(ctx.inst[g] for g in gates[:5])}) form a component that is not '
            f'connected to the main circuit (touches {c["pi"]} primary input bit(s), {c["po"]} output bit(s)).',
            gate_ids=gates[:MAX_SAMPLE], size=len(gates)))
    return out


def _topo_order(ctx):
    indeg = [len(p) for p in ctx.pred]
    q = deque(g for g in range(ctx.n) if indeg[g] == 0)
    order = []
    while q:
        g = q.popleft()
        order.append(g)
        for h in ctx.succ[g]:
            indeg[h] -= 1
            if indeg[h] == 0:
                q.append(h)
    cyclic = sorted(set(range(ctx.n)) - set(order))
    return order, cyclic


def _support_cones(ctx, order, cyclic):
    """PI-support bitset per gate and a net -> support function."""
    m = ctx.m
    pi_index = {b: i for i, b in enumerate(m['primary_inputs'])}
    gate_sup = [0] * ctx.n

    def net_sup(net):
        s = 0
        for d in m['nets'][net]['drivers']:
            if 'pi' in d:
                s |= 1 << pi_index[d['pi']]
            elif 'gate_id' in d:
                s |= gate_sup[d['gate_id']]
        return s

    for g in order + cyclic:
        s = 0
        for _, net in ctx.in_nets[g]:
            s |= net_sup(net)
        gate_sup[g] = s
    return pi_index, gate_sup, net_sup


def _cone_gates(ctx, net, limit=None):
    """Gates in the transitive fan-in of a net."""
    e = ctx.m['nets'].get(net)
    if e is None:
        return set()
    seen = set(d['gate_id'] for d in e['drivers'] if 'gate_id' in d)
    q = deque(seen)
    while q and (limit is None or len(seen) < limit):
        g = q.popleft()
        for h in ctx.pred[g]:
            if h not in seen:
                seen.add(h)
                q.append(h)
    return seen


def _check_bit_patterns(ctx, net_sup, pi_index):
    """
    Arithmetic buses (adders, subtractors, multipliers) have a triangular
    dependency pattern: output bit of significance w depends on exactly the
    operand bits of significance 0..min(w, W-1).  Bits that break an otherwise
    triangular pattern are reported (carry_break / bit_slice_anomaly).
    """
    m = ctx.m
    buses = m['buses']
    nets = m['nets']
    in_buses = [(n, b) for n, b in buses.items() if b['kind'] == 'input' and b['width'] >= MIN_BUS_WIDTH]
    raw = []   # (bus, operand, run) records

    for bname, bus in buses.items():
        if bus['kind'] not in ('output', 'wire') or bus['width'] < MIN_BUS_WIDTH:
            continue
        bit_sup = {}
        for w, bit in enumerate(bus['bits']):
            e = _lookup_net(m, bit)
            if e is None or not any('gate_id' in d for d in e['drivers']):
                continue
            canon = bit if bit in nets else next(k for k, v in nets.items() if v is e)
            bit_sup[w] = net_sup(canon)
        if len(bit_sup) < MIN_BUS_WIDTH:
            continue
        for aname, abus in in_buses:
            W = abus['width']
            a_idx = [pi_index[b] for b in abus['bits']]
            S = {}
            for w, sup in bit_sup.items():
                S[w] = frozenset(sig for sig, i in enumerate(a_idx) if sup >> i & 1)
            dep_bits = [w for w in S if S[w]]
            if len(dep_bits) < MIN_BUS_WIDTH:
                continue
            expected = {w: frozenset(range(min(w, W - 1) + 1)) for w in S}
            matched = [w for w in dep_bits if S[w] == expected[w]]
            # Classify by the upper edge (depends on its own significance, nothing higher):
            # a broken carry only removes lower bits, so the shape survives the fault.
            shaped = [w for w in dep_bits if S[w] <= expected[w] and max(S[w]) == min(w, W - 1)]
            nontrivial = [w for w in shaped if w < W - 1]
            if len(shaped) < 0.6 * len(dep_bits) or len(nontrivial) < 2:
                continue
            ctx.triangular.append({'bus': bname, 'operand': aname, 'bits_with_dependency': len(dep_bits),
                                   'bits_matching_pattern': len(matched)})
            top = max(dep_bits)
            deviant = sorted(w for w in S if w <= top and S[w] != expected[w])
            # contiguous runs of deviant bits
            run = []
            for w in deviant + [None]:
                if run and (w is None or w != run[-1] + 1):
                    raw.append((bname, aname, tuple(run), S, expected, abus))
                    run = []
                if w is not None:
                    run.append(w)

    # Merge runs that share bus + bits across operands (a and b usually break together)
    merged = OrderedDict()
    for bname, aname, run, S, expected, abus in raw:
        w0 = run[0]
        missing = sorted(expected[w0] - S[w0])
        extra = sorted(S[w0] - expected[w0])
        key = (bname, run)
        rec = merged.setdefault(key, {'bus': bname, 'run': run, 'operands': []})
        rec['operands'].append({'bus': aname, 'missing': missing, 'extra': extra, 'abus': abus})

    out = []
    for rec in merged.values():
        bname, run = rec['bus'], rec['run']
        bus = buses[bname]
        w0, w1 = run[0], run[-1]
        first_bit = bus['bits'][w0]
        cone = _cone_gates(ctx, _canon(m, first_bit))
        carry = all(op['missing'] and not op['extra'] and max(op['missing']) < w0 for op in rec['operands'])
        parts, gate_ids, suggested = [], set(), []
        verb = 'depends' if w0 == w1 else 'depend'
        for op in rec['operands']:
            abus = op['abus']
            if op['missing']:
                parts.append(f'no longer {verb} on {op["bus"]} bits of significance '
                             f'{_fmt_range(op["missing"])}')
            if op['extra']:
                parts.append(f'unexpectedly {verb} on {op["bus"]} bits of significance {_fmt_range(op["extra"])}')
            if carry:
                stage = max(op['missing']) + 1
                stage_bits = {abus['bits'][stage]} if stage < abus['width'] else set()
                gate_ids |= {g for g in cone if any(net in stage_bits for _, net in ctx.in_nets[g])}
            if op['extra']:
                extra_bits = {abus['bits'][s] for s in op['extra']}
                culprits = [(g, pin, net) for g in sorted(cone) for pin, net in ctx.in_nets[g] if net in extra_bits]
                gate_ids |= {g for g, _, _ in culprits}
                if len(op['missing']) == 1 and len(op['extra']) == 1:
                    want = abus['bits'][op['missing'][0]]
                    have = abus['bits'][op['extra'][0]]
                    for g, pin, net in culprits:
                        suggested.append({'from_net': want, 'to_gate': g, 'to_pin': pin, 'replaces_net': have,
                                          'reason': f'{bname} bit of significance {w0} should use {want} '
                                                    f'(significance {op["missing"][0]}), not {have}.',
                                          'confidence': 0.8})
                    # partner: a same-block gate outside this cone that reads the missing bit
                    blocks = {ctx.m['hier_prefix'][g] for g, _, _ in culprits}
                    for g in range(ctx.n):
                        if g in cone or ctx.m['hier_prefix'][g] not in blocks:
                            continue
                        for pin, net in ctx.in_nets[g]:
                            if net == want:
                                suggested.append({'from_net': have, 'to_gate': g, 'to_pin': pin, 'replaces_net': want,
                                                  'reason': f'Likely the other half of a swapped pair: {ctx.inst[g]}.{pin} '
                                                            f'reads {want} but its bit slice expects {have}.',
                                                  'confidence': 0.6})
        check = 'carry_break' if carry else 'bit_slice_anomaly'
        span = f'bit {first_bit}' if w0 == w1 else f'bits {first_bit}..{bus["bits"][w1]}'
        evidence = f'{bname} {span} (significance {w0}' + (f'..{w1}' if w1 != w0 else '') + ') ' + '; '.join(parts) + '.'
        if carry:
            stage = max(rec['operands'][0]['missing']) + 1
            evidence += (f' Every other bit of {bname} follows the expected ripple pattern, so the carry/propagate '
                         f'path from significance {stage - 1} into {stage} is likely broken.')
        out.append(_finding(check, 'structural', 'warning', evidence,
                            gate_ids=sorted(gate_ids)[:MAX_SAMPLE], nets=[bus['bits'][w] for w in run][:MAX_SAMPLE],
                            suggested_edges=suggested, confidence=0.9 if carry else 0.8,
                            bus=bname, bit_run=[w0, w1],
                            deviant_nets=[_canon(m, bus['bits'][w]) for w in run]))

    # Findings whose deviant bits are explained by an upstream deviant bus are consequences.
    for f in out:
        cone = _cone_gates(ctx, f['deviant_nets'][0])
        cone_nets = {net for g in cone for _, net in ctx.in_nets[g]}
        upstream = [o for o in out if o is not f and set(o['deviant_nets']) & cone_nets]
        if upstream:
            f['severity'] = 'info'
            f['consequence_of_bus'] = sorted({o['bus'] for o in upstream})
            f['evidence'] += (' This follows from the anomaly in ' + ', '.join(f['consequence_of_bus'])
                              + ', which feeds these bits.')
            f['suggested_edges'] = []
    for f in out:
        f.pop('deviant_nets', None)
    return out


def _canon(model, name):
    if name in model['nets']:
        return name
    for k, v in model['nets'].items():
        if name in v['aliases']:
            return k
    return name


def _fmt_range(sigs):
    if not sigs:
        return '-'
    if sigs == list(range(sigs[0], sigs[-1] + 1)) and len(sigs) > 2:
        return f'{sigs[0]}..{sigs[-1]}'
    return ', '.join(map(str, sigs))


def _check_structural(ctx):
    out = _check_components(ctx)
    order, cyclic = _topo_order(ctx)
    if cyclic:
        out.append(_finding('combinational_loop', 'structural', 'warning',
                            f'{len(cyclic)} gate(s) lie on or behind a combinational cycle '
                            f'({", ".join(ctx.inst[g] for g in cyclic[:5])}).',
                            gate_ids=cyclic[:MAX_SAMPLE], size=len(cyclic)))
    pi_index, _, net_sup = _support_cones(ctx, order, cyclic)
    out.extend(_check_bit_patterns(ctx, net_sup, pi_index))
    return out


# ---------------------------------------------------------------------------
# GNN suspicion (model-based)
# ---------------------------------------------------------------------------

CLASS_NAMES = ["Adder", "Multiplier", "Control Logic", "Subtractor", "Comparator"]


def _check_gnn(ctx, predictions, probabilities, source):
    if predictions is None or len(predictions) != ctx.n:
        return []
    weak = source == 'baseline'
    base_conf = 0.2 if weak else 0.4
    note = (' (baseline GCN predictions; this model is weak and mostly predicts one class)' if weak
            else ' (GraphSAINT predictions)')
    out = []

    neigh = [ctx.succ[g] | ctx.pred[g] for g in range(ctx.n)]
    groups = defaultdict(list)
    for g in range(ctx.n):
        if len(neigh[g]) < 3:
            continue
        counts = defaultdict(int)
        for h in neigh[g]:
            counts[predictions[h]] += 1
        maj, cnt = max(counts.items(), key=lambda kv: kv[1])
        if maj != predictions[g] and cnt / len(neigh[g]) >= NEIGHBOUR_MAJORITY:
            groups[(ctx.m['hier_prefix'][g], predictions[g], maj)].append(g)
    for (block, p, maj), gids in sorted(groups.items()):
        out.append(_finding('class_disagrees_with_neighbours', 'gnn_suspicion', 'info',
                            f'{len(gids)} gate(s) in block "{block or "top"}" are predicted {CLASS_NAMES[p]} while '
                            f'at least {int(NEIGHBOUR_MAJORITY * 100)}% of their neighbours are predicted '
                            f'{CLASS_NAMES[maj]}{note}.',
                            gate_ids=gids[:MAX_SAMPLE], confidence=base_conf, count=len(gids)))

    if probabilities is not None and len(probabilities) == ctx.n and source == 'graphsaint':
        low = defaultdict(list)
        for g, row in enumerate(probabilities):
            if row and max(row) < LOW_PROB_THRESHOLD:
                low[ctx.m['hier_prefix'][g]].append(g)
        for block, gids in sorted(low.items()):
            out.append(_finding('low_confidence_prediction', 'gnn_suspicion', 'info',
                                f'{len(gids)} gate(s) in block "{block or "top"}" have max class probability '
                                f'< {LOW_PROB_THRESHOLD}{note}.',
                                gate_ids=gids[:MAX_SAMPLE], confidence=0.5, count=len(gids)))

    subs = extract_subcircuit_boundaries(ctx.m['nodes'], ctx.m['edges'], list(predictions))
    singles = defaultdict(list)
    for sc in subs:
        if sc['size'] == 1:
            singles[sc['class_id']].append(sc['gate_ids'][0])
    for cid, gids in sorted(singles.items()):
        out.append(_finding('singleton_subcircuit', 'gnn_suspicion', 'info',
                            f'{len(gids)} gate(s) predicted {CLASS_NAMES[cid]} have no neighbour of the same '
                            f'predicted class, so each forms a one-gate "sub-circuit"{note}.',
                            gate_ids=sorted(gids)[:MAX_SAMPLE], confidence=base_conf * 0.75, count=len(gids)))
    return out


# ---------------------------------------------------------------------------
# Suggested-edge matcher: pair "needs a connection" with "connection available"
# ---------------------------------------------------------------------------

def _score(ctx, src, sink):
    hp = ctx.m['hier_prefix']
    s = 1.0 - src.get('penalty', 0.0)
    sg = src.get('gate_id')
    if sink['kind'] == 'pin':
        tg = sink['gate_id']
        if sg is not None:
            if sg == tg:
                return None
            if hp[sg] == hp[tg]:
                s += 3
            if src['pin'] == 'CO':
                s += 4 if sink['pin'] == 'CI' else 0
            elif sink['pin'] == 'CI':
                s -= 1
            s -= min(abs(sg - tg), 1000) / 1000.0
        if sink.get('net') and src.get('net'):
            s += difflib.SequenceMatcher(None, sink['net'], src['net']).ratio()
    else:  # primary output sink
        if src['kind'] == 'pi':
            s -= 2
        elif src.get('net'):
            s += difflib.SequenceMatcher(None, sink['po'], src['net']).ratio()
    return s


def _describe_edge(ctx, src, sink, conf):
    e = {}
    if src['kind'] == 'gate':
        e['from_gate'], e['from_pin'] = src['gate_id'], src['pin']
        what = f'{ctx.inst[src["gate_id"]]}.{src["pin"]}'
        why = {'multi_driver': f'{what} currently fights another driver on {src["net"]}'}.get(
            src['finding']['check'], f'{what} drives {src["net"]}, which nothing reads')
    else:
        e['from_net'] = src['net']
        what = src['net']
        why = f'primary input {what} is unused'
    if sink['kind'] == 'pin':
        e['to_gate'], e['to_pin'] = sink['gate_id'], sink['pin']
        target = f'{ctx.inst[sink["gate_id"]]}.{sink["pin"]}'
        need = 'is unconnected' if sink['net'] is None else f'reads undriven net {sink["net"]}'
    else:
        e['to_po'] = sink['po']
        target, need = f'primary output {sink["po"]}', 'is undriven'
    e['reason'] = f'{target} {need}, and {why}.'
    e['confidence'] = conf
    return e


def _match_suggestions(ctx):
    if not ctx.sinks or not ctx.sources:
        return
    scored = []
    for i, sink in enumerate(ctx.sinks):
        cands = []
        for j, src in enumerate(ctx.sources):
            s = _score(ctx, src, sink)
            if s is not None:
                cands.append((s, j))
        cands.sort(reverse=True)
        scored.append(cands)

    # Greedy: highest-scoring pairs first, each dangling source used once.
    pairs = sorted(((c[0][0], i) for i, c in enumerate(scored) if c), reverse=True)
    used = set()
    for _, i in pairs:
        cands = [c for c in scored[i] if c[1] not in used
                 or ctx.sources[c[1]]['finding']['check'] == 'multi_driver']
        if not cands:
            continue
        best_s, best_j = cands[0]
        margin = best_s - cands[1][0] if len(cands) > 1 else 99
        conf = 0.9 if margin >= 2 else 0.6 if margin >= 0.5 else 0.4
        chosen = [(best_j, conf, False)]
        src_finding = ctx.sources[best_j]['finding']
        if src_finding['check'] == 'multi_driver':
            # Which driver is the extra one is not decidable from structure (a bit-slice
            # heuristic was right only 86% of the time when it decided at all), so every
            # driver of the net is offered with equal confidence, in gate-id order.
            group = sorted((j for j, s in enumerate(ctx.sources) if s['finding'] is src_finding),
                           key=lambda j: ctx.sources[j]['gate_id'])
            chosen = [(j, round(1.0 / len(group), 2), True) for j in group]
        for j, c, ambiguous in chosen:
            used.add(j)
            edge = _describe_edge(ctx, ctx.sources[j], ctx.sinks[i], c)
            if ambiguous:
                edge['ambiguous'] = True
                edge['reason'] = (f'ambiguous: one of these is the extra driver of {ctx.sources[j]["net"]}. '
                                  + edge['reason'])
            for f in (ctx.sinks[i]['finding'], ctx.sources[j]['finding']):
                if edge not in f['suggested_edges']:
                    f['suggested_edges'].append(edge)


def _attach_repairs_to_structural(ctx, findings):
    """A carry/bit-slice anomaly located at a gate with a broken input inherits that input's repair."""
    for f in findings:
        if f['check'] not in ('carry_break', 'bit_slice_anomaly') or f['severity'] == 'info':
            continue
        gids = set(f['gate_ids'])
        for sink in ctx.sinks:
            if sink['kind'] == 'pin' and sink['gate_id'] in gids:
                for e in sink['finding']['suggested_edges']:
                    if e.get('to_gate') == sink['gate_id'] and e not in f['suggested_edges']:
                        f['suggested_edges'].append(e)


# ---------------------------------------------------------------------------
# Grouping, ordering, entry point
# ---------------------------------------------------------------------------

def _group(ctx, findings):
    buckets = OrderedDict()
    for f in findings:
        block = ctx.m['hier_prefix'][f['gate_ids'][0]] if f['gate_ids'] else ''
        buckets.setdefault((f['check'], f['severity'], block), []).append(f)
    out = []
    for (check, sev, block), fs in buckets.items():
        if len(fs) <= GROUP_THRESHOLD:
            out.extend(fs)
            continue
        g = dict(fs[0])
        g['gate_ids'] = sorted({x for f in fs for x in f['gate_ids']})[:MAX_SAMPLE]
        g['nets'] = list(dict.fromkeys(n for f in fs for n in f['nets']))[:MAX_SAMPLE]
        g['pins'] = [p for f in fs for p in f['pins']][:MAX_SAMPLE]
        g['suggested_edges'] = [e for f in fs for e in f['suggested_edges']][:GROUP_THRESHOLD]
        g['count'] = len(fs)
        g['evidence'] = fs[0]['evidence'] + f' (and {len(fs) - 1} similar findings in block "{block or "top"}")'
        out.append(g)
    return out


def run_checks(model, predictions=None, probabilities=None, prediction_source=None):
    """Run all deterministic checks. Returns {'findings': [...], 'stats': {...}}."""
    t0 = time.time()
    ctx = _Ctx(model)
    findings = []
    findings += _check_electrical(ctx)
    findings += _check_reachability(ctx)
    findings += _check_structural(ctx)
    _match_suggestions(ctx)
    _attach_repairs_to_structural(ctx, findings)
    findings += _check_gnn(ctx, predictions, probabilities, prediction_source)
    findings = _group(ctx, findings)
    findings.sort(key=lambda f: (SEVERITY_ORDER[f['severity']], CATEGORY_ORDER[f['category']],
                                 f['check'], f['gate_ids'][:1], f['nets'][:1]))
    for i, f in enumerate(findings, 1):
        f['id'] = f'F{i:03d}'

    by = defaultdict(int)
    for f in findings:
        by['severity:' + f['severity']] += 1
        by['check:' + f['check']] += 1
    stats = {
        'num_gates': ctx.n,
        'num_nets': len(model['nets']),
        'num_edges': len(model['edges']),
        'num_primary_inputs': len(model['primary_inputs']),
        'num_primary_outputs': len(model['primary_outputs']),
        'prediction_source': prediction_source,
        'errors': by['severity:error'],
        'warnings': by['severity:warning'],
        'infos': by['severity:info'],
        'by_check': {k[6:]: v for k, v in sorted(by.items()) if k.startswith('check:')},
        'arithmetic_bus_patterns': ctx.triangular,
        'parse_warnings': model['parse_warnings'],
        'elapsed_ms': round((time.time() - t0) * 1000, 1),
    }
    return {'findings': findings, 'stats': stats}


# ---------------------------------------------------------------------------
# Thread-safe LRU cache keyed by (circuit key, file sha256, prediction source)
# ---------------------------------------------------------------------------

_cache = OrderedDict()
_cache_lock = threading.Lock()
CACHE_SIZE = 32


def cached(key, compute):
    with _cache_lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key], True
    value = compute()
    with _cache_lock:
        _cache[key] = value
        _cache.move_to_end(key)
        while len(_cache) > CACHE_SIZE:
            _cache.popitem(last=False)
    return value, False


if __name__ == '__main__':
    import json
    import sys
    from netlist_graph_engine import build_circuit_model

    if len(sys.argv) < 2:
        print('usage: python circuit_checks.py <netlist.v> [--json]')
        sys.exit(1)
    res = run_checks(build_circuit_model(sys.argv[1]))
    if '--json' in sys.argv:
        print(json.dumps(res, indent=1))
    else:
        print(json.dumps(res['stats'], indent=1))
        for f in res['findings']:
            print(f"{f['id']} [{f['severity']:7s}] {f['check']}: {f['evidence']}")
            for e in f['suggested_edges']:
                print('      suggest:', e)
