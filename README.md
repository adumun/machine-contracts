# ADÜMÜN Machine Contracts

Reusable repository for versioned machine-readable contracts, schemas, vocabularies, fixtures and local validators used across ADÜMÜN.

## Authority

Human-readable normative authority remains in the applicable ADÜMÜN Standards repository. This repository implements and encodes approved semantics for machines; it MUST NOT create, widen or silently override normative policy by itself.

## Toolkit boundary

The reusable validation surface is described by `toolkit/toolkit-manifest.yaml` and currently includes:

- `validators/validate.py` — reusable schema + semantic validator entrypoint;
- `conformance/core-fixtures.yaml` — positive/negative core contract fixtures;
- `conformance/run.py` — deterministic core conformance runner;
- `conformance/communication/contract_test.py` — stack-neutral communication contract-test runner that consumes the authoritative schemas from a Standards checkout;
- `scripts/validate-local.sh` — local validation gate.

COI readers, materializers, policies and portfolio reconciliation logic remain domain-specialized. Their presence in this repository does not make them generic toolkit semantics.

## Coverage and assurance

Toolkit version `0.1.0` is `EVALUATED` and `UNRELEASED`.

No `FULL`, `CERTIFIED` or `PREFERRED` claim is implied by repository ownership. Promotion requires exact standard-version coverage, deterministic conformance evidence, source-to-artifact provenance, immutable release identity, digest/checksum, applicable security/dependency review, and signature/attestation when feasible.

## Local validation

Run the complete repository-local gate:

```bash
./scripts/validate-local.sh
```

To also validate the communication normative fixtures without copying them into this repository, provide an authoritative Standards checkout:

```bash
STANDARDS_ROOT=/path/to/platform-standards ./scripts/validate-local.sh
```

The communication runner can also be invoked independently:

```bash
python3 conformance/communication/contract_test.py \
  --standards-root /path/to/platform-standards \
  --suite conformance/communication/example-suite.yaml
```

Consumer-specific live suites may additionally use `--base-url`; those suites own any safe mechanism needed to induce dependency-failure cases such as 502/503/504 mappings.

## Validation policy

Validation MUST be reproducible locally. GitHub Actions are not required evidence when account billing or spending constraints prevent hosted execution; equivalent local validation with retained evidence remains mandatory where applicable.
