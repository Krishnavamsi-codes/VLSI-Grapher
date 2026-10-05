"""
design_insights.py - Deterministic design-level analysis for the Design Copilot.

    compute(model, analysis) -> dict

Structure (ports, control signals, datapaths, blocks), structural timing (logic levels, longest paths, carry
chains, fan-out), structural power indicators, area proxies (gate counts), duplicate logic, GraphSAINT region
explanations and optimization candidates.

This repository has no delay, power or area data: cell_library.json lists pin directions only, and there are no
liberty, SDF, SAIF/VCD or area reports. Every metric here is therefore a structural proxy (gate levels, fan-out,
gate counts) and says so. Nothing is estimated in ns, mW or um^2. All gate ids, nets and paths come from the
parsed netlist; GraphSAINT outputs are labelled as ML predictions and kept apart from netlist facts.
"""

import re
from collections import Counter, defaultdict, deque

import cell_datasheet
import circuit_checks as cc
from gnn_engine import extract_subcircuit_boundaries

DATA_AVAILABILITY = {
    'netlist_structure': True,
    'gate_delays': False,
    'switching_activity': False,
    'power_data': False,
    'cell_area': False,
    'note': ('No timing, power or area data exists for this circuit (the cell library holds pin directions only; '
             'there are no liberty, SDF, SAIF/VCD or area files). Only structural indicators are available: gate '
             'levels, fan-out and gate counts. These are proxies, not measured delay, power or area.'),
}
STRUCTURAL_NOTE = 'structural indicator only; no delay/power/area data exists'

MUX_SELECT_PINS = frozenset({'S0', 'S1', 'S', 'SEL'})
SEQUENTIAL_RE = re.compile(r'^(S?DFF|LAT|ICG|PREICG|POSTICG|FRICG|RF\dR)', re.I)
_DRIVE_RE = re.compile(r'_X(\d+)(?:P(\d+))?[A-Z]*_')
HIGH_FANOUT_MIN = 8
TOP_N = 8
MAX_PATHS = 5


def cell_base(cell):
    """ADDF_X1M_A9TH -> ADDF; NAND2XB_X0P5M_A9TH -> NAND2XB (function, without drive strength)."""
    return re.sub(r'_X\w+$', '', cell)


def drive_strength(cell):
    """Drive multiple from the cell-name suffix (X0P5 -> 0.5), by naming convention; None if absent."""
    m = _DRIVE_RE.search(cell + '_')
    if not m:
        return None
    return float(m.group(1) + ('.' + m.group(2) if m.group(2) else ''))


def _block(prefix):
    return prefix.split('/')[0] if prefix else 'top'


def _gl(ids, cap=12):
    ids = list(ids)
    return ', '.join(f'G{g}' for g in ids[:cap]) + (f' (+{len(ids) - cap} more)' if len(ids) > cap else '') \
        if ids else 'none'


