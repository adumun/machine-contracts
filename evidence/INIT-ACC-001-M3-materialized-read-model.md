# INIT-ACC-001 — S8 / M3 Materialized Read Model Evidence

Status: candidate M3 PASS pending merge and registry promotion.

## Scope

This change materializes one rebuildable file/JSON read model from the deterministic M2 reader output. It does not acquire source data, create source authority, add a database/runtime, or implement a persistent visual Control Center.

## Read model

- ID: `RM-COI-001`
- Name: `Corporate Operating Snapshot`
- Authority: `DERIVED_NON_AUTHORITATIVE`
- Input: `coi-reader-output.v1`
- Output: `coi-materialized-snapshot.v1`
- Persistence: rebuildable file/JSON

The snapshot carries `generated_at`, `as_of`, aggregate freshness/reconciliation state, source envelopes, governed concern records, and a deterministic fact index.

## Deterministic rebuild

For identical M2 reader input (including its retrieval timestamp), materialization produces the same logical JSON structure and ordering. Records, source envelopes and indexed facts are sorted using stable governed identities; no random IDs, wall-clock reads or provider calls occur inside materialization.

## Consumer-independence check

Three bounded projections consume the same snapshot object:

1. Quick Lookup resolves `object_id + canonical_concept` from the snapshot fact index.
2. Executive Briefing projection reads snapshot identity, as-of, health and aggregate fact counts.
3. Static View projection filters the same fact index by concern family.

No consumer reconstructs source semantics or invokes the original governed source.

## Integrity checks

- Snapshot authority remains `DERIVED_NON_AUTHORITATIVE`.
- Source/fact authority is preserved in indexed facts.
- `UNKNOWN`/`MISSING`/restricted states do not gain a value during materialization.
- A missing source degrades aggregate reconciliation to `RECONCILIATION_REQUIRED` and records the unavailable source; no replacement facts are synthesized.
- Source provenance remains attached through source refs and original M1 records.

## Local validation

Canonical command:

```bash
python validators/validate_coi_materialized_snapshot.py
```

Expected pass conditions:

- materialized snapshot validates against JSON Schema;
- identical reader input rebuilds an identical logical snapshot;
- fact index count equals governed fact count;
- no authority elevation;
- unknown integrity preserved;
- Quick Lookup / Executive Briefing / Static View observe the same snapshot identity and facts;
- degraded-source case becomes `RECONCILIATION_REQUIRED`;
- no GitHub Actions or paid runtime dependency.

## Publication/security boundary

The repository is public. Real internal source snapshots and financial values are not committed. Synthetic fixtures exercise the complete M3 path; real current-source validation is retained only as non-sensitive invariant evidence in the human lifecycle artifact/evidence registry.

## Exit recommendation

If merged and `RM-COI-001` is promoted into `REG-RM-001` with owner, steward, refresh/freshness and drift-control metadata, M3 is complete and the next authorized milestone is M4 — Quick Lookup + Executive Snapshot + Evidence Trace over this same governed read model.
