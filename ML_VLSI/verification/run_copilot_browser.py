"""
run_copilot_browser.py - Playwright check of the Design Copilot in the REAL website (real Qwen via Ollama).

Targets the running server (APP_URL, default http://127.0.0.1:8501). Verifies: assistant loads, Qwen available,
Insights tab, capability-gated starters, click a gate in the schematic -> ask -> reply with chips, follow-up,
chip click -> highlight, GraphSAINT module click -> "why suspicious" with ML vs fact evidence, issue -> "How do I
fix this?" -> ghost repair edge, graph view, upload. Records console errors and 5xx responses; screenshots go to
verification/copilot_*.png and results to verification/copilot_browser.json.

    .venv/Scripts/python verification/run_copilot_browser.py
"""
import json
import os
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from playwright.sync_api import sync_playwright  # noqa: E402

URL = os.environ.get('APP_URL', 'http://127.0.0.1:8501') + '/'
R = {'scenarios': {}, 'console_errors': [], 'http_5xx': [], 'failures': []}
CHAT_TIMEOUT = 300000


def shot(page, name):
    page.screenshot(path=os.path.join(HERE, name))
    return name


def ok(name, cond, detail=''):
    if not cond:
        R['failures'].append(f'{name}: {detail}')
    return bool(cond)


def wait_analysis(page, circuit=None, upload=False):
    cond = "() => window.Assistant && Assistant.state.analysis && !Assistant.state.analysisBusy && Assistant.state.insights"
    if circuit:
        cond += f" && Assistant.state.source.circuit_name === {json.dumps(circuit)}"
    if upload:
        cond += " && Assistant.state.source.upload_id"
    page.wait_for_function(cond, timeout=600000)


def last_reply(page, n_before):
    page.wait_for_function(f"() => document.querySelectorAll('#chat-log .msg-assistant .reply, #chat-log .msg-assistant .err').length > {n_before}",
                           timeout=CHAT_TIMEOUT)
    return page.evaluate("""() => { const m = [...document.querySelectorAll('#chat-log .msg-assistant')].pop();
        return {text: m.innerText, chips: [...m.querySelectorAll('.reply .ref-chip')].map(c => c.textContent),
                evidence: [...m.querySelectorAll('.ev-card .basis')].map(b => b.textContent),
                trace: m.querySelector('.trace') ? [...m.querySelectorAll('.trace div')].map(d => d.textContent) : [],
                error: m.querySelector('.err') ? m.querySelector('.err').textContent : null}; }""")


def n_replies(page):
    return page.evaluate("() => document.querySelectorAll('#chat-log .msg-assistant .reply, #chat-log .msg-assistant .err').length")


def ask_typed(page, text):
    n = n_replies(page)
    page.evaluate("Assistant.setTab('chat')")
    page.fill('#chat-input', text)
    page.press('#chat-input', 'Enter')
    return last_reply(page, n)


def click_gate_on_canvas(page, g):
    pos = page.evaluate(f"""() => {{ const p = schematicLayout.positions[{g}], v = schematicView;
        const r = document.getElementById('schematic-overlay').getBoundingClientRect();
        return {{x: r.left + v.tx + (p.x + schematicLayout.gateWidth / 2) * v.scale,
                 y: r.top + v.ty + (p.y + schematicLayout.gateHeight / 2) * v.scale}}; }}""")
    page.mouse.click(pos['x'], pos['y'])
    page.wait_for_timeout(400)


