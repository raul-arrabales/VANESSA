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
  local service_name="$1"
  llm_runtime_internal_http_ok "${service_name}" "/health"
}

llm_runtime_image_mismatch_reason() {
  local service_name="$1"
  local expected_image=""
  local container_id=""
  local actual_image=""

  if [[ "${runtime_accelerator}" == "cpu" ]]; then
    expected_image="${LLM_RUNTIME_CPU_IMAGE:-vanessa-llm-runtime-cpu:local}"
  else
    expected_image="${LLM_RUNTIME_GPU_IMAGE:-vanessa-llm-runtime-gpu:local}"
  fi

  container_id="$(compose ps -q "${service_name}" 2>/dev/null || true)"
  [[ -n "${container_id}" ]] || return 0
  actual_image="$(docker inspect --format '{{.Config.Image}}' "${container_id}" 2>/dev/null || true)"
  [[ -n "${actual_image}" ]] || return 0
  if [[ "${actual_image}" != "${expected_image}" ]]; then
    printf 'expected_image=%s, actual_image=%s, hint=use ops/local-staging/compose.sh or local-staging scripts\n' "${expected_image}" "${actual_image}"
  fi
}

llama_cpp_ready_ok() {
  llama_cpp_internal_http_ok "/v1/models"
}

qdrant_ready_ok() {
  qdrant_internal_http_ok "/healthz"
}

searxng_ready_ok() {
  searxng_internal_http_ok "/"
}

mcp_gateway_ready_ok() {
  mcp_gateway_internal_http_ok "/health"
}

runtime_profile_endpoint_ok() {
  local status
  status="$(curl --silent --show-error --max-time 2 -o /dev/null -w '%{http_code}' "http://localhost:5000/v1/runtime/profile")"
  [[ "${status}" == "200" || "${status}" == "401" ]]
}

embeddings_slot_target() {
  compose exec -T postgres psql -U vanessa -d vanessa -At -F $'\t' -c "
    SELECT
      COALESCE(i.config_json->>'loaded_managed_model_id', ''),
      COALESCE(i.config_json->>'loaded_runtime_model_id', ''),
      COALESCE(i.config_json->>'loaded_local_path', '')
    FROM platform_provider_instances i
    WHERE i.provider_key = 'vllm_embeddings_local'
    ORDER BY i.slug ASC
    LIMIT 1
  "
}

service_model_ids() {
  local service_name="$1"
  local capability_key="$2"
  compose exec -T "${service_name}" python -c "
import json
import urllib.request

payload = json.load(urllib.request.urlopen('http://127.0.0.1:8000/v1/models', timeout=3))
items = payload.get('data') if isinstance(payload, dict) else []
if not isinstance(items, list):
    items = []
for item in items:
    if not isinstance(item, dict):
        continue
    capabilities = item.get('capabilities') if isinstance(item.get('capabilities'), dict) else {}
    if '${capability_key}' == 'embeddings' and not bool(capabilities.get('embeddings')):
        continue
    if '${capability_key}' == 'llm_inference' and not bool(capabilities.get('text')):
        continue
    model_id = str(item.get('id') or '').strip()
    if model_id:
        print(model_id)
" 2>/dev/null
}

runtime_admin_state_fields() {
  local service_name="$1"
  compose exec -T "${service_name}" python -c "
import json
import urllib.request

payload = json.load(urllib.request.urlopen('http://127.0.0.1:8000/v1/admin/runtime-state', timeout=3))
print('\t'.join([
    str(payload.get('load_state') or '').strip(),
    str(payload.get('runtime_model_id') or '').strip(),
    str(payload.get('managed_model_id') or '').strip(),
    str(payload.get('local_path') or '').strip(),
    str(payload.get('last_error') or '').strip(),
]))
" 2>/dev/null
}

