#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib/common.sh"

wait_mode=false
timeout_seconds="${START_TIMEOUT_SECONDS}"

usage() {
  cat <<USAGE
Usage: $(basename "$0") [--wait] [--timeout <seconds>]

Runs local health/liveness checks for all VANESSA services.
USAGE
}

http_ok() {
  local url="$1"
  curl --silent --show-error --max-time 2 --fail "$url" >/dev/null
}

llm_contract_ok() {
  # Lightweight contract check: endpoint exists and returns a models payload.
  curl --silent --show-error --max-time 3 --fail "http://localhost:8000/v1/models" | grep -q '"data"'
}

tcp_ok() {
  local host="$1"
  local port="$2"

  if command -v nc >/dev/null 2>&1; then
    nc -z -w 2 "$host" "$port" >/dev/null 2>&1
    return $?
  fi

  timeout 2 bash -c "</dev/tcp/${host}/${port}" >/dev/null 2>&1
}

run_checks() {
  local failures=0
  local llm_routing_mode="${LLM_ROUTING_MODE:-local_only}"
  local runtime_profile="${VANESSA_RUNTIME_PROFILE:-offline}"
  local runtime_accelerator
  runtime_accelerator="$(resolve_llm_runtime_accelerator)"

  if http_ok "http://localhost:5000/health"; then
    printf 'backend: OK\n'
  else
    printf 'backend: FAIL\n'
    failures=$((failures + 1))
  fi

  if http_ok "http://localhost:7000/health"; then
    printf 'agent_engine: OK\n'
  else
    printf 'agent_engine: FAIL\n'
    failures=$((failures + 1))
  fi

  if http_ok "http://localhost:6000/health"; then
    printf 'sandbox: OK\n'
  else
    printf 'sandbox: FAIL\n'
    failures=$((failures + 1))
  fi

  if http_ok "http://localhost:10400/health"; then
    printf 'kws: OK\n'
  else
    printf 'kws: FAIL\n'
    failures=$((failures + 1))
  fi

  if http_ok "http://localhost:3000/"; then
    printf 'frontend: OK\n'
  else
    printf 'frontend: FAIL\n'
    failures=$((failures + 1))
  fi

  if http_ok "http://localhost:8000/health" && llm_contract_ok; then
    printf 'llm: OK (health + models)\n'
  else
    printf 'llm: FAIL\n'
    failures=$((failures + 1))
  fi

  if [[ "${llm_routing_mode}" == "local_only" ]]; then
    if compose ps --status running llm_runtime | grep -q 'llm_runtime'; then
      printf 'llm_runtime: OK (accelerator=%s)\n' "${runtime_accelerator}"
    else
      printf 'llm_runtime: FAIL (accelerator=%s)\n' "${runtime_accelerator}"
      failures=$((failures + 1))
    fi
  else
    printf 'llm_runtime: SKIP (LLM_ROUTING_MODE=%s)\n' "${llm_routing_mode}"
  fi

  if http_ok "http://localhost:8080/v1/.well-known/live"; then
    printf 'weaviate: OK\n'
  else
    printf 'weaviate: FAIL\n'
    failures=$((failures + 1))
  fi

  if tcp_ok "localhost" "5432"; then
    printf 'postgres: OK\n'
  else
    printf 'postgres: FAIL\n'
    failures=$((failures + 1))
  fi

  if curl --silent --show-error --max-time 2 --fail "http://localhost:5000/v1/runtime/profile" | grep -q "\"profile\""; then
    printf 'runtime_profile: OK (env=%s)\n' "${runtime_profile}"
  else
    printf 'runtime_profile: FAIL\n'
    failures=$((failures + 1))
  fi

  return "${failures}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --wait)
      wait_mode=true
      shift
      ;;
    --timeout)
      [[ $# -ge 2 ]] || die "--timeout requires a value"
      timeout_seconds="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage
      die "Unknown argument: $1"
      ;;
  esac
done

[[ "${timeout_seconds}" =~ ^[0-9]+$ ]] || die "--timeout must be an integer"
require_prerequisites

if [[ "${wait_mode}" == true ]]; then
  log_info "Waiting for all services to become healthy (timeout ${timeout_seconds}s)"
  deadline=$((SECONDS + timeout_seconds))

  while (( SECONDS < deadline )); do
    if run_checks; then
      exit 0
    fi
    echo "---"
    sleep 2
  done

  log_error "Timeout reached before all services became healthy"
  run_checks || true
  exit 3
fi

if run_checks; then
  exit 0
fi

exit 3
