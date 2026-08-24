# MC-V0.1 Completion Evidence

Status: VALIDATION_REQUIRED_BEFORE_MERGE  
Date: 2026-08-24  
Branch: `feat/machine-contracts-v0.1-completion`

## Scope completed in this branch
- Complete S0-S12 Initiative Lifecycle candidate profile in YAML.
- YAML input support in the local validator.
- Semantic workflow validation: unique stage/transition/artifact IDs, known transition endpoints, direction consistency, conditional artifact condition, lifecycle/reconciliation separation.
- Semantic WorkItem validation: READY-or-later owner/acceptance criteria, DONE evidence requirement, reclassification integrity.
- Negative fixtures for unknown transition stage, conditional artifact without condition and DONE without evidence.
- Deterministic YAML -> canonical JSON projection tool.
- Migration/version compatibility rules.
- Dependent-PR sequencing rule in `AGENTS.md`.

## Required local validation gate
Run on the exact PR head revision:

```bash
python -m pip install -r requirements-dev.txt
python validators/validate.py \
  examples/valid/work-item.task.json \
  examples/valid/workflow.stage-s7.json \
  profiles/initiative-lifecycle/stage-contracts.v0.1.yaml

python validators/validate.py --expect-invalid \
  examples/invalid/work-item.unknown-type.json \
  examples/invalid/work-item.done-without-evidence.json \
  examples/invalid/workflow.unknown-stage.json \
  examples/invalid/workflow.conditional-without-condition.json

python tools/project_yaml.py \
  profiles/initiative-lifecycle/stage-contracts.v0.1.yaml \
  /tmp/initiative-lifecycle.v0.1.json
python validators/validate.py /tmp/initiative-lifecycle.v0.1.json
```

## Current execution evidence
The ChatGPT execution environment attempted to clone the public repository to run this gate, but its runtime could not resolve `github.com`; therefore no local PASS is claimed from that environment.

This is an execution-environment limitation, not a repository validation result. Per ADÜMÜN policy, the PR MUST remain unmerged until the exact head revision passes the local validation contract in an accepted environment and the result is retained here or in the PR.

GitHub Actions are not required and must not be substituted as a mandatory gate while financial/provider constraints apply.
