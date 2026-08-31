# INIT-ACC-001 — S10-R2 Wave 2 / Project Pulse Reconciliation

Status: RECONCILED_VALIDATED
Authority: DERIVED_NON_AUTHORITATIVE implementation evidence
Read model: RM-COI-001 — Corporate Operating Snapshot
Lifecycle: OPERATING / S10 — Operation, Support, Maintenance & Warranty / G10 OPEN
Reconciled: 2026-08-30

## Trigger

RM-COI-001 entered `REVIEW_REQUIRED` after portfolio identity reconciliation Wave 2 (`DEC-ADM-009`). `DEC-ADM-010` subsequently corrected the Project Pulse clause and established that Project Pulse is not an independently canonical initiative/product. It is an `APPLICATION_COMPONENT` embedded in Powerful Brain with normalized identity `powerful-brain/project-pulse`.

Current governed registry state used for this reconciliation:

- Project Pulse: `Portfolio Object Type=APPLICATION_COMPONENT`
- `Normalized Object ID=powerful-brain/project-pulse`
- `Reconciliation Status=MAPPED`
- `Authority State=CURRENT`
- no independent lifecycle stage/gate/canonical lifecycle state

## Defect corrected

`tools/coi_coverage.py::build_portfolio_coverage` previously treated every lifecycle-registry row that was not a fully comparable `INITIATIVE` as `non_comparable`.

That conflated:

1. unresolved/stale/unmapped/authority-uncertain portfolio identity, which must remain fail-closed; and
2. a correctly governed non-initiative object intentionally outside initiative lifecycle progression.

The corrected projection now:

- compares only rows explicitly classified as `INITIATIVE`;
- excludes a non-initiative row from initiative comparability only when it has an explicit non-empty object type and is both `MAPPED` and `CURRENT`;
- records those rows in `excluded_non_initiative_row_count`;
- continues counting unresolved, stale, unmapped, authority-uncertain, or incomplete initiative rows as `non_comparable`;
- keeps `PORTFOLIO_POPULATION_NOT_FULLY_COMPARABLE` and disables global comparison while those rows remain.

## Regression protection

`validators/validate_coi_project_pulse_component.py` is wired into `scripts/validate-local.sh` and asserts that:

- Project Pulse as `APPLICATION_COMPONENT / powerful-brain/project-pulse` does not enter the initiative lifecycle population;
- the governed component does not disable otherwise valid initiative comparison merely because it is non-initiative;
- `excluded_non_initiative_row_count` preserves the exclusion explicitly;
- a true unresolved/stale/unmapped identity still disables global comparison and remains fail-closed.

## Validation evidence

Full local gate executed successfully on 2026-08-30:

- `validators.validate_coi_source_mapping` — PASS
- `validators.validate_coi_readers` — PASS
- `validators.validate_coi_materialized_snapshot` — PASS
- `validators.validate_coi_consumers` — PASS
- `validators.validate_coi_operability` — PASS
- `validators.validate_coi_coverage` — PASS
- `validators.validate_coi_project_pulse_component` — PASS
- `validators.validate_coi_portfolio_reconciliation` — PASS
- result: `8/8 validation modules completed successfully`

GitHub Actions are not required for this gate. The correction was merged through PR #17; merge commit: `60ae05f5e9327b2c8fc23a4e18a76dd0b01abc57`.

## Live source reconciliation

Live governed-source readback on 2026-08-30 confirmed:

- 5 `CURRENT + MAPPED + INITIATIVE` rows are comparable;
- 34 rows remain non-comparable / reconciliation-required;
- 1 governed non-initiative row is explicitly excluded from initiative progression: Project Pulse;
- global initiative comparison remains unsupported while unresolved identities remain;
- `DEC-ADM-009` and scoped superseding correction `DEC-ADM-010` are `ACCEPTED / REGISTRY_AUTHORITY`;
- Project Pulse remains `APPLICATION_COMPONENT / powerful-brain/project-pulse` with no independent lifecycle authority.

`RM-COI-001` was therefore reconciled from `REVIEW_REQUIRED` to `FRESH` as-of 2026-08-30 while preserving `DERIVED_NON_AUTHORITATIVE` authority and `PARTIAL` portfolio coverage semantics. Freshness does not imply full portfolio comparability.

Drive evidence: `EVD-2026-0063`.

## Scope boundary

This reconciliation does not:

- infer a lifecycle for Project Pulse;
- promote Project Pulse to initiative/product authority;
- resolve the remaining non-comparable portfolio identities;
- enable global initiative ranking;
- change INIT-ACC-001 lifecycle, S10, or G10;
- introduce ETA/value/priority/success inference;
- open S11/G11.

## Final disposition

- `INIT-ACC-001`: `OPERATING`
- stage: `S10 — Operation, Support, Maintenance & Warranty`
- gate: `G10 OPEN`
- `RM-COI-001`: `FRESH / CURRENT / KEEP_CURRENT`
- portfolio coverage: `PARTIAL`
- global comparison: disabled until remaining portfolio identity reconciliation converges
