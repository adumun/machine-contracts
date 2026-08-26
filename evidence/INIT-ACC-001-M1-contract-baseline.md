# INIT-ACC-001 — S8 M1 Contract Baseline Evidence

Status: M1 CANDIDATE COMPLETION EVIDENCE  
Initiative: INIT-ACC-001  
Capability: CAP-COI-001 — Corporate Operating Intelligence & Control  
Milestone: S8 / M1 — Contract Baseline  
Decision authority: DEC-ACC-G7-001  
Reconciliation checkpoint: artifact 43 / EVD-2026-0043  

## Scope

This change establishes only the first-horizon COI machine contract baseline. It does not implement source readers, persistence, runtime services, a database, a visual Control Center, writeback or approvals.

The baseline covers:
- common Material Answer envelope;
- Source Envelope for authority/freshness/confidentiality metadata;
- generic Concern Record with bounded FH-CF-01..05 object classes;
- controlled COI vocabulary;
- positive and negative fixtures;
- local deterministic validator.

## Preserved invariants

1. COI projections remain DERIVED_NON_AUTHORITATIVE unless the source contract explicitly says otherwise.
2. UNKNOWN, MISSING, STALE, RECONCILIATION_REQUIRED, RESTRICTED and NOT_APPLICABLE are first-class states.
3. KNOWN requires a value; non-value states must not silently carry a material value.
4. semantic class, source authority, provenance, freshness and confidentiality are explicit.
5. concern families are bounded to FH-CF-01..05 for the first horizon.
6. all source envelopes are read-only.
7. provider-specific implementation detail is excluded from canonical schemas.
8. no GitHub Actions dependency is introduced.

## Local validation

Command:

```bash
python validators/validate_coi_contracts.py
```

Observed result on the exact candidate contract set:

```text
PASS: 3 COI schemas are structurally valid
PASS: controlled vocabularies load and valid fixture uses governed values
PASS: valid material-answer fixture validates
PASS: invalid fixture is rejected (1 expected validation error(s))
PASS: local validation path does not depend on GitHub Actions
```

## M1 exit assessment

- common material-answer envelope: SATISFIED
- concern-family schemas and semantic classes: SATISFIED
- source/authority/freshness metadata contract: SATISFIED
- local contract validation: SATISFIED
- S5/S6 invariants preserved: SATISFIED

Recommended milestone outcome: M1 PASS, then proceed to M2 deterministic bounded read-only readers/adapters after merge.
