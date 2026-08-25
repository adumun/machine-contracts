# MIG-TXCR-MC-FINAL — Machine Contract Cutover

Status: **READY FOR MERGE**

This wave removes the last machine-contract authority dependency on `cmartinezs/the-x-contract-registry`.

## Legacy mapping

- `registry/contracts.yaml` → `registries/contract-authority-index.yaml`
- `schemas/contracts.schema.json` → `schemas/contracts/contract-authority-index.schema.json`
- `schemas/repositories.schema.json` → `schemas/governance/repository-registry.schema.json`
- `schemas/relationships.schema.json` → `schemas/governance/relationship-registry.schema.json`
- `schemas/standards.schema.json` → `schemas/governance/standards-registry.schema.json`
- audit schemas → already cut over to `adumun/audit-framework`

Predecessor schema/registry observations remain provenance; they are not silently reinterpreted as ADÜMÜN semantics.

## Authority reconciliation

The legacy contract registry was primarily an index. It did not own the semantics of Capability, CapacityBudget, Commitment, ExecutionRecord, AgentDefinition or Shipping Mode runtime contracts. Their existing external legacy semantic authorities remain explicit until separately migrated by their owning bounded contexts.

`work-item` now has an ADÜMÜN candidate successor in this repository. `initiative-manifest` remains `RECONCILIATION_REQUIRED` because the predecessor itself declared distributed initiative-local authority; deprecating the index does not erase or transfer that authority.

## Validation entry point

```bash
python -m pip install -r requirements-dev.txt
python validators/validate_legacy_cutover.py
```

The validator checks all new JSON Schemas and validates the migrated contract-authority index. GitHub Actions is not required; the enterprise financial-bypass rule applies.

## Cutover conclusion

After this PR is merged, the legacy repository no longer needs to remain active as semantic authority for audit, repository governance or machine-contract indexing. Its remaining value is historical provenance, enabling global transition to `DEPRECATED` / read-only preservation in a subsequent dependent PR.
