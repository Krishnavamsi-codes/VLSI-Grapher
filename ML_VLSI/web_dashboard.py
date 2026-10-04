"""
web_dashboard.py - Interactive GNN-RE Web Application & API Server
Serves an interactive visual dashboard for hardware netlist reverse engineering,
graph visualization, circuit schematic diagrams with identified sub-circuits,
live GNN inference, and Layman/Professor explanations.
"""

import csv
import http.server
import io
import json
import os
import traceback
import urllib.parse
import time
from netlist_graph_engine import (parse_verilog_netlist, parse_verilog_text, build_circuit_graph,
                                  NetlistParseError, CLASS_NAMES, CLASS_COLORS)
from gnn_engine import CircuitGNN, extract_subcircuit_boundaries
import gnn_re_inference
import circuit_store
from circuit_store import CircuitRefError, DATASET_DIR, resolve_circuit
import threading
from analysis_service import AnalysisService
from assistant import Assistant, MAX_MESSAGE_CHARS
from llm_client import LLMClient, LLMError

HOST = '127.0.0.1'
PORT = 8501
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
STATIC_TYPES = {
    '.js': 'application/javascript; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.svg': 'image/svg+xml',
    '.png': 'image/png',
    '.woff2': 'font/woff2',
}
# Upload text arrives JSON-escaped, so allow headroom over the raw 10 MB limit
MAX_BODY_BYTES = 2 * circuit_store.MAX_UPLOAD_BYTES + 64 * 1024

# Initialize GNN model
gnn_model = CircuitGNN(in_dim=34, hidden_dim=64, num_classes=5, depth=2, lr=0.03)

def fast_pretrain():
    start = time.time()
    candidate_files = [
        'Train_add_mul_1_bit_Syn_65nm.v',
        'Train_add_mul_4_bit_Syn_65nm.v',
        'Train_add_mul_combine_4_bit_Syn_65nm.v',
        'Train_add_mul_comp_4_bit_Syn_65nm.v',
        'Train_add_mul_sub_2_bit_Syn_65nm.v'
    ]
    for cfile in candidate_files:
        fpath = os.path.join(DATASET_DIR, cfile)
        if os.path.exists(fpath):
            parsed = parse_verilog_netlist(fpath)
            if parsed and len(parsed['gates']) > 0:
                _, edges, feats, labels = build_circuit_graph(parsed)
                for _ in range(3):
                    gnn_model.train_epoch(feats, edges, labels)
    print(f"[*] Pre-trained Circuit GNN in {time.time() - start:.2f}s.")

try:
    fast_pretrain()
except Exception as e:
    print("Pre-training warning:", e)

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>GNN-RE Studio | AI Circuit Reverse Engineering</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <link rel="stylesheet" href="/static/dashboard.css">
  <link rel="stylesheet" href="/static/assistant.css">