embeddings_slot_runtime_alignment_ok() {
  local slot_fields managed_model_id runtime_model_id local_path expected_runtime_model_id
  slot_fields="$(embeddings_slot_target || true)"
  IFS=$'\t' read -r managed_model_id runtime_model_id local_path <<< "${slot_fields}"

  if [[ -z "${managed_model_id}" ]]; then
    EMBEDDINGS_SLOT_ALIGNMENT_STATUS="ok"
    EMBEDDINGS_SLOT_ALIGNMENT_REASON="no persisted slot intent"
    return 0
  fi

  expected_runtime_model_id="${runtime_model_id:-${local_path}}"
  if [[ -z "${expected_runtime_model_id}" ]]; then
    EMBEDDINGS_SLOT_ALIGNMENT_STATUS="fail"
    EMBEDDINGS_SLOT_ALIGNMENT_REASON="persisted slot is missing a runtime model identifier"
    return 1
  fi

  local runtime_state_fields runtime_load_state runtime_state_model_id runtime_state_managed_model_id runtime_state_local_path runtime_last_error
  runtime_state_fields="$(runtime_admin_state_fields "llm_runtime_embeddings" || true)"
  if [[ -z "${runtime_state_fields}" ]]; then
    EMBEDDINGS_SLOT_ALIGNMENT_STATUS="fail"
    EMBEDDINGS_SLOT_ALIGNMENT_REASON="runtime admin state is unavailable for llm_runtime_embeddings"
    return 1
  fi
  IFS=$'\t' read -r runtime_load_state runtime_state_model_id runtime_state_managed_model_id runtime_state_local_path runtime_last_error <<< "${runtime_state_fields}"

  case "${runtime_load_state}" in
    loading|reconciling)
      EMBEDDINGS_SLOT_ALIGNMENT_STATUS="wait"
      EMBEDDINGS_SLOT_ALIGNMENT_REASON="persisted slot '${managed_model_id}' is ${runtime_load_state} in llm_runtime_embeddings (runtime model '${runtime_state_model_id:-${expected_runtime_model_id}}')"
      return 0
      ;;
    error)
      EMBEDDINGS_SLOT_ALIGNMENT_STATUS="fail"
      EMBEDDINGS_SLOT_ALIGNMENT_REASON="persisted slot '${managed_model_id}' failed in llm_runtime_embeddings: ${runtime_last_error:-runtime error}"
      return 1
      ;;
    loaded)
      ;;
    empty)
      EMBEDDINGS_SLOT_ALIGNMENT_STATUS="fail"
      EMBEDDINGS_SLOT_ALIGNMENT_REASON="persisted slot '${managed_model_id}' is not loaded into llm_runtime_embeddings"
      return 1
      ;;
    *)
      EMBEDDINGS_SLOT_ALIGNMENT_STATUS="fail"
      EMBEDDINGS_SLOT_ALIGNMENT_REASON="unexpected runtime admin load_state '${runtime_load_state:-<empty>}' for llm_runtime_embeddings"
      return 1
      ;;
  esac

  local runtime_model_ids
  runtime_model_ids="$(service_model_ids "llm_runtime_embeddings" "embeddings" || true)"
  if [[ -z "${runtime_model_ids}" ]]; then
    EMBEDDINGS_SLOT_ALIGNMENT_STATUS="fail"
    EMBEDDINGS_SLOT_ALIGNMENT_REASON="persisted slot '${managed_model_id}' is not loaded into llm_runtime_embeddings"
    return 1
  fi
  if ! printf '%s\n' "${runtime_model_ids}" | grep -Fxq "${expected_runtime_model_id}"; then
    EMBEDDINGS_SLOT_ALIGNMENT_STATUS="fail"
    EMBEDDINGS_SLOT_ALIGNMENT_REASON="expected runtime model '${expected_runtime_model_id}' is missing from llm_runtime_embeddings"
    return 1
  fi

  local llm_embeddings_model_ids
  llm_embeddings_model_ids="$(service_model_ids "llm" "embeddings" || true)"
  if [[ -z "${llm_embeddings_model_ids}" ]]; then
    EMBEDDINGS_SLOT_ALIGNMENT_STATUS="fail"
    EMBEDDINGS_SLOT_ALIGNMENT_REASON="llm does not advertise any embeddings-capable models"
    return 1
  fi
  if ! printf '%s\n' "${llm_embeddings_model_ids}" | grep -Fxq "${expected_runtime_model_id}"; then
    EMBEDDINGS_SLOT_ALIGNMENT_STATUS="fail"
    EMBEDDINGS_SLOT_ALIGNMENT_REASON="llm is not advertising the expected embeddings model '${expected_runtime_model_id}'"
    return 1
  fi

  EMBEDDINGS_SLOT_ALIGNMENT_STATUS="ok"
  EMBEDDINGS_SLOT_ALIGNMENT_REASON="slot aligned"
  return 0
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

  if searxng_ready_ok; then
    printf 'searxng: OK (/)\n'
  else
    printf 'searxng: FAIL\n'
    failures=$((failures + 1))
  fi

  if mcp_gateway_ready_ok; then
    printf 'mcp_gateway: OK (/health)\n'
  else
    printf 'mcp_gateway: FAIL\n'
    failures=$((failures + 1))
  fi

  if [[ "${llm_routing_mode}" == "local_only" ]]; then
    if [[ "${LLM_RUNTIME_CPU_SUPPORTED:-true}" == "false" && "${runtime_accelerator}" == "cpu" ]]; then
      printf 'llm_runtime_inference: FAIL (accelerator=%s, variant=%s, reason=unsupported_cpu)\n' "${runtime_accelerator}" "${runtime_cpu_variant}"
      printf 'llm_runtime_embeddings: FAIL (accelerator=%s, variant=%s, reason=unsupported_cpu)\n' "${runtime_accelerator}" "${runtime_cpu_variant}"
      failures=$((failures + 2))
    else
      inference_image_mismatch="$(llm_runtime_image_mismatch_reason "llm_runtime_inference")"
      embeddings_image_mismatch="$(llm_runtime_image_mismatch_reason "llm_runtime_embeddings")"
      if [[ -n "${inference_image_mismatch}" ]]; then
        printf 'llm_runtime_inference: FAIL (accelerator=%s, reason=image_mismatch, %s)\n' "${runtime_accelerator}" "${inference_image_mismatch}"
        failures=$((failures + 1))
      elif llm_runtime_ready_ok "llm_runtime_inference"; then
        if [[ "${runtime_accelerator}" == "cpu" ]]; then
          printf 'llm_runtime_inference: OK (accelerator=%s, variant=%s, bind=%s)\n' "${runtime_accelerator}" "${runtime_cpu_variant}" "${runtime_cpu_bind}"
        else
          printf 'llm_runtime_inference: OK (accelerator=%s)\n' "${runtime_accelerator}"
        fi
      else
        if [[ "${runtime_accelerator}" == "cpu" ]]; then
          printf 'llm_runtime_inference: FAIL (accelerator=%s, variant=%s, bind=%s)\n' "${runtime_accelerator}" "${runtime_cpu_variant}" "${runtime_cpu_bind}"
        else
          printf 'llm_runtime_inference: FAIL (accelerator=%s)\n' "${runtime_accelerator}"
        fi
        failures=$((failures + 1))
      fi

      if [[ -n "${embeddings_image_mismatch}" ]]; then
        printf 'llm_runtime_embeddings: FAIL (accelerator=%s, reason=image_mismatch, %s)\n' "${runtime_accelerator}" "${embeddings_image_mismatch}"
        failures=$((failures + 1))
      elif llm_runtime_ready_ok "llm_runtime_embeddings"; then
        if [[ "${runtime_accelerator}" == "cpu" ]]; then
          printf 'llm_runtime_embeddings: OK (accelerator=%s, variant=%s, bind=%s)\n' "${runtime_accelerator}" "${runtime_cpu_variant}" "${runtime_cpu_bind}"
        else
          printf 'llm_runtime_embeddings: OK (accelerator=%s)\n' "${runtime_accelerator}"
        fi
        if embeddings_slot_runtime_alignment_ok; then
          case "${EMBEDDINGS_SLOT_ALIGNMENT_STATUS:-ok}" in
            wait)
              printf 'llm_runtime_embeddings_slot: WAIT (%s)\n' "${EMBEDDINGS_SLOT_ALIGNMENT_REASON:-slot still converging}"
              ;;
            *)
              if [[ "${EMBEDDINGS_SLOT_ALIGNMENT_REASON:-}" == "no persisted slot intent" ]]; then
                printf 'llm_runtime_embeddings_slot: OK (no persisted slot intent)\n'
              else
                printf 'llm_runtime_embeddings_slot: OK (%s)\n' "${EMBEDDINGS_SLOT_ALIGNMENT_REASON:-slot aligned}"
              fi
              ;;
          esac
        else
          printf 'llm_runtime_embeddings_slot: FAIL (%s)\n' "${EMBEDDINGS_SLOT_ALIGNMENT_REASON:-alignment check failed}"
          failures=$((failures + 1))
        fi
      else
        if [[ "${runtime_accelerator}" == "cpu" ]]; then
          printf 'llm_runtime_embeddings: FAIL (accelerator=%s, variant=%s, bind=%s)\n' "${runtime_accelerator}" "${runtime_cpu_variant}" "${runtime_cpu_bind}"
        else
          printf 'llm_runtime_embeddings: FAIL (accelerator=%s)\n' "${runtime_accelerator}"
        fi
        failures=$((failures + 1))
      fi
    fi
  else
    if [[ "${LLM_RUNTIME_CPU_SUPPORTED:-true}" == "false" && "${runtime_accelerator}" == "cpu" ]]; then
      printf 'llm_runtime_inference: SKIP (LLM_ROUTING_MODE=%s, accelerator=%s, variant=%s, reason=unsupported_cpu)\n' "${llm_routing_mode}" "${runtime_accelerator}" "${runtime_cpu_variant}"
      printf 'llm_runtime_embeddings: SKIP (LLM_ROUTING_MODE=%s, accelerator=%s, variant=%s, reason=unsupported_cpu)\n' "${llm_routing_mode}" "${runtime_accelerator}" "${runtime_cpu_variant}"
    else
      printf 'llm_runtime_inference: SKIP (LLM_ROUTING_MODE=%s)\n' "${llm_routing_mode}"
      printf 'llm_runtime_embeddings: SKIP (LLM_ROUTING_MODE=%s)\n' "${llm_routing_mode}"
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
