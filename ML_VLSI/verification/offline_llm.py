"""
offline_llm.py - Deterministic, rule-based stand-in for the LLM, used ONLY for UI verification
while no OpenAI credits are available. It is NOT a language model: it fills the same strict
schemas from the payload it receives (findings, suggested edges, tool outputs), so the real
pipeline (grounding, tool loop, chips, overlays) is exercised end to end.
Its model name is shown in the UI as "offline-stand-in (not an LLM)".
"""
import json
import re

from llm_client import LLMConfig, LLMResult

WHY = {
    'missing_pin': 'the cell computes with an undefined input, so every bit downstream of it is unreliable',
    'floating_net': 'an undriven net floats, so the gates reading it produce undefined values',
    'carry_out_unread': 'the carry of this stage never reaches the next stage, so higher sum bits are wrong',
    'dangling_output': 'this logic is computed but never used, which usually means a connection went missing',
    'carry_break': 'higher-significance result bits no longer see lower operand bits: additions with a carry are wrong',
    'bit_slice_anomaly': 'one bit slice uses the wrong operand bit, so that result bit is computed from the wrong input',
    'multi_driver': 'two drivers fight on one net, giving undefined logic levels',
    'undriven_po': 'the output port is undefined',
}


class OfflineLLM:
    def __init__(self):
        self.config = LLMConfig(api_key='offline', model='offline-stand-in (not an LLM)')
        self.available = True
        self.reason = None
        self.calls = []

    @property
    def model(self):
        return self.config.model

    def status(self):
        return {'available': True, 'model': self.model, 'reason': None}

    def probe(self):
        return True

    def _result(self, parsed=None, calls=None):
        usage = {'input_tokens': 0, 'cached_tokens': 0, 'output_tokens': 0, 'reasoning_tokens': 0, 'cost_usd': 0.0}
        if calls:
            items = [{'type': 'function_call', 'call_id': c['call_id'], 'name': c['name'],
                      'arguments': json.dumps(c['arguments'])} for c in calls]
            return LLMResult('', None, calls, items, usage, 0)
        return LLMResult(json.dumps(parsed), parsed, [], [], usage, 0)

    def create(self, **kw):
        self.calls.append(kw)
        name = kw['schema_name']
        if name == 'circuit_intent':
            payload = json.loads(kw['input'][0]['content'])
            h = payload['deterministic_hypothesis']
            return self._result({'intended_function': h['intended_function'],
                                 'summary_for_layman': 'This circuit ' + h['intended_function'][:1].lower()
                                 + h['intended_function'][1:] + ' (structural reading of the dependency cones).',
                                 'blocks': h['blocks'], 'dataflow': h['dataflow'],
                                 'expected_connections': h['expected_connections'], 'unchecked_rules': [],
                                 'confidence': h['confidence'], 'reasoning': 'Rule-based stand-in: echoes the cone signatures.'})
        if name == 'circuit_report':
            return self._result(self._report(json.loads(kw['input'][0]['content'])))
        if name == 'chat_reply':
            return self._chat(kw)
        raise ValueError(name)

    def _report(self, ctx):
        items = []
        for f in ctx['findings']:
            if f['severity'] == 'info':
                continue
            edges = f.get('suggested_edges') or []
            fix = 'Inspect the cited gates.'
            snippet = None
            if edges:
                e = edges[0]
                src = f"[G{e['from_gate']}] pin {e['from_pin']}" if 'from_gate' in e else f"[N:{e['from_net']}]"
                dst = f"[G{e['to_gate']}] pin {e['to_pin']}" if 'to_gate' in e else f"output {e['to_po']}"
                fix = f'Connect {src} to {dst} (suggestion, not applied).'
                if 'to_gate' in e:
                    src_txt = f"G{e['from_gate']}.{e['from_pin']}" if 'from_gate' in e else e['from_net']
                    snippet = f"// connect {src_txt} -> G{e['to_gate']}.{e['to_pin']}"
            items.append({'title': f['check'].replace('_', ' ').capitalize(), 'severity': f['severity'],
                          'certainty': f['certainty'], 'what': f['evidence'][:300],
                          'where': ' '.join(f'[G{g}]' for g in f['gate_ids'][:4]),
                          'why_it_matters': WHY.get(f['check'], 'it breaks the intended function'),
                          'fix': fix, 'verilog_suggestion': snippet, 'finding_ids': [f['id']],
                          'gate_ids': f['gate_ids'][:6]})
        if ctx['model_based_suspicions']:
            items.append({'title': 'Model-based suspicions', 'severity': 'info', 'certainty': 'suspicion',
                          'what': f"{len(ctx['model_based_suspicions'])} groups of gates where the GNN predictions look inconsistent.",
                          'where': '', 'why_it_matters': 'hints only; not evidence of a wiring fault', 'fix': 'none needed',
                          'verilog_suggestion': None, 'finding_ids': [s['id'] for s in ctx['model_based_suspicions']],
                          'gate_ids': []})
        it = ctx['intent']
        summary = (f"{it['intended_function']} ({round(it['confidence'] * 100)}% confidence). "
                   + ('No connection problems were found.' if ctx['health'] == 'ok'
                      else f"{ctx['counts']['errors']} error(s) and {ctx['counts']['warnings']} warning(s) found."))
        return {'summary': summary, 'health': ctx['health'], 'items': items,
                'clean_confirmation': '; '.join(ctx['checks_passed'][:6])}

    def _chat(self, kw):
        inputs = kw['input']
        user = next(m['content'] for m in reversed(inputs) if isinstance(m, dict) and m.get('role') == 'user')
        outputs = [i for i in inputs if isinstance(i, dict) and i.get('type') == 'function_call_output']
        m = re.search(r'F\d{3}', user)
        if m and not outputs:
            return self._result(calls=[{'call_id': 'offline-1', 'name': 'explain_finding',
                                        'arguments': {'finding_id': m.group(0)}}])
        if outputs:
            f = json.loads(outputs[-1]['output'])
            if 'error' in f:
                return self._result({'reply': f['error'], 'highlights': {'gate_ids': [], 'nets': [], 'finding_ids': [], 'edges': []}})
            e = (f.get('suggested_edges') or [None])[0]
            fix = ''
            if e and 'from_gate' in e and 'to_gate' in e:
                fix = f" Suggested fix (not applied): connect [G{e['from_gate']}] pin {e['from_pin']} to [G{e['to_gate']}] pin {e['to_pin']}."
            reply = (f"[{f['id']}] is a {f['check'].replace('_', ' ')} ({f['certainty']}): {f['evidence'][:220]}" + fix)
            return self._result({'reply': reply, 'highlights': {'gate_ids': f['gate_ids'][:10], 'nets': [],
                                                                'finding_ids': [f['id']], 'edges': []}})
        return self._result({'reply': 'I am the offline stand-in; ask about a finding, e.g. "how do I fix F001?".',
                             'highlights': {'gate_ids': [], 'nets': [], 'finding_ids': [], 'edges': []}})