def main():
    tmp = tempfile.mkdtemp()
    from circuit_store import DATASET_DIR
    upload = os.path.join(tmp, 'my_design.v')
    shutil.copy(os.path.join(DATASET_DIR, 'Train_add_mul_4_bit_Syn_65nm.v'), upload)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1700, 'height': 1000})
        page.on('pageerror', lambda e: R['console_errors'].append(f'pageerror: {e}'))
        page.on('console', lambda m: m.type == 'error' and R['console_errors'].append(f'console: {m.text}'))
        page.on('response', lambda resp: resp.status >= 500 and R['http_5xx'].append(f'{resp.status} {resp.url}'))
        t0 = time.time()
        page.goto(URL)
        page.wait_for_function("() => document.getElementById('metric-acc').textContent !== '--%'", timeout=120000)

        # 1. assistant loads, Qwen available, insights + capability-gated starters
        page.click('#assistant-toggle')
        page.wait_for_function("() => Assistant.state.status.available", timeout=300000)
        page.select_option('#circuit-select', 'Validate_add_mul_8_bit_Syn_65nm.v')
        wait_analysis(page, 'Validate_add_mul_8_bit_Syn_65nm.v')
        page.evaluate("Assistant.setTab('insights')")
        s1 = page.evaluate("""() => ({status: document.getElementById('assistant-status-text').textContent,
            banner: document.querySelector('#tab-insights .data-banner').innerText,
            opt_cards: document.querySelectorAll('#tab-insights .opt').length,
            longest: document.querySelector('#tab-insights .ins-path') && document.querySelector('#tab-insights .ins-path').innerText.slice(0, 120),
            starter_groups: [...document.querySelectorAll('#chat-starters .grp')].map(g => g.firstChild.textContent),
            modules_listed: document.querySelectorAll('#subcircuits-list > div').length})""")
        s1['page_ready_s'] = round(time.time() - t0, 1)
        s1['screenshot'] = shot(page, 'copilot_1_insights.png')
        ok('qwen status', 'qwen' in s1['status'].lower(), s1['status'])
        ok('insights opt cards', s1['opt_cards'] >= 3, s1)
        ok('graphsaint starters on benchmark', 'GRAPHSAINT' in s1['starter_groups'], s1['starter_groups'])
        ok('GraphSAINT modules listed', s1['modules_listed'] > 0)
        R['scenarios']['1_load_insights'] = s1

        # highlight the longest path from the Insights tab
        page.click('#tab-insights [data-hlpath]')
        page.wait_for_timeout(800)
        R['scenarios']['1_load_insights']['highlighted_path_gates'] = page.evaluate('[...Overlays.state.focus.gates].length')

        # 2. click a gate on the canvas -> inspector ask buttons -> "Explain this gate"
        page.click('button[onclick="renderCircuitSchematic(true)"]')
        page.wait_for_timeout(300)
        click_gate_on_canvas(page, 23)
        s2 = page.evaluate("""() => ({inspector: document.getElementById('inspector-badge').textContent,
            ask_buttons: [...document.querySelectorAll('#inspector-ask [data-ask]')].map(b => b.innerText.trim()),
            pill: document.getElementById('chat-context').innerText})""")
        gsel = page.evaluate("Assistant.state.selection && Assistant.state.selection.kind === 'gate' ? Assistant.state.selection.id : null")
        s2['selected_gate'] = gsel
        ok('canvas click selects a gate', gsel is not None and f'#{gsel}' in s2['inspector'], s2)
        n = n_replies(page)
        page.click('#inspector-ask [data-ask="Explain this gate"]')
        s2['reply'] = last_reply(page, n)
        ok('explain gate reply', not s2['reply']['error'] and s2['reply']['chips'], s2['reply'])
        s2['screenshot'] = shot(page, 'copilot_2_gate_ask.png')
        R['scenarios']['2_gate_click_ask'] = s2

        # 3. follow-ups use the same object
        s3 = {'drives': ask_typed(page, 'What drives it?'), 'critical': ask_typed(page, 'Is that on a critical path?'),
              'optimize': ask_typed(page, 'How could I optimize it?')}
        ok('follow-up drives', any(f'get_gate({{"gate_id":{gsel}}})' in t.replace(' ', '') for t in s3['drives']['trace']), s3['drives']['trace'])
        ok('follow-up critical path', any(f'timing_analysis({{"gate_id":{gsel}}})' in t.replace(' ', '') for t in s3['critical']['trace']),
           s3['critical']['trace'])
        ok('follow-up optimize', any(f'"gate_id":{gsel}' in t.replace(' ', '') and 'optimization' in t for t in s3['optimize']['trace']),
           s3['optimize']['trace'])
        # chip click in the reply highlights that gate
        chip = page.query_selector('#chat-log .msg-assistant:last-child .reply .chip-gate') or \
            page.query_selector('#chat-log .reply .chip-gate')
        if chip:
            val = int(chip.get_attribute('data-val'))
            chip.click()
            page.wait_for_timeout(900)
            s3['chip_click_focus_has_gate'] = page.evaluate(f'Overlays.state.focus.gates.has({val})')
            ok('chip click highlights', s3['chip_click_focus_has_gate'])
        s3['screenshot'] = shot(page, 'copilot_3_followups.png')
        R['scenarios']['3_followups'] = s3

        # 4. PPA questions with evidence cards
        s4 = {'timing': ask_typed(page, 'Show the longest paths'),
              'perf': ask_typed(page, 'How could I improve performance?'),
              'nano': ask_typed(page, 'What is the critical path delay in nanoseconds?')}
        ok('timing evidence', 'deterministic' in s4['timing']['evidence'], s4['timing']['evidence'])
        ok('optimization evidence', any(b in ('structural heuristic', 'deterministic') for b in s4['perf']['evidence']),
           s4['perf']['evidence'])
        s4['screenshot'] = shot(page, 'copilot_4_ppa.png')
        R['scenarios']['4_ppa'] = s4

        # 5. GraphSAINT module click -> "Why is this suspicious?"
        page.click('#subcircuits-list > div:nth-child(1)')
        page.wait_for_timeout(600)
        n = n_replies(page)
        page.click('#inspector-ask [data-ask="Why is this region suspicious?"]')
        s5 = {'reply': last_reply(page, n), 'pill': page.evaluate("document.getElementById('chat-context').innerText")}
        ok('module ask has ML evidence', 'ML prediction' in s5['reply']['evidence'], s5['reply'])
        ok('module ask has fact evidence', 'deterministic' in s5['reply']['evidence'], s5['reply'])
        s5['screenshot'] = shot(page, 'copilot_5_module.png')
        R['scenarios']['5_graphsaint_module'] = s5

        # 6. demo fault: issue -> "How do I fix this?" -> ghost repair edge
        page.select_option('#circuit-select', 'Demo_cut_carry__Validate_add_mul_8_bit_Syn_65nm.v')
        wait_analysis(page, 'Demo_cut_carry__Validate_add_mul_8_bit_Syn_65nm.v')
        page.evaluate("Assistant.setTab('issues')")
        n = n_replies(page)
        page.click('[data-finding="F001"] [data-ask="How do I fix this?"]')
        s6 = {'reply': last_reply(page, n)}
        page.wait_for_timeout(500)
        s6['ghost'] = page.evaluate('Overlays.state.focus ? Overlays.state.focus.ghost : []')
        ok('fix reply', not s6['reply']['error'], s6['reply'])
        ok('ghost repair edge G24->G23', any(e.get('from_gate') == 24 and e.get('to_gate') == 23 for e in s6['ghost']),
           s6['ghost'])
        s6['screenshot'] = shot(page, 'copilot_6_fix.png')
        R['scenarios']['6_issue_fix'] = s6

        # 7. graph view still works; optimization highlight
        page.evaluate("switchVisualView('graph')")
        page.wait_for_function("() => network && graphEdgesDS && Object.keys(network.body.nodes).length > 0", timeout=240000)
        page.wait_for_timeout(1500)
        page.evaluate("Assistant.setTab('insights')")
        page.click('#tab-insights [data-hl]')
        page.wait_for_timeout(1200)
        s7 = page.evaluate("() => ({nodes: graphNodesDS.length, focus: [...Overlays.state.focus.gates].length})")
        ok('graph view', s7['nodes'] > 200 and s7['focus'] > 0, s7)
        s7['screenshot'] = shot(page, 'copilot_7_graph.png')
        R['scenarios']['7_graph'] = s7
        page.evaluate("switchVisualView('schematic')")

        # 8. upload: GraphSAINT capability hidden, chat works
        page.click('#tab-upload-btn')
        page.set_input_files('#file-input', upload)
        wait_analysis(page, upload=True)
        s8 = page.evaluate("""() => ({metric: document.getElementById('metric-acc').textContent,
            starter_groups: [...document.querySelectorAll('#chat-starters .grp')].map(g => g.firstChild.textContent)})""")
        s8['reply'] = ask_typed(page, 'What does this circuit do?')
        ok('upload N/A metric', s8['metric'] == 'N/A', s8['metric'])
        ok('upload hides GraphSAINT starters', 'GRAPHSAINT' not in s8['starter_groups'], s8['starter_groups'])
        ok('upload chat', not s8['reply']['error'] and s8['reply']['text'].strip(), s8['reply'])
        s8['screenshot'] = shot(page, 'copilot_8_upload.png')
        R['scenarios']['8_upload'] = s8
        browser.close()
    ok('no console errors', not R['console_errors'], R['console_errors'])
    ok('no 5xx', not R['http_5xx'], R['http_5xx'])
    with open(os.path.join(HERE, 'copilot_browser.json'), 'w', encoding='utf-8') as f:
        json.dump(R, f, indent=1)
    print(json.dumps({'failures': R['failures'], 'console_errors': R['console_errors'], 'http_5xx': R['http_5xx']},
                     indent=1))
    return 1 if R['failures'] else 0


if __name__ == '__main__':
    sys.exit(main())
