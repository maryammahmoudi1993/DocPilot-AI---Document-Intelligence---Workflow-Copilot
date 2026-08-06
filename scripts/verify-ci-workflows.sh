#!/usr/bin/env bash
# verify-ci-workflows.sh
#
# Deterministic checks against .github/workflows/*.yml:
#   1. Each workflow file is valid YAML.
#   2. The backend workflow's step commands cover: ruff check, ruff format
#      --check, mypy, manage.py check, makemigrations --check, pytest, and
#      OpenAPI schema generation.
#   3. The frontend workflow's step commands cover: npm ci, lint, typecheck,
#      test, and build.
#
# Exit code 0 = pass, 1 = fail.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

PY="C:/Users/mahmo/AppData/Local/Programs/Python/Python312/python.exe"
if ! command -v "$PY" >/dev/null 2>&1; then
  PY="python3"
fi

fail=0
workflows_dir=".github/workflows"

if [[ ! -d "$workflows_dir" ]]; then
  echo "FAIL: $workflows_dir is missing" >&2
  exit 1
fi

check_yaml_valid() {
  local file="$1"
  if ! "$PY" -c "import sys, yaml; yaml.safe_load(open(sys.argv[1], encoding='utf-8'))" "$file" 2>/tmp/yaml-err; then
    echo "FAIL: $file is not valid YAML:" >&2
    cat /tmp/yaml-err >&2
    fail=1
    return 1
  fi
  return 0
}

check_contains_all() {
  local file="$1"
  shift
  local needle
  for needle in "$@"; do
    if ! grep -qF -- "$needle" "$file"; then
      echo "FAIL: $file is missing required step command: $needle" >&2
      fail=1
    fi
  done
}

backend_workflow="$workflows_dir/backend-ci.yml"
if [[ -f "$backend_workflow" ]]; then
  check_yaml_valid "$backend_workflow" || true
  check_contains_all "$backend_workflow" \
    "ruff check" \
    "ruff format --check" \
    "mypy" \
    "manage.py check" \
    "makemigrations --check" \
    "pytest" \
    "spectacular"
else
  echo "FAIL: $backend_workflow is missing" >&2
  fail=1
fi

frontend_workflow="$workflows_dir/frontend-ci.yml"
if [[ -f "$frontend_workflow" ]]; then
  check_yaml_valid "$frontend_workflow" || true
  check_contains_all "$frontend_workflow" \
    "npm ci" \
    "run lint" \
    "run typecheck" \
    "run test" \
    "run build"
else
  echo "FAIL: $frontend_workflow is missing" >&2
  fail=1
fi

if [[ "$fail" -eq 0 ]]; then
  echo "OK: CI workflows verified (valid YAML, required gates present)"
fi
exit "$fail"