class Insights:
    """All deterministic design-level facts for one circuit. Built once per (circuit, sha) and cached."""

    def __init__(self, model, analysis, liberty=None):
        self.m = model
        self.a = analysis
        self.ctx = cc._Ctx(model)
        self.n = self.ctx.n
        self.order, self.cyclic = cc._topo_order(self.ctx)
        self.blocks = [_block(p) for p in model['hier_prefix']]
        self.po_set = set(model['primary_outputs'])
        self.findings = analysis['findings']
        self.preds = analysis.get('predictions')
        self.probs = analysis.get('probabilities')
        self.source = analysis.get('prediction_source')
        self._levels()
        self._fanout()
        self.structure = self._structure()
        self.structure['plain_purpose'] = self._plain_language_purpose(self.structure)
        self.timing = self._timing()
        self.area = self._area()
        self.power = self._power()
        self.subcircuits = (extract_subcircuit_boundaries(model['nodes'], model['edges'], list(self.preds))
                            if self.preds is not None and len(self.preds) == self.n else [])
        self.module_of = {}
        for i, sc in enumerate(self.subcircuits, 1):
            for g in sc['gate_ids']:
                self.module_of[g] = i
        self.liberty = liberty if liberty is not None else cell_datasheet.load_liberty()
        self.bom = self._bom()
        self.optimizations = self._optimizations()

    # ------------------------------------------------------------------ basics
    def _levels(self):
        """Unit-delay logic levels: level_in = gates on the longest path from a primary input up to and including
        the gate; level_out = gates from the gate to the end of its longest downstream path."""
        ctx, n = self.ctx, self.n
        lin = [0] * n
        for g in self.order:
            lin[g] = 1 + max((lin[p] for p in ctx.pred[g]), default=0)
        lout = [0] * n
        for g in reversed(self.order):
            lout[g] = 1 + max((lout[s] for s in ctx.succ[g]), default=0)
        self.level_in, self.level_out = lin, lout
        self.max_depth = max(lin, default=0)
        self.through = [lin[g] + lout[g] - 1 if lin[g] else 0 for g in range(n)]   # longest path through g
        self.critical = {g for g in range(n) if self.through[g] == self.max_depth and self.max_depth}

    def _fanout(self):
        m = self.m
        self.net_fanout = {}
        for net, e in m['nets'].items():
            self.net_fanout[net] = len(e['readers'])
        self.gate_out_nets = self.ctx.out_nets

    def gate_fanout(self, g):
        return sum(self.net_fanout.get(net, 0) for _, net in self.ctx.out_nets[g])

    def _driver_text(self, net):
        e = self.m['nets'][net]
        parts = []
        for d in e['drivers']:
            if 'gate_id' in d:
                g = d['gate_id']
                parts.append(f"G{g} ({self.ctx.cell[g]})")
            elif 'pi' in d:
                parts.append(f"primary input {d['pi']}")
            elif 'const' in d:
                parts.append(f"constant {d['const']}")
        return ' and '.join(parts) or 'nothing'

    def _driver_gates(self, net):
        return [d['gate_id'] for d in self.m['nets'][net]['drivers'] if 'gate_id' in d]

    # ------------------------------------------------------------------ structure
    def _structure(self):
        m, ctx = self.m, self.ctx
        ev = self.a['evidence']
        buses = m['buses']
        inputs = [{'name': b, 'width': v['width']} for b, v in buses.items() if v['kind'] in ('input', 'inout')]
        outputs = [{'name': b, 'width': v['width']} for b, v in buses.items() if v['kind'] in ('output', 'inout')]
        inputs += [{'name': p, 'width': 1} for p in m['primary_inputs'] if p not in m['bit_info']]
        outputs += [{'name': p, 'width': 1} for p in m['primary_outputs'] if p not in m['bit_info']]

        # control signals: nets that drive mux select pins, and narrow primary inputs outside the operand buses
        operand_bits = {b for name, v in buses.items() if v['kind'] == 'input' and v['width'] >= cc.MIN_BUS_WIDTH
                        for b in v['bits']}
        control = {}
        for net, e in m['nets'].items():
            sel = [r for r in e['readers'] if 'gate_id' in r and r['pin'] in MUX_SELECT_PINS
                   and cell_base(ctx.cell[r['gate_id']]).startswith('MX')]
            is_pi = any('pi' in d for d in e['drivers'])
            narrow_pi = is_pi and net not in operand_bits and not any(a in operand_bits for a in e['aliases'])
            if sel or (narrow_pi and len(e['readers']) >= 2):
                why = []
                if sel:
                    why.append(f'drives the select pin of {len(sel)} multiplexer cell(s)')
                if narrow_pi:
                    why.append('primary input outside the operand buses')
                control[net] = {'net': net, 'fanout': len(e['readers']), 'select_pins': len(sel),
                                'driver': self._driver_text(net), 'primary_input': is_pi, 'why': '; '.join(why),
                                'gates': sorted({r['gate_id'] for r in e['readers'] if 'gate_id' in r})[:40]}
        controls = sorted(control.values(), key=lambda c: (-c['select_pins'], -c['fanout'], c['net']))[:10]

        # datapaths from the deterministic dependency-cone signatures
        datapaths = []
        sigs = {s['bus']: s for s in ev['cone_signatures']}
        for s in ev['cone_signatures']:
            cls = s['classification']
            if cls in (None, 'unclassified'):
                continue
            src = s.get('selects_between') if cls == 'select-like' else s.get('operand_buses', [])
            drivers = [p for p in s['driver_prefixes'] if p != 'top']
            kind = buses.get(s['bus'], {}).get('kind', 'output' if s['bus'] in self.po_set else 'wire')
            datapaths.append({'to': s['bus'], 'to_kind': kind, 'from': list(src or []), 'classification': cls,
                              'driver_blocks': sorted({_block(p) for p in drivers})[:3] or ['top'],
                              'width': s['width']})
        # chain text: inputs -> internal result -> output
        chains = []
        for d in datapaths:
            if d['to_kind'] in ('output', 'inout'):
                for mid in d['from']:
                    up = next((x for x in datapaths if x['to'] == mid), None)
                    if up:
                        chains.append(f"{', '.join(up['from'])} -> {'/'.join(up['driver_blocks'])} ({up['classification']}) "
                                      f"-> {mid} -> {'/'.join(d['driver_blocks'])} ({d['classification']}) -> output {d['to']}")
                if not any(x['to'] == mid for mid in d['from'] for x in datapaths):
                    chains.append(f"{', '.join(d['from'])} -> {'/'.join(d['driver_blocks'])} ({d['classification']}) "
                                  f"-> output {d['to']}")

        blocks = []
        intent_roles = {}
        for b in self.a['intent'].get('blocks', []):
            for p in b.get('hier_prefixes', []) + [b['name']]:
                intent_roles.setdefault(_block(p), b['role'])
        counts = Counter(self.blocks)
        for name, cnt in counts.most_common():
            cells = Counter(cell_base(ctx.cell[g]) for g in range(self.n) if self.blocks[g] == name)
            blocks.append({'name': name, 'gates': cnt, 'share': round(cnt / max(self.n, 1), 3),
                           'top_cells': dict(cells.most_common(5)), 'inferred_role': intent_roles.get(name)})
        flow = [{'from': d['from_block'], 'to': d['to_block'], 'via': d['via']} for d in ev['dataflow']]
        seq = sorted({ctx.cell[g] for g in range(self.n) if SEQUENTIAL_RE.match(ctx.cell[g])})
        return {'inputs': inputs, 'outputs': outputs, 'control_signals': controls, 'datapaths': datapaths,
                'datapath_chains': list(dict.fromkeys(chains))[:8], 'blocks': blocks, 'block_connections': flow,
                'sequential_cells': seq, 'combinational_only': not seq,
                'num_gates': self.n, 'num_nets': len(m['nets'])}

    # ------------------------------------------------------------------ timing (structural)
    def _path_to(self, end):
        """Longest path ending at `end` (signal-flow order); ties broken by the smallest gate id."""
        path, g = [end], end
        while self.level_in[g] > 1:
            g = min(p for p in self.ctx.pred[g] if self.level_in[p] == self.level_in[g] - 1)
            path.append(g)
        return path[::-1]

    def _path_endpoints(self, path):
        m = self.m
        start, end = path[0], path[-1]
        pis = sorted({d['pi'] for _, net in self.ctx.in_nets[start] for d in m['nets'][net]['drivers'] if 'pi' in d})
        pos = sorted({r['po'] for _, net in self.ctx.out_nets[end] for r in m['nets'][net]['readers'] if 'po' in r}
                     | {net for _, net in self.ctx.out_nets[end] if net in self.po_set})
        return pis, pos

    def _timing(self):
        ctx, m = self.ctx, self.m
        if not self.max_depth:
            return {'max_depth': 0, 'paths': [], 'note': STRUCTURAL_NOTE}
        # longest paths to distinct output endpoints first, then any remaining deepest gates
        po_drivers = sorted({g for g in range(self.n) for _, net in ctx.out_nets[g]
                             if net in self.po_set or any('po' in r for r in m['nets'][net]['readers'])},
                            key=lambda g: (-self.level_in[g], g))
        ends = po_drivers[:MAX_PATHS] or sorted(range(self.n), key=lambda g: (-self.level_in[g], g))[:MAX_PATHS]
        deepest = max(range(self.n), key=lambda g: (self.level_in[g], -g))
        if self.level_in[deepest] > self.level_in[ends[0]]:
            ends = [deepest] + ends[:MAX_PATHS - 1]
        paths = []
        for e in ends:
            p = self._path_to(e)
            pis, pos = self._path_endpoints(p)
            paths.append({'levels': len(p), 'gates': p, 'from_inputs': pis[:4], 'to_outputs': pos[:4],
                          'blocks': [b for b, _ in Counter(self.blocks[g] for g in p).most_common()]})
        # output arrival levels (slowest outputs)
        arrivals = []
        for po in m['primary_outputs']:
            e = m['nets'].get(cc._canon(m, po))
            drv = [d['gate_id'] for d in (e['drivers'] if e else []) if 'gate_id' in d]
            if drv:
                arrivals.append({'output': po, 'levels': max(self.level_in[g] for g in drv)})
        arrivals.sort(key=lambda x: (-x['levels'], x['output']))
        # ripple carry chains: adder CO pin feeding the CI pin of another adder cell
        nxt = defaultdict(list)
        for g in range(self.n):
            if not ctx.cell[g].startswith(cc.ADDER_CELL_PREFIXES):
                continue
            co = m['gate_pins'][g].get('CO')
            if co is None:
                continue
            for r in m['nets'][co]['readers']:
                if 'gate_id' in r and r['pin'] == 'CI' and ctx.cell[r['gate_id']].startswith(cc.ADDER_CELL_PREFIXES):
                    nxt[g].append(r['gate_id'])
        has_prev = {h for v in nxt.values() for h in v}
        chains = []
        for g in sorted(nxt):
            if g in has_prev:
                continue
            chain, cur, seen = [g], g, {g}
            while nxt.get(cur):
                cur = min(nxt[cur])
                if cur in seen:
                    break
                seen.add(cur)
                chain.append(cur)
            if len(chain) >= 3:
                chains.append({'length': len(chain), 'gates': chain, 'block': Counter(self.blocks[x] for x in chain).most_common(1)[0][0]})
        chains.sort(key=lambda c: (-c['length'], c['gates'][0]))
        high = self.high_fanout()
        critical_high = [h for h in high if h['driver_gates'] and set(h['driver_gates']) & self.critical]
        hist = Counter(self.level_in[g] for g in range(self.n))
        buckets = [(1, 1), (2, 2), (3, 3), (4, 5), (6, 8), (9, 16), (17, 32), (33, 10 ** 9)]
        fo = Counter()
        for net, k in self.net_fanout.items():
            if k and not any('const' in d for d in self.m['nets'][net]['drivers']):
                b = next(b for b in buckets if b[0] <= k <= b[1])
                fo[b] += 1
        fanout_hist = [{'label': (f'{a}' if a == b else f'{a}+' if b > 10 ** 6 else f'{a}-{b}'), 'nets': fo[(a, b)]}
                       for a, b in buckets if fo[(a, b)]]
        return {'max_depth': self.max_depth, 'paths': paths, 'critical_gate_count': len(self.critical),
                'slowest_outputs': arrivals[:8], 'carry_chains': chains[:5], 'high_fanout': high,
                'high_fanout_on_critical': critical_high, 'cyclic_gates': len(self.cyclic),
                'depth_histogram': dict(sorted(hist.items())), 'fanout_histogram': fanout_hist,
                'note': STRUCTURAL_NOTE,
                'model': 'unit-delay gate levels (each gate counts 1; real delays differ by cell and load)'}

    def high_fanout(self, top=TOP_N):
        rows = []
        for net, fo in self.net_fanout.items():
            e = self.m['nets'][net]
            if fo < 2 or any('const' in d for d in e['drivers']):
                continue
            rows.append((fo, net))
        rows.sort(key=lambda x: (-x[0], x[1]))
        out = []
        for fo, net in rows[:top]:
            drv = self._driver_gates(net)
            weak = [g for g in drv if (drive_strength(self.ctx.cell[g]) or 99) < 1]
            out.append({'net': net, 'fanout': fo, 'driver': self._driver_text(net), 'driver_gates': drv,
                        'weak_drive': bool(weak), 'on_longest_path': bool(set(drv) & self.critical),
                        'reader_gates': sorted({r['gate_id'] for r in self.m['nets'][net]['readers'] if 'gate_id' in r})[:30]})
        return out

    def gate_timing(self, g):
        ctx = self.ctx
        fo = self.gate_fanout(g)
        on = g in self.critical
        slack = self.max_depth - self.through[g]
        return {'gate_id': g, 'instance': ctx.inst[g], 'cell': ctx.cell[g], 'block': self.blocks[g],
                'levels_from_inputs': self.level_in[g], 'levels_to_end': self.level_out[g],
                'longest_path_through_gate': self.through[g], 'circuit_max_depth': self.max_depth,
                'on_longest_path': on, 'level_slack': slack, 'fanout_pins': fo,
                'fanin_gates': sorted(ctx.pred[g])[:20], 'fanout_gates': sorted(ctx.succ[g])[:20],
                'drive_strength_from_name': drive_strength(ctx.cell[g]), 'in_cycle': g in set(self.cyclic)}

    # ------------------------------------------------------------------ area (structural proxy)
    def _duplicates(self):
        """Gates with the same cell function reading exactly the same net on every input pin compute the same
        signal: a deterministic redundancy."""
        groups = defaultdict(list)
        for g in range(self.n):
            ins = self.ctx.in_nets[g]
            outs = self.ctx.out_nets[g]
            if not ins or len(outs) != 1 or SEQUENTIAL_RE.match(self.ctx.cell[g]):
                continue
            key = (cell_base(self.ctx.cell[g]), tuple(sorted(ins)))
            groups[key].append(g)
        dups = [{'cell_function': k[0], 'gates': v, 'inputs': [f'{p}={n}' for p, n in k[1]]}
                for k, v in groups.items() if len(v) > 1]
        dups.sort(key=lambda d: (-len(d['gates']), d['gates'][0]))
        return dups

    def _inverter_pairs(self):
        ctx, m = self.ctx, self.m
        pairs = []
        for g in range(self.n):
            if cell_base(ctx.cell[g]) != 'INV' or not ctx.out_nets[g]:
                continue
            net = ctx.out_nets[g][0][1]
            rd = m['nets'][net]['readers']
            if len(rd) == 1 and 'gate_id' in rd[0] and cell_base(ctx.cell[rd[0]['gate_id']]) == 'INV' \
                    and net not in self.po_set:
                pairs.append([g, rd[0]['gate_id']])
        return pairs

    def _area(self):
        ctx = self.ctx
        fams = Counter(cell_base(c) for c in ctx.cell)
        sub = Counter(p for p in self.m['hier_prefix'] if p)
        # gates none of whose outputs reaches a primary output (multi-output gates with one unread pin excluded)
        unused = sorted({g for f in self.findings if f['check'] == 'no_path_to_po' for g in f['gate_ids']})
        dups = self._duplicates()
        return {'total_gates': self.n, 'blocks': self.structure['blocks'],
                'cell_families': dict(fams.most_common(12)),
                'densest_sub_blocks': [{'prefix': p, 'gates': c} for p, c in sub.most_common(6)],
                'duplicate_groups': dups[:10], 'duplicate_gate_count': sum(len(d['gates']) - 1 for d in dups),
                'inverter_pairs': self._inverter_pairs()[:10], 'logic_without_output_path': unused[:50],
                'note': 'gate counts are an area proxy; no cell area data exists'}

    # ------------------------------------------------------------------ power (structural indicators)
    def _cone_sizes(self):
        out = []
        for name, b in self.m['buses'].items():
            if b['kind'] == 'input':
                continue
            seen = set()
            q = deque()
            for bit in b['bits']:
                e = self.m['nets'].get(cc._canon(self.m, bit))
                for d in (e['drivers'] if e else []):
                    if 'gate_id' in d and d['gate_id'] not in seen:
                        seen.add(d['gate_id'])
                        q.append(d['gate_id'])
            while q:
                g = q.popleft()
                for h in self.ctx.pred[g]:
                    if h not in seen:
                        seen.add(h)
                        q.append(h)
            if seen:
                xor = sum(1 for g in seen if cell_base(self.ctx.cell[g]).startswith(('XOR', 'XNOR', 'ADDF', 'ADDH')))
                out.append({'bus': name, 'kind': b['kind'], 'cone_gates': len(seen), 'xor_adder_cells': xor})
        out.sort(key=lambda c: (-c['cone_gates'], c['bus']))
        return out

    def _power(self):
        ctx = self.ctx
        per_block = []
        for b in self.structure['blocks']:
            gs = [g for g in range(self.n) if self.blocks[g] == b['name']]
            x = sum(1 for g in gs if cell_base(ctx.cell[g]).startswith(('XOR', 'XNOR', 'ADDF', 'ADDH')))
            depth = max((self.level_in[g] for g in gs), default=0)
            per_block.append({'block': b['name'], 'gates': len(gs), 'xor_adder_cells': x, 'max_level': depth})
        selects = [d for d in self.structure['datapaths'] if d['classification'] == 'select-like' and len(d['from']) >= 2]
        return {'high_fanout': self.high_fanout(), 'cones': self._cone_sizes(), 'blocks': per_block,
                'select_outputs': selects, 'control_signals': self.structure['control_signals'][:5],
                'combinational_only': self.structure['combinational_only'],
                'duplicate_gate_count': self.area['duplicate_gate_count'],
                'note': 'no switching-activity or power data; these are candidates to investigate, not measurements'}

    # ------------------------------------------------------------------ cell BOM + datasheets
    def _bom(self):
        """Bill of materials of standard cells: one row per cell type, counted from the netlist."""
        ctx, lib = self.ctx, self.liberty
        by_cell = defaultdict(list)
        for g in range(self.n):
            by_cell[ctx.cell[g]].append(g)
        rows = []
        for cell, gates in by_cell.items():
            ds = cell_datasheet.datasheet(cell, lib)
            row = {'cell': cell, 'family': ds['family'], 'description': ds['description'], 'count': len(gates),
                   'share': round(len(gates) / max(self.n, 1), 4),
                   'blocks': dict(Counter(self.blocks[g] for g in gates).most_common()),
                   'drive_strength': ds['drive_strength'], 'function': ds['function'],
                   'inputs': ds['inputs'], 'outputs': ds['outputs'], 'in_cell_library': ds['pins_source'] == 'cell_library.json',
                   'area_each': ds['area'], 'leakage_each': ds['leakage_power'], 'library_data': ds['library_data'],
                   'gate_ids': gates[:200]}
            if ds['area'] is not None:
                row['area_total'] = round(ds['area'] * len(gates), 4)
            if ds['leakage_power'] is not None:
                row['leakage_total'] = round(ds['leakage_power'] * len(gates), 6)
            rows.append(row)
        rows.sort(key=lambda r: (-r['count'], r['cell']))
        fams = Counter()
        for r in rows:
            fams[r['family']] += r['count']
        with_area = [r for r in rows if 'area_total' in r]
        totals = {'cell_types': len(rows), 'instances': self.n, 'families': len(fams)}
        if lib and with_area:
            totals['area'] = round(sum(r['area_total'] for r in with_area), 4)
            totals['area_coverage'] = round(sum(r['count'] for r in with_area) / max(self.n, 1), 4)
            leak = [r for r in rows if 'leakage_total' in r]
            if leak:
                totals['leakage_power'] = round(sum(r['leakage_total'] for r in leak), 6)
        # instance-level sizing view: drive strength (cell name) against the load each gate drives
        sizing = []
        for g in range(self.n):
            d = drive_strength(ctx.cell[g])
            if d is not None:
                sizing.append((g, d, self.gate_fanout(g)))
        weak_loaded = sorted(((g, d, fo) for g, d, fo in sizing if d < 1 and fo >= HIGH_FANOUT_MIN),
                             key=lambda x: (x[0] not in self.critical, -x[2], x[0]))
        strong_light = sorted(((g, d, fo) for g, d, fo in sizing if d >= 2 and fo <= 1), key=lambda x: (-x[1], x[0]))
        missing = [r['cell'] for r in rows if not r['in_cell_library']]
        no_lib = [r['cell'] for r in rows if lib and not r['library_data']]
        source = ('liberty: ' + ', '.join(lib['files'])) if lib else 'pins: cell_library.json; function and drive: naming convention'
        return {'rows': rows, 'families': dict(fams.most_common()), 'totals': totals,
                'drive_mix': dict(sorted(Counter(f'X{d:g}' for _, d, _ in sizing).items(),
                                         key=lambda kv: float(kv[0][1:]))),
                'weak_drive_high_fanout': [{'gate': g, 'cell': ctx.cell[g], 'drive': d, 'fanout': fo,
                                            'on_longest_path': g in self.critical} for g, d, fo in weak_loaded[:20]],
                'strong_drive_light_load': [{'gate': g, 'cell': ctx.cell[g], 'drive': d, 'fanout': fo}
                                            for g, d, fo in strong_light[:20]],
                'cells_without_datasheet': missing, 'cells_without_library_data': no_lib,
                'library_loaded': bool(lib), 'source': source,
                'units': lib['units'] if lib else None,
                'note': ('Counts are exact (from the netlist). ' + (
                    'Area/leakage come from the loaded liberty file.' if lib else
                    'No liberty file is loaded, so there are no area, leakage or capacitance values; put a .lib file '
                    'in ML_VLSI/libs/ to add them.'))}

    def bom_summary(self, cell=None):
        b = self.bom
        if cell is not None:
            ds = cell_datasheet.datasheet(cell, self.liberty)
            row = next((r for r in b['rows'] if r['cell'] == cell), None)
            lines = [f"DATASHEET {cell} ({ds['description']}; family {ds['family']}):",
                     f"- pins: inputs {', '.join(ds['inputs']) or 'unknown'}; outputs {', '.join(ds['outputs']) or 'unknown'} "
                     f"(source: {ds['pins_source']})",
                     f"- function: {ds['function'] or 'not derivable from the name'} (source: {ds['function_source']})",
                     f"- drive strength: " + (f"X{ds['drive_strength']:g}" if ds['drive_strength'] is not None else 'unknown')
                     + f" (source: {ds['drive_source']})"]
            if ds['library_data']:
                lines.append(f"- area {ds['area']}, leakage {ds['leakage_power']} ({b['units']['leakage_power']} units), "
                             f"pin capacitance {ds['pin_capacitance']} ({b['units']['capacitance']} units) (source: liberty)")
            else:
                lines.append('- area / leakage / capacitance: not available (no liberty data for this cell)')
            lines.append(f"- used {row['count']} time(s) in this circuit, blocks "
                         + ', '.join(f'{k} {v}' for k, v in row['blocks'].items()) if row else '- not used in this circuit')
            return '\n'.join(lines)
        t = b['totals']
        lines = [f"CELL BOM: {t['instances']} instances of {t['cell_types']} cell types in {t['families']} families "
                 f"(counts exact; source: {b['source']})."]
        for r in b['rows'][:12]:
            lines.append(f"- {r['cell']}: {r['count']} ({round(r['share'] * 100, 1)}%), {r['description']}, drive "
                         + (f"X{r['drive_strength']:g}" if r['drive_strength'] is not None else '?')
                         + (f", area total {r['area_total']}" if 'area_total' in r else ''))
        if len(b['rows']) > 12:
            lines.append(f"- ... and {len(b['rows']) - 12} more cell types")
        lines.append('Drive strength mix (from cell names): ' + ', '.join(f'{k} {v}' for k, v in b['drive_mix'].items()))
        weak = [r for r in b['rows'] if r['drive_strength'] is not None and r['drive_strength'] < 1]
        if weak:
            lines.append('Cell types with drive below X1 (cell name): ' + ', '.join(
                f"{r['cell']} {r['count']}" for r in weak[:10]) + (f' (+{len(weak) - 10} more)' if len(weak) > 10 else ''))
        if 'area' in t:
            lines.append(f"Total cell area {t['area']} (library area units; covers {round(t['area_coverage'] * 100)}% of "
                         f"instances)" + (f"; total leakage {t['leakage_power']} ({b['units']['leakage_power']} units)"
                                          if 'leakage_power' in t else '') + '.')
        else:
            lines.append('No liberty file loaded: area, leakage and capacitance are not available.')
        if b['cells_without_datasheet']:
            lines.append('Cells with no datasheet entry (pins unknown): ' + ', '.join(b['cells_without_datasheet']))
        return '\n'.join(lines)

    def _bom_optimizations(self, add):
        b = self.bom
        base_add = add

        def add(*args, **kw):                        # same as _optimizations' add, tagged as BOM-derived
            base_add(*args, **kw)
            self._pending[-1]['source'] = 'bom'
        if b['weak_drive_high_fanout']:
            w = b['weak_drive_high_fanout']
            crit = [x for x in w if x['on_longest_path']]
            add('performance', f"{len(w)} weak-drive cell(s) driving {HIGH_FANOUT_MIN}+ loads",
                [x['gate'] for x in w],
                'A low-drive cell charging a large load is slow; the cell name says drive < X1.',
                '; '.join(f"G{x['gate']} {x['cell']} drives {x['fanout']} pins" for x in w[:5])
                + (f" ({len(crit)} on a longest path)" if crit else '') + '.',
                'Upsizing these cells or buffering their loads could reduce delay, at some area and power cost; '
                'unmeasured.', 'medium' if crit else 'low', 'structural heuristic')
        if b['strong_drive_light_load']:
            s = b['strong_drive_light_load']
            add('area', f"{len(s)} high-drive cell(s) (X2+) driving at most one load", [x['gate'] for x in s],
                'High-drive cells are larger and leak more; with one load or none the extra drive is rarely needed.',
                '; '.join(f"G{x['gate']} {x['cell']} drives {x['fanout']} pin(s)" for x in s[:5]) + '.',
                'Downsizing could reduce area and power if timing allows; unmeasured.', 'low', 'structural heuristic')
        buf = sum(r['count'] for r in b['rows'] if r['family'] in ('INV', 'BUF', 'BUFH'))
        if buf / max(self.n, 1) >= 0.15:
            gates = [g for r in b['rows'] if r['family'] in ('INV', 'BUF', 'BUFH') for g in r['gate_ids']]
            add('area', f"inverters/buffers are {round(100 * buf / self.n)}% of all cells ({buf})", gates,
                'A high share of inverters and buffers is overhead that computes no new function.',
                f"{buf} of {self.n} cells are INV/BUF/BUFH (cell BOM).",
                'Absorbing inversions into complex gates (e.g. NAND/NOR/AOI with inverted inputs) could reduce area '
                'and power; unmeasured.', 'low', 'structural heuristic')
        if self.liberty and 'area' in b['totals']:
            top = sorted((r for r in b['rows'] if 'area_total' in r), key=lambda r: -r['area_total'])[:3]
            add('area', 'largest area contributors by cell type: ' + ', '.join(r['cell'] for r in top),
                [g for r in top for g in r['gate_ids'][:20]],
                'These cell types account for the most cell area (count x library area).',
                '; '.join(f"{r['cell']}: {r['count']} x {r['area_each']} = {r['area_total']}" for r in top)
                + f" of total {b['totals']['area']} (library area units).",
                'Reducing or remapping these cells has the largest area effect; the numbers are library cell areas, '
                'not placed area.', 'high', 'deterministic')

    # ------------------------------------------------------------------ optimization candidates
    def _optimizations(self):
        t, a, p, s = self.timing, self.area, self.power, self.structure
        out = self._pending = []

        def add(category, target, gates, reason, evidence, impact, confidence, kind, nets=()):
            out.append({'category': category, 'target': target, 'gate_ids': list(gates)[:60], 'nets': list(nets)[:8],
                        'reason': reason, 'evidence': evidence, 'impact': impact, 'confidence': confidence,
                        'type': kind})

        if t.get('paths'):
            lp = t['paths'][0]
            nxt = t['paths'][1]['levels'] if len(t['paths']) > 1 else None
            add('performance', f"longest path {_gl([lp['gates'][0]], 1)} -> {_gl([lp['gates'][-1]], 1)} "
                f"({lp['levels']} gate levels)", lp['gates'],
                'Longest combinational dependency in the circuit (unit-delay gate levels).',
                f"{lp['levels']} gates in series: {' -> '.join(f'G{g}' for g in lp['gates'][:14])}"
                + (' ...' if lp['levels'] > 14 else '')
                + (f"; from input(s) {', '.join(lp['from_inputs'])}" if lp['from_inputs'] else '')
                + (f" to output(s) {', '.join(lp['to_outputs'])}" if lp['to_outputs'] else '')
                + (f"; the next output path has {nxt} levels" if nxt else '') + '.',
                'Could reduce worst-case propagation delay if logic on this path is restructured or rebalanced; '
                'actual benefit is unmeasured (no delay data).', 'medium', 'structural heuristic')
        for c in t.get('carry_chains', [])[:1]:
            if c['length'] >= 4:
                add('performance', f"ripple carry chain in {c['block']} ({c['length']} adder cells)", c['gates'],
                    'A ripple-carry chain: each stage waits for the previous carry, so the chain length sets the '
                    'carry delay.',
                    f"CO -> CI chain of {c['length']} full/half-adder cells: {_gl(c['gates'], 10)}.",
                    'A carry-lookahead or parallel-prefix structure could shorten the carry path, at the cost of area; '
                    'unmeasured.', 'medium', 'structural heuristic')
        loads = sorted((h for h in t.get('high_fanout', []) if h['fanout'] >= HIGH_FANOUT_MIN),
                       key=lambda h: (not h['on_longest_path'], -h['fanout'], h['net']))
        for h in loads[:3]:
            extra = []
            if h['on_longest_path']:
                extra.append('its driver is on a longest path')
            if h['weak_drive']:
                extra.append('the driver cell name indicates a low drive strength (naming convention)')
            add('performance', f"net {h['net']} (fan-out {h['fanout']})", h['driver_gates'] + h['reader_gates'][:20],
                'High fan-out load on one net' + (' and ' + ' and '.join(extra) if extra else '') + '.',
                f"{h['net']} is driven by {h['driver']} and read by {h['fanout']} pins.",
                'Buffering, cloning the driver or upsizing it could reduce load-dependent delay; unmeasured.',
                'medium' if h['on_longest_path'] else 'low', 'structural heuristic', nets=[h['net']])
        for sel in p.get('select_outputs', [])[:1]:
            sizes = {c['bus']: c['cone_gates'] for c in p['cones']}
            ctrl_gates = [g for c in s['control_signals'][:1] for g in c['gates']]
            add('power', f"output {sel['to']} selects between {', '.join(sel['from'])}", ctrl_gates,
                'The output picks one of several results that are all computed in parallel from the same inputs, '
                'so every result block switches whatever the select signal chooses.',
                f"{sel['to']} has a select-like dependency cone over {', '.join(sel['from'])} "
                f"(cone sizes: {', '.join(f'{b} {sizes.get(b, 0)} gates' for b in sel['from'])})"
                + (f"; control signal(s): {', '.join(c['net'] for c in s['control_signals'][:2])}"
                   if s['control_signals'] else '') + '.',
                'Operand isolation or gating of the unselected block could reduce dynamic power; unmeasured '
                '(no activity data).', 'medium', 'structural heuristic')
        for h in p.get('high_fanout', [])[:2]:
            if h['fanout'] >= HIGH_FANOUT_MIN:
                add('power', f"net {h['net']} (fan-out {h['fanout']})", h['driver_gates'] + h['reader_gates'][:20],
                    'A high fan-out net switches a large load each time it toggles.',
                    f"{h['net']} drives {h['fanout']} pins (driver: {h['driver']}).",
                    'Restructuring or reducing this load could reduce dynamic power if the net toggles often; '
                    'switching activity is unknown.', 'low', 'structural heuristic', nets=[h['net']])
        if p.get('cones'):
            c = p['cones'][0]
            add('power', f"logic cone of {c['bus']} ({c['cone_gates']} gates)", [],
                'The largest combinational cone; large XOR/adder-rich cones are typical high-activity and '
                'glitch-prone regions.',
                f"{c['bus']} depends on {c['cone_gates']} gates, {c['xor_adder_cells']} of them XOR/XNOR/adder cells.",
                'Worth investigating first for dynamic power once activity data is available; unmeasured.',
                'low', 'structural heuristic')
        for d in a.get('duplicate_groups', [])[:3]:
            add('area', f"duplicate {d['cell_function']} gates {_gl(d['gates'], 6)}", d['gates'],
                'These gates have the same cell function and read the same net on every input pin, so they compute '
                'the same signal.',
                f"{len(d['gates'])} x {d['cell_function']} with inputs {', '.join(d['inputs'])}.",
                f"Merging them would remove {len(d['gates']) - 1} gate(s) and their switching; the kept gate's "
                'fan-out grows, which can affect delay.', 'high', 'deterministic')
        if a.get('logic_without_output_path'):
            gs = a['logic_without_output_path']
            add('area', f"{len(gs)} gate(s) whose outputs never reach a primary output", gs,
                'Logic with no path to any output does not affect the circuit outputs.',
                f"Reported by the reachability/connectivity checks: {_gl(gs, 10)}.",
                'Removing it would save those gates, unless a missing connection should make it reachable '
                '(check the related findings first).', 'high', 'deterministic')
        if a.get('inverter_pairs'):
            pr = a['inverter_pairs'][:5]
            add('area', f"{len(a['inverter_pairs'])} back-to-back inverter pair(s)", [g for x in pr for g in x],
                'Two inverters in series restore the original signal.',
                'Pairs: ' + '; '.join(f'G{x} -> G{y}' for x, y in pr) + '.',
                'Removing a pair saves two gates, unless it was inserted deliberately as a buffer.',
                'medium', 'structural heuristic')
        if s['blocks'] and s['blocks'][0]['share'] >= 0.4 and len(s['blocks']) > 1:
            b = s['blocks'][0]
            add('area', f"block {b['name']} ({b['gates']} gates, {round(b['share'] * 100)}% of the circuit)", [],
                'The block holding most of the logic; architectural choices there dominate the gate count.',
                f"{b['name']} has {b['gates']} of {self.n} gates; main cells: "
                + ', '.join(f'{k} {v}' for k, v in b['top_cells'].items()) + '.',
                'Area reduction efforts here (e.g. a different architecture for this function) have the largest '
                'potential effect; unmeasured.', 'low', 'structural heuristic')
        self._bom_optimizations(add)
        order = {'performance': 0, 'power': 1, 'area': 2}
        out.sort(key=lambda o: order[o['category']])
        for i, o in enumerate(out, 1):
            o['id'] = f'O{i}'
        return out

    # ------------------------------------------------------------------ text summaries (code-written)
    def _plain_language_purpose(self, structure):
        """A short, non-jargon-first explanation for the dashboard and assistant."""
        roles = {b.get('inferred_role') for b in structure['blocks']}
        operand_inputs = [p for p in structure['inputs'] if p['width'] > 1]
        if {'adder', 'multiplier'} <= roles and structure['control_signals'] and len(operand_inputs) >= 2 and structure['outputs']:
            left, right = operand_inputs[:2]
            result = structure['outputs'][0]
            control = structure['control_signals'][0]['net']
            return (f"This is an add-or-multiply unit. It takes {left['name']} and {right['name']}, calculates "
                    f"both answers in parallel, then {control} selects which answer reaches {result['name']}. "
                    f"The netlist shows that it selects a result, but does not by itself prove which value of "
                    f"{control} means add or multiply.")
        return self.a['intent'].get('summary_for_layman') or 'The circuit purpose is not yet known.'

    def overview_summary(self):
        s = self.structure
        it = self.a['intent']
        lines = ['In simple terms: ' + s['plain_purpose'],
                 f"Inferred function: {it.get('intended_function')} (confidence {it.get('confidence')}, "
                 f"source {it.get('source')}; derived from dependency cones and names, not verified design data).",
                 'Inputs: ' + ', '.join(f"{p['name']}[{p['width']}]" if p['width'] > 1 else p['name'] for p in s['inputs']),
                 'Outputs: ' + ', '.join(f"{p['name']}[{p['width']}]" if p['width'] > 1 else p['name'] for p in s['outputs'])]
        if s['control_signals']:
            lines.append('Control signals: ' + '; '.join(f"{c['net']} ({c['why']}, fan-out {c['fanout']})"
                                                         for c in s['control_signals'][:4]))
        else:
            lines.append('Control signals: none detected (no mux select pins or narrow non-operand inputs).')
        lines.append('Blocks (hierarchy, by gate count): ' + '; '.join(
            f"{b['name']} {b['gates']} gates" + (f" ({b['inferred_role']})" if b['inferred_role'] else '')
            for b in s['blocks'][:6]))
        if s['datapath_chains']:
            lines.append('Datapaths: ' + ' | '.join(s['datapath_chains'][:4]))
        if s['block_connections']:
            lines.append('Block connections: ' + '; '.join(
                f"{d['from']} -> {d['to']} via {', '.join(d['via'][:3])}" for d in s['block_connections'][:6]))
        lines.append('Purely combinational (no registers or clock cells).' if s['combinational_only']
                     else 'Sequential cells present: ' + ', '.join(s['sequential_cells'][:5]))
        return '\n'.join(lines)

    def timing_summary(self):
        t = self.timing
        lines = ['TIMING (structural only: unit-delay gate levels; no delay data, so no ns/ps values exist).']
        if not t['max_depth']:
            return lines[0] + '\nNo gate levels could be computed.'
        lines.append(f"Maximum logic depth: {t['max_depth']} gate levels; {t['critical_gate_count']} gate(s) lie on "
                     f"a longest path.")
        for i, p in enumerate(t['paths'][:3], 1):
            lines.append(f"Path {i} ({p['levels']} levels): " + ' -> '.join(f'G{g}' for g in p['gates'][:16])
                         + (' ...' if p['levels'] > 16 else '')
                         + (f"; from {', '.join(p['from_inputs'])}" if p['from_inputs'] else '')
                         + (f"; to output {', '.join(p['to_outputs'])}" if p['to_outputs'] else '')
                         + f"; blocks {', '.join(p['blocks'][:3])}")
        if t['slowest_outputs']:
            lines.append('Deepest outputs: ' + ', '.join(f"{o['output']} ({o['levels']} levels)"
                                                         for o in t['slowest_outputs'][:5]))
        for c in t['carry_chains'][:2]:
            lines.append(f"Ripple carry chain: {c['length']} adder cells in {c['block']} ({_gl(c['gates'], 6)}).")
        if t['high_fanout']:
            lines.append('Highest fan-out nets: ' + '; '.join(
                f"{h['net']} {h['fanout']} loads, driven by {h['driver']}"
                + (' (driver on a longest path)' if h['on_longest_path'] else '') for h in t['high_fanout'][:5]))
        return '\n'.join(lines)

    def gate_timing_summary(self, g):
        x = self.gate_timing(g)
        lines = [f"G{g} ({x['cell']}, block {x['block']}) timing indicators (structural; no delay data):",
                 f"- {x['levels_from_inputs']} gate level(s) from the primary inputs up to G{g}; "
                 f"{x['levels_to_end']} level(s) from G{g} to the end of its longest downstream path.",
                 f"- the longest path through G{g} has {x['longest_path_through_gate']} levels; the circuit maximum is "
                 f"{x['circuit_max_depth']}.",
                 f"- G{g} is {'ON' if x['on_longest_path'] else 'NOT on'} a longest (critical) path"
                 + ('' if x['on_longest_path'] else f" ({x['level_slack']} level(s) shorter than the longest path)") + '.',
                 f"- fan-out: G{g} drives {x['fanout_pins']} pin(s) ({_gl(x['fanout_gates'])}); fan-in gates: "
                 f"{_gl(x['fanin_gates'])}."]
        if x['drive_strength_from_name'] is not None:
            lines.append(f"- drive strength from the cell name suffix: X{x['drive_strength_from_name']:g} "
                         f"(naming convention, not library data).")
        if x['on_longest_path']:
            p = self._path_to(max((h for h in self.critical if self.through[h] == self.max_depth
                                   and self._reaches(g, h)), key=lambda h: (self.level_in[h], -h), default=g))
            if g in p:
                lines.append('- a longest path through it: ' + ' -> '.join(f'G{h}' for h in p[:18])
                             + (' ...' if len(p) > 18 else ''))
        return '\n'.join(lines)

    def _reaches(self, a, b):
        if a == b:
            return True
        seen, q = {a}, deque([a])
        while q:
            g = q.popleft()
            for h in self.ctx.succ[g]:
                if h == b:
                    return True
                if h not in seen and self.level_in[h] <= self.level_in[b]:
                    seen.add(h)
                    q.append(h)
        return False

    def power_summary(self):
        p = self.power
        lines = ['POWER (structural indicators only: no switching activity or power data, so no mW/uW values '
                 'exist). Regions worth investigating:']
        if p['combinational_only']:
            lines.append('- the circuit is purely combinational: there is no clock network or register power.')
        for sel in p['select_outputs'][:2]:
            lines.append(f"- {sel['to']} selects between {', '.join(sel['from'])}: all of these results are computed "
                         f"in parallel, so every block switches regardless of the selection.")
        for c in p['cones'][:4]:
            lines.append(f"- logic cone of {c['bus']}: {c['cone_gates']} gates, {c['xor_adder_cells']} XOR/XNOR/adder "
                         f"cells (larger, XOR-rich cones are typical high-activity regions).")
        for h in p['high_fanout'][:4]:
            lines.append(f"- high fan-out net {h['net']}: {h['fanout']} loads (driver {h['driver']}).")
        for c in p['control_signals'][:2]:
            lines.append(f"- control signal {c['net']} fans out to {c['fanout']} pins; each toggle switches them all.")
        if p['duplicate_gate_count']:
            lines.append(f"- {p['duplicate_gate_count']} redundant duplicate gate(s) switch without adding function.")
        return '\n'.join(lines)

    def area_summary(self, block=None):
        a = self.area
        lines = ['AREA (gate counts as a proxy; no cell area data, so no um^2 values exist).',
                 f"Total: {a['total_gates']} gates."]
        blocks = [b for b in a['blocks'] if block is None or b['name'] == block]
        for b in blocks[:6]:
            lines.append(f"- block {b['name']}: {b['gates']} gates ({round(b['share'] * 100)}%); main cells "
                         + ', '.join(f'{k} {v}' for k, v in b['top_cells'].items()))
        if block is None:
            lines.append('Densest sub-blocks: ' + ', '.join(f"{d['prefix']} {d['gates']}" for d in a['densest_sub_blocks'][:4]))
            lines.append('Cell families: ' + ', '.join(f'{k} {v}' for k, v in list(a['cell_families'].items())[:8]))
        if a['duplicate_groups']:
            lines.append(f"Duplicate logic (deterministic): {a['duplicate_gate_count']} redundant gate(s), e.g. "
                         + '; '.join(_gl(d['gates'], 4) + f" ({d['cell_function']})" for d in a['duplicate_groups'][:3]))
        else:
            lines.append('Duplicate logic: none found (no two gates of the same function read identical inputs).')
        if a['inverter_pairs']:
            lines.append(f"Back-to-back inverter pairs: {len(a['inverter_pairs'])}, e.g. "
                         + '; '.join(f'G{x} -> G{y}' for x, y in a['inverter_pairs'][:3]))
        if a['logic_without_output_path']:
            lines.append(f"Logic with no path to an output: {_gl(a['logic_without_output_path'], 8)}")
        return '\n'.join(lines)

    def optimization_summary(self, items):
        if not items:
            return 'No optimization candidates matched.'
        lines = ['OPTIMIZATION CANDIDATES (to investigate; none of these has been measured):']
        for o in items:
            lines.append(f"{o['id']} [{o['category']}] target: {o['target']}. Reason: {o['reason']} Evidence: "
                         f"{o['evidence']} Potential impact: {o['impact']} Confidence: {o['confidence']}. "
                         f"Type: {o['type']}.")
        return '\n'.join(lines)

    def optimizations_for(self, category=None, gate_id=None):
        items = [o for o in self.optimizations if category in (None, o['category'])]
        if gate_id is not None:
            items = [o for o in items if gate_id in o['gate_ids']]
        return items

    # ------------------------------------------------------------------ GraphSAINT regions
    def region(self, gate_id=None, module=None):
        """ML prediction for a region (predicted module) kept apart from the netlist facts about the same gates."""
        if not self.subcircuits:
            return {'error': 'no predictions are available for this circuit'}
        if module is None and gate_id is not None:
            module = self.module_of.get(gate_id)
        if module is None or not 1 <= module <= len(self.subcircuits):
            return {'error': f'unknown module {module!r}; valid modules are 1..{len(self.subcircuits)}'}
        sc = self.subcircuits[module - 1]
        gates = sorted(sc['gate_ids'])
        gs = set(gates)
        names = [self.m['nodes'][g]['class_name'] for g in gates]
        agree = sum(1 for nm in names if nm == sc['class_name'])
        probs = None
        if self.probs is not None and len(self.probs) == self.n:
            mx = [max(self.probs[g]) for g in gates if self.probs[g]]
            if mx:
                probs = {'mean_max_probability': round(sum(mx) / len(mx), 3), 'min_max_probability': round(min(mx), 3),
                         'gates_below_0.6': sum(1 for v in mx if v < cc.LOW_PROB_THRESHOLD)}
        boundary = Counter()
        for g in gates:
            for h in self.ctx.succ[g] | self.ctx.pred[g]:
                if h not in gs:
                    boundary[cc.CLASS_NAMES[self.preds[h]]] += 1
        ml_findings = [f for f in self.findings if f['category'] == 'gnn_suspicion' and gs & set(f['gate_ids'])]
        det_findings = [f for f in self.findings if f['category'] != 'gnn_suspicion' and gs & set(f['gate_ids'])]
        blocks = Counter(self.blocks[g] for g in gates)
        cells = Counter(cell_base(self.ctx.cell[g]) for g in gates)
        predictor = 'GraphSAINT' if self.source == 'graphsaint' else 'the baseline GCN (weak model)'
        lines = [f"Module #{module}: {len(gates)} gate(s) ({_gl(gates, 10)}).",
                 f"ML PREDICTION ({predictor}, not a circuit fact): every gate of this module is predicted "
                 f"{sc['class_name']}; a module is a connected group of gates with the same predicted class."]
        if probs:
            lines.append(f"ML PREDICTION confidence: mean max class probability {probs['mean_max_probability']}, "
                         f"lowest {probs['min_max_probability']}; {probs['gates_below_0.6']} gate(s) below 0.6.")
        else:
            lines.append('ML PREDICTION confidence: per-gate probabilities are not available for this circuit.')
        if ml_findings:
            lines.append('ML-BASED HINTS on these gates: ' + '; '.join(f"{f['id']} ({f['check']})" for f in ml_findings[:4])
                         + '. These are model-based suspicions, not wiring faults.')
        lines.append(f"STRUCTURAL FACT: instance-name labels agree with the prediction on {agree} of {len(gates)} gate(s)"
                     f" (labels come from instance names, a heuristic).")
        lines.append('STRUCTURAL FACT: hierarchy blocks ' + ', '.join(f'{b} {c}' for b, c in blocks.most_common(3))
                     + '; cells ' + ', '.join(f'{k} {v}' for k, v in cells.most_common(5)) + '.')
        if boundary:
            lines.append('STRUCTURAL FACT: neighbouring gates outside the module are predicted '
                         + ', '.join(f'{k} ({v} connection(s))' for k, v in boundary.most_common()) + '.')
        if det_findings:
            lines.append('STRUCTURAL FACT: deterministic findings on these gates: '
                         + '; '.join(f"{f['id']} ({f['check']}, {f['severity']})" for f in det_findings[:5]) + '.')
        else:
            lines.append('STRUCTURAL FACT: no deterministic connectivity finding touches these gates, so any '
                         'suspicion here is ML-only.')
        return {'summary': '\n'.join(lines), 'module': module, 'size': len(gates), 'gate_ids': gates[:200],
                'predicted_class': sc['class_name'], 'predictor': self.source, 'probabilities': probs,
                'name_label_agreement': [agree, len(gates)], 'ml_findings': [f['id'] for f in ml_findings],
                'deterministic_findings': [f['id'] for f in det_findings], 'blocks': dict(blocks)}

    def suspicious_regions(self, top=5):
        """Predicted modules touched by model-based hints, most-hinted first."""
        score = Counter()
        for f in self.findings:
            if f['category'] != 'gnn_suspicion':
                continue
            for g in f['gate_ids']:
                if g in self.module_of:
                    score[self.module_of[g]] += 1
        return [m for m, _ in score.most_common(top)]

    def data_availability(self):
        if not self.liberty:
            return DATA_AVAILABILITY
        return dict(DATA_AVAILABILITY, cell_area=True, power_data='leakage only', note=(
            f"Liberty data loaded ({', '.join(self.liberty['files'])}): cell area, leakage power and pin capacitance "
            'per cell type are library values. There is still no delay analysis, no switching activity and no '
            'placement, so dynamic power and timing in ns are not available; gate levels and fan-out remain '
            'structural indicators.'))

    def ppa_values(self):
        """Library-derived numbers the assistant may quote (everything else with a PPA unit is rejected)."""
        vals = set()
        for r in self.bom['rows']:
            for k in ('area_each', 'area_total', 'leakage_each', 'leakage_total'):
                if r.get(k) is not None:
                    vals.add(float(r[k]))
        for k in ('area', 'leakage_power'):
            if k in self.bom['totals']:
                vals.add(float(self.bom['totals'][k]))
        return vals

    def capabilities(self):
        return {
            'understand': {'supported': True, 'mode': 'deterministic'},
            'debug': {'supported': True, 'mode': 'deterministic'},
            'timing': {'supported': self.max_depth > 0, 'mode': 'structural',
                       'note': 'gate levels and fan-out only; no delay data'},
            'power': {'supported': True, 'mode': 'structural', 'note': 'structural indicators only; no activity data'},
            'area': {'supported': True, 'mode': 'structural', 'note': 'gate counts only; no cell area data'},
            'optimize': {'supported': bool(self.optimizations), 'mode': 'structural'},
            'bom': {'supported': True, 'mode': 'liberty' if self.liberty else 'naming',
                    'note': 'counts exact; ' + ('area/leakage from liberty' if self.liberty else
                                                'no liberty file: pins + naming convention only')},
            'graphsaint': {'supported': bool(self.subcircuits) and self.source == 'graphsaint',
                           'mode': self.source or 'none',
                           'note': None if self.source == 'graphsaint' else
                           'no GraphSAINT prediction for this circuit; only a weak baseline GCN'},
        }

    def public(self):
        """JSON for /api/insights (deterministic; no LLM)."""
        return {'data_availability': self.data_availability(), 'capabilities': self.capabilities(),
                'bom': {k: v for k, v in self.bom.items()},
                'structure': self.structure, 'timing': self.timing, 'power': self.power, 'area': self.area,
                'optimizations': self.optimizations, 'prediction_source': self.source,
                'modules': len(self.subcircuits), 'suspicious_modules': self.suspicious_regions()}


def compute(model, analysis, liberty=None):
    return Insights(model, analysis, liberty)
