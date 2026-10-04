"""
grounding.py - Validate every reference the LLM makes against the circuit model.

Citation format (the only one parsed):
    [G<id>]      gate            e.g. [G123]
    [N:<net>]    net             e.g. [N:\\adder_1/n4]  [N:Result_add[3]]
    [F<id>]      finding         e.g. [F001]
    [B:<bus>]    bus             e.g. [B:Result_add]
    [M<n>]       predicted module e.g. [M3]  (GraphSAINT sub-circuit #3, as numbered in the UI)

Unknown references are removed from text (replaced by "[unverified]") and from
structured fields, and reported in `dropped_refs`. Overlays are drawn only for
what survives.
"""

import re

# [N:...] may itself contain brackets (bus bits), so match balanced one level deep.
REF_RE = re.compile(r'\[(?:G(\d+)|F(\d+)|N:((?:[^\[\]]|\[\d+\])+)|B:([^\[\]\s]+))\]')
UNVERIFIED = '[unverified]'

# claim checking (see Grounder.check_claims)
_SENT_SPLIT = re.compile(r'(?<=[.!?])\s+')
_LIST_ITEM = re.compile(r'\s*(?:[-*]|\d+\.)\s')
_GATE_ID = re.compile(r'G(\d+)\b')
_NAME_TOKEN = re.compile(r'\[N:(?:[^\[\]]|\[\d+\])+\]|\\?[A-Za-z_][\w$/.]*(?:\[\d+\])?')
_SUBJ = r"\[N:(?:[^\[\]]|\[\d+\])+\]|\[?G\d+\]?|\\?[A-Za-z_][\w$/.]*(?:\[\d+\])?"
_REL_RE = re.compile(r"(?P<subj>" + _SUBJ + r")(?:(?:'s?)?(?:\s+(?:output|input))?\s+pin\s+\w+)?\s+(?:also\s+|only\s+)?"
                     r"(?P<verb>drives|feeds|reads|is\s+driven\s+by|is\s+fed\s+by|is\s+read\s+by)\b"
                     r"(?P<obj>[^.;:!?\n]*)", re.I)
_OBJ_CUT = re.compile(r',\s*(?:and|which|while|but|so|where)\b|\s+(?:and|but)\s+(?:it|its|this|that|then)\b'
                      r'|\s+(?:and|but)\s+(?:also\s+)?(?:drives|feeds|reads|is)\b'
                      r'|\s+(?:and|but)\s+(?:is\s+)?(?:read|driven|fed)\s+by\b'
                      r'|\s+(?:and|but)\s+(?:gate\s+)?\[?G\d+\]?\s+(?:drives|feeds|reads|is)\b', re.I)
_CHAIN_RE = re.compile(r'\[?G\d+\]?(?:\s*->\s*\[?G\d+\]?)+')
_CLASSES = r'(?P<cls>Adder|Multiplier|Control Logic|Subtractor|Comparator)'
_PRED_RE = re.compile(r'\[?G(?P<g>\d+)\]?(?:\s*\([^)]*\))?\s+(?:is|was)\s+(?:also\s+)?predicted\s+(?:to\s+be\s+|as\s+)?'
                      r'(?:(?:part\s+of|in|a|an)\s+)?(?:both\s+)?(?:the\s+)?' + _CLASSES, re.I)
MOD_RE = re.compile(r'\[M(\d+)\]')

