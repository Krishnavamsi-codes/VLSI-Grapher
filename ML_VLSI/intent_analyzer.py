"""
intent_analyzer.py - What is this circuit meant to be?

1. collect_evidence(): deterministic facts (no LLM): buses, cell histogram, blocks
   (hierarchy prefixes), block->block dataflow, predicted-class distribution,
   sub-circuits and per-bus dependency-cone signatures.
2. deterministic_intent(): an intent built from the cone signatures alone
   (used when the LLM is unavailable; lower confidence).
3. llm_intent(): the LLM interprets the evidence (strict JSON schema). Every bus,
   prefix and block it names is validated; invalid templates are dropped.

The LLM never sees file names, header comments or netlist text: only the evidence
dict built here.
"""

import json
import re
from collections import Counter, defaultdict

import circuit_checks as cc
from grounding import Grounder
from llm_client import LLMError

ROLES = ['adder', 'multiplier', 'subtractor', 'comparator', 'control', 'unknown']
NAME_HINT_RE = re.compile(r'add|sum|mul|mult|prod|sub|diff|comp|cmp|mux|sel|alu|carry', re.I)
CLASS_NAMES = cc.CLASS_NAMES
CIRCUIT_ALIAS = 'circuit under analysis'


def _cell_base(cell):
    return re.sub(r'_X\w+$', '', cell)


def _block_of(prefix):
    return prefix.split('/')[0] if prefix else 'top'


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------

def _pattern(dep, W, live=None):
    """Classify [(sig, S)] rows of a target bus w.r.t. one operand of width W.
    `live` = operand significances that are actually driven (declared-but-unused bits excluded)."""
    live = frozenset(range(W)) if live is None else live
    if len(live) < cc.MIN_BUS_WIDTH:
        return 'too_small'
    if len(dep) < cc.MIN_BUS_WIDTH:     # narrow result (e.g. comparator flags): only 'full' is meaningful
        return 'full' if all(S >= live for _, S in dep) else 'too_small'
    # bitwise first: bit s depends only on source bit s (a mux/select), which also has the
    # triangular "upper edge" but none of the lower-bit dependencies
    if all(S <= {s - 1, s} for s, S in dep) and sum(1 for s, _ in dep if s >= 2) >= 2:
        return 'bitwise'
    top = max(live)
    shaped = []
    for s, S in dep:
        exp = cc.expected_support(s, live)
        if exp and S <= exp and max(S) == max(exp):
            shaped.append(s)
    if len(shaped) >= 0.6 * len(dep) and sum(1 for s in shaped if s < top) >= 2:
        return 'triangular'
    if all(S >= live for _, S in dep):
        return 'full'
    return 'partial'


def _profiles(model, ctx, order, target_bits, sources):
    """One support pass w.r.t. all bits of `sources` (bus names); returns
    {target: {source_bus: [(sig, S)]}} with S = set of source significances."""
    flat, spans = [], {}
    for b in sources:
        bits = [cc._canon(model, x) for x in model['buses'][b]['bits']]
        spans[b] = (len(flat), len(bits), cc.live_significances(model, b))
        flat += bits
    _, net_sup = cc.support_wrt(ctx, flat, order)
    out = {}
    for t, tbits in target_bits.items():
        per = {}
        sups = [(sig, net_sup.driven(net)) for sig, net in tbits]
        for b, (start, width, live) in spans.items():
            if b == t:
                continue
            rows = [(sig, frozenset(i for i in range(width) if (s >> (start + i)) & 1)) for sig, s in sups]
            dep = [(sig, S) for sig, S in rows if S]
            if dep:
                per[b] = (dep, width, live)
        out[t] = per
    return out


