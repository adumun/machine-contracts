# Provider-neutral mapping contracts

Status: **CANDIDATE**  
Work item: **WMS-113**

These mappings translate between ADÜMÜN canonical work semantics and provider-specific representations. Providers are adapters, not semantic authorities.

## Core rules

1. Canonical `WorkItem` semantics are defined by ADÜMÜN standards and schemas, not by Jira, GitHub, MCP, labels, custom fields or workflow names.
2. A provider profile MUST explicitly map canonical work types, states and fields; unknown values fail closed or remain explicitly unsupported.
3. Provider-specific project/field/status identifiers stay in the provider profile. They MUST NOT contaminate canonical vocabularies merely because a provider uses them.
4. Mappings may be bidirectional or one-way. Lossy mappings MUST be declared and explained.
5. A provider transition is valid only when canonical transition guards remain enforceable. If guards cannot be preserved, the transition MUST remain unmapped or require an explicit exception decision.
6. Reclassification of a work type is a canonical decision, not a provider status transition.
7. Provider metadata is retained as `provider_refs`/adapter configuration and must not silently overwrite canonical IDs or authority.
8. Project-specific Jira field IDs, workflow transition IDs and GitHub Project field option IDs belong in project configuration profiles layered on top of these mappings.

## Layers

```text
ADÜMÜN Work Semantics
        ↓
Canonical WorkItem
        ↓
Provider-neutral Mapping Contract
        ↓
Provider Profile (GitHub / Jira / future)
        ↓
Project/Repository Configuration Profile
        ↓
Adapter / MCP / API integration
```

## Current candidate profiles

- `github/work-item.v0.1.yaml`
- `jira/work-item.v0.1.yaml`

These profiles demonstrate semantic compatibility only. They do not assert that every repository or Jira project is already configured with those exact provider values.

## Validation

```bash
python validators/validate.py \
  mappings/github/work-item.v0.1.yaml \
  mappings/jira/work-item.v0.1.yaml

python validators/validate.py --expect-invalid \
  examples/invalid/provider-mapping.semantic-override.yaml
```

GitHub Actions are not required; local deterministic validation is the mandatory path.
