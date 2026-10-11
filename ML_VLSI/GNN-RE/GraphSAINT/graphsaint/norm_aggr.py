"""
norm_aggr.py - Pure Python/NumPy drop-in for graphsaint.norm_aggr
Replaces compiled Cython extension with vector indexing: data[:] = norm_aggr[edge_index]
"""
import numpy as np

def norm_aggr(data, edge_index, norm_aggr_weights, num_proc=20):
    data[:] = norm_aggr_weights[edge_index]
