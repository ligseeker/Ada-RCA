# RCAEval Confirmatory Baseline Execution Status and Handoff

Status: **POST-LOCK INDEPENDENT BASELINE AUDIT COMPLETE — CAUSALRCA RUNTIME NOT EXECUTED**
State revision: `2026-09-12.3`
Last operational audit: 2026-09-12, Asia/Shanghai
Branch: `evaluation/rcaeval-baselines`  
Last synchronized central commit: `8077f57` fault-level audit handoff; report wording clarification follows

This is the canonical operational handoff for the RCAEval confirmatory
baseline work. Read it at the start of every new session and update it after
every completed task that changes code, environments, artifacts, execution
coverage, locks, blockers, or the next plan.

The historical six-method V2 evaluation remains immutable. The current
canonical thesis-facing comparison is the independent seven-baseline V3
composite documented in
`RCA_BASELINE_FINAL_COMPARISON_V3.md`.

The frozen protocol documents remain authoritative for scientific semantics.
If this status document conflicts with committed artifacts or a fresh read-only
audit, stop execution, resolve the discrepancy without inspecting prediction
contents, and update this document.

## 1. Required reading order

1. repository-root `AGENTS.md`;
2. this status and handoff document;
3. `RCA_BASELINE_PROTOCOL_FREEZE_V1.md`;
4. `RCA_BASELINE_ADAPTER_SPEC_V1.md`;
5. `RCA_BASELINE_EXECUTION_MATRIX_V1.md`;
6. `RCA_BASELINE_FAILURE_POLICY_V1.md`;
7. `RCA_BASELINE_PERFORMANCE_FIREWALL_V1.md`;
8. `RCA_BASELINE_PARALLEL_EXECUTION_AMENDMENT_V1_1.md`;
9. `RCA_BASELINE_TRACE_CSV_PARSER_AMENDMENT_V1_2.md`;
10. `RCA_BASELINE_CASE_PARALLELISM_AMENDMENT_V1_3.md`;
11. `RCA_BASELINE_PARALLEL_RUNBOOK_V1_1.md`; and
12. `RCA_BASELINE_ENVIRONMENTS.md`.

## 2. Frozen repository and provenance

| Item | Frozen/current value | Status |
|---|---|---|
| Required branch | `evaluation/rcaeval-baselines` | PASS |
| Push state for this revision | `origin/evaluation/rcaeval-baselines` contains the final composite through `a22cda0`; local audit commits are not pushed | NOT PUSHED |
| This task Starting HEAD | `a0aebe29f7e568b6aa523fb259f2bbd62002a57c` | recorded |
| Required starting HEAD | `54b403ff0441c318817818abeda13526652ae1d2` | ancestor present |
| Ada-RCA Scientific V1 | `bed295326e567395e725caa82840a534dcc0b1de` | immutable |
| Evidence-closure reference | `9342e06db91945be2e44703437229ba45b18bda8` | frozen |
| RCAEval checkout | `/home/zhangll24/RCA_project/RCAEval-clean` | clean |
| RCAEval commit | `5e96b700445bfb5c599e505ecf37d53bf847bbeb` | PASS |
| Protocol digest | `aa4f03363e1347a4b4e3c6427fd846be80452f025c3a6d08042ed6f6de0a849e` | frozen |
| Input-manifest digest | `b8280866432cdd494825cf831d2a73d2fe157de0ecd8801347953172e1ab43ec` | frozen |
| V2.1 rescue protocol digest | `dbba81fae2b879bc77084bd6cc07c207c4a9f30dc5a286eb6b1533b0144429de` | frozen |
| V2 combined CausalRCA protocol digest | `24419f179d44ee09f082a23173a0d35c5ec2d3d5592cd93ff9a2afe1d0591e54` | additive; lock/evaluation complete |
| BARO V1 prediction lock | `artifacts/baseline_eval/execution_v1/locks/baro_prediction_lock.json`; SHA-256 `75cd1020aaaced22eef445856e4e73842ed4949fef4fd2fe85ffb278bcc08e65`; commit `fbfb6e6e1f112f93fe544f8b6c71aca4f5b336f7` | PASS; inherited immutable evidence |
| Six-method V2 combined prediction lock | `artifacts/baseline_eval/execution_v2/prediction_lock_v2_causalrca.json`; SHA-256 `935d0a3e57e27cf3b8c0d267e6d114499846f7abbce1ffec3c34ad34a63f2200`; commit `2778c64f137601f307e21e735e2ad23a3e14eda6` | PASS; inherited immutable evidence |
| BARO scope-freeze commit | `bf6349e342fa2e1ffbb1348bccbf852821503bec` | PASS; committed before BARO label join |
| Final comparison code | `60770dab33b22dc27f862c5aa9405b8bf608b613`; firewall compatibility `1fed561` | complete |
| Final comparison regression tests | `badefd4` | focused `15/15` PASS |
| V3 final metrics artifacts | `ad6b03ca794df30a2e83adb26344f689ad9282f9` | complete; six inherited rows identity-checked |
| V3 canonical report | `docs/baseline_eval/RCA_BASELINE_FINAL_COMPARISON_V3.md`; commit `8b07b79` | PASS; current canonical report |
| Final validation before audit | common-env unittest `262 tests`, pytest `262 passed`; old V2 SHA identity audit PASS | complete |
| Independent audit provenance | `artifacts/baseline_eval/audit_fix_v1/provenance_audit.json`; pinned RCAEval `5e96b700`; local audit source HEAD `218eb30` | complete; post-lock |
| Independent audit artifacts | `artifacts/baseline_eval/audit_fix_v1/`; report `RCA_BASELINE_AUDIT_FIX_V1.md` | complete; committed `46c8450` |
| Final audit validation | common-env unittest `275 tests`, `0` failures; JSON/CSV/JSONL integrity checks PASS; fault-level reconciliation PASS | complete |

