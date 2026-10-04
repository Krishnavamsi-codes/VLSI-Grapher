"""
qwen_copilot_eval.py - Real-Qwen round through the running application (HTTP API at 127.0.0.1:8501).

Asks the Design Copilot questions a user would ask, checks every answer against the netlist (deterministic
expectations, no PPA numbers, no 5xx), and measures model load / first analysis / warm latency, tokens/sec,
context usage, VRAM and CPU. Writes verification/qwen_copilot_eval.json.

    .venv/Scripts/python web_dashboard.py            (in another terminal; .env points at Ollama)
    .venv/Scripts/python verification/qwen_copilot_eval.py
"""
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
BASE = os.environ.get('APP_URL', 'http://127.0.0.1:8501')
OLLAMA = 'http://localhost:11434'
CONTEXT = 16384
PPA_NUMBER = re.compile(r'\d\s*(ns|ps|MHz|GHz|mW|uW|µW|nW|um2|µm²|um\^2|mm2)\b|\d\s*%\s*(faster|less|lower|reduction)'
                        r'|\b\d+(\.\d+)?x\s+faster', re.I)
OUT = os.path.join(HERE, 'qwen_copilot_eval.json')


def http(method, path, body=None, timeout=600):
    url = (BASE if path.startswith('/') else '') + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={'Content-Type': 'application/json'})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read()), time.time() - t0
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b'{}'), time.time() - t0


def ps(cmd):
    try:
        return subprocess.run(['powershell', '-NoProfile', '-Command', cmd], capture_output=True, text=True,
                              timeout=30).stdout.strip()
    except Exception as exc:   # measurement only
        return f'error: {exc}'


class CpuSampler(threading.Thread):
    """Total CPU % sampled once per second while a request runs."""

    def __init__(self):
        super().__init__(daemon=True)
        self.samples, self.stop = [], False

    def run(self):
        while not self.stop:
            v = ps("(Get-Counter '\\Processor(_Total)\\% Processor Time' -SampleInterval 1 -MaxSamples 1)"
                   ".CounterSamples.CookedValue")
            try:
                self.samples.append(round(float(v), 1))
            except ValueError:
                pass


def gpu():
    out = ps('nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv,noheader')
    loaded = http('GET', OLLAMA + '/api/ps', timeout=10)[1]
    models = [{'name': m['name'], 'size_vram_mb': round(m.get('size_vram', 0) / 2**20),
               'size_mb': round(m.get('size', 0) / 2**20), 'context_length': m.get('context_length')}
              for m in loaded.get('models', [])]
    return {'nvidia_smi': out, 'ollama_loaded': models}


RESULTS = {'questions': [], 'failures': [], 'metrics': {}}


def check(name, cond, detail=''):
    if not cond:
        RESULTS['failures'].append(f'{name}: {detail}')
    return bool(cond)


def ask(src, q, session=None, focus=None, expect=None, label=None):
    body = dict(src, message=q, session_id=session)
    if focus:
        body['focus'] = focus
    cpu = CpuSampler()
    cpu.start()
    st, r, dt = http('POST', '/api/assistant/chat', body)
    cpu.stop = True
    rec = {'question': q, 'focus': focus, 'status': st, 'seconds': round(dt, 1)}
    name = label or q
    if not check(name, st == 200, f'HTTP {st} {r}'):
        rec['error'] = r
        RESULTS['questions'].append(rec)
        return rec, session
    reply = r['reply']
    rec.update(reply=reply, tools=[(t['tool'], t['arguments']) for t in r['tool_trace']],
               evidence=[f"{c['basis']}: {c['title']}" for c in r.get('evidence', [])],
               dropped=[d['ref'] for d in r['dropped_refs']], usage=r['usage'], subject=r.get('subject'),
               cpu_percent_samples=cpu.samples)
    rec['context_fraction'] = round((r['usage'].get('input_tokens') or 0) / max(1, CONTEXT), 3)
    rec['checks'] = {}
    rec['checks']['non_empty'] = check(name, reply.strip(), 'empty reply')
    rec['checks']['no_ppa_numbers'] = check(name, not PPA_NUMBER.search(reply), f'PPA number in reply: {reply}')
    for key, fn in (expect or {}).items():
        ok = False
        try:
            ok = bool(fn(r))
        except Exception as exc:     # an expectation that crashes is a failed expectation
            ok = False
            key += f' ({exc})'
        rec['checks'][key] = check(name, ok, f'{key}; reply={reply[:300]!r}; tools={rec["tools"]}')
    RESULTS['questions'].append(rec)
    print(f"[{dt:5.1f}s] {q}\n    tools={rec['tools']}\n    reply={reply[:400]!r}\n    checks={rec['checks']}\n",
          flush=True)
    return rec, r['session_id']


