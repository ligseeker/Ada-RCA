# P6-E4 Tier-A Integration Qualification Report

Date: 2026-08-29  
Branch: `exp/p6-baselines`  
Protocol: `docs/P6_E4_TIER_A_INTEGRATION_QUALIFICATION_PROTOCOL.md`  
Scope: non-performance integration qualification on RE2-OB and RE2-TT only

## A. Branch Isolation

- Frozen base branch: `main`.
- Frozen base SHA: `bed295326e567395e725caa82840a534dcc0b1de`.
- Qualification branch: `exp/p6-baselines`.
- The branch merge-base with `main` is the frozen base SHA.
- No baseline commit was made on `main`; no merge into `main` occurred.
- Ada-RCA Z2, conditional-logit scoring, lambda, splits, candidate registries,
  and P3/P4/P6-G0 conclusions were not modified.

## B. RCAEval Provenance

Formal qualification used the clean detached worktree:

- Path: `/home/zhangll24/RCA_project/RCAEval-clean`.
- Remote: `https://github.com/phamquiluan/RCAEval.git`.
- HEAD: `5e96b700445bfb5c599e505ecf37d53bf847bbeb`.
- Working tree: clean before and after qualification.
- Environment: pre-existing isolated conda environment `rcaeval`.
- Python: 3.10.20.
- Full package versions and `pip freeze` are stored in
  `artifacts/p6_e4/upstream_provenance.json`.

Pinned source SHA-256 values:

| Source | SHA-256 |
|---|---|
| `RCAEval/e2e/baro.py` | `ddaae58b4b03453a812c4af33eb0053d803bcb6132453dd37bfa1f5e675b72c4` |
| `RCAEval/e2e/tracerca.py` | `1ef420e4430a7ad0379689c1d18eee9dd7fb0d15ac4371f6ff968900a22b0946` |
| `RCAEval/e2e/__init__.py` | `2373740adece37e6da49c78c08f22553016c29a024784374ea1e30460c3a1e3b` |
| `RCAEval/io/time_series.py` | `e6c1e2ee5f3a98308182bdd3de72a4f03d950bfc1511385dce532797688fbbb0` |
| `main.py` | `367a2f086c599480b913d9b7b6b3c20a572a079e03e0d0d2e5feb573734384e8` |

No file in the clean RCAEval worktree was modified.

## C. All-Case Static Audit

`artifacts/p6_e4/all_case_schema_audit.json` covers all 180 legal cases:

- RE2-OB: 90;
- RE2-TT: 90;
- missing required sources: 0 cases;
- CSV parse-error cases: 0;
- malformed raw log rows: 0;
- malformed raw trace rows: 0; and
- blank timestamp rows: 514 in `metrics.csv` and the corresponding 514 in
  `simple_metrics.csv`, preserving the already documented missingness.

The audit records only schema, source presence, row counts, timestamp columns,
numeric support, trace start/duration/end support, and malformed counts. It
contains no localization outcome fields.

## D. Smoke Manifest

`artifacts/p6_e4/smoke_case_manifest.json` was generated and committed before
the first Tier-A invocation. Selection used ascending
SHA-256 of the normalized POSIX relative path and a path tie-breaker.

RE2-OB:

| Case path | SHA-256 |
|---|---|
| `currencyservice_delay/1` | `04b0ab5ba19c6f32c51d39ccfbcfd52c1327782950fe61a4b18e5a946dcf21f8` |
| `currencyservice_delay/3` | `0c789951532c6e571a6e6d41212a1e73629e38fc5bcec0d89df98c4c61365d22` |
| `currencyservice_socket/1` | `0dd7f48cc5785cba8bf7a03da80cc2b10b4cafb5b1a7ea41db8152c394ff7708` |

RE2-TT:

| Case path | SHA-256 |
|---|---|
| `ts-order-service_socket/1` | `037847ef12795bd92f60335f91706d49eab395b0a41fa7e80ae7a3688b62e676` |
| `ts-order-service_mem/2` | `05f39ee8c893b1bdc3649ce68dba8aafd618b0840948847501c6533a0d7e7e26` |
| `ts-route-service_delay/2` | `06ed19a76111c3b3b464af9e82c302bdcefbb44c113ae027808a9daab0e6f3c6` |

No label, method output, or published result entered selection.

## E. BARO

- Official callable: clean pinned `RCAEval/e2e/baro.py::baro`.
- Input: official `simple_metrics.csv` plus `inject_time.txt`.
- Loader: remove latency-50 columns, replace infinities, forward fill then zero
  fill, half-open `[t0 - 600, t0 + 600)`, and apply the upstream latency-90
  rename.
- RCAEval preprocessing: drop time and constant columns and convert memory
  indicators to MB.
- Scoring semantics: per-indicator pre-event `RobustScaler`, ranked by maximum
  post-event robust standardized value.
- Ada-RCA Z2 preprocessing was not used.
- Full observed-indicator audit: 86 OB and 383 TT names; unknown mapping count
  is zero. Passthrough, health, tracing, and other explicitly governed
  non-service entities are excluded from service projection.
- All six cases had 600 pre and 600 post metric rows.
- Twelve of twelve executions succeeded.
- Both executions of every case produced identical projected-ranking checksums.
- Native service duplicates were removed by first occurrence and no unranked
  legal service was appended.

