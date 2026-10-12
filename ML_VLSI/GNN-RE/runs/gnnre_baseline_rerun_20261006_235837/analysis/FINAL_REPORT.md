# GNN-RE Authors' Released Implementation — Clean PyTorch Rerun

## 1. Experiment Information

| | |
|---|---|
| Experiment ID | `gnnre_baseline_rerun_20261006_235837` |
| Purpose | Measure what the authors' released GNN-RE configuration (`TCAD.yml`) achieves in the PyTorch GraphSAINT implementation when the final predictions come from the restored best-validation checkpoint |
| Training window | 2026-10-06 23:59:56 → 2026-10-07 01:44:24 |
| Runner | `runs/run_baseline.py` (copied to `config/run_baseline.py`). It is a logging and checkpoint wrapper around the unmodified repository functions `parse_n_prepare`, `prepare`, `Minibatch.set_sampler/shuffle/one_batch/end`, `GraphSAINT.train_step/eval_step` and `calc_f1`. Its loop repeats `graphsaint/pytorch_version/train.py::train()` step for step. |
| Seed | 42 (Python, NumPy, PyTorch and CUDA). The repository has no seed mechanism of its own. |

## 2. Environment

| | |
|---|---|
| Python / PyTorch / CUDA | 3.11 / 2.1.2+cu121 / 12.1 (CUDA available) |
| GPU | NVIDIA GeForce RTX 4050 Laptop GPU, 6 GB |
| OS | Windows 11 |
| GNN-RE commit | `567ece42ed2273f57ccdff28aebb781fbf3efd55` |
| GraphSAINT commit | `c9b1e340d7b951465ac4a9251eef93832e68b003` |
| Local changes already present before this run (execution only) | NumPy drop-ins `graphsaint/cython_sampler.py` and `graphsaint/norm_aggr.py` replace the Cython extensions, which were not compiled on Windows; both were audited as algorithmically identical. `graphsaint/__init__.py` adds an `np.bool` alias for newer NumPy. **No repository file was changed by this run.** |

Full details are in `config/environment.txt`, `config/git_status.txt` and `logs/system.log`.

## 3. Dataset Verification

Every check passed (`metrics/dataset_verification.txt`, `metrics/graph_verification.txt`, `metrics/feature_verification.txt`):

| Item | Expected | Measured |
|---|---|---|
| Nodes | 104,727 | 104,727 |
| Train / Val / Test nodes | 96,251 / 1,938 / 6,538 | 96,251 / 1,938 / 6,538 |
| Train / Val / Test circuits | 22 / 6 / 9 | 22 / 6 / 9 |
| Classes | 5 | 5 |
| Features | 34 in the repo (33 in the paper) | 34; 10 columns are constant zero, including KEY (column 2) |

- **Graph:** undirected (`adj_full` is symmetric). There are 1,638 self-loops; the parser adds one for every gate that drives a primary output.
- **Training adjacency:** `adj_train` contains only train–train edges.
- **Splits:** no node belongs to two splits, and no circuit spans two splits.
- **Scaling:** `StandardScaler` is fitted on training nodes only. An independent recomputation matches it exactly (max difference 0).
- **Test circuits:** six 16-bit designs plus three 2-bit designs.

## 4. Model Architecture

This is the instantiated model (`metrics/model_architecture.txt`), not an inference from the config:

| Layer | Class | Order | In | Out | Heads | Aggregation | Activation | Params |
|---|---|---|---|---|---|---|---|---|
| 1 | AttentionAggregator | 1 | 34 | 512 | 8 | concat | ReLU | 19,456 |
| 2 | AttentionAggregator | 1 | 512 | 512 | 8 | concat | ReLU | 264,192 |
| 3 | AttentionAggregator | 0 | 512 | 256 | 8 | concat | ReLU | 131,840 |
| 4 | HighOrderAggregator (classifier) | 0 | 256 | 5 | – | – | identity, then softmax | 1,295 |

Total trainable parameters: **416,783**. An L2 normalization sits before the classifier, and gradients are clipped to norm 5.

## 5. GraphSAINT Configuration

These values were verified on the live sampler objects (`metrics/graphsaint_verification.txt`):

