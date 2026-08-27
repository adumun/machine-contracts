# INIT-ACC-001 — S8 M6-R2 Coverage Remediation

Status: CANDIDATE — LOCAL VALIDATION REQUIRED
Date: 2026-08-27
Authority: DEC-ACC-G7-001; EVD-2026-0051; Artifact 51

## Why this remediation exists

M6-R1 demonstrated safe real-use behavior over RM-COI-001 but exposed bounded coverage gaps:

1. portfolio comparison could not determine the globally most advanced initiative;
2. initiative validation detail did not expose the linked evidence/milestone inventory;
3. ETA / remaining-work was unsupported and must remain unsupported unless a governed authoritative source exists.

Direct registry inspection after M6-R1 showed that the portfolio-comparison gap is partly governance population, not reader failure: only rows explicitly classified as `Portfolio Object Type = INITIATIVE`, `Reconciliation Status = MAPPED`, with a normalized ID and current authority may be compared. Unresolved legacy/candidate rows must not be coerced into initiatives.

## Bounded implementation

M6-R2 adds a deterministic optional coverage enrichment over the existing RM-COI-001 snapshot:

- `tools/coi_coverage.py`
  - consumes externally acquired Lifecycle Registry and Evidence Registry row snapshots;
  - keeps source acquisition outside the deterministic projection layer;
  - admits only canonically classified `INITIATIVE` rows with `MAPPED` reconciliation and `CURRENT` authority to the comparable portfolio population;
  - retains non-comparable row count and explicitly marks global comparison unsupported while unresolved population exists;
  - derives only a bounded canonical-lifecycle progression rank and explicitly states that it is not business value, health, priority or success ranking;
  - builds exact initiative-linked evidence inventories from the Evidence Registry without semantic inference;
  - introduces no ETA/completion percentage.

- RM-COI-001 materialized snapshot contract permits optional `coverage` extension and bumps enriched instances to contract `1.2.0`.

- `tools/coi_consumers.py`
  - adds `portfolio` consumer;
  - adds `initiative-evidence <initiative_id>` consumer;
  - continues consuming RM-COI-001 only;
  - keeps consumer authority `DERIVED_NON_AUTHORITATIVE`.

- `validators/validate_coi_coverage.py`
  - proves unresolved portfolio rows prevent false global ranking;
  - proves only canonical `INITIATIVE` rows are comparable;
  - proves deterministic progression ordering;
  - proves unrelated Evidence Registry rows do not leak into an initiative inventory;
  - proves no ETA/completion semantics are invented.

- `scripts/validate-local.sh`
  - unified validation expands from 5 to 6 modules.

## Explicit non-scope

M6-R2 does not:

- reconcile the broader legacy portfolio;
- classify unresolved portfolio objects as initiatives;
- infer percent complete, remaining work or ETA;
- add a database, runtime, provider SDK, scheduled acquisition, visual UI, shared deployment, RBAC implementation, writeback or decision authority.

## Exit candidate

M6-R2 may PASS only after the exact branch/PR candidate passes `bash scripts/validate-local.sh` locally with all 6 validation modules successful. After merge, build a current private coverage bundle from the Lifecycle and Evidence registries, enrich RM-COI-001, and run a short M6-R3 operational trial.

G8 remains OPEN until that trial and the accumulated S8 evidence support a genuine release-candidate decision.
