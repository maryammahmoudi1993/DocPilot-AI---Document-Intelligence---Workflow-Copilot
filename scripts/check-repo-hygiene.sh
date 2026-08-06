#!/usr/bin/env bash
# check-repo-hygiene.sh
#
# Deterministic repository hygiene check for Phase 0A.
#
# Verifies:
#   1. `.gitignore` exists and contains the patterns required to keep
#      secrets, environment files, and build artifacts out of version
#      control.
#   2. No file matching a secret-like name (`.env`, `*.pem`, `*.key`,
#      `credentials.json`, ssh private keys, ...) is tracked by git.
#
# Exit code 0 = pass, 1 = fail. Failures are listed on stderr so the
# script is safe to use in CI without parsing stdout.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

fail=0

required_patterns=(
  ".env"
  ".env.*"
  "*.pem"
  "*.key"
  "credentials.json"
  "__pycache__/"
  "*.pyc"
  ".venv/"
  "venv/"
  "node_modules/"
  "*.log"
  ".DS_Store"
)

if [[ ! -f .gitignore ]]; then
  echo "FAIL: .gitignore is missing" >&2
  fail=1
else
  for pattern in "${required_patterns[@]}"; do
    if ! grep -qxF "$pattern" .gitignore; then
      echo "FAIL: .gitignore does not contain required pattern: $pattern" >&2
      fail=1
    fi
  done
fi

secret_like_regex='(^|/)\.env($|\.[^.]+$)|\.pem$|\.key$|(^|/)id_rsa$|credentials\.json$'
# .env.example (and similarly named templates) are meant to be committed —
# they document required variable names, not real values.
tracked_secret_hits="$(git ls-files | grep -E "$secret_like_regex" | grep -vE '\.env\.example$' || true)"
if [[ -n "$tracked_secret_hits" ]]; then
  echo "FAIL: secret-like files are tracked by git:" >&2
  echo "$tracked_secret_hits" >&2
  fail=1
fi

if [[ "$fail" -eq 0 ]]; then
  echo "OK: repository hygiene checks passed"
fi
exit "$fail"
