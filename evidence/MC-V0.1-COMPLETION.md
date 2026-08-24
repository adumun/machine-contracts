# MC-V0.1 Completion Evidence

Status: PASS  
Date: 2026-08-24  
Branch: `feat/machine-contracts-v0.1-completion`  
Validated head: `16db5201613b60032b330da8e72d3e149c6a1e73`

## Scope completed in this branch
- Complete S0-S12 Initiative Lifecycle candidate profile in YAML.
- YAML input support in the local validator.
- Semantic workflow validation: unique stage/transition/artifact IDs, known transition endpoints, direction consistency, conditional artifact condition, lifecycle/reconciliation separation.
- Semantic WorkItem validation: READY-or-later owner/acceptance criteria, DONE evidence requirement, reclassification integrity.
- Negative fixtures for unknown transition stage, conditional artifact without condition and DONE without evidence.
- Deterministic YAML -> canonical JSON projection tool.
- Migration/version compatibility rules.
- Dependent-PR sequencing rule in `AGENTS.md`.

## Validation environment
- Python 3.13.5
- jsonschema 4.26.0
- PyYAML 6.0.3
- Execution mode: local deterministic validation reconstructed from the exact GitHub PR head contents through the connected GitHub integration; no GitHub Actions required.

## Validation history
The first executable validation pass exposed two repository defects and blocked merge as intended:
1. `examples/valid/workflow.stage-s7.json` referenced target stage `S8` while only declaring `S7`.
2. Several inline YAML scalars containing commas were parsed as unintended map properties.

Both defects were corrected on the same PR branch before merge.

## Required local validation gate
Executed against the exact PR head revision:

```bash
python validators/validate.py \
  examples/valid/work-item.task.json \
  examples/valid/workflow.stage-s7.json \
  profiles/initiative-lifecycle/stage-contracts.v0.1.yaml
```

Result:

```text
PASS examples/valid/work-item.task.json
PASS examples/valid/workflow.stage-s7.json
PASS profiles/initiative-lifecycle/stage-contracts.v0.1.yaml
```

Executed negative-fixture gate:

```bash
python validators/validate.py --expect-invalid \
  examples/invalid/work-item.unknown-type.json \
  examples/invalid/work-item.done-without-evidence.json \
  examples/invalid/workflow.unknown-stage.json \
  examples/invalid/workflow.conditional-without-condition.json
```

Result: PASS for all four invalid fixtures; each was rejected for the expected structural/semantic reason.

Executed deterministic projection gate:

```bash
python tools/project_yaml.py \
  profiles/initiative-lifecycle/stage-contracts.v0.1.yaml \
  /tmp/initiative-lifecycle.v0.1.json
python validators/validate.py /tmp/initiative-lifecycle.v0.1.json
```

Result:

```text
WROTE /tmp/initiative-lifecycle.v0.1.json
PASS /tmp/initiative-lifecycle.v0.1.json
```

## Decision
The v0.1 completion validation contract passes. PR #2 is eligible for merge under the local-validation policy. GitHub Actions were not required.
