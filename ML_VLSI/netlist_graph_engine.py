"""
netlist_graph_engine.py - Pure Python Netlist-to-Graph Converter and Feature Extractor
Extracts gate-level netlists into graph topologies and node feature vectors matching GNN-RE specifications.
"""

import re
import os
import json
import numpy as np

# Standard feature map aligned with TCAD'21 GNN-RE
FEATURE_MAP = {
    "PI": 0, "PO": 1, "KEY": 2, "XOR": 3, "XNOR": 4, "AND": 5, "OR": 6,
    "NAND": 7, "NOR": 8, "INV": 9, "BUF": 10, "BUFH": 10, "BUFZ": 10,
    "ADDF": 11, "AOI": 12, "OAI": 13, "MXIT": 14, "AO1B": 15, "AOI2XB": 16,
    "AO": 17, "OA": 18, "OAI2XB": 19, "in_degree": 20, "out_degree": 21,
    "TIELO": 22, "TIEHI": 23, "RF2R": 24, "RF1R": 25, "PREICG": 26,
    "POSTICG": 27, "M": 28, "A": 29, "FRICG": 30, "MXT": 31, "MX": 32, "ADDH": 33
}

NUM_BASE_FEATURES = 34
NUM_CLASSES = 5
CLASS_NAMES = ["Adder", "Multiplier", "Control Logic", "Subtractor", "Comparator"]
CLASS_COLORS = {
    0: "#3B82F6",  # Adder (Blue)
    1: "#10B981",  # Multiplier (Green)
    2: "#F59E0B",  # Control Logic (Amber/Orange)
    3: "#8B5CF6",  # Subtractor (Purple)
    4: "#06B6D4"   # Comparator (Cyan)
}

# Pins treated as outputs when a cell is missing from cell_library.json
OUTPUT_PIN_NAMES = frozenset({'Y', 'S', 'CO', 'Q', 'QN', 'Z', 'ZN'})
_CELL_LIBRARY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cell_library.json')
_cell_library = None

_GATE_RE = re.compile(r'(\w+)\s+([\w\\/]+)\s*\((.*?)\);', re.DOTALL)
_PIN_RE = re.compile(r'\.(\w+)\s*\(\s*([^)]+)\s*\)')
_EMPTY_PIN_RE = re.compile(r'\.(\w+)\s*\(\s*\)')
_DECL_RE = re.compile(r'(?<![\w\\$])(input|output|inout|wire)\b\s*(?:\[\s*(\d+)\s*:\s*(\d+)\s*\])?\s*([^;]*);')
_ASSIGN_RE = re.compile(r'(?<![\w\\$])assign\s+([^=;]+?)\s*=\s*([^;]+);')
_CONST_RE = re.compile(r"^\d*'[bBhHdDoO][0-9a-fA-FxXzZ_]+$")
_SIMPLE_NET_RE = re.compile(r'^(\\\S+|[A-Za-z_][\w$]*(\[\d+\])?)$')
_IDENT_RE = re.compile(r'\\\S+|[A-Za-z_][\w$]*(?:\s*\[\d+\])?')


class NetlistParseError(ValueError):
    pass


def _strip_comments(content):
    content = re.sub(r'//.*', '', content)
    return re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)


