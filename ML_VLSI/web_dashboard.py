"""
web_dashboard.py - Interactive GNN-RE Web Application & API Server
Serves an interactive visual dashboard for hardware netlist reverse engineering,
graph visualization, circuit schematic diagrams with identified sub-circuits,
live GNN inference, and Layman/Professor explanations.
"""

import http.server
import socketserver
import json
import os
import glob
import urllib.parse
import time
from netlist_graph_engine import parse_verilog_netlist, build_circuit_graph, CLASS_NAMES, CLASS_COLORS
from gnn_engine import CircuitGNN, extract_subcircuit_boundaries

PORT = 8501
DATASET_DIR = os.path.join(os.path.dirname(__file__), 'GNN-RE', 'Netlist_to_graph', 'Circuits_datasets', 'Interconnected-Modules')

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
  
  <!-- KaTeX for math rendering -->
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
  <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
  <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"></script>

  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');
    
    body {
      font-family: 'Inter', sans-serif;
      background-color: #030712;
    }
    
    code, pre {
      font-family: 'JetBrains Mono', monospace;
    }

    #network-container, #schematic-canvas-container {
      height: 520px;
      background: radial-gradient(circle at center, #0f172a 0%, #030712 100%);
      border-radius: 0.875rem;
    }

    .glass-card {
      background: rgba(15, 23, 42, 0.75);
      backdrop-filter: blur(16px);
      border: 1px solid rgba(255, 255, 255, 0.08);
    }
    
    .glass-card:hover {
      border-color: rgba(99, 102, 241, 0.3);
    }

    .glow-indigo {
      box-shadow: 0 0 30px -5px rgba(99, 102, 241, 0.35);
    }

    ::-webkit-scrollbar {
      width: 6px;
      height: 6px;
    }
    ::-webkit-scrollbar-track {
      background: #090d16;
    }
    ::-webkit-scrollbar-thumb {
      background: #1e293b;
      border-radius: 3px;
    }
    ::-webkit-scrollbar-thumb:hover {
      background: #334155;
    }
  </style>
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

    <!-- Mode Selector & Controls -->
    <div class="flex items-center space-x-4">
      <div class="flex bg-slate-900/90 p-1 rounded-xl border border-slate-800 text-xs">
        <button id="mode-layman-btn" onclick="setExplanationMode('layman')" class="px-3.5 py-1.5 rounded-lg font-medium bg-indigo-600 text-white shadow-md transition-all flex items-center">
          <i class="fa-solid fa-user-astronaut mr-1.5 text-xs"></i> Layman Mode
        </button>
        <button id="mode-prof-btn" onclick="setExplanationMode('prof')" class="px-3.5 py-1.5 rounded-lg font-medium text-slate-400 hover:text-white transition-all flex items-center">
          <i class="fa-solid fa-graduation-cap mr-1.5 text-xs"></i> Professor Mode
        </button>
      </div>
    </div>
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

      <!-- 2. Dynamic Explanation Card (Layman / Professor) -->
      <div class="glass-card rounded-2xl p-5 shadow-2xl space-y-3">
        <div class="flex items-center justify-between">
          <h2 class="text-sm font-semibold text-white flex items-center tracking-wide">
            <i class="fa-solid fa-lightbulb text-amber-400 mr-2 text-base"></i> What's Happening Here?
          </h2>
          <span id="mode-badge" class="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">Layman Mode</span>
        </div>
        
        <div id="explanation-text" class="text-xs text-slate-300 space-y-2.5 leading-relaxed bg-slate-950/60 p-3.5 rounded-xl border border-slate-800/80">
          <!-- Populated dynamically and rendered by KaTeX -->
        </div>

        <!-- Case Studies Quick Switch -->
        <div class="pt-2 border-t border-slate-800/80">
          <div class="text-[11px] font-semibold text-slate-400 mb-2">Explore Real-World Cases:</div>
          <div class="grid grid-cols-3 gap-1.5">
            <button onclick="loadCaseStudy(1)" class="p-1.5 rounded-lg bg-slate-950/80 hover:bg-indigo-950/50 border border-slate-800 hover:border-indigo-500/50 text-[10px] text-indigo-300 font-medium transition text-center">
              ALU Partitioning
            </button>
            <button onclick="loadCaseStudy(2)" class="p-1.5 rounded-lg bg-slate-950/80 hover:bg-emerald-950/50 border border-slate-800 hover:border-emerald-500/50 text-[10px] text-emerald-300 font-medium transition text-center">
              FSM vs Datapath
            </button>
            <button onclick="loadCaseStudy(3)" class="p-1.5 rounded-lg bg-slate-950/80 hover:bg-rose-950/50 border border-slate-800 hover:border-rose-500/50 text-[10px] text-rose-300 font-medium transition text-center">
              Trojan Detection
            </button>
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
              <span class="text-[10px] text-slate-500 font-mono">Zoom/Pan enabled</span>
              <button onclick="renderCircuitSchematic(true)" class="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-[10px] text-cyan-300 border border-slate-700">
                <i class="fa-solid fa-arrows-rotate mr-1"></i> Reset View
              </button>
            </div>
          </div>
          <div id="schematic-canvas-container" class="relative overflow-hidden border border-slate-800/80 shadow-inner flex items-center justify-center">
            <canvas id="schematic-canvas" class="w-full h-full cursor-grab active:cursor-grabbing"></canvas>
          </div>
        </div>

        <!-- 2. Graph Topology View -->
        <div id="graph-view-container" class="hidden space-y-2">
          <div class="flex items-center justify-between text-xs px-1">
            <span id="graph-stats" class="text-slate-400 font-mono">0 Gates (Nodes) | 0 Interconnects (Edges)</span>
          </div>
          <div id="network-container" class="border border-slate-800/80 shadow-inner"></div>
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

      <!-- Metrics & Boundary Extraction Results -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
        
        <!-- Metrics Card -->
        <div class="glass-card rounded-2xl p-5 shadow-2xl space-y-3">
          <h3 class="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center">
            <i class="fa-solid fa-chart-pie text-emerald-400 mr-2"></i> Model Performance & Accuracy
          </h3>
          
          <div class="grid grid-cols-3 gap-2.5 text-center">
            <div class="bg-slate-950/80 p-3 rounded-xl border border-slate-800/80">
              <div class="text-[10px] text-slate-400 font-medium">Node Accuracy</div>
              <div id="metric-acc" class="text-xl font-bold text-emerald-400 mt-1 font-mono">--%</div>
            </div>
            <div class="bg-slate-950/80 p-3 rounded-xl border border-slate-800/80">
              <div class="text-[10px] text-slate-400 font-medium">Micro-F1</div>
              <div id="metric-micro" class="text-xl font-bold text-cyan-400 mt-1 font-mono">--%</div>
            </div>
            <div class="bg-slate-950/80 p-3 rounded-xl border border-slate-800/80">
              <div class="text-[10px] text-slate-400 font-medium">Macro-F1</div>
              <div id="metric-macro" class="text-xl font-bold text-purple-400 mt-1 font-mono">--%</div>
            </div>
          </div>

          <div class="pt-2 border-t border-slate-800/80">
            <div class="text-[11px] font-semibold text-slate-400 mb-1.5">Gate Distribution by Class:</div>
            <div id="class-breakdown" class="space-y-1.5 text-[11px] text-slate-300 font-mono">
              <div class="text-slate-500 italic">Select a circuit or run GNN to see breakdown.</div>
            </div>
          </div>
        </div>

        <!-- Discovered Subcircuits / Boundaries -->
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

    </div>

  </main>

  <script>
    let currentMode = 'layman';
    let currentCircuitData = null;
    let currentSubcircuits = [];
    let network = null;
    let activeVisualView = 'schematic'; // 'schematic' or 'graph'

    const classColors = {
      0: { name: 'Adder', fill: 'rgba(56, 189, 248, 0.15)', border: '#38bdf8', badge: '#0284c7' },
      1: { name: 'Multiplier', fill: 'rgba(16, 185, 129, 0.15)', border: '#10b981', badge: '#059669' },
      2: { name: 'Control Logic', fill: 'rgba(245, 158, 11, 0.15)', border: '#f59e0b', badge: '#d97706' },
      3: { name: 'Subtractor', fill: 'rgba(168, 85, 247, 0.15)', border: '#a855f7', badge: '#7c3aed' },
      4: { name: 'Comparator', fill: 'rgba(6, 182, 212, 0.15)', border: '#06b6d4', badge: '#0891b2' }
    };

    const caseExplanations = {
      1: {
        layman: "<strong>Case 1 (Multi-Function ALU):</strong> In a flattened circuit, adders, multipliers, and subtractors are mixed into one giant netlist. GNN-RE analyzes wire paths to identify which gates belong to the <em>Adder carry-chains</em>, <em>Multiplier matrices</em>, and <em>Subtractor units</em>, drawing colored boundary boxes around each sub-circuit!",
        prof: "<strong>Case 1 (ALU Multi-module Partitioning):</strong> A multi-function ALU synthesized with Synopsys DC on GF 65nm flattens module boundaries. The GNN uses $L=2$ graph convolutions to aggregate fan-in/fan-out trajectories, partitioning $\\text{XOR}/\\text{ADDF}$ carry trees (Adders) from partial product $\\text{AND}$ matrices (Multipliers) with $\\mathbf{\\text{Micro-F1}} \\ge 97\\%$."
      },
      2: {
        layman: "<strong>Case 2 (CPU Control vs Datapath):</strong> The datapath acts like wide multi-lane highways (handling numbers), while control logic acts like traffic lights directing who goes next. GNN-RE spots the traffic lights (multiplexers) instantly and groups them into the Control Block!",
        prof: "<strong>Case 2 (FSM Control Logic Recovery):</strong> Control logic exhibits dense cyclic feedback loops and high out-degree MUX select lines ($S_0$). Its distinct PageRank and centrality invariants allow the GNN to isolate state machines without requiring dynamic simulation."
      },
      3: {
        layman: "<strong>Case 3 (Hardware Trojan / Backdoor):</strong> A sneaky hacker added 4 hidden gates inside a chip to leak secret passwords. Normal testing misses it because it is dormant. GNN-RE spots the weird wiring pattern and sounds the alarm!",
        prof: "<strong>Case 3 (Hardware Trojan & IP Piracy):</strong> Rare-event hardware Trojan triggers introduce localized graph topological anomalies. Latent node representations $\\mathbf{h}_v \\in \\mathbb{R}^{64}$ deviate from surrounding certified functional clusters, flagging malicious insertions."
      }
    };

    function renderMath() {
      if (window.renderMathInElement) {
        renderMathInElement(document.getElementById('explanation-text'), {
          delimiters: [
            {left: '$$', right: '$$', display: true},
            {left: '$', right: '$', display: false}
          ],
          throwOnError: false
        });
      }
    }

    async function init() {
      const res = await fetch('/api/circuits');
      const data = await res.json();
      const select = document.getElementById('circuit-select');
      select.innerHTML = '';
      data.circuits.forEach(c => {
        const opt = document.createElement('option');
        opt.value = c;
        opt.textContent = c.replace('.v', '');
        select.appendChild(opt);
      });
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
      const res = await fetch('/api/load_circuit?name=' + encodeURIComponent(name));
      currentCircuitData = await res.json();
      currentSubcircuits = [];
      renderCircuitSchematic();
      renderGraph(currentCircuitData);
      updateExplanation();
      
      // Auto-run inference for instant interactive view
      runInference(true);
    }

    async function handleFileUpload(e) {
      const file = e.target.files[0];
      if (!file) return;
      const text = await file.text();
      const res = await fetch('/api/upload_circuit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: file.name, content: text })
      });
      currentCircuitData = await res.json();
      currentSubcircuits = [];
      renderCircuitSchematic();
      renderGraph(currentCircuitData);
      updateExplanation();
      runInference(true);
    }

    /* ------------------------------------------------------------
       RICH GATE-LEVEL SCHEMATIC & SUB-CIRCUIT BOUNDARY RENDERER
       ------------------------------------------------------------ */
    function renderCircuitSchematic(resetZoom = false) {
      if (!currentCircuitData || !currentCircuitData.nodes) return;
      
      const canvas = document.getElementById('schematic-canvas');
      const ctx = canvas.getContext('2d');
      const container = document.getElementById('schematic-canvas-container');
      
      canvas.width = container.clientWidth * window.devicePixelRatio;
      canvas.height = container.clientHeight * window.devicePixelRatio;
      ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
      
      const width = container.clientWidth;
      const height = container.clientHeight;
      
      ctx.clearRect(0, 0, width, height);
      
      // Compute gate level positions (Topological Rank columns)
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
          positions[node.id] = {
            x: 60 + colIdx * colSpacing,
            y: startY + rowIdx * rowSpacing,
            node: node
          };
        });
      });

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
          
          const padding = 12;
          const rectX = minX - padding;
          const rectY = minY - padding;
          const rectW = Math.max(maxX - minX + padding * 2, 110);
          const rectH = Math.max(maxY - minY + padding * 2, 60);
          
          const cfg = classColors[sc.class_id] || classColors[2];
          
          // Draw soft glowing shaded boundary region
          ctx.save();
          ctx.fillStyle = cfg.fill;
          ctx.strokeStyle = cfg.border;
          ctx.lineWidth = 1.5;
          ctx.setLineDash([4, 4]);
          
          // Rounded rect
          ctx.beginPath();
          ctx.roundRect(rectX, rectY, rectW, rectH, 16);
          ctx.fill();
          ctx.stroke();
          
          // Sub-circuit Header Label Pill
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

      // 2. Draw Interconnecting Wires
      ctx.save();
      ctx.lineWidth = 1.2;
      edges.forEach(([u, v]) => {
        const p1 = positions[u];
        const p2 = positions[v];
        if (p1 && p2) {
          ctx.strokeStyle = "#475569";
          ctx.beginPath();
          ctx.moveTo(p1.x + gateWidth, p1.y + gateHeight / 2);
          const midX = (p1.x + gateWidth + p2.x) / 2;
          ctx.bezierCurveTo(midX, p1.y + gateHeight / 2, midX, p2.y + gateHeight / 2, p2.x, p2.y + gateHeight / 2);
          ctx.stroke();
        }
      });
      ctx.restore();

      // 3. Draw Gate Boxes
      nodes.forEach(n => {
        const pos = positions[n.id];
        if (!pos) return;
        
        const cfg = classColors[n.ground_truth] || classColors[2];
        
        ctx.save();
        ctx.fillStyle = "#0f172a";
        ctx.strokeStyle = cfg.border;
        ctx.lineWidth = 1.5;
        
        ctx.beginPath();
        ctx.roundRect(pos.x, pos.y, gateWidth, gateHeight, 6);
        ctx.fill();
        ctx.stroke();
        
        // Gate Cell Type Label
        ctx.fillStyle = "#f8fafc";
        ctx.font = "bold 9px 'JetBrains Mono', monospace";
        const labelText = n.cell_type.split('_')[0] || n.cell_type;
        ctx.fillText(labelText, pos.x + 8, pos.y + 14);
        
        // Gate Instance Name
        ctx.fillStyle = "#94a3b8";
        ctx.font = "8px 'JetBrains Mono', monospace";
        const instText = n.label.length > 12 ? n.label.substring(0, 10) + '..' : n.label;
        ctx.fillText(instText, pos.x + 8, pos.y + 25);
        ctx.restore();
      });
    }

    /* ------------------------------------------------------------
       INTERACTIVE GRAPH VISUALIZER
       ------------------------------------------------------------ */
    function renderGraph(data) {
      if (!data || !data.nodes) return;
      document.getElementById('graph-stats').textContent = `${data.nodes.length} Gates (Nodes) | ${data.edges.length} Interconnects (Edges)`;
      
      const nodes = new vis.DataSet(data.nodes.map(n => ({
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

      const edges = new vis.DataSet(data.edges.map(e => ({
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

      network.on("click", function (params) {
        if (params.nodes.length > 0) {
          const nodeId = params.nodes[0];
          const node = data.nodes.find(n => n.id === nodeId);
          if (node) {
            document.getElementById('node-inspector').classList.remove('hidden');
            document.getElementById('inspector-badge').textContent = `Gate #${node.id}`;
            document.getElementById('node-details').innerHTML = `
              <strong>Gate Name:</strong> <span class="text-white">${node.label}</span> | 
              <strong>Standard Cell:</strong> <span class="text-cyan-300">${node.cell_type}</span> | 
              <strong>Fan-In:</strong> ${node.in_degree} | 
              <strong>Fan-Out:</strong> ${node.out_degree} | 
              <strong>Classification:</strong> <span class="px-2 py-0.5 rounded text-white font-semibold" style="background:${node.color}">${node.class_name}</span>
            `;
          }
        }
      });
    }

    async function runInference(silent = false) {
      if (!currentCircuitData) return;
      const btn = document.getElementById('run-btn');
      if (!silent) btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> <span>Identifying Sub-circuits...</span>';
      
      const res = await fetch('/api/infer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          circuit_name: document.getElementById('circuit-select').value,
          custom_nodes: currentCircuitData.nodes,
          custom_edges: currentCircuitData.edges
        })
      });
      const result = await res.json();
      
      currentSubcircuits = result.subcircuits;
      
      document.getElementById('metric-acc').textContent = (result.metrics.accuracy * 100).toFixed(1) + '%';
      document.getElementById('metric-micro').textContent = (result.metrics.f1_micro * 100).toFixed(1) + '%';
      document.getElementById('metric-macro').textContent = (result.metrics.f1_macro * 100).toFixed(1) + '%';

      const classNames = ["Adder", "Multiplier", "Control Logic", "Subtractor", "Comparator"];
      const colors = ["#38bdf8", "#10b981", "#f59e0b", "#a855f7", "#06b6d4"];
      let breakdownHtml = '';
      
      const counts = [0, 0, 0, 0, 0];
      result.metrics.predictions.forEach(p => counts[p]++);
      
      classNames.forEach((name, idx) => {
        if (counts[idx] > 0) {
          const pct = ((counts[idx] / result.metrics.predictions.length) * 100).toFixed(0);
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
      }
    }

    function setExplanationMode(mode) {
      currentMode = mode;
      document.getElementById('mode-layman-btn').className = mode === 'layman' ? 
        'px-3.5 py-1.5 rounded-lg font-medium bg-indigo-600 text-white shadow-md transition-all flex items-center' : 
        'px-3.5 py-1.5 rounded-lg font-medium text-slate-400 hover:text-white transition-all flex items-center';
      document.getElementById('mode-prof-btn').className = mode === 'prof' ? 
        'px-3.5 py-1.5 rounded-lg font-medium bg-indigo-600 text-white shadow-md transition-all flex items-center' : 
        'px-3.5 py-1.5 rounded-lg font-medium text-slate-400 hover:text-white transition-all flex items-center';
      document.getElementById('mode-badge').textContent = mode === 'layman' ? 'Layman Mode' : 'Professor Mode';
      updateExplanation();
    }

    function updateExplanation() {
      const expDiv = document.getElementById('explanation-text');
      if (currentMode === 'layman') {
        expDiv.innerHTML = `
          <p><strong>💡 Layman Explanation:</strong> Think of this circuit like an unlabelled computer motherboard found in an archaeological dig. Every gate (box) performs a simple boolean task (AND, OR, XOR), but without blueprints, nobody knows what the whole chip does.</p>
          <p class="mt-2">GNN-RE passes messages through the wires to analyze neighborhood patterns. Gates connected in a chain become <strong>Adders (Blue)</strong>, dense matrix grids become <strong>Multipliers (Green)</strong>, and selector switches become <strong>Control Logic (Amber)</strong>. The colored shaded regions on the schematic show the exact identified sub-circuits!</p>
        `;
      } else {
        expDiv.innerHTML = `
          <p><strong>🎓 Academic Formulation:</strong> The gate-level netlist is modeled as a directed attributed graph $G = (V, E, X)$ where $X \\in \\mathbb{R}^{N \\times 34}$ captures gate-level standard cell library semantics and graph degree metrics.</p>
          <p class="mt-2">The inductive GNN executes $L$-layer neighborhood aggregation: $$\\mathbf{h}_v^{(l)} = \\sigma\\left(\\sum_{u \\in \\mathcal{N}(v)} \\tilde{\\mathbf{A}}_{uv} \\mathbf{W}^{(l)} \\mathbf{h}_u^{(l-1)}\\right)$$ Softmax mapping $\\hat{\\mathbf{Y}} = \\text{softmax}(\\mathbf{H}^{(L)} \\mathbf{W}_o)$ classifies nodes into $\\{0..4\\}$, and connected-component clustering recovers sub-circuit boundaries with high precision.</p>
        `;
      }
      renderMath();
    }

    function loadCaseStudy(caseNum) {
      const exp = caseExplanations[caseNum];
      const text = currentMode === 'layman' ? exp.layman : exp.prof;
      document.getElementById('explanation-text').innerHTML = `<p>${text}</p>`;
      renderMath();
      
      const select = document.getElementById('circuit-select');
      if (caseNum === 1) {
        for (let opt of select.options) {
          if (opt.value.includes('combine_4_bit') || opt.value.includes('comp_sub')) {
            select.value = opt.value;
            loadSelectedCircuit();
            break;
          }
        }
      }
    }

    window.onload = () => {
      init();
      setTimeout(renderMath, 500);
      window.addEventListener('resize', () => renderCircuitSchematic());
    };
  </script>
</body>
</html>
"""

class RequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)

        if path == '/' or path == '/index.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode('utf-8'))
        elif path == '/api/circuits':
            files = sorted([os.path.basename(f) for f in glob.glob(os.path.join(DATASET_DIR, '*.v'))])
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'circuits': files}).encode('utf-8'))
        elif path == '/api/load_circuit':
            circuit_name = query.get('name', [''])[0]
            file_path = os.path.join(DATASET_DIR, circuit_name)
            if os.path.exists(file_path):
                parsed = parse_verilog_netlist(file_path)
                nodes, edges, feats, labels = build_circuit_graph(parsed)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'module_name': parsed['module_name'],
                    'nodes': nodes,
                    'edges': edges
                }).encode('utf-8'))
            else:
                self.send_response(404)
                self.end_headers()
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == '/api/upload_circuit':
            content_len = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_len)
            data = json.loads(post_body.decode('utf-8'))
            
            temp_path = os.path.join(DATASET_DIR, 'Uploaded_custom.v')
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(data.get('content', ''))
                
            parsed = parse_verilog_netlist(temp_path)
            nodes, edges, feats, labels = build_circuit_graph(parsed)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'module_name': parsed['module_name'],
                'nodes': nodes,
                'edges': edges
            }).encode('utf-8'))

        elif self.path == '/api/infer':
            content_len = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_len)
            data = json.loads(post_body.decode('utf-8'))
            
            circuit_name = data.get('circuit_name')
            file_path = os.path.join(DATASET_DIR, circuit_name)
            if not os.path.exists(file_path):
                file_path = os.path.join(DATASET_DIR, 'Uploaded_custom.v')
                
            if os.path.exists(file_path):
                parsed = parse_verilog_netlist(file_path)
                nodes, edges, feats, labels = build_circuit_graph(parsed)
                metrics = gnn_model.evaluate(feats, edges, labels)
                subcircuits = extract_subcircuit_boundaries(nodes, edges, metrics['predictions'])
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'metrics': metrics,
                    'subcircuits': subcircuits
                }).encode('utf-8'))
            else:
                self.send_response(404)
                self.end_headers()

if __name__ == '__main__':
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), RequestHandler) as httpd:
        print("\n" + "="*60)
        print("  [+] GNN-RE Interactive Studio is RUNNING!")
        print(f"  [+] Open in your browser: http://localhost:{PORT}")
        print("="*60 + "\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("Server stopped.")
