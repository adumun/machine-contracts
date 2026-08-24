# Provider Configuration Profiles v0.1 — Validation Evidence

Status: PASS
Date: 2026-08-24
Branch: `feat/provider-config-profiles-v0.1`

Validated:
- `CFG-GITHUB-ADUMUN-MACHINE-CONTRACTS-001` — BOUND to repository ID `1344824664` and `https://github.com/adumun/machine-contracts`;
- `CFG-JIRA-PROJECT-TEMPLATE-001` — TEMPLATE with deliberately unresolved Jira project key/IDs/fields/transitions;
- invalid BOUND profile without concrete target identity and without local-validation fallback.

Structural validation uses `provider-config.v0.1.0`. Semantic rules require:
- a BOUND target to retain concrete external ID and URL;
- local validation when hosted validation is not required;
- every provider configuration to reference a provider mapping contract.

Result:
- GitHub repository profile: PASS.
- Jira project template: PASS.
- Invalid bound profile: PASS as expected-invalid (`external_id`, `url`, and local-validation fallback missing).

The GitHub profile records governed/intended configuration. Provider-side conformance (rulesets, branch protection and repository settings) remains a separate audit concern and must not be fabricated from policy text.
