# INIT-ACC-001 — S8 M4 Quick Lookup + Executive Snapshot + Evidence Trace

Status: CANDIDATE PASS
Date: 2026-08-26
Authority: DEC-ACC-G7-001; RM-COI-001; artifacts 43–47

## Delivered

- `tools/coi_consumers.py`
  - Quick Lookup over exact `object_id + canonical_concept`
  - Executive Snapshot over the immutable RM-COI-001 fact index
  - Evidence Trace from `fact_key` to concern record and source envelopes
- `consumer-output.schema.json`
- enriched RM-COI-001 fact index contract v1.1.0 preserving display label, authority, provenance, freshness, confidentiality, limitations and drill-through reference
- `validators/validate_coi_consumers.py`

## Boundaries

All three consumers accept only a materialized RM-COI-001 snapshot. They do not acquire or mutate authoritative sources, perform writeback, approve decisions, infer new business semantics or introduce DB/runtime/UI dependencies.

Consumer authority is always `DERIVED_NON_AUTHORITATIVE`.

## Validation evidence

An isolated local semantic execution using the exact M4 consumer logic passed the following invariants:

- Quick Lookup finds the bounded governed fact by exact key.
- UNKNOWN remains UNKNOWN and carries no `value`.
- Executive Snapshot and Evidence Trace expose the same governed fact representation as Quick Lookup.
- Evidence Trace resolves preserved source refs to source envelopes.
- NOT_FOUND is explicit and does not synthesize a fact.
- consumer authority remains `DERIVED_NON_AUTHORITATIVE`.

The repository includes `validators/validate_coi_consumers.py` so the same invariants can be reproduced against the repository fixtures and JSON Schemas without GitHub Actions or paid infrastructure.

## Exit recommendation

M4 PASS after merge. Proceed only to M5 Operability / degraded mode. G8 remains OPEN.
