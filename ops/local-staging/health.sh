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

llm_runtime_ready_ok() {
  llm_runtime_internal_http_ok "/health"
}

llama_cpp_ready_ok() {
  llama_cpp_internal_http_ok "/v1/models"
}

qdrant_ready_ok() {
  qdrant_internal_http_ok "/healthz"
}

mcp_gateway_ready_ok() {
  mcp_gateway_internal_http_ok "/health"
}

runtime_profile_endpoint_ok() {
  local status
  status="$(curl --silent --show-error --max-time 2 -o /dev/null -w '%{http_code}' "http://localhost:5000/v1/runtime/profile")"
  [[ "${status}" == "200" || "${status}" == "401" ]]
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
  local runtime_profile_seed="${VANESSA_RUNTIME_PROFILE:-offline}"
  local runtime_profile_force="${VANESSA_RUNTIME_PROFILE_FORCE:-}"
  local runtime_accelerator
  runtime_accelerator="$(resolve_llm_runtime_accelerator)"
  local runtime_cpu_variant
  runtime_cpu_variant="$(resolve_llm_runtime_cpu_variant)"
  local runtime_cpu_bind
  runtime_cpu_bind="$(resolve_llm_cpu_thread_binding)"
  validate_llm_runtime_support >/dev/null 2>&1 || true

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

  if llama_cpp_enabled_requested; then
    if llama_cpp_ready_ok; then
      printf 'llama_cpp: OK (/v1/models)\n'
    else
      printf 'llama_cpp: FAIL\n'
      failures=$((failures + 1))
    fi
  else
    printf 'llama_cpp: SKIP (LLAMA_CPP_URL not set)\n'
  fi

  if qdrant_enabled_requested; then
    if qdrant_ready_ok; then
      printf 'qdrant: OK (/healthz)\n'
    else
      printf 'qdrant: FAIL\n'
      failures=$((failures + 1))
    fi
  else
    printf 'qdrant: SKIP (QDRANT_URL not set)\n'
  fi

  if mcp_gateway_enabled_requested; then
    if mcp_gateway_ready_ok; then
      printf 'mcp_gateway: OK (/health)\n'
    else
      printf 'mcp_gateway: FAIL\n'
      failures=$((failures + 1))
    fi
  else
    printf 'mcp_gateway: SKIP (MCP_GATEWAY_URL not set)\n'
  fi

  if [[ "${llm_routing_mode}" == "local_only" ]]; then
    if [[ "${LLM_RUNTIME_CPU_SUPPORTED:-true}" == "false" && "${runtime_accelerator}" == "cpu" ]]; then
      printf 'llm_runtime: FAIL (accelerator=%s, variant=%s, reason=unsupported_cpu)\n' "${runtime_accelerator}" "${runtime_cpu_variant}"
      failures=$((failures + 1))
    elif llm_runtime_ready_ok; then
      if [[ "${runtime_accelerator}" == "cpu" ]]; then
        printf 'llm_runtime: OK (accelerator=%s, variant=%s, bind=%s)\n' "${runtime_accelerator}" "${runtime_cpu_variant}" "${runtime_cpu_bind}"
      else
        printf 'llm_runtime: OK (accelerator=%s)\n' "${runtime_accelerator}"
      fi
    else
      if [[ "${runtime_accelerator}" == "cpu" ]]; then
        printf 'llm_runtime: FAIL (accelerator=%s, variant=%s, bind=%s)\n' "${runtime_accelerator}" "${runtime_cpu_variant}" "${runtime_cpu_bind}"
      else
        printf 'llm_runtime: FAIL (accelerator=%s)\n' "${runtime_accelerator}"
      fi
      failures=$((failures + 1))
    fi
  else
    if [[ "${LLM_RUNTIME_CPU_SUPPORTED:-true}" == "false" && "${runtime_accelerator}" == "cpu" ]]; then
      printf 'llm_runtime: SKIP (LLM_ROUTING_MODE=%s, accelerator=%s, variant=%s, reason=unsupported_cpu)\n' "${llm_routing_mode}" "${runtime_accelerator}" "${runtime_cpu_variant}"
    else
      printf 'llm_runtime: SKIP (LLM_ROUTING_MODE=%s)\n' "${llm_routing_mode}"
    fi
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

  if runtime_profile_endpoint_ok; then
    if [[ -n "${runtime_profile_force}" ]]; then
      printf 'runtime_profile: OK (seed=%s, forced=%s, auth=required)\n' "${runtime_profile_seed}" "${runtime_profile_force}"
    else
      printf 'runtime_profile: OK (seed=%s, auth=required)\n' "${runtime_profile_seed}"
    fi
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
