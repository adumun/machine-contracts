# Machine Contract Migration Rules

Status: CANDIDATE

## Compatibility classes
- PATCH: editorial or validation clarification that does not invalidate previously valid documents.
- MINOR: backward-compatible additive contract evolution.
- MAJOR: breaking semantic or structural change requiring explicit migration.

## Required migration evidence
A breaking migration must preserve or explicitly map:
- stable governed-object IDs;
- predecessor/successor lineage;
- authority state;
- provenance/evidence references;
- provider mappings where applicable;
- known unknown/reconciliation states without coercion.

## Migration fixture convention
When v0.2+ introduces a shape or semantic change, add fixtures under:

`migrations/<contract>/<from>-to-<to>/`

with:
- `before.*`
- `after.*`
- `mapping.yaml`
- `VALIDATION.md`

No migration may silently reinterpret provider-specific or ambiguous legacy values as canonical enterprise semantics.
