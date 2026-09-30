"""Grounder.check_claims: connectivity / path / prediction statements that contradict the netlist are removed."""
import pytest

import circuit_checks as cc
from analysis_service import AnalysisService
from circuit_store import resolve_circuit
from fake_llm import FakeLLM
from grounding import Grounder

BS = chr(92)


@pytest.fixture(scope='module')
def circuit():
    svc = AnalysisService(FakeLLM(available=False), lambda m: [2] * m['num_gates'])
    ref = resolve_circuit('Validate_add_mul_8_bit_Syn_65nm.v')
    analysis = svc.analyze(ref)
    model, _ = svc.load(ref)
    return model, analysis


def _check(circuit, text):
    model, analysis = circuit
    g = Grounder(model, analysis['findings'])
    return g.check_claims(text, 'x', analysis['predictions'], cc.CLASS_NAMES), g.dropped


@pytest.mark.parametrize('sentence', [
    'G23 drives G5.', 'G24 pin CO drives G23 pin CI.', 'G5 reads G23.', 'G23 is fed by G24 and feeds G5 and G22.',
    'Result_add[12] is driven by G23 and read by G5.', 'G5 reads Result_add[12].', 'G23 drives Result_add[12].',
    'The path is G25 -> G24 -> G23 -> G5.', f'The net [N:{BS}adder_1/intadd_0/n4] is read by G22.',
    'Its instance-name label is Adder, but GraphSAINT predicts Multiplier.', 'This circuit adds and multiplies.',
    "G5 reads G23's S output and Gate G22 reads G23's CO output.",
])
def test_true_claims_survive(circuit, sentence):
    out, dropped = _check(circuit, sentence)
    assert out == sentence and dropped == []


@pytest.mark.parametrize('sentence', [
    'G23 reads G5.', 'Gate G23 reads the net Result_add[12] through its pin S.', 'Result_add[12] is driven by G5.',
    'G23 -> G22 -> G5.', f'{BS}adder_1/intadd_0/n4 is read by G5.', 'G0 -> G1',
])
def test_false_connectivity_claims_are_removed(circuit, sentence):
    out, dropped = _check(circuit, sentence)
    assert out == '' and dropped and dropped[0]['ref'].startswith('claim:')


def test_false_prediction_claim_is_removed(circuit):
    model, analysis = circuit
    wrong = next(n for i, n in enumerate(cc.CLASS_NAMES) if i != analysis['predictions'][23])
    out, dropped = _check(circuit, f'G23 is predicted to be part of the {wrong} class. G23 drives G5.')
    assert out == 'G23 drives G5.' and len(dropped) == 1


def test_only_false_sentences_and_orphaned_lead_ins_go(circuit):
    text = ('G23 drives G5. G23 reads G5.\nThe suggested connections are:\n- G0 -> G1\n- G1 -> G2\n'
            'These are hints only.')
    out, dropped = _check(circuit, text)
    assert out == 'G23 drives G5.\nThese are hints only.' and len(dropped) == 3
