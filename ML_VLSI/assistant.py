"""
assistant.py - Auto report + multi-turn chat on top of the deterministic analysis.

Division of labour: all detection is done in code (circuit_checks); the LLM only
explains, ranks and suggests. Everything the LLM returns passes through the
Grounder, and the server enforces what the LLM may not decide:
  * health        = computed from findings (errors > warnings > ok)
  * item severity = the most severe cited finding
  * certainty     = fact / likely / suspicion from the cited findings
  * every report item must cite at least one real finding (no invented issues)
  * suggested edges come only from cited findings (the LLM cannot draw new ones)
  * Verilog snippets are always labelled "Suggestion, not applied"
The LLM never receives file names, header comments or netlist text.
"""

import json
import re
import threading
import time
import uuid
from collections import Counter, OrderedDict, deque

import circuit_checks as cc
from grounding import Grounder
from intent_analyzer import CIRCUIT_ALIAS
from llm_client import LLMError

MAX_TOOL_CALLS = 6
TOOL_OUTPUT_CHARS = 4000
MAX_TURNS = 20
MAX_SESSIONS = 100
SESSION_TTL_S = 3600
MAX_MESSAGE_CHARS = 2000
CHAT_MAX_OUTPUT_TOKENS_LOCAL = 1024
SUGGESTION_LABEL = '// Suggestion, not applied'

RULES = """Hard rules:
1. Ground every claim in the findings, intent or tool outputs you were given. Never invent gates, nets, buses or
   problems.
2. Cite references exactly as [G<id>] for gates, [N:<net>] for nets, [F<id>] for findings (e.g. [F001]) and
   [B:<bus>] for buses. Also list them in the structured fields.
3. Certainty wording: electrical/reachability findings with confidence 1.0 are FACTS ("is"); structural and intent
   findings are LIKELY ("likely", "appears to"); model-based findings are SUSPICIONS ("the model suspects").
4. Suggestions only: never claim anything was fixed or applied. Any Verilog you show is a suggestion; start it with
   the line "// Suggestion, not applied".
5. Honesty: functional labels come from instance-name heuristics; GraphSAINT metrics of training circuits are
   training-set results; uploads have no GraphSAINT prediction. If evidence is weak or names are obfuscated, say so.
6. Buses may be declared MSB-first ([0:15] means index 0 is the MSB). Talk about bit significance, not raw indices,
   when that matters.
"""


def _compact_finding(f, evidence_chars=400):
    out = {'id': f['id'], 'check': f['check'], 'category': f['category'], 'severity': f['severity'],
           'certainty': f.get('certainty') or cc.certainty(f), 'confidence': f['confidence'],
           'evidence': f['evidence'][:evidence_chars], 'gate_ids': f['gate_ids'][:12], 'nets': f['nets'][:6]}
    if f['suggested_edges']:
        out['suggested_edges'] = f['suggested_edges'][:4]
    for k in ('bus', 'bit_run', 'count', 'size'):
        if k in f:
            out[k] = f[k]
    return out


def _edge_text(e):
    src = f"G{e['from_gate']} pin {e.get('from_pin')}" if e.get('from_gate') is not None else f"net {e.get('from_net')}"
    if e.get('to_gate') is not None:
        dst = f"G{e['to_gate']} pin {e.get('to_pin')}"
    else:
        dst = f"primary output {e.get('to_po')}"
    text = f'connect {src} to {dst}'
    if e.get('replaces_net'):
        text += f" (instead of net {e['replaces_net']})"
    if e.get('ambiguous'):
        text += ' (ambiguous: one of the candidates is the extra driver)'
    return text


def _strip_comment_lines(text):
    """Drop Verilog comment lines a small model sometimes puts into prose fields."""
    kept = [l for l in (text or '').splitlines() if not l.strip().startswith('//')]
    return ' '.join(l.strip() for l in kept if l.strip())


def suggested_fix_text(edges):
    """The finding's suggested edges as one sentence; code-written, so the fix never depends on the LLM."""
    return ('Repair computed by the connectivity checks (a suggestion; not applied automatically): '
            + '; '.join(_edge_text(e) for e in edges[:4]) + '.')


def _ref_gates(model, texts, nets=(), buses=()):
    """Gates behind every [N:..]/[B:..] reference, so the UI can make those chips clickable."""
    nets, buses = set(nets), set(buses)
    for t in texts:
        refs = Grounder.refs_in(t or '')
        nets |= set(refs['nets'])
        buses |= set(refs['buses'])
    out = {'nets': {}, 'buses': {}}

    def gates_of(net):
        canon = cc._canon(model, net)
        e = model['nets'].get(canon)
        if e is None:
            return []
        return sorted({x['gate_id'] for x in e['drivers'] + e['readers'] if 'gate_id' in x})[:20]

    for n in sorted(nets)[:40]:
        g = gates_of(n)
        if g:
            out['nets'][n] = g
    for b in sorted(buses)[:10]:
        if b in model['buses']:
            gs = []
            for bit in model['buses'][b]['bits'][:64]:
                e = model['nets'].get(cc._canon(model, bit))
                if e:
                    gs += [d['gate_id'] for d in e['drivers'] if 'gate_id' in d]
            out['buses'][b] = sorted(set(gs))[:64]
    return out


def require_keys(parsed, schema, what):
    """Defence in depth: strict mode should guarantee the shape, but never trust it blindly."""
    if not isinstance(parsed, dict) or any(k not in parsed for k in schema['required']):
        raise LLMError(f'The model returned a {what} that does not match the required schema', kind='schema')
    return parsed


def _health(findings):
    if any(f['severity'] == 'error' for f in findings):
        return 'errors'
    if any(f['severity'] == 'warning' for f in findings):
        return 'warnings'
    return 'ok'


def _checks_passed(findings):
    fired = {f['check'] for f in findings if f['severity'] in ('error', 'warning')}
    return [f'{name}: {desc}' for name, (cat, _, desc) in cc.CHECK_CATALOG.items()
            if cat != 'gnn_suspicion' and name not in fired and name not in ('const_input', 'unknown_cell')]


