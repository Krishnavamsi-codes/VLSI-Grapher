"""
cell_datasheet.py - Per-cell "datasheet" entries and an optional liberty (.lib) loader.

What is known about a standard cell, and where it comes from:
  * pins and pin directions      cell_library.json (built from the benchmark netlists)        -> fact
  * logic function               derived from the cell family name and pin names using the
                                 usual standard-cell naming convention (AOI21, NAND2B, ...)  -> naming convention
  * drive strength               the _X<n> suffix of the cell name (X0P5 = 0.5)             -> naming convention
  * area, leakage, pin cap,      only from a liberty file placed in ML_VLSI/libs/*.lib       -> library data
    max transition/capacitance   (none ships with this repository)

Nothing numeric is ever estimated: without a liberty file, area/leakage/capacitance are None.
"""

import glob
import os
import re

from netlist_graph_engine import load_cell_library

HERE = os.path.dirname(os.path.abspath(__file__))
LIB_DIR = os.path.join(HERE, 'libs')
_DRIVE_RE = re.compile(r'_X(\d+)(?:P(\d+))?([A-Z]*)_')
_FIXED = {
    'INV': 'Y = !A', 'BUF': 'Y = A', 'BUFH': 'Y = A (high-drive buffer)',
    'ADDF': 'S = A ^ B ^ CI; CO = majority(A, B, CI)  (full adder)',
    'ADDH': 'S = A ^ B; CO = A & B  (half adder)',
    'XOR2': 'Y = A ^ B', 'XOR3': 'Y = A ^ B ^ C', 'XNOR2': 'Y = !(A ^ B)', 'XNOR3': 'Y = !(A ^ B ^ C)',
    'MX2': 'Y = S0 ? B : A  (2:1 multiplexer)',
    'MXIT2': 'Y = !(S0 ? B : A)  (inverting 2:1 multiplexer)',
}
DESCRIPTION = {
    'INV': 'inverter', 'BUF': 'buffer', 'BUFH': 'high-drive buffer', 'ADDF': 'full adder', 'ADDH': 'half adder',
    'XOR': 'exclusive OR', 'XNOR': 'exclusive NOR', 'MX': 'multiplexer', 'NAND': 'NAND gate', 'NOR': 'NOR gate',
    'AND': 'AND gate', 'OR': 'OR gate', 'AOI': 'AND-OR-invert complex gate', 'OAI': 'OR-AND-invert complex gate',
    'AO': 'AND-OR complex gate', 'OA': 'OR-AND complex gate',
}


def family(cell):
    """ADDF_X1M_A9TH -> ADDF (cell function without drive strength / track suffix)."""
    return re.sub(r'_X\w+$', '', cell)


def drive_strength(cell):
    m = _DRIVE_RE.search(cell + '_')
    return float(m.group(1) + ('.' + m.group(2) if m.group(2) else '')) if m else None


def _lit(pin):
    return f'!{pin[:-1]}' if pin.endswith('N') and len(pin) > 1 else pin


def logic_function(fam, inputs):
    """Boolean function by naming convention, or None when it cannot be derived safely."""
    if fam in _FIXED:
        return _FIXED[fam]
    m = re.fullmatch(r'(AOI|OAI|AO|OA)\d+\w*', fam)
    if m:
        kind = m.group(1)
        groups = {}
        for p in inputs:
            groups.setdefault(p[0], []).append(_lit(p))
        inner, outer = (' & ', ' | ') if kind in ('AOI', 'AO') else (' | ', ' & ')
        expr = outer.join(f'({inner.join(g)})' if len(g) > 1 else g[0] for _, g in sorted(groups.items()))
        return f'Y = !({expr})' if kind.endswith('I') else f'Y = {expr}'
    m = re.fullmatch(r'(NAND|NOR|AND|OR)\d\w*', fam)
    if m:
        op = ' & ' if m.group(1) in ('NAND', 'AND') else ' | '
        expr = op.join(_lit(p) for p in inputs)
        return f'Y = !({expr})' if m.group(1) in ('NAND', 'NOR') else f'Y = {expr}'
    return None


def describe(fam):
    for k in sorted(DESCRIPTION, key=len, reverse=True):
        if fam.startswith(k):
            return DESCRIPTION[k]
    return 'standard cell'


