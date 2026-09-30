"""
run_browser_check.py - Headless Playwright verification of the dashboard + assistant.

Starts the real server in-process with the offline stand-in LLM (no OpenAI calls), drives
Chromium through six scenarios, saves screenshots to verification/ and writes results.json.

    .venv/Scripts/python verification/run_browser_check.py
"""
import json
import os
import shutil
import sys
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

from playwright.sync_api import sync_playwright  # noqa: E402

import web_dashboard  # noqa: E402
from circuit_store import DATASET_DIR  # noqa: E402
from offline_llm import OfflineLLM  # noqa: E402

RESULTS = {'scenarios': {}, 'console_errors': []}


def shot(page, name):
    page.screenshot(path=os.path.join(HERE, name), full_page=False)
    return name


def wait_ready(page, circuit=None, report=True, timeout=240000):
    cond = "() => window.Assistant && Assistant.state.analysis && !Assistant.state.analysisBusy"
    if circuit:
        cond += f" && Assistant.state.source && Assistant.state.source.circuit_name === {json.dumps(circuit)}"
    if report:
        cond += " && (Assistant.state.report || Assistant.state.reportError)"
    page.wait_for_function(cond, timeout=timeout)


def select(page, circuit, report=True):
    t0 = time.time()
    page.select_option('#circuit-select', circuit)
    wait_ready(page, circuit, report)
    return round(time.time() - t0, 2)


def to_view(page, view):
    page.evaluate(f"switchVisualView('{view}')")
    if view == 'graph':
        page.wait_for_function("() => network && graphEdgesDS && network.body && Object.keys(network.body.nodes).length > 0",
                               timeout=240000)
        page.wait_for_timeout(1500)


def click_finding(page, fid):
    page.evaluate("Assistant.setTab('issues')")
    page.click(f'[data-finding="{fid}"]')
    page.wait_for_timeout(1700)          # pulse (1.5 s) + zoom animation