def _cone_signatures(model, ctx, order):
    """Classify each non-input bus (and scalar output) by its dependency cone."""
    buses = model['buses']
    in_buses = [n for n, b in buses.items() if b['kind'] == 'input']
    targets = [n for n, b in buses.items() if b['kind'] != 'input' and b['width'] >= 2]
    targets += [po for po in model['primary_outputs'] if po not in model['bit_info']]
    internal = [n for n, b in buses.items() if b['kind'] != 'input']
    target_bits = {t: cc._target_bits(model, t) for t in targets}
    target_bits = {t: b for t, b in target_bits.items() if b}
    wrt_inputs = _profiles(model, ctx, order, target_bits, in_buses)       # through internal buses
    wrt_internal = _profiles(model, ctx, order, target_bits, internal)     # stops at internal bus bits
    sigs = []
    for t, tbits in target_bits.items():
        per_operand = {}
        for a, (dep, W, live) in wrt_inputs[t].items():
            exact = sum(1 for s, S in dep if S == cc.expected_support(s, live))
            per_operand[a] = {'pattern': _pattern(dep, W, live), 'operand_width': len(live),
                              'bits_with_dependency': len(dep), 'bits_matching_exactly': exact}
        feeds = {b: {'pattern': _pattern(dep, W, live), 'source_width': len(live)}
                 for b, (dep, W, live) in wrt_internal[t].items()}
        # inverted-operand evidence: operand bits read by an inverter inside this bus's cone
        cone = set()
        for _, net in tbits:
            cone |= cc._cone_gates(ctx, net)
        inv_ratio = {}
        for a in per_operand:
            bits = set(cc._canon(model, b) for b in buses[a]['bits'])
            inverted = {n for g in cone if ctx.cell[g].startswith('INV') for _, n in ctx.in_nets[g] if n in bits}
            inv_ratio[a] = round(len(inverted) / max(len(bits), 1), 2)
        drivers = Counter(model['hier_prefix'][d['gate_id']] for _, net in tbits
                          for d in model['nets'][net]['drivers'] if 'gate_id' in d)
        sigs.append({'bus': t, 'width': len(tbits), 'operands': per_operand, 'fed_by_buses': feeds,
                     'operand_bits_inverted_in_cone': inv_ratio,
                     'driver_prefixes': [p or 'top' for p, _ in drivers.most_common(3)],
                     'classification': None})
    # classification
    for s in sigs:
        tri = {a: o for a, o in s['operands'].items() if o['pattern'] == 'triangular'}
        full = {a: o for a, o in s['operands'].items() if o['pattern'] == 'full'}
        feeds = s['fed_by_buses']
        bitwise_feeds = sorted(b for b, f in feeds.items() if f['pattern'] == 'bitwise')
        tri_feeds = sorted(b for b, f in feeds.items() if f['pattern'] == 'triangular')
        if len(bitwise_feeds) >= 2:
            s['classification'] = 'select-like'
            s['selects_between'] = bitwise_feeds
        elif len(tri_feeds) >= 2:
            # arithmetic on internal buses, e.g. (a+b)*(c+d): compare with the feeds' driven widths
            W = max(feeds[b]['source_width'] for b in tri_feeds)
            s['classification'] = 'multiplier-like' if s['width'] >= 1.75 * W else 'adder-like'
            s['operand_buses'] = tri_feeds
            s['operand_width'] = W
        elif tri:
            W = max(o['operand_width'] for o in tri.values())
            dep = max(o['bits_with_dependency'] for o in tri.values())
            if dep >= 1.75 * W:
                s['classification'] = 'multiplier-like'
            else:
                inv = s['operand_bits_inverted_in_cone']
                ops = sorted(tri, key=lambda a: -inv.get(a, 0))
                if len(ops) >= 2 and inv.get(ops[0], 0) >= 0.5 and inv.get(ops[1], 0) <= 0.25:
                    s['classification'] = 'subtractor-like'
                    s['subtrahend'] = ops[0]
                    s['minuend'] = ops[1]
                else:
                    s['classification'] = 'adder-like'
            s['operand_buses'] = sorted(tri)
        elif full and s['width'] <= 2 and len(full) >= 2:
            s['classification'] = 'comparator-like'
            s['operand_buses'] = sorted(full)
        else:
            s['classification'] = 'unclassified'
            s['operand_buses'] = sorted(s['operands'])
    return sigs


