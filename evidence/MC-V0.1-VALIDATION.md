# MC-V0.1 Validation Evidence

Status: CANDIDATE IMPLEMENTATION EVIDENCE  
Date: 2026-08-24  
Scope: initial workflow/work-management machine contract implementation.

## Structural checks

- JSON Schema draft: 2020-12.
- `work-item.schema.json` parses as JSON and accepts the valid Task fixture.
- `work-item.schema.json` rejects the invalid `FEATURE_REQUEST` type fixture as expected.
- Workflow contract schema uses explicit `additionalProperties: false` boundaries.
- CONDITIONAL ArtifactContract requires an explicit `condition`.
- Provider references are structurally separated from canonical type/category/state.
- Stable object IDs and `schema_version` are explicit.

## Local validation command

```bash
python -m pip install -r requirements-dev.txt
python validators/validate.py examples/valid/work-item.task.json
python validators/validate.py examples/valid/workflow.stage-s7.json
python validators/validate.py --expect-invalid examples/invalid/work-item.unknown-type.json
```

Hosted GitHub Actions are intentionally not required for validation. Local deterministic validation is the mandatory path for this repository.

## Promotion state

This evidence does **not** promote v0.1 to CANONICAL/CURRENT. The implementation remains CANDIDATE until schema parity, fixtures and validator behavior are sufficiently complete and reviewed against the human-readable ADÜMÜN standards.

## Known remaining work

- Full S0-S12 lifecycle profile fixture/definition.
- Additional invalid workflow fixtures.
- Semantic validator rules beyond JSON Schema shape validation (DoR/DoD transition guards, provider overwrite detection, reclassification integrity).
- Deterministic canonical JSON projection from human-maintainable YAML definitions.
- Schema/version migration fixtures.
- Provider-neutral mapping contract before GitHub/Jira adapters.