</head>
<body class="text-slate-100 min-h-screen selection:bg-indigo-500 selection:text-white">
  <!-- Top Navigation Bar -->
  <header class="border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-xl sticky top-0 z-50 px-6 py-3.5 flex items-center justify-between">
    <div class="flex items-center space-x-3">
      <div class="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-500 via-purple-500 to-cyan-400 flex items-center justify-center font-bold text-lg shadow-lg glow-indigo">
        <i class="fa-solid fa-microchip text-white"></i>
      </div>
      <div>
        <div class="flex items-center space-x-2">
          <h1 class="text-base font-bold text-white tracking-wide">GNN-RE Studio</h1>
          <span class="text-[10px] uppercase font-semibold tracking-wider px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">IEEE TCAD</span>
        </div>
        <p class="text-[11px] text-slate-400">Netlist-to-Graph & Sub-Circuit Boundary Recognition Engine</p>
      </div>
    </div>
    <button id="assistant-toggle" onclick="Assistant.toggle()" class="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-indigo-600/20 border border-indigo-500/40 text-indigo-200 text-xs font-semibold hover:bg-indigo-600/40 transition">
      <span id="assistant-dot" class="status-dot off"></span><i class="fa-solid fa-robot"></i> Assistant
    </button>
  </header>

  <!-- Main Grid Layout -->
  <main class="max-w-[1600px] mx-auto px-6 py-5 grid grid-cols-1 lg:grid-cols-12 gap-5">
    
    <!-- LEFT COLUMN: Circuit Input & Explanations (4 cols) -->
    <div class="lg:col-span-4 space-y-5">
      
      <!-- 1. Circuit Selector & Upload Card -->
      <div class="glass-card rounded-2xl p-5 shadow-2xl space-y-4">
        <div class="flex items-center justify-between">
          <h2 class="text-sm font-semibold text-white flex items-center tracking-wide">
            <i class="fa-solid fa-cloud-arrow-up text-cyan-400 mr-2 text-base"></i> 1. Circuit Input & Netlist
          </h2>
          <span id="circuit-badge" class="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">Synthesized 65nm</span>
        </div>

        <!-- Tab selection: Benchmark vs Upload -->
        <div class="flex space-x-2 border-b border-slate-800/80 pb-2 text-xs">
          <button id="tab-bench-btn" onclick="switchInputTab('benchmark')" class="text-cyan-400 font-semibold border-b-2 border-cyan-400 pb-1 px-1">Benchmark Library</button>
          <button id="tab-upload-btn" onclick="switchInputTab('upload')" class="text-slate-400 hover:text-white pb-1 px-1 transition">Upload Custom .V</button>
        </div>

        <!-- Benchmark Dropdown -->
        <div id="tab-benchmark-content" class="space-y-2">
          <label class="text-[11px] text-slate-400 font-medium">Select Gate-Level Benchmark Netlist</label>
          <select id="circuit-select" onchange="loadSelectedCircuit()" class="w-full bg-slate-950/90 border border-slate-700/80 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500">
            <option value="">Loading circuits...</option>
          </select>
        </div>

        <!-- Upload File Box -->
        <div id="tab-upload-content" class="hidden space-y-2">
          <label class="text-[11px] text-slate-400 font-medium">Upload Gate-Level Verilog File</label>
          <div id="drop-zone" onclick="document.getElementById('file-input').click()" class="border-2 border-dashed border-slate-700/80 hover:border-indigo-500 rounded-xl p-4 text-center cursor-pointer bg-slate-950/50 transition">
            <i class="fa-solid fa-file-arrow-up text-2xl text-indigo-400 mb-1"></i>
            <div class="text-xs text-slate-300 font-medium">Click or Drag & Drop .v netlist</div>
            <div class="text-[10px] text-slate-500">Supports Gate-Level Verilog (*.v)</div>
            <input type="file" id="file-input" accept=".v,.verilog,.txt" onchange="handleFileUpload(event)" class="hidden">
          </div>
        </div>

        <!-- Run Inference CTA Button -->
        <button onclick="runInference()" id="run-btn" class="w-full bg-gradient-to-r from-indigo-500 via-purple-600 to-cyan-500 hover:opacity-95 text-white font-semibold py-2.5 rounded-xl shadow-lg glow-indigo flex items-center justify-center space-x-2 text-xs transition active:scale-[0.99]">
          <i class="fa-solid fa-bolt"></i> <span>Run GNN Reverse Engineering</span>
        </button>
      </div>

      <!-- 2. Model Performance & Accuracy Card -->
      <div class="glass-card rounded-2xl p-5 shadow-2xl space-y-3">
        <h3 class="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center">
          <i class="fa-solid fa-chart-pie text-emerald-400 mr-2"></i> Model Performance & Accuracy
        </h3>

        <!-- Column headers -->
        <div class="grid grid-cols-2 gap-3 text-center text-[10px] font-semibold mb-1">
          <div class="bg-slate-800/60 rounded-lg py-1.5 text-slate-400 border border-slate-700/60">
            <i class="fa-solid fa-microchip mr-1 text-slate-500"></i> Baseline GNN <span class="text-slate-600">(2-layer, 3ep)</span>
          </div>
          <div class="bg-indigo-950/60 rounded-lg py-1.5 text-indigo-300 border border-indigo-500/30">
            <i class="fa-solid fa-brain mr-1 text-indigo-400"></i> GNN-RE <span class="text-indigo-500">(GraphSAINT, 2k ep)</span>
          </div>
        </div>

        <!-- Metric rows -->
        <div class="grid grid-cols-2 gap-3">
          <!-- Baseline -->
          <div class="space-y-2">
            <div class="bg-slate-950/80 p-2.5 rounded-xl border border-slate-800/80 text-center">
              <div class="text-[10px] text-slate-500 font-medium">Node Accuracy</div>
              <div id="base-acc" class="text-lg font-bold text-slate-400 mt-0.5 font-mono">--%</div>
            </div>
            <div class="bg-slate-950/80 p-2.5 rounded-xl border border-slate-800/80 text-center">
              <div class="text-[10px] text-slate-500 font-medium">Micro-F1</div>
              <div id="base-micro" class="text-lg font-bold text-slate-400 mt-0.5 font-mono">--%</div>
            </div>
            <div class="bg-slate-950/80 p-2.5 rounded-xl border border-slate-800/80 text-center">
              <div class="text-[10px] text-slate-500 font-medium">Macro-F1</div>
              <div id="base-macro" class="text-lg font-bold text-slate-400 mt-0.5 font-mono">--%</div>
            </div>
          </div>
          <!-- GNN-RE -->
          <div class="space-y-2">
            <div class="bg-indigo-950/40 p-2.5 rounded-xl border border-indigo-500/20 text-center">
              <div class="text-[10px] text-indigo-400 font-medium">Node Accuracy</div>
              <div id="metric-acc" class="text-lg font-bold text-emerald-400 mt-0.5 font-mono">--%</div>
            </div>
            <div class="bg-indigo-950/40 p-2.5 rounded-xl border border-indigo-500/20 text-center">
              <div class="text-[10px] text-indigo-400 font-medium">Micro-F1</div>
              <div id="metric-micro" class="text-lg font-bold text-cyan-400 mt-0.5 font-mono">--%</div>
            </div>
            <div class="bg-indigo-950/40 p-2.5 rounded-xl border border-indigo-500/20 text-center">
              <div class="text-[10px] text-indigo-400 font-medium">Macro-F1</div>
              <div id="metric-macro" class="text-lg font-bold text-purple-400 mt-0.5 font-mono">--%</div>
            </div>
          </div>
        </div>

        <div id="gnnre-note" class="hidden text-[10px] text-amber-300/90 leading-snug"></div>

        <div class="pt-2 border-t border-slate-800/80">
          <div class="text-[11px] font-semibold text-slate-400 mb-1.5">Gate Distribution by Class:</div>
          <div id="class-breakdown" class="space-y-1.5 text-[11px] text-slate-300 font-mono">
            <div class="text-slate-500 italic">Select a circuit or run GNN to see breakdown.</div>
          </div>
        </div>
      </div>

    </div>

    <!-- RIGHT COLUMN: Dual Visualization (Schematic & Graph), Gate Inspector & Metrics (8 cols) -->
    <div class="lg:col-span-8 space-y-5">
      
      <!-- Visualization Card with Tabs -->
      <div class="glass-card rounded-2xl p-5 shadow-2xl space-y-3">
        <div class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800/80 pb-3">
          
          <!-- View Tabs (Circuit Schematic vs Graph Topology) -->
          <div class="flex items-center space-x-2 bg-slate-950/90 p-1 rounded-xl border border-slate-800/80 text-xs">
            <button id="view-schematic-btn" onclick="switchVisualView('schematic')" class="px-3 py-1.5 rounded-lg font-semibold bg-indigo-600 text-white transition flex items-center">
              <i class="fa-solid fa-shapes mr-1.5"></i> Circuit Schematic & Identified Sub-circuits
            </button>
            <button id="view-graph-btn" onclick="switchVisualView('graph')" class="px-3 py-1.5 rounded-lg font-medium text-slate-400 hover:text-white transition flex items-center">
              <i class="fa-solid fa-diagram-project mr-1.5"></i> Graph Topology View
            </button>
          </div>

          <!-- Color-coded Legend -->
          <div class="flex flex-wrap items-center gap-2.5 text-[11px] bg-slate-950/80 px-3 py-1.5 rounded-xl border border-slate-800/80">
            <span class="flex items-center"><span class="w-2.5 h-2.5 rounded-full mr-1.5 bg-[#38bdf8] shadow-[0_0_8px_#38bdf8]"></span> Adder</span>
            <span class="flex items-center"><span class="w-2.5 h-2.5 rounded-full mr-1.5 bg-[#10b981] shadow-[0_0_8px_#10b981]"></span> Multiplier</span>
            <span class="flex items-center"><span class="w-2.5 h-2.5 rounded-full mr-1.5 bg-[#f59e0b] shadow-[0_0_8px_#f59e0b]"></span> Control</span>
            <span class="flex items-center"><span class="w-2.5 h-2.5 rounded-full mr-1.5 bg-[#a855f7] shadow-[0_0_8px_#a855f7]"></span> Subtractor</span>
            <span class="flex items-center"><span class="w-2.5 h-2.5 rounded-full mr-1.5 bg-[#06b6d4] shadow-[0_0_8px_#06b6d4]"></span> Comparator</span>
          </div>
        </div>

        <!-- 1. Circuit Schematic View with Identified Sub-circuit Boundary Clouds -->
        <div id="schematic-view-container" class="space-y-2">
          <div class="flex items-center justify-between text-xs px-1">
            <span class="text-slate-400">
              <i class="fa-solid fa-layer-group text-purple-400 mr-1"></i>
              <strong>Gate-Level Schematic Diagram:</strong> Shaded regions indicate <em>Identified Functional Sub-circuits</em>
            </span>
            <div class="flex items-center space-x-2">
              <span class="text-[10px] text-slate-500 font-mono">Wheel: zoom · Drag: pan · Click: select</span>
              <button onclick="renderCircuitSchematic(true)" class="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-[10px] text-cyan-300 border border-slate-700">
                <i class="fa-solid fa-arrows-rotate mr-1"></i> Reset View
              </button>
            </div>
          </div>
          <div id="schematic-canvas-container" class="relative overflow-hidden border border-slate-800/80 shadow-inner flex items-center justify-center">
            <canvas id="schematic-canvas" class="w-full h-full cursor-grab active:cursor-grabbing"></canvas>
            <canvas id="schematic-overlay"></canvas>
          </div>
        </div>

        <!-- 2. Graph Topology View -->
        <div id="graph-view-container" class="hidden space-y-2">
          <div class="flex items-center justify-between text-xs px-1">
            <span id="graph-stats" class="text-slate-400 font-mono">0 Gates (Nodes) | 0 Interconnects (Edges)</span>
          </div>
          <div id="network-container" class="border border-slate-800/80 shadow-inner"></div>
        </div>

        <!-- Issue overlays: toggle + legend -->
        <div class="flex flex-wrap items-center justify-between gap-2 px-1">
          <label class="flex items-center gap-2 text-[11px] text-slate-300 cursor-pointer"><input id="show-issues" type="checkbox" checked onchange="Overlays.setShow(this.checked)"> Show issues</label>
          <div class="overlay-legend">
            <span class="lg"><span class="lg-solid"></span>existing wire</span>
            <span class="lg"><span class="lg-ghost"></span>suggested missing (not applied)</span>
            <span class="lg"><span class="lg-halo" style="border-color:#ef4444"></span>error</span>
            <span class="lg"><span class="lg-halo" style="border-color:#f59e0b"></span>warning / structural</span>
            <span class="lg"><span class="lg-halo" style="border-color:#fb923c;border-style:dotted"></span>model-based suspicion</span>
            <span class="lg"><span class="lg-dot" style="background:#ef4444"></span>floating / missing input</span>
            <span class="lg"><span class="lg-dot" style="background:#f59e0b"></span>dangling output</span>
            <span class="lg"><span class="lg-stub">PI</span> primary-input stub</span>
          </div>
        </div>
        <!-- Node / Gate Inspector -->
        <div id="node-inspector" class="p-3 bg-slate-950/90 border border-slate-800/80 rounded-xl text-xs text-slate-300 hidden">
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-2">
              <span class="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></span>
              <span class="font-semibold text-cyan-300">Gate Inspector:</span>
            </div>
            <span id="inspector-badge" class="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">Active Gate</span>
          </div>
          <div id="node-details" class="mt-2 text-slate-300 leading-relaxed font-mono text-[11px]">
            Click on any gate in the Schematic or Graph to inspect standard-cell library details.
          </div>
        </div>
      </div>

      <!-- Identified Sub-Circuits -->
      <div class="glass-card rounded-2xl p-5 shadow-2xl space-y-3">
        <div class="flex items-center justify-between">
          <h3 class="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center">
            <i class="fa-solid fa-cubes-stacked text-purple-400 mr-2"></i> Identified Functional Sub-Circuits
          </h3>
          <span id="subcircuit-count" class="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-500/10 text-purple-300 border border-purple-500/20">0 Modules</span>
        </div>

        <div id="subcircuits-list" class="space-y-2 max-h-48 overflow-y-auto pr-1 text-xs">
          <div class="p-3 bg-slate-950/80 border border-slate-800/80 rounded-xl text-slate-500 italic text-center">
            Run GNN Reverse Engineering to partition and visualize identified sub-circuits.
          </div>
        </div>
      </div>

    </div>

  </main>

  <!-- Error toast -->
  <div id="toast" class="hidden fixed bottom-5 right-5 z-[60] max-w-sm bg-rose-950/95 border border-rose-500/40 text-rose-100 text-xs rounded-xl shadow-2xl px-4 py-3 flex items-start space-x-2">
    <i class="fa-solid fa-triangle-exclamation text-rose-400 mt-0.5"></i>
    <span id="toast-text"></span>
  </div>

  <script>
    let currentSource = null;          // {circuit_name} or {upload_id} of the loaded circuit
    let currentCircuitData = null;
    let currentSubcircuits = [];
    let network = null;
    let activeVisualView = 'schematic'; // 'schematic' or 'graph'
    let graphNodesDS = null, graphEdgesDS = null;       // vis DataSets (overlays.js updates them)
    let schematicView = { scale: 1, tx: 0, ty: 0 };     // canvas zoom / pan
    let schematicLayout = null;                         // cached gate positions

    const classColors = {
      0: { name: 'Adder', fill: 'rgba(56, 189, 248, 0.15)', border: '#38bdf8', badge: '#0284c7' },
      1: { name: 'Multiplier', fill: 'rgba(16, 185, 129, 0.15)', border: '#10b981', badge: '#059669' },
      2: { name: 'Control Logic', fill: 'rgba(245, 158, 11, 0.15)', border: '#f59e0b', badge: '#d97706' },
      3: { name: 'Subtractor', fill: 'rgba(168, 85, 247, 0.15)', border: '#a855f7', badge: '#7c3aed' },
      4: { name: 'Comparator', fill: 'rgba(6, 182, 212, 0.15)', border: '#06b6d4', badge: '#0891b2' }
    };

    function showError(message) {
      const toast = document.getElementById('toast');
      document.getElementById('toast-text').textContent = message;
      toast.classList.remove('hidden');
      clearTimeout(showError._timer);
      showError._timer = setTimeout(() => toast.classList.add('hidden'), 7000);
    }

    // fetch wrapper: throws Error(message) on network failure, non-JSON or non-2xx responses
    async function apiFetch(url, options) {
      let res;
      try {
        res = await fetch(url, options);
      } catch (e) {
        throw new Error('Network error: could not reach the server.');
      }
      let data = null;
      try { data = await res.json(); } catch (e) { /* non-JSON body */ }
      if (!res.ok) {
        throw new Error((data && data.message) || `Request failed (HTTP ${res.status}).`);
      }
      if (data === null) throw new Error('Unexpected response from the server.');
      return data;
    }

    function postJson(url, body) {
      return apiFetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
    }

    function setCircuitData(data) {
      currentCircuitData = data;
      currentSubcircuits = [];
      schematicView = { scale: 1, tx: 0, ty: 0 };
      schematicLayout = null;
      const badge = document.getElementById('circuit-badge');
      badge.textContent = { upload: 'Uploaded netlist', demo: 'Demo fault (injected)' }[data.source] || 'Synthesized 65nm';
      renderCircuitSchematic();
      // vis-network is built lazily: a 12k-node physics layout would block the page in schematic view
      if (activeVisualView === 'graph') renderGraph(currentCircuitData);
      else if (network) { network.destroy(); network = null; graphNodesDS = graphEdgesDS = null; }
      if (window.Assistant) Assistant.onCircuitLoaded(currentSource);
    }

    async function init() {
      const select = document.getElementById('circuit-select');
      let data;
      try {
        data = await apiFetch('/api/circuits');
      } catch (e) {
        select.innerHTML = '<option value="">Could not load circuits</option>';
        showError(e.message);
        return;
      }
      select.innerHTML = '';
      const addGroup = (label, names) => {
        if (!names || names.length === 0) return;
        const group = document.createElement('optgroup');
        group.label = label;
        names.forEach(c => {
          const opt = document.createElement('option');
          opt.value = c;
          opt.textContent = c.replace('.v', '');
          group.appendChild(opt);
        });
        select.appendChild(group);
      };
      addGroup('Benchmarks', data.circuits);
      addGroup('Demo faults (injected)', data.demo_circuits);
      if (data.circuits.length > 0) {
        select.value = data.circuits[0];
        loadSelectedCircuit();
      }
    }

    function switchInputTab(tab) {
      if (tab === 'benchmark') {
        document.getElementById('tab-benchmark-content').classList.remove('hidden');
        document.getElementById('tab-upload-content').classList.add('hidden');
        document.getElementById('tab-bench-btn').className = "text-cyan-400 font-semibold border-b-2 border-cyan-400 pb-1 px-1";
        document.getElementById('tab-upload-btn').className = "text-slate-400 hover:text-white pb-1 px-1 transition";
      } else {
        document.getElementById('tab-benchmark-content').classList.add('hidden');
        document.getElementById('tab-upload-content').classList.remove('hidden');
        document.getElementById('tab-upload-btn').className = "text-cyan-400 font-semibold border-b-2 border-cyan-400 pb-1 px-1";
        document.getElementById('tab-bench-btn').className = "text-slate-400 hover:text-white pb-1 px-1 transition";
      }
    }

    function switchVisualView(view) {
      activeVisualView = view;
      if (view === 'schematic') {
        document.getElementById('schematic-view-container').classList.remove('hidden');
        document.getElementById('graph-view-container').classList.add('hidden');
        document.getElementById('view-schematic-btn').className = "px-3 py-1.5 rounded-lg font-semibold bg-indigo-600 text-white transition flex items-center";
        document.getElementById('view-graph-btn').className = "px-3 py-1.5 rounded-lg font-medium text-slate-400 hover:text-white transition flex items-center";
        renderCircuitSchematic();
      } else {
        document.getElementById('schematic-view-container').classList.add('hidden');
        document.getElementById('graph-view-container').classList.remove('hidden');
        document.getElementById('view-graph-btn').className = "px-3 py-1.5 rounded-lg font-semibold bg-indigo-600 text-white transition flex items-center";
        document.getElementById('view-schematic-btn').className = "px-3 py-1.5 rounded-lg font-medium text-slate-400 hover:text-white transition flex items-center";
        renderGraph(currentCircuitData);
      }
    }

    async function loadSelectedCircuit() {
      const name = document.getElementById('circuit-select').value;
      if (!name) return;
      try {
        const data = await apiFetch('/api/load_circuit?name=' + encodeURIComponent(name));
        currentSource = { circuit_name: name };
        setCircuitData(data);
      } catch (e) {
        showError(e.message);
        return;
      }
      // Auto-run inference for instant interactive view
      runInference(true);
    }

    async function handleFileUpload(e) {
      const file = e.target.files[0];
      if (!file) return;
      try {
        const text = await file.text();
        const data = await postJson('/api/upload_circuit', { filename: file.name, content: text });
        currentSource = { upload_id: data.upload_id };
        setCircuitData(data);
      } catch (err) {
        showError(err.message);
        return;
      } finally {
        e.target.value = '';   // allow re-uploading the same file
      }
      runInference(true);
    }

    function computeSchematicLayout(width, height) {
      const nodes = currentCircuitData.nodes;
      const edges = currentCircuitData.edges;

      // Calculate in-degree rank
      const ranks = {};
      nodes.forEach(n => ranks[n.id] = 0);
      edges.forEach(([u, v]) => {
        if (ranks[v] !== undefined && ranks[u] !== undefined) {
          ranks[v] = Math.max(ranks[v], ranks[u] + 1);
        }
      });

      const maxRank = Math.max(...Object.values(ranks), 1);
      const cols = Math.min(maxRank + 2, 6);
      const colBuckets = Array.from({ length: cols }, () => []);
      nodes.forEach(n => {
        const colIdx = Math.min(ranks[n.id] || 0, cols - 1);
        colBuckets[colIdx].push(n);
      });

      // Assign (x, y) coordinates to each gate
      const positions = {};
      const gateWidth = 85;
      const gateHeight = 32;
      const colSpacing = (width - 120) / Math.max(cols - 1, 1);
      colBuckets.forEach((bucket, colIdx) => {
        const rowSpacing = Math.min((height - 80) / Math.max(bucket.length, 1), 50);
        const startY = (height - bucket.length * rowSpacing) / 2 + 20;
        bucket.forEach((node, rowIdx) => {
          positions[node.id] = { x: 60 + colIdx * colSpacing, y: startY + rowIdx * rowSpacing, node: node };
        });
      });
      return { positions, gateWidth, gateHeight, width, height, data: currentCircuitData };
    }

    /* ------------------------------------------------------------
       RICH GATE-LEVEL SCHEMATIC & SUB-CIRCUIT BOUNDARY RENDERER
       (wheel = zoom, drag = pan, click = select; overlays are drawn
        on #schematic-overlay by overlays.js)
       ------------------------------------------------------------ */
    function renderCircuitSchematic(resetZoom = false) {
      if (!currentCircuitData || !currentCircuitData.nodes) return;

      const canvas = document.getElementById('schematic-canvas');
      const ctx = canvas.getContext('2d');
      const container = document.getElementById('schematic-canvas-container');
      const dpr = window.devicePixelRatio || 1;
      const width = container.clientWidth;
      const height = container.clientHeight;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      if (resetZoom) schematicView = { scale: 1, tx: 0, ty: 0 };
      if (!schematicLayout || schematicLayout.data !== currentCircuitData
          || schematicLayout.width !== width || schematicLayout.height !== height) {
        schematicLayout = computeSchematicLayout(width, height);
      }
      const { positions, gateWidth, gateHeight } = schematicLayout;
      const nodes = currentCircuitData.nodes;
      const edges = currentCircuitData.edges;
      const v = schematicView;

      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.setTransform(dpr * v.scale, 0, 0, dpr * v.scale, dpr * v.tx, dpr * v.ty);

      // world-space viewport for culling (keeps large circuits responsive)
      const vx0 = -v.tx / v.scale - 20, vy0 = -v.ty / v.scale - 20;
      const vx1 = (width - v.tx) / v.scale + 20, vy1 = (height - v.ty) / v.scale + 20;
      const visible = p => p.x + gateWidth >= vx0 && p.x <= vx1 && p.y + gateHeight >= vy0 && p.y <= vy1;

      // 1. Draw Identified Sub-Circuit Shaded Regions (Bounding Envelopes)
      if (currentSubcircuits.length > 0) {
        currentSubcircuits.forEach((sc, scIdx) => {
          const scGatePos = sc.gate_ids.map(id => positions[id]).filter(Boolean);
          if (scGatePos.length === 0) return;

          let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
          scGatePos.forEach(p => {
            minX = Math.min(minX, p.x - 18);
            minY = Math.min(minY, p.y - 14);
            maxX = Math.max(maxX, p.x + gateWidth + 18);
            maxY = Math.max(maxY, p.y + gateHeight + 14);
          });
          if (maxX < vx0 || minX > vx1 || maxY < vy0 || minY > vy1) return;

          const padding = 12;
          const rectX = minX - padding;
          const rectY = minY - padding;
          const rectW = Math.max(maxX - minX + padding * 2, 110);
          const rectH = Math.max(maxY - minY + padding * 2, 60);
          const cfg = classColors[sc.class_id] || classColors[2];

          ctx.save();
          ctx.fillStyle = cfg.fill;
          ctx.strokeStyle = cfg.border;
          ctx.lineWidth = 1.5;
          ctx.setLineDash([4, 4]);
          ctx.beginPath();
          ctx.roundRect(rectX, rectY, rectW, rectH, 16);
          ctx.fill();
          ctx.stroke();

          ctx.fillStyle = cfg.badge;
          ctx.setLineDash([]);
          ctx.beginPath();
          ctx.roundRect(rectX + 10, rectY - 10, Math.min(rectW - 20, 160), 20, 6);
          ctx.fill();

          ctx.fillStyle = "#ffffff";
          ctx.font = "bold 10px Inter, sans-serif";
          ctx.fillText(`Module #${scIdx+1}: ${sc.class_name} (${sc.size} gates)`, rectX + 16, rectY + 4);
          ctx.restore();
        });
      }

      // 2. Draw Interconnecting Wires (one path: fast on 20k+ wires)
      const onScreenRow = v.scale * Math.min(gateHeight, (height - 80) / Math.max(nodes.length / 6, 1));
      ctx.lineWidth = 1.2;
      ctx.strokeStyle = "#475569";
      ctx.beginPath();
      edges.forEach(([u, w]) => {
        const p1 = positions[u];
        const p2 = positions[w];
        if (p1 && p2 && (visible(p1) || visible(p2))) {
          ctx.moveTo(p1.x + gateWidth, p1.y + gateHeight / 2);
          const midX = (p1.x + gateWidth + p2.x) / 2;
          ctx.bezierCurveTo(midX, p1.y + gateHeight / 2, midX, p2.y + gateHeight / 2, p2.x, p2.y + gateHeight / 2);
        }
      });
      ctx.stroke();

      // 3. Draw Gate Boxes: batched per class colour; labels only when readable on screen
      const byColour = {};
      const labelled = [];
      nodes.forEach(n => {
        const pos = positions[n.id];
        if (!pos || !visible(pos)) return;
        const cfg = classColors[n.ground_truth] || classColors[2];
        (byColour[cfg.border] = byColour[cfg.border] || []).push(pos);
        labelled.push(n);
      });
      ctx.lineWidth = 1.5;
      ctx.fillStyle = "#0f172a";
      for (const [colour, list] of Object.entries(byColour)) {
        ctx.strokeStyle = colour;
        ctx.beginPath();
        list.forEach(pos => ctx.roundRect(pos.x, pos.y, gateWidth, gateHeight, 6));
        ctx.fill();
        ctx.stroke();
      }
      if (onScreenRow >= 9 || labelled.length < 400) {
        labelled.forEach(n => {
          const pos = positions[n.id];
          // Gate Cell Type Label
          ctx.fillStyle = "#f8fafc";
          ctx.font = "bold 9px 'JetBrains Mono', monospace";
          ctx.fillText(n.cell_type.split('_')[0] || n.cell_type, pos.x + 8, pos.y + 14);
          // Gate Instance Name
          ctx.fillStyle = "#94a3b8";
          ctx.font = "8px 'JetBrains Mono', monospace";
          ctx.fillText(n.label.length > 12 ? n.label.substring(0, 10) + '..' : n.label, pos.x + 8, pos.y + 25);
        });
      }

      if (window.Overlays) Overlays.drawCanvas();
    }

    function showGateInspector(nodeId) {
      const node = currentCircuitData && currentCircuitData.nodes[nodeId];
      if (!node) return;
      document.getElementById('node-inspector').classList.remove('hidden');
      document.getElementById('inspector-badge').textContent = `Gate #${node.id}`;
      document.getElementById('node-details').innerHTML = `
        <strong>Gate Name:</strong> <span class="text-white">${node.label}</span> |
        <strong>Standard Cell:</strong> <span class="text-cyan-300">${node.cell_type}</span> |
        <strong>Fan-In:</strong> ${node.in_degree} |
        <strong>Fan-Out:</strong> ${node.out_degree} |
        <strong>Classification:</strong> <span class="px-2 py-0.5 rounded text-white font-semibold" style="background:${node.color}">${node.class_name}</span>
      `;
      if (window.Assistant) Assistant.onGateInspected(node.id);   // "ask about this gate" buttons
    }

    /* ------------------------------------------------------------
       INTERACTIVE GRAPH VISUALIZER
       ------------------------------------------------------------ */
    function renderGraph(data) {
      if (!data || !data.nodes) return;
      document.getElementById('graph-stats').textContent = `${data.nodes.length} Gates (Nodes) | ${data.edges.length} Interconnects (Edges)`;
      
      const nodes = graphNodesDS = new vis.DataSet(data.nodes.map(n => ({
        id: n.id,
        label: n.label.length > 15 ? n.label.substring(0, 12) + '..' : n.label,
        color: {
          background: n.color,
          border: '#ffffff',
          highlight: { background: '#f43f5e', border: '#ffffff' }
        },
        font: { color: '#f8fafc', size: 10, face: 'Inter' },
        shape: 'dot',
        size: 10 + Math.min(n.in_degree + n.out_degree, 12) * 2,
        title: `${n.label} [${n.cell_type}] - Class: ${n.class_name}`
      })));

      const edges = graphEdgesDS = new vis.DataSet(data.edges.map(e => ({
        from: e[0],
        to: e[1],
        arrows: { to: { enabled: true, scaleFactor: 0.6 } },
        color: { color: '#334155', highlight: '#38bdf8' },
        width: 1.2
      })));

      const container = document.getElementById('network-container');
      const networkData = { nodes, edges };
      const options = {
        physics: {
          stabilization: { iterations: 80 },
          barnesHut: { gravitationalConstant: -2000, springLength: 55, springConstant: 0.04 }
        },
        interaction: { hover: true, tooltipDelay: 100 }
      };

      if (network) network.destroy();
      network = new vis.Network(container, networkData, options);

      network.once('stabilizationIterationsDone', () => {
        if (data.nodes.length > 1500) network.setOptions({ physics: false });   // keep big graphs responsive
        if (window.Overlays) Overlays.applyGraph();
      });
      if (window.Overlays) Overlays.applyGraph();

      network.on("click", function (params) {
        if (params.nodes.length > 0 && typeof params.nodes[0] === 'number') showGateInspector(params.nodes[0]);
      });
    }

    async function runInference(silent = false) {
      if (!currentCircuitData || !currentSource) return;
      const btn = document.getElementById('run-btn');
      const idleLabel = '<i class="fa-solid fa-bolt"></i> <span>Run GNN Reverse Engineering</span>';
      if (!silent) btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> <span>Identifying Sub-circuits...</span>';

      let result;
      try {
        result = await postJson('/api/infer', currentSource);
      } catch (e) {
        showError(e.message);
        btn.innerHTML = idleLabel;
        return;
      }

      currentSubcircuits = result.subcircuits;

      // GNN-RE metrics (real 2k-epoch GraphSAINT predictions), or N/A for uploads
      const note = document.getElementById('gnnre-note');
      if (result.metrics) {
        document.getElementById('metric-acc').textContent   = (result.metrics.accuracy * 100).toFixed(1) + '%';
        document.getElementById('metric-micro').textContent = (result.metrics.f1_micro  * 100).toFixed(1) + '%';
        document.getElementById('metric-macro').textContent = (result.metrics.f1_macro  * 100).toFixed(1) + '%';
      } else {
        ['metric-acc', 'metric-micro', 'metric-macro'].forEach(id => document.getElementById(id).textContent = 'N/A');
      }
      note.textContent = result.gnn_re_message || '';
      note.classList.toggle('hidden', !result.gnn_re_message);

      // Baseline metrics (toy 2-layer GNN, 3 training epochs)
      if (result.baseline) {
        document.getElementById('base-acc').textContent   = (result.baseline.accuracy * 100).toFixed(1) + '%';
        document.getElementById('base-micro').textContent = (result.baseline.f1_micro  * 100).toFixed(1) + '%';
        document.getElementById('base-macro').textContent = (result.baseline.f1_macro  * 100).toFixed(1) + '%';
      }

      const classNames = ["Adder", "Multiplier", "Control Logic", "Subtractor", "Comparator"];
      const colors = ["#38bdf8", "#10b981", "#f59e0b", "#a855f7", "#06b6d4"];
      let breakdownHtml = '';

      const counts = [0, 0, 0, 0, 0];
      result.predictions.forEach(p => counts[p]++);

      classNames.forEach((name, idx) => {
        if (counts[idx] > 0) {
          const pct = ((counts[idx] / result.predictions.length) * 100).toFixed(0);
          breakdownHtml += `
            <div class="flex items-center justify-between py-0.5">
              <span class="flex items-center"><span class="w-2 h-2 rounded-full mr-2" style="background:${colors[idx]}"></span>${name}</span>
              <span class="text-slate-400">${counts[idx]} gates (${pct}%)</span>
            </div>
          `;
        }
      });
      document.getElementById('class-breakdown').innerHTML = breakdownHtml;

      document.getElementById('subcircuit-count').textContent = `${result.subcircuits.length} Modules`;
      let subcircuitsHtml = '';
      result.subcircuits.forEach((sc, i) => {
        const color = colors[sc.class_id] || '#64748b';
        subcircuitsHtml += `
          <div class="p-2.5 bg-slate-950/80 border border-slate-800/80 rounded-xl hover:border-slate-600 transition cursor-pointer" onclick="highlightSubcircuit(${i})">
            <div class="flex items-center justify-between font-semibold text-slate-200">
              <span class="flex items-center">
                <span class="w-2 h-2 rounded-full mr-1.5" style="background:${color}"></span>
                Module #${i+1}: ${sc.class_name}
              </span>
              <span class="px-2 py-0.5 rounded text-[10px] text-white font-mono" style="background:${color}">${sc.size} gates</span>
            </div>
            <div class="text-[10px] text-slate-400 mt-1 font-mono truncate">Gates: ${sc.gates.slice(0, 4).join(', ')}${sc.gates.length > 4 ? '...' : ''}</div>
          </div>
        `;
      });
      document.getElementById('subcircuits-list').innerHTML = subcircuitsHtml;

      // Re-render schematic with newly identified sub-circuit boundaries!
      renderCircuitSchematic();

      if (!silent) {
        btn.innerHTML = '<i class="fa-solid fa-circle-check"></i> <span>Sub-circuits Identified!</span>';
        setTimeout(() => {
          btn.innerHTML = '<i class="fa-solid fa-bolt"></i> <span>Run GNN Reverse Engineering</span>';
        }, 2000);
      }
    }

    function highlightSubcircuit(scIdx) {
      if (currentSubcircuits[scIdx]) {
        const sc = currentSubcircuits[scIdx];
        document.getElementById('node-inspector').classList.remove('hidden');
        document.getElementById('inspector-badge').textContent = `Sub-circuit #${scIdx+1}`;
        document.getElementById('node-details').innerHTML = `
          <strong>Identified Module:</strong> <span class="text-cyan-300 font-bold">${sc.class_name}</span> | 
          <strong>Total Gates:</strong> ${sc.size} | 
          <strong>Instances:</strong> <span class="text-slate-300 font-mono text-[10px]">${sc.gates.slice(0, 8).join(', ')}${sc.gates.length > 8 ? '...' : ''}</span>
        `;
        if (window.Assistant) Assistant.onModuleInspected(scIdx + 1, sc.gate_ids);   // highlight + "why suspicious?"
      }
    }

    window.onload = () => {
      init();
      window.addEventListener('resize', () => renderCircuitSchematic());
    };
  </script>
  <script src="/static/overlays.js"></script>
  <script src="/static/assistant.js"></script>