def llm_context(analysis):
    """Everything the LLM may know about the circuit. No file names, no netlist text."""
    intent = analysis['intent']
    findings = analysis['findings']
    main = [f for f in findings if f['category'] != 'gnn_suspicion']
    model_based = [f for f in findings if f['category'] == 'gnn_suspicion']
    return {
        'circuit': {'alias': CIRCUIT_ALIAS, 'module_name': analysis['module_name'],
                    'source': analysis['evidence']['circuit']['source'],
                    'num_gates': analysis['stats']['num_gates'], 'num_nets': analysis['stats']['num_nets']},
        'honesty_notes': analysis['honesty_notes'],
        'intent': {k: intent.get(k) for k in ('intended_function', 'summary_for_layman', 'blocks', 'dataflow',
                                              'confidence', 'source')},
        'template_results': [{'template': t['template'], 'target': t['params'].get('out_bus') or t['params'].get('block_prefix'),
                              'status': t['status'], 'finding_ids': t['finding_ids'], 'note': t['note']}
                             for t in intent.get('template_results', [])],
        'health': _health(findings),
        'counts': {'errors': analysis['stats']['errors'], 'warnings': analysis['stats']['warnings'],
                   'infos': analysis['stats']['infos']},
        'findings': [_compact_finding(f) for f in main[:60]],
        'model_based_suspicions': [{'id': f['id'], 'check': f['check'], 'count': f.get('count', len(f['gate_ids'])),
                                    'evidence': f['evidence'][:200]} for f in model_based[:30]],
        'checks_passed': _checks_passed(findings),
        'prediction_source': analysis['prediction_source'],
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

REPORT_SCHEMA = {
    'type': 'object', 'additionalProperties': False,
    'required': ['summary', 'health', 'items', 'clean_confirmation'],
    'properties': {
        'summary': {'type': 'string'},
        'health': {'type': 'string', 'enum': ['ok', 'warnings', 'errors']},
        'items': {'type': 'array', 'items': {
            'type': 'object', 'additionalProperties': False,
            'required': ['title', 'severity', 'certainty', 'what', 'where', 'why_it_matters', 'fix',
                         'verilog_suggestion', 'finding_ids', 'gate_ids'],
            'properties': {
                'title': {'type': 'string'},
                'severity': {'type': 'string', 'enum': ['error', 'warning', 'info']},
                'certainty': {'type': 'string', 'enum': ['fact', 'likely', 'suspicion']},
                'what': {'type': 'string'}, 'where': {'type': 'string'},
                'why_it_matters': {'type': 'string'}, 'fix': {'type': 'string'},
                'verilog_suggestion': {'type': ['string', 'null']},
                'finding_ids': {'type': 'array', 'items': {'type': 'string'}},
                'gate_ids': {'type': 'array', 'items': {'type': 'integer'}}}}},
        'clean_confirmation': {'type': 'string'},
    },
}

REPORT_INSTRUCTIONS = """You write the health report for a gate-level netlist ("circuit under analysis") for an
engineer. You receive the inferred intent and the findings of deterministic checks.

""" + RULES + """
Report rules:
- summary: 2-4 sentences: what the circuit is (with intent confidence) and its overall health.
- items: one item per real problem, ranked: errors first, then by impact on the intended function. Merge findings
  that describe the same root cause into one item (cite all their ids). Every item MUST cite finding_ids from the
  list. Put ALL model-based suspicions into ONE final item (certainty "suspicion", severity "info").
- where: block / bit significance / gates, with [G..]/[N..]/[B..] refs.
- why_it_matters: the concrete impact on THIS circuit's intended function.
- fix: concrete steps (which pin to connect to which net). Use the finding's suggested_edges when present; if a
  suggestion is marked ambiguous, say that one of the candidates is the extra driver.
- verilog_suggestion: a short instance-level snippet or null. Start it with "// Suggestion, not applied".
- If there are no errors or warnings: say clearly that no connection problems were found, do not invent issues,
  and fill clean_confirmation with what was checked and passed (from checks_passed). Otherwise clean_confirmation
  lists the checks that did pass.
"""


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

def _tool(name, description, props, required):
    return {'type': 'function', 'name': name, 'description': description, 'strict': True,
            'parameters': {'type': 'object', 'additionalProperties': False, 'properties': props,
                           'required': required}}


_INT = {'type': 'integer'}
_STR = {'type': 'string'}
TOOLS = [
    _tool('get_gate', 'Details of one gate: cell, block, pin->net connections, fan-in/fan-out gates, findings.',
          {'gate_id': _INT}, ['gate_id']),
    _tool('get_neighborhood', 'Gates within `hops` (1-2) of a gate and the edges among them (max_nodes <= 50).',
          {'gate_id': _INT, 'hops': _INT, 'max_nodes': {'type': ['integer', 'null']}},
          ['gate_id', 'hops', 'max_nodes']),
    _tool('get_net', 'One net (wire) or one bus bit such as Result_add[12]: driver(s), readers, bus bit significance '
                     '(0 = least significant), related findings. Copy escaped names exactly, including a leading '
                     'backslash.', {'name': _STR}, ['name']),
    _tool('trace_path', 'Shortest signal path between two gates (either direction), up to max_nodes (<=200).',
          {'from_id': _INT, 'to_id': _INT, 'max_nodes': {'type': ['integer', 'null']}},
          ['from_id', 'to_id', 'max_nodes']),
    _tool('list_findings', 'List findings, optionally filtered by category and/or severity.',
          {'category': {'type': ['string', 'null'],
                        'enum': ['electrical', 'reachability', 'structural', 'intent', 'gnn_suspicion', None]},
           'severity': {'type': ['string', 'null'], 'enum': ['error', 'warning', 'info', None]}},
          ['category', 'severity']),
    _tool('get_block', 'A block (hierarchy prefix or inferred block name): size, cells, buses, dataflow.',
          {'name': _STR}, ['name']),
    _tool('get_bus', 'A whole bus such as Result_add: every bit (LSB first) with significance and drivers, and its '
                     'dependency-cone signature.',
          {'name': _STR}, ['name']),
    _tool('explain_finding', 'Full details of one finding (evidence, gates, nets, suggested edges).',
          {'finding_id': _STR}, ['finding_id']),
]


class CircuitTools:
    def __init__(self, model, analysis):
        self.m = model
        self.a = analysis
        self.ctx = cc._Ctx(model)
        self.findings = {f['id']: f for f in analysis['findings']}
        self.preds = analysis.get('predictions')
        self.by_gate = {}
        for f in analysis['findings']:
            for g in f['gate_ids']:
                self.by_gate.setdefault(g, []).append(f['id'])

    def _gate_brief(self, g):
        brief = {'id': g, 'instance': self.ctx.inst[g], 'cell': self.ctx.cell[g],
                 'block': self.m['hier_prefix'][g] or 'top'}
        if self.preds:
            brief['predicted_class'] = cc.CLASS_NAMES[self.preds[g]]
        return brief

    @staticmethod
    def _endpoint(x):
        if 'gate_id' in x:
            return f"G{x['gate_id']} pin {x['pin']}"
        if 'pi' in x:
            return f"primary input {x['pi']}"
        if 'po' in x:
            return f"primary output {x['po']}"
        return str(x)

    def _pin_info(self, g, pin, net):
        """One pin with the gates on the other side of its net, so the model need not infer connectivity."""
        info = {'pin': pin, 'direction': self.m['gate_dirs'][g][pin], 'net': net}
        e = self.m['nets'].get(cc._canon(self.m, net)) if net else None
        if info['direction'] == 'output':
            info['read_by'] = [self._endpoint(r) for r in (e['readers'] if e else [])][:10]
        else:
            info['driven_by'] = [self._endpoint(d) for d in (e['drivers'] if e else [])]
        return info

    def _find_net(self, name):
        nets = self.m['nets']
        s = name.strip()
        for cand in (name, s, s[1:] if s.startswith('\\') else '\\' + s):
            if cand in nets:
                return cand
            alias = next((k for k, v in nets.items() if cand in v['aliases']), None)
            if alias is not None:
                return alias
        return None

    def _gate_err(self, g):
        return {'error': f'unknown gate id {g!r}; valid ids are 0..{self.ctx.n - 1}'}

    def _ok_gate(self, g):
        return isinstance(g, int) and not isinstance(g, bool) and 0 <= g < self.ctx.n

    def call(self, name, args):
        fn = getattr(self, 't_' + name, None)
        if fn is None:
            return {'error': f'unknown tool {name!r}'}
        try:
            return fn(**args)
        except TypeError as exc:
            return {'error': f'bad arguments for {name}: {exc}'}

    def t_get_gate(self, gate_id):
        if not self._ok_gate(gate_id):
            return self._gate_err(gate_id)
        g = gate_id
        preds = self.a.get('predictions')
        pins = [self._pin_info(g, p, n) for p, n in self.m['gate_pins'][g].items()]
        missing = [mp['pin'] for mp in self.m['missing_pins'] if mp['gate_id'] == g]
        fan_in, fan_out = sorted(self.ctx.pred[g])[:20], sorted(self.ctx.succ[g])[:20]
        label = self.m['nodes'][g]['class_name']
        predicted = cc.CLASS_NAMES[preds[g]] if preds else None
        findings = self.by_gate.get(g, [])
        out = {'summary': self._gate_summary(g, pins, missing, fan_in, fan_out, label, predicted, findings)}
        out.update(self._gate_brief(g))
        out.update(pins=pins, missing_pins=missing, fan_in_gates=fan_in, fan_out_gates=fan_out,
                   name_heuristic_label=label, predicted_class=predicted,
                   prediction_source=self.a.get('prediction_source'), findings=findings)
        return out

    def _predictor(self):
        return 'GraphSAINT' if self.a.get('prediction_source') == 'graphsaint' else 'The baseline model'

    def _gate_summary(self, g, pins, missing, fan_in, fan_out, label, predicted, findings):
        """Facts written by code, one per line, so a small model can quote them instead of interpreting raw fields."""
        gl = lambda ids: ', '.join(f'G{x}' for x in ids) or 'none'
        lines = [f"G{g}: instance {self.ctx.inst[g]}, cell type {self.ctx.cell[g]}, block "
                 f"{self.m['hier_prefix'][g] or 'top'}. Arrows show signal direction (left drives right)."]
        for p in pins:
            if 'driven_by' in p:
                lines.append(f"- input pin {p['pin']}: {' and '.join(p['driven_by']) or 'nothing'} -> G{g} pin "
                             f"{p['pin']} (net {p['net']})")
            else:
                lines.append(f"- output pin {p['pin']}: G{g} pin {p['pin']} -> {', '.join(p['read_by']) or 'nothing'} "
                             f"(net {p['net']})")
        lines += [f"- unconnected pin {x}" for x in missing]
        lines.append(f"- fan-in (gates that feed G{g}): {gl(fan_in)}")
        lines.append(f"- fan-out (gates that G{g} feeds): {gl(fan_out)}")
        if predicted:
            agree = 'agrees' if predicted == label else 'disagrees'
            lines.append(f"- instance-name label: {label}; {self._predictor()} prediction: {predicted} "
                         f"({agree} with the label; a prediction, not a fact)")
        lines.append(f"- findings on this gate: {', '.join(findings) or 'none'}")
        return '\n'.join(lines)

    def _endpoint_long(self, x):
        text = self._endpoint(x)
        if 'gate_id' in x:
            g = x['gate_id']
            text += (f" (instance {self.ctx.inst[g]}, cell {self.ctx.cell[g]}, "
                     f"block {self.m['hier_prefix'][g] or 'top'})")
        return text

    def t_get_neighborhood(self, gate_id, hops, max_nodes=None):
        if not self._ok_gate(gate_id):
            return self._gate_err(gate_id)
        hops = max(1, min(int(hops or 1), 2))
        cap = max(1, min(int(max_nodes or 50), 50))
        seen, frontier = {gate_id}, [gate_id]
        for _ in range(hops):
            nxt = []
            for g in frontier:
                for h in sorted(self.ctx.succ[g] | self.ctx.pred[g]):
                    if h not in seen and len(seen) < cap:
                        seen.add(h)
                        nxt.append(h)
            frontier = nxt
        edges = [[u, v] for u in seen for v in self.ctx.succ[u] if v in seen]
        nodes = [self._gate_brief(g) for g in sorted(seen)]
        summary = f"{len(nodes)} gates within {hops} hop(s) of G{gate_id}: " + ', '.join(f"G{g}" for g in sorted(seen)) + '.'
        if self.preds:
            lines = [f"- G{n['id']}{' (center)' if n['id'] == gate_id else ''}: {self._predictor()} predicts "
                     f"{n['predicted_class']} (one class per gate; a prediction, not a fact)" for n in nodes]
            counts = Counter(n['predicted_class'] for n in nodes)
            summary += '\n' + '\n'.join(lines) + '\n- totals: ' + ', '.join(f'{k} {v}' for k, v in counts.most_common())
        return {'summary': summary, 'center': gate_id, 'hops': hops, 'nodes': nodes,
                'edges': edges, 'truncated': len(seen) >= cap}

    def t_get_net(self, name):
        canon = self._find_net(name) if isinstance(name, str) else None
        if canon is None:
            bus = name.strip() if isinstance(name, str) else None
            if bus in self.m['buses']:
                first = self.m['buses'][bus]['bits'][0] if self.m['buses'][bus]['bits'] else bus
                return dict(self.t_get_bus(bus), note=f'{bus!r} is a bus, not a single net; showing the whole bus. '
                                                      f'Ask for one bit by name, e.g. {first}.')
            return {'error': f'unknown net {name!r}'}
        e = self.m['nets'][canon]
        fmt = lambda x: dict(x, instance=self.ctx.inst[x['gate_id']]) if 'gate_id' in x else x
        info = self.m['bit_info'].get(canon)
        drivers = ' and '.join(self._endpoint(d) for d in e['drivers']) or 'nothing (undriven)'
        lines = [f"Net {canon}. Arrows show signal direction (left drives right)."]
        lines += [f"- {drivers} -> {self._endpoint(r)}" for r in e['readers'][:10]] or [f"- {drivers} -> nothing (unread)"]
        if len(e['readers']) > 10:
            lines.append(f"- and {len(e['readers']) - 10} more readers")
        lines += [f"- driver: {self._endpoint_long(d)}" for d in e['drivers']] or ['- driver: none (undriven)']
        lines += [f"- reader: {self._endpoint_long(r)}" for r in e['readers'][:10]]
        if info:
            lines.append(f"- bit of bus {info['bus']}, significance {info['significance']} (0 = least significant)")
        summary = '\n'.join(lines)
        return {'summary': summary, 'name': canon, 'aliases': e['aliases'], 'drivers': [fmt(d) for d in e['drivers']],
                'readers': [fmt(r) for r in e['readers'][:30]], 'num_readers': len(e['readers']),
                'bus_bit': info, 'findings': [f['id'] for f in self.a['findings'] if canon in f['nets']]}

    def t_trace_path(self, from_id, to_id, max_nodes=None):
        if not self._ok_gate(from_id):
            return self._gate_err(from_id)
        if not self._ok_gate(to_id):
            return self._gate_err(to_id)
        cap = max(2, min(int(max_nodes or 200), 200))
        for a, b, direction in ((from_id, to_id, 'forward'), (to_id, from_id, 'backward')):
            prev = {a: None}
            q = deque([a])
            while q and b not in prev:
                g = q.popleft()
                for h in sorted(self.ctx.succ[g]):
                    if h not in prev:
                        prev[h] = g
                        q.append(h)
            if b in prev:
                path = []
                g = b
                while g is not None:
                    path.append(g)
                    g = prev[g]
                path.reverse()
                flow = ' -> '.join(f'G{x}' for x in path[:cap])     # always in signal-flow order here
                if direction == 'backward':
                    path.reverse()
                summary = (f"Signal path ({len(path)} gates) in signal-flow order: {flow}. "
                           + ('' if direction == 'forward' else
                              f"No path from G{from_id} to G{to_id}; the signal flows the other way. ")
                           + "Only the gates listed are on the path.")
                return {'summary': summary,
                        'direction': 'signal flows ' + ('from_id -> to_id' if direction == 'forward'
                                                         else 'to_id -> from_id'),
                        'length': len(path), 'path': [self._gate_brief(g) for g in path[:cap]],
                        'truncated': len(path) > cap}
        return {'error': f'no signal path between G{from_id} and G{to_id} in either direction'}

    def t_list_findings(self, category=None, severity=None):
        fs = [f for f in self.a['findings'] if (category is None or f['category'] == category)
              and (severity is None or f['severity'] == severity)]
        out = []
        for f in fs[:40]:
            item = {'id': f['id'], 'check': f['check'], 'category': f['category'], 'severity': f['severity'],
                    'certainty': f.get('certainty'), 'evidence': f['evidence'][:160]}
            if f['suggested_edges']:
                item['suggested_fix'] = suggested_fix_text(f['suggested_edges'])
            out.append(item)
        wiring = [f['id'] for f in fs if f['category'] != 'gnn_suspicion' and f['severity'] in ('error', 'warning')]
        hints = [f['id'] for f in fs if f['category'] == 'gnn_suspicion']
        summary = (f"{len(fs)} finding(s).\n- real problems found by the deterministic connectivity checks "
                   f"(errors/warnings): {', '.join(wiring) or 'none'}\n"
                   f"- model-based hints from GNN predictions (not wiring faults): {', '.join(hints) or 'none'}")
        return {'summary': summary, 'count': len(fs), 'findings': out}

    def t_get_block(self, name):
        ev = next((b for b in self.a['evidence']['blocks'] if b['name'] == name), None)
        inferred = [b for b in self.a['intent'].get('blocks', [])
                    if b['name'] == name or name in b.get('hier_prefixes', [])]
        if ev is None and not inferred:
            names = [b['name'] for b in self.a['evidence']['blocks']] + [b['name'] for b in self.a['intent'].get('blocks', [])]
            return {'error': f'unknown block {name!r}; known: {names[:20]}'}
        flow = [d for d in self.a['evidence']['dataflow'] if name in (d['from_block'], d['to_block'])]
        return {'hierarchy_block': ev, 'inferred_blocks': inferred, 'dataflow': flow}

    def t_get_bus(self, name):
        bus = self.m['buses'].get(name)
        if bus is None:
            return {'error': f'unknown bus {name!r}; known: {sorted(self.m["buses"])[:30]}'}
        bits = []
        for sig, b in enumerate(bus['bits'][:64]):
            canon = cc._canon(self.m, b)
            e = self.m['nets'].get(canon)
            drv = [dict(d, instance=self.ctx.inst[d['gate_id']]) if 'gate_id' in d else d
                   for d in (e['drivers'] if e else [])]
            bits.append({'bit': b, 'significance': sig, 'drivers': drv, 'num_readers': len(e['readers']) if e else 0})
        sig = next((s for s in self.a['evidence']['cone_signatures'] if s['bus'] == name), None)
        return {'name': name, 'direction': bus['kind'], 'declared': f'[{bus["msb"]}:{bus["lsb"]}]',
                'width': bus['width'], 'bits_lsb_first': bits, 'truncated': bus['width'] > 64,
                'cone_signature': sig}

    def t_explain_finding(self, finding_id):
        f = self.findings.get(finding_id)
        if f is None:
            return {'error': f'unknown finding {finding_id!r}; known: {sorted(self.findings)[:30]}'}
        kind = ('a model-based hint from the GNN predictions, not a wiring fault' if f['category'] == 'gnn_suspicion'
                else f"a {f['certainty'] if f.get('certainty') else cc.certainty(f)} {f['category']} finding")
        summary = f"{f['id']} ({f['check']}, severity {f['severity']}) is {kind}. Evidence: {f['evidence'][:400]}"
        if f['suggested_edges']:
            summary += ' Fix: ' + suggested_fix_text(f['suggested_edges'])
        out = {'summary': summary}
        out.update(_compact_finding(f, 2000))
        out.update(gates=[self._gate_brief(g) for g in f['gate_ids'][:8]], pins=f['pins'][:8],
                   suggested_edges=f['suggested_edges'][:8])
        return out


def _truncate(obj):
    text = json.dumps(obj, separators=(',', ':'), default=str)
    if len(text) > TOOL_OUTPUT_CHARS:
        text = text[:TOOL_OUTPUT_CHARS - 40] + '... [truncated to 4000 characters]'
    return text


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------

class SessionStore:
    """In-memory chat sessions: LRU capped, TTL-expired, one lock per session."""

    def __init__(self, max_sessions=MAX_SESSIONS, ttl=SESSION_TTL_S, max_turns=MAX_TURNS, clock=time.time):
        self.max_sessions, self.ttl, self.max_turns, self.clock = max_sessions, ttl, max_turns, clock
        self._s = OrderedDict()
        self._lock = threading.Lock()

    def get(self, session_id, circuit_key):
        now = self.clock()
        with self._lock:
            for sid in [k for k, v in self._s.items() if now - v['last_used'] > self.ttl]:
                del self._s[sid]
            s = self._s.get(session_id) if session_id else None
            if s is None or s['circuit_key'] != circuit_key:
                session_id = session_id if (s is not None and session_id) else uuid.uuid4().hex
                s = {'id': session_id, 'circuit_key': circuit_key, 'turns': [], 'last_used': now,
                     'lock': threading.Lock()}
                self._s[session_id] = s
            s['last_used'] = now
            self._s.move_to_end(session_id)
            while len(self._s) > self.max_sessions:
                self._s.popitem(last=False)
            return s

    def add_turn(self, s, user, assistant_text):
        with self._lock:
            s['turns'].append((user, assistant_text))
            del s['turns'][:-self.max_turns]

    def __len__(self):
        with self._lock:
            return len(self._s)


CHAT_SCHEMA = {
    'type': 'object', 'additionalProperties': False, 'required': ['reply', 'highlights'],
    'properties': {
        'reply': {'type': 'string'},
        'highlights': {'type': 'object', 'additionalProperties': False,
                       'required': ['gate_ids', 'nets', 'finding_ids', 'edges'],
                       'properties': {
                           'gate_ids': {'type': 'array', 'items': {'type': 'integer'}},
                           'nets': {'type': 'array', 'items': {'type': 'string'}},
                           'finding_ids': {'type': 'array', 'items': {'type': 'string'}},
                           'edges': {'type': 'array', 'items': {
                               'type': 'object', 'additionalProperties': False,
                               'required': ['from_gate', 'to_gate'],
                               'properties': {'from_gate': {'type': 'integer'}, 'to_gate': {'type': 'integer'}}}}}},
    },
}

CHAT_INSTRUCTIONS = """You are the Circuit Assistant inside a gate-level netlist viewer. You answer questions about ONE
circuit (the "circuit under analysis") using only the context below and the tool results in the conversation.

Words to keep apart:
- Gate ID: G<number>, e.g. G23 (the viewer's index). Instance name: e.g. adder_1/intadd_0/U5. Cell type: the library
  cell, e.g. ADDF_X1M_A9TH. Never mix these up.
- Pins: each pin has a direction (input or output) and a net. For input pins, driven_by says what drives the net; for
  output pins, read_by says which gates read it. Fan-in gates drive this gate; fan-out gates read its outputs.
  Do not guess what a pin does from its name: report pin name, direction and net as given.
- Net: one signal connection with driver(s) and readers. Names may start with a backslash (escaped Verilog names such as
  \\adder_1/intadd_0/n4): copy every name exactly as the tools give it.
- Bus: a group of bits such as Result_add; one bit is Result_add[12]. significance 0 = least significant bit. Buses
  may be declared MSB-first, so the index is not the significance.
- name_heuristic_label is a label taken from instance names. predicted_class comes from the GraphSAINT model (or a
  weak baseline GNN for uploads): it is a prediction, not a fact, and may disagree with the label.
- Findings (F001, ...) are results of deterministic checks; category gnn_suspicion is only a model-based hint, not a
  wiring fault.

How to answer:
0. Most tool results start with a "summary" written by code from the circuit data. Build your answer on the
   summary: copy the lines that answer the question, keeping names, pins, directions and gate order exactly. Each
   summary line is one fact: never move a gate, pin or net from one line to another, and do not add gates, pins or
   nets it does not list. Describe only gates you have a summary for.
   Arrows "A -> B" mean A drives B (the signal goes from A to B). Say "A drives B" or "A feeds B"; never say that
   the driving gate "reads" anything.
1. Tool results already in the conversation are real circuit data: use them first. If you need other exact data,
   call a tool (at most 6 calls). Never guess gates, pins, nets, buses or connections.
2. If a tool returns an error, say plainly that the item was not found, or try the fitting tool once (get_bus for a
   bus name, get_net for one bit such as X[3], list_findings for problems). Never invent a replacement.
3. Answer the question asked in 1-5 short sentences or a short list of plain English. Do not bring up findings or
   predictions that the question is not about.
4. Refer to items only as [G23], [N:<net>], [B:<bus>] or [F001], and only for items that appear in the context or
   tool results. Plain names are fine too.
5. Say "GraphSAINT predicts" (or "the baseline model predicts") for predictions; state checked facts directly.
6. Do not write Verilog unless the user asks for it. You cannot change the circuit: never say anything was fixed.
   A finding's suggested repair comes from the deterministic checks; present it as the recommended fix for the
   engineer to apply. Only findings with category gnn_suspicion are model-based.
7. For greetings or questions that are not about the circuit, answer in one or two sentences and say what you can
   help with (gates, nets, buses, paths, findings, what the circuit does, GraphSAINT predictions).
8. highlights: only gate ids, nets, finding ids and existing edges that your answer is about.
9. To explain a fix, use the finding's suggested edges; do not propose other connections.
"""

# ---------------------------------------------------------------------------
# Automatic lookups: entities named in the question are looked up with the same CircuitTools before the model
# answers, so a small local model does not have to choose tools or copy exact names itself.
# ---------------------------------------------------------------------------

MAX_AUTO_LOOKUPS = 4
_GATE_RE = re.compile(r'\b(?:G|gate\s*#?\s*)(\d+)\b', re.I)
_FINDING_RE = re.compile(r'\bF(\d{1,4})\b', re.I)
_NAME_RE = re.compile(r'\\\S+|[A-Za-z_][\w$/.]*(?:\[\d+\])?')
_PATH_RE = re.compile(r'\b(path|trace|route|between|reach(?:es)?|flows?)\b', re.I)
_ISSUE_RE = re.compile(r'\b(issues?|problems?|errors?|warnings?|wrong|faults?|faulty|missing|suspicious|flagged|'
                       r'findings?|broken|unconnected|floating|dangling|health|healthy)\b', re.I)
_PRED_RE = re.compile(r'\b(graphsaint|predict\w*|gnn|classif\w*)\b', re.I)
_FOLLOW_UP_RE = re.compile(r'\b(this|that|these|those|it|its|they|them|their|same|above|previous)\b', re.I)
_NAME_HINT_RE = re.compile(r'\b(net|nets|bus|buses|signal|wire|bit)\s*$', re.I)
_FOLLOW_KIND = [(re.compile(r'\b(nets?|wires?|signals?)\b', re.I), 'get_net'),
                (re.compile(r'\b(gates?|cells?|instances?)\b', re.I), 'get_gate'),
                (re.compile(r'\b(bus|buses)\b', re.I), 'get_bus'),
                (re.compile(r'\b(findings?|issues?|problems?)\b', re.I), 'explain_finding'),
                (re.compile(r'\b(paths?)\b', re.I), 'trace_path')]


def _follow_up(message, history):
    """Lookups a follow-up question ("what reads this net?") refers to: the latest lookup of the kind it names,
    else the previous turn's lookups."""
    for rx, tool in _FOLLOW_KIND:
        if rx.search(message):
            for turn in reversed(history):
                hit = [c for c in turn if c[0] == tool]
                if hit:
                    return hit[-1:]
    return list(history[-1]) if history else []


def plan_lookups(message, model, history=()):
    """Tool calls for the entities a question names (history: earlier turns' lookups, oldest first).
    Deterministic; the model can still call more tools."""
    calls = []
    gates = list(dict.fromkeys(int(x) for x in _GATE_RE.findall(message)))
    findings = list(dict.fromkeys(f'F{int(x):03d}' for x in _FINDING_RE.findall(message)))
    names = []
    for m in _NAME_RE.finditer(message):
        tok = m.group(0).rstrip('?.,;:!)\'"')
        if re.fullmatch(r'[GgFf]\d+', tok):
            continue
        specific = any(c in tok for c in '[_/\\') or any(c.isdigit() for c in tok)
        if specific or _NAME_HINT_RE.search(message[:m.start()]):
            names.append(tok)
    for tok in dict.fromkeys(names):
        s = tok.lstrip('\\')
        if tok in model['nets'] or s in model['nets'] or '\\' + s in model['nets']:
            calls.append(('get_net', {'name': tok}))
        elif tok in model['buses']:
            calls.append(('get_bus', {'name': tok}))
    if len(gates) >= 2 and _PATH_RE.search(message):
        calls.insert(0, ('trace_path', {'from_id': gates[0], 'to_id': gates[1], 'max_nodes': None}))
    else:
        calls = [('get_gate', {'gate_id': g}) for g in gates[:3]] + calls
    calls += [('explain_finding', {'finding_id': f}) for f in findings[:2]]
    if _ISSUE_RE.search(message) and not findings:
        calls.append(('list_findings', {'category': None, 'severity': None}))
    if not calls and history and _FOLLOW_UP_RE.search(message):
        calls = _follow_up(message, history)
    if _PRED_RE.search(message):
        net_drivers = [d['gate_id'] for n, a in calls if n == 'get_net'
                       for d in model['nets'].get(cc._canon(model, a['name']), {}).get('drivers', []) if 'gate_id' in d]
        focus = gates[:1] or [a['gate_id'] for n, a in calls if n == 'get_gate'][:1] or \
            [a['from_id'] for n, a in calls if n == 'trace_path'][:1] or net_drivers[:1]
        if focus:
            calls.append(('get_neighborhood', {'gate_id': focus[0], 'hops': 1, 'max_nodes': 20}))
    out = []
    for c in calls:
        if c not in out:
            out.append(c)
    return out[:MAX_AUTO_LOOKUPS]


def _subject_gates(tool, out):
    """Gates an automatic lookup was about (highlighted in the UI whatever the model writes)."""
    if 'error' in out:
        return []
    if tool == 'get_gate':
        return [out['id']]
    if tool == 'trace_path':
        return [p['id'] for p in out['path']]
    if tool == 'get_net':
        return [x['gate_id'] for x in out.get('drivers', []) + out.get('readers', []) if 'gate_id' in x]
    return []


_REF_FIXES = [
    (re.compile(r'\[\s*G(?:ate)?\s*[:#]?\s*(\d+)\s*\]', re.I), lambda m: f'[G{m.group(1)}]'),
    (re.compile(r'\[\s*F\s*:?\s*F?(\d{1,4})\s*\]', re.I), lambda m: f'[F{int(m.group(1)):03d}]'),
    (re.compile(r'\[\s*(?:G|F|Block|Blk)\s*:\s*([^\[\]\d][^\[\]]*)\]', re.I), lambda m: m.group(1).strip()),
]
_NB_REF_RE = re.compile(r'\[(N|B):((?:[^\[\]]|\[\d+\])+)\]')


def normalize_refs(text, model):
    """Rewrite near-miss reference tags ([G:23], [F:F001], [N:<bus>]) into the canonical forms the Grounder and the
    UI understand. Nothing is invented: the Grounder still validates every canonical reference afterwards."""
    if not text:
        return text
    text = re.sub(r'\\\\(?=[A-Za-z_])', r'\\', text)       # doubly escaped names: \\adder_1/n4 -> \adder_1/n4
    text = re.sub(r'\[(?:G|F|N:|B:)\s*<[^>\]]*>\]', '', text)   # prompt placeholders copied verbatim, e.g. [G<id>]
    for rx, fn in _REF_FIXES:
        text = rx.sub(fn, text)

    def fix_nb(m):
        kind, name = m.group(1), m.group(2)
        if kind == 'N' and name in model['buses'] and name not in model['nets']:
            return f'[B:{name}]'
        if kind == 'B' and name not in model['buses'] and name in model['nets']:
            return f'[N:{name}]'
        return m.group(0)
    return _NB_REF_RE.sub(fix_nb, text)


class Assistant:
    def __init__(self, llm, service):
        self.llm = llm
        self.service = service
        self.sessions = SessionStore()
        self._reports = {}
        self._reports_lock = threading.Lock()

    # ---- status -------------------------------------------------------------
    def status(self):
        return self.llm.status() if self.llm is not None else {'available': False, 'model': None,
                                                               'reason': 'assistant not configured'}

    def _require(self):
        st = self.status()
        if not st['available']:
            raise LLMError(f'Assistant unavailable: {st["reason"]}', kind='unavailable')

    # ---- report -------------------------------------------------------------
    def generate_report(self, ref, regenerate=False):
        self._require()
        analysis = self.service.analyze(ref)
        key = (ref.key, analysis['sha256'], self.llm.model)
        with self._reports_lock:
            if not regenerate and key in self._reports:
                return dict(self._reports[key], cached=True)
        ctx = llm_context(analysis)
        res = self.llm.create(purpose='report', instructions=REPORT_INSTRUCTIONS,
                              input=[{'role': 'user', 'content': json.dumps(ctx, separators=(',', ':'), default=str)}],
                              schema=REPORT_SCHEMA, schema_name='circuit_report',
                              effort=self.llm.config.effort_report, max_output_tokens=16000)
        model, _ = self.service.load(ref)
        report = self._finalize_report(require_keys(res.parsed, REPORT_SCHEMA, 'report'), analysis, model)
        report['usage'] = res.usage
        report['model'] = self.llm.model
        with self._reports_lock:
            self._reports[key] = report
            while len(self._reports) > 64:
                self._reports.pop(next(iter(self._reports)))
        return dict(report, cached=False)

    def _finalize_report(self, raw, analysis, model):
        findings = analysis['findings']
        by_id = {f['id']: f for f in findings}
        g = Grounder(model, findings, [b['name'] for b in analysis['intent'].get('blocks', [])])
        items, suspicion_items = [], []
        for i, it in enumerate(raw['items']):
            where = f'report.items[{i}]'
            fids = g.finding_ids(it['finding_ids'], where + '.finding_ids')
            if not fids:
                g._drop(f'item "{it["title"][:60]}" (cites no valid finding)', where)
                continue
            cited = [by_id[f] for f in fids]
            sev = min((f['severity'] for f in cited), key=lambda s: cc.SEVERITY_ORDER[s])
            cert_rank = {'fact': 0, 'likely': 1, 'suspicion': 2}
            cert = min((f.get('certainty') or cc.certainty(f) for f in cited), key=lambda c: cert_rank[c])
            snippet = it['verilog_suggestion']
            if snippet and not snippet.replace(SUGGESTION_LABEL, '').strip():
                snippet = None                                   # only the label, no actual suggestion
            if snippet:
                snippet = g.clean_text(snippet, where + '.verilog_suggestion')
                if not snippet.lstrip().startswith(SUGGESTION_LABEL):
                    snippet = SUGGESTION_LABEL + '\n' + snippet
            edges = []
            for f in cited:
                for e in f['suggested_edges']:
                    if e not in edges:
                        edges.append(e)
            item = {
                'title': it['title'], 'severity': sev, 'certainty': cert,
                'what': g.clean_text(normalize_refs(it['what'], model), where + '.what'),
                'where': g.clean_text(normalize_refs(it['where'], model), where + '.where'),
                'why_it_matters': g.clean_text(normalize_refs(it['why_it_matters'], model), where + '.why_it_matters'),
                # the model's wording is always audited (dropped refs are reported), but when the checks computed
                # the repair, the item states that repair exactly instead
                'fix': (lambda llm_fix: suggested_fix_text(edges) if edges else llm_fix)(
                    g.clean_text(normalize_refs(_strip_comment_lines(it['fix']), model), where + '.fix')),
                'verilog_suggestion': snippet,
                'finding_ids': fids,
                'gate_ids': g.gates(it['gate_ids'], where + '.gate_ids')
                or sorted({x for f in cited for x in f['gate_ids']})[:20],
                'suggested_edges': g.suggested_edges(edges, where + '.suggested_edges'),
            }
            (suspicion_items if cert == 'suspicion' else items).append(item)
        items.sort(key=lambda it: cc.SEVERITY_ORDER[it['severity']])   # stable: keeps LLM impact order
        if suspicion_items:
            if len(suspicion_items) > 1:
                merged = dict(suspicion_items[0])
                merged['title'] = 'Model-based suspicions'
                merged['finding_ids'] = [f for it in suspicion_items for f in it['finding_ids']]
                merged['gate_ids'] = sorted({x for it in suspicion_items for x in it['gate_ids']})[:40]
                merged['what'] = ' '.join(it['what'] for it in suspicion_items)
                suspicion_items = [merged]
            items += suspicion_items
        health = _health(findings)
        clean = g.clean_text(normalize_refs(raw['clean_confirmation'], model), 'report.clean_confirmation') or ''
        if health == 'ok' and not clean.strip():
            clean = 'No connection problems found. Checks passed: ' + '; '.join(_checks_passed(findings)) + '.'
        summary = g.clean_text(normalize_refs(raw['summary'], model), 'report.summary')
        texts = [summary, clean] + [it[k] for it in items for k in ('what', 'where', 'why_it_matters', 'fix')]
        return {
            'ref_gates': _ref_gates(model, texts),
            'summary': summary,
            'health': health,
            'llm_health': raw['health'],
            'items': items,
            'clean_confirmation': clean,
            'checks_passed': _checks_passed(findings),
            'dropped_refs': g.dropped,
        }

    # ---- chat ---------------------------------------------------------------
    def chat(self, session_id, ref, message):
        self._require()
        if not isinstance(message, str) or not message.strip():
            raise ValueError('message must be a non-empty string')
        message = message.strip()[:MAX_MESSAGE_CHARS]
        analysis = self.service.analyze(ref)
        model, _ = self.service.load(ref)
        session = self.sessions.get(session_id, (ref.key, analysis['sha256']))
        with session['lock']:
            return self._chat_turn(session, ref, analysis, model, message)

    def _chat_turn(self, session, ref, analysis, model, message):
        tools = CircuitTools(model, analysis)
        with self._reports_lock:
            report = self._reports.get((ref.key, analysis['sha256'], self.llm.model))
        ctx = llm_context(analysis)
        ctx['findings'] = [{'id': f['id'], 'check': f['check'], 'severity': f['severity'],
                            'certainty': f['certainty'], 'evidence': f['evidence'][:160]} for f in ctx['findings']]
        if report:
            ctx['report_summary'] = report['summary']
        ev = analysis['evidence']
        ctx['circuit']['gate_ids'] = f'G0..G{analysis["stats"]["num_gates"] - 1}'
        ctx['buses'] = ev['buses']
        ctx['predictions'] = {'source': analysis['prediction_source'],
                              'counts': ev['predicted_class_distribution']['counts'],
                              'per_block': {b['name']: b['predicted_classes'] for b in ev['blocks']}}
        instructions = CHAT_INSTRUCTIONS + '\nContext:\n' + json.dumps(ctx, separators=(',', ':'), default=str)
        conv = []
        for user, answer in session['turns']:
            conv.append({'role': 'user', 'content': user})
            conv.append({'role': 'assistant', 'content': answer})
        conv.append({'role': 'user', 'content': message})

        trace, calls_used, usage_total = [], 0, {'input_tokens': 0, 'output_tokens': 0, 'cost_usd': 0.0}
        tool_texts, subject_gates, summaries = [], [], []
        # a local model can loop on its own output at low temperature: keep chat answers short and bounded
        max_out = CHAT_MAX_OUTPUT_TOKENS_LOCAL if getattr(self.llm.config, 'base_url', '') else 8000
        lookups = plan_lookups(message, model, session.get('lookup_history', []))
        for i, (name, args) in enumerate(lookups):
            out = tools.call(name, args)
            subject_gates += _subject_gates(name, out)
            if out.get('summary'):
                summaries.append(out['summary'])
            text = _truncate(out)
            tool_texts.append(text)
            call_id = f'auto_{i}'
            conv.append({'type': 'function_call', 'call_id': call_id, 'name': name, 'arguments': json.dumps(args)})
            conv.append({'type': 'function_call_output', 'call_id': call_id, 'output': text})
            trace.append({'tool': name, 'arguments': args, 'ok': 'error' not in out, 'output_chars': len(text),
                          'auto': True})
        if lookups:
            session['lookup_history'] = (session.get('lookup_history', []) + [lookups])[-MAX_TURNS:]
        final = None
        for _ in range(MAX_TOOL_CALLS + 2):
            force_answer = calls_used >= MAX_TOOL_CALLS
            res = self.llm.create(purpose='chat', instructions=instructions, input=conv, schema=CHAT_SCHEMA,
                                  schema_name='chat_reply', tools=TOOLS,
                                  tool_choice='none' if force_answer else None,
                                  effort=self.llm.config.effort_chat, max_output_tokens=max_out)
            for k in ('input_tokens', 'output_tokens'):
                usage_total[k] += res.usage.get(k) or 0
            usage_total['cost_usd'] = round(usage_total['cost_usd'] + (res.usage.get('cost_usd') or 0), 6)
            if not res.function_calls:
                final = require_keys(res.parsed, CHAT_SCHEMA, 'chat reply')
                require_keys(final['highlights'], CHAT_SCHEMA['properties']['highlights'], 'chat reply')
                break
            conv += res.output_items
            for call in res.function_calls:
                if calls_used >= MAX_TOOL_CALLS:
                    out = {'error': f'tool call limit ({MAX_TOOL_CALLS}) reached; answer with what you have'}
                else:
                    calls_used += 1
                    out = tools.call(call['name'], call['arguments'])
                text = _truncate(out)
                tool_texts.append(text)
                trace.append({'tool': call['name'], 'arguments': call['arguments'],
                              'ok': 'error' not in out, 'output_chars': len(text)})
                conv.append({'type': 'function_call_output', 'call_id': call['call_id'], 'output': text})
        if final is None:
            raise LLMError('The assistant did not produce an answer within the tool-call budget', kind='incomplete')

        g = Grounder(model, analysis['findings'], [b['name'] for b in analysis['intent'].get('blocks', [])])
        reply = g.clean_text(normalize_refs(final['reply'], model), 'chat.reply')
        # statements about connections, paths and predictions that the netlist contradicts are removed
        reply = g.check_claims(reply, 'chat.reply', analysis.get('predictions'), cc.CLASS_NAMES)
        if not (reply or '').strip():
            reply = ('I could not phrase a verified answer. The circuit data says:\n' + '\n'.join(summaries)
                     if summaries else 'I could not give a verified answer to that. Please ask about a specific '
                                       'gate, net, bus, path or finding.')
        # plain gate ids that exist become clickable references; unknown ids (e.g. G999) stay plain text
        reply = re.sub(r'(?<![\[\w])G(\d+)\b(?!\])',
                       lambda m: f'[G{m.group(1)}]' if g.gate_ok(int(m.group(1))) else m.group(0), reply)
        hl = final['highlights']
        cited = Grounder.refs_in(reply)
        finding_ids = g.finding_ids(list(dict.fromkeys(hl['finding_ids'] + cited['finding_ids'])), 'chat.highlights')
        # only findings this turn is about: cited in the reply, named in the question or returned by a tool
        relevant = set(cited['finding_ids']) | {f'F{int(x):03d}' for x in _FINDING_RE.findall(message)}
        relevant |= {f for t in tool_texts for f in re.findall(r'"(F\d{3,})"', t)}
        finding_ids = [f for f in finding_ids if f in relevant]
        by_id = {f['id']: f for f in analysis['findings']}
        sugg = []
        for fid in finding_ids:
            for e in by_id[fid]['suggested_edges']:
                if e not in sugg:
                    sugg.append(e)
        highlights = {
            'gate_ids': g.gates(list(dict.fromkeys(hl['gate_ids'] + cited['gate_ids'] + subject_gates)),
                                'chat.highlights.gate_ids'),
            'nets': g.net_list(list(dict.fromkeys(hl['nets'] + cited['nets'])), 'chat.highlights.nets'),
            'finding_ids': finding_ids,
            'edges': g.existing_edges(hl['edges'], 'chat.highlights.edges'),
            'suggested_edges': g.suggested_edges(sugg, 'chat.highlights.suggested_edges'),
        }
        self.sessions.add_turn(session, message, reply)
        return {'session_id': session['id'], 'reply': reply, 'highlights': highlights, 'tool_trace': trace,
                'ref_gates': _ref_gates(model, [reply], nets=highlights['nets']),
                'dropped_refs': g.dropped, 'usage': usage_total}
