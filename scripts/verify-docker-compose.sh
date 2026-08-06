#!/usr/bin/env bash
# verify-docker-compose.sh
#
# Deterministic checks against the root docker-compose.yml, without
# requiring a running Docker daemon (uses `docker compose config`, which
# only parses/renders the compose file — it doesn't talk to the daemon).
#
# Verifies:
#   1. The compose file parses and resolves (`docker compose config`).
#   2. The required services exist: postgres, redis, backend.
#   3. postgres and redis each declare a healthcheck.
#   4. postgres and redis each mount a named (persistent) volume.
#
# Exit code 0 = pass, 1 = fail.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

fail=0

if [[ ! -f docker-compose.yml ]]; then
  echo "FAIL: docker-compose.yml is missing" >&2
  exit 1
fi

if ! rendered="$(docker compose config 2>&1)"; then
  echo "FAIL: 'docker compose config' could not parse docker-compose.yml:" >&2
  echo "$rendered" >&2
  exit 1
fi

require_service() {
  local service="$1"
  if ! echo "$rendered" | grep -qE "^  ${service}:"; then
    echo "FAIL: service '$service' is not defined" >&2
    fail=1
  fi
}

require_service "postgres"
require_service "redis"
require_service "backend"

require_healthcheck() {
  local service="$1"
  local service_block
  service_block="$(echo "$rendered" | awk -v s="  ${service}:" '
    $0 == s {found=1; print; next}
    found && /^  [a-zA-Z]/ {exit}
    found {print}
  ')"
  if ! echo "$service_block" | grep -q "healthcheck:"; then
    echo "FAIL: service '$service' has no healthcheck" >&2
    fail=1
  fi
}

require_healthcheck "postgres"
require_healthcheck "redis"

if ! echo "$rendered" | grep -q "postgres_data"; then
  echo "FAIL: postgres does not use a named persistent volume (expected 'postgres_data')" >&2
  fail=1
fi

if ! echo "$rendered" | grep -q "redis_data"; then
  echo "FAIL: redis does not use a named persistent volume (expected 'redis_data')" >&2
  fail=1
fi

if [[ "$fail" -eq 0 ]]; then
  echo "OK: docker-compose.yml verified (services, healthchecks, persistent volumes)"
fi
exit "$fail"
