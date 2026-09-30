"""
analysis_service.py - Orchestrates one circuit analysis and caches everything.

    analyze(ref) -> {'intent', 'findings', 'stats', 'cached', 'llm_available'}

Pipeline: build_circuit_model -> predictions (GraphSAINT CSV or baseline GCN)
-> run_checks -> collect_evidence -> intent (LLM, or deterministic fallback)
-> run_intent_checks (templates) -> merged findings.

Caches (all thread-safe LRU) are keyed by (circuit key, file sha256[, model]).
"""

import threading
from collections import OrderedDict

import circuit_checks as cc
import gnn_re_inference
import intent_analyzer as ia
from circuit_store import file_sha256
from llm_client import LLMError
from netlist_graph_engine import build_circuit_model


class LRU:
    def __init__(self, size):
        self.size = size
        self._d = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            if key in self._d:
                self._d.move_to_end(key)
                return self._d[key]
            return None

    def put(self, key, value):
        with self._lock:
            self._d[key] = value
            self._d.move_to_end(key)
            while len(self._d) > self.size:
                self._d.popitem(last=False)

    def pop(self, key):
        with self._lock:
            self._d.pop(key, None)


def honesty_notes(ref):
    notes = ['Functional labels (ground truth) come from instance-name heuristics, not from verified design data.']
    split = (ref.csv_key or '').split('_')[0]
    if ref.kind == 'upload':
        notes.append('This is an uploaded netlist: there is no GraphSAINT prediction; model-based hints use a '
                     'weak baseline GCN.')
    elif ref.kind == 'demo':
        notes.append('GraphSAINT predictions come from the original benchmark netlist; this netlist may differ from it.')
    if split == 'Train':
        notes.append('GraphSAINT metrics for this circuit are training-set results (the model saw it during training).')
    elif split == 'Validate':
        notes.append('GraphSAINT metrics for this circuit are validation-set results.')
    elif split == 'Test':
        notes.append('GraphSAINT metrics for this circuit are held-out test-set results.')
    return notes


class AnalysisService:
    def __init__(self, llm, baseline_predict):
        """baseline_predict(model) -> list of class ids (weak baseline GCN)."""
        self.llm = llm
        self.baseline_predict = baseline_predict
        self._models = LRU(16)
        self._analyses = LRU(32)
        self._key_locks = {}
        self._key_locks_lock = threading.Lock()

    def _lock_for(self, key):
        with self._key_locks_lock:
            return self._key_locks.setdefault(key, threading.Lock())

    # ------------------------------------------------------------------
    def load(self, ref):
        sha = file_sha256(ref.path)
        key = (ref.key, sha)
        model = self._models.get(key)
        if model is None:
            model = build_circuit_model(ref.path)
            self._models.put(key, model)
        return model, sha

    def predictions(self, ref, model):
        if ref.csv_key and ref.csv_key in gnn_re_inference.CIRCUIT_LOOKUP:
            entry = gnn_re_inference.CIRCUIT_LOOKUP[ref.csv_key]
            preds = entry['pred_class']
            if len(preds) == model['num_gates']:
                return list(preds), entry['probabilities'], 'graphsaint'
        return list(self.baseline_predict(model)), None, 'baseline'

    def llm_model_tag(self):
        return self.llm.model if self.llm is not None and self.llm.available else 'deterministic'

    # ------------------------------------------------------------------
    def analyze(self, ref, regenerate=False):
        model, sha = self.load(ref)
        key = (ref.key, sha, self.llm_model_tag())
        with self._lock_for(key):
            if not regenerate:
                hit = self._analyses.get(key)
                if hit is not None:
                    return dict(hit, cached=True)
            result = self._compute(ref, model, sha)
            self._analyses.put(key, result)
            return dict(result, cached=False)

    def _compute(self, ref, model, sha):
        preds, probs, source = self.predictions(ref, model)
        base = cc.run_checks(model, preds, probs, source)
        notes = honesty_notes(ref)
        evidence = ia.collect_evidence(model, base, preds, source, 'upload' if ref.kind == 'upload' else 'benchmark',
                                       notes)
        fallback = ia.deterministic_intent(evidence)
        intent = fallback
        if self.llm is not None and self.llm.available:
            try:
                intent = ia.llm_intent(self.llm, evidence, model, fallback)
            except LLMError as err:
                intent = dict(fallback, llm_error=err.message)
        intent_findings, template_results = cc.run_intent_checks(model, intent['expected_connections'],
                                                                 base['findings'])
        findings = base['findings'] + intent_findings
        for f in findings:
            f['certainty'] = cc.certainty(f)
        stats = dict(base['stats'])
        stats['errors'] = sum(f['severity'] == 'error' for f in findings)
        stats['warnings'] = sum(f['severity'] == 'warning' for f in findings)
        stats['infos'] = sum(f['severity'] == 'info' for f in findings)
        by = dict(stats['by_check'])
        for f in intent_findings:
            by[f['check']] = by.get(f['check'], 0) + 1
        stats['by_check'] = by
        stats['prediction_source'] = source
        stats['template_results'] = template_results
        intent = dict(intent, template_results=template_results)
        return {
            'intent': intent,
            'findings': findings,
            'stats': stats,
            'llm_available': bool(self.llm is not None and self.llm.available),
            'honesty_notes': notes,
            'evidence': evidence,
            'sha256': sha,
            'module_name': model['module_name'],
            'predictions': preds,
            'prediction_source': source,
        }