The `.gitignore` change was re-audited. It does **not** add ignore patterns; it
only removes the final newline from the existing `artifacts/cache/` line. On
2026-08-31 the user explicitly accepted this state and authorized selective
future ignore additions only for files that are not execution evidence. The
change is included in recovery-readiness commit `3bedcb5`. The CIRCA execution
records remain intentionally untracked evidence until a valid method lock can
be produced; they are not ignored.

## 3. Environment migration status

Environment migration is complete. New virtual environments live outside all
project worktrees under `~/.venvs/`.

| Method | Environment/interpreter | Python | Key dependency | Current state |
|---|---|---|---|---|
| BARO | project `.venv/bin/python` | 3.10.20 | historical frozen stack | environment valid; execution complete |
| CIRCA | project `.venv/bin/python` (historical A1/A2); V2 `~/.venvs/ada-rca-baselines-common/bin/python` | 3.10.20 | historical frozen stack; V2 common stack | A1/A2 retained; V2 execution complete; lock verified centrally |
| MicroCause | `~/.venvs/ada-rca-baselines-microcause/bin/python` | 3.10.20 | `tigramite==4.2.2.1` | A1 retained; A2 complete; four-worker lock verified centrally |
| MicroRank | `~/.venvs/ada-rca-baselines-common/bin/python` | 3.10.20 | Tigramite 5.2.10.1 in common stack | A1/A2 integrated; method lock verified centrally |
| TraceRCA | `~/.venvs/ada-rca-baselines-common/bin/python` | 3.10.20 | common stack | A1/A2 integrated; method lock verified centrally |
| mmBARO | `~/.venvs/ada-rca-baselines-common/bin/python` | 3.10.20 | common stack | A1/A2 integrated; method lock verified centrally |
| CausalRCA | `~/.venvs/ada-rca-baselines-common/bin/python` | 3.10.20 | additive CPU case-level extension | environment frozen; execution complete; lock valid |

Activation commands:

```bash
source ~/.venvs/ada-rca-baselines-common/bin/activate
source ~/.venvs/ada-rca-baselines-microcause/bin/activate
```

The project-local `.venv` remains part of the historical BARO/CIRCA evidence
and must not be removed or replaced. Full activation, recreation, and routing
details are in `RCA_BASELINE_ENVIRONMENTS.md`.

## 4. Implementation and validation completed

| Work item | Commit | State |
|---|---|---|
| Frozen adapter/protocol audit | `b777f15` through `f7dcd8d` | complete |
| Performance firewall | `54b403f`, `2d9e96e` | complete |
| Original sequential execution harness | `e056958` | superseded for cross-method scheduling only |
| Parallel execution amendment and method-isolated harness | this revision | complete; all task runs integrated |
| Frozen input manifest | `5b3d944` | complete |
| BARO environment freeze | `5018f5d` | complete |
| BARO label-free prediction lock | `fbfb6e6` | complete |
| CIRCA environment freeze | `d5d837e` | complete |
| Later-baseline preflight hardening | `5ae9ebb` | complete |
| External environment documentation | `1529f4b` | complete and merged into this branch |
| Read-only later-method environment preflight | `6b01649` | complete |
| Environment/preflight guide update | `1a7718c` | complete |
| Canonical execution status/handoff | `a5ea541` | complete |
| Later-baseline execution-integrity hardening | `c51d37a` | complete |
| Later-baseline data/graph contract validation | `0d0efcf` | complete |
| Raw-trace CSV parser repair and V1.2 amendment | `f072c2a` | complete; central and affected task branches integrated |
| Four-way case scheduler, runtime summary, and V1.3 amendment | this revision | implementation complete; all five A2 task commits integrated |
| Frozen-environment/preflight stabilization | `c1c7a96` | complete; merged as `83e2df7` (CIRCA) and `60a346a` (MicroCause) |
| Central integration of five method tracks | `d6ca33f` through `db78094` | complete; method-scoped artifacts merged and all five locks verified |
| Deferred CausalRCA GPU work | branch `wip/causalrca-gpu-amendment`, commit `89db7ec` | saved only; not authorized for execution |
| V2.1 performance-blind rescue protocol and metric timestamp repair | `3a27d0e`; `dbba81fae2b879bc77084bd6cc07c207c4a9f30dc5a286eb6b1533b0144429de` | frozen; V2 execution complete |
| V2 no-timeout scheduler, provenance, resume, and process monitoring | `26b1864`, `6f1df1a` | complete; all six task tracks integrated |
| V2 post-lock evaluator and failure semantics | `60b45b1` | complete; labels gated by committed V2 global lock |
| V2 task-container runbook | `f60252c`; command-path sync `596f68b`; current recovery `ceac081` | complete; exact commands in `RCA_BASELINE_RESCUE_RUNBOOK_V2.md` |
| V2 fault-level row regression test | `c226ff5` | complete; focused suite 70/70 |
| V2 preflight metadata/environment-isolation repair | `8ee08ed` | complete; focused suite 72/72; task preflights passed |
| V2 preflight caller regression test | `de70370` | complete; focused suite 73/73 |
| V2 no-timeout preflight/server-startup and validity repair | `41badec` | complete; V2 synthetic preflight uses `timeout=None`; nested blocking counts fixed |
| V2 immutable method-lock re-attestation | `759f780`, `dfe48f1` | complete; corrected `_reissued_v2` sidecars preserve original locks |
| V2 lock-sidecar firewall allowlist | `dd7ce3c` | complete; historical and corrected sidecars remain immutable and pre-lock safe |
| V2.2 implementation amendment | `9f10742`; `RCA_BASELINE_RESCUE_IMPLEMENTATION_AMENDMENT_V2_2.md` | recorded; performance-blind execution correction |
| V2 pre-lock interim unified tables | `RCA_BASELINE_INTERIM_UNIFIED_TABLES_V2.md` | recorded; RE2-OB operational snapshot only, metric cells intentionally blank |
| CausalRCA CPU case-level V2 extension | `088b044`; merged evidence `ed4026f`; protocol digest `fe46fc498507370563452aa3b31fa65938f5a23c6850586a22afcafa0787551b` | complete; 180 records; lock valid |
| Six-method V2 combined lock/evaluation amendment | `RCA_BASELINE_V2_CAUSALRCA_COMBINED_LOCK_AMENDMENT_V1.md`; machine digest `24419f179d44ee09f082a23173a0d35c5ec2d3d5592cd93ff9a2afe1d0591e54` | authorized; lock `2778c64`, metrics `8da9b44`, report `c990c0e` |
| V2 final Table C/D presentation refresh | `ce673c9`; report `c990c0e` | complete; no lock or metric JSON changes; full suite 247/247 |
| BARO final integration amendment and scope lock | `bf6349e342fa2e1ffbb1348bccbf852821503bec`; `RCA_BASELINE_BARO_FINAL_INTEGRATION_AMENDMENT_V1.md`; `final_comparison_v3/scope_lock_v3.json` | complete before post-scope BARO evaluation |
| Seven-baseline final comparison implementation | `60770da`; `badefd4`; `1fed561` | complete; no baseline rerun |
| Seven-baseline final comparison artifacts | `ad6b03c` at `artifacts/baseline_eval/final_comparison_v3/` | complete; independent BARO evaluation plus inherited V2 identity |
| Seven-baseline canonical report | `docs/baseline_eval/RCA_BASELINE_FINAL_COMPARISON_V3.md`; commit `8b07b79` | complete; current canonical report |
| Frozen dual service-level evaluators | `bd34cce`, aligned to pinned RCAEval slot projection in `f88a7cb` | complete; synthetic tests PASS |
| CausalRCA diagnostic seam and mock tests | `f1f4af7` | complete; no real CausalRCA invocation |
| Post-lock audit generator and firewall gate | `31ffa24`; MicroRank case-evidence persistence `218eb30` | complete; audit outputs require committed lock binding |
| Post-lock audit evidence and report | `46c8450` | complete; historical records/locks unchanged |

