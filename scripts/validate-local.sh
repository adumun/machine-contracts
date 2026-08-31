#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-.venv}"
REQ_FILE="requirements-validation.txt"
STANDARDS_ROOT="${STANDARDS_ROOT:-}"

printf '\n== ADÜMÜN machine-contracts local validation ==\n'
printf 'Repository: %s\n' "$ROOT_DIR"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "ERROR: '$PYTHON_BIN' was not found in PATH." >&2
  exit 2
fi

PY_VERSION="$($PYTHON_BIN -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')"
printf 'Python: %s (%s)\n' "$PYTHON_BIN" "$PY_VERSION"

if [[ ! -f "$REQ_FILE" ]]; then
  echo "ERROR: $REQ_FILE is missing." >&2
  exit 2
fi

if [[ ! -d "$VENV_DIR" ]]; then
  echo "Creating virtual environment: $VENV_DIR"
  if ! "$PYTHON_BIN" -m venv "$VENV_DIR"; then
    echo "ERROR: could not create $VENV_DIR. On Debian/Ubuntu install python3-venv and retry." >&2
    exit 2
  fi
fi

VENV_PY="$VENV_DIR/bin/python"
if [[ ! -x "$VENV_PY" ]]; then
  echo "ERROR: virtual environment Python not found at $VENV_PY." >&2
  exit 2
fi

if ! "$VENV_PY" -c 'import jsonschema, referencing, yaml' >/dev/null 2>&1; then
  echo "Installing validation dependencies from $REQ_FILE"
  "$VENV_PY" -m pip install --upgrade pip
  "$VENV_PY" -m pip install -r "$REQ_FILE"
else
  echo "Validation dependencies: OK"
fi

export PYTHONPATH="$ROOT_DIR${PYTHONPATH:+:$PYTHONPATH}"

printf '\n-- core contract conformance fixtures --\n'
"$VENV_PY" conformance/run.py

VALIDATORS=(
  validators.validate_coi_source_mapping
  validators.validate_coi_readers
  validators.validate_coi_materialized_snapshot
  validators.validate_coi_consumers
  validators.validate_coi_operability
  validators.validate_coi_coverage
  validators.validate_coi_project_pulse_component
  validators.validate_coi_portfolio_reconciliation
)

passed=0
for validator in "${VALIDATORS[@]}"; do
  printf '\n-- %s --\n' "$validator"
  "$VENV_PY" -m "$validator"
  passed=$((passed + 1))
done

if [[ -n "$STANDARDS_ROOT" ]]; then
  printf '\n-- communication standards fixture conformance --\n'
  "$VENV_PY" conformance/communication/contract_test.py \
    --standards-root "$STANDARDS_ROOT" \
    --suite conformance/communication/example-suite.yaml
else
  printf '\nCommunication conformance: SKIPPED (set STANDARDS_ROOT to a checkout of adumun/platform-standards).\n'
fi

printf '\nPASS: core conformance plus %d/%d specialized validation modules completed successfully.\n' "$passed" "${#VALIDATORS[@]}"
printf 'Local validation evidence is complete for executed gates; GitHub Actions are not required.\n\n'
