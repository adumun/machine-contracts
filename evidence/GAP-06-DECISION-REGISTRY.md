# GAP-06 — Structured Decision Registry Cutover Evidence

Status: PASS
Date: 2026-08-24

## Human authority

- `STD-DEC-001 — Enterprise Decision Records, Registry & ADR Mapping` is CANONICAL in Google Drive.
- `REG-DEC-001 — ADÜMÜN Enterprise Decision Registry` exists as the structured enterprise registry.

## Source inventory

Representative initiative-local decision logs were inspected without rewriting their authority:

- `cmartinezs/initiative-control-center/governance/decisions.yaml` (`DEC-ICC-*`);
- `cmartinezs/nexus-community-ecosystem/governance/decisions.yaml` (`DEC-NCS-*`).

The enterprise model therefore uses federated authority: enterprise decisions may be authoritative in REG-DEC-001, while initiative/ADR/gate decisions may be indexed with `SOURCE_AUTHORITY` and retain their bounded-context source as authority.

## Machine implementation

- `schemas/decision-governance/decision-record.schema.json`
- `schemas/decision-governance/decision-registry.schema.json`
- `validators/validate_decision_registry.py`
- valid federated fixture: `examples/valid/decision-registry.enterprise.json`
- invalid supersession fixture: `examples/invalid/decision-registry.invalid-supersession.json`

## Validation

Validated locally against the exact candidate definitions:

- Draft 2020-12 DecisionRecord schema: PASS
- Draft 2020-12 DecisionRegistry schema: PASS
- valid federated registry fixture: PASS
- invalid SUPERSEDED record without `superseded_by`: rejected as expected
- duplicate IDs, registry-authority-without-statement, accepted-with-conditions-without-conditions, and self-supersession are guarded by the deterministic validator.

GitHub Actions are not required for this evidence; local deterministic validation is the canonical execution path under the current tooling policy.

## Cutover conclusion

GAP-06 is resolved. The previous TRV-009 decision-register convention is superseded for enterprise registry semantics by STD-DEC-001 + REG-DEC-001. Existing initiative-local `DEC-*`, architecture `ADR-*`, and lifecycle `GDR-*` records retain their stable identifiers and scoped authority and may be indexed without content duplication.
