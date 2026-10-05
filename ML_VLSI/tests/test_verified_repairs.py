"""Proof-oriented repair selection and safe LLM phrasing."""

import circuit_checks as cc
import assistant
from netlist_graph_engine import build_circuit_model


def test_reference_and_functional_full_adder_fix_agree():
    wrong = build_circuit_model('demo_faults/Demo_05_Full_Adder__Wrong_Floating_Sum_Input.v')
    correct = build_circuit_model('demo_faults/Demo_04_Full_Adder__Correct.v')
    repair = cc.compute_fix(wrong, correct)
    assert repair['fix_net'] == 'cin'
    assert repair['confidence'] == 'verified'


def test_correct_full_adder_has_no_connection_errors():
    correct = build_circuit_model('demo_faults/Demo_04_Full_Adder__Correct.v')
    assert not [f for f in cc.run_checks(correct)['findings'] if f['severity'] == 'error']


def test_no_fix_is_reported_when_no_spec_is_available():
    model = build_circuit_model(text='''module t(a, y); input a; output y; wire ghost;
        AND2_X1M_A9TH U1 (.A(a), .B(ghost), .Y(y)); endmodule''')
    repair = cc.compute_fix(model)
    assert repair['confidence'] == 'no_fix_found'
    assert repair['fix_net'] is None


def test_bad_llm_fix_text_uses_verified_template():
    model = build_circuit_model('demo_faults/Demo_05_Full_Adder__Wrong_Floating_Sum_Input.v')
    repair = cc.compute_fix(model)
    reply = assistant.validate_fix_reply('Connect imaginary_net to U2.B.', repair, model)
    assert reply == assistant.verified_fix_template(repair)
    assert 'cin' in reply and 'imaginary_net' not in reply
