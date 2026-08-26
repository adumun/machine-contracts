# INIT-ACC-001 — S8 / M5 Operability & Degraded Mode Evidence

## Scope

First-horizon local operability only over the merged M1–M4 baseline and RM-COI-001.

## Implemented controls

- explicit `HEALTHY` / `DEGRADED` / `UNAVAILABLE` operational assessment;
- source-unavailable, schema-drift, identity-drift and transform/mapping failure diagnostics;
- safe rebuild wrapper that never promotes an exception/failed candidate;
- last-known-good (LKG) preservation on degraded or failed rebuild;
- explicit consumer blocking when rebuild fails and no usable LKG exists;
- local recovery/runbook path with no GitHub Actions or paid runtime dependency.

## Degraded-mode scenarios encoded in validator

1. stale funding source -> snapshot explicitly DEGRADED;
2. missing source snapshot -> SOURCE_UNAVAILABLE + reconciliation degradation, no invented facts;
3. mapped source column removed -> SOURCE_SCHEMA_DRIFT;
4. degraded rebuild with LKG -> KEEP_LAST_KNOWN_GOOD;
5. rebuild exception with LKG -> no candidate promotion, LKG retained;
6. rebuild exception without LKG -> REBUILD_FAILED_NO_FALLBACK and all consumers BLOCKED.

## Safety boundary

M5 adds no database, server/runtime, provider SDK, persistent visual UI, writeback, approval mechanism or decision authority. Source repair is never performed inside the projection layer. Legitimate source/schema change requires governed mapping/contract change and full local revalidation.

## Reproducibility

Primary command:

```bash
python validators/validate_coi_operability.py
```

The runbook additionally requires M1–M4 validators before promoting a repaired candidate.

## Proposed M5 exit

PASS when the PR is merged and the local operability scenario validator passes on the merged candidate. Next milestone then becomes M6 — First-horizon Evidence Review; G8 remains OPEN until that review decides readiness.