The read-only command below performs dependency identity collection, two
synthetic predictions, clean-checkout import verification, and OB/TT schema
checks. It writes no artifact and does not authorize real execution:

```bash
python scripts/run_baseline_confirmatory.py preflight-environment \
  --method <METHOD> \
  --python <ABSOLUTE_EXTERNAL_PYTHON>
```

Verified synthetic fingerprints:

| Method | Fingerprint | State |
|---|---|---|
| MicroCause | `594e370ebd9cbc7da54d97e8cd3d6fc0084961fd08bdb8ca3ef31b6e1df5a0ea` | two-run PASS |
| MicroRank | `8495edcc420230bc760d43bba175cec747bf2c0edda21ef5b5a80c4450e2a491` | two-run PASS |
| TraceRCA | `b56fedf7a64308ce1ba3f915712b3672ae029c060e319ff1d942628751dfb125` | two-run PASS |
| mmBARO | `233b5ca861daaaab6f39198b5244a1f858b6a753a74a1bed1812527029eaec49` | two-run PASS |

All four read-only preflights were repeated after `0d0efcf`; their fingerprints
remained identical to the values above. The stricter BARO method-lock verifier
also passed against all 180 frozen terminal records. Adapter-only input loading
for one opaque MicroRank case per dataset passed the real trace schema, digest,
timestamp-unit, and canonical-window checks without invoking the method.

The full suite for the V1.2 parser-repair revision passed with `193` tests.
This includes the actual 365,484-by-11 crashing trace in a subprocess, parser
scope enforcement, both amendment digests, same-method exclusion, different-
method concurrent locks, disjoint artifact paths, and shared Git-common lock
placement. The original failing case also reached `SUCCESS` for TraceRCA and
mmBARO with the repaired code; prediction contents were not inspected.

The V1.3 preflight repair passed the full suite with `203` tests. It resolves
the frozen user-site visibility profile from the complete committed environment
identity instead of inheriting a container's ambient `PYTHONNOUSERSITE` value.
The MicroCause synthetic-only random walk is bounded to 10 epochs and 100 steps;
the two-run fingerprint remains the frozen `594e370e...` value, while the exact
preflight completed in 12.1 seconds. CIRCA's exact two-run preflight completed
in 9.0 seconds. Real case invocations retain the native 1,000-by-1,000
MicroCause random walk.

On 2026-09-02 the central coordinator cherry-picked only method-scoped
environment, retained A1 evidence, and A2 record/runtime/lock commits. The
central commits are CIRCA `d6ca33f`/`5a49b58`, MicroCause
`9d2db42`/`60a0b87`, MicroRank `f634745`/`865cbdb`/`9ead45b`/`6136ba4`,
TraceRCA `8ef492e`/`cbb4404`/`0c4d9a3`, and mmBARO
`9719386`/`2b147cc`/`db78094`. No user-method source or `artifacts/p6_*`
path was merged; baseline orchestration remains under `src/baseline_eval`,
and baseline execution evidence remains under `artifacts/baseline_eval`.

The following V2 implementation paragraph is a historical checkpoint retained
for provenance; the current state is recorded in Sections 5–8 and at the top
of this document.

