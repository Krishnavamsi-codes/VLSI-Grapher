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
    refGates: { nets: {}, buses: {} },
  };
  const STARTERS = ['What does this circuit do?', 'Are there any issues?', 'Why is F001 reported?',
                    'What is G0 connected to?', 'What are the fan-in and fan-out of G0?','What does GraphSAINT predict for G0?'];
  const CAT_LABEL = { electrical: 'Electrical', reachability: 'Reachability', structural: 'Structural',
                      intent: 'Intent', gnn_suspicion: 'Model-based' };

  const $ = id => document.getElementById(id);
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const REF_RE = /\[(?:G(\d+)|F(\d+)|N:((?:[^\[\]]|\[\d+\])+)|B:([^\[\]\s]+))\]/g;

  // ----------------------------------------------------------------- rendering helpers
  function chipify(text) {
    let out = '', last = 0;
    const src = String(text || '');
    src.replace(REF_RE, (m, g, f, n, b, idx) => {
      out += esc(src.slice(last, idx));
      last = idx + m.length;
      if (g !== undefined) out += `<button class="ref-chip chip-gate" data-kind="gate" data-val="${esc(g)}">G${esc(g)}</button>`;
      else if (f !== undefined) out += `<button class="ref-chip chip-finding" data-kind="finding" data-val="F${esc(f)}">F${esc(f)}</button>`;
      else if (n !== undefined) out += `<button class="ref-chip chip-net" data-kind="net" data-val="${esc(n)}">${esc(n)}</button>`;
      else out += `<button class="ref-chip chip-bus" data-kind="bus" data-val="${esc(b)}">${esc(b)}</button>`;
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
        <button data-tab="chat" class="tab">Chat</button>
      </div>
      <div class="drawer-body">
        <section id="tab-overview"></section>
        <section id="tab-issues" class="hidden"></section>
        <section id="tab-chat" class="hidden">
          <div id="chat-log" class="chat-log"></div>
          <div id="chat-starters" class="starters"></div>
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
    $('chat-starters').innerHTML = STARTERS.map(q => `<button class="starter">${esc(q)}</button>`).join('');
    $('chat-starters').querySelectorAll('.starter').forEach(b => b.addEventListener('click', () => sendChat(b.textContent)));
    renderAll();
  }

  function toggle(open) {
    const want = open === undefined ? !document.body.classList.contains('drawer-open') : open;
    document.body.classList.toggle('drawer-open', want);
    setTimeout(() => {
      window.dispatchEvent(new Event('resize'));
      if (typeof network !== 'undefined' && network) network.redraw();
    }, 260);
  }

  function setTab(tab) {
    S.tab = tab;
    document.querySelectorAll('#assistant-drawer .tab').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
    ['overview', 'issues', 'chat'].forEach(t => $('tab-' + t).classList.toggle('hidden', t !== tab));
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
    else if (S.status.available && S.analysis && !S.report && !S.reportError) loadReport(false);
    renderOverview();
    renderChatAvailability();
  }

  // ----------------------------------------------------------------- data flow
  function onCircuitLoaded(source) {
    S.source = source;
    S.analysis = null; S.report = null; S.reportError = null; S.sessionId = null;
    S.token += 1;
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
    if (token === S.token && S.analysis && S.status.available) loadReport(regenerate);
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
  }

  // ----------------------------------------------------------------- overview
  function renderAll() { renderOverview(); renderIssues(); renderChatAvailability(); }

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
          <button id="regen-btn" class="regen" ${S.reportBusy || S.analysisBusy ? 'disabled' : ''}><i class="fa-solid fa-rotate"></i> Regenerate</button>
        </div>
        <div class="muted small">${S.analysis.stats.errors} errors · ${S.analysis.stats.warnings} warnings · ${S.analysis.stats.infos} info</div>
        ${reportHtml}
      </div>
      <div class="notes">${(S.analysis.honesty_notes || []).map(n => `<div><i class="fa-solid fa-circle-info"></i> ${esc(n)}</div>`).join('')}</div>`;
    const rb = $('regen-btn');
    if (rb) rb.addEventListener('click', regenerate);
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
      </div>`).join('');
    const filt = f => (S.filters.severity === 'all' || f.severity === S.filters.severity)
                    && (S.filters.category === 'all' || f.category === S.filters.category);
    const groups = {};
    main.filter(filt).forEach(f => (groups[f.category] = groups[f.category] || []).push(f));
    const fHtml = f => `
      <div class="finding sev-border-${esc(f.severity)}" data-finding="${esc(f.id)}">
        <div class="item-head">${sevBadge(f.severity)} ${certChip(f.certainty)} <b>${esc(f.id)}</b> <span class="muted">${esc(f.check)}</span></div>
        <div class="small">${esc(f.evidence)}</div>
        ${f.suggested_edges && f.suggested_edges.length ? `<div class="small sugg"><i class="fa-solid fa-link-slash"></i> ${f.suggested_edges.length} suggested connection(s)${f.suggested_edges.some(e => e.ambiguous) ? ' · ambiguous' : ''}</div>` : ''}
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
      if (ev.target.closest('.ref-chip')) return;
      focusFinding(n.dataset.finding);
    }));
  }

  function focusFinding(fid) {
    const f = S.analysis && S.analysis.findings.find(x => x.id === fid);
    if (!f) return;
    if (f.category === 'gnn_suspicion' && !S.suspicionsOpen) { S.suspicionsOpen = true; Overlays.setShowSuspicions(true); }
    Overlays.focus({ gate_ids: f.gate_ids, suggested_edges: f.suggested_edges, finding_ids: [f.id] });
  }

  // ----------------------------------------------------------------- chips
  function onChipClick(ev) {
    const chip = ev.target.closest('.ref-chip');
    if (!chip) return;
    ev.stopPropagation();
    const kind = chip.dataset.kind, val = chip.dataset.val;
    if (kind === 'gate') Overlays.focus({ gate_ids: [Number(val)] });
    else if (kind === 'finding') focusFinding(val);
    else if (kind === 'net') Overlays.focus({ gate_ids: S.refGates.nets[val] || [] });
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
      const r = await postJson('/api/assistant/chat', Object.assign({ session_id: S.sessionId, message: text }, S.source));
      if (token !== S.token) { pending.remove(); return; }
      S.sessionId = r.session_id;
      mergeRefGates(r.ref_gates);
      const tools = r.tool_trace.length ? `<details class="trace"><summary>${r.tool_trace.length} tool call(s)</summary>${r.tool_trace.map(t =>
        `<div>${t.ok ? '✓' : '✗'} ${esc(t.tool)}(${esc(JSON.stringify(t.arguments))})${t.auto ? ' <span class="muted">auto</span>' : ''}</div>`).join('')}</details>` : '';
      pending.innerHTML = `<div class="reply">${chipify(r.reply)}</div>${droppedNote(r.dropped_refs)}${tools}`;
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

  window.Assistant = { toggle, onCircuitLoaded, refreshStatus, setTab, focusFinding, state: S };
  document.addEventListener('DOMContentLoaded', () => { buildDrawer(); refreshStatus(); });
})();