def main():
    srv = web_dashboard.make_server('127.0.0.1', 0, llm=OfflineLLM(), probe=False)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{srv.server_address[1]}/'
    tmp = tempfile.mkdtemp()
    upload = os.path.join(tmp, 'my_design.v')
    shutil.copy(os.path.join(DATASET_DIR, 'Train_add_mul_4_bit_Syn_65nm.v'), upload)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1600, 'height': 1000})
        page.on('pageerror', lambda e: RESULTS['console_errors'].append(f'pageerror: {e}'))
        page.on('console', lambda m: m.type == 'error' and RESULTS['console_errors'].append(f'console: {m.text}'))
        page.goto(url)

        # 1. clean circuit: metrics auto-populate, drawer health OK
        page.wait_for_function("() => document.getElementById('metric-acc').textContent !== '--%'", timeout=120000)
        page.click('#assistant-toggle')
        load = select(page, 'Validate_add_mul_8_bit_Syn_65nm.v')
        page.wait_for_function("() => document.getElementById('metric-acc').textContent !== '--%'")
        r = page.evaluate("""() => ({metric: document.getElementById('metric-acc').textContent,
            health: document.querySelector('#tab-overview .health').textContent,
            intent: document.querySelector('#tab-overview .intent-fn').textContent,
            status: document.getElementById('assistant-status-text').textContent,
            report_health: Assistant.state.report && Assistant.state.report.health})""")
        r['load_s'] = load
        r['screenshot'] = shot(page, '1_clean_overview.png')
        RESULTS['scenarios']['1_clean'] = r

        # 2. Demo_cut_carry: ghost edge between the right gates, F001 click zooms, report item explains it
        load = select(page, 'Demo_cut_carry__Validate_add_mul_8_bit_Syn_65nm.v')
        scale_before = page.evaluate('schematicView.scale')
        click_finding(page, 'F001')
        r = page.evaluate("""() => ({scale: schematicView.scale,
            focus_gates: [...Overlays.state.focus.gates], ghost: Overlays.state.focus.ghost,
            inspector: document.getElementById('inspector-badge').textContent,
            item_title: document.querySelector('#tab-issues .item .title') && document.querySelector('#tab-issues .item .title').textContent,
            item_text: document.querySelector('#tab-issues .item') && document.querySelector('#tab-issues .item').innerText.slice(0, 600)})""")
        r.update(load_s=load, scale_before=scale_before, canvas_screenshot=shot(page, '2_cut_carry_canvas.png'))
        to_view(page, 'graph')
        click_finding(page, 'F001')
        page.wait_for_timeout(800)
        r['graph_ghost_edge'] = page.evaluate("() => { const e = graphEdgesDS.get('ov-ghost-0'); return e && {from: e.from, to: e.to, label: e.label, dashes: !!e.dashes, title: e.title}; }")
        r['graph_screenshot'] = shot(page, '2_cut_carry_graph.png')
        RESULTS['scenarios']['2_cut_carry'] = r

        # 3. Demo_miswire_bits: bit-slice warning + swap suggestion visible on the graph
        to_view(page, 'schematic')
        load = select(page, 'Demo_miswire_bits__Test_add_mul_16_bit_Syn_65nm.v')
        click_finding(page, 'F001')
        r = {'load_s': load, 'canvas_screenshot': shot(page, '3_miswire_canvas.png')}
        to_view(page, 'graph')
        click_finding(page, 'F001')
        page.wait_for_timeout(800)
        r.update(page.evaluate("""() => ({
            finding: Assistant.state.analysis.findings.find(f => f.id === 'F001').check,
            ghost_edges: graphEdgesDS.get({filter: e => String(e.id).startsWith('ov-ghost') && !e.hidden}).map(e => ({from: e.from, to: e.to, label: e.label})),
            pi_stubs: graphNodesDS.get({filter: n => String(n.id).startsWith('ov-pi') && !n.hidden}).map(n => n.label)})"""))
        r['graph_screenshot'] = shot(page, '3_miswire_graph.png')
        RESULTS['scenarios']['3_miswire'] = r
        page.evaluate("Assistant.setTab('overview')")
        RESULTS['scenarios']['3_miswire']['overview_screenshot'] = shot(page, '3_miswire_overview.png')

        # 4. upload: GNN-RE shows N/A, analysis still runs
        to_view(page, 'schematic')
        page.click('#tab-upload-btn')
        page.set_input_files('#file-input', upload)
        page.wait_for_function("() => document.getElementById('metric-acc').textContent === 'N/A'", timeout=120000)
        page.wait_for_function("() => Assistant.state.source && Assistant.state.source.upload_id && Assistant.state.analysis && Assistant.state.report", timeout=120000)
        r = page.evaluate("""() => ({metric: document.getElementById('metric-acc').textContent,
            note: document.getElementById('gnnre-note').textContent,
            intent: Assistant.state.analysis.intent.intended_function,
            health: Assistant.state.report.health,
            notes: Assistant.state.analysis.honesty_notes})""")
        r['screenshot'] = shot(page, '4_upload.png')
        RESULTS['scenarios']['4_upload'] = r
        page.click('#tab-bench-btn')

        # 5. chat: "how do I fix F001?" -> reply with chips; clicking a chip highlights the gate
        select(page, 'Demo_cut_carry__Validate_add_mul_8_bit_Syn_65nm.v')
        page.evaluate("Assistant.setTab('chat')")
        page.fill('#chat-input', 'how do I fix F001?')
        page.press('#chat-input', 'Enter')
        page.wait_for_selector('#chat-log .msg-assistant .reply', timeout=60000)
        chips = page.evaluate("() => [...document.querySelectorAll('#chat-log .reply .ref-chip')].map(c => c.textContent)")
        page.click('#chat-log .reply .ref-chip.chip-gate')
        page.wait_for_timeout(1600)
        r = page.evaluate("""() => ({reply: document.querySelector('#chat-log .msg-assistant .reply').innerText,
            trace: document.querySelector('#chat-log .trace summary') && document.querySelector('#chat-log .trace summary').textContent,
            inspector: document.getElementById('inspector-badge').textContent,
            focus_gates: [...Overlays.state.focus.gates]})""")
        r['chips'] = chips
        r['screenshot'] = shot(page, '5_chat.png')
        RESULTS['scenarios']['5_chat'] = r

        # 6. 12.5k-gate circuit: overlays stay responsive
        big = 'Train_add_mul_comp_sub_64_bit_Syn_65nm.v'
        t_load = select(page, big)
        perf = page.evaluate("""() => {
            const t = f => { const s = performance.now(); f(); return +(performance.now() - s).toFixed(1); };
            const gates = Array.from({length: 200}, (_, i) => i * 60);
            return {
              gates: currentCircuitData.nodes.length,
              full_render_ms: t(() => renderCircuitSchematic()),
              overlay_only_ms: t(() => Overlays.drawCanvas()),
              focus_200_gates_canvas_ms: t(() => Overlays.focus({gate_ids: gates}, {zoom: true, inspect: true})),
              zoomed_render_ms: t(() => renderCircuitSchematic()),
            };
        }""")
        page.mouse.move(900, 450)
        t0 = time.time()
        for _ in range(10):
            page.mouse.wheel(0, -200)
        page.wait_for_timeout(100)
        perf['ten_wheel_zooms_s'] = round(time.time() - t0, 2)
        perf['load_and_analyze_s'] = t_load
        perf['canvas_screenshot'] = shot(page, '6_big_canvas.png')
        t0 = time.time()
        to_view(page, 'graph')
        perf['graph_view_ready_s'] = round(time.time() - t0, 1)
        perf.update(page.evaluate("""() => {
            const t = f => { const s = performance.now(); f(); return +(performance.now() - s).toFixed(1); };
            const gates = Array.from({length: 200}, (_, i) => i * 60);
            return {physics_enabled_after_stabilize: network.physics.physicsEnabled,
                    focus_200_gates_graph_ms: t(() => Overlays.focus({gate_ids: gates}, {zoom: false, inspect: false})),
                    reapply_overlays_graph_ms: t(() => Overlays.applyGraph())};
        }"""))
        perf['graph_screenshot'] = shot(page, '6_big_graph.png')
        RESULTS['scenarios']['6_big_circuit'] = perf
        browser.close()
    srv.shutdown()
    with open(os.path.join(HERE, 'results.json'), 'w', encoding='utf-8') as f:
        json.dump(RESULTS, f, indent=1)
    print(json.dumps(RESULTS, indent=1))


if __name__ == '__main__':
    main()