def collect_evidence(model, check_result, predictions, prediction_source, ref_kind, honesty):
    ctx = cc._Ctx(model)
    order, cyclic = cc._topo_order(ctx)
    order = order + cyclic

    blocks = defaultdict(lambda: {'gates': 0, 'cells': Counter(), 'sub_prefixes': set(), 'pred': Counter()})
    for g in range(ctx.n):
        pfx = model['hier_prefix'][g]
        b = blocks[_block_of(pfx)]
        b['gates'] += 1
        b['cells'][_cell_base(ctx.cell[g])] += 1
        if pfx:
            b['sub_prefixes'].add(pfx)
        if predictions is not None:
            b['pred'][CLASS_NAMES[predictions[g]]] += 1

    flow = defaultdict(set)
    for net, e in model['nets'].items():
        src = {_block_of(model['hier_prefix'][d['gate_id']]) for d in e['drivers'] if 'gate_id' in d}
        dst = {_block_of(model['hier_prefix'][r['gate_id']]) for r in e['readers'] if 'gate_id' in r}
        via = model['bit_info'].get(net, {}).get('bus') or next(
            (model['bit_info'][a]['bus'] for a in e['aliases'] if a in model['bit_info']), None)
        for s in src:
            for d in dst:
                if s != d:
                    flow[(s, d)].add(via or '(internal nets)')

    cells = Counter(_cell_base(c) for c in ctx.cell)
    arith = sum(v for k, v in cells.items() if k.startswith(('ADDF', 'ADDH', 'XOR', 'XNOR', 'MAJ')))
    name_tokens = sorted({t.lower() for p in model['hier_prefix'] for t in NAME_HINT_RE.findall(p)} |
                         {t.lower() for b in model['buses'] for t in NAME_HINT_RE.findall(b)} |
                         {t.lower() for t in NAME_HINT_RE.findall(model['module_name'])})
    subs = cc.extract_subcircuit_boundaries(model['nodes'], model['edges'], list(predictions)) \
        if predictions is not None else []
    stats = check_result['stats']

    return {
        'circuit': {'alias': CIRCUIT_ALIAS, 'module_name': model['module_name'], 'source': ref_kind,
                    'num_gates': ctx.n, 'num_nets': len(model['nets']),
                    'primary_input_bits': len(model['primary_inputs']),
                    'primary_output_bits': len(model['primary_outputs'])},
        'honesty_notes': honesty,
        'buses': [{'name': n, 'direction': b['kind'], 'width': b['width'], 'declared': f'[{b["msb"]}:{b["lsb"]}]',
                   'index_order': 'MSB-first (index 0 is the most significant bit)' if b['msb'] < b['lsb']
                   else 'LSB-first (index 0 is the least significant bit)'}
                  for n, b in model['buses'].items()],
        'scalar_ports': [p for p in model['primary_inputs'] + model['primary_outputs'] if p not in model['bit_info']],
        'cell_histogram': dict(cells.most_common(15)),
        'arithmetic_cell_share': round(arith / max(ctx.n, 1), 3),
        'name_hints': name_tokens,
        'names_look_obfuscated': not name_tokens,
        'blocks': [{'name': k, 'gates': v['gates'], 'top_cells': dict(v['cells'].most_common(5)),
                    'hier_prefixes': sorted(v['sub_prefixes'])[:8],
                    'predicted_classes': dict(v['pred'])} for k, v in sorted(blocks.items())],
        'dataflow': [{'from_block': s, 'to_block': d, 'via': sorted(v)[:6]} for (s, d), v in sorted(flow.items())],
        'predicted_class_distribution': {'source': prediction_source,
                                         'counts': dict(Counter(CLASS_NAMES[p] for p in predictions))
                                         if predictions is not None else {}},
        'subcircuits': {'count': len(subs), 'largest': [{'class': s['class_name'], 'size': s['size']}
                                                        for s in sorted(subs, key=lambda s: -s['size'])[:8]]},
        'cone_signatures': _cone_signatures(model, ctx, order),
        'check_summary': {'errors': stats['errors'], 'warnings': stats['warnings'], 'infos': stats['infos'],
                          'by_check': stats['by_check']},
    }


# ---------------------------------------------------------------------------
# Deterministic intent (fallback)
# ---------------------------------------------------------------------------

