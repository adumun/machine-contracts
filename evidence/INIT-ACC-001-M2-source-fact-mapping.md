# INIT-ACC-001 — S8 / M2 Source-to-Fact Mapping Evidence

Date: 2026-08-26
Scope: mapping baseline only; no readers/adapters implemented in this change.

## Canonical checkpoint
- DEC-ACC-G7-001 authorizes only the READ-MODEL / AGENT-FIRST first horizon.
- Artifact 43 is the pre-S8 reconciliation checkpoint.
- Artifact 44 / EVD-2026-0044 closes M1 Contract Baseline PASS.

## Exact selected first-horizon sources

| Concern family | Source | Selector baseline | Authority mode |
| --- | --- | --- | --- |
| FH-CF-01 Funding / Finance | RM-FUND-001 / Funding Dashboard | label/value rows in `Dashboard` | DERIVED_NON_AUTHORITATIVE |
| FH-CF-02 Initiative Lifecycle | REG-INIT-LIFECYCLE-001 | `Registry` rows where `Portfolio Object Type = INITIATIVE`, keyed by `Normalized Object ID` | REGISTRY_AUTHORITY |
| FH-CF-03 Enterprise Decisions | REG-DEC-001 | `Decision Registry`, keyed by `decision_id` | REGISTRY_AUTHORITY |
| FH-CF-04 Structural Ownership | REG-STR-REC-001 | `Structural Register`, `object_class in {BUSINESS_VERTICAL,CORPORATE_FUNCTION}`, keyed by `object_id` | REGISTRY_AUTHORITY |
| FH-CF-05 Source Health | REG-RM-001 | `Read Models`, keyed by `read_model_id` | REGISTRY_AUTHORITY |

## Source inspection
Direct source reads confirmed the mapped sheet/tab and field names exist as declared.

Funding Dashboard inspected labels include:
- `WHAT — Consolidated Operating Minimum (CLP/mo)`
- `Predictable coverage (CLP/mo)`
- `Coverage gap (CLP/mo)`
- `Collected cash MTD (CLP)`

Initiative Registry inspected columns include `Lifecycle Stage`, `Current Gate`, `Gate Outcome`, `Canonical Lifecycle State`, `Portfolio Object Type`, and `Normalized Object ID`.

Decision Registry inspected columns include `decision_id`, `title`, `status`, and `authority_mode`.

Structural Register inspected columns include `object_id`, `object_class`, `canonical_name`, `primary_owner`, `parent_unit`, and `reconciliation_status`.

Read Model Registry inspected columns include `read_model_id`, `authority_mode`, `freshness_state`, `lifecycle`, and `disposition`.

## Semantic decisions
Two distinctions were added as a backwards-compatible vocabulary extension rather than coercing them into existing classes:
- `LIFECYCLE_STAGE` is distinct from `LIFECYCLE_STATE`.
- `PREDICTABLE_COVERAGE` is distinct from collected cash, recognized revenue, booked/committed value and pipeline.

## Missing/unknown handling
The mapping is fail-safe:
- `-` and blank financial source tokens are never parsed as zero.
- Missing predictable coverage and collected-cash values map to `value_state: UNKNOWN` with limitation `SOURCE_NOT_EVIDENCED`.
- Required registry fields that are absent map to `MISSING` rather than being inferred.
- Consumer authority remains `DERIVED_NON_AUTHORITATIVE` even when facts originate from registry-authoritative sources.

## Local validation performed
The mapping YAML was parsed locally and validated against `source-fact-mapping.schema.json` using JSON Schema Draft 2020-12.

Observed:
- PASS: mapping validates against schema with 0 validation errors.
- PASS: exactly five first-horizon sources cover FH-CF-01..05.
- PASS: 17 canonical fact mappings are defined.
- PASS: every used semantic class exists in the controlled vocabulary.
- PASS: read-only, semantic-inference-prohibited and authority-escalation-prohibited policy is explicit.
- PASS: dash/blank financial tokens have explicit UNKNOWN handling.

## M2 boundary
This evidence does **not** claim M2 completion. It establishes the exact mapping prerequisite for reader implementation.

Still not introduced:
- source reader/adaptor code;
- DB/runtime/provider infrastructure;
- writeback;
- visual Control Center;
- semantic guessing;
- shared/public deployment.

Next authorized step: implement bounded deterministic read-only readers that consume exactly this mapping and emit M1-compliant Concern Records / Material Answers, then validate them against current source samples.
