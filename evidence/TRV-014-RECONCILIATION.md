# TRV-014 — Initiative Governance Manifest Reconciliation Evidence

Status: **PASS — CANDIDATE IMPLEMENTATION READY FOR MERGE**  
Date: 2026-08-24  
Human authority: `STD-IGM-001 — Initiative Governance Manifest & Distributed Registry Contract`  
Machine implementation: `schemas/initiative-governance/initiative-manifest.schema.json`

## Source inventory

Representative predecessor manifests were inspected directly:

| Initiative | Repository | Source blob SHA | Key evidence |
| --- | --- | --- | --- |
| Initiative Control Center | `cmartinezs/initiative-control-center` | `7d4f5b04e31ed4e24f5d4f18fe64d2b12cb439ba` | prospective adoption, lifecycle/gate refs, distributed registries, non-authoritative projections |
| Nexus Community Ecosystem | `cmartinezs/nexus-community-ecosystem` | `d6ffe2455db88619d7a42ea71f27199791fbb105` | product profile, prospect-specific registry/context extension, dashboard projection |
| Auto IG Posting | `cmartinezs/auto-ig-posting` | `1e9682a4b051b470d94205893bc83933d18fc220` | retrospective adoption, incomplete gate history, legacy operational lifecycle |
| Astra Project | `cmartinezs/astra-project` | `c1bd60fc9f3ce368b17a8494bc16a09e37d5c724` | creative-IP tailoring, domain canon refs, privacy-sensitive portfolio projection |

## Reconciliation result

The observed implementations share a stable enterprise envelope but legitimately diverge in bounded-context concerns. TRV-014 is therefore implemented as **distributed semantic authority with an enterprise interoperability contract**, not as one centralized initiative database.

Enterprise core:
- stable initiative identity and repository locator;
- profile + rigor;
- lifecycle declaration and reconciliation status;
- registry references with explicit local/domain/enterprise authority scope;
- generated/read-model authority declaration;
- freshness metadata.

Local authority retained:
- source/evidence/hypothesis/risk/decision/artifact registry contents;
- commercial/prospect metadata;
- creative canon structures;
- initiative-specific constraints and next actions;
- other namespaced bounded-context extensions.

## Compatibility implementation

`profiles/initiative-governance/legacy-ils-0.2-alpha.mapping.yaml` documents a non-destructive mapping from the observed legacy manifest family. `tools/project_legacy_initiative_manifest.py` projects that source shape into `initiative-manifest.v1` while preserving unknown/domain fields under namespaced extensions and preserving local registry references.

Retrospective initiatives do not fabricate canonical state or historical gate acceptance: their legacy state remains visible, `canonical_state` remains null until reconciled, and `reconciliation_status` remains explicit.

## Validation evidence

- JSON Schema draft: Draft 2020-12.
- Schema structure check: PASS.
- Prospective representative fixture (`initiative-manifest.nexus.json`): PASS.
- Retrospective representative fixture (`initiative-manifest.auto-ig-retrospective.json`): PASS.
- Generated projection attempting authority (`initiative-manifest.generated-authoritative.json`): rejected by semantic validator as expected.
- Registry types are required to be unique by semantic validator.
- Retrospective incomplete gate history cannot claim a last accepted gate without a decision record.

Validation is local/provider-independent. GitHub Actions is not required for semantic validity.

## Authority cutover

`registries/contract-authority-index.yaml` is changed from `RECONCILIATION_REQUIRED` to `DISTRIBUTED_WITH_ENTERPRISE_CONTRACT` for `initiative-manifest`.

This does **not** transfer the content authority of initiative-local registries to `adumun/machine-contracts`; it assigns the enterprise envelope/schema concern to the machine-contract repository while leaving domain truth distributed.

## TRV-014 closure criteria

- human authority boundary defined: PASS;
- executable schema exists: PASS;
- representative legacy shapes reconciled: PASS;
- retrospective adoption represented without fabricated history: PASS;
- domain extensions preserved without overriding enterprise fields: PASS;
- generated read models remain non-authoritative: PASS;
- distributed registry authority preserved: PASS;
- cutover lineage/evidence retained: PASS.

Recommended matrix disposition after merge: `MIGRATED` / target authority `CANONICAL`, with distributed initiative-local authority explicitly preserved.