# ---------------------------------------------------------------------------------------------------------------
# Liberty (.lib) - minimal reader: library units, and per cell: area, cell_leakage_power, pin direction/capacitance.
# ---------------------------------------------------------------------------------------------------------------

def _blocks(text, kind):
    """(name, body) of every `kind (name) { ... }` group, brace-matched."""
    out = []
    for m in re.finditer(r'\b' + kind + r'\s*\(\s*"?([^")\s]+)"?\s*\)\s*\{', text):
        depth, i = 1, m.end()
        while depth and i < len(text):
            depth += {'{': 1, '}': -1}.get(text[i], 0)
            i += 1
        out.append((m.group(1), text[m.end():i - 1]))
    return out


def _attr(body, name):
    m = re.search(r'(?<![\w])' + name + r'\s*:\s*"?([-\d.eE+]+)"?\s*;', body)
    return float(m.group(1)) if m else None


def parse_liberty(text):
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    lib_name = (re.search(r'\blibrary\s*\(\s*"?([^")\s]+)', text) or [None, None])[1]
    leak = re.search(r'leakage_power_unit\s*:\s*"?([\d.]+)\s*([munpf]?W)"?', text)
    cap = re.search(r'capacitive_load_unit\s*\(\s*([\d.]+)\s*,\s*([munpf]?f)\s*\)', text, re.I)
    units = {'area': 'library area unit (conventionally um^2)',
             'leakage_power': f'{leak.group(1)}{leak.group(2)}' if leak else 'unspecified',
             'capacitance': f'{cap.group(1)}{cap.group(2)}' if cap else 'unspecified'}
    cells = {}
    for name, body in _blocks(text, 'cell'):
        pins = {}
        for pname, pbody in _blocks(body, 'pin'):
            d = re.search(r'direction\s*:\s*(\w+)', pbody)
            pins[pname] = {'direction': d.group(1) if d else None, 'capacitance': _attr(pbody, 'capacitance'),
                           'max_capacitance': _attr(pbody, 'max_capacitance')}
        # strip pin groups so a pin-level attribute is not read as a cell attribute
        top = re.sub(r'\bpin\s*\([^)]*\)\s*\{(?:[^{}]|\{[^{}]*\})*\}', '', body)
        cells[name] = {'area': _attr(top, 'area'), 'leakage_power': _attr(top, 'cell_leakage_power'), 'pins': pins}
    return {'library': lib_name, 'units': units, 'cells': cells}


_LIB_CACHE = {}


def load_liberty(lib_dir=LIB_DIR):
    """Merged liberty data from lib_dir/*.lib (cached by file names + mtimes); None when there is none."""
    files = sorted(glob.glob(os.path.join(lib_dir, '*.lib')))
    if not files:
        return None
    key = tuple((f, os.path.getmtime(f)) for f in files)
    if key not in _LIB_CACHE:
        merged = {'library': [], 'units': None, 'cells': {}, 'files': [os.path.basename(f) for f in files]}
        for f in files:
            with open(f, encoding='utf-8', errors='ignore') as fh:
                lib = parse_liberty(fh.read())
            merged['library'].append(lib['library'])
            merged['units'] = merged['units'] or lib['units']
            merged['cells'].update(lib['cells'])
        _LIB_CACHE.clear()
        _LIB_CACHE[key] = merged
    return _LIB_CACHE[key]


def datasheet(cell, liberty=None):
    """Everything known about one cell type, each field labelled with its source."""
    spec = load_cell_library().get(cell)
    fam = family(cell)
    inputs = spec['inputs'] if spec else []
    lib = (liberty or {}).get('cells', {}).get(cell)
    return {
        'cell': cell, 'family': fam, 'description': describe(fam),
        'inputs': inputs, 'outputs': spec['outputs'] if spec else [],
        'pins_source': 'cell_library.json' if spec else 'not in cell_library.json (pins unknown)',
        'function': logic_function(fam, inputs) if spec or fam in _FIXED else None,
        'function_source': 'naming convention (not verified against library data)',
        'drive_strength': drive_strength(cell), 'drive_source': 'cell-name suffix (naming convention)',
        'area': lib['area'] if lib else None, 'leakage_power': lib['leakage_power'] if lib else None,
        'pin_capacitance': {p: v['capacitance'] for p, v in lib['pins'].items()} if lib else None,
        'library_data': bool(lib),
        'units': (liberty or {}).get('units') if lib else None,
    }
