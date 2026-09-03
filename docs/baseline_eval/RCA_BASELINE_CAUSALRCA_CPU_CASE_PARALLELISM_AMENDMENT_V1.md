# CausalRCA CPU Case-Level Parallelism Amendment V1

Status: **USER-AUTHORIZED ADDITIVE V2 EXECUTION EXTENSION**<br>
Date: 2026-09-03<br>
Base protocol: `RCA_BASELINE_RESCUE_PROTOCOL_V2`<br>
Base protocol digest:
`dbba81fae2b879bc77084bd6cc07c207c4a9f30dc5a286eb6b1533b0144429de`

## Scope

The user has restored CausalRCA to the confirmatory baseline scope and
authorized CPU case-level parallelism. This amendment adds one isolated
CausalRCA execution track. It does not rewrite the frozen five-method V2
protocol, change any existing five-method record or lock, or reuse the saved
GPU amendment.

The machine-readable binding is
`artifacts/baseline_eval/rescue_protocol_v2_causalrca_cpu.json`. The extension
digest is the SHA-256 of that file and is carried by every CausalRCA V2
environment, attempt, record, runtime summary, and method lock. The base V2
digest remains bound as the parent protocol digest.

## Frozen native and input contract

- Use the pinned RCAEval checkout at commit
  `5e96b700445bfb5c599e505ecf37d53bf847bbeb`.
- Invoke the untouched
  `RCAEval/e2e/causalrca.py::causalrca` source; its source digest is
  `74aebfb9f8211db3a48385a73ae577e9673a432d719f859771bbf66dc2a008f0`.
- Use the frozen RE2-OB and RE2-TT input manifest and its existing
  label-independent adapter.
- Cover exactly 90 opaque cases per dataset in the canonical `re2ob` then
  `re2tt` order.
- Preserve seed `20260830`, Torch deterministic algorithms, and the existing
  CausalRCA empty-graph failure detector. No native parameter, preprocessing,
  ranking, candidate, or service-projection change is authorized.

## CPU case-level execution contract

- Set `CUDA_VISIBLE_DEVICES=""`; a visible CUDA device is an environment
  failure. The saved `wip/causalrca-gpu-amendment` branch is not used.
- A requested worker count may be `1`, `4`, `10`, or `20`; actual workers are
  `min(requested_workers, available_cpu_count)`.
- The scheduler creates deterministic round-robin case shards. Each slot
  processes its assigned cases serially, and every case runs in a fresh child
  process. No model or optimizer state is shared across cases.
- Cap OMP, MKL, OpenBLAS, NumExpr, and Torch intra-case threads at one. This is
  outer case parallelism, not native algorithm modification.
- Real execution is explicitly no-timeout, has no automatic retry, and keeps
  all terminal failure records. A container may still be stopped externally;
  a later resume may schedule missing records only with the same commit,
  environment, and worker configuration.

## Determinism and lock gates

Before a real run, the task container must pass the synthetic environment
preflight and the existing opaque determinism preflight at the selected
worker-count configurations. Any status or native/adapted output-digest
mismatch is a stop condition. The preflight is label-free and never creates a
prediction lock.

The CausalRCA method lock is written only after all 180 terminal records and
the runtime summary are present and validated. It remains a separate
method-scoped lock until the central coordinator explicitly creates a later
combined global lock. Labels, metrics, and ranking contents remain behind the
global prediction-lock firewall.

Final decision: `CAUSALRCA_CPU_CASE_LEVEL_PARALLELISM_AUTHORIZED_V1`.
