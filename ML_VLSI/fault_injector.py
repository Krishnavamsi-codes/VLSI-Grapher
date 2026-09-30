"""
fault_injector.py - Create broken copies of benchmark netlists for testing.

Each injector edits the netlist text of ONE instance (never adds/removes
instances, so gate ids and order stay identical to the original) and returns
the ground truth the checks are expected to recover:

    {'fault', 'text', 'gate_id', 'pin', 'net', 'expected_check', 'expected_edge', 'description'}

Fault types:
    drop_pin             delete one input pin connection
    float_net            reconnect one input pin to a new, undriven net
    cut_carry            delete the CI connection that receives a full-adder carry-out
    cut_partial_product  delete the pin that reads a multiplier partial-product gate
    second_driver        redirect a gate output onto a net that is already driven
    disconnect_po        rename the net driving a primary output
    miswire_bits         swap two operand bits between adjacent adder bit slices
                         (electrically clean: only the bit-slice check can see it)

CLI:
    python fault_injector.py --demo      regenerate demo_faults/ (+ manifest.json)
"""

import json
import os
import random
import re
import sys

from netlist_graph_engine import _GATE_RE, build_circuit_model
from circuit_store import DATASET_DIR, DEMO_DIR, DEMO_MANIFEST

FAULT_TYPES = ('drop_pin', 'float_net', 'cut_carry', 'cut_partial_product',
               'second_driver', 'disconnect_po', 'miswire_bits')