- **Settings:** random-walk sampler, 3,000 roots, walk length 2, sample coverage 50. Each batch has a budget of 6,000 nodes, giving 17 batches per epoch.
- **Roots:** drawn uniformly, with replacement, from training nodes only.
- **Subgraphs:** the induced-subgraph check and the edge-index check both passed.
- **Normalization:** `norm_loss` is zero on validation and test nodes, and the GraphSAINT α/λ normalization is active.

## 6. Training Configuration

Adam, learning rate 0.01, dropout 0.1, 2,000 epochs, validation every epoch. The model is selected on validation Micro-F1, saving only on a strict improvement, exactly as in the repo. The `TCAD.yml` used has SHA-256 `76cf8de9…85efa` and is unchanged.

## 7. Training Summary

| | |
|---|---|
| Epochs completed | 2,000 of 2,000 (no crash) |
| Training wall time | 6,268.6 s (1 h 44 m) |
| Pure train-step time | 5,993.5 s |
| Average epoch | 3.13 s |
| Time to best epoch | 847.1 s |
| Data loading / model init / sampler pre-sampling / final eval | 0.22 s / 0.69 s / 71.95 s / 0.38 s |

The per-epoch log is in `logs/train.log`; the machine-readable history is in `metrics/training_history.json`.

## 8. Best Checkpoint

| | |
|---|---|
| Best epoch | **286** |
| Best validation Micro-F1 = accuracy | **96.59%** |
| Best validation Macro-F1 | 93.33% |
| Checkpoint | `checkpoints/best_model.pkl` (saved 2026-10-07 00:14:03) |

**Integrity checks** (`metrics/checkpoint_integrity.txt`):
- The reloaded checkpoint's epoch matches the recorded best epoch.
- The model is in evaluation mode and all 4 dropout modules are inactive.
- Gradients are off (`torch.no_grad`).
- Two separate inference passes give identical predictions; the largest probability difference is 1.9e-7.
- Validation Micro-F1 after reloading equals the recorded value exactly.

**Test predictions were exported only after the best checkpoint was reloaded.**

## 9. Test Results

| Metric | Value |
|---|---|
| Accuracy | **97.22%** |
| Micro-F1 | **97.22%** (identical to accuracy for single-label classification) |
| Macro-F1 | **95.54%** |
| Errors | 182 of 6,538 (2.78%) |

The repo's own `calc_f1` gives the same values.

## 10. Per-Class Precision / Recall / F1

Classes are in the paper's Table IV order.

| Class | Rerun Precision | Paper Precision | Rerun Recall | Paper Recall | Rerun F1 | Paper F1 |
|---|---:|---:|---:|---:|---:|---:|
| ADD | 88.02 | 97.51 | 89.16 | 96.24 | 88.59 | 96.87 |
| MUL | 98.35 | 99.14 | 98.73 | 99.61 | 98.54 | 99.38 |
| CTRL | 97.06 | 94.74 | 95.85 | 97.50 | 96.45 | 96.10 |
| COMP | 99.13 | 100 | 99.13 | 97.39 | 99.13 | 98.68 |
| SUB | 98.55 | 100 | 91.64 | 94.88 | 94.97 | 97.37 |

The rerun matches or beats the paper on 4 of 15 values: CTRL precision, CTRL F1, COMP recall and COMP F1.

## 11. Confusion Matrix

Rows are the true class, columns the predicted class.

| | ADD | MUL | CTRL | SUB | COMP |
|---|---:|---:|---:|---:|---:|
| ADD | 617 | 70 | 2 | 3 | 0 |
| MUL | 63 | 5054 | 2 | 0 | 0 |
| CTRL | 4 | 4 | 231 | 2 | 0 |
| SUB | 17 | 11 | 2 | 340 | 1 |
| COMP | 0 | 0 | 1 | 0 | 114 |

## 12. Error Analysis

See `analysis/error_analysis.txt`.

| Direction | Rerun share of errors | Paper |
|---|---:|---:|
| ADD → MUL | 38.46% | 18% |
| MUL → ADD | 34.62% | 40% |
| SUB → ADD | 9.34% | – |
| SUB → MUL | 6.04% | – |
| ADD → SUB | 1.65% | – |
| COMP → MUL | 0% | 0% (never) |
| COMP → ADD | 0% | rare |

