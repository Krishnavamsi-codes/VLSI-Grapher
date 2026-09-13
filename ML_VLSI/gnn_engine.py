"""
gnn_engine.py - High-Performance Sparse Graph Neural Network for Circuit Reverse Engineering
Uses scipy.sparse for sub-millisecond message passing and sub-circuit boundary recognition.
"""

import numpy as np
import scipy.sparse as sp
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix

class CircuitGNN:
    """
    Ultra-Fast Sparse Graph Neural Network for Circuit Reverse Engineering (GNN-RE).
    """
    def __init__(self, in_dim=34, hidden_dim=64, num_classes=5, depth=2, lr=0.02):
        self.in_dim = in_dim
        self.hidden_dim = hidden_dim
        self.num_classes = num_classes
        self.depth = depth
        self.lr = lr
        
        np.random.seed(42)
        self.weights = []
        dims = [in_dim] + [hidden_dim] * (depth - 1) + [num_classes]
        for i in range(len(dims) - 1):
            limit = np.sqrt(6.0 / (dims[i] + dims[i+1]))
            W = np.random.uniform(-limit, limit, (dims[i], dims[i+1])).astype(np.float32)
            b = np.zeros(dims[i+1], dtype=np.float32)
            self.weights.append([W, b])

    def _normalize_adj_sparse(self, num_nodes, edges):
        """
        Fast sparse symmetric normalization with self-loops: D^(-1/2) * (A + I) * D^(-1/2)
        """
        if num_nodes == 0:
            return sp.csr_matrix((0, 0), dtype=np.float32)
            
        rows = list(range(num_nodes))
        cols = list(range(num_nodes))
        
        for src, dst in edges:
            if src < num_nodes and dst < num_nodes:
                rows.extend([src, dst])
                cols.extend([dst, src])
                
        data = np.ones(len(rows), dtype=np.float32)
        adj = sp.coo_matrix((data, (rows, cols)), shape=(num_nodes, num_nodes)).tocsr()
        
        deg = np.array(adj.sum(axis=1)).flatten()
        deg_inv_sqrt = np.zeros_like(deg, dtype=np.float32)
        nonzero = deg > 0
        deg_inv_sqrt[nonzero] = 1.0 / np.sqrt(deg[nonzero])
        
        D_inv_sqrt = sp.diags(deg_inv_sqrt)
        norm_adj = (D_inv_sqrt @ adj @ D_inv_sqrt).tocsr()
        return norm_adj

    def _relu(self, x):
        return np.maximum(0, x)

    def _softmax(self, x):
        exp_x = np.exp(x - np.max(x, axis=-1, keepdims=True))
        return exp_x / np.sum(exp_x, axis=-1, keepdims=True)

    def forward(self, features, edges):
        num_nodes = features.shape[0]
        if num_nodes == 0:
            return np.zeros((0, self.num_classes)), []
            
        norm_adj = self._normalize_adj_sparse(num_nodes, edges)
        
        H = features
        layer_activations = [H]
        
        for idx, (W, b) in enumerate(self.weights):
            agg = norm_adj.dot(H)
            z = agg.dot(W) + b
            
            if idx < len(self.weights) - 1:
                H = self._relu(z)
            else:
                H = self._softmax(z)
            layer_activations.append(H)
            
        return H, layer_activations

    def train_epoch(self, features, edges, labels):
        num_nodes = features.shape[0]
        if num_nodes == 0:
            return 0.0, 0.0
            
        norm_adj = self._normalize_adj_sparse(num_nodes, edges)
        probs, activations = self.forward(features, edges)
        
        one_hot = np.zeros_like(probs)
        for i, l in enumerate(labels):
            if 0 <= l < self.num_classes:
                one_hot[i, l] = 1.0
                
        loss = -np.mean(np.sum(one_hot * np.log(np.clip(probs, 1e-12, 1.0)), axis=1))
        
        grad_H = (probs - one_hot) / len(labels)
        for idx in reversed(range(len(self.weights))):
            W, b = self.weights[idx]
            H_in = activations[idx]
            
            agg_in = norm_adj.dot(H_in)
            dW = agg_in.T.dot(grad_H)
            db = np.sum(grad_H, axis=0)
            
            grad_agg = grad_H.dot(W.T)
            grad_H_prev = norm_adj.T.dot(grad_agg)
            if idx > 0:
                grad_H = grad_H_prev * (activations[idx] > 0)
                
            self.weights[idx][0] -= self.lr * dW
            self.weights[idx][1] -= self.lr * db
            
        preds = np.argmax(probs, axis=1)
        acc = accuracy_score(labels, preds)
        return float(loss), float(acc)

    def evaluate(self, features, edges, labels):
        probs, _ = self.forward(features, edges)
        preds = np.argmax(probs, axis=1)
        
        acc = accuracy_score(labels, preds)
        precision, recall, f1_macro, _ = precision_recall_fscore_support(
            labels, preds, average='macro', zero_division=0
        )
        _, _, f1_micro, _ = precision_recall_fscore_support(
            labels, preds, average='micro', zero_division=0
        )
        conf_mat = confusion_matrix(labels, preds, labels=list(range(self.num_classes)))
        
        return {
            'accuracy': float(acc),
            'f1_micro': float(f1_micro),
            'f1_macro': float(f1_macro),
            'precision': float(precision),
            'recall': float(recall),
            'confusion_matrix': conf_mat.tolist(),
            'predictions': preds.tolist(),
            'probabilities': probs.tolist()
        }

def extract_subcircuit_boundaries(nodes, edges, predictions):
    adj_list = {node['id']: [] for node in nodes}
    for src, dst in edges:
        if src in adj_list and dst in adj_list:
            adj_list[src].append(dst)
            adj_list[dst].append(src)
            
    visited = set()
    subcircuits = []
    
    for node in nodes:
        nid = node['id']
        if nid in visited:
            continue
            
        target_class = predictions[nid]
        comp = []
        queue = [nid]
        visited.add(nid)
        
        while queue:
            curr = queue.pop(0)
            comp.append(curr)
            for neighbor in adj_list[curr]:
                if neighbor not in visited and predictions[neighbor] == target_class:
                    visited.add(neighbor)
                    queue.append(neighbor)
                    
        subcircuits.append({
            'class_id': int(target_class),
            'class_name': ["Adder", "Multiplier", "Control Logic", "Subtractor", "Comparator"][target_class],
            'gate_ids': comp,
            'size': len(comp),
            'gates': [nodes[g]['label'] for g in comp]
        })
        
    return subcircuits