</body>
</html>
"""

def _load_parsed(ref):
    parsed = parse_verilog_netlist(ref.path)
    if parsed is None:
        raise NetlistParseError('No "module <name> ( ... );" declaration found.')
    return parsed


def _baseline_predict(model):
    """Weak baseline GCN predictions, used for model-based hints when GraphSAINT has none."""
    if model['num_gates'] == 0:
        return []
    return gnn_model.evaluate(model['features'], model['edges'], model['labels'])['predictions']


# Configured by make_server(); the LLM client is injectable so tests never hit the network.
SERVICE = None
ASSISTANT = None


def _ref_from(data):
    return resolve_circuit(circuit_name=data.get('circuit_name'), upload_id=data.get('upload_id'))


def _public_analysis(result):
    """What /api/analyze returns (no predictions array, no raw evidence dump)."""
    return {k: result[k] for k in ('intent', 'findings', 'stats', 'cached', 'llm_available', 'honesty_notes')}


class RequestHandler(http.server.BaseHTTPRequestHandler):
    """Explicit routes only: '/', '/api/*' and whitelisted files under /static/."""

    # ---- response helpers -------------------------------------------------
    def _send_bytes(self, status, body, content_type):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status, obj):
        self._send_bytes(status, json.dumps(obj).encode('utf-8'), 'application/json')

    def _send_error_json(self, status, error_code, message):
        self._send_json(status, {'error_code': error_code, 'message': message})

    def _read_json(self):
        try:
            length = int(self.headers.get('Content-Length') or 0)
        except ValueError:
            raise CircuitRefError(400, 'INVALID_REQUEST', 'Invalid Content-Length.')
        if length > MAX_BODY_BYTES:
            raise CircuitRefError(413, 'BODY_TOO_LARGE', 'Request body too large.')
        try:
            data = json.loads(self.rfile.read(length).decode('utf-8') or '{}')
        except (ValueError, UnicodeDecodeError):
            raise CircuitRefError(400, 'INVALID_JSON', 'Request body must be JSON.')
        if not isinstance(data, dict):
            raise CircuitRefError(400, 'INVALID_JSON', 'Request body must be a JSON object.')
        return data

    def _dispatch(self, handler):
        try:
            handler()
        except CircuitRefError as e:
            self._send_error_json(e.status, e.error_code, e.message)
        except NetlistParseError as e:
            self._send_error_json(400, 'INVALID_NETLIST', f'Could not parse netlist: {e}')
        except LLMError as e:
            if e.kind == 'unavailable':
                self._send_json(503, {'error_code': 'ASSISTANT_UNAVAILABLE', 'reason': e.message,
                                      'message': e.message})
            else:
                self._send_json(502, {'error_code': 'ASSISTANT_ERROR', 'message': e.message})
        except Exception:
            traceback.print_exc()
            self._send_error_json(500, 'INTERNAL_ERROR', 'Internal server error.')

    def do_GET(self):
        self._dispatch(self._handle_get)

    def do_POST(self):
        self._dispatch(self._handle_post)

    # ---- GET ----------------------------------------------------------------
    def _handle_get(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)

        if path == '/' or path == '/index.html':
            self._send_bytes(200, HTML_CONTENT.encode('utf-8'), 'text/html; charset=utf-8')
        elif path == '/api/circuits':
            self._send_json(200, {'circuits': circuit_store.list_benchmarks(),
                                  'demo_circuits': circuit_store.list_demos()})
        elif path == '/api/load_circuit':
            ref = resolve_circuit(circuit_name=query.get('name', [None])[0],
                                  upload_id=query.get('upload_id', [None])[0])
            parsed = _load_parsed(ref)
            nodes, edges, feats, labels = build_circuit_graph(parsed)
            self._send_json(200, {
                'module_name': parsed['module_name'],
                'source': ref.kind,
                'nodes': nodes,
                'edges': edges
            })
        elif path == '/api/bom.csv':
            # cell bill of materials (counts from the netlist; area/leakage only if a liberty file is loaded)
            ref = resolve_circuit(circuit_name=query.get('circuit_name', [None])[0],
                                  upload_id=query.get('upload_id', [None])[0])
            bom = SERVICE.insights(ref).bom
            buf = io.StringIO()
            w = csv.writer(buf)
            w.writerow(['cell', 'family', 'description', 'function (naming convention)', 'drive (from name)', 'count',
                        'share', 'blocks', 'inputs', 'outputs', 'area_each', 'area_total', 'leakage_each',
                        'leakage_total', 'data_source'])
            for r in bom['rows']:
                w.writerow([r['cell'], r['family'], r['description'], r['function'] or '', r['drive_strength'],
                            r['count'], r['share'], ' '.join(f'{k}:{v}' for k, v in r['blocks'].items()),
                            ' '.join(r['inputs']), ' '.join(r['outputs']), r['area_each'], r.get('area_total'),
                            r['leakage_each'], r.get('leakage_total'),
                            'liberty' if r['library_data'] else 'cell_library.json + naming convention'])
            body = buf.getvalue().encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/csv; charset=utf-8')
            self.send_header('Content-Disposition', f'attachment; filename="bom_{ref.key.split(":")[-1][:60]}.csv"')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(body)
        elif path == '/api/assistant/status':
            self._send_json(200, ASSISTANT.status())
        elif path.startswith('/static/'):
            self._serve_static(path[len('/static/'):])
        else:
            self._send_error_json(404, 'NOT_FOUND', 'Not found.')

    def _serve_static(self, rel):
        rel = urllib.parse.unquote(rel)
        ext = os.path.splitext(rel)[1].lower()
        if not rel or '\x00' in rel or ext not in STATIC_TYPES or not circuit_store.is_inside(STATIC_DIR, rel):
            self._send_error_json(404, 'NOT_FOUND', 'Not found.')
            return
        full = os.path.realpath(os.path.join(STATIC_DIR, rel))
        if not os.path.isfile(full):
            self._send_error_json(404, 'NOT_FOUND', 'Not found.')
            return
        with open(full, 'rb') as f:
            self._send_bytes(200, f.read(), STATIC_TYPES[ext])

    # ---- POST ---------------------------------------------------------------
    def _handle_post(self):
        path = urllib.parse.urlparse(self.path).path
        if path == '/api/upload_circuit':
            data = self._read_json()
            content = data.get('content')
            circuit_store.check_upload_size(content)
            parsed = parse_verilog_text(content)
            if parsed is None:
                raise NetlistParseError('No "module <name> ( ... );" declaration found.')
            if not parsed['gates']:
                raise NetlistParseError('No gate instances found.')
            upload_id = circuit_store.save_upload(content)
            nodes, edges, feats, labels = build_circuit_graph(parsed)
            self._send_json(200, {
                'upload_id': upload_id,
                'module_name': parsed['module_name'],
                'source': 'upload',
                'nodes': nodes,
                'edges': edges
            })

        elif path == '/api/infer':
            data = self._read_json()
            ref = resolve_circuit(circuit_name=data.get('circuit_name'), upload_id=data.get('upload_id'))
            parsed = _load_parsed(ref)
            nodes, edges, feats, labels = build_circuit_graph(parsed)
            if not nodes:
                raise NetlistParseError('No gate instances found.')

            # ── Baseline: toy 2-layer GNN (3 training epochs) ──────────
            baseline_metrics = gnn_model.evaluate(feats, edges, labels)

            # ── GNN-RE: real 2000-epoch GraphSAINT predictions ──────────
            real_result = gnn_re_inference.lookup_circuit(ref.csv_key) if ref.csv_key else None
            gnn_re_message = None
            if real_result is not None:
                real_preds = real_result['metrics']['predictions']
                n_nodes = len(nodes)
                if len(real_preds) > n_nodes:
                    real_preds = real_preds[:n_nodes]
                elif len(real_preds) < n_nodes:
                    real_preds = real_preds + [int(labels[i]) for i in range(len(real_preds), n_nodes)]
                real_result['metrics']['predictions'] = real_preds
                gnn_re_metrics = real_result['metrics']
                predictions = real_preds
                prediction_source = 'graphsaint'
                if ref.kind == 'demo':
                    gnn_re_message = (f'GraphSAINT predictions of the unfaulted base circuit {ref.csv_key} '
                                      f'(the injected fault keeps gate order).')
                print(f'[/api/infer] GNN-RE predictions for {ref.display_name}: '
                      f'acc={gnn_re_metrics["accuracy"]:.4f}, f1_mic={gnn_re_metrics["f1_micro"]:.4f}')
            else:
                # No GraphSAINT predictions (uploads): report N/A, never pass the baseline off as GNN-RE
                gnn_re_metrics = None
                predictions = baseline_metrics['predictions']
                prediction_source = 'baseline'
                gnn_re_message = 'N/A: no GraphSAINT prediction for uploads. Sub-circuits use the baseline GNN.'
                print(f'[/api/infer] No GraphSAINT predictions for {ref.display_name}; baseline only')

            # Sub-circuit boundaries driven by the best available predictions
            subcircuits = extract_subcircuit_boundaries(nodes, edges, predictions)

            self._send_json(200, {
                'metrics':   gnn_re_metrics,
                'baseline':  baseline_metrics,
                'subcircuits': subcircuits,
                'predictions': predictions,
                'prediction_source': prediction_source,
                'gnn_re_available': gnn_re_metrics is not None,
                'gnn_re_message': gnn_re_message
            })

        elif path == '/api/analyze':
            data = self._read_json()
            result = SERVICE.analyze(_ref_from(data), regenerate=bool(data.get('regenerate')))
            self._send_json(200, _public_analysis(result))

        elif path == '/api/assistant/report':
            data = self._read_json()
            ref = _ref_from(data)
            self._send_json(200, ASSISTANT.generate_report(ref, regenerate=bool(data.get('regenerate'))))

        elif path == '/api/assistant/chat':
            data = self._read_json()
            ref = _ref_from(data)
            message = data.get('message')
            if not isinstance(message, str) or not message.strip():
                raise CircuitRefError(400, 'INVALID_MESSAGE', 'message must be a non-empty string.')
            if len(message) > MAX_MESSAGE_CHARS:
                raise CircuitRefError(413, 'MESSAGE_TOO_LONG', f'message exceeds {MAX_MESSAGE_CHARS} characters.')
            session_id = data.get('session_id')
            if session_id is not None and (not isinstance(session_id, str) or len(session_id) > 64):
                raise CircuitRefError(400, 'INVALID_SESSION', 'Invalid session_id.')
            focus = data.get('focus')
            if focus is not None and (not isinstance(focus, dict) or len(json.dumps(focus)) > 600):
                raise CircuitRefError(400, 'INVALID_FOCUS', 'focus must be an object {kind, id}.')
            self._send_json(200, ASSISTANT.chat(session_id, ref, message, focus=focus))

        elif path == '/api/insights':
            # deterministic design insights (structure, structural timing/power/area, optimization candidates);
            # works without the LLM
            data = self._read_json()
            ref = _ref_from(data)
            self._send_json(200, SERVICE.insights(ref).public())
        else:
            self._send_error_json(404, 'NOT_FOUND', 'Not found.')


def configure_assistant(llm=None, probe=True):
    """Wire the analysis service + assistant. `llm` is injectable (tests pass a fake)."""
    global SERVICE, ASSISTANT
    if llm is None:
        llm = LLMClient()
    SERVICE = AnalysisService(llm, _baseline_predict)
    ASSISTANT = Assistant(llm, SERVICE)
    if probe and hasattr(llm, 'probe'):
        if llm.config.api_key:
            llm.reason = 'checking the model (startup probe in progress)'
            threading.Thread(target=llm.probe, name='llm-probe', daemon=True).start()
        else:
            llm.reason = 'OPENAI_API_KEY is not set in ML_VLSI/.env'
    return ASSISTANT


def make_server(host=HOST, port=PORT, llm=None, probe=True):
    if ASSISTANT is None or llm is not None:
        configure_assistant(llm, probe)
    http.server.ThreadingHTTPServer.allow_reuse_address = True
    server = http.server.ThreadingHTTPServer((host, port), RequestHandler)
    server.daemon_threads = True
    return server


if __name__ == '__main__':
    with make_server() as httpd:
        print("\n" + "="*60)
        print("  [+] GNN-RE Interactive Studio is RUNNING!")
        print(f"  [+] Open in your browser: http://{HOST}:{PORT}")
        print("="*60 + "\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("Server stopped.")
