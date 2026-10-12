# Reproducibility Manifest

| Field | Value |
|---|---|
| Experiment ID | gnnre_baseline_rerun_20261006_235837 |
| Date/time | Training 2026-10-06 23:59:56 → 2026-10-07 01:44:24 (local, UTC+5:30) |
| Git commit (GNN-RE) | 567ece42ed2273f57ccdff28aebb781fbf3efd55 |
| Git commit (GraphSAINT) | c9b1e340d7b951465ac4a9251eef93832e68b003 |
| Git status | See `config/git_status.txt`. Pre-existing untracked NumPy sampler and norm_aggr drop-ins plus the `np.bool` alias; nothing was changed by this run. |
| Python | 3.11 (anaconda env `torch311`) |
| PyTorch | 2.1.2+cu121 |
| CUDA | 12.1 |
| GPU | NVIDIA GeForce RTX 4050 Laptop GPU (6 GB) |
| Seed | 42 (Python, NumPy, PyTorch, CUDA); see `config/seed.txt` |
| Dataset | GNN-RE `Netlist_to_graph/Graphs_datasets/Interconnected-Modules` (104,727 nodes; 96,251 / 1,938 / 6,538) |
| Dataset hashes (SHA-256) | feats.npy `c9f340dd…8b39db`; role.json `f47eb4a6…368a8d`; class_map.json `b5b85aff…42947d`; adj_full.npz `fa452b98…81e39d`; adj_train.npz `94877e8c…3d183` (full values in `metrics/dataset_verification.txt`) |
| TCAD.yml | `config/TCAD.yml` (SHA-256 76cf8de931415360d0d127c8dd784a2fcc8aa8c436e1a28b4d65ca9e57d85efa), unchanged: dim 256, aggr concat, loss softmax, arch 1-1-0, act relu, attention 8, bias norm; lr 0.01, dropout 0.1, weight_decay 0, sample_coverage 50; phase end 2000, sampler rw, depth 2, num_root 3000 |
| Model architecture | AttentionAggregator 34→512, 512→512, 512→256 (order 1, 1, 0; 8 heads; concat; ReLU), then L2-normalize, then classifier 256→5; 416,783 parameters (`metrics/model_architecture.txt`) |
| Sampler configuration | Random walk, 3000 roots, walk length 2, coverage 50, 6000-node budget, 17 batches per epoch |
| Training configuration | Adam, lr 0.01, dropout 0.1, gradient clip 5, 2000 epochs, validation every epoch, best checkpoint saved on strictly higher validation Micro-F1 |
| Best epoch | 286 |
| Best validation metrics | Micro-F1 = accuracy 96.5944%, Macro-F1 93.3299% |
| Final test metrics | Accuracy 97.22%, Micro-F1 97.22%, Macro-F1 95.54%, 182 errors (2.78%) |
| Training duration | 6,268.6 s wall (5,993.5 s in train steps); 3.13 s per epoch on average |
| Checkpoint path | `checkpoints/best_model.pkl` (+ `checkpoints/best_model_meta.json`) |
| Prediction path | `predictions/test_predictions.csv` |
| Command | `~/anaconda3/envs/torch311/python.exe -u runs/run_baseline.py --exp_dir runs/gnnre_baseline_rerun_20261006_235837` |