class NoEligibleSite(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# Text editing on one instance's port map
# ---------------------------------------------------------------------------

def _instance_spans(text):
    """[(start, end) of the port-map group] per gate id, same filtering as the parser."""
    spans = []
    # Offsets must refer to the raw text; the netlists only have // comments
    # before the module header, so blanking comments keeps offsets intact.
    blanked = re.sub(r'//.*', lambda m: ' ' * len(m.group(0)), text)
    blanked = re.sub(r'/\*.*?\*/', lambda m: re.sub(r'[^\n]', ' ', m.group(0)), blanked, flags=re.DOTALL)
    for m in _GATE_RE.finditer(blanked):
        if m.group(1) in ('module', 'input', 'output', 'wire', 'reg'):
            continue
        spans.append((m.start(3), m.end(3)))
    return spans


def _edit_pin(text, gate_id, pin, new_net=None):
    """Remove pin `pin` of gate `gate_id` (new_net=None) or reconnect it to new_net."""
    start, end = _instance_spans(text)[gate_id]
    ports = text[start:end]
    pat = re.compile(r'\.' + re.escape(pin) + r'\s*\(\s*[^)]*\)')
    m = pat.search(ports)
    if m is None:
        raise ValueError(f'gate {gate_id} has no pin {pin}')
    if new_net is None:
        # remove ".PIN(net)" and one adjacent comma
        before, after = ports[:m.start()], ports[m.end():]
        if re.match(r'\s*,', after):
            after = re.sub(r'^\s*,', '', after, count=1)
        else:
            before = re.sub(r',\s*$', '', before)
        ports = before + after
    else:
        ports = ports[:m.start()] + f'.{pin}({new_net} )' + ports[m.end():]
    return text[:start] + ports + text[end:]


# ---------------------------------------------------------------------------
# Site selection helpers
# ---------------------------------------------------------------------------

def _single_reader_links(model, pin_filter=None, driver_filter=None, reader_filter=None):
    """(driver_gate, driver_pin, net, reader_gate, reader_pin) where the net has exactly
    one driver (a gate) and exactly one reader (a gate)."""
    links = []
    for net, e in model['nets'].items():
        if len(e['drivers']) != 1 or len(e['readers']) != 1:
            continue
        d, r = e['drivers'][0], e['readers'][0]
        if 'gate_id' not in d or 'gate_id' not in r or d['gate_id'] == r['gate_id']:
            continue
        if pin_filter and not pin_filter(r['pin']):
            continue
        if driver_filter and not driver_filter(d['gate_id'], d['pin']):
            continue
        if reader_filter and not reader_filter(r['gate_id'], r['pin']):
            continue
        links.append((d['gate_id'], d['pin'], net, r['gate_id'], r['pin']))
    links.sort(key=lambda x: (x[3], x[4]))
    return links


def _pick(sites, seed):
    if not sites:
        raise NoEligibleSite('no eligible site for this fault in this netlist')
    return random.Random(seed).choice(sites)


def _inst(model, g):
    return model['gates'][g]['inst_name'].lstrip('\\').strip()


def _cell(model, g):
    return model['gates'][g]['cell_type']


# ---------------------------------------------------------------------------
# Fault injectors
# ---------------------------------------------------------------------------

def drop_pin(text, model, seed=0):
    d, dp, net, r, rp = _pick(_single_reader_links(model), seed)
    return {
        'fault': 'drop_pin', 'text': _edit_pin(text, r, rp),
        'gate_id': r, 'pin': rp, 'net': net, 'expected_check': 'missing_pin',
        'expected_edge': {'from_gate': d, 'from_pin': dp, 'to_gate': r, 'to_pin': rp},
        'description': f'Removed the connection of pin {rp} on {_inst(model, r)} ({_cell(model, r)}); '
                       f'it used to read {net} from {_inst(model, d)}.{dp}.',
    }


def float_net(text, model, seed=0):
    d, dp, net, r, rp = _pick(_single_reader_links(model), seed)
    new = f'n{100000 + r}'   # neutral name: must not hint at the fault
    return {
        'fault': 'float_net', 'text': _edit_pin(text, r, rp, new),
        'gate_id': r, 'pin': rp, 'net': new, 'expected_check': 'floating_net',
        'expected_edge': {'from_gate': d, 'from_pin': dp, 'to_gate': r, 'to_pin': rp},
        'description': f'Reconnected pin {rp} of {_inst(model, r)} ({_cell(model, r)}) from {net} to a new '
                       f'undriven net {new}; {_inst(model, d)}.{dp} now drives nothing.',
    }


def cut_carry(text, model, seed=0):
    is_add = lambda g: _cell(model, g).startswith(('ADDF', 'ADDH'))
    in_adder = lambda g: 'add' in model['hier_prefix'][g].lower()
    links = _single_reader_links(
        model, pin_filter=lambda p: p == 'CI',
        driver_filter=lambda g, p: p == 'CO' and is_add(g) and in_adder(g),
        reader_filter=lambda g, p: is_add(g) and in_adder(g))
    d, dp, net, r, rp = _pick(links, seed)
    return {
        'fault': 'cut_carry', 'text': _edit_pin(text, r, rp),
        'gate_id': r, 'pin': rp, 'net': net, 'expected_check': 'missing_pin',
        'expected_edge': {'from_gate': d, 'from_pin': 'CO', 'to_gate': r, 'to_pin': 'CI'},
        'description': f'Cut the carry link {_inst(model, d)}.CO -> {_inst(model, r)}.CI (net {net}).',
    }


def cut_partial_product(text, model, seed=0):
    bit_info = model['bit_info']

    def operand_bus(net):
        """Bus of an operand bit read directly or through one inverter/buffer."""
        if net in bit_info:
            return bit_info[net]['bus']
        drv = model['nets'][net]['drivers']
        if len(drv) == 1 and 'gate_id' in drv[0] and _cell(model, drv[0]['gate_id']).startswith(('INV', 'BUF')):
            src = [n for p, n in model['gate_pins'][drv[0]['gate_id']].items()
                   if model['gate_dirs'][drv[0]['gate_id']][p] == 'input']
            if len(src) == 1 and src[0] in bit_info:
                return bit_info[src[0]]['bus']
        return None

    def is_pp(g, _pin):
        if 'mul' not in model['hier_prefix'][g].lower():
            return False
        ins = [n for p, n in model['gate_pins'][g].items() if model['gate_dirs'][g][p] == 'input']
        buses = {operand_bus(n) for n in ins}
        return len(ins) == 2 and None not in buses and len(buses) == 2

    d, dp, net, r, rp = _pick(_single_reader_links(model, driver_filter=is_pp), seed)
    return {
        'fault': 'cut_partial_product', 'text': _edit_pin(text, r, rp),
        'gate_id': r, 'pin': rp, 'net': net, 'expected_check': 'missing_pin',
        'expected_edge': {'from_gate': d, 'from_pin': dp, 'to_gate': r, 'to_pin': rp},
        'description': f'Removed partial product {net} ({_inst(model, d)}, {_cell(model, d)}) from the '
                       f'summation input {_inst(model, r)}.{rp}.',
    }


def second_driver(text, model, seed=0):
    pis = set(model['primary_inputs'])
    pos = set(model['primary_outputs'])

    def first_level(g):
        return all(n in pis for p, n in model['gate_pins'][g].items() if model['gate_dirs'][g][p] == 'input')

    cands = []
    outs = {}
    for g in range(model['num_gates']):
        if not first_level(g):
            continue
        for p, n in model['gate_pins'][g].items():
            if model['gate_dirs'][g][p] == 'output' and n not in pos \
                    and any('gate_id' in r for r in model['nets'][n]['readers']):
                outs[g] = (p, n)
    gates = sorted(outs)
    for g in gates:
        for h in gates:
            if h != g and model['hier_prefix'][h] == model['hier_prefix'][g]:
                cands.append((g, h))
    g, h = _pick(cands, seed)
    gp, gnet = outs[g]
    _, hnet = outs[h]
    readers = [r for r in model['nets'][gnet]['readers'] if 'gate_id' in r]
    return {
        'fault': 'second_driver', 'text': _edit_pin(text, g, gp, hnet),
        'gate_id': g, 'pin': gp, 'net': hnet, 'expected_check': 'multi_driver',
        'expected_edge': {'from_gate': g, 'from_pin': gp, 'to_gate': readers[0]['gate_id'], 'to_pin': readers[0]['pin']},
        'description': f'Redirected output {gp} of {_inst(model, g)} from {gnet} onto {hnet}, which '
                       f'{_inst(model, h)} already drives; {gnet} is left floating.',
    }


def disconnect_po(text, model, seed=0):
    sites = []
    for po in model['primary_outputs']:
        e = model['nets'].get(po)
        if e and len(e['drivers']) == 1 and 'gate_id' in e['drivers'][0] \
                and not any('gate_id' in r for r in e['readers']):
            sites.append((po, e['drivers'][0]['gate_id'], e['drivers'][0]['pin']))
    po, g, p = _pick(sorted(sites), seed)
    new = f'n{200000 + g}'   # neutral name
    return {
        'fault': 'disconnect_po', 'text': _edit_pin(text, g, p, new),
        'gate_id': g, 'pin': p, 'net': po, 'expected_check': 'undriven_po',
        'expected_edge': {'from_gate': g, 'from_pin': p, 'to_po': po},
        'description': f'Renamed the net driven by {_inst(model, g)}.{p} from {po} to {new}, '
                       f'leaving primary output {po} undriven.',
    }


def miswire_bits(text, model, seed=0):
    """Swap operand bits of significance s and s+1 between two adder bit slices."""
    bit_info = model['bit_info']
    pis = set(model['primary_inputs'])
    readers = {}   # (block, bus, sig) -> [(gate, pin)]
    for g in range(model['num_gates']):
        block = model['hier_prefix'][g]
        if 'add' not in block.lower():
            continue
        for p, n in model['gate_pins'][g].items():
            if model['gate_dirs'][g][p] == 'input' and n in pis and n in bit_info:
                readers.setdefault((block, bit_info[n]['bus'], bit_info[n]['significance']), []).append((g, p))
    sites = []
    for (block, bus, sig), rs in sorted(readers.items()):
        nxt = readers.get((block, bus, sig + 1))
        if sig >= 1 and len(rs) == 1 and nxt and len(nxt) == 1:
            sites.append((rs[0], nxt[0], bus, sig))
    (g1, p1), (g2, p2), bus, s = _pick(sites, seed)
    lo, hi = model['gate_pins'][g1][p1], model['gate_pins'][g2][p2]
    text = _edit_pin(text, g1, p1, hi)
    text = _edit_pin(text, g2, p2, lo)
    return {
        'fault': 'miswire_bits', 'text': text,
        'gate_id': g1, 'pin': p1, 'net': hi, 'expected_check': 'bit_slice_anomaly',
        'expected_edge': {'from_net': lo, 'to_gate': g1, 'to_pin': p1},
        'partner': {'gate_id': g2, 'pin': p2},
        'description': f'Swapped operand bits {lo} and {hi}: {_inst(model, g1)}.{p1} now reads {hi} and '
                       f'{_inst(model, g2)}.{p2} now reads {lo}. The netlist stays electrically valid.',
    }


INJECTORS = {
    'drop_pin': drop_pin, 'float_net': float_net, 'cut_carry': cut_carry,
    'cut_partial_product': cut_partial_product, 'second_driver': second_driver,
    'disconnect_po': disconnect_po, 'miswire_bits': miswire_bits,
}


def inject(path, fault, seed=0):
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    model = build_circuit_model(text=text)
    return INJECTORS[fault](text, model, seed)


# ---------------------------------------------------------------------------
# Demo files
# ---------------------------------------------------------------------------

DEMOS = [
    ('cut_carry', 'Validate_add_mul_8_bit_Syn_65nm.v', 0),
    ('float_net', 'Train_add_mul_comp_sub_4_bit_Syn_65nm.v', 0),
    ('miswire_bits', 'Test_add_mul_16_bit_Syn_65nm.v', 0),
]


def write_demos():
    os.makedirs(DEMO_DIR, exist_ok=True)
    manifest = {}
    for fault, base, seed in DEMOS:
        res = inject(os.path.join(DATASET_DIR, base), fault, seed)
        name = f'Demo_{fault}__{base}'
        header = (f'// DEMO FAULT ({fault}) injected into {base} by fault_injector.py.\n'
                  f'// {res["description"]}\n')
        with open(os.path.join(DEMO_DIR, name), 'w', encoding='utf-8', newline='\n') as f:
            f.write(header + res['text'])
        manifest[name] = {'base': base, 'fault': fault, 'seed': seed, 'description': res['description'],
                          'expected_check': res['expected_check'], 'expected_edge': res['expected_edge']}
        print('wrote', name, '-', res['description'])
    with open(DEMO_MANIFEST, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=1)


if __name__ == '__main__':
    if '--demo' in sys.argv:
        write_demos()
    else:
        print(__doc__)
