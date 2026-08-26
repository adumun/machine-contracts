# INIT-ACC-001 — S8 M2 Deterministic Readers Evidence

Status: CANDIDATE_M2_COMPLETION_EVIDENCE  
Date: 2026-08-26  
Scope: bounded deterministic read-only transformation only

## Implemented

- `tools/coi_readers.py`
- source acquisition intentionally remains outside the reader boundary
- input is a tabular JSON snapshot bundle plus explicit freshness/confidentiality metadata
- mapping authority is `mappings/corporate-operating-intelligence/source-fact-mapping.v1.yaml`
- outputs conform to M1 `ConcernRecord`, `MaterialAnswer` and `SourceEnvelope` contracts
- supported selectors: `LABEL_VALUE`, `TABLE_COLUMNS`
- supported transforms: exact string copy and formatted-integer normalization
- source failures fail closed as `UNAVAILABLE`
- per-fact transform/mapping defects make the affected record `RECONCILIATION_REQUIRED`
- no semantic inference, writeback, provider SDK, database or hosted runtime

## Reproducible synthetic validation

Command after checkout:

```bash
python validators/validate_coi_readers.py
```

Expected invariant checks:

- all five bounded source families execute;
- generated records validate against M1 schemas;
- `-`/blank finance tokens remain `UNKNOWN` without `value`;
- lifecycle rows are restricted to `Portfolio Object Type = INITIATIVE`;
- structural rows are restricted to `BUSINESS_VERTICAL` / `CORPORATE_FUNCTION`;
- a missing source snapshot becomes `UNAVAILABLE` rather than a fabricated empty/current source;
- no GitHub Actions dependency.

## Current governed-source sample validation

The candidate reader logic was additionally exercised against current source samples obtained through the authorized Google Drive connector on 2026-08-26. Raw financial values are deliberately not copied into this public repository.

| Concern family | Governed source | Sample result |
|---|---|---|
| FH-CF-01 | RM-FUND-001 / Funding Dashboard | 1 concern record / 4 facts. Two unevidenced financial source tokens remained `UNKNOWN` with no `value`; no zero coercion. |
| FH-CF-02 | REG-INIT-LIFECYCLE-001 | Current `INIT-ACC-001` row emitted 4 facts preserving lifecycle state, stage, gate and gate outcome as separate concepts. |
| FH-CF-03 | REG-DEC-001 | Current decision rows emitted only `DECISION_STATUS` and `DECISION_AUTHORITY_MODE`; no decision meaning or approval authority was inferred. |
| FH-CF-04 | REG-STR-REC-001 | Business-vertical/corporate-function rows emitted ownership/reconciliation facts; initiative rows were excluded by the approved filter. |
| FH-CF-05 | REG-RM-001 | Read-model rows emitted freshness, authority mode, lifecycle and disposition facts without promoting projections to source authority. |

Schema validation of the representative real-source output produced zero M1 contract errors.

## Security / data handling

`adumun/machine-contracts` is public. Therefore current internal source snapshots and actual confidential financial values are not committed. The public fixture is synthetic; evidence records only transformation results/invariants. Source access remains governed by the original systems and authorized connector/tool boundary.

## M2 exit assessment

The M2 exit condition is satisfied by the candidate implementation if repository review confirms the retained code/fixture/validator as merged: selected governed source inputs can be transformed reproducibly without semantic inference, and unsupported/missing source conditions are explicit.

This milestone still does **not** authorize M3 materialized read-model publication before this change is merged and M2 evidence is registered canonically.
