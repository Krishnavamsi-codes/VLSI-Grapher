"""build_circuit_model: buses, PI/PO, assign aliases, constants, missing pins, fallbacks."""
import pytest

from netlist_graph_engine import NetlistParseError, build_circuit_model, parse_verilog_text, pin_direction

NETLIST = r"""
// synthetic test netlist
module t ( a, b, c, y, z, k );
  input [3:0] a;
  input b;
  input [0:1] c;
  output [1:0] y;
  output z, k;
  wire n1, n2, \blk/n3 ;
  assign z = n2;
  assign y[1] = 1'b0;
  NAND2_X1M_A9TH U1 ( .A(a[0]), .B(b), .Y(n1) );
  INV_X1M_A9TH U2 ( .A(n1), .Y(n2) );
  AND2_X1M_A9TH \blk/U3  ( .A(a[3]), .B(), .Y(y[0]) );
  FOO_CELL U4 ( .A(c[1]), .Y(\blk/n3 ) );
  INV_X1M_A9TH U5 ( .A(\blk/n3 ), .Y(k) );
endmodule
"""


@pytest.fixture(scope='module')
def model():
    return build_circuit_model(text=NETLIST)


def test_gate_order_and_ids(model):
    assert [g['inst_name'].strip() for g in model['gates']] == ['U1', 'U2', '\\blk/U3', 'U4', 'U5']
    assert model['hier_prefix'] == ['', '', 'blk', '', '']


def test_bus_expansion_and_significance(model):
    assert model['buses']['a']['bits'] == ['a[0]', 'a[1]', 'a[2]', 'a[3]']      # [3:0]: a[0] is LSB
    assert model['buses']['c']['bits'] == ['c[1]', 'c[0]']                      # [0:1]: c[1] is LSB
    assert model['bit_info']['a[3]'] == {'bus': 'a', 'significance': 3}
    assert model['bit_info']['c[0]'] == {'bus': 'c', 'significance': 1}
    assert set(model['primary_inputs']) == {'a[0]', 'a[1]', 'a[2]', 'a[3]', 'b', 'c[0]', 'c[1]'}
    assert set(model['primary_outputs']) == {'y[0]', 'y[1]', 'z', 'k'}


def test_assign_alias_connects_po(model):
    n2 = model['nets']['n2']
    assert {'po': 'z'} in n2['readers']
    assert 'z' in n2['aliases']
    assert {'gate_id': 1, 'pin': 'Y'} in n2['drivers']


def test_assign_constant(model):
    const = model['nets']["1'b0"]
    assert {'const': "1'b0"} in const['drivers']
    assert {'po': 'y[1]'} in const['readers']


def test_escaped_names_and_net_table(model):
    n3 = model['nets']['\\blk/n3']
    assert n3['drivers'] == [{'gate_id': 3, 'pin': 'Y'}]
    assert n3['readers'] == [{'gate_id': 4, 'pin': 'A'}]


def test_missing_and_empty_pins(model):
    assert {'gate_id': 2, 'pin': 'B', 'direction': 'input', 'explicit_empty': True} in model['missing_pins']
    assert len(model['missing_pins']) == 1


def test_unknown_cell_fallback(model):
    assert model['unknown_cells'] == ['FOO_CELL']
    assert model['gate_dirs'][3] == {'A': 'input', 'Y': 'output'}
    assert pin_direction('FOO_CELL', 'CO') == 'output'
    assert pin_direction('ADDF_X1M_A9TH', 'S') == 'output'
    assert pin_direction('ADDF_X1M_A9TH', 'CI') == 'input'


def test_parse_error_without_module():
    with pytest.raises(NetlistParseError):
        build_circuit_model(text='NAND2_X1M_A9TH U1 ( .A(a), .B(b), .Y(y) );')


def test_behavioral_begin_is_not_mistaken_for_a_gate():
    rtl = '''module mux(input a, b, sel, output reg y);
      always @(*) begin
        if (sel) y = a;
        else y = b;
      end
    endmodule'''
    assert parse_verilog_text(rtl)['gates'] == []


def test_expression_assign_is_flagged_not_dropped():
    m = build_circuit_model(text='module t (a, b, y); input a, b; output y; assign y = a & b; endmodule')
    assert any('expression not modeled' in w for w in m['parse_warnings'])
    assert m['nets']['y']['drivers'] == [{'assign': 'a & b'}]
    assert {'assign': 'y'} in m['nets']['a']['readers']