The V2.1 implementation is extended by the performance-blind V2.2 correction
in `41badec`, `759f780`, and `dfe48f1`. V2 synthetic preflight and server
startup now wait without a wall-clock timeout; real-case execution remains
explicitly `--no-timeout`. Lock validity now inspects nonzero nested blocking
counts, and an invalid pre-correction lock can only be superseded by an
immutable, fully verified `_prediction_lock_reissued_v2.json` sidecar. The
focused rescue/evaluator suite passed 81 tests after the correction; the full
repository suite passed 241 tests. At that historical checkpoint, V2
operational evidence was split across the five task worktrees and no V2 global
lock or label evaluation had been created.

## 5. Confirmatory execution coverage (operational evidence)

This section intentionally records execution counts and status taxonomy only.
The post-scope BARO evaluation and final composite result tables are recorded
in B8 and the V3 canonical report; this section is not retroactively converted
into a label-free seven-method lock claim.

Only operational state is recorded here. No prediction contents, labels, root
ranks, or metrics may be added before the global prediction lock.

| Method | Dataset | Records | SUCCESS | METHOD_FAILURE | ADAPTER_FAILURE | DATA_FAILURE | TIMEOUT | Method lock |
|---|---|---:|---:|---:|---:|---:|---:|---|
| BARO | RE2-OB | 90/90 | 90 | 0 | 0 | 0 | 0 | valid |
| BARO | RE2-TT | 90/90 | 90 | 0 | 0 | 0 | 0 | valid |
| CIRCA A1 | RE2-OB | 90/90 | 86 | 4 | 0 | 0 | 0 | absent; retained |
| CIRCA A1 | RE2-TT | 27/90 | 8 | 2 | 0 | 0 | 17 | absent; retained |
| CIRCA A2 | RE2-OB | 90/90 | 85 | 3 | 0 | 2 | 0 | valid; 4 workers |
| CIRCA A2 | RE2-TT | 90/90 | 7 | 10 | 0 | 0 | 73 | valid; 4 workers |
| MicroCause A1 | RE2-OB | 90/90 | 87 | 1 | 0 | 2 | 0 | absent; retained |
| MicroCause A1 | RE2-TT | 10/90 | 0 | 0 | 0 | 0 | 10 | absent; retained |
| MicroCause A2 | RE2-OB | 90/90 | 87 | 1 | 0 | 2 | 0 | valid; 4 workers |
| MicroCause A2 | RE2-TT | 90/90 | 0 | 7 | 0 | 0 | 83 | valid; 4 workers |
| MicroRank A1 | RE2-OB | 59/90 | 59 | 0 | 0 | 0 | 0 | absent; retained |
| MicroRank A1 | RE2-TT | 0/90 | 0 | 0 | 0 | 0 | 0 | absent; retain |
| MicroRank A2 | RE2-OB | 90/90 | 90 | 0 | 0 | 0 | 0 | valid |
| MicroRank A2 | RE2-TT | 90/90 | 75 | 15 | 0 | 0 | 0 | valid |
| TraceRCA A1 | RE2-OB | 59/90 | 59 | 0 | 0 | 0 | 0 | absent; retain |
| TraceRCA A1 | RE2-TT | 0/90 | 0 | 0 | 0 | 0 | 0 | absent; retain |
| TraceRCA A2 | RE2-OB | 90/90 | 90 | 0 | 0 | 0 | 0 | valid centrally |
| TraceRCA A2 | RE2-TT | 90/90 | 75 | 15 | 0 | 0 | 0 | valid centrally |
| mmBARO A1 | RE2-OB | 59/90 | 57 | 0 | 0 | 2 | 0 | absent; retain |
| mmBARO A1 | RE2-TT | 0/90 | 0 | 0 | 0 | 0 | 0 | absent; retain |
| mmBARO A2 | RE2-OB | 90/90 | 88 | 0 | 0 | 2 | 0 | valid centrally |
| mmBARO A2 | RE2-TT | 90/90 | 89 | 1 | 0 | 0 | 0 | valid centrally |
| CausalRCA CPU extension | RE2-OB | 90/90 | 90 | 0 | 0 | 0 | 0 | valid; 20 workers |
| CausalRCA CPU extension | RE2-TT | 90/90 | 90 | 0 | 0 | 0 | 0 | valid; 20 workers |

V2 rescue coverage, recorded without prediction inspection, is:

| Method | Dataset | Records | SUCCESS | METHOD_FAILURE | Blocking statuses | Active method lock |
|---|---|---:|---:|---:|---|---|
| CIRCA | RE2-OB | 90/90 | 86 | 4 | none | valid; reissued V2 sidecar |
| CIRCA | RE2-TT | 90/90 | 80 | 10 | none | valid; reissued V2 sidecar |
| MicroCause | RE2-OB | 90/90 | 89 | 1 | none | valid |
| MicroCause | RE2-TT | 90/90 | 83 | 7 | none | valid |
| MicroRank | RE2-OB | 90/90 | 90 | 0 | none | corrected V2 sidecar verified |
| MicroRank | RE2-TT | 90/90 | 75 | 15 | none | corrected V2 sidecar verified |
| TraceRCA | RE2-OB | 90/90 | 90 | 0 | none | corrected V2 sidecar verified |
| TraceRCA | RE2-TT | 90/90 | 75 | 15 | none | corrected V2 sidecar verified |
| mmBARO | RE2-OB | 90/90 | 90 | 0 | none | corrected V2 sidecar verified |
| mmBARO | RE2-TT | 90/90 | 89 | 1 | none | corrected V2 sidecar verified |
| CausalRCA CPU extension | RE2-OB | 90/90 | 90 | 0 | none | valid; CPU extension lock |
| CausalRCA CPU extension | RE2-TT | 90/90 | 90 | 0 | none | valid; CPU extension lock |