def tools_of(r):
    return [t['tool'] for t in r['tool_trace']]


def main():
    # ---- model load: wait for the startup probe, then time a cold model load in Ollama --------------------
    t0 = time.time()
    while True:
        st = http('GET', '/api/assistant/status')[1]
        if st['available'] or 'checking' not in (st.get('reason') or ''):
            break
        time.sleep(2)
    RESULTS['status'] = st
    RESULTS['metrics']['probe_wait_s'] = round(time.time() - t0, 1)
    if not check('assistant available', st['available'], str(st)):
        json.dump(RESULTS, open(OUT, 'w'), indent=1)
        return 1
    model = st['model']
    # cold load: unload, then time a 1-token generation (load time reported by Ollama)
    http('POST', OLLAMA + '/api/generate', {'model': model, 'keep_alive': 0}, timeout=60)
    time.sleep(2)
    _, gen, wall = http('POST', OLLAMA + '/api/generate', {'model': model, 'prompt': 'Say OK.', 'stream': False,
                                                            'options': {'num_predict': 4}}, timeout=300)
    RESULTS['metrics']['model_load_s'] = round(gen.get('load_duration', 0) / 1e9, 2)
    RESULTS['metrics']['cold_first_token_wall_s'] = round(wall, 2)
    _, gen, _ = http('POST', OLLAMA + '/api/generate', {
        'model': model, 'stream': False, 'options': {'num_predict': 200, 'temperature': 0.1},
        'prompt': 'Explain in about 150 words what a ripple-carry adder is and why its delay grows with width.'},
        timeout=300)
    RESULTS['metrics']['decode_tokens_per_s'] = round(gen['eval_count'] / (gen['eval_duration'] / 1e9), 1)
    RESULTS['metrics']['prompt_tokens_per_s'] = round(gen['prompt_eval_count'] / max(gen['prompt_eval_duration'] / 1e9, 1e-6), 1)
    RESULTS['metrics']['gpu_after_load'] = gpu()

    # ---- first circuit analysis (cold, not yet cached in this server) --------------------------------------
    cold = {'circuit_name': 'Test_add_mul_16_bit_Syn_65nm.v'}
    _, a, t_an = http('POST', '/api/analyze', cold)
    _, ins, t_ins = http('POST', '/api/insights', cold)
    RESULTS['metrics']['first_analysis_s (incl. LLM intent)'] = round(t_an, 1)
    RESULTS['metrics']['first_insights_s'] = round(t_ins, 2)
    _, _, t_an2 = http('POST', '/api/analyze', cold)
    RESULTS['metrics']['cached_analysis_s'] = round(t_an2, 3)
    big = {'circuit_name': 'Train_add_mul_comp_sub_64_bit_Syn_65nm.v'}
    _, _, t_big = http('POST', '/api/insights', big, timeout=900)
    RESULTS['metrics']['insights_12520_gates_s (incl. analysis)'] = round(t_big, 1)

    # ---- session A: clean 8-bit adder/multiplier -------------------------------------------------------------
    A = {'circuit_name': 'Validate_add_mul_8_bit_Syn_65nm.v'}
    http('POST', '/api/analyze', A)
    _, insA, _ = http('POST', '/api/insights', A)
    lp = insA['timing']['paths'][0]
    depth = insA['timing']['max_depth']
    has = lambda *words: (lambda r: all(w.lower() in r['reply'].lower() for w in words))

    ask(A, 'What does this circuit do?', expect={'mentions adder+multiplier': has('add', 'multipl')})
    ask(A, 'What are the control signals?', expect={'names operation': has('operation'),
                                                     'overview tool': lambda r: 'circuit_overview' in tools_of(r)})
    ask(A, 'Explain the main blocks', expect={'names multiplier_1': has('multiplier')})
    _, sid = ask(A, 'What is G23?', expect={'get_gate 23': lambda r: r['tool_trace'][0]['arguments'] == {'gate_id': 23}})
    _, sid = ask(A, 'What drives it?', sid, expect={'G24 drives G23': has('G24'),
                                                     'subject kept': lambda r: r['subject'] == {'kind': 'gate', 'id': 23}})
    _, sid = ask(A, 'Is that on a critical path?', sid, expect={
        'timing tool on G23': lambda r: ('timing_analysis', {'gate_id': 23}) in [(t['tool'], t['arguments']) for t in r['tool_trace']],
        'says not on longest path': lambda r: re.search(r'\bnot\b', r['reply'], re.I)})
    _, sid = ask(A, 'How could I optimize it?', sid, expect={
        'optimization tool on G23': lambda r: r['tool_trace'][0]['arguments'].get('gate_id') == 23})
    ask(A, 'Show the longest paths', expect={
        'timing tool': lambda r: 'timing_analysis' in tools_of(r),
        'evidence card with longest path': lambda r: any('Longest path' in c['title'] for c in r['evidence']),
        'path gates highlighted': lambda r: set(lp['gates']) <= set(r['highlights']['gate_ids']) or
        any(c['gate_ids'] == lp['gates'] for c in r['evidence'])})
    ask(A, 'Which gates are timing bottlenecks?', expect={'timing tool': lambda r: 'timing_analysis' in tools_of(r)})
    ask(A, 'Which signals have high fan-out?', expect={'names operation': has('operation')})
    ask(A, 'What regions may consume more power?', expect={'power tool': lambda r: 'power_analysis' in tools_of(r)})
    ask(A, 'Which blocks are largest?', expect={'names multiplier_1': has('multiplier'),
                                                 'area tool': lambda r: 'area_analysis' in tools_of(r)})
    ask(A, 'How could I improve performance?', expect={
        'optimization cards': lambda r: sum(c['kind'] == 'optimization' for c in r['evidence']) >= 2,
        'cards carry all fields': lambda r: all(all(c.get(k) for k in ('target', 'reason', 'evidence', 'impact',
                                                                        'confidence', 'type'))
                                                for c in r['evidence'] if c['kind'] == 'optimization')})
    ask(A, 'What should I investigate for PPA?', expect={'optimization tool': lambda r: 'optimization_suggestions' in tools_of(r)})
    ask(A, 'Which regions does GraphSAINT find suspicious?', expect={
        'region tool': lambda r: 'explain_region' in tools_of(r),
        'ML evidence labelled': lambda r: any(c['basis'] == 'ml_prediction' for c in r['evidence'])})
    ask(A, 'What is G9999?', expect={'says not found': lambda r: re.search(r'not (found|exist|valid)|no gate|unknown|invalid|only', r['reply'], re.I),
                                     'no G9999 chip': lambda r: '[G9999]' not in r['reply']})
    ask(A, 'What is the critical path delay in nanoseconds?', label='hallucination: timing', expect={
        'admits no delay data': lambda r: re.search(r'not available|no (timing|delay)|structural|cannot|isn.t available|only', r['reply'], re.I)})
    ask(A, 'How many milliwatts does the multiplier consume?', label='hallucination: power', expect={
        'admits no power data': lambda r: re.search(r'not available|no (power|switching|activity)|structural|cannot|only', r['reply'], re.I)})
    ask(A, 'What is the silicon area of this circuit in square microns?', label='hallucination: area', expect={
        'admits no area data': lambda r: re.search(r'not available|no (cell )?area|gate count|structural|cannot|only', r['reply'], re.I)})
    ask(A, 'Does G23 drive G100 directly?', label='hallucination: connection', expect={
        'no false "G23 drives G100" survives': lambda r: not re.search(r'\[?G23\]? (directly )?drives \[?G100\]?', r['reply'])})

    # ---- session B: injected cut-carry fault --------------------------------------------------------------
    B = {'circuit_name': 'Demo_cut_carry__Validate_add_mul_8_bit_Syn_65nm.v'}
    http('POST', '/api/analyze', B)
    _, insB, _ = http('POST', '/api/insights', B)
    ask(B, 'Are there connectivity issues?', expect={'mentions F001': has('F001')})
    ask(B, 'How do I fix this?', focus={'kind': 'finding', 'id': 'F001'}, expect={
        'repair edge G24->G23 CI highlighted': lambda r: any(e.get('from_gate') == 24 and e.get('to_gate') == 23
                                                             for e in r['highlights']['suggested_edges']),
        'reply names G24 and G23': has('G24', 'G23')})
    mod = next(m for m in range(1, insB['modules'] + 1)) if insB['modules'] else None
    # module that contains G23 (its CI pin is the cut one)
    _, regB, _ = http('POST', '/api/assistant/chat', dict(B, message='Why is this region suspicious?',
                                                           focus={'kind': 'gate', 'id': 23}))
    m23 = next((c.get('module') for c in regB.get('evidence', []) if c.get('module')), mod)
    ask(B, 'Why is this region suspicious?', focus={'kind': 'module', 'id': m23}, expect={
        'says prediction': lambda r: re.search(r'predict|graphsaint|ml', r['reply'], re.I),
        'ML and fact cards separated': lambda r: {c['basis'] for c in r['evidence']} >= {'ml_prediction', 'deterministic'}})
    ask(B, 'Explain this gate', focus={'kind': 'gate', 'id': 23}, expect={'get_gate 23': lambda r: r['tool_trace'][0]['arguments'] == {'gate_id': 23}})

    # ---- session C: uploaded .v ------------------------------------------------------------------------------
    from circuit_store import DATASET_DIR
    text = open(os.path.join(DATASET_DIR, 'Train_add_mul_4_bit_Syn_65nm.v'), encoding='utf-8').read()
    st, up, _ = http('POST', '/api/upload_circuit', {'filename': 'my_design.v', 'content': text})
    check('upload', st == 200, str(up)[:200])
    C = {'upload_id': up['upload_id']}
    http('POST', '/api/analyze', C)
    _, insC, _ = http('POST', '/api/insights', C)
    check('upload has no GraphSAINT capability', insC['capabilities']['graphsaint']['supported'] is False)
    ask(C, 'What does this circuit do?', expect={'mentions add/mul': has('add')})
    ask(C, 'Where could I reduce area?', expect={'optimization tool': lambda r: 'optimization_suggestions' in tools_of(r)})
    ask(C, 'What is the critical path?', expect={'timing tool': lambda r: 'timing_analysis' in tools_of(r)})

    # ---- metrics summary --------------------------------------------------------------------------------------
    qs = [q for q in RESULTS['questions'] if q.get('status') == 200]
    lat = sorted(q['seconds'] for q in qs)
    RESULTS['metrics']['warm_chat_latency_s'] = {'median': lat[len(lat) // 2], 'p90': lat[int(len(lat) * 0.9)],
                                                 'min': lat[0], 'max': lat[-1], 'n': len(lat)}
    ins_tok = [q['usage']['input_tokens'] for q in qs]
    RESULTS['metrics']['chat_input_tokens_per_turn (summed over LLM calls)'] = {
        'median': sorted(ins_tok)[len(ins_tok) // 2], 'max': max(ins_tok)}
    RESULTS['metrics']['context_window'] = CONTEXT
    cpu = [s for q in qs for s in q.get('cpu_percent_samples', [])]
    RESULTS['metrics']['cpu_total_percent_during_chat'] = {'mean': round(sum(cpu) / max(len(cpu), 1), 1),
                                                           'max': max(cpu or [0])}
    RESULTS['metrics']['gpu_end'] = gpu()
    n_checks = sum(len(q.get('checks', {})) for q in RESULTS['questions'])
    n_ok = sum(v for q in RESULTS['questions'] for v in q.get('checks', {}).values())
    RESULTS['summary'] = {'questions': len(RESULTS['questions']), 'checks': n_checks, 'checks_passed': n_ok,
                          'failures': len(RESULTS['failures'])}
    json.dump(RESULTS, open(OUT, 'w', encoding='utf-8'), indent=1, default=str)
    print(json.dumps({'summary': RESULTS['summary'], 'metrics': RESULTS['metrics'], 'failures': RESULTS['failures']},
                     indent=1, default=str))
    return 0


if __name__ == '__main__':
    sys.exit(main())
