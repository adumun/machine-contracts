# AGENTS.md

## Purpose
This repository is the canonical version-control home for ADÜMÜN machine-readable contracts. Human-readable corporate policy remains authoritative in its applicable ADÜMÜN canon/standard; this repository encodes that approved meaning for deterministic consumption.

## Mandatory operating rules
1. Do not invent governance semantics in code or schemas. Trace material fields, vocabularies and validation rules to an approved human-readable source.
2. Preserve stable IDs and explicit predecessor/successor lineage across migrations.
3. Fail closed on unknown governed vocabulary. Never coerce ambiguous values into valid values.
4. Provider-specific fields belong in mappings/adapters, not in canonical schemas unless the concept is genuinely provider-neutral.
5. Every breaking schema change requires an explicit migration path and MAJOR version change.
6. Add or update valid and invalid fixtures with every material schema/semantic change.
7. Validation must run locally. Hosted GitHub Actions are optional and must never be the only validation path.
8. Generated projections are non-authoritative unless an explicit contract says otherwise.
9. Do not accumulate dependent pull requests. If PR N is a prerequisite for PR N+1 in the same workstream, merge/close PR N before opening PR N+1 unless a documented stacked/parallel exception declares dependency, merge order and conflict handling.

## Branch / change discipline
- `main` contains accepted repository state.
- Material changes are developed on a branch and proposed through a PR.
- Schema changes must include validation evidence in the PR description or repository evidence artifact.
- Parallel PRs are acceptable only when they are truly independent or intentionally stacked with explicit dependency metadata.

## Initial normative sources
- Enterprise Machine Contracts, Manifests, Relationships & Registries canon
- STD-WCT-001 — Workflow Contract, Readiness, Completion & Transition Governance
- STD-WMS-001 — Work Management — Core Model & Executable Work Governance
- STD-WMS-TYPES-001 — Executable Work Type Specification
- STD-ILS-001 — Initiative Lifecycle Standard — End-to-End States, Stages & Gates
- STD-CIIA-001 — Canonical Initiative Information & Ingestion Architecture
- STD-TOOL-001 — Tool Usage, Configuration, Integration & Template Governance (CANDIDATE)
