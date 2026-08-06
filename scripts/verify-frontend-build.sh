#!/usr/bin/env bash
# verify-frontend-build.sh
#
# Confirms the frontend produces a real production build from a clean
# state: removes any existing dist/, runs the documented build command,
# and checks the expected output exists.
#
# Exit code 0 = pass, 1 = fail.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root/frontend"

rm -rf dist

if ! npm run build; then
  echo "FAIL: npm run build failed" >&2
  exit 1
fi

if [[ ! -f dist/index.html ]]; then
  echo "FAIL: dist/index.html was not produced by the build" >&2
  exit 1
fi

if [[ -z "$(find dist/assets -maxdepth 1 -name '*.js' 2>/dev/null)" ]]; then
  echo "FAIL: no JS bundle found under dist/assets" >&2
  exit 1
fi

echo "OK: frontend production build verified (dist/index.html + JS bundle present)"