The original invalid locks for CIRCA, MicroRank, TraceRCA, and mmBARO printed
`INTEGRITY_INVALID` because
their first V2 lock used the defective outer-dictionary truthiness check. Their
original locks remain unchanged; the corrected V2 sidecars were verified against
the same 180 records and runtime summaries. CIRCA's corrected sidecar was
created after its completed attempt was integrated. These are lock-attestation
repairs, not method reruns.

BARO lock verification: `EXECUTION_COMPLETE`, 180 terminal record digests,
both 90-case denominators valid, environment unchanged.

CIRCA, MicroCause, MicroRank, TraceRCA, mmBARO, and CausalRCA V2 evidence are
now committed centrally. All six active method locks pass
`verify-method-lock`; no runner process was observed at the latest audit.

## 6. Current blockers and decisions required

### B1. External A1 stop/archive — resolved

The user stopped both external A1 runners. CIRCA A1 is preserved in `ee98d7f`
and MicroCause A1 in `95dd037`. V1.3 and the preflight repair are merged into
the same path-bound worktrees. Their exact global and environment preflights
pass, so each A2 may now start from case 1 with exactly `--workers 4`. Never
resume either A1 and never overlap two top-level runners for the same method.

### B2. `.gitignore` decision — resolved

The user accepted the current no-final-newline state. It does not ignore the
execution artifact tree. Future ignore rules may be added selectively only for
non-evidence files; terminal records, locks, manifests, and execution logs must
remain visible to Git and the integrity workflow.

### B3. CausalRCA disposition — restored by explicit user authorization

On 2026-09-03 the user explicitly restored CausalRCA and authorized the CPU
case-level parallel protocol. The additive extension is bound to
`RCA_BASELINE_CAUSALRCA_CPU_CASE_PARALLELISM_AMENDMENT_V1.md` and machine
readable digest
`fe46fc498507370563452aa3b31fa65938f5a23c6850586a22afcafa0787551b`.
It uses the common Python environment, hides CUDA, preserves the pinned
`RCAEval/e2e/causalrca.py`, and isolates every case in a fresh child process.
The saved GPU branch `wip/causalrca-gpu-amendment` at `89db7ec` remains
separate and is not used. The CPU extension completed 180/180 cases with a
valid method lock and no blocking terminal statuses.

### B4. Cross-method concurrency — authorized

The user explicitly authorized different baselines to run concurrently in
separate task containers provided their experiment data cannot interfere. The
committed V1.1 amendment provides method-scoped environment, record, lock, and
branch ownership. Because containers share the filesystem, the coordinator
must pre-create one linked Git worktree and unique branch per method; two
containers must never use the same path. The harness stores per-method process
locks below the shared Git common directory rather than container-local
`/tmp`. Registry order is reporting order only. Each container must still have
adequate CPU and memory; reduce task concurrency if the platform does not
isolate physical resources.

### B5. Raw-trace native parser crash — repaired; A2 required

TraceRCA and mmBARO A1 deterministically stopped after 59 records on
`re2ob-f30e2feeaa5218b8`. Both child workers exited on signal 11 inside Pandas
2.3.3's C CSV parser while loading the valid raw trace source. The same file
has 365,484 rows and 11 fields per row and loads with Pandas' Python engine.

V1.2 limits the repair to `pandas.read_csv(..., engine="python")` for the
logical `traces` role. The package environment and all scientific semantics
remain unchanged. TraceRCA and mmBARO A1 must be archived and never resumed;
MicroRank A1 is also restarted prospectively because it shares the loader and
one attempt cannot mix execution commits. Authorized IDs are
`microrank-a2-20260901`, `tracerca-a2-20260901`, and
`mmbaro-a2-20260901`.

Central repair commit `f072c2a` passed 193 tests and global preflight. A1
evidence commits are `3c4c0d5` plus `8b1a15f` (MicroRank 59 records),
`37e288e` (TraceRCA 59 records), and `414140c` (mmBARO 59 records). Repair
cherry-picks are `2a66e75`, `65878d8`, and `7650588`, respectively.

The original MicroRank failure is now confirmed at the same opaque case and
same C-parser signal-11 path. A performance-blind repaired execution of that
full case reached `SUCCESS`; the A1 tail is committed, the task worktree is
clean, and both global and environment preflights pass. MicroRank A2 may start.
MicroCause does not load the raw `traces` role; all 180 frozen
`simple_metrics` CSVs loaded successfully with its isolated environment, so
its active A1 is not restarted for V1.2.
TraceRCA A2 commit `c7c8265` and mmBARO A2 commit `643cde4` each contain 180
terminal records and a method lock that passes `verify_method_lock`; their
method-scoped commits are now integrated centrally.

### B6. Central method-result integration — resolved

All five base V2 method tracks plus the authorized CausalRCA CPU extension are
present on `evaluation/rcaeval-baselines` with frozen environment manifests,
complete records, runtime summaries, and method locks. CIRCA, MicroCause,
MicroRank, TraceRCA, and mmBARO use the base V2 execution root; CausalRCA uses
its separate CPU-extension root. The merge did not touch the user method's
`src/rca` or `artifacts/p6_*` paths. All five base V2 locks and the independent
CausalRCA extension lock verify centrally.

### B7. V2 post-launch rescue state — complete; six-method evaluation published

- CIRCA, MicroCause, MicroRank, TraceRCA, and mmBARO each have 180/180
  terminal records, no blocking terminal statuses, and a centrally verified
  active method lock. CIRCA's valid lock is the immutable
  `circa_prediction_lock_reissued_v2.json` sidecar; its original invalid lock
  remains preserved.
- CausalRCA has 180/180 CPU case-level records, no blocking terminal statuses,
  and a valid independent extension lock. Its run used 20 requested/actual
  workers, as recorded in the lock; no rerun is authorized or needed.
