# P3-A0 RE2 Dataset Audit

Status: PASS.

The local frozen data roots are:

- RE2-OB: `/home/zhangll24/RCA_project/datasets/RCAEval/RE2-OB`
- RE2-TT: `/home/zhangll24/RCA_project/datasets/RCAEval/RE2/RE2-TT`

Each dataset has 90 accepted cases, exactly 5 root services × 6 fault types × 3 repetitions, with zero exclusions. Every accepted case has metrics, logs, traces, t0, and the four official derived numeric channels (`simple_metrics.csv`, `logts.csv`, `tracets_err.csv`, `tracets_lat.csv`).

Candidate registries are derived from label-free `simple_metrics.csv` CPU and MEM entity columns, removing only the fixed auxiliary entities `frontend-check`, `frontend-external`, `istio-init`, and `loadgenerator`:

| Dataset | Candidate count | Candidate set variation | Root-in-registry violations |
|---|---:|---:|---:|
| RE2-OB | 11 | 0 | 0 |
| RE2-TT | 68 | 0 | 0 |

The complete machine-readable manifest is in `artifacts/source/{re2ob,re2tt}/`. P3-R0 recorded the content tree digests and malformed timestamp evidence. In particular, two RE2-OB `simple_metrics.csv` files contain 514 blank timestamp rows in total; these rows are not deleted or imputed by the audit and remain explicit missingness for the representation stage.

## Label separation

Each bundle has separate `inputs.jsonl`, `labels.jsonl`, and trusted `sources.jsonl`. Prediction-visible inputs contain opaque case IDs, t0, the complete candidate registry, modality references, and label-free metadata only. Root service, fault type, directory names, and local source paths occur only in label/source sidecars.
