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

def parse_verilog_netlist(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Strip comments
    content = re.sub(r'//.*', '', content)
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)

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
    gate_pattern = re.compile(r'(\w+)\s+([\w\\/]+)\s*\((.*?)\);', re.DOTALL)
    gates = []
    
    for match in gate_pattern.finditer(content):
        cell_type = match.group(1)
        inst_name = match.group(2).strip()
        port_map_str = match.group(3)
        
        if cell_type in ['module', 'input', 'output', 'wire', 'reg']:
            continue
            
        pin_connections = {}
        for pm in re.finditer(r'\.(\w+)\s*\(\s*([^)]+)\s*\)', port_map_str):
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

if __name__ == '__main__':
    test_path = 'GNN-RE/Netlist_to_graph/Circuits_datasets/Interconnected-Modules/Train_add_mul_combine_4_bit_Syn_65nm.v'
    if os.path.exists(test_path):
        parsed = parse_verilog_netlist(test_path)
        nodes, edges, feats, labels = build_circuit_graph(parsed)
        print(f"Parsed {parsed['module_name']}: {len(nodes)} nodes, {len(edges)} edges.")
        print(f"Features: {feats.shape}, Labels: {labels.shape}")
        print("First node:", nodes[0])
