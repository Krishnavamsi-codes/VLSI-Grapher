"""
live_smoke.py - One real OpenAI run (only if the startup probe succeeds).

Runs the real pipeline on Demo_miswire_bits: LLM intent + report + one chat turn, and
records token usage / cost to verification/live_smoke.json. Never prints the API key.

    .venv/Scripts/python verification/live_smoke.py
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import web_dashboard  # noqa: E402  (baseline GCN + CSV predictions)
from analysis_service import AnalysisService  # noqa: E402
from assistant import Assistant  # noqa: E402
from circuit_store import resolve_circuit  # noqa: E402
from llm_client import LLMClient, LLMError  # noqa: E402

CIRCUIT = 'Demo_miswire_bits__Test_add_mul_16_bit_Syn_65nm.v'
OUT = os.path.join(HERE, 'live_smoke.json')


def main():
    llm = LLMClient()
    t0 = time.time()
    ok = llm.probe()
    result = {'model': llm.model, 'probe_ok': ok, 'probe_seconds': round(time.time() - t0, 1),
              'status': llm.status()}
    if not ok:
        result['skipped'] = 'Probe failed, so no live report was generated.'
        print(json.dumps(result, indent=1))
        json.dump(result, open(OUT, 'w'), indent=1)
        return 1
    service = AnalysisService(llm, web_dashboard._baseline_predict)
    assistant = Assistant(llm, service)
    ref = resolve_circuit(CIRCUIT)
    try:
        t0 = time.time()
        analysis = service.analyze(ref)
        result['intent'] = {k: analysis['intent'].get(k) for k in
                            ('intended_function', 'summary_for_layman', 'confidence', 'blocks', 'dataflow',
                             'template_results', 'dropped_refs', 'dropped_templates', 'usage', 'llm_error')}
        result['intent_seconds'] = round(time.time() - t0, 1)
        t0 = time.time()
        report = assistant.generate_report(ref)
        result['report'] = report
        result['report_seconds'] = round(time.time() - t0, 1)
        t0 = time.time()
        chat = assistant.chat(None, ref, 'How do I fix F001?')
        result['chat'] = {'question': 'How do I fix F001?', **chat}
        result['chat_seconds'] = round(time.time() - t0, 1)
    except LLMError as err:
        result['error'] = err.message
    usages = [u for u in (result.get('intent', {}).get('usage'), result.get('report', {}).get('usage'),
                          result.get('chat', {}).get('usage')) if u]
    result['total_cost_usd'] = round(sum((u.get('cost_usd') or 0) for u in usages), 6)
    json.dump(result, open(OUT, 'w'), indent=1, default=str)
    print(json.dumps(result, indent=1, default=str))
    return 0


if __name__ == '__main__':
    sys.exit(main())