ROLE_OF = {'adder-like': 'adder', 'multiplier-like': 'multiplier', 'subtractor-like': 'subtractor',
           'comparator-like': 'comparator', 'select-like': 'control'}


def _templates_for(sig, prefixes):
    role = ROLE_OF.get(sig['classification'])
    ops = sig.get('operand_buses', [])
    base = {'out_bus': sig['bus'], 'in_buses': ops, 'block_prefix': None, 'minuend': None, 'subtrahend': None}
    out = []
    if role == 'adder' and ops:
        out.append({'template': 'adder_triangular', 'params': base})
        for p in prefixes:
            out.append({'template': 'carry_chain', 'params': dict(base, out_bus=None, in_buses=[], block_prefix=p)})
    elif role == 'multiplier' and ops:
        out.append({'template': 'multiplier_pp_complete', 'params': base})
    elif role == 'subtractor':
        out.append({'template': 'subtractor_inverted',
                    'params': dict(base, in_buses=[], minuend=sig['minuend'], subtrahend=sig['subtrahend'])})
    elif role == 'comparator' and ops:
        out.append({'template': 'comparator_all_bits', 'params': base})
    return out


def deterministic_intent(evidence):
    blocks, templates, phrases = [], [], []
    by_bus = {}
    for s in evidence['cone_signatures']:
        role = ROLE_OF.get(s['classification'])
        if role is None:
            continue
        W = s.get('operand_width') or max((o['operand_width'] for a, o in s['operands'].items()
                                           if a in s.get('operand_buses', [])), default=s['width'])
        prefixes = [p for p in s['driver_prefixes'] if p != 'top']
        name = prefixes[0].split('/')[0] if prefixes else f'{role}_{s["bus"]}'
        if any(b['name'] == name for b in blocks):
            name = f'{name}:{s["bus"]}'
        ins = s.get('selects_between', []) if role == 'control' else s.get('operand_buses', [])
        blocks.append({'name': name, 'role': role, 'width': W, 'input_buses': ins, 'output_buses': [s['bus']],
                       'hier_prefixes': [p for p in prefixes if p != 'top'][:3],
                       'evidence': f'{s["bus"]}: {s["classification"]} dependency cone'
                                   + (f' w.r.t. {", ".join(s.get("operand_buses", []))}' if s.get('operand_buses') else '')
                                   + (f', selects between {", ".join(s["selects_between"])}' if role == 'control' else '')})
        by_bus[s['bus']] = name
        templates += _templates_for(s, prefixes[:2])
        phrases.append({'adder': f'{W}-bit adder', 'multiplier': f'{W}x{W} multiplier',
                        'subtractor': f'{W}-bit subtractor', 'comparator': f'{W}-bit comparator',
                        'control': 'output select logic'}[role])
    dataflow = []
    for b in blocks:
        for bus in b['input_buses']:
            if bus in by_bus and by_bus[bus] != b['name']:
                dataflow.append({'from_block': by_bus[bus], 'to_block': b['name'], 'via_bus': bus})

    obfuscated = evidence['names_look_obfuscated']
    if blocks:
        conf = 0.55 * (0.6 if obfuscated else 1.0)
    else:
        conf = 0.1
    fn = ', '.join(dict.fromkeys(phrases)) if phrases else 'unknown combinational logic'
    feeding = [f'{d["from_block"]} feeds {d["to_block"]} via {d["via_bus"]}' for d in dataflow]
    return {
        'intended_function': fn[:1].upper() + fn[1:],
        'summary_for_layman': (f'This looks like {fn}.' if blocks else
                               'The structure does not match a known arithmetic pattern, so its purpose is unclear.')
                              + (' Names give no hints, so this is a structural guess.' if obfuscated else ''),
        'blocks': blocks,
        'dataflow': dataflow,
        'expected_connections': templates,
        'unchecked_rules': [],
        'confidence': round(conf, 2),
        'reasoning': ('Derived from dependency-cone signatures only (no language model). '
                      + ('; '.join(b['evidence'] for b in blocks) + '. ' if blocks else '')
                      + ('; '.join(feeding) + '.' if feeding else '')).strip(),
        'source': 'deterministic',
    }


