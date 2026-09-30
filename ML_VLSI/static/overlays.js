/*
 * overlays.js - "missing connection spotted here" overlays for the graph view (vis-network)
 * and the canvas schematic, plus canvas zoom / pan / click-to-select.
 *
 * Two layers:
 *   background : halos + pin markers for error/warning findings (capped at MAX_MARKERS gates)
 *   focus      : the selected finding / report item / chat highlight: ghost "missing?" edges,
 *                PI/PO stubs, markers, pulsing halo
 * Overlays never change the ground-truth fill colour: only borders, shadows and extra items.
 * Globals used from the page script: currentCircuitData, network, graphNodesDS, graphEdgesDS,
 * schematicView, schematicLayout, activeVisualView, renderCircuitSchematic, showGateInspector.
 */
(function () {
  'use strict';
  const MAX_MARKERS = 200;
  const COLORS = { error: '#ef4444', warning: '#f59e0b', suspicion: '#fb923c', focus: '#f472b6',
                   ghost: '#ef4444', pi: '#22d3ee', existing: '#38bdf8' };
  const RANK = { error: 0, warning: 1, suspicion: 2 };

  const state = {
    show: true,
    showSuspicions: false,
    analysis: null,
    background: new Map(),      // gate id -> 'error' | 'warning' | 'suspicion'
    markers: [],                // {gate, pin, level, title}
    focus: null,                // {gates:Set, ghost:[], edges:[], markers:[]}
    pulseUntil: 0,
    touched: new Set(),
    extraNodeIds: [],           // overlay items currently in the vis DataSets
    extraEdgeIds: [],
  };
  const BIG_GRAPH = 3000;       // above this many gates: no shadows / pulse on the graph (render cost)

  const nodeCount = () => (currentCircuitData && currentCircuitData.nodes) ? currentCircuitData.nodes.length : 0;
  const validGate = g => Number.isInteger(g) && g >= 0 && g < nodeCount();

  function levelOf(f) {
    if (f.category === 'gnn_suspicion') return 'suspicion';
    if (f.severity === 'error') return 'error';
    if (f.severity === 'warning') return 'warning';
    return null;
  }

  function markersFor(f, cap) {
    const out = [];
    const input = ['missing_pin', 'floating_net'].includes(f.check);
    const output = ['dangling_output', 'carry_out_unread'].includes(f.check);
    if (!input && !output) return out;
    for (const p of f.pins || []) {
      if (out.length >= cap || !validGate(p.gate_id)) break;
      out.push({ gate: p.gate_id, pin: p.pin, level: input ? 'error' : 'warning',
                 title: input ? `Input pin ${p.pin} ${f.check === 'floating_net' ? 'reads an undriven net' : 'is unconnected'} (${f.id})`
                              : `Output pin ${p.pin} drives nothing (${f.id})` });
    }
    return out;
  }

  function rebuildBackground() {
    state.background = new Map();
    state.markers = [];
    if (!state.analysis) return;
    for (const f of state.analysis.findings) {
      const lvl = levelOf(f);
      if (!lvl || (lvl === 'suspicion' && !state.showSuspicions)) continue;
      for (const g of f.gate_ids) {
        if (!validGate(g)) continue;
        if (!state.background.has(g) && state.background.size >= MAX_MARKERS) break;
        const cur = state.background.get(g);
        if (cur === undefined || RANK[lvl] < RANK[cur]) state.background.set(g, lvl);
      }
      if (state.markers.length < MAX_MARKERS) state.markers.push(...markersFor(f, MAX_MARKERS - state.markers.length));
    }
  }

  // ------------------------------------------------------------------ public API
  function setAnalysis(analysis) {
    state.analysis = analysis;
    state.focus = null;
    rebuildBackground();
    refresh();
  }

  function clear() {
    state.analysis = null;
    state.focus = null;
    state.background = new Map();
    state.markers = [];
    refresh();
  }

  function setShow(on) {
    state.show = !!on;
    refresh();
  }

  function setShowSuspicions(on) {
    state.showSuspicions = !!on;
    rebuildBackground();
    refresh();
  }

  /* spec: {gate_ids, suggested_edges, edges, finding_ids}; opts: {zoom:true, inspect:true} */
  function focus(spec, opts) {
    opts = Object.assign({ zoom: true, inspect: true }, opts || {});
    const findings = state.analysis ? state.analysis.findings : [];
    const byId = new Map(findings.map(f => [f.id, f]));
    const gates = new Set((spec.gate_ids || []).filter(validGate));
    const ghost = [];
    const markers = [];
    for (const fid of spec.finding_ids || []) {
      const f = byId.get(fid);
      if (!f) continue;
      f.gate_ids.filter(validGate).slice(0, 50).forEach(g => gates.add(g));
      markers.push(...markersFor(f, 50));
    }
    for (const e of spec.suggested_edges || []) {
      const fromOk = e.from_gate == null ? typeof e.from_net === 'string' : validGate(e.from_gate);
      const toOk = e.to_gate == null ? typeof e.to_po === 'string' : validGate(e.to_gate);
      if (!fromOk || !toOk) continue;                       // never draw an invalid id
      ghost.push(e);
      if (e.from_gate != null) gates.add(e.from_gate);
      if (e.to_gate != null) gates.add(e.to_gate);
    }
    const edges = (spec.edges || []).filter(e => validGate(e.from_gate) && validGate(e.to_gate));
    edges.forEach(e => { gates.add(e.from_gate); gates.add(e.to_gate); });
    state.focus = { gates, ghost, edges, markers };
    state.pulseUntil = performance.now() + 1500;
    if (!state.show) setShow(true);
    refresh();
    if (opts.zoom) zoomTo([...gates]);
    if (opts.inspect && gates.size && typeof showGateInspector === 'function') showGateInspector([...gates][0]);
    pulse();
    return [...gates];
  }

  function refresh() {
    applyGraph();
    drawCanvas();
  }

  // ------------------------------------------------------------------ vis-network layer
  function applyGraph() {
    if (typeof network === 'undefined' || !network || typeof graphNodesDS === 'undefined' || !graphNodesDS) return;
    // vis-network charges a fixed cost per DataSet operation on big graphs (~0.4 s at 12k nodes),
    // so all node changes go into ONE upsert and all edge changes into ONE upsert. Stale overlay
    // items are hidden, not removed.
    if (state.ds !== graphNodesDS) {            // new circuit / rebuilt network: forget old overlay ids
      state.ds = graphNodesDS;
      state.touched.clear();
      state.extraNodeIds = [];
      state.extraEdgeIds = [];
    }
    const nodes = currentCircuitData.nodes;
    const big = nodes.length > BIG_GRAPH;
    const nodeUpd = new Map();
    const edgeUpd = new Map();
    for (const id of state.touched) {
      const n = nodes[id];
      if (n) nodeUpd.set(id, { id, borderWidth: 1, shadow: { enabled: false },
                               color: { background: n.color, border: '#ffffff',
                                        highlight: { background: '#f43f5e', border: '#ffffff' } },
                               shapeProperties: { borderDashes: false } });
    }
    state.touched.clear();
    state.extraNodeIds.forEach(id => nodeUpd.set(id, { id, hidden: true }));
    state.extraEdgeIds.forEach(id => edgeUpd.set(id, { id, hidden: true }));

    const extraNodes = [], extraEdges = [];
    if (state.show) {
      const halo = (g, color, width, size, dashed) => {
        const n = nodes[g];
        if (!n) return;
        nodeUpd.set(g, { id: g, borderWidth: big ? width + 2 : width,
                         color: { background: n.color, border: color, highlight: { background: n.color, border: color } },
                         shadow: { enabled: !big, color, size, x: 0, y: 0 },
                         shapeProperties: { borderDashes: dashed ? [2, 3] : false } });
        state.touched.add(g);
      };
      for (const [g, lvl] of state.background) {
        halo(g, COLORS[lvl], lvl === 'suspicion' ? 2 : 3, lvl === 'suspicion' ? 6 : 12, lvl === 'suspicion');
      }
      const pulsing = performance.now() < state.pulseUntil;
      if (state.focus) {
        for (const g of state.focus.gates) {
          const lvl = state.background.get(g);
          halo(g, lvl ? COLORS[lvl] : COLORS.focus, 5, pulsing ? 28 : 18, false);
        }
      }

      // extra items: ghost edges, PI/PO stubs, pin markers
      const needPos = new Set();
      const allMarkers = state.markers.concat(state.focus ? state.focus.markers : []).slice(0, MAX_MARKERS);
      allMarkers.forEach(m => needPos.add(m.gate));
      const ghost = state.focus ? state.focus.ghost : [];
      ghost.forEach(e => { if (e.from_gate != null) needPos.add(e.from_gate); if (e.to_gate != null) needPos.add(e.to_gate); });
      const pos = needPos.size ? network.getPositions([...needPos]) : {};
      const stub = (id, label, x, y, title) => extraNodes.push({
        id, label, x, y, hidden: false, fixed: true, physics: false, shape: 'box', size: 8, title,
        color: { background: '#083344', border: COLORS.pi }, font: { color: '#a5f3fc', size: 10, face: 'JetBrains Mono' } });
      ghost.forEach((e, i) => {
        let from = e.from_gate, to = e.to_gate;
        const title = `Suggested missing connection (not applied)\n${e.reason || ''}\nconfidence ${e.confidence}`
                      + (e.ambiguous ? '\nambiguous: one of the candidates is the extra driver' : '');
        if (from == null) {
          const p = pos[to] || { x: 0, y: 0 };
          from = `ov-pi-${i}`;
          stub(from, e.from_net, p.x - 90, p.y - 50, `Primary input ${e.from_net}`);
        }
        if (to == null) {
          const p = pos[from] || { x: 0, y: 0 };
          to = `ov-po-${i}`;
          stub(to, e.to_po, p.x + 90, p.y - 50, `Primary output ${e.to_po}`);
        }
        extraEdges.push({ id: `ov-ghost-${i}`, from, to, hidden: false, label: 'missing?', title, physics: false,
                          smooth: false, dashes: [8, 6], width: 2.5, color: { color: COLORS.ghost, highlight: COLORS.ghost },
                          arrows: { to: { enabled: true, scaleFactor: 0.9 } },
                          font: { color: '#fecaca', size: 12, strokeWidth: 3, strokeColor: '#450a0a', align: 'top' } });
      });
      (state.focus ? state.focus.edges : []).forEach((e, i) => extraEdges.push({
        id: `ov-hl-${i}`, from: e.from_gate, to: e.to_gate, hidden: false, physics: false, width: 4,
        color: { color: COLORS.existing }, arrows: { to: { enabled: true } } }));
      allMarkers.forEach((m, i) => {
        const p = pos[m.gate];
        if (!p) return;
        extraNodes.push({ id: `ov-m-${i}`, x: p.x + 16, y: p.y - 16, hidden: false, fixed: true, physics: false,
                          shape: 'dot', size: 5, title: m.title, label: m.pin, font: { color: '#fecaca', size: 9 },
                          color: { background: COLORS[m.level], border: '#ffffff' } });
      });
    }
    extraNodes.forEach(n => nodeUpd.set(n.id, n));
    extraEdges.forEach(e => edgeUpd.set(e.id, e));
    const known = new Set(state.extraNodeIds.concat(extraNodes.map(n => n.id)));
    const knownE = new Set(state.extraEdgeIds.concat(extraEdges.map(e => e.id)));
    if (nodeUpd.size) graphNodesDS.update([...nodeUpd.values()]);
    if (edgeUpd.size) graphEdgesDS.update([...edgeUpd.values()]);
    state.extraNodeIds = [...known];     // hidden-or-visible overlay items that exist in the DataSets
    state.extraEdgeIds = [...knownE];
  }

  // ------------------------------------------------------------------ canvas layer
  function overlayCanvas() {
    return document.getElementById('schematic-overlay');
  }

  function drawCanvas() {
    const canvas = overlayCanvas();
    if (!canvas || typeof schematicLayout === 'undefined' || !schematicLayout) return;
    const container = canvas.parentElement;
    const dpr = window.devicePixelRatio || 1;
    const W = container.clientWidth, H = container.clientHeight;
    if (canvas.width !== W * dpr || canvas.height !== H * dpr) {
      canvas.width = W * dpr;
      canvas.height = H * dpr;
    }
    const ctx = canvas.getContext('2d');
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (!state.show) return;
    const v = schematicView;
    ctx.setTransform(dpr * v.scale, 0, 0, dpr * v.scale, dpr * v.tx, dpr * v.ty);
    const { positions, gateWidth: gw, gateHeight: gh } = schematicLayout;
    const px = 1 / v.scale;   // one screen pixel in world units

    const ring = (p, color, width, dashed, pad) => {
      ctx.save();
      ctx.strokeStyle = color;
      ctx.lineWidth = width * px;
      ctx.shadowColor = color;
      ctx.shadowBlur = 10;
      if (dashed) ctx.setLineDash([3 * px, 3 * px]);
      ctx.beginPath();
      ctx.roundRect(p.x - pad * px, p.y - pad * px, gw + 2 * pad * px, gh + 2 * pad * px, 8);
      ctx.stroke();
      ctx.restore();
    };
    for (const [g, lvl] of state.background) {
      const p = positions[g];
      if (p) ring(p, COLORS[lvl], lvl === 'suspicion' ? 1.5 : 2.5, lvl === 'suspicion', 3);
    }
    const now = performance.now();
    if (state.focus) {
      const t = Math.max(0, state.pulseUntil - now) / 1500;
      const pad = 4 + 6 * Math.abs(Math.sin(t * Math.PI * 3));
      for (const g of state.focus.gates) {
        const p = positions[g];
        if (p) ring(p, state.background.has(g) ? COLORS[state.background.get(g)] : COLORS.focus, 3.5, false, pad);
      }
      state.focus.edges.forEach(e => {
        const a = positions[e.from_gate], b = positions[e.to_gate];
        if (a && b) wire(ctx, a.x + gw, a.y + gh / 2, b.x, b.y + gh / 2, COLORS.existing, 3 * px, null, px);
      });
      state.focus.ghost.forEach(e => {
        let a = e.from_gate != null ? positions[e.from_gate] : null;
        let b = e.to_gate != null ? positions[e.to_gate] : null;
        let ax, ay, bx, by;
        if (b) { bx = b.x; by = b.y + gh / 2; }
        if (a) { ax = a.x + gw; ay = a.y + gh / 2; }
        if (!a && b) { ax = bx - 90 * px; ay = by - 40 * px; stubBox(ctx, ax, ay, e.from_net, px, 'left'); }
        if (a && !b) { bx = ax + 90 * px; by = ay - 40 * px; stubBox(ctx, bx, by, e.to_po, px, 'right'); }
        if (ax === undefined || bx === undefined) return;
        wire(ctx, ax, ay, bx, by, COLORS.ghost, 2.5 * px, [7 * px, 5 * px], px, 'missing?');
      });
    }
    const allMarkers = state.markers.concat(state.focus ? state.focus.markers : []).slice(0, MAX_MARKERS);
    for (const m of allMarkers) {
      const p = positions[m.gate];
      if (!p) continue;
      ctx.save();
      ctx.fillStyle = COLORS[m.level];
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = px;
      ctx.beginPath();
      ctx.arc(p.x + gw, p.y, 4.5 * px, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
      ctx.restore();
    }
  }

  function wire(ctx, ax, ay, bx, by, color, width, dash, px, label) {
    ctx.save();
    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    ctx.lineWidth = width;
    if (dash) ctx.setLineDash(dash);
    const mx = (ax + bx) / 2;
    ctx.beginPath();
    ctx.moveTo(ax, ay);
    ctx.bezierCurveTo(mx, ay, mx, by, bx, by);
    ctx.stroke();
    ctx.setLineDash([]);
    // arrowhead in the signal direction (towards b)
    const s = 8 * px;
    ctx.beginPath();
    ctx.moveTo(bx, by);
    ctx.lineTo(bx - s, by - s * 0.6);
    ctx.lineTo(bx - s, by + s * 0.6);
    ctx.closePath();
    ctx.fill();
    if (label) {
      ctx.font = `bold ${11 * px}px Inter, sans-serif`;
      const tw = ctx.measureText(label).width;
      ctx.fillStyle = 'rgba(69,10,10,0.9)';
      ctx.fillRect(mx - tw / 2 - 3 * px, (ay + by) / 2 - 14 * px, tw + 6 * px, 14 * px);
      ctx.fillStyle = '#fecaca';
      ctx.fillText(label, mx - tw / 2, (ay + by) / 2 - 3 * px);
    }
    ctx.restore();
  }

  function stubBox(ctx, x, y, text, px, side) {
    ctx.save();
    ctx.font = `${10 * px}px 'JetBrains Mono', monospace`;
    const tw = ctx.measureText(text || '').width + 8 * px;
    const bx = side === 'left' ? x - tw : x;
    ctx.fillStyle = '#083344';
    ctx.strokeStyle = COLORS.pi;
    ctx.lineWidth = px;
    ctx.fillRect(bx, y - 8 * px, tw, 16 * px);
    ctx.strokeRect(bx, y - 8 * px, tw, 16 * px);
    ctx.fillStyle = '#a5f3fc';
    ctx.fillText(text || '', bx + 4 * px, y + 3.5 * px);
    ctx.restore();
  }

  // ------------------------------------------------------------------ pulse + zoom
  let pulseTimer = null;
  function pulse() {
    if (pulseTimer) return;
    const step = () => {
      const alive = performance.now() < state.pulseUntil;
      drawCanvas();
      if (activeVisualView === 'graph' && nodeCount() <= BIG_GRAPH) applyGraphFocusOnly(alive);
      if (alive) pulseTimer = setTimeout(() => requestAnimationFrame(step), 120);
      else { pulseTimer = null; if (nodeCount() <= BIG_GRAPH) applyGraph(); drawCanvas(); }
    };
    step();
  }

  let pulseFlip = false;
  function applyGraphFocusOnly(alive) {
    if (!state.focus || typeof graphNodesDS === 'undefined' || !graphNodesDS || !state.show) return;
    pulseFlip = !pulseFlip;
    const nodes = currentCircuitData.nodes;
    const upd = [];
    for (const g of state.focus.gates) {
      const color = state.background.has(g) ? COLORS[state.background.get(g)] : COLORS.focus;
      if (nodes[g]) upd.push({ id: g, shadow: { enabled: true, color, size: alive && pulseFlip ? 34 : 14, x: 0, y: 0 } });
    }
    if (upd.length) graphNodesDS.update(upd);
  }

  function zoomTo(gates) {
    gates = gates.filter(validGate);
    if (!gates.length) return;
    if (activeVisualView === 'graph') {
      if (typeof network !== 'undefined' && network) {
        // freeze the layout first: with physics still running the focused nodes drift out of view
        // (and the PI/PO stubs, which are pinned, would detach from their gates)
        network.stopSimulation();
        network.fit({ nodes: gates, maxZoomLevel: 1.6, animation: { duration: 500, easingFunction: 'easeInOutQuad' } });
      }
      return;
    }
    centerCanvasOn(gates);
  }

  function centerCanvasOn(gates) {
    if (typeof schematicLayout === 'undefined' || !schematicLayout) renderCircuitSchematic();
    if (!schematicLayout) return;
    const { positions, gateWidth: gw, gateHeight: gh } = schematicLayout;
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    gates.forEach(g => {
      const p = positions[g];
      if (!p) return;
      x0 = Math.min(x0, p.x); y0 = Math.min(y0, p.y);
      x1 = Math.max(x1, p.x + gw); y1 = Math.max(y1, p.y + gh);
    });
    if (!isFinite(x0)) return;
    const container = document.getElementById('schematic-canvas-container');
    const W = container.clientWidth, H = container.clientHeight;
    const pad = 140;
    const scale = Math.max(0.2, Math.min(400, Math.min(W / (x1 - x0 + pad), H / (y1 - y0 + pad)), 6));
    schematicView.scale = scale;
    schematicView.tx = W / 2 - ((x0 + x1) / 2) * scale;
    schematicView.ty = H / 2 - ((y0 + y1) / 2) * scale;
    renderCircuitSchematic();
  }

  // ------------------------------------------------------------------ canvas interaction
  function initCanvas() {
    const canvas = overlayCanvas();
    if (!canvas) return;
    let drag = null;
    canvas.addEventListener('wheel', ev => {
      ev.preventDefault();
      const r = canvas.getBoundingClientRect();
      const mx = ev.clientX - r.left, my = ev.clientY - r.top;
      const v = schematicView;
      const k = Math.exp(-ev.deltaY * 0.0015);
      const ns = Math.max(0.2, Math.min(400, v.scale * k));
      v.tx = mx - (mx - v.tx) * (ns / v.scale);
      v.ty = my - (my - v.ty) * (ns / v.scale);
      v.scale = ns;
      scheduleRender();
    }, { passive: false });
    canvas.addEventListener('mousedown', ev => {
      drag = { x: ev.clientX, y: ev.clientY, tx: schematicView.tx, ty: schematicView.ty, moved: false };
    });
    window.addEventListener('mousemove', ev => {
      if (!drag) return;
      const dx = ev.clientX - drag.x, dy = ev.clientY - drag.y;
      if (Math.abs(dx) + Math.abs(dy) > 3) drag.moved = true;
      schematicView.tx = drag.tx + dx;
      schematicView.ty = drag.ty + dy;
      if (drag.moved) scheduleRender();
    });
    window.addEventListener('mouseup', ev => {
      if (!drag) return;
      const wasClick = !drag.moved;
      drag = null;
      if (wasClick && ev.target === canvas) selectAt(ev);
    });
  }

  let renderPending = false;
  function scheduleRender() {
    if (renderPending) return;
    renderPending = true;
    requestAnimationFrame(() => { renderPending = false; renderCircuitSchematic(); });
  }

  function selectAt(ev) {
    if (!schematicLayout) return;
    const canvas = overlayCanvas();
    const r = canvas.getBoundingClientRect();
    const v = schematicView;
    const wx = (ev.clientX - r.left - v.tx) / v.scale, wy = (ev.clientY - r.top - v.ty) / v.scale;
    const { positions, gateWidth: gw, gateHeight: gh } = schematicLayout;
    for (const id in positions) {
      const p = positions[id];
      if (wx >= p.x && wx <= p.x + gw && wy >= p.y && wy <= p.y + gh) {
        const g = Number(id);
        if (typeof showGateInspector === 'function') showGateInspector(g);
        focus({ gate_ids: [g] }, { zoom: false, inspect: false });
        return;
      }
    }
  }

  window.Overlays = { setAnalysis, clear, setShow, setShowSuspicions, focus, refresh, applyGraph, drawCanvas,
                      zoomTo, centerCanvasOn, initCanvas, state, COLORS };
  document.addEventListener('DOMContentLoaded', initCanvas);
})();
