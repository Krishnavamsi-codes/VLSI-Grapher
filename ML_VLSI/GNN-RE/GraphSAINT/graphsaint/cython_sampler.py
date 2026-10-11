"""
cython_sampler.py - Pure Python/NumPy drop-in for graphsaint.cython_sampler
Implements the exact canonical GraphSAINT Random Walk (RW) and FullBatch sampler algorithms.
"""
import numpy as np
import scipy.sparse as sp

class RW:
    def __init__(self, adj_indptr, adj_indices, node_train, num_proc, num_sample_per_proc, size_root, size_depth):
        self.adj_indptr = np.asarray(adj_indptr, dtype=np.int32)
        self.adj_indices = np.asarray(adj_indices, dtype=np.int32)
        self.node_train = np.asarray(node_train, dtype=np.int32)
        self.num_proc = num_proc
        self.num_sample_per_proc = num_sample_per_proc
        self.size_root = int(size_root)
        self.size_depth = int(size_depth)
        self.total_samples = max(1, num_proc * num_sample_per_proc)

    def par_sample(self):
        ret_indptr = []
        ret_indices = []
        ret_data = []
        node_sampled = []
        ret_edge_index = []

        num_train = len(self.node_train)
        adj_indptr = self.adj_indptr
        adj_indices = self.adj_indices
        node_train = self.node_train
        size_root = self.size_root
        size_depth = self.size_depth

        for _ in range(self.total_samples):
            # 1. Uniformly sample roots from training nodes
            rand_indices = np.random.randint(0, num_train, size=size_root)
            roots = node_train[rand_indices]
            visited = list(roots)

            # 2. Length-d random walk from each root
            for v in roots:
                curr = v
                for _ in range(size_depth):
                    s = adj_indptr[curr]
                    e = adj_indptr[curr + 1]
                    deg = e - s
                    if deg > 0:
                        curr = adj_indices[s + np.random.randint(0, deg)]
                        visited.append(curr)

            # 3. Form sorted unique node set
            subg_nodes = np.unique(visited).astype(np.int32)
            subg_nodes.sort()
            num_subg = len(subg_nodes)

            # 4. Map original node ID -> subgraph local index
            # Using an array lookup for fast O(1) integer indexing
            max_nid = int(subg_nodes[-1])
            orig2subg = np.full(max_nid + 1, -1, dtype=np.int32)
            orig2subg[subg_nodes] = np.arange(num_subg, dtype=np.int32)

            subg_indptr = np.zeros(num_subg + 1, dtype=np.int32)
            subg_indices_list = []
            subg_edges_list = []

            for i, nid in enumerate(subg_nodes):
                s = adj_indptr[nid]
                e = adj_indptr[nid + 1]
                neighs = adj_indices[s:e]
                # Filter neighbors that are in subgraph and get their local IDs
                valid_mask = (neighs <= max_nid)
                if np.any(valid_mask):
                    valid_neighs = neighs[valid_mask]
                    mapped = orig2subg[valid_neighs]
                    in_subg = (mapped >= 0)
                    if np.any(in_subg):
                        local_neighs = mapped[in_subg]
                        subg_indices_list.append(local_neighs)
                        subg_indptr[i + 1] = len(local_neighs)
                        # Edge index in original adj_train
                        orig_edge_offsets = np.where(valid_mask)[0][in_subg]
                        subg_edges_list.append(s + orig_edge_offsets)

            subg_indptr = subg_indptr.cumsum().astype(np.int32)
            if len(subg_indices_list) > 0:
                subg_indices = np.concatenate(subg_indices_list).astype(np.int32)
                subg_edges = np.concatenate(subg_edges_list).astype(np.int32)
            else:
                subg_indices = np.empty(0, dtype=np.int32)
                subg_edges = np.empty(0, dtype=np.int32)

            subg_data = np.ones(len(subg_indices), dtype=np.float32)

            ret_indptr.append(subg_indptr)
            ret_indices.append(subg_indices)
            ret_data.append(subg_data)
            node_sampled.append(subg_nodes)
            ret_edge_index.append(subg_edges)

        return [ret_indptr, ret_indices, ret_data, node_sampled, ret_edge_index]


class FullBatch:
    def __init__(self, adj_indptr, adj_indices, node_train, num_proc, num_sample_per_proc):
        self.adj_indptr = np.asarray(adj_indptr, dtype=np.int32)
        self.adj_indices = np.asarray(adj_indices, dtype=np.int32)
        self.node_train = np.asarray(node_train, dtype=np.int32)

    def par_sample(self):
        data = np.ones(len(self.adj_indices), dtype=np.float32)
        edge_index = np.arange(len(self.adj_indices), dtype=np.int32)
        return [[self.adj_indptr], [self.adj_indices], [data], [self.node_train], [edge_index]]