# ---------------------------------------------------------------------------
# LLM intent
# ---------------------------------------------------------------------------

_NULLABLE_STR = {'type': ['string', 'null']}
INTENT_SCHEMA = {
    'type': 'object', 'additionalProperties': False,
    'required': ['intended_function', 'summary_for_layman', 'blocks', 'dataflow', 'expected_connections',
                 'unchecked_rules', 'confidence', 'reasoning'],
    'properties': {
        'intended_function': {'type': 'string'},
        'summary_for_layman': {'type': 'string'},
        'blocks': {'type': 'array', 'items': {
            'type': 'object', 'additionalProperties': False,
            'required': ['name', 'role', 'width', 'input_buses', 'output_buses', 'hier_prefixes', 'evidence'],
            'properties': {
                'name': {'type': 'string'}, 'role': {'type': 'string', 'enum': ROLES},
                'width': {'type': 'integer'},
                'input_buses': {'type': 'array', 'items': {'type': 'string'}},
                'output_buses': {'type': 'array', 'items': {'type': 'string'}},
                'hier_prefixes': {'type': 'array', 'items': {'type': 'string'}},
                'evidence': {'type': 'string'}}}},
        'dataflow': {'type': 'array', 'items': {
            'type': 'object', 'additionalProperties': False, 'required': ['from_block', 'to_block', 'via_bus'],
            'properties': {'from_block': {'type': 'string'}, 'to_block': {'type': 'string'},
                           'via_bus': {'type': 'string'}}}},
        'expected_connections': {'type': 'array', 'items': {
            'type': 'object', 'additionalProperties': False, 'required': ['template', 'params'],
            'properties': {
                'template': {'type': 'string', 'enum': list(cc.INTENT_TEMPLATES)},
                'params': {'type': 'object', 'additionalProperties': False,
                           'required': ['out_bus', 'in_buses', 'block_prefix', 'minuend', 'subtrahend'],
                           'properties': {'out_bus': _NULLABLE_STR, 'in_buses': {'type': 'array', 'items': {'type': 'string'}},
                                          'block_prefix': _NULLABLE_STR, 'minuend': _NULLABLE_STR,
                                          'subtrahend': _NULLABLE_STR}}}}},
        'unchecked_rules': {'type': 'array', 'items': {'type': 'string'}},
        'confidence': {'type': 'number'},
        'reasoning': {'type': 'string'},
    },
}

INTENT_INSTRUCTIONS = """You are a digital-design reverse-engineering assistant. You receive deterministic evidence
extracted from a flattened gate-level netlist (the "circuit under analysis"). Infer what the circuit is meant to do.

Rules:
- Use ONLY the evidence given. Bus, prefix and block names you output must appear in the evidence exactly.
- Cite buses as [B:<bus>], nets as [N:<net>], gates as [G<id>] in free text.
- Buses may be MSB-first: respect the stated index_order.
- dependency-cone signatures are the strongest evidence; hierarchy names are hints only (labels in this dataset
  are derived from instance names). If names give no hints or evidence is weak, confidence must be <= 0.4 and you
  must say so. Never exceed 0.95.
- expected_connections: choose templates that the code can check. params: out_bus = the result bus, in_buses =
  operand buses, block_prefix = hierarchy prefix (carry_chain only), minuend/subtrahend (subtractor_inverted only).
  Unused params must be null / empty. Put anything else you expect into unchecked_rules.
- Model predictions (GraphSAINT/baseline) are suspicions, not facts.
- summary_for_layman: 1-2 plain sentences, no jargon.
"""