- The independent method locks and the additive six-method combined global
  prediction lock are complete. The lock is committed as `2778c64` at
  `execution_v2/prediction_lock_v2_causalrca.json`; it records
  `labels_joined=false` and `contains_evaluation=false` before the post-lock
  stage. Committed-lock verification and the performance firewall passed.
- Post-lock evaluation joined labels only after the combined lock and completed
  as `8da9b44`; the five JSON tables are under
  `execution_v2/evaluation_causalrca/`. The final Markdown table, including
  CausalRCA, is committed as `c990c0e` at
  `docs/baseline_eval/RCA_BASELINE_CONFIRMATORY_RESULTS_V2.md`.

### B8 — Final composite V3 comparison — complete

- Scope completeness was frozen before any BARO label join in commit
  `bf6349e342fa2e1ffbb1348bccbf852821503bec`. The amendment is
  `docs/baseline_eval/RCA_BASELINE_BARO_FINAL_INTEGRATION_AMENDMENT_V1.md`,
  its machine-readable companion is
  `artifacts/baseline_eval/baro_final_integration_amendment_v1.json`, and the
  committed gate is `artifacts/baseline_eval/final_comparison_v3/scope_lock_v3.json`.
- The decision was scope completeness: BARO was already an original RCAEval
  confirmatory baseline with a complete V1 label-free prediction lock, and
  V2 rescue did not rerun a method that was already complete. BARO metrics were
  not inspected before the scope freeze; six-method performance was not used
  to decide inclusion.
- BARO V1 audit passed: `EXECUTION_COMPLETE`, `contains_evaluation=false`,
  90/90 records on both RE2-OB and RE2-TT, 90 `SUCCESS` on each dataset, no
  `METHOD_FAILURE`, `DATA_FAILURE`, `ADAPTER_FAILURE`, or `TIMEOUT`, exact
  record digests, environment/input/RCAEval identities, and exact frozen case
  universes. Its historical environment is bound by the lock/manifest digest;
  live environment re-resolution is not required for inherited evidence.
- The final set is exactly `BARO`, `CIRCA`, `MicroCause`, `MicroRank`,
  `TraceRCA`, `mmBARO`, and `CausalRCA`; Ada-RCA remains the separate user
  method. RE2-OB and RE2-TT remain separate and are never pooled. Baseline MRR
  remains `NOT-IDENTIFIABLE`, with no candidate completion.
- V3 outputs are under
  `artifacts/baseline_eval/final_comparison_v3/`: `scope_lock_v3.json`,
  `provenance_v3.json`, `overall_v3.json`, `fault_level_v3.json`,
  `robustness_v3.json`, `comparability_v3.json`, and
  `paired_bootstrap_v3.json`. Only BARO rows were newly evaluated; the six
  inherited baseline rows are copied from the immutable V2 JSON files with
  exact identity assertions, and frozen Ada-RCA identity is asserted.
- The final comparison is explicitly
  `FINAL_COMPOSITE_SEVEN_BASELINE_COMPARISON`, not
  `SEVEN_METHOD_ORIGINAL_PRELABEL_GLOBAL_LOCK`. BARO is V1 locked complete;
  CIRCA/MicroCause/MicroRank/TraceRCA/mmBARO are V2 rescue evidence; and
  CausalRCA is the V2 CPU additive extension. No BARO rerun, six-baseline
  rerun, Ada-RCA retraining, algorithm change, adapter search, or candidate
  completion occurred.
- The canonical current report is
  `docs/baseline_eval/RCA_BASELINE_FINAL_COMPARISON_V3.md`. The prior
  `RCA_BASELINE_CONFIRMATORY_RESULTS_V2.md` remains the historical immutable
  six-method V2 report.
- Focused V3 regression tests passed `15/15`. The full common-environment
  unittest suite passed `262 tests` with `failed=0`, `skipped=0` in 94.716 s;
  the independent `pytest -q` run passed `262` tests in 38.40 s. The five
  historical V2 evaluation JSON SHA-256 identity checks also passed.

### B9 — Independent post-lock audit — complete

- The pinned RCAEval checkout was revalidated read-only at commit
  `5e96b700445bfb5c599e505ecf37d53bf847bbeb`; the checkout is clean. The
  input manifest and active BARO/V2 combined locks are bound in
  `artifacts/baseline_eval/audit_fix_v1/provenance_audit.json`.
- The audit covers all seven baseline methods on both datasets. Every selected
  method/dataset has exactly 90 discovered records and 90 terminal records;
  there are no missing, duplicate, foreign, or blocking records. Existing
  `METHOD_FAILURE` records remain in the 90-case denominator and have zero
  utility. Historical records and locks were not modified.
- The existing fault-level evaluation source was independently checked without
  writing a new performance artifact: all 84 baseline method/dataset/fault
  rows (7 x 2 x 6) contain 15 cases, and their stored AC@1/3/5 and Avg@5
  values exactly equal the case-micro `unique_service` recomputation. This is
  a consistency check only; fault-level, seed, group, batch, successful-only,
  partial-denominator, and duplicate aggregation are not used for the main
  table.
- The dual evaluator was frozen before the final comparison: `unique_service`
  retains the current alias/longest-prefix/first-occurrence adapter behavior;
  `rcaeval_service_slot` follows pinned native entity projection and the
  pinned `Evaluator`'s non-deduplicated slot Top-K behavior. The old 14 metric
  rows equal the fresh `unique_service` raw-hit recomputation; both protocols
  are published without performance-based selection. CausalRCA's full slot
  and unique rankings differ because slot projection retains native duplicates,
  although their frozen K=1..5 root-hit counts happen to match.