- **Error rate:** 2.78% here versus 1.13% in the paper. The rerun exceeds the paper's ceiling of 2.25% across all datasets.
- **Main confusion:** adder versus multiplier gates account for 73.1% of all errors, in both directions. The paper's asymmetry (MUL→ADD dominant) is not reproduced.

## 13. Comparison With Previous 96.27% Run

| | Old reported | Clean rerun | Difference |
|---|---:|---:|---:|
| Accuracy | 96.27% | 97.22% | **+0.95 pp** |
| Macro-F1 | 92.24% | 95.54% | **+3.30 pp** |

**The old 96.27% did not come from the best checkpoint.** This is confirmed by evaluating the old checkpoint directly (`analysis/old_checkpoint_eval.json`, inference only):

- The old run's own best-validation checkpoint (`pytorch_models/saved_model_2026-09-04 15-42-03.pkl`, last saved at 17:03) scores **97.54% accuracy and 95.97% macro-F1 on test**, with validation at 96.08%.
- The old `predictions_test_per_gate.csv` (96.27%) disagrees with that checkpoint on **178 of 6,538** test gates.
- The CSV was written at 15:48:38, 6.5 minutes after the run started. So it came from an early, non-best model state.
- The dashboard's 96.27% figure was therefore an export error, not the released model's performance.
- Two correctly evaluated runs of the released configuration now exist: **97.54%** (old, seed unknown) and **97.22%** (this run, seed 42). That spread is ordinary seed-to-seed variance.

## 14. Comparison With Paper's 98.87%

| | Paper | Clean rerun | Difference |
|---|---:|---:|---:|
| Accuracy | 98.87% | 97.22% | **−1.65 pp** |
| Macro-F1 | 97.68% (recomputed from Table IV) | 95.54% | −2.14 pp |
| Error rate | 1.13% | 2.78% | +1.65 pp |
| Training time | 16,317.44 s (Tesla K20m, TensorFlow) | 6,268.6 s (RTX 4050, PyTorch) | Not comparable: different hardware and framework |

The paper does not report a macro-F1 itself. The 97.68% is the mean of its five per-class F1 values. **I did not invent an overall paper precision, recall or F1.**

## 15. Reproducibility Assessment

- **The rerun is internally reliable.**
  - The dataset, graph, features, sampler and configuration were all verified.
  - The best checkpoint was restored and checked.
  - Inference is deterministic.
  - Training completed all 2,000 epochs.
- **Across seeds, the released configuration lands at 97.2–97.5% on test.** This is consistent across the two evaluated runs, and both are well below 98.87%.
- **Bit-exact reruns are not guaranteed.** GPU sparse operations are not forced to be deterministic; the repo does not force it, so this run doesn't either.

## 16. Important Differences From Paper

1. **Architecture:** `TCAD.yml` (`1-1-0`) builds 3 aggregator layers with two `[512,256]` stages. Table III describes 5 layers with four `[512,256]` stages. This is a genuine difference.
2. **Framework:** this is PyTorch GraphSAINT; the paper used TensorFlow. The GAT layers are only partially equivalent: the attention score's functional form, where ReLU is applied, and how normalization is grouped all differ.
3. **Features:** 34 here versus 33 in the paper (a constant-zero KEY column plus 9 other constant columns). This is a harmless representation difference.
4. **Sampler:** NumPy replacements for the Cython extensions. They are algorithmically identical.
5. **Experiments not run:** circuit-level majority vote and the unseen-design experiments.

## 17. Conclusion

**B. "Clean rerun confirms a reproducibility gap"**

- **Released implementation result:** 97.22% accuracy (Micro-F1 97.22%, Macro-F1 95.54%), best-validation checkpoint at epoch 286, seed 42.
- **Paper result:** 98.87% accuracy.
- **Difference:** −1.65 percentage points.

**Why the gap exists is not established by this run.** The leading candidates are the 3-layer versus 5-layer architecture and the differences between the PyTorch and TensorFlow GAT layers. Only the planned 5-layer (`1-1-1-1-0`) experiment can separate those causes.