def parse_verilog_netlist(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    return parse_verilog_text(content)


def parse_verilog_text(content):
    # Strip comments
    content = _strip_comments(content)

    # Extract module name
    module_match = re.search(r'module\s+(\w+)\s*\((.*?)\);', content, re.DOTALL)
    if not module_match:
        return None
    module_name = module_match.group(1)

    # Extract inputs and outputs
    inputs = []
    outputs = []
    for inp in re.finditer(r'input\s*(?:\[\d+:\d+\])?\s*([^;]+);', content):
        names = [x.strip() for x in inp.group(1).split(',')]
        inputs.extend(names)
    for out in re.finditer(r'output\s*(?:\[\d+:\d+\])?\s*([^;]+);', content):
        names = [x.strip() for x in out.group(1).split(',')]
        outputs.extend(names)

    # Extract gate instances
    gates = []

    for match in _GATE_RE.finditer(content):
        cell_type = match.group(1)
        inst_name = match.group(2).strip()
        port_map_str = match.group(3)
        
        if cell_type in ['module', 'input', 'output', 'wire', 'reg']:
            continue
            
        pin_connections = {}
        for pm in _PIN_RE.finditer(port_map_str):
            pin = pm.group(1).strip()
            net = pm.group(2).strip()
            pin_connections[pin] = net
            
        ground_truth = 2 # Default: Control logic
        inst_lower = inst_name.lower()
        if 'adder' in inst_lower or 'add_' in inst_lower:
            ground_truth = 0
        elif 'multiplier' in inst_lower or 'mul_' in inst_lower:
            ground_truth = 1
        elif 'subtractor' in inst_lower or 'sub_' in inst_lower:
            ground_truth = 3
        elif 'comparator' in inst_lower or 'comp_' in inst_lower:
            ground_truth = 4
            
        gates.append({
            'cell_type': cell_type,
            'inst_name': inst_name,
            'pins': pin_connections,
            'ground_truth': ground_truth
        })

    return {
        'module_name': module_name,
        'inputs': inputs,
        'outputs': outputs,
        'gates': gates
    }

def build_circuit_graph(parsed_netlist):
    gates = parsed_netlist['gates']
    num_nodes = len(gates)
    if num_nodes == 0:
        return [], [], np.zeros((0, NUM_BASE_FEATURES)), np.zeros(0)

    net_drivers = {}
    net_readers = {}
    output_pin_names = {'Y', 'S', 'CO', 'Q', 'QN', 'Z', 'ZN'}
    
    for idx, gate in enumerate(gates):
        for pin, net in gate['pins'].items():
            if pin.upper() in output_pin_names:
                net_drivers.setdefault(net, []).append(idx)
            else:
                net_readers.setdefault(net, []).append(idx)

    edges = set()
    in_degrees = np.zeros(num_nodes)
    out_degrees = np.zeros(num_nodes)

    for net, drivers in net_drivers.items():
        readers = net_readers.get(net, [])
        for d in drivers:
            for r in readers:
                if d != r:
                    edges.add((d, r))

    for src, dst in edges:
        out_degrees[src] += 1
        in_degrees[dst] += 1

    features = np.zeros((num_nodes, NUM_BASE_FEATURES), dtype=np.float32)
    labels = np.zeros(num_nodes, dtype=np.int64)

    for idx, gate in enumerate(gates):
        cell = gate['cell_type'].upper()
        labels[idx] = gate['ground_truth']

        for feat_key, feat_idx in FEATURE_MAP.items():
            if feat_key in cell:
                features[idx, feat_idx] = 1.0

        features[idx, FEATURE_MAP['in_degree']] = in_degrees[idx]
        features[idx, FEATURE_MAP['out_degree']] = out_degrees[idx]

    nodes = []
    for idx, gate in enumerate(gates):
        nodes.append({
            'id': idx,
            'label': gate['inst_name'].replace('\\', ''),
            'cell_type': gate['cell_type'],
            'ground_truth': int(labels[idx]),
            'class_name': CLASS_NAMES[labels[idx]],
            'color': CLASS_COLORS[labels[idx]],
            'in_degree': int(in_degrees[idx]),
            'out_degree': int(out_degrees[idx])
        })

    return nodes, list(edges), features, labels


# ---------------------------------------------------------------------------
# Net-level circuit model (used by circuit_checks / the assistant).
# Gate IDs and order are exactly those of parse_verilog_netlist/build_circuit_graph.
# ---------------------------------------------------------------------------

def load_cell_library():
    """cell type -> {'inputs': [...], 'outputs': [...]} from cell_library.json ({} if absent)."""
    global _cell_library
    if _cell_library is None:
        try:
            with open(_CELL_LIBRARY_PATH, 'r', encoding='utf-8') as f:
                _cell_library = json.load(f)['cells']
        except (OSError, ValueError, KeyError):
            _cell_library = {}
    return _cell_library


def pin_direction(cell_type, pin):
    """'output' or 'input'. Library first; unknown cells/pins fall back to OUTPUT_PIN_NAMES."""
    entry = load_cell_library().get(cell_type)
    if entry is not None:
        if pin in entry['outputs']:
            return 'output'
        if pin in entry['inputs']:
            return 'input'
    return 'output' if pin.upper() in OUTPUT_PIN_NAMES else 'input'


def _norm_net(net):
    net = net.strip()
    if net.startswith('\\'):
        return net
    return re.sub(r'\s+\[', '[', net)


def _decl_bits(msb, lsb, names):
    """Expand one declaration into (name, msb, lsb, [bit names LSB-first]) tuples."""
    out = []
    for name in (n.strip() for n in names.split(',')):
        if not name:
            continue
        if msb is None:
            out.append((name, None, None, [name]))
        else:
            step = 1 if lsb >= msb else -1
            # LSB first: significance 0 is the lsb index
            bits = [f'{name}[{i}]' for i in range(lsb, msb - step, -step)]
            out.append((name, msb, lsb, bits))
    return out


class _UnionFind:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        root = x
        while self.parent.get(root, root) != root:
            root = self.parent[root]
        while self.parent.get(x, x) != root:
            self.parent[x], x = root, self.parent[x]
        return root

    def union_into(self, x, root_target):
        rx, rt = self.find(x), self.find(root_target)
        if rx != rt:
            self.parent[rx] = rt


def build_circuit_model(path=None, text=None):
    """
    Parse a flat gate-level netlist into a net-level model.

    Returns a dict containing the legacy build_circuit_graph() outputs
    ('nodes', 'edges', 'features', 'labels') plus:
        gates, gate_pins (canonical nets), gate_dirs, hier_prefix,
        primary_inputs, primary_outputs (bit-level), buses, bit_info,
        nets {net: {drivers, readers, aliases}}, missing_pins,
        unknown_cells, assigns, parse_warnings.
    Raises NetlistParseError if no module declaration is found.
    """
    if text is None:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
    content = _strip_comments(text)
    parsed = parse_verilog_text(text)
    if parsed is None:
        raise NetlistParseError('No "module <name> ( ... );" declaration found.')
    warnings = []
    if len(re.findall(r'(?<![\w\\$])module\s+\w+', content)) > 1:
        warnings.append('Multiple modules found; the file is modeled as one flat netlist.')

    nodes, edges, features, labels = build_circuit_graph(parsed)
    gates = parsed['gates']
    library = load_cell_library()

    # --- Port / wire declarations (bit-expanded) ---------------------------
    buses, bit_info = {}, {}
    primary_inputs, primary_outputs = [], []
    for m in _DECL_RE.finditer(content):
        kind = m.group(1)
        msb = int(m.group(2)) if m.group(2) is not None else None
        lsb = int(m.group(3)) if m.group(3) is not None else None
        for name, b_msb, b_lsb, bits in _decl_bits(msb, lsb, m.group(4)):
            if b_msb is not None:
                buses[name] = {'kind': kind, 'msb': b_msb, 'lsb': b_lsb,
                               'width': len(bits), 'bits': bits}
                for sig, b in enumerate(bits):
                    bit_info[b] = {'bus': name, 'significance': sig}
            if kind in ('input', 'inout'):
                primary_inputs.extend(bits)
            if kind in ('output', 'inout'):
                primary_outputs.extend(bits)

    # --- assign statements: simple ones are aliases -------------------------
    uf = _UnionFind()
    assigns = []
    complex_assigns = []
    for m in _ASSIGN_RE.finditer(content):
        lhs, rhs = _norm_net(m.group(1)), _norm_net(m.group(2))
        if _SIMPLE_NET_RE.match(lhs) and (_SIMPLE_NET_RE.match(rhs) or _CONST_RE.match(rhs)):
            uf.union_into(lhs, rhs)
            assigns.append({'lhs': lhs, 'rhs': rhs, 'kind': 'const' if _CONST_RE.match(rhs) else 'alias'})
        else:
            complex_assigns.append((lhs, rhs))
            assigns.append({'lhs': lhs, 'rhs': rhs, 'kind': 'expression'})
            warnings.append(f'assign {lhs} = {rhs[:60]}: expression not modeled at gate level; '
                            f'{lhs} treated as driven, its operands as read.')

    nets = {}

    def net_entry(name):
        canon = uf.find(name)
        entry = nets.get(canon)
        if entry is None:
            entry = nets[canon] = {'drivers': [], 'readers': [], 'aliases': []}
            if _CONST_RE.match(canon):
                entry['drivers'].append({'const': canon})
        if name != canon and name not in entry['aliases']:
            entry['aliases'].append(name)
        return canon, entry

    for b in primary_inputs:
        net_entry(b)[1]['drivers'].append({'pi': b})

    # --- Gate pins ---------------------------------------------------------
    gate_pins, gate_dirs, hier_prefix, missing_pins = [], [], [], []
    unknown_cells = set()
    gate_matches = [m for m in _GATE_RE.finditer(content)
                    if m.group(1) not in ('module', 'input', 'output', 'wire', 'reg')]
    for gid, gate in enumerate(gates):
        cell = gate['cell_type']
        pins, dirs = {}, {}
        for pin, raw_net in gate['pins'].items():
            direction = pin_direction(cell, pin)
            canon, entry = net_entry(_norm_net(raw_net))
            pins[pin], dirs[pin] = canon, direction
            if direction == 'output':
                entry['drivers'].append({'gate_id': gid, 'pin': pin})
            else:
                entry['readers'].append({'gate_id': gid, 'pin': pin})
        gate_pins.append(pins)
        gate_dirs.append(dirs)

        inst = gate['inst_name'].lstrip('\\').strip()
        hier_prefix.append(inst.rsplit('/', 1)[0] if '/' in inst else '')

        explicit_empty = {pm.group(1) for pm in _EMPTY_PIN_RE.finditer(gate_matches[gid].group(3))}
        spec = library.get(cell)
        if spec is None:
            unknown_cells.add(cell)
            expected = set()
        else:
            expected = set(spec['inputs']) | set(spec['outputs'])
        for pin in sorted((expected - set(pins)) | (explicit_empty - set(pins))):
            missing_pins.append({'gate_id': gid, 'pin': pin,
                                 'direction': pin_direction(cell, pin),
                                 'explicit_empty': pin in explicit_empty})

    for b in primary_outputs:
        net_entry(b)[1]['readers'].append({'po': b})

    for lhs, rhs in complex_assigns:
        net_entry(lhs)[1]['drivers'].append({'assign': rhs[:80]})
        for ident in _IDENT_RE.findall(rhs):
            ident = _norm_net(ident)
            if not _CONST_RE.match(ident):
                net_entry(ident)[1]['readers'].append({'assign': lhs})

    return {
        'module_name': parsed['module_name'],
        'parsed': parsed,
        'nodes': nodes, 'edges': edges, 'features': features, 'labels': labels,
        'gates': gates,
        'num_gates': len(gates),
        'gate_pins': gate_pins,
        'gate_dirs': gate_dirs,
        'hier_prefix': hier_prefix,
        'primary_inputs': primary_inputs,
        'primary_outputs': primary_outputs,
        'buses': buses,
        'bit_info': bit_info,
        'nets': nets,
        'missing_pins': missing_pins,
        'unknown_cells': sorted(unknown_cells),
        'assigns': assigns,
        'parse_warnings': warnings,
    }

if __name__ == '__main__':
    test_path = 'GNN-RE/Netlist_to_graph/Circuits_datasets/Interconnected-Modules/Train_add_mul_combine_4_bit_Syn_65nm.v'
    if os.path.exists(test_path):
        parsed = parse_verilog_netlist(test_path)
        nodes, edges, feats, labels = build_circuit_graph(parsed)
        print(f"Parsed {parsed['module_name']}: {len(nodes)} nodes, {len(edges)} edges.")
        print(f"Features: {feats.shape}, Labels: {labels.shape}")
        print("First node:", nodes[0])