- Static method-source review confirmed the pinned BARO/mmBARO, CIRCA,
  MicroCause, MicroRank, and TraceRCA paths and their failure counts. CIRCA's
  pinned TT `dataset="ob"` argument is recorded as upstream behavior, not a
  local repair. MicroRank's `top_max + 6` native cap and case-level examples
  are recorded in `microrank_static_audit.json`.
- CausalRCA's persisted service ranking is fixed within each dataset despite
  69 (OB) and 80 (TT) unique native ranking digests; its adapted digest is
  unique within each dataset. The resulting OB positions explain the exact
  `0/90, 0/90, 18/90, 36/90, 54/90` hits, while all TT roots are outside
  Top-5. The pinned source has broad PageRank and wrapper `except Exception`
  fallbacks, but the frozen records retain neither the runtime exception nor
  adjacency, so the exact historical trigger remains unknown.
- Codex prepared a five-root-diverse-case-per-dataset diagnostic runner and
  schema. It has not been run. A manual diagnostic is the next evidence step;
  any repaired full CausalRCA result requires a new authorized attempt and
  isolated output, never a resume or overwrite of the CPU lock.

## 7. Historical V1 plan and completed V2 replacement

MicroCause, MicroRank, TraceRCA, and mmBARO were independent worker tracks.
CIRCA recovery was a fifth independent legacy track. All five tracks are now
integrated and centrally verified for V1. The P0–P8 entries below are retained
as historical V1 handoff evidence and are not instructions to resume A1/A2 or
to create a V1 lock.

### V2 execution/evaluation plan (completed historical state)

- V2.1 protocol and adapter amendment are frozen; digest is
  `dbba81fae2b879bc77084bd6cc07c207c4a9f30dc5a286eb6b1533b0144429de`.
- V2 code and tests are integrated through the method worktree merge commits;
  the command-aligned runbook is
  synchronized by `596f68b` at `docs/baseline_eval/RCA_BASELINE_RESCUE_RUNBOOK_V2.md`.
- CIRCA, MicroCause, MicroRank, TraceRCA, mmBARO, and CausalRCA now each have
  a frozen environment, 180 terminal records, runtime summary, and an active
  centrally verified method lock. Their legacy `execution/*-a1-*` worktrees
  remain historical and are not execution targets.
- The original five-method V2 lock set and the CausalRCA CPU extension lock
  remain separate. All six active locks are integrity-valid and contain no
  blocking terminal statuses; METHOD_FAILURE remains a legal zero-utility
  robustness observation.
- The additive six-method combined V2 prediction lock is committed at
  `artifacts/baseline_eval/execution_v2/prediction_lock_v2_causalrca.json`.
  The combined protocol is
  `artifacts/baseline_eval/rescue_protocol_v2_causalrca_combined.json` with
  digest `24419f179d44ee09f082a23173a0d35c5ec2d3d5592cd93ff9a2afe1d0591e54`.
  Labels and metrics were read only after that lock; no method was rerun.

### P0 — Resolve repository transition readiness

- Completed: user accepted the `.gitignore` byte state; CIRCA evidence remains
  unignored and preserved.
- Completed: branch, protocol bundle, input manifest, Ada-RCA frozen paths, and
  clean pinned RCAEval checkout passed their preflights.
- Completed: the current full suite passed all 203 tests.
- Completed: both A1 attempts are archived and both A2 worktrees contain the
  same central repair commit.

### P0A — Finish performance-blind later-adapter hardening

- Completed in `0d0efcf`: structural graph-output validation for MicroCause
  and the other graph methods without changing native algorithms or ranking
  semantics.
- Completed in `0d0efcf`: real-input schema/type checks so pre-invocation
  malformed telemetry is consistently classified as `DATA_FAILURE`.
- Add symmetric deterministic synthetic tests for MicroCause, TraceRCA, and
  mmBARO where their method-specific environments permit it.
- Keep this work synthetic/schema-only; do not schedule a real later-method
  case and do not alter the frozen CIRCA attempt.

### P1 — Stop/archive CIRCA A1, then execute four-worker A2

- Completed: A1 stopped and its 117 terminal records are committed without a
  method lock; V1.3 and `c1c7a96` are merged into the same worktree.
- Completed: both preflights pass against the unchanged CIRCA environment.
- Completed: central integration as `d6ca33f` (A1) and `5a49b58` (A2).
- The A2 lock verifies 180 records, the runtime summary, and four-worker
  provenance.

### P2 — Stop/archive MicroCause A1, then execute four-worker A2

- Completed: A1 stopped and its 100 terminal records are committed without a
  method lock; V1.3 and `c1c7a96` are merged into the same worktree.
- Completed: both preflights pass against the unchanged MicroCause environment;
  the two-run synthetic fingerprint is unchanged.
- Completed: central integration as `9d2db42` (A1) and `60a0b87` (A2).
- The A2 lock verifies 180 records, the runtime summary, and four-worker
  provenance.

### P3 — Archive MicroRank A1, execute repaired A2, and lock

- A1 is completely archived by `3c4c0d5` plus `8b1a15f`; never resume it.
- V1.2 is integrated as `2a66e75`, the environment is unchanged, and both
  preflights pass.
- Completed: central integration as `f634745` (environment), `865cbdb` and
  `9ead45b` (A1), and `6136ba4` (A2); method lock verifies centrally.

### P4 — Archive TraceRCA A1, execute repaired A2, and lock

- A1 remains immutable evidence and must not be resumed.
- A2 is complete and method-locked in task commit `c7c8265`; preserve raw
  trace microseconds, span-end filtering, and `t0*1_000_000`.
- Completed: central integration as `8ef492e` (environment), `cbb4404` (A1),
  and `0c4d9a3` (A2).

