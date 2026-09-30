# Requirements Document

## Introduction

This feature adds Phase 2 of the VLSI Grapher roadmap: an RTL-to-Netlist synthesis pipeline that lets users provide a Verilog or SystemVerilog RTL design, automatically synthesize it using Yosys, parse the resulting gate-level netlist, and visualize it in the existing VLSI Grapher web dashboard.

The pipeline is: **RTL (Verilog/SystemVerilog) → Yosys → Synthesized netlist → GenericNetlistParser → Graph (existing model) → Existing visualization**.

The feature integrates cleanly with the existing codebase:
- The `SynthesisService` produces a `SynthesisResult` whose graph data is consumed by the existing `build_circuit_graph()` and visualization layer without modification.
- The new API endpoint `POST /api/synthesize` follows the same JSON-over-HTTP pattern as `POST /api/infer` and `POST /api/upload_circuit`.
- The frontend extends the existing "Upload Custom .V" tab to support RTL upload, adding a top-module field and a progress indicator.

## Glossary

- **RTL_Input**: A user-supplied Verilog or SystemVerilog source file (.v / .sv) containing a Register Transfer Level design.
- **Synthesis_Service**: The Python module `synthesis_service.py` that manages Yosys invocation, temp-file lifecycle, and error handling. Accepts `RTL_Input` and returns `SynthesisResult`.
- **Synthesis_Result**: The structured output of `Synthesis_Service` containing the synthesized gate-level netlist text, metadata, and structured log.
- **Yosys**: The open-source RTL synthesis tool (https://yosyshq.net/yosys/) used as the synthesis backend. Must be installed separately.
- **Synthesis_Script**: The ordered sequence of Yosys passes executed for each synthesis job.
- **Generic_Netlist_Parser**: The new parser module `rtl_netlist_parser.py` that converts a Yosys-emitted gate-level Verilog netlist into the intermediate `ParsedNetlist` structure consumed by the existing `build_circuit_graph()`.
- **ParsedNetlist**: The dict `{module_name, inputs, outputs, gates}` already produced by the existing `parse_verilog_netlist()`. The `Generic_Netlist_Parser` produces the same structure.
- **Graph_Node**: An entry in the `nodes` list produced by `build_circuit_graph()`: `{id, label, cell_type, ground_truth, class_name, color, in_degree, out_degree}`.
- **Graph_Edge**: A `(src_id, dst_id)` integer tuple in the `edges` list produced by `build_circuit_graph()`.
- **Synthesis_Log**: A per-job structured record capturing: input filename, top module, Yosys version, job start time, job end time, duration (seconds), success/failure flag, cell count, net count, node count, edge count, and any error message.
- **Temp_Dir**: An isolated, process-scoped temporary directory created per synthesis job and deleted on job completion or error.
- **Top_Module**: The name of the root Verilog module to synthesize. Specified by the user; validated against the RTL source before invoking Yosys.
- **CLI_Tool**: The command-line script `synthesize_rtl.py` that exposes the `Synthesis_Service` for developer use.
- **Job_ID**: A UUID-v4 string assigned to each synthesis job, used to correlate log entries and SSE progress events.
- **SSE**: Server-Sent Events — an HTTP/1.1 streaming mechanism used to push synthesis progress updates to the browser.
- **FEATURE_MAP**: The existing 34-entry dictionary in `netlist_graph_engine.py` mapping cell-type tokens to feature-vector indices.
- **Primary_IO_Node**: A synthetic Graph_Node representing a primary input or output port of the synthesized design (not a standard-cell gate instance).

---

## Requirements

### Requirement 1: Synthesis Service Abstraction

**User Story:** As a developer, I want a clean `SynthesisService` class that wraps Yosys, so that the rest of the system interacts with a well-defined Python interface and is not coupled to Yosys internals.

#### Acceptance Criteria

1. THE `Synthesis_Service` SHALL accept an `RTL_Input` (file path string) and a `top_module` (string) and return a `Synthesis_Result`.
2. WHEN `Synthesis_Service` is constructed, THE `Synthesis_Service` SHALL accept an optional `yosys_path` parameter; IF `yosys_path` is not provided, THEN THE `Synthesis_Service` SHALL locate Yosys using the system `PATH`.
3. IF Yosys is not found on the system, THEN THE `Synthesis_Service` SHALL raise a `YosysNotFoundError` with a message that includes installation guidance.
4. THE `Synthesis_Service` SHALL create a `Temp_Dir` per synthesis job, write all intermediate files to that directory, and delete it upon job completion or error.
5. WHEN a synthesis job completes (success or failure), THE `Synthesis_Service` SHALL emit one `Synthesis_Log` entry to the Python standard logger at `INFO` level.
6. THE `Synthesis_Log` SHALL contain: `job_id`, `input_file`, `top_module`, `yosys_version`, `started_at` (ISO-8601), `ended_at` (ISO-8601), `duration_seconds` (float), `success` (bool), `cell_count` (int), `net_count` (int), `node_count` (int), `edge_count` (int), `error` (string or null).
7. WHEN a synthesis job exceeds 120 seconds, THE `Synthesis_Service` SHALL terminate the Yosys subprocess and raise a `SynthesisTimeoutError`.

---

### Requirement 2: Yosys Synthesis Script

**User Story:** As a developer, I want a reproducible, documented synthesis script so that every RTL design goes through the same optimization passes before netlist extraction.

#### Acceptance Criteria

1. THE `Synthesis_Service` SHALL execute the following Yosys passes in order for every synthesis job: `read_verilog`, `hierarchy`, `proc`, `flatten`, `opt`, `fsm`, `memory`, `techmap`, `opt`, `abc`, `clean`, `write_verilog`.
2. WHEN invoking `read_verilog`, THE `Synthesis_Service` SHALL pass the `-sv` flag so that SystemVerilog input is accepted.
3. WHEN invoking `hierarchy`, THE `Synthesis_Service` SHALL pass `-check` and `-top <top_module>` so that Yosys validates that the `Top_Module` exists and makes it the design root.
4. WHEN invoking `abc`, THE `Synthesis_Service` SHALL use the generic standard cell mapping (no technology library flag) to produce technology-independent gate-level logic.
5. WHEN invoking `write_verilog`, THE `Synthesis_Service` SHALL write the output netlist to a file in the `Temp_Dir` with the suffix `_synth.v`.
6. THE `Synthesis_Service` SHALL build the Yosys command as a list of strings and execute it via `subprocess.run` with `shell=False` to prevent shell injection.

---

### Requirement 3: Top-Module Validation

**User Story:** As a user, I want clear feedback if my specified top module does not exist in my RTL file, so that I do not have to read Yosys error output to understand the problem.

#### Acceptance Criteria

1. WHEN the user provides a `top_module` name, THE `Synthesis_Service` SHALL scan the RTL source text for a `module <top_module>` declaration before invoking Yosys.
2. IF the `top_module` is not found in the RTL source, THEN THE `Synthesis_Service` SHALL raise a `TopModuleNotFoundError` that includes the requested name and a list of all module names found in the file (up to 20).
3. IF the RTL source contains exactly one module and the user omits `top_module`, THEN THE `Synthesis_Service` SHALL infer the `top_module` from that single module declaration.
4. IF the RTL source contains more than one module and the user omits `top_module`, THEN THE `Synthesis_Service` SHALL raise a `TopModuleRequiredError` listing all found module names.

---

### Requirement 4: Generic Netlist Parser

**User Story:** As a developer, I want a generic parser for Yosys-emitted gate-level Verilog netlists, so that any synthesized design can be converted into the existing graph model without hardcoding cell type names.

#### Acceptance Criteria

1. THE `Generic_Netlist_Parser` SHALL parse a gate-level Verilog netlist and extract: all module declarations, all cell instances (with unique instance name, cell type, and named port connections), all net declarations (wire names), and all primary input/output port declarations.
2. THE `Generic_Netlist_Parser` SHALL assign each cell instance a unique integer `id` (0-indexed, sequential) that matches the `id` used in `Graph_Node`.
3. THE `Generic_Netlist_Parser` SHALL extract net connectivity and determine for each net: the driver cell (the instance whose output port drives the net) and the load cells (the instances whose input ports receive the net).
4. WHEN a net has no identified driver (e.g., a primary input net), THE `Generic_Netlist_Parser` SHALL create a synthetic `Primary_IO_Node` representing that primary input as the driver.
5. THE `Generic_Netlist_Parser` SHALL produce a `ParsedNetlist` dict with the same structure as the existing `parse_verilog_netlist()` output: `{module_name: str, inputs: list[str], outputs: list[str], gates: list[{cell_type, inst_name, pins, ground_truth}]}`.
6. WHEN parsing bus/vector signals (e.g., `wire [7:0] data`), THE `Generic_Netlist_Parser` SHALL preserve the bit-index relationship by treating each bit as a separate named net (e.g., `data[0]`, `data[1]`, …, `data[7]`).
7. IF a cell type token from the parsed netlist matches a key in `FEATURE_MAP`, THEN THE `Generic_Netlist_Parser` SHALL set the corresponding feature-vector entry to `1.0`; otherwise all gate-type feature entries SHALL remain `0.0`, preserving generality for unseen cell types.

---

### Requirement 5: Graph Model Mapping

**User Story:** As a developer, I want synthesized netlists mapped into the existing VLSI Grapher graph model, so that the visualization and GNN inference work without modification.

#### Acceptance Criteria

1. THE `Synthesis_Service` SHALL pass the `ParsedNetlist` produced by the `Generic_Netlist_Parser` directly to the existing `build_circuit_graph()` function to produce `nodes`, `edges`, `features`, and `labels`.
2. WHEN mapping a Yosys cell to a `Graph_Node`, THE `Synthesis_Service` SHALL use the Yosys cell type string as the `cell_type` field with no truncation or remapping.
3. WHEN mapping a net connection to a `Graph_Edge`, THE `Synthesis_Service` SHALL represent each driver→load relationship as one directed `(src_id, dst_id)` tuple, consistent with the existing edge representation.
4. THE `Synthesis_Service` SHALL preserve primary input ports as `Primary_IO_Node` entries in the `nodes` list with `cell_type` set to `"PI"` and `ground_truth` set to `2` (Control Logic, the existing default for unclassified nodes).
5. THE `Synthesis_Service` SHALL preserve primary output ports as `Primary_IO_Node` entries in the `nodes` list with `cell_type` set to `"PO"` and `ground_truth` set to `2`.
6. WHEN the synthesized design contains registers (Yosys `$dff`, `$sdff`, `$dffe` cells or mapped DFF standard cells), THE `Synthesis_Service` SHALL set the `is_register` metadata field to `true` for those nodes.
7. THE `Synthesis_Result` SHALL include a `metadata` list where each entry corresponds to one node (by index) and contains: `cell_type`, `net_names` (list of connected net names), `module` (parent module name), `fan_in` (int), `fan_out` (int), `is_primary_input` (bool), `is_primary_output` (bool), `is_register` (bool), `rtl_src_location` (string or null).

---

### Requirement 6: API Endpoint

**User Story:** As a frontend developer, I want a `POST /api/synthesize` endpoint so that the browser can trigger synthesis and receive the graph data needed by the existing visualization.

#### Acceptance Criteria

1. THE `web_dashboard.py` `RequestHandler` SHALL handle `POST /api/synthesize` requests with `Content-Type: application/json`.
2. WHEN a `POST /api/synthesize` request is received, THE `RequestHandler` SHALL accept a JSON body with fields: `filename` (string), `content` (string — RTL source text), and `top_module` (string, optional).
3. WHEN synthesis completes successfully, THE `RequestHandler` SHALL respond with HTTP 200 and a JSON body containing: `job_id` (string), `module_name` (string), `nodes` (list), `edges` (list), `metadata` (list), `log` (`Synthesis_Log` dict), and `synthesis_info` (dict with `cell_count`, `net_count`, `yosys_version`).
4. WHEN synthesis fails due to a `TopModuleNotFoundError`, THE `RequestHandler` SHALL respond with HTTP 422 and a JSON body containing `error_code: "TOP_MODULE_NOT_FOUND"`, `message` (string), and `available_modules` (list of strings).
5. WHEN synthesis fails due to a `SynthesisTimeoutError`, THE `RequestHandler` SHALL respond with HTTP 504 and a JSON body containing `error_code: "SYNTHESIS_TIMEOUT"` and `message` (string).
6. WHEN synthesis fails due to a Yosys subprocess non-zero exit code, THE `RequestHandler` SHALL respond with HTTP 422 and a JSON body containing `error_code: "SYNTHESIS_FAILED"`, `message` (string), and `yosys_stderr` (string, truncated to 2000 characters).
7. WHEN synthesis fails for any other reason, THE `RequestHandler` SHALL respond with HTTP 500 and a JSON body containing `error_code: "INTERNAL_ERROR"` and `message` (string).
8. THE `RequestHandler` SHALL validate that `filename` ends with `.v` or `.sv`; IF the extension is invalid, THEN THE `RequestHandler` SHALL respond with HTTP 400 and `error_code: "INVALID_FILE_TYPE"`.

---

### Requirement 7: Security and Path Safety

**User Story:** As a system operator, I want the synthesis pipeline to safely handle untrusted user input, so that the server cannot be compromised through file path manipulation or shell injection.

#### Acceptance Criteria

1. THE `Synthesis_Service` SHALL write all RTL input and intermediate files inside a UUID-named `Temp_Dir` within the system temporary directory (`tempfile.mkdtemp()`); it SHALL NOT write to any user-controlled path.
2. WHEN constructing the Yosys subprocess command, THE `Synthesis_Service` SHALL use a Python list of strings and `subprocess.run(..., shell=False)` to prevent shell injection from any user-supplied input.
3. THE `Synthesis_Service` SHALL strip the uploaded filename of any directory separators (e.g., `/`, `\`, `..`) before using it as a file name within the `Temp_Dir`.
4. WHEN the RTL source content is written to disk, THE `Synthesis_Service` SHALL limit the file size to 10 MB; IF the content exceeds this limit, THEN THE `Synthesis_Service` SHALL raise a `FileSizeLimitError` before writing.
5. THE `Synthesis_Service` SHALL NOT pass user-controlled strings directly as shell arguments; all parameters MUST be elements of the subprocess command list.

---

### Requirement 8: Frontend Integration

**User Story:** As a hardware designer, I want to upload RTL directly in the existing VLSI Grapher web UI, specify a top module, click synthesize, see live progress, and have the synthesized circuit appear in the existing visualization — without learning a new tool.

#### Acceptance Criteria

1. THE `web_dashboard.py` inline HTML SHALL add an "RTL Synthesis" tab alongside the existing "Benchmark Library" and "Upload Custom .V" tabs in the Circuit Input card.
2. WHEN the "RTL Synthesis" tab is active, THE frontend SHALL display a file upload area that accepts `.v` and `.sv` files and a text input for `top_module`.
3. WHEN the user uploads an RTL file and clicks a "Synthesize & Visualize" button, THE frontend SHALL send the RTL content and `top_module` to `POST /api/synthesize`.
4. WHILE synthesis is in progress, THE frontend SHALL display a progress indicator (spinner or animated status text) that prevents duplicate submissions.
5. WHEN synthesis completes successfully, THE frontend SHALL update `currentCircuitData` with the returned `nodes` and `edges` and re-render both the Circuit Schematic view and the Graph Topology view using the existing `renderCircuitSchematic()` and `renderGraph()` functions.
6. WHEN synthesis returns a `TOP_MODULE_NOT_FOUND` error, THE frontend SHALL display the error message and the list of available modules to the user without clearing the current visualization.
7. WHEN synthesis returns any other error, THE frontend SHALL display a human-readable error message derived from the `message` field.
8. WHEN synthesis succeeds, THE frontend SHALL update the circuit badge (currently showing "Synthesized 65nm") to display "RTL → Synthesized" to indicate the source of the circuit data.

---

### Requirement 9: Structured Logging

**User Story:** As a system operator, I want per-job structured logs so that I can audit synthesis activity and diagnose failures.

#### Acceptance Criteria

1. THE `Synthesis_Service` SHALL emit one JSON-structured log entry per synthesis job using Python's `logging` module at `INFO` level on success and `ERROR` level on failure.
2. THE `Synthesis_Log` SHALL contain all fields defined in Requirement 1.6.
3. WHEN Yosys reports its version string in stdout or stderr, THE `Synthesis_Service` SHALL extract and store it in `Synthesis_Log.yosys_version`; IF the version cannot be parsed, THEN THE `Synthesis_Service` SHALL store the string `"unknown"`.
4. WHEN a synthesis job fails, THE `Synthesis_Log` SHALL include the full Yosys stderr output (truncated to 4000 characters) in the `error` field.

---

### Requirement 10: Metadata for Future AI Phases

**User Story:** As a future AI developer, I want synthesis output to carry rich per-node metadata, so that upcoming LLM/RAG phases have structured context without re-parsing the netlist.

#### Acceptance Criteria

1. WHEN `Synthesis_Service` produces a `Synthesis_Result`, THE `Synthesis_Result` SHALL include a `metadata` list with one dict per node (indexed identically to `nodes`).
2. EACH metadata entry SHALL contain: `cell_type` (string), `net_names` (list of net name strings connected to this node), `module` (string — parent module name), `fan_in` (int), `fan_out` (int), `is_primary_input` (bool), `is_primary_output` (bool), `is_register` (bool), `rtl_src_location` (string or null — Yosys `src` attribute if present).
3. WHEN Yosys includes `(* src = "file:line" *)` attributes on cell instances, THE `Generic_Netlist_Parser` SHALL extract the source location string and place it in `rtl_src_location`.
4. THE `metadata` list SHALL be serializable to JSON using `json.dumps()` with no custom encoder.

---

### Requirement 11: Unit and Integration Tests

**User Story:** As a developer, I want automated tests for every layer of the pipeline so that regressions are caught before they reach production.

#### Acceptance Criteria

1. THE test suite SHALL include unit tests for: input validation (filename extension check, file-size limit, top-module absence), Yosys command construction (correct pass sequence, `shell=False`), `Generic_Netlist_Parser` (AND gate, DFF, MUX, multi-module), and graph conversion (node count, edge count, feature vector shape).
2. THE test suite SHALL include integration tests that invoke the full `Synthesis_Service` pipeline (requires Yosys installed) for: a single AND gate, a D flip-flop, a 2:1 MUX, a small sequential design (counter), a design with bus signals (8-bit adder), and a multi-module design.
3. WHEN running unit tests, THE tests SHALL NOT require Yosys to be installed; Yosys subprocess calls SHALL be mockable.
4. WHEN an integration test runs successfully, THE test SHALL assert that `len(nodes) > 0`, `len(edges) > 0`, and `features.shape[1] == 34`.
5. THE test suite SHALL be runnable with `python -m pytest tests/` from the workspace root.

---

### Requirement 12: CLI Developer Tool

**User Story:** As a developer, I want to synthesize RTL from the command line so that I can test the pipeline without running the web server.

#### Acceptance Criteria

1. THE `CLI_Tool` (`synthesize_rtl.py`) SHALL accept positional argument `rtl_file` (path to the RTL source) and optional argument `--top-module` (string).
2. WHEN invoked with a valid RTL file, THE `CLI_Tool` SHALL print a summary including: `Job ID`, `Module`, `Nodes`, `Edges`, `Duration`, `Yosys version`, and `Status: success`.
3. WHEN invoked with `--output <path>`, THE `CLI_Tool` SHALL write the `Synthesis_Result` as a JSON file to the specified path.
4. WHEN synthesis fails, THE `CLI_Tool` SHALL print the error message to stderr and exit with code 1.
5. THE `CLI_Tool` SHALL follow the existing project convention of a top-level `if __name__ == '__main__':` block using `argparse`.
