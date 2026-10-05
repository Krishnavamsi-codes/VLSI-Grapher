/*
 * assistant.js - Circuit Assistant drawer: Overview (intent + health + report summary),
 * Issues (report items, findings, model-based suspicions) and Chat.
 * Uses page globals: apiFetch, postJson, showError, currentSource, activeVisualView, switchVisualView.
 */
(function () {
  'use strict';

  const S = {
    source: null, analysis: null, report: null, reportError: null, sessionId: null,
    status: { available: false, reason: 'checking...' }, tab: 'overview', token: 0,
    filters: { severity: 'all', category: 'all' }, suspicionsOpen: false, chatBusy: false,
    refGates: { nets: {}, buses: {}, modules: {} },
    insights: null, insightsError: null, selection: null,
  };
  // Starter prompts by Design Copilot category; `cap` = capability key from /api/insights, `needs` = a selection kind
  const STARTER_GROUPS = [
    { name: 'UNDERSTAND', cap: 'understand', items: [
      { q: 'What does this circuit do?' }, { q: 'Explain the main blocks' }, { q: 'What are the control signals?' },
      { q: 'Explain this gate', needs: 'gate' }] },
    { name: 'DEBUG', cap: 'debug', items: [
      { q: 'Are there connectivity issues?' }, { q: 'Find suspicious connections' },
      { q: 'Explain this finding', needs: 'finding' }, { q: 'How do I fix this?', needs: 'finding' }] },
    { name: 'TIMING', cap: 'timing', items: [
      { q: 'Show the longest paths' }, { q: 'What could hurt timing?' }, { q: 'Which gates are timing bottlenecks?' },
      { q: 'Is this gate on a critical path?', needs: 'gate' }] },
    { name: 'POWER', cap: 'power', items: [
      { q: 'What regions may consume more power?' }, { q: 'Where should I investigate switching activity?' }] },
    { name: 'AREA', cap: 'area', items: [
      { q: 'Which blocks are largest?' }, { q: 'Where is logic most concentrated?' }] },
    { name: 'OPTIMIZE', cap: 'optimize', items: [
      { q: 'How could I improve performance?' }, { q: 'Where could I reduce area?' },
      { q: 'What should I investigate for PPA?' }] },
    { name: 'BOM', cap: 'bom', items: [
      { q: 'Show the cell BOM' }, { q: 'Give power, performance and area recommendations based on the cell BOM' },
      { q: 'Which cells have weak drive strength?' }] },
    { name: 'GRAPHSAINT', cap: 'graphsaint', items: [
      { q: 'Which regions does GraphSAINT find suspicious?' }, { q: 'Why is this region suspicious?', needs: 'module' },
      { q: 'What does GraphSAINT predict for this gate?', needs: 'gate' }] },
  ];
  const CAT_LABEL = { electrical: 'Electrical', reachability: 'Reachability', structural: 'Structural',
                      intent: 'Intent', gnn_suspicion: 'Model-based' };
  const BASIS = { deterministic: ['deterministic', 'Deterministic: computed from the netlist'],
                  'structural heuristic': ['heuristic', 'Structural heuristic: an engineering inference from netlist structure'],
                  ml_prediction: ['ml', 'ML prediction (GraphSAINT): not a circuit fact'] };

  const $ = id => document.getElementById(id);
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const REF_RE = /\[(?:G(\d+)|F(\d+)|N:((?:[^\[\]]|\[\d+\])+)|B:([^\[\]\s]+)|M(\d+))\]/g;

  // ----------------------------------------------------------------- rendering helpers
  function chipify(text) {
    let out = '', last = 0;
    const src = String(text || '');
    src.replace(REF_RE, (m, g, f, n, b, mod, idx) => {
      out += esc(src.slice(last, idx));
      last = idx + m.length;
      if (g !== undefined) out += `<button class="ref-chip chip-gate" data-kind="gate" data-val="${esc(g)}">G${esc(g)}</button>`;
      else if (f !== undefined) out += `<button class="ref-chip chip-finding" data-kind="finding" data-val="F${esc(f)}">F${esc(f)}</button>`;
      else if (n !== undefined) out += `<button class="ref-chip chip-net" data-kind="net" data-val="${esc(n)}">${esc(n)}</button>`;
      else if (b !== undefined) out += `<button class="ref-chip chip-bus" data-kind="bus" data-val="${esc(b)}">${esc(b)}</button>`;
      else out += `<button class="ref-chip chip-module" data-kind="module" data-val="${esc(mod)}">Module #${esc(mod)}</button>`;
      return m;
    });
    out += esc(src.slice(last));
    return out.replace(/\[unverified\]/g, '<span class="unverified" title="Reference removed: not found in this circuit">[unverified]</span>');
  }

  const sevBadge = s => `<span class="sev sev-${esc(s)}">${esc(s)}</span>`;
  const certChip = c => `<span class="cert cert-${esc(c)}" title="${{ fact: 'Deterministic fact', likely: 'Structural/intent inference', suspicion: 'Model-based suspicion' }[c] || ''}">${esc(c)}</span>`;

  function droppedNote(list) {
    if (!list || !list.length) return '';
    const n = list.length;
    return `<div class="dropped" title="${esc(list.map(d => d.ref).join(', '))}"><i class="fa-solid fa-shield-halved"></i> ${n} unverifiable reference${n > 1 ? 's' : ''} removed</div>`;
  }

  // ----------------------------------------------------------------- drawer shell
  function buildDrawer() {
    const d = document.createElement('aside');
    d.id = 'assistant-drawer';
    d.innerHTML = `
      <div class="drawer-head">
        <div class="flex items-center gap-2"><i class="fa-solid fa-robot text-indigo-300"></i>
          <span class="font-semibold text-sm text-white">Circuit Assistant</span>
          <span id="assistant-status-text" class="status-text"></span></div>
        <button class="icon-btn" onclick="Assistant.toggle(false)" title="Close"><i class="fa-solid fa-xmark"></i></button>
      </div>
      <div class="drawer-tabs">
        <button data-tab="overview" class="tab active">Overview</button>
        <button data-tab="issues" class="tab">Issues <span id="issues-count" class="count"></span></button>
        <button data-tab="bom" class="tab">BOM</button>
        <button data-tab="insights" class="tab">Insights</button>
        <button data-tab="chat" class="tab">Chat</button>
      </div>
      <div class="drawer-body">
        <section id="tab-overview"></section>
        <section id="tab-issues" class="hidden"></section>
        <section id="tab-bom" class="hidden"></section>
        <section id="tab-insights" class="hidden"></section>
        <section id="tab-chat" class="hidden">
          <div id="chat-log" class="chat-log"></div>
          <div id="chat-starters" class="starters"></div>
          <div id="chat-context" class="ctx-pill hidden"></div>
          <form id="chat-form" class="chat-form">
            <input id="chat-input" maxlength="2000" autocomplete="off" placeholder="Ask about this circuit...">
            <button id="chat-send" type="submit"><i class="fa-solid fa-paper-plane"></i></button>
          </form>
        </section>
      </div>`;
    document.body.appendChild(d);
    d.querySelectorAll('.tab').forEach(b => b.addEventListener('click', () => setTab(b.dataset.tab)));
    d.addEventListener('click', onChipClick);
    $('chat-form').addEventListener('submit', ev => { ev.preventDefault(); sendChat($('chat-input').value); });
    $('chat-starters').addEventListener('click', ev => {
      const b = ev.target.closest('.starter');
      if (!b) return;
      const needs = b.dataset.needs;
      if (needs && (!S.selection || S.selection.kind !== needs)) {
        showError(`Select a ${needs} first (click it in the schematic, the graph, the Issues tab or a chip).`);
        return;
      }
      sendChat(b.dataset.q);
    });
    $('chat-context').addEventListener('click', ev => { if (ev.target.closest('button')) setSelection(null); });
    renderAll();
  }

  // ----------------------------------------------------------------- selection (what "this"/"it" refers to)
  function selectionLabel(sel) {
    if (!sel) return '';
    return { gate: `G${sel.id}`, finding: sel.id, net: sel.id, bus: sel.id, module: `Module #${sel.id}` }[sel.kind] || '';
  }

  function setSelection(sel) {
    S.selection = sel;
    const el = $('chat-context');
    if (!el) return;
    el.classList.toggle('hidden', !sel);
    el.innerHTML = sel ? `<i class="fa-solid fa-crosshairs"></i> Context: <b>${esc(selectionLabel(sel))}</b>
      <span class="muted">("this" / "it")</span><button title="Clear context"><i class="fa-solid fa-xmark"></i></button>` : '';
    renderStarters();
  }

  function ask(text, focus) {
    if (!S.status.available) { showError('Assistant unavailable: ' + (S.status.reason || '')); return; }
    toggle(true);
    setTab('chat');
    if (focus) setSelection(focus);
    sendChat(text);
  }

  function askButtons(items) {
    return items.map(([label, q, kind, id]) => `<button class="mini ask" data-ask="${esc(q)}" data-kind="${esc(kind)}"
      data-id="${esc(id)}"><i class="fa-solid fa-comment-dots"></i> ${esc(label)}</button>`).join('');
  }

  function bindAsk(root) {
    root.querySelectorAll('[data-ask]').forEach(b => b.addEventListener('click', ev => {
      ev.stopPropagation();
      const kind = b.dataset.kind;
      const id = ['gate', 'module'].includes(kind) ? Number(b.dataset.id) : b.dataset.id;
      ask(b.dataset.ask, kind ? { kind, id } : null);
    }));
  }

  // hooks called by the page (gate inspector, sub-circuit list)
  function inspectorAsk(html) {
    const insp = $('node-inspector');
    if (!insp) return;
    let row = $('inspector-ask');
    if (!row) { row = document.createElement('div'); row.id = 'inspector-ask'; row.className = 'ask-row'; insp.appendChild(row); }
    row.innerHTML = html;
    bindAsk(row);
  }

  function onGateInspected(g) {
    setSelection({ kind: 'gate', id: g });
    inspectorAsk(askButtons([['Explain this gate', 'Explain this gate', 'gate', g],
      ['What drives it?', 'What drives this gate and what does it feed?', 'gate', g],
      ['Critical path?', 'Is this gate on a critical path?', 'gate', g],
      ['Optimize?', 'How could I optimize this gate?', 'gate', g]]));
  }

  function onModuleInspected(n, gateIds) {
    setSelection({ kind: 'module', id: n });
    if (window.Overlays && gateIds) Overlays.focus({ gate_ids: gateIds.slice(0, 300) }, { zoom: true, inspect: false });
    inspectorAsk(askButtons([['Why is this suspicious?', 'Why is this region suspicious?', 'module', n],
      ['Explain this module', 'What does GraphSAINT predict for this module and what does the netlist show?', 'module', n]]));
  }

  function toggle(open) {
    const want = open === undefined ? !document.body.classList.contains('drawer-open') : open;
    document.body.classList.toggle('drawer-open', want);
    setTimeout(() => {
      window.dispatchEvent(new Event('resize'));
      if (typeof network !== 'undefined' && network) network.redraw();
    }, 260);
  }

  function openBom() {
    toggle(true);
    setTab('bom');
  }

  function setTab(tab) {
    S.tab = tab;
    document.querySelectorAll('#assistant-drawer .tab').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
    ['overview', 'issues', 'bom', 'insights', 'chat'].forEach(t => $('tab-' + t).classList.toggle('hidden', t !== tab));
  }

  // ----------------------------------------------------------------- status
  async function refreshStatus() {
    try {
      S.status = await apiFetch('/api/assistant/status');
    } catch (e) {
      S.status = { available: false, reason: e.message };
    }
    const dot = $('assistant-dot');
    if (dot) {
      dot.className = 'status-dot ' + (S.status.available ? 'on' : 'off');
      dot.title = S.status.available ? `Assistant available (${S.status.model})` : `Assistant unavailable: ${S.status.reason}`;
    }
    const t = $('assistant-status-text');
    if (t) t.textContent = S.status.available ? S.status.model : 'unavailable';
    if (!S.status.available && /checking/.test(S.status.reason || '')) setTimeout(refreshStatus, 3000);
    renderOverview();
    renderChatAvailability();
  }

  // ----------------------------------------------------------------- data flow
  function onCircuitLoaded(source) {
    S.source = source;
    S.analysis = null; S.report = null; S.reportError = null; S.sessionId = null;
    S.insights = null; S.insightsError = null;
    S.refGates = { nets: {}, buses: {}, modules: {} };
    S.token += 1;
    setSelection(null);
    $('chat-log').innerHTML = '';
    if (window.Overlays) Overlays.clear();
    renderAll();
    runAnalysis(false);
  }

  async function runAnalysis(regenerate) {
    if (!S.source) return;
    const token = S.token;
    S.analysisBusy = true;
    renderOverview(); renderIssues();
    try {
      const a = await postJson('/api/analyze', Object.assign({ regenerate: !!regenerate }, S.source));
      if (token !== S.token) return;
      S.analysis = a;
      if (window.Overlays) Overlays.setAnalysis(a);
    } catch (e) {
      if (token === S.token) { S.analysisError = e.message; showError('Analysis failed: ' + e.message); }
    } finally {
      if (token === S.token) { S.analysisBusy = false; renderAll(); }
    }
    if (token === S.token && S.analysis) loadInsights();
    // Analysis and insights are deterministic and load immediately. The
    // optional LLM report is user-triggered so loading a circuit never queues
    // a long local-model request in the background.
  }

  async function loadInsights() {
    const token = S.token;
    try {
      const ins = await postJson('/api/insights', S.source);
      if (token !== S.token) return;
      S.insights = ins;
    } catch (e) {
      if (token === S.token) S.insightsError = e.message;
    } finally {
      if (token === S.token) { renderInsights(); renderStarters(); }
    }
  }

  async function loadReport(regenerate) {
    const token = S.token;
    S.reportBusy = true; S.reportError = null;
    renderOverview(); renderIssues();
    try {
      const r = await postJson('/api/assistant/report', Object.assign({ regenerate: !!regenerate }, S.source));
      if (token !== S.token) return;
      S.report = r;
      mergeRefGates(r.ref_gates);
    } catch (e) {
      if (token === S.token) S.reportError = e.message;
    } finally {
      if (token === S.token) { S.reportBusy = false; renderAll(); }
    }
  }

  function regenerate() {
    S.report = null; S.reportError = null;
    runAnalysis(true);
  }

  function mergeRefGates(rg) {
    if (!rg) return;
    Object.assign(S.refGates.nets, rg.nets || {});
    Object.assign(S.refGates.buses, rg.buses || {});
    Object.assign(S.refGates.modules, rg.modules || {});
  }

  // ----------------------------------------------------------------- insights (deterministic; no LLM)
  const gchips = ids => (ids || []).map(g => `[G${g}]`).join(' -> ');
  const gref = text => String(text || '').replace(/(?<![\w\[])G(\d+)\b/g, '[G$1]');   // plain G12 -> chip
  function laymanFinding(f) {
    const net = (f.nets || [])[0] || 'this signal';
    const messages = {
      floating_net: `The wire "${net}" is being used, but it is not connected to anything that supplies a 0 or 1. Think of it as an unplugged wire: this part of the circuit cannot produce a reliable answer. Connect it to the intended source.`,
      multi_driver: `Two parts of the circuit are trying to control the same wire "${net}". That is like two people steering one car at once. Keep only the intended driver or add proper selection logic.`,
      no_path_to_po: 'This logic is doing work, but its result never reaches an output. It is wasted circuitry and may mean a connection was missed.',
      dangling_output: `A gate creates "${net}", but nothing uses it. Check whether that output should feed another gate or be removed.`,
      missing_pin: 'A required gate connection is empty. The gate cannot perform its intended logic until that pin is wired correctly.',
      undriven_po: `The output "${net}" has no source, so the circuit cannot reliably produce a value there.`
    };
    return messages[f.check] || 'The tool found a connection pattern that needs an engineer to inspect it.';
  }

  // small inline SVG bar chart: rows = [{label, value, hl}], vertical bars; values shown on hover and above bars
  function barChart(title, rows, opts) {
    opts = opts || {};
    if (!rows.length) return '';
    const W = 400, H = 120, pad = 18, bw = (W - 10) / rows.length;
    const max = Math.max(...rows.map(r => r.value), 1);
    const bars = rows.map((r, i) => {
      const h = Math.max(1, (H - pad - 14) * r.value / max), x = 5 + i * bw, y = H - pad - h;
      const showLbl = rows.length <= 24 || i % Math.ceil(rows.length / 24) === 0;
      return `<g><title>${esc(r.label)}: ${r.value} ${esc(opts.unit || '')}</title>
        <rect x="${x + 1}" y="${y}" width="${Math.max(1, bw - 2)}" height="${h}" rx="2" fill="${r.hl ? '#f472b6' : 'url(#cg)'}"/>
        ${rows.length <= 16 ? `<text x="${x + bw / 2}" y="${y - 2}" text-anchor="middle" class="cv">${r.value}</text>` : ''}
        ${showLbl ? `<text x="${x + bw / 2}" y="${H - 5}" text-anchor="middle" class="cl">${esc(String(r.label).slice(0, 9))}</text>` : ''}</g>`;
    }).join('');
    return `<div class="chart"><div class="chart-title">${esc(title)}</div>
      <svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img" aria-label="${esc(title)}">
        <defs><linearGradient id="cg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#22d3ee"/><stop offset="1" stop-color="#6366f1"/></linearGradient></defs>
        ${bars}</svg>${opts.note ? `<div class="muted small">${esc(opts.note)}</div>` : ''}</div>`;
  }

  function chartsHtml(I) {
    const t = I.timing, a = I.area, p = I.power;
    const depth = Object.entries(t.depth_histogram || {}).map(([lvl, n]) => ({ label: lvl, value: n, hl: Number(lvl) === t.max_depth }));
    const fo = (t.fanout_histogram || []).map(r => ({ label: r.label, value: r.nets }));
    const cells = Object.entries(a.cell_families).slice(0, 10).map(([k, v]) => ({ label: k, value: v }));
    const cones = (p.cones || []).slice(0, 8).map(c => ({ label: c.bus, value: c.cone_gates }));
    return `<div class="card"><div class="flex justify-between"><span class="label">Charts</span>${basisChip('deterministic')}</div>
      ${barChart('Gates per logic level (pink = deepest level)', depth, { unit: 'gates', note: 'x: gate levels from the inputs (unit delay, not ns)' })}
      ${barChart('Nets by fan-out', fo, { unit: 'nets', note: 'x: number of loads on the net' })}
      ${barChart('Cell types', cells, { unit: 'cells' })}
      ${barChart('Logic cone size per output/result bus', cones, { unit: 'gates' })}</div>`;
  }

  function bomHtml(I) {
    const b = I.bom;
    if (!b) return '';
    const lib = b.library_loaded;
    const q = new URLSearchParams(S.source).toString();
    const rows = b.rows.slice(0, 6).map((r, i) => `
      <tr class="bom-row" data-bom="${i}"><td class="mono">${esc(r.cell)}</td><td>${r.count}</td>
        <td>${r.drive_strength == null ? '?' : 'X' + r.drive_strength}</td>
        <td>${lib ? esc(r.area_total == null ? '-' : r.area_total) : esc(r.description)}</td></tr>
      <tr class="bom-ds hidden" data-ds="${i}"><td colspan="4">
        <div><b>Function</b> ${esc(r.function || 'not derivable from the name')} <span class="muted">(naming convention)</span></div>
        <div><b>Pins</b> in: ${esc(r.inputs.join(', ') || '?')} · out: ${esc(r.outputs.join(', ') || '?')} <span class="muted">(${r.in_cell_library ? 'cell_library.json' : 'unknown'})</span></div>
        <div><b>Blocks</b> ${esc(Object.entries(r.blocks).map(([k, v]) => k + ' ' + v).join(', '))}</div>
        <div><b>Area / leakage</b> ${r.library_data ? `${esc(r.area_each)} each · leakage ${esc(r.leakage_each)} <span class="muted">(liberty)</span>` : '<span class="muted">not available (no liberty data)</span>'}</div>
        <div class="ask-row"><button class="mini" data-bomhl="${i}"><i class="fa-solid fa-location-crosshairs"></i> Highlight instances</button>
          ${askButtons([['Ask about this cell', `Show the datasheet for ${r.cell} and how it is used in this circuit`, '', '']])}</div>
      </td></tr>`).join('');
    return `<div class="card"><div class="flex justify-between"><span class="label">Bill of materials</span>${basisChip('deterministic')}</div>
      <div class="bom-summary"><div><b>${b.totals.instances}</b><span>instances</span></div><div><b>${b.totals.cell_types}</b><span>cell types</span></div><div><b>${b.totals.families}</b><span>families</span></div></div>
      <div class="ins-line small">${b.totals.instances} cells · ${b.totals.cell_types} cell types · ${b.totals.families} families
        ${b.totals.area != null ? ` · total cell area <b>${b.totals.area}</b> (library units)` : ''}
        ${b.totals.leakage_power != null ? ` · leakage <b>${b.totals.leakage_power}</b> (${esc(b.units.leakage_power)})` : ''}</div>
      <details><summary>Cell breakdown — top ${Math.min(b.rows.length, 6)} of ${b.rows.length} types</summary>
        <table class="bom"><thead><tr><th>Cell</th><th>Qty</th><th>Drive</th><th>${lib ? 'Area total' : 'Type'}</th></tr></thead><tbody>${rows}</tbody></table>
        ${b.rows.length > 6 ? `<div class="muted small">The complete list is in the CSV export.</div>` : ''}
      </details>
      <details><summary>Data notes</summary><div class="muted small">${esc(b.note)}</div>${b.cells_without_datasheet.length ? `<div class="unavail small">No datasheet entry for: ${esc(b.cells_without_datasheet.join(', '))}</div>` : ''}</details>
      <div class="ask-row"><a class="mini" href="/api/bom.csv?${esc(q)}" download><i class="fa-solid fa-file-csv"></i> Download BOM (CSV)</a>
        ${askButtons([['BOM PPA recommendations', 'Give power, performance and area recommendations based on the cell BOM', '', '']])}</div></div>`;
  }

  function basisChip(type) {
    const b = BASIS[type] || ['ai', type];
    return `<span class="basis basis-${b[0]}" title="${esc(b[1])}">${esc(type === 'ml_prediction' ? 'ML prediction' : type)}</span>`;
  }

  function optHtml(o) {
    return `<div class="opt opt-${esc(o.category)}" data-opt="${esc(o.id)}">
      <div class="item-head"><b class="text-white">${esc(o.id)}</b><span class="muted">${esc(o.category)}</span>${basisChip(o.type)}
        <span class="muted small">confidence: ${esc(o.confidence)}</span></div>
      <div class="ins-line"><span class="k">Target</span>${chipify(gref(o.target))}</div>
      <div class="ins-line"><span class="k">Reason</span>${esc(o.reason)}</div>
      <div class="ins-line"><span class="k">Evidence</span>${chipify(gref(o.evidence))}</div>
      <div class="ins-line"><span class="k">Potential impact</span>${esc(o.impact)}</div>
      <div class="opt-actions">${o.gate_ids.length ? `<button class="mini" data-hl="${esc(o.id)}"><i class="fa-solid fa-location-crosshairs"></i> Highlight</button>` : ''}
        ${askButtons([['Ask about this', `Explain optimization candidate ${o.id}: ${o.target}. Why is it suggested and what is the evidence?`, '', '']])}</div>
    </div>`;
  }

  function renderInsights() {
    const el = $('tab-insights');
    if (!el) return;
    if (!S.source) { el.innerHTML = '<p class="muted">Load a circuit to analyse it.</p>'; return; }
    if (!S.insights) {
      el.innerHTML = S.insightsError ? `<div class="unavail">Insights failed: ${esc(S.insightsError)}</div>`
        : '<p class="muted"><i class="fa-solid fa-spinner fa-spin"></i> Computing structural insights...</p>';
      return;
    }
    const I = S.insights, s = I.structure, t = I.timing, a = I.area, p = I.power;
    const caps = Object.entries(I.capabilities).map(([k, c]) =>
      `<span class="cap ${c.supported ? '' : 'off'}" title="${esc(c.note || c.mode)}">${esc(k)}${c.supported && c.mode !== 'deterministic' ? ' · ' + esc(c.mode) : ''}</span>`).join('');
    const path = t.paths && t.paths[0];
    const maxGates = Math.max(...a.blocks.map(b => b.gates), 1);
    el.innerHTML = `
      <div class="data-banner"><i class="fa-solid fa-circle-info"></i> ${esc(I.data_availability.note)}</div>
      <div class="card"><span class="label">Capabilities for this circuit</span><div class="cap-row">${caps}</div></div>
      ${chartsHtml(I)}
      ${bomHtml(I)}
      <div class="card"><div class="flex justify-between"><span class="label">Structure</span>${basisChip('deterministic')}</div>
        <div class="ins-line"><b>What it does:</b> ${esc(s.plain_purpose || 'No plain-language function has been inferred yet.')}</div>
        <div class="ins-line"><b>Inputs:</b> ${s.inputs.map(x => esc(x.name) + (x.width > 1 ? `[${x.width}]` : '')).join(', ')}</div>
        <div class="ins-line"><b>Outputs:</b> ${s.outputs.map(x => esc(x.name) + (x.width > 1 ? `[${x.width}]` : '')).join(', ')}</div>
        <div class="ins-line"><b>Control signals:</b> ${s.control_signals.length ? s.control_signals.slice(0, 4).map(c =>
          `${chipify('[N:' + c.net + ']')} <span class="muted">(${esc(c.why)}; fan-out ${c.fanout})</span>`).join('; ') : '<span class="muted">none detected</span>'}</div>
        ${s.datapath_chains.length ? `<div class="ins-line"><b>Datapaths:</b>${s.datapath_chains.slice(0, 4).map(d => `<div class="small">${esc(d)}</div>`).join('')}</div>` : ''}
        <div class="ins-line muted small">${s.combinational_only ? 'Purely combinational: no registers or clock cells.' : 'Sequential cells: ' + esc(s.sequential_cells.join(', '))}</div>
      </div>
      <div class="card"><div class="flex justify-between"><span class="label">Timing (structural: gate levels)</span>${basisChip('deterministic')}</div>
        ${path ? `<div class="ins-line">Longest path: <b>${path.levels} gate levels</b> (${t.critical_gate_count} gates on a longest path)
          <button class="mini" data-hlpath="1"><i class="fa-solid fa-location-crosshairs"></i> Highlight</button></div>
          <div class="ins-path">${chipify(gchips(path.gates))}</div>
          <div class="muted small">from ${esc(path.from_inputs.join(', ') || '-')} to ${esc(path.to_outputs.join(', ') || '-')} · ${esc(t.model)}</div>` : '<p class="muted">No levels computed.</p>'}
        ${(t.carry_chains || []).slice(0, 2).map(c => `<div class="ins-line">Ripple carry chain (${esc(c.block)}): ${c.length} cells ${chipify(gchips(c.gates))}</div>`).join('')}
        <div class="ins-line"><b>Highest fan-out:</b> ${t.high_fanout.slice(0, 5).map(h => `${chipify('[N:' + h.net + ']')} ${h.fanout}`).join(' · ')}</div>
        <div class="ask-row">${askButtons([['Show the longest paths', 'Show the longest paths', '', ''], ['What could hurt timing?', 'What could hurt timing?', '', '']])}</div>
      </div>
      <div class="card"><div class="flex justify-between"><span class="label">Area proxy (gate counts)</span>${basisChip('deterministic')}</div>
        ${a.blocks.map(b => `<div class="bar-row"><span>${esc(b.name)}</span><div class="bar"><div style="width:${(100 * b.gates / maxGates).toFixed(1)}%"></div></div><span class="muted">${b.gates} (${Math.round(b.share * 100)}%)</span></div>`).join('')}
        <div class="ins-line small">Duplicate gates: <b>${a.duplicate_gate_count}</b>${a.duplicate_groups.length ? ' · e.g. ' + chipify(a.duplicate_groups[0].gates.map(g => `[G${g}]`).join(' ')) : ''} · inverter pairs: <b>${a.inverter_pairs.length}</b> · logic without output path: <b>${a.logic_without_output_path.length}</b></div>
      </div>
      <div class="card"><div class="flex justify-between"><span class="label">Power indicators</span>${basisChip('structural heuristic')}</div>
        ${p.select_outputs.map(x => `<div class="ins-line">${esc(x.to)} selects between ${esc(x.from.join(', '))}: all results switch in parallel.</div>`).join('')}
        ${p.cones.slice(0, 4).map(c => `<div class="ins-line small">Cone of ${esc(c.bus)}: ${c.cone_gates} gates, ${c.xor_adder_cells} XOR/adder cells</div>`).join('')}
        <div class="muted small">${esc(p.note)}</div>
      </div>
      <span class="label">Optimization candidates (${I.optimizations.length}) · none measured</span>
      ${I.optimizations.map(optHtml).join('') || '<p class="muted small">No candidates.</p>'}
      ${I.capabilities.graphsaint.supported ? `<div class="card"><div class="flex justify-between"><span class="label">GraphSAINT regions</span>${basisChip('ml_prediction')}</div>
        <div class="ins-line">${I.modules} predicted modules. With model-based hints: ${I.suspicious_modules.length ? I.suspicious_modules.map(m => chipify(`[M${m}]`)).join(' ') : 'none'}</div></div>`
        : `<div class="card muted small">${esc(I.capabilities.graphsaint.note || 'No GraphSAINT prediction.')}</div>`}`;
    el.querySelectorAll('[data-hl]').forEach(b => b.addEventListener('click', () => {
      const o = I.optimizations.find(x => x.id === b.dataset.hl);
      if (o) Overlays.focus({ gate_ids: o.gate_ids });
    }));
    el.querySelectorAll('[data-bom]').forEach(tr => tr.addEventListener('click', () => {
      const ds = el.querySelector(`[data-ds="${tr.dataset.bom}"]`);
      if (ds) ds.classList.toggle('hidden');
    }));
    el.querySelectorAll('[data-bomhl]').forEach(btn => btn.addEventListener('click', () => {
      Overlays.focus({ gate_ids: I.bom.rows[Number(btn.dataset.bomhl)].gate_ids.slice(0, 200) }, { inspect: false });
    }));
    const hp = el.querySelector('[data-hlpath]');
    if (hp) hp.addEventListener('click', () => Overlays.focus({ gate_ids: path.gates }));
    bindAsk(el);
  }

  function renderStarters() {
    const el = $('chat-starters');
    if (!el) return;
    const caps = S.insights ? S.insights.capabilities : { understand: { supported: true }, debug: { supported: true } };
    el.innerHTML = STARTER_GROUPS.filter(g => caps[g.cap] && caps[g.cap].supported).map(g => {
      const mode = caps[g.cap].mode;
      return `<div class="starter-group"><span class="grp">${g.name}${mode === 'structural' ? '<small>structural</small>' : ''}</span>
        ${g.items.map(it => `<button class="starter" data-q="${esc(it.q)}" ${it.needs ? `data-needs="${it.needs}" title="Uses the selected ${it.needs}"` : ''}>${esc(it.q)}</button>`).join('')}</div>`;
    }).join('');
  }

  // ----------------------------------------------------------------- overview
  function renderBom() {
    const el = $('tab-bom');
    if (!el) return;
    if (!S.source) { el.innerHTML = '<p class="muted">Load a circuit to view its bill of materials.</p>'; return; }
    if (!S.insights) { el.innerHTML = '<p class="muted"><i class="fa-solid fa-spinner fa-spin"></i> Building the BOM...</p>'; return; }
    el.innerHTML = bomHtml(S.insights);
  }

  function renderAll() { renderOverview(); renderIssues(); renderBom(); renderInsights(); renderStarters(); renderChatAvailability(); }

  function healthOf() {
    if (S.report) return S.report.health;
    if (!S.analysis) return null;
    return S.analysis.stats.errors ? 'errors' : (S.analysis.stats.warnings ? 'warnings' : 'ok');
  }

  function renderOverview() {
    const el = $('tab-overview');
    if (!el) return;
    if (!S.source) { el.innerHTML = '<p class="muted">Load a circuit to analyse it.</p>'; return; }
    if (S.analysisBusy && !S.analysis) { el.innerHTML = '<p class="muted"><i class="fa-solid fa-spinner fa-spin"></i> Running connectivity checks...</p>'; return; }
    if (!S.analysis) { el.innerHTML = `<p class="muted">${esc(S.analysisError || 'No analysis yet.')}</p>`; return; }
    const it = S.analysis.intent;
    const conf = Math.round((it.confidence || 0) * 100);
    const h = healthOf();
    const hLabel = { ok: 'Healthy: no connection problems found', warnings: 'Warnings found', errors: 'Errors found' }[h];
    const blocks = (it.blocks || []).map(b => `
      <div class="block-row"><span class="role role-${esc(b.role)}">${esc(b.role)}</span>
        <span class="bname">${esc(b.name)}</span><span class="muted">${b.width ? esc(b.width) + '-bit' : ''}</span>
        <div class="muted small">in: ${(b.input_buses || []).map(x => chipify('[B:' + x + ']')).join(' ') || '-'} &rarr;
          out: ${(b.output_buses || []).map(x => chipify('[B:' + x + ']')).join(' ') || '-'}</div></div>`).join('');
    const flow = (it.dataflow || []).length ? `<div class="flow">${it.dataflow.map(d =>
      `<span class="flow-node">${esc(d.from_block)}</span><span class="flow-arrow">&rarr;<small>${esc(d.via_bus)}</small>&rarr;</span><span class="flow-node">${esc(d.to_block)}</span>`).join('<br>')}</div>` : '';
    let reportHtml;
    if (S.reportBusy) reportHtml = '<p class="muted"><i class="fa-solid fa-spinner fa-spin"></i> Writing the report...</p>';
    else if (S.report) reportHtml = `<div class="summary">${chipify(S.report.summary)}</div>
        ${S.report.health === 'ok' ? `<div class="clean"><i class="fa-solid fa-circle-check"></i> ${chipify(S.report.clean_confirmation)}</div>` : ''}
        ${droppedNote(S.report.dropped_refs)}`;
    else if (!S.status.available) reportHtml = `<div class="unavail">Assistant unavailable: ${esc(S.status.reason || S.reportError || '')}. Detection and overlays still work.</div>`;
    else if (S.reportError) reportHtml = `<div class="unavail">Report failed: ${esc(S.reportError)}</div>`;
    else if (S.status.available) reportHtml = '<p class="muted small">Generate a concise assistant summary when you need it. The circuit checks and BOM are already available.</p>';
    else reportHtml = '';
    el.innerHTML = `
      <div class="card">
        <div class="flex justify-between items-center"><span class="label">Inferred intent</span>
          <span class="src">${it.source === 'llm' ? 'LLM + checks' : 'deterministic'}${S.analysis.cached ? ' · cached' : ''}</span></div>
        <div class="intent-fn">${esc(it.intended_function)}</div>
        <div class="layman">${chipify(it.summary_for_layman)}</div>
        <div class="conf"><div class="conf-bar"><div style="width:${conf}%"></div></div><span>${conf}% confidence</span></div>
        ${it.llm_error ? `<div class="unavail small">LLM intent failed (${esc(it.llm_error)}); showing the deterministic intent.</div>` : ''}
        ${droppedNote(it.dropped_refs)}
      </div>
      <div class="card"><span class="label">Blocks</span>${blocks || '<p class="muted small">No recognisable blocks.</p>'}${flow}</div>
      <div class="card">
        <div class="flex justify-between items-center">
          <span class="health health-${esc(h)}">${esc(hLabel)}</span>
          <div class="flex gap-2"><button id="generate-report-btn" class="regen" ${S.reportBusy || S.analysisBusy || !S.status.available ? 'disabled' : ''}><i class="fa-solid fa-wand-magic-sparkles"></i> Generate summary</button>
          <button id="regen-btn" class="regen" ${S.reportBusy || S.analysisBusy ? 'disabled' : ''} title="Refresh deterministic analysis"><i class="fa-solid fa-rotate"></i></button></div>
        </div>
        <div class="muted small">${S.analysis.stats.errors} errors · ${S.analysis.stats.warnings} warnings · ${S.analysis.stats.infos} info</div>
        ${reportHtml}
      </div>
      <div class="notes">${(S.analysis.honesty_notes || []).map(n => `<div><i class="fa-solid fa-circle-info"></i> ${esc(n)}</div>`).join('')}</div>`;
    const rb = $('regen-btn');
    if (rb) rb.addEventListener('click', regenerate);
    const grb = $('generate-report-btn');
    if (grb) grb.addEventListener('click', () => loadReport(false));
  }

  // ----------------------------------------------------------------- issues
  function renderIssues() {
    const el = $('tab-issues');
    if (!el) return;
    const cnt = $('issues-count');
    if (!S.analysis) {
      el.innerHTML = S.analysisBusy ? '<p class="muted"><i class="fa-solid fa-spinner fa-spin"></i> Analysing...</p>' : '<p class="muted">No analysis yet.</p>';
      if (cnt) cnt.textContent = '';
      return;
    }
    const fs = S.analysis.findings;
    const main = fs.filter(f => f.category !== 'gnn_suspicion');
    const sus = fs.filter(f => f.category === 'gnn_suspicion');
    if (cnt) cnt.textContent = main.filter(f => f.severity !== 'info').length || '';
    const items = S.report ? S.report.items : [];
    const itemHtml = items.map((it, i) => `
      <div class="item sev-border-${esc(it.severity)}" data-item="${i}">
        <div class="item-head">${sevBadge(it.severity)} ${certChip(it.certainty)} <span class="title">${esc(it.title)}</span></div>
        <div><b>What:</b> ${chipify(it.what)}</div>
        <div><b>Where:</b> ${chipify(it.where)}</div>
        <div><b>Why it matters:</b> ${chipify(it.why_it_matters)}</div>
        <div><b>Fix:</b> ${chipify(it.fix)}</div>
        ${it.verilog_suggestion ? `<div class="snippet-label">Suggestion, not applied</div><pre class="snippet">${esc(it.verilog_suggestion)}</pre>` : ''}
        <div class="muted small">Findings: ${it.finding_ids.map(f => chipify('[' + f + ']')).join(' ')}</div>
        <div class="ask-row">${askButtons(it.certainty === 'suspicion'
          ? [['Why is this suspicious?', 'Why is this flagged as suspicious? Is it an ML prediction or a netlist fact?', 'finding', it.finding_ids[0]]]
          : [['How do I fix this?', 'How do I fix this?', 'finding', it.finding_ids[0]]])}</div>
      </div>`).join('');
    const filt = f => (S.filters.severity === 'all' || f.severity === S.filters.severity)
                    && (S.filters.category === 'all' || f.category === S.filters.category);
    const groups = {};
    main.filter(filt).forEach(f => (groups[f.category] = groups[f.category] || []).push(f));
    const fHtml = f => `
      <div class="finding sev-border-${esc(f.severity)}" data-finding="${esc(f.id)}">
        <div class="item-head">${sevBadge(f.severity)} ${certChip(f.certainty)} <b>${esc(f.id)}</b> <span class="muted">${esc(f.check)}</span></div>
        <div class="small"><b>In simple terms:</b> ${esc(laymanFinding(f))}</div>
        <div class="small">${esc(f.evidence)}</div>
        ${f.suggested_edges && f.suggested_edges.length ? `<div class="small sugg"><i class="fa-solid fa-link-slash"></i> ${f.suggested_edges.length} suggested connection(s)${f.suggested_edges.some(e => e.ambiguous) ? ' · ambiguous' : ''}</div>` : ''}
        <div class="ask-row">${askButtons(f.category === 'gnn_suspicion'
          ? [['Why is this suspicious?', 'Why is this flagged as suspicious? Is it an ML prediction or a netlist fact?', 'finding', f.id]]
          : [['Explain', 'Explain this finding', 'finding', f.id], ['How do I fix this?', 'How do I fix this?', 'finding', f.id]])}</div>
      </div>`;
    el.innerHTML = `
      ${S.reportBusy ? '<p class="muted small"><i class="fa-solid fa-spinner fa-spin"></i> Report in progress...</p>' : ''}
      ${items.length ? `<div class="label">Report</div>${itemHtml}` : (S.report ? '<div class="clean small"><i class="fa-solid fa-circle-check"></i> The report lists no problems.</div>' : '')}
      <div class="filters">
        <select id="f-sev"><option value="all">All severities</option><option>error</option><option>warning</option><option>info</option></select>
        <select id="f-cat"><option value="all">All categories</option>${['electrical', 'reachability', 'structural', 'intent'].map(c => `<option value="${c}">${CAT_LABEL[c]}</option>`).join('')}</select>
      </div>
      ${Object.keys(groups).length ? Object.entries(groups).map(([c, list]) => `<div class="label">${CAT_LABEL[c] || c} (${list.length})</div>${list.map(fHtml).join('')}`).join('')
        : '<p class="muted small">No findings match (no connection problems detected).</p>'}
      <details id="sus-group" ${S.suspicionsOpen ? 'open' : ''}><summary>Model-based suspicions (${sus.length})</summary>
        <p class="muted small">Hints from the GNN predictions (${esc(S.analysis.stats.prediction_source)}); not evidence of a wiring fault.</p>
        ${sus.map(fHtml).join('')}</details>`;
    $('f-sev').value = S.filters.severity;
    $('f-cat').value = S.filters.category;
    $('f-sev').addEventListener('change', e => { S.filters.severity = e.target.value; renderIssues(); });
    $('f-cat').addEventListener('change', e => { S.filters.category = e.target.value; renderIssues(); });
    $('sus-group').addEventListener('toggle', e => { S.suspicionsOpen = e.target.open; Overlays.setShowSuspicions(S.suspicionsOpen); });
    el.querySelectorAll('[data-item]').forEach(n => n.addEventListener('click', ev => {
      if (ev.target.closest('.ref-chip')) return;
      const it = items[Number(n.dataset.item)];
      Overlays.focus({ gate_ids: it.gate_ids, suggested_edges: it.suggested_edges, finding_ids: it.finding_ids });
    }));
    el.querySelectorAll('[data-finding]').forEach(n => n.addEventListener('click', ev => {
      if (ev.target.closest('.ref-chip') || ev.target.closest('[data-ask]')) return;
      focusFinding(n.dataset.finding);
    }));
    bindAsk(el);
  }

  function focusFinding(fid) {
    const f = S.analysis && S.analysis.findings.find(x => x.id === fid);
    if (!f) return;
    if (f.category === 'gnn_suspicion' && !S.suspicionsOpen) { S.suspicionsOpen = true; Overlays.setShowSuspicions(true); }
    Overlays.focus({ gate_ids: f.gate_ids, suggested_edges: f.suggested_edges, finding_ids: [f.id] });
    // after focus: the gate inspector it opens would otherwise make the gate the selection
    setSelection({ kind: 'finding', id: fid });
    inspectorAsk(askButtons(f.category === 'gnn_suspicion'
      ? [['Why is this suspicious?', 'Why is this flagged as suspicious? Is it an ML prediction or a netlist fact?', 'finding', fid]]
      : [['Explain ' + fid, 'Explain this finding', 'finding', fid], ['How do I fix this?', 'How do I fix this?', 'finding', fid]]));
  }

  // ----------------------------------------------------------------- chips
  function onChipClick(ev) {
    const chip = ev.target.closest('.ref-chip');
    if (!chip) return;
    ev.stopPropagation();
    const kind = chip.dataset.kind, val = chip.dataset.val;
    if (kind === 'gate') { Overlays.focus({ gate_ids: [Number(val)] }); onGateInspected(Number(val)); }
    else if (kind === 'finding') focusFinding(val);
    else if (kind === 'module') {
      const n = Number(val);
      const gates = S.refGates.modules[val] || (typeof currentSubcircuits !== 'undefined' && currentSubcircuits[n - 1]
                                                 ? currentSubcircuits[n - 1].gate_ids : []);
      if (typeof highlightSubcircuit === 'function' && typeof currentSubcircuits !== 'undefined' && currentSubcircuits[n - 1]) {
        highlightSubcircuit(n - 1);             // shows the module in the inspector and calls onModuleInspected
      } else onModuleInspected(n, gates);
    }
    else if (kind === 'net') {
      Overlays.focus({ gate_ids: S.refGates.nets[val] || [] }, { inspect: false });
      setSelection({ kind: 'net', id: val });
      $('node-inspector').classList.remove('hidden');
      $('inspector-badge').textContent = 'Net';
      $('node-details').textContent = `Net ${val}: drivers and readers highlighted (gates ${(S.refGates.nets[val] || []).map(g => 'G' + g).join(', ') || 'unknown'}).`;
      inspectorAsk(askButtons([['What drives this net?', 'What drives this net and what reads it?', 'net', val],
        ['High fan-out?', 'Does this net have a high fan-out, and could that hurt timing or power?', 'net', val]]));
    }
    else if (kind === 'bus') {
      let gates = S.refGates.buses[val];
      if (!gates && S.analysis) gates = [];
      Overlays.focus({ gate_ids: gates || [] });
    }
  }

  // ----------------------------------------------------------------- chat
  function renderChatAvailability() {
    const input = $('chat-input'), send = $('chat-send');
    if (!input) return;
    const ok = S.status.available && !!S.source;
    input.disabled = !ok || S.chatBusy;
    send.disabled = !ok || S.chatBusy;
    input.placeholder = !S.status.available ? `Assistant unavailable: ${S.status.reason || ''}` : 'Ask about this circuit...';
    $('chat-starters').classList.toggle('hidden', !ok);
  }

  function addMsg(role, html) {
    const log = $('chat-log');
    const div = document.createElement('div');
    div.className = 'msg msg-' + role;
    div.innerHTML = html;
    log.appendChild(div);
    log.scrollTop = log.scrollHeight;
    return div;
  }

  async function sendChat(text) {
    text = (text || '').trim();
    if (!text || S.chatBusy || !S.source) return;
    S.chatBusy = true;
    renderChatAvailability();
    $('chat-input').value = '';
    addMsg('user', esc(text));
    const pending = addMsg('assistant', '<i class="fa-solid fa-spinner fa-spin"></i> Thinking...');
    const token = S.token;
    try {
      const body = Object.assign({ session_id: S.sessionId, message: text }, S.source);
      if (S.selection) body.focus = { kind: S.selection.kind, id: S.selection.id };
      const r = await postJson('/api/assistant/chat', body);
      if (token !== S.token) { pending.remove(); return; }
      S.sessionId = r.session_id;
      mergeRefGates(r.ref_gates);
      // the context pill follows what the conversation is about, so "it" is always visible
      if (r.subject) setSelection({ kind: r.subject.kind, id: r.subject.id });
      const tools = r.tool_trace.length ? `<details class="trace"><summary>${r.tool_trace.length} tool call(s)</summary>${r.tool_trace.map(t =>
        `<div>${t.ok ? '✓' : '✗'} ${esc(t.tool)}(${esc(JSON.stringify(t.arguments))})${t.auto ? ' <span class="muted">auto</span>' : ''}</div>`).join('')}</details>` : '';
      const ev = (r.evidence || []);
      const evHtml = ev.length ? `<div class="evidence"><div class="muted small">Evidence computed from the circuit (not written by the AI):</div>${ev.map((c, i) => `
        <div class="ev-card"><div class="ev-head" data-ev="${i}"><span>${chipify(gref(c.title))}</span>${basisChip(c.basis)}</div>
          ${c.kind === 'optimization' ? `<div class="ins-line"><span class="k">Reason</span>${esc(c.reason)}</div>
            <div class="ins-line"><span class="k">Evidence</span>${chipify(gref(c.evidence))}</div>
            <div class="ins-line"><span class="k">Impact</span>${esc(c.impact)} <span class="muted">(confidence ${esc(c.confidence)})</span></div>`
          : c.lines.slice(0, 8).map(l => `<div class="ins-line">${chipify(gref(l))}</div>`).join('')}
        </div>`).join('')}</div>` : '';
      pending.innerHTML = `${ev.length ? `<div class="ai-label">${basisChip('AI explanation')}</div>` : ''}<div class="reply">${chipify(r.reply)}</div>${droppedNote(r.dropped_refs)}${evHtml}${tools}`;
      pending.querySelectorAll('[data-ev]').forEach(n => n.addEventListener('click', e => {
        if (e.target.closest('.ref-chip')) return;
        const c = ev[Number(n.dataset.ev)];
        if (c.gate_ids.length) Overlays.focus({ gate_ids: c.gate_ids, finding_ids: c.finding_ids }, { inspect: false });
      }));
      const h = r.highlights;
      if (h && (h.gate_ids.length || h.suggested_edges.length || h.edges.length)) {
        Overlays.focus({ gate_ids: h.gate_ids, suggested_edges: h.suggested_edges, edges: h.edges,
                         finding_ids: h.finding_ids }, { zoom: false, inspect: false });
      }
    } catch (e) {
      pending.innerHTML = `<span class="err">${esc(e.message)}</span>`;
    } finally {
      S.chatBusy = false;
      renderChatAvailability();
    }
  }

  window.Assistant = { toggle, openBom, onCircuitLoaded, refreshStatus, setTab, focusFinding, ask, setSelection,
                       onGateInspected, onModuleInspected, state: S };
  document.addEventListener('DOMContentLoaded', () => { buildDrawer(); refreshStatus(); });
})();