### P5 — Archive mmBARO A1, execute repaired A2, and lock

- A1 remains immutable evidence and must not be resumed.
- A2 is complete and method-locked in task commit `643cde4`; preserve the
  official `mm-ob` / `mm-tt` keys and frozen modality-specific preprocessing.
- Completed: central integration as `9719386` (environment), `2b147cc` (A1),
  and `db78094` (A2).

### P6 — Historical CausalRCA cancellation (superseded)

- The 2026-08-31 cancellation remains historical evidence only.
- It is superseded for the current work by the explicit 2026-09-03 CPU
  extension authorization recorded in B3.
- The saved GPU branch remains non-executed context; it must not be reused for
  the CPU track.

### P7 — Six-method combined global prediction lock — complete

- Complete: all five base V2 method environments and prediction commits are
  integrated; worker-owned paths remain disjoint and all five active locks
  verify. The CausalRCA CPU extension is also integrated under its separate
  execution root and lock.
- Complete: the additive combined-lock amendment is recorded and explicitly
  authorized by the user. The six-method lock was created and committed as
  `2778c64`, and committed-lock verification plus the performance firewall
  passed.
- Complete: the committed combined lock was the gate for the label join and
  metric computation; no method rerun occurred.

### P8 — Post-lock evaluation and reporting — complete

- Join labels only after the committed global prediction lock.
- Never rerun a baseline during evaluation.
- Keep every failure in the 90-case dataset denominator with zero top-k utility.
- Report AC@1, AC@3, AC@5, and Avg@5; baseline MRR remains
  `NOT-IDENTIFIABLE`.
- Complete: generated the six-method overall, fault-level, robustness,
  comparability, and paired-bootstrap tables under
  `execution_v2/evaluation_causalrca/` in `8da9b44`, then published and
  refreshed `RCA_BASELINE_CONFIRMATORY_RESULTS_V2.md` in `c990c0e` (renderer
  clarification in `ce673c9`). The full suite passed `247` tests; the
  performance firewall and committed combined-lock audit pass.
- Commit evaluation and reporting separately.
- Update this document with final artifact paths, commits, tests, push state,
  limitations, and final decision.

## 8. Safe new-session audit commands

Run these before taking action in a new conversation:

```bash
git status --short --branch
git log --oneline -12
git -C /home/zhangll24/RCA_project/RCAEval-clean status --short --branch
git -C /home/zhangll24/RCA_project/RCAEval-clean rev-parse HEAD
find artifacts/baseline_eval/execution_v1/environments -maxdepth 1 -type f -printf '%f\n' | sort
find artifacts/baseline_eval/execution_v1/locks -maxdepth 1 -type f -printf '%f\n' | sort
ps -eo pid,etimes,cmd | rg 'run_baseline_confirmatory|baseline_eval.server|baseline_eval.worker'
tmux list-sessions
```

Record inspection during B2-E/B2-L must select only opaque identity, terminal
status, lengths, counts, runtimes, and digests. Never print native/adapted
ranking contents or join labels while auditing progress.

## 9. Mandatory end-of-task synchronization

After every completed task:

1. update the state revision and audit date at the top of this file;
2. update repository/environment state if it changed;
3. update the execution coverage and lock status using operational fields only;
4. mark completed plan items and rewrite the immediate next action;
5. record new artifact paths, test results, commit subjects, and push state;
6. run `git diff --check` on edited files;
7. include this document in the task's logical commit, or make an immediate
   follow-up documentation commit; and
8. push the branch when the active workflow authorizes pushing.

If a task is purely diagnostic and changes no repository or execution state,
update this document only when the diagnosis changes a blocker, decision, or
next action. Do not add prediction contents, labels, ranks, or pre-lock metrics
to this handoff.

## 10. V2 rescue transition (historical checkpoint)

The V2.1 performance-blind execution-rescue protocol and machine-readable
freeze extend the original V2 transition in `2c14e63`. At that historical
checkpoint, the V2.1 protocol digest was
`dbba81fae2b879bc77084bd6cc07c207c4a9f30dc5a286eb6b1533b0144429de`. It
authorizes only CIRCA, MicroCause, MicroRank, TraceRCA, and mmBARO, with new
method-scoped `*-a3-rescue-v2` attempts under `execution_v2/`. It cancels no
historical evidence, changes no Ada-RCA or RCAEval source, and did not yet
create or authorize a V2 global lock. The V2.1 role-level mmBARO audit found that
both historical OB source bundles match the frozen manifest; only the metric
adapter's non-finite timestamp validation failed. The pre-registered repair
drops existing numeric non-finite timestamp rows by one fixed label-free rule
before the canonical window. The diagnostic artifacts are
`execution_v2/diagnostics/mmbaro_input_v2.json` and
`execution_v2/diagnostics/operation_sets_v2.json`; the latter confirms equal
15-case KeyError sets for MicroRank/TraceRCA and retains native trace/SLO
semantics.

At that historical checkpoint, V2 real-case execution was partially complete in
the isolated task worktrees.
The current central implementation/test HEAD before this handoff update is
`6b7635a`; the focused rescue/evaluator suite passed `81` tests and the full
repository suite passed `241` tests after the no-timeout and lock-validity
corrections. V2 supports requested workers
`1, 4, 10, 20`, caps actual workers by container CPU availability, sets one
thread for the audited numeric libraries, uses `timeout_seconds=null`, and
resumes only missing terminal records. MicroCause's synthetic preflight now
passes with no timeout and its environment is frozen. MicroRank, TraceRCA, and
mmBARO have complete integrity-valid corrected sidecars despite their original
invalid lock attestations. The subsequent execution, combined-lock, and
evaluation state is maintained in the current sections above.