def _validate_intent(raw, model, evidence):
    g = Grounder(model, [], ())
    prefixes = set(p for p in model['hier_prefix'] if p)
    prefixes |= {p.split('/')[0] for p in prefixes}
    notes, dropped_templates = [], []

    def prefix_ok(p):
        return isinstance(p, str) and p.rstrip('/') in prefixes

    blocks = []
    for b in raw['blocks']:
        b = dict(b)
        b['input_buses'] = g.bus_list(b['input_buses'], f'intent.blocks[{b["name"]}].input_buses', allow_nets=True)
        b['output_buses'] = g.bus_list(b['output_buses'], f'intent.blocks[{b["name"]}].output_buses', allow_nets=True)
        good = [p for p in b['hier_prefixes'] if prefix_ok(p)]
        for p in b['hier_prefixes']:
            if p not in good:
                g._drop(f'prefix:{p}', f'intent.blocks[{b["name"]}].hier_prefixes')
        b['hier_prefixes'] = good
        b['width'] = max(0, int(b['width']))
        b['evidence'] = g.clean_text(b['evidence'], 'intent.blocks.evidence')
        blocks.append(b)
    names = {b['name'] for b in blocks}
    dataflow = []
    for d in raw['dataflow']:
        if d['from_block'] in names and d['to_block'] in names and g.bus_or_net_ok(d['via_bus']):
            dataflow.append(d)
        else:
            g._drop(f'dataflow {d}', 'intent.dataflow')

    templates = []
    for t in raw['expected_connections']:
        kind, p = t['template'], t['params']
        why = None
        if kind in ('adder_triangular', 'multiplier_pp_complete', 'comparator_all_bits'):
            if not g.bus_or_net_ok(p.get('out_bus')):
                why = f'unknown out_bus {p.get("out_bus")!r}'
            elif not p.get('in_buses') or not all(g.bus_ok(x) for x in p['in_buses']):
                why = f'invalid in_buses {p.get("in_buses")}'
        elif kind == 'subtractor_inverted':
            if not g.bus_or_net_ok(p.get('out_bus')) or not g.bus_ok(p.get('minuend')) or not g.bus_ok(p.get('subtrahend')):
                why = f'invalid out_bus/minuend/subtrahend ({p.get("out_bus")}, {p.get("minuend")}, {p.get("subtrahend")})'
        elif kind == 'carry_chain':
            if not prefix_ok(p.get('block_prefix')):
                why = f'unknown block_prefix {p.get("block_prefix")!r}'
        else:
            why = f'unknown template {kind!r}'
        if why:
            dropped_templates.append({'template': kind, 'params': p, 'reason': why})
        else:
            templates.append({'template': kind, 'params': p})

    conf = float(raw['confidence'])
    conf = max(0.0, min(conf, 0.95))
    if evidence['names_look_obfuscated']:
        conf = min(conf, 0.4)
        notes.append('Confidence capped at 0.4: names give no functional hints.')
    if evidence['circuit']['source'] == 'upload' and not evidence['cone_signatures']:
        conf = min(conf, 0.3)
    return {
        'intended_function': raw['intended_function'],
        'summary_for_layman': g.clean_text(raw['summary_for_layman'], 'intent.summary_for_layman'),
        'blocks': blocks, 'dataflow': dataflow, 'expected_connections': templates,
        'unchecked_rules': [g.clean_text(r, 'intent.unchecked_rules') for r in raw['unchecked_rules']],
        'confidence': round(conf, 2),
        'reasoning': g.clean_text(raw['reasoning'], 'intent.reasoning'),
        'source': 'llm', 'dropped_templates': dropped_templates, 'dropped_refs': g.dropped, 'notes': notes,
    }


def llm_intent(llm, evidence, model, fallback):
    payload = {'evidence': evidence, 'deterministic_hypothesis': {
        k: fallback[k] for k in ('intended_function', 'blocks', 'dataflow', 'expected_connections', 'confidence')}}
    res = llm.create(purpose='intent', instructions=INTENT_INSTRUCTIONS,
                     input=[{'role': 'user', 'content': json.dumps(payload, separators=(',', ':'))}],
                     schema=INTENT_SCHEMA, schema_name='circuit_intent',
                     effort=llm.config.effort_report, max_output_tokens=12000)
    raw = res.parsed
    if not isinstance(raw, dict) or any(k not in raw for k in INTENT_SCHEMA['required']):
        raise LLMError('The model returned an intent that does not match the required schema', kind='schema')
    intent = _validate_intent(raw, model, evidence)
    intent['usage'] = res.usage
    return intent