# PPA claims (see Grounder.check_metrics). This repository has no delay, power or area data, so any value in
# these units, and any quantified improvement, cannot be grounded.
_UNITS = {
    'timing': r'(?:ns|ps|fs|ms|us|µs|nanoseconds?|picoseconds?|[kMG]Hz|hertz)',
    'power': r'(?:[munµp]?W|watts?|milliwatts?|microwatts?|nanowatts?|[muµ]A|[pfn]J|joules?)',
    'area': r'(?:[uµm]m(?:2|\^2|²)|square\s+(?:microns?|micrometers?|millimeters?|nanometers?)|sq\.?\s*um)',
}
_PPA_VALUE_RE = {k: re.compile(r'(?<![\w.])\d+(?:[.,]\d+)?\s*' + u + r'(?![\w])') for k, u in _UNITS.items()}
_GAIN_WORDS = re.compile(r'\b(reduc\w*|improv\w*|sav\w*|speed\w*|faster|slower|lower\w*|increas\w*|decreas\w*|cut\w*|'
                         r'gain\w*|shrink\w*|smaller|less|boost\w*)\b', re.I)
_GAIN_NUM = re.compile(r'(?<![\w.])\d+(?:\.\d+)?\s*(?:%|percent\b|x\b|times\b)', re.I)
_DEFINITE = [(re.compile(r'\b(?:will|would)\s+(?:definitely\s+|certainly\s+|always\s+)?'
                         r'(improve|reduce|increase|lower|speed\s+up|save|cut|decrease|shorten|eliminate)\b', re.I),
              r'could \1'),
             (re.compile(r'\b(?:is\s+)?guaranteed\s+to\s+', re.I), 'could '),
             (re.compile(r'\b(?:definitely|certainly)\s+', re.I), '')]
_LEVELS_RE = re.compile(r'(?<![\w.])(\d+)\s*(?:-\s*)?(?:gate\s+|logic\s+)?levels?\b', re.I)
_DEPTH_RE = re.compile(r'\bdepth\s+(?:of\s+|is\s+|=\s*)?(\d+)\b', re.I)
_FANOUT_RE = re.compile(r"(?P<subj>\[N:(?:[^\[\]]|\[\d+\])+\]|\[?G\d+\]?|\\?[A-Za-z_][\w$/.]*(?:\[\d+\])?)(?:'s)?\s+"
                        r"(?:has\s+(?:a\s+)?(?:fan-?out|load)\s+(?:of\s+)?|fan-?out\s+(?:is\s+|of\s+)?|"
                        r"drives\s+|fans\s+out\s+to\s+)(?P<n>\d+)\b", re.I)
_ML_HEDGE = re.compile(r'predict|graphsaint|\bmodel\b|\bml\b|gnn|label|instance.name|likely|suspect|appears|classif',
                       re.I)
_ML_FACT_RE = re.compile(r'\[?G(?P<g>\d+)\]?\s+(?:is|belongs\s+to)\s+(?:a\s+|an\s+|part\s+of\s+|in\s+)?(?:the\s+)?'
                         r'(?P<cls>Adder|Multiplier|Control Logic|Subtractor|Comparator)\b', re.I)
ML_QUALIFIER = ' (GraphSAINT prediction, not a verified fact)'

_PRED_RE2 = re.compile(r'predicts?\s+(?:that\s+)?\[?G(?P<g>\d+)\]?\s+(?:is|as)\s+(?:(?:part\s+of|in|a|an)\s+)?'
                       r'(?:the\s+)?' + _CLASSES, re.I)


