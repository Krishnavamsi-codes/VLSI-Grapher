# GNN-RE Studio: project explanation

## One-minute explanation

GNN-RE Studio is a local web tool for understanding a **gate-level Verilog netlist**. It converts cells and their signal connections into a directed graph, checks the graph for electrical and structural problems, groups related gates into likely functional regions, and presents the evidence through a schematic, graph view, BOM, and grounded Qwen assistant. It does not claim that a prediction is a verified circuit fact: deterministic checks, structural inferences, and ML predictions are labelled separately.

## The problem it solves

Synthesis often turns a readable RTL design into thousands of standard-cell instances such as NAND, AOI, flip-flops, and inverters. The original hierarchy and intent can be hard to recover. This project helps an engineer answer:

- What cells, nets, inputs, and outputs are present?
- Which gates drive or read a signal?
- Are there floating nets, multiple drivers, missing pins, disconnected outputs, or suspicious wiring?
- Which regions resemble adders, multipliers, subtractors, comparators, or control logic?
- What is the cell bill of materials and which cells dominate the design?

## Supported input

The main input is a flat **gate-level** `.v` netlist. The parser understands named-pin cell instances, standard Verilog primitives, buses, escaped names, constants, simple `assign` aliases, and selected expressions.

Behavioral RTL is deliberately not reverse-engineered as if it were a gate netlist. Constructs such as `always`, `begin`, `if`, and `case` describe behaviour rather than physical cells. Uploading such a file now produces a clear message: synthesize it first, then upload the synthesized netlist. This prevents the old incorrect result where `begin` was reported as a gate.

## End-to-end flow

1. **Input and parsing** — `web_dashboard.py` accepts a benchmark or uploaded Verilog file. `netlist_graph_engine.py` tokenizes module declarations, ports, cells, pins, buses, aliases, and net connectivity.
2. **Graph construction** — every cell becomes a node. An edge runs from the cell driving a net to every cell reading that net. Each node receives a 34-feature vector based on cell type and graph degree.
3. **Baseline classification** — `gnn_engine.py` contains a small pure-Python GNN used for interactive baseline predictions. If precomputed GraphSAINT results exist for a benchmark, those are shown separately; uploads do not pretend to have GraphSAINT accuracy.
4. **Boundary recognition** — predicted labels and graph connectivity are used to group gates into candidate functional sub-circuits.
5. **Deterministic checks** — `circuit_checks.py` and `analysis_service.py` derive findings such as floating signals, multiple drivers, missing pins, output reachability, and structural anomalies.
6. **Design insights and BOM** — `design_insights.py` counts cell types, estimates structural timing by gate levels, identifies fan-out and area proxies, and generates the downloadable CSV BOM.
7. **Assistant** — `assistant.py` supplies grounded context and tools to Qwen. `grounding.py` rejects references the model cannot support. The assistant can explain evidence, but it cannot silently modify the circuit or invent a net/gate.
8. **Presentation** — the dashboard shows the active netlist, schematic, topology, metrics, findings, compact BOM, and assistant drawer.

## Important files

| File | Responsibility |
| --- | --- |
| `web_dashboard.py` | HTTP server, API routes, page markup, graph/schematic UI |
| `netlist_graph_engine.py` | Verilog parsing, net model, graph features |
| `gnn_engine.py` | Interactive baseline GNN and sub-circuit grouping |
| `gnn_re_inference.py` | Optional precomputed GraphSAINT lookup |
| `circuit_checks.py` | Deterministic connectivity and structural checks |
| `analysis_service.py` | Caches and combines parsing, checks, intent, insights |
| `design_insights.py` | BOM, timing/area/power structural insights |
| `assistant.py`, `llm_client.py`, `grounding.py` | Qwen integration, local OpenAI-compatible client, evidence grounding |
| `circuit_store.py` | Safe benchmark/upload resolution and dataset bootstrap |

## What the ML results mean

The five classes are Adder, Multiplier, Control Logic, Subtractor, and Comparator. A class label is an ML estimate, not proof. The dashboard labels baseline predictions, GraphSAINT results, and deterministic facts differently. For uploaded files, there is no ground-truth label, so accuracy is correctly shown as N/A.

## Qwen assistant design

Qwen runs locally through Ollama at `http://localhost:11434/v1`. It is used for natural-language explanation, not for deciding electrical truth. The GPU-backed local model is deliberately asked only when the user chats or clicks **Generate summary**; deterministic parsing, checks, BOM, and insights remain immediate. This prevents a large background report from delaying normal UI use.

## Training-data plan

The public mini-project repositories are useful **RTL source corpora**, not ready-made classifier data. To use them responsibly:

1. Obtain/verify permission and license for each source.
2. Split designs by project, not by individual gates, to avoid train/test leakage.
3. Synthesize every RTL design with the same tool, library, and constraints.
4. Generate gate-level graphs.
5. Create or verify node/region labels for the five target classes.
6. Keep a held-out test set of whole designs and report per-class precision, recall, and F1.

Without synthesis and validated labels, simply adding RTL files to training would make reported accuracy misleading.

## Honest limitations to state in a viva

- It is a reverse-engineering aid, not a sign-off or formal-verification tool.
- Structural timing is measured in gate levels, not nanoseconds.
- Power and area are proxies unless a characterized liberty library is supplied.
- Functional labels are confidence-ranked hypotheses; deterministic findings carry stronger evidence.
- Large/complex Verilog that is behavioural RTL must be synthesized before this tool can analyze it as a physical netlist.
