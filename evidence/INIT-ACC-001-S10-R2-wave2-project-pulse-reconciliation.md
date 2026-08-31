# INIT-ACC-001 — S10-R2 Wave 2 / Project Pulse Reconciliation

Status: IMPLEMENTED_PENDING_LOCAL_VALIDATION
Authority: DERIVED_NON_AUTHORITATIVE implementation evidence
Read model: RM-COI-001 — Corporate Operating Snapshot
Lifecycle: OPERATING / S10 — Operation, Support, Maintenance & Warranty / G10 OPEN

## Trigger

RM-COI-001 entered `REVIEW_REQUIRED` after portfolio identity reconciliation Wave 2 (`DEC-ADM-009`). `DEC-ADM-010` subsequently corrected the Project Pulse clause and established that Project Pulse is not an independently canonical initiative/product. It is an `APPLICATION_COMPONENT` embedded in Powerful Brain with normalized identity `powerful-brain/project-pulse`.

Current governed registry observation used for this implementation:

- Project Pulse: `Portfolio Object Type=APPLICATION_COMPONENT`
- `Normalized Object ID=powerful-brain/project-pulse`
- `Reconciliation Status=MAPPED`
- `Authority State=CURRENT`
- no independent lifecycle stage/gate/canonical lifecycle state

## Defect found

`tools/coi_coverage.py::build_portfolio_coverage` treated every lifecycle-registry row that was not a fully comparable `INITIATIVE` as `non_comparable`.

That behavior conflated two different conditions:

1. an unresolved/stale/unmapped/authority-uncertain portfolio identity, which must continue to fail closed; and
2. a correctly governed non-initiative object (for example `APPLICATION_COMPONENT`) that is intentionally outside initiative lifecycle progression.

Under DEC-ADM-010, the second condition made Project Pulse incorrectly degrade global initiative comparability even though the registry classification was correct.

## Implemented correction

The coverage projection now:

- compares only rows explicitly classified as `INITIATIVE`;
- excludes a non-initiative row from initiative comparability only when it has an explicit non-empty object type and is both `MAPPED` and `CURRENT`;
- records those rows in `excluded_non_initiative_row_count` for observability;
- continues counting `UNRESOLVED`, stale, unmapped, authority-uncertain, or incomplete initiative rows as `non_comparable`;
- preserves `PORTFOLIO_POPULATION_NOT_FULLY_COMPARABLE` and disables global comparison whenever such unresolved/non-comparable rows remain.

## Regression protection

Added `validators/validate_coi_project_pulse_component.py` and wired it into `scripts/validate-local.sh`.

The regression fixture asserts:

- Project Pulse as `APPLICATION_COMPONENT / powerful-brain/project-pulse` does not enter the initiative lifecycle population;
- that governed component does not disable otherwise valid initiative comparison;
- `excluded_non_initiative_row_count` preserves the exclusion explicitly;
- a true `UNRESOLVED` row still disables global comparison and remains fail-closed.

## Scope boundary

This change does not:

- mutate REG-INIT-LIFECYCLE-001, REG-DEC-001, REG-RM-001, or RM-COI-001;
- infer a lifecycle for Project Pulse;
- promote Project Pulse to initiative/product authority;
- change INIT-ACC-001 lifecycle, S10, or G10;
- introduce ETA/value/priority/success inference;
- open S11/G11.

## Validation state

Repository changes are committed on `fix/coi-project-pulse-component-coverage`.

Full local gate execution (`scripts/validate-local.sh`) is still required before this implementation evidence can be promoted from `IMPLEMENTED_PENDING_LOCAL_VALIDATION` to accepted regeneration/reconciliation evidence and before RM-COI-001 can return from `REVIEW_REQUIRED` to `FRESH/CURRENT`.
