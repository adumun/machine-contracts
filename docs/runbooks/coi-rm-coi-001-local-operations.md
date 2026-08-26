# RM-COI-001 — Local Operability & Recovery Runbook

Status: S8/M5 first-horizon runbook  
Scope: local/on-demand operation only; no paid runtime, DB, persistent UI or writeback.

## Operating principle

RM-COI-001 is rebuildable and `DERIVED_NON_AUTHORITATIVE`. Never replace authoritative source records. A candidate snapshot is promoted only when the rebuild is healthy. If a rebuild is degraded or fails, preserve the last-known-good (LKG) snapshot and surface explicit status/diagnostics.

## Standard local sequence

1. Acquire bounded source snapshots through an authorized connector/tool boundary.
2. Run deterministic M2 readers against the approved mapping.
3. Inspect reader diagnostics before materialization.
4. Materialize candidate RM-COI-001.
5. Assess freshness/reconciliation/diagnostics.
6. Promote only a healthy candidate; otherwise retain LKG.
7. Consumers must expose the current snapshot identity/as-of and degraded status.

## Validation commands

```bash
python validators/validate_coi_source_mapping.py
python validators/validate_coi_readers.py
python validators/validate_coi_materialized_snapshot.py
python validators/validate_coi_consumers.py
python validators/validate_coi_operability.py
```

GitHub Actions are not required evidence. Retain the local command output when a milestone/release decision depends on it.

## Failure classification

- `SOURCE_UNAVAILABLE`: bounded source snapshot absent/unreachable.
- `SOURCE_SCHEMA_DRIFT`: expected mapped source column disappeared/changed.
- `SOURCE_IDENTITY_DRIFT`: deterministic row identity/label selector no longer resolves exactly one governed record.
- `SOURCE_TRANSFORM_OR_MAPPING_FAILURE`: representation no longer satisfies an approved deterministic transform.
- `REBUILD_EXCEPTION`: reader/materializer execution cannot create a candidate snapshot.

## Safe behavior

### STALE source

Snapshot becomes `DEGRADED`. Consumers may operate only with explicit freshness status. Do not silently claim current data.

### PARTIAL / unavailable source

Snapshot becomes `RECONCILIATION_REQUIRED`. Missing facts are not synthesized. Preserve LKG for operational continuity where one exists.

### Schema/identity drift

Do not update mappings ad hoc inside a reader. Classify the drift, inspect the authoritative source, and change the mapping/contract through the governed machine-contract change process.

### Rebuild exception

Do not promote candidate output. Keep LKG. If no LKG exists, consumers are `BLOCKED` and the read model is operationally unavailable.

## Recovery

1. Identify diagnostic code and affected source.
2. Verify the authoritative source itself; do not repair a projection by inventing values.
3. If source changed legitimately, update mapping/schema in a reviewed branch/PR.
4. Run all M1–M5 local validators.
5. Rebuild candidate from fresh bounded source snapshots.
6. Confirm candidate is healthy and preserves authority/provenance/freshness/value-state invariants.
7. Promote candidate and update operational evidence/read-model freshness record as applicable.

## Escalation triggers

Escalate beyond file/JSON-first only if evidence shows material need for persistent scheduling, concurrency, historical query load, row/field authorization, incremental refresh, operational events, or unacceptable rebuild latency. Provider/runtime/database selection remains outside M5.