**BARO = READY**

## F. TraceRCA

### Timestamp and window semantics

- `inject_time`: Unix seconds.
- `startTime`: Unix microseconds.
- `duration`: microseconds.
- `startTime + duration`: Unix microseconds.
- Frozen conversion factor: `1_000_000`.

Evidence is stored in
`artifacts/p6_e4/tracerca/timestamp_unit_audit.json`. It combines the pinned
README, TraceRCA source, PDiagnose's explicit trace conversion, TraceRCA's
duration scaling, git history, and the all-case RE2 numeric magnitudes. OB and
TT are consistent and no timestamp-unit ambiguity remains.

The adapter uses span end time because TraceRCA itself partitions on
`startTime + duration`. It imposes the half-open raw-span window
`[t0 - 600, t0 + 600)`. The symmetric-window choice is explicitly recorded as
an `ADAPTER ASSUMPTION` because no official generic TraceRCA runner window is
implemented.

### Operation projection and execution

Each native operation is constructed exactly as upstream does and mapped to
the explicit `serviceName` from the selected raw span. No operation-to-service
conflicts or unknown projected services occurred. Duplicate services are
deduplicated by first occurrence; partial rankings remain partial.

OB produced six successful deterministic executions. Two TT cases also
produced successful deterministic executions. The remaining TT case,
`ts-order-service_mem/2`, failed identically on both repeats with upstream
`KeyError: 'ts-order-service_getMore ts.orders'`. The post-event operation is
absent from the pre-event `normal_slo` dictionary. This is recorded as F-A
algorithmic failure. Filtering the operation, inventing an SLO, or changing
the algorithm would be an unauthorized semantic patch, so no rescue was made.

The allowed top-level qualification taxonomy has no separate algorithmic-failure
state. The failed legal input is therefore carried as
`BLOCKED / UNSUPPORTED_INPUT`, while the underlying raw taxonomy remains F-A
and is not represented as an officially declared unsupported case.

**TraceRCA = BLOCKED / UNSUPPORTED_INPUT**

## G. mmBARO

Static source analysis confirms all seven dictionary keys are required by
direct access. Actual computation uses metric and log time series. Raw logs,
raw spans, and `cluster_info` are loaded but unused. Trace-error and
trace-latency time series are used only when `dataset` equals literal `mm-ob`
or `mm-tt`.

The official dataset identifiers are `re2-ob` and `re2-tt`. Clean source,
history, docs, notebook, CI, and path searches found no explicit intended alias
mapping from `re2-*` to `mm-*`. The official multi-source notebook calls
`mmbaro` without a dataset argument, which also does not activate the trace
branches. Therefore the proposed alias cannot be frozen without human evidence.

Under official RE2 identifiers the auditable modality description is metric +
log time series; trace time series are loaded but unused. A tri-modal claim is
not permitted. Because alias qualification failed, no mmBARO smoke invocation
was performed.

**mmBARO = BLOCKED / SEMANTIC_AMBIGUITY**

## H. Output Mapping

The frozen projection rule was applied throughout:

> native ranking -> deterministic service projection -> preserve first
> occurrence -> deduplicate service.

No legal candidate completion was performed. BARO mapping uses the longest
legal service prefix at an underscore boundary plus documented aliases and
auxiliary exclusions. TraceRCA mapping uses the raw operation-to-`serviceName`
dictionary. Unknown mapping count is zero for all executed smoke records.

## I. Failure Audit

- Raw F-A records: 2, both repeats of the same TraceRCA TT case.
- F-B, F-C, F-D, and F-E records: 0.
- Exception-to-dummy fallback accepted: no.
- Successful-subset suppression used: no.
- Failure converted to a localization score: no.
- Tier-B substitution: no.

## J. Performance Firewall

The firewall audit passes. Qualification source imports neither the Ada-RCA
performance evaluator nor the RCAEval benchmark evaluator, and has no root-label
dependency. Smoke artifacts contain no ranking-performance, correctness, root
position, comparison, bootstrap, runtime-comparison, or leaderboard fields.
No published numerical result or reproduced localization outcome influenced an
adapter, timestamp, window, alias, mapping, modality, or status decision.

## K. Deviations and Unknowns

1. The first all-case audit implementation counted physical newline characters
   in quoted multiline log messages. This was corrected before commit to count
   parsed logical CSV records; the final audit has no raw-log malformed rows.
2. Raw logs contain both a display `time` field and a nanosecond `timestamp`.
   The final audit uses the source-semantic `timestamp` field.
3. The active `DAG` environment lacks `pytest`. The full suite was run in the
   recorded isolated `rcaeval` environment instead; no package was installed
   into DAG.
4. TraceRCA's top-level blocked category is an allowed-state projection of the
   preserved F-A raw failure, not a claim of official unsupported status.
5. The mmBARO dataset alias remains unresolved and requires human/upstream
   evidence. No trace-channel activation was forced.

## L. Method Status

| Method | Qualification status |
|---|---|
| BARO | `READY` |
| TraceRCA | `BLOCKED / UNSUPPORTED_INPUT` |
| mmBARO | `BLOCKED / SEMANTIC_AMBIGUITY` |

The full repository suite passes 74 tests in the isolated `rcaeval`
environment. Formal P6-E5 baseline reproduction was not executed.