class Grounder:
    def __init__(self, model, findings, block_names=(), modules=0):
        self.model = model
        self.n = model['num_gates']
        self.nets = set(model['nets'])
        self.alias = {}
        for canon, e in model['nets'].items():
            for a in e['aliases']:
                self.alias[a] = canon
        self.buses = set(model['buses'])
        self.findings = {f['id']: f for f in findings}
        self.blocks = set(block_names)
        self.modules = modules
        self.gate_pins = [set(model['gate_pins'][g]) | {m['pin'] for m in model['missing_pins'] if m['gate_id'] == g}
                          for g in range(self.n)] if self.n < 200000 else None
        self.dropped = []

    # --- single checks ------------------------------------------------------
    def gate_ok(self, g):
        return isinstance(g, int) and not isinstance(g, bool) and 0 <= g < self.n

    def net_ok(self, name):
        return isinstance(name, str) and (name in self.nets or name in self.alias)

    def canon_net(self, name):
        return name if name in self.nets else self.alias.get(name, name)

    def bus_ok(self, name):
        return isinstance(name, str) and name in self.buses

    def finding_ok(self, fid):
        return isinstance(fid, str) and fid in self.findings

    def module_ok(self, n):
        return isinstance(n, int) and 1 <= n <= self.modules

    def bus_or_net_ok(self, name):
        return self.bus_ok(name) or self.net_ok(name)

    def _drop(self, ref, where):
        self.dropped.append({'ref': str(ref), 'where': where})

    # --- text ---------------------------------------------------------------
    def clean_text(self, text, where):
        if not isinstance(text, str) or not text:
            return text

        def repl(m):
            g, f, n, b = m.groups()
            if g is not None:
                ok = self.gate_ok(int(g))
            elif f is not None:
                ok = self.finding_ok('F' + f)
            elif n is not None:
                ok = self.net_ok(n)
            else:
                ok = self.bus_ok(b)
            if ok:
                return m.group(0)
            self._drop(m.group(0), where)
            return UNVERIFIED

        def mod(m):
            if self.module_ok(int(m.group(1))):
                return m.group(0)
            self._drop(m.group(0), where)
            return UNVERIFIED
        return MOD_RE.sub(mod, REF_RE.sub(repl, text))

    # --- claims -------------------------------------------------------------
    def check_claims(self, text, where, predictions=None, class_names=()):
        """Remove sentences whose connectivity or prediction claims contradict the netlist.

        Checked (conservatively; anything not recognised is left alone):
          "X drives/feeds Y", "X reads Y", "X is driven/fed/read by Y"  (X, Y = gates G<id> or nets)
          "Ga -> Gb -> ..." chains (every hop must be a real driver->reader edge)
          "Gx is predicted (to be) <class>", "predicts (that) Gx is <class>"
        """
        if not isinstance(text, str) or not text:
            return text
        out_lines = []
        for line in text.split('\n'):
            kept = []
            for sent in _SENT_SPLIT.split(line):
                bad = self._false_claim(sent, predictions, class_names)
                if bad:
                    self._drop(f'claim: {bad}', where)
                else:
                    kept.append(sent)
            if kept or not line.strip():
                out_lines.append(' '.join(kept))
            else:
                out_lines.append(None)                       # a line whose every sentence was false
        lines = [l for l in out_lines if l is not None]
        # a lead-in such as "The connections are:" whose list items were all removed is dropped too
        cleaned = []
        for i, l in enumerate(lines):
            nxt = next((x for x in lines[i + 1:] if x.strip()), '')
            if l.rstrip(' *_').endswith(':') and not _LIST_ITEM.match(nxt):
                continue
            cleaned.append(l)
        return re.sub(r'\n{3,}', '\n\n', '\n'.join(cleaned)).strip()

    def _edge(self, u, v):
        if not hasattr(self, '_edges'):
            self._edges = set(map(tuple, self.model['edges']))
        return (u, v) in self._edges

    def _net_of(self, token):
        t = token[3:-1] if token.startswith('[N:') and token.endswith(']') else token
        for cand in (t, t.lstrip('\\'), '\\' + t.lstrip('\\')):
            if self.net_ok(cand):
                return self.canon_net(cand)
        return None

    def _ends(self, net, side):
        return {x['gate_id'] for x in self.model['nets'][net][side] if 'gate_id' in x}

    def _false_claim(self, sent, predictions, class_names):
        for m in _CHAIN_RE.finditer(sent):
            ids = [int(x) for x in _GATE_ID.findall(m.group(0))]
            for u, v in zip(ids, ids[1:]):
                if self.gate_ok(u) and self.gate_ok(v) and not self._edge(u, v):
                    return m.group(0)
        for m in _REL_RE.finditer(sent):
            subj, verb = m.group('subj'), m.group('verb').lower()
            obj = _OBJ_CUT.split(m.group('obj'))[0]
            gates = [int(x) for x in _GATE_ID.findall(obj) if self.gate_ok(int(x))]
            nets = [n for n in (self._net_of(t) for t in _NAME_TOKEN.findall(obj)) if n]
            g_subj = _GATE_ID.fullmatch(subj.strip('[]'))
            if g_subj:
                x = int(g_subj.group(1))
                if not self.gate_ok(x):
                    continue
                if verb in ('drives', 'feeds'):
                    ok = all(self._edge(x, y) for y in gates) and all(x in self._ends(n, 'drivers') for n in nets)
                elif verb == 'reads':
                    ok = all(self._edge(y, x) for y in gates) and all(x in self._ends(n, 'readers') for n in nets)
                elif verb in ('is driven by', 'is fed by'):
                    ok = all(self._edge(y, x) for y in gates)
                else:                                            # is read by
                    ok = all(self._edge(x, y) for y in gates)
            else:
                net = self._net_of(subj)
                if net is None:
                    continue
                if verb in ('is driven by', 'is fed by'):
                    ok = all(y in self._ends(net, 'drivers') for y in gates)
                elif verb in ('is read by', 'drives', 'feeds'):
                    ok = all(y in self._ends(net, 'readers') for y in gates)
                else:
                    continue
            if not ok:
                return m.group(0).strip()
        if predictions and class_names:
            for rx in (_PRED_RE, _PRED_RE2):
                for m in rx.finditer(sent):
                    g = int(m.group('g'))
                    if self.gate_ok(g) and g < len(predictions) and \
                            class_names[predictions[g]].lower() != m.group('cls').lower():
                        return m.group(0)
        return None

    # --- PPA metrics and ML attribution --------------------------------------
    def check_metrics(self, text, where, facts=None, predictions=None, class_names=()):
        """Remove sentences with ungrounded PPA claims and label predictions stated as facts.

          * any timing/power/area value with a unit (ns, MHz, mW, um^2, ...): no such data exists here;
          * quantified improvements ("reduces power by 30%", "2x faster"): nothing has been measured;
          * "will improve/reduce ..." is softened to "could ..." (suggestions are never guaranteed);
          * longest-path level counts, fan-out counts and block gate counts must match `facts`
            ({'max_depth', 'path_levels', 'gate_fanout', 'net_fanout', 'block_gates', 'total_gates'});
          * "G5 is a Multiplier" without a prediction word: kept with a qualifier if only GraphSAINT says so,
            removed if neither the prediction nor the instance-name label says so.
        """
        if not isinstance(text, str) or not text:
            return text
        facts = facts or {}
        out_lines = []
        for line in text.split('\n'):
            kept = []
            for sent in _SENT_SPLIT.split(line):
                for rx, rep in _DEFINITE:
                    sent = rx.sub(rep, sent)
                bad = self._bad_metric(sent, facts)
                if bad:
                    self._drop(f'claim: {bad}', where)
                    continue
                sent = self._ml_attribution(sent, where, predictions, class_names)
                if sent is not None:
                    kept.append(sent)
            if kept or not line.strip():
                out_lines.append(' '.join(kept))
        return re.sub(r'\n{3,}', '\n\n', '\n'.join(out_lines)).strip()

    def _bad_metric(self, sent, facts):
        allowed = facts.get('ppa_values') or ()
        for kind, rx in _PPA_VALUE_RE.items():
            for m in rx.finditer(sent):
                num = float(re.match(r'[\d.,]+', m.group(0)).group(0).replace(',', '.').rstrip('.'))
                # a liberty-derived value (area/leakage from a loaded .lib) may be quoted; nothing else
                if kind != 'timing' and any(abs(num - v) <= 0.005 * max(abs(v), 1e-9) for v in allowed):
                    continue
                return f'unsupported {kind} value "{m.group(0).strip()}" (no matching {kind} data exists)'
        for m in _GAIN_NUM.finditer(sent):
            before, after = sent[max(0, m.start() - 60):m.start()], sent[m.end():m.end() + 30]
            by_gain = _GAIN_WORDS.search(before) and re.search(r'\b(by|up\s+to|about|around|roughly|nearly|over|'
                                                               r'approximately)\s*~?\s*$', before, re.I)
            gain_after = re.match(r'\s*(?:\w+\s+)?' + _GAIN_WORDS.pattern, after, re.I)
            if by_gain or gain_after:
                return f'unmeasured improvement "{m.group(0).strip()}"'
        if facts.get('max_depth') and re.search(r'\b(longest|critical|maximum|max|deepest|worst)\b', sent, re.I) \
                and not re.search(r'\bthrough\b|\bshorter\b|\bnext\b|\bsecond\b|\bthird\b', sent, re.I):
            allowed = {facts['max_depth']} | set(facts.get('path_levels', ()))
            for m in list(_LEVELS_RE.finditer(sent)) + list(_DEPTH_RE.finditer(sent)):
                if int(m.group(1)) not in allowed:
                    return f'wrong depth "{m.group(0).strip()}" (the longest path has {facts["max_depth"]} levels)'
        for m in _FANOUT_RE.finditer(sent):
            if not re.search(r'fan-?out|load|fans', m.group(0), re.I) and \
                    not re.match(r'\s*(?:pins?|loads?|gates?|readers?|inputs?)\b', sent[m.end():m.end() + 24], re.I):
                continue                                  # "G5 drives 2-bit ...": not a fan-out count
            n, subj = int(m.group('n')), m.group('subj')
            g = _GATE_ID.fullmatch(subj.strip('[]'))
            if g and self.gate_ok(int(g.group(1))):
                ok = n in facts.get('gate_fanout', {}).get(int(g.group(1)), {n})
            else:
                net = self._net_of(subj)
                if net is None or net not in facts.get('net_fanout', {}):
                    continue
                ok = n == facts['net_fanout'][net]
            if not ok:
                return f'wrong fan-out "{m.group(0).strip()}"'
        for blk, cnt in (facts.get('block_gates') or {}).items():
            for m in re.finditer(r'(?<![\w/])' + re.escape(blk) + r'(?:\s+block)?\s+(?:has|contains|holds|with|uses|'
                                 r'is\s+made\s+of)\s+(?:about\s+|around\s+|roughly\s+)?(\d+)\s+gates', sent, re.I):
                if int(m.group(1)) != cnt:
                    return f'wrong gate count "{m.group(0).strip()}" ({blk} has {cnt} gates)'
        for cell, cnt in (facts.get('cell_counts') or {}).items():
            # "NOR2_X0P5M_A9TH: 67 instances", "NOR2_X0P5M_A9TH (67)", "67 x NOR2_X0P5M_A9TH", "NOR2_X0P5M_A9TH is used 67 times"
            esc = r'(?<![\w])' + re.escape(cell) + r'(?![\w])'
            for rx in (esc + r'\W{0,3}\s*(?:is\s+used\s+|appears\s+|with\s+)?\(?(\d+)\)?\s*(?:instances?|times|cells?|uses?)?\b',
                       r'\b(\d+)\s*(?:x|instances?\s+of|copies\s+of)\s+' + esc):
                for m in re.finditer(rx, sent, re.I):
                    tail = sent[m.end():m.end() + 2]
                    if tail.startswith('%') or tail.startswith('.') and tail[1:2].isdigit():
                        continue                          # a share or a decimal, not a count
                    if int(m.group(1)) != cnt:
                        return f'wrong cell count "{m.group(0).strip()}" ({cell} is used {cnt} times)'
        if facts.get('total_gates'):
            for m in re.finditer(r'\b(?:circuit|design|netlist)\s+(?:has|contains|is\s+made\s+of|consists\s+of)\s+'
                                 r'(?:about\s+|around\s+)?(\d+)\s+gates', sent, re.I):
                if int(m.group(1)) != facts['total_gates']:
                    return f'wrong gate count "{m.group(0).strip()}" (the circuit has {facts["total_gates"]} gates)'
        return None

    def _ml_attribution(self, sent, where, predictions, class_names):
        if not predictions or not class_names or _ML_HEDGE.search(sent):
            return sent
        for m in _ML_FACT_RE.finditer(sent):
            g = int(m.group('g'))
            if not self.gate_ok(g) or g >= len(predictions):
                continue
            cls = m.group('cls').lower()
            label = self.model['nodes'][g]['class_name'].lower()
            pred = class_names[predictions[g]].lower()
            if cls == label:
                continue                                   # what the instance names say; not an ML claim
            if cls == pred:
                return sent[:m.end()] + ML_QUALIFIER + sent[m.end():]
            self._drop(f'claim: {m.group(0)} (neither the prediction nor the instance-name label says so)', where)
            return None
        return sent

    @staticmethod
    def refs_in(text):
        out = {'gate_ids': [], 'nets': [], 'finding_ids': [], 'buses': [],
               'modules': [int(x) for x in MOD_RE.findall(text or '')]}
        for m in REF_RE.finditer(text or ''):
            g, f, n, b = m.groups()
            if g is not None:
                out['gate_ids'].append(int(g))
            elif f is not None:
                out['finding_ids'].append('F' + f)
            elif n is not None:
                out['nets'].append(n)
            else:
                out['buses'].append(b)
        return out

    # --- structured fields --------------------------------------------------
    def gates(self, ids, where):
        out = []
        for g in ids or []:
            if self.gate_ok(g):
                if g not in out:
                    out.append(g)
            else:
                self._drop(f'G{g}', where)
        return out

    def finding_ids(self, ids, where):
        out = []
        for f in ids or []:
            if self.finding_ok(f):
                if f not in out:
                    out.append(f)
            else:
                self._drop(f, where)
        return out

    def net_list(self, names, where):
        out = []
        for n in names or []:
            if self.net_ok(n):
                c = self.canon_net(n)
                if c not in out:
                    out.append(c)
            else:
                self._drop(f'N:{n}', where)
        return out

    def bus_list(self, names, where, allow_nets=False):
        out = []
        for b in names or []:
            if self.bus_ok(b) or (allow_nets and self.net_ok(b)):
                if b not in out:
                    out.append(b)
            else:
                self._drop(f'B:{b}', where)
        return out

    def existing_edges(self, edges, where):
        """Edges the model wants to highlight must exist in the netlist graph."""
        valid = set(map(tuple, self.model['edges']))
        out = []
        for e in edges or []:
            u, v = e.get('from_gate'), e.get('to_gate')
            if self.gate_ok(u) and self.gate_ok(v) and ((u, v) in valid or (v, u) in valid):
                if {'from_gate': u, 'to_gate': v} not in out:
                    out.append({'from_gate': u, 'to_gate': v})
            else:
                self._drop(f'edge G{u}->G{v}', where)
        return out

    def suggested_edges(self, edges, where):
        """Suggested edges must have valid endpoints and, for gates, a real pin of that cell."""
        out = []
        for e in edges or []:
            ok = True
            if e.get('from_gate') is not None:
                ok &= self.gate_ok(e['from_gate'])
            elif e.get('from_net') is not None:
                ok &= self.net_ok(e['from_net'])
            else:
                ok = False
            if e.get('to_gate') is not None:
                ok &= self.gate_ok(e['to_gate'])
                if ok and self.gate_pins is not None and e.get('to_pin') is not None:
                    ok &= e['to_pin'] in self.gate_pins[e['to_gate']]
            elif e.get('to_po') is not None:
                ok &= e['to_po'] in set(self.model['primary_outputs'])
            else:
                ok = False
            if ok:
                out.append(e)
            else:
                self._drop(f'suggested edge {e}', where)
        return out
