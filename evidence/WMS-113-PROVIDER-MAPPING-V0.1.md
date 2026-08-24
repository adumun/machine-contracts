# WMS-113 Provider-neutral Mapping Contract v0.1 — Validation Evidence

Status: PASS  
Date: 2026-08-24  
Branch: `feat/provider-neutral-mapping-v0.1`

## Scope

Validated the candidate provider-neutral mapping layer between ADÜMÜN `WorkItem` semantics and provider-specific representations.

Included:
- `provider-mapping.v0.1.0` JSON Schema;
- GitHub candidate mapping profile;
- Jira candidate mapping profile;
- provider-mapping semantic validation;
- invalid semantic-override fixture;
- mapping governance documentation.

## Validation contract

Structural validation uses JSON Schema Draft 2020-12. Semantic validation additionally checks:
- canonical work types are known;
- canonical workflow states are known;
- canonical fields exist in the WorkItem contract;
- canonical/provider mappings are not duplicated ambiguously;
- lossy mappings require explanation;
- transition endpoints use canonical states;
- mapped provider transitions preserve canonical guards.

## Result

GitHub candidate mapping: PASS (structural + semantic).  
Jira candidate mapping: PASS (structural + semantic).  
Invalid provider semantic-override fixture: PASS as expected-invalid.

The invalid fixture was rejected for multiple independent reasons:
- unknown canonical type `FEATURE_REQUEST`;
- duplicate mapping for canonical state `READY`;
- unknown canonical field `provider_status`;
- provider transition declared with `guards_preserved: false`.

## Decision

WMS-113 v0.1 is fit to merge as a CANDIDATE provider-neutral mapping contract. It does **not** assert that any concrete GitHub repository or Jira project is already configured to these example provider values. Project-specific field IDs, workflow transition IDs and option IDs remain a subsequent configuration-profile concern.

No GitHub Actions evidence is required; local deterministic validation is the accepted gate.
