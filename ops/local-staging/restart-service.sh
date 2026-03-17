#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib/common.sh"

target_service=""
build_mode=true
wait_mode=true
with_deps=false
timeout_seconds=90

usage() {
  cat <<USAGE
Usage: $(basename "$0") --service <name> [--no-build] [--with-deps] [--no-wait] [--timeout <seconds>] [--env-file <path>]

Rebuilds/restarts a single VANESSA service for faster local iteration.
Defaults to --build, --no-deps, and waiting for the target service readiness check.
USAGE
}

http_ok() {
  local url="$1"
  curl --silent --show-error --max-time 2 --fail "$url" >/dev/null
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

check_service_ready() {
  case "${target_service}" in
    frontend) http_ok "http://localhost:3000/" ;;
    backend) http_ok "http://localhost:5000/health" ;;
    agent_engine) http_ok "http://localhost:7000/health" ;;
    sandbox) http_ok "http://localhost:6000/health" ;;
    kws) http_ok "http://localhost:10400/health" ;;
    llm) http_ok "http://localhost:8000/health" ;;
    llm_runtime) llm_runtime_internal_http_ok "/health" ;;
    llama_cpp) llama_cpp_internal_http_ok "/v1/models" ;;
    qdrant) qdrant_internal_http_ok "/healthz" ;;
    weaviate) http_ok "http://localhost:8080/v1/.well-known/live" ;;
    postgres) tcp_ok "localhost" "5432" ;;
    *) return 1 ;;
  esac
}

wait_for_service() {
  local deadline=$((SECONDS + timeout_seconds))

  log_info "Waiting for ${target_service} readiness (timeout: ${timeout_seconds}s)"
  while (( SECONDS < deadline )); do
    if check_service_ready; then
      log_info "${target_service} is ready"
      return 0
    fi
    sleep 2
  done

  log_error "Timeout waiting for ${target_service} readiness"
  return 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --service)
      [[ $# -ge 2 ]] || die "--service requires a value"
      target_service="$2"
      shift 2
      ;;
    --no-build)
      build_mode=false
      shift
      ;;
    --with-deps)
      with_deps=true
      shift
      ;;
    --no-wait)
      wait_mode=false
      shift
      ;;
    --timeout)
      [[ $# -ge 2 ]] || die "--timeout requires a value"
      timeout_seconds="$2"
      shift 2
      ;;
    --env-file)
      [[ $# -ge 2 ]] || die "--env-file requires a path"
      COMPOSE_ENV_FILE="$2"
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

[[ -n "${target_service}" ]] || die "--service is required"
[[ "${timeout_seconds}" =~ ^[0-9]+$ ]] || die "--timeout must be an integer"
is_valid_service "${target_service}" || die "Invalid service: ${target_service}. Valid services: ${SERVICES[*]}"

if [[ -n "${COMPOSE_ENV_FILE}" ]]; then
  [[ -f "${COMPOSE_ENV_FILE}" ]] || die "--env-file does not exist: ${COMPOSE_ENV_FILE}"
fi

require_prerequisites

resolved_accelerator="$(resolve_llm_runtime_accelerator)"
resolved_cpu_variant="$(resolve_llm_runtime_cpu_variant)"
validate_llm_runtime_support || true
log_info "Resolved llm_runtime accelerator: ${resolved_accelerator}"
if [[ "${resolved_accelerator}" == "cpu" ]]; then
  log_info "Resolved llm_runtime CPU variant: ${resolved_cpu_variant}"
  log_info "Resolved llm_runtime CPU thread binding: ${VLLM_CPU_OMP_THREADS_BIND_DEFAULT}"
fi

if [[ "${target_service}" == "llm_runtime" ]] && [[ "${LLM_RUNTIME_CPU_SUPPORTED:-true}" == "false" ]]; then
  if llm_runtime_disable_local_requested && ! llm_routing_requires_local_runtime; then
    die "llm_runtime is unsupported on this CPU host and has been disabled for non-local routing."
  fi
  die "llm_runtime is unsupported on this CPU host. Use a compatible AVX2/AVX512 CPU or an NVIDIA GPU host."
fi

if [[ "${target_service}" == "llm_runtime" || "${target_service}" == "llm" ]]; then
  validate_llm_local_model_path
fi
if [[ "${target_service}" == "llama_cpp" ]]; then
  llama_cpp_enabled_requested || die "llama_cpp is disabled. Set LLAMA_CPP_URL to enable the optional llama.cpp runtime."
  validate_llama_cpp_model_path
fi
if [[ "${target_service}" == "qdrant" ]]; then
  qdrant_enabled_requested || die "qdrant is disabled. Set QDRANT_URL to enable the optional Qdrant runtime."
fi
validate_llm_cpu_thread_binding

log_info "Validating compose configuration"
compose config >/dev/null || die "Compose configuration is invalid"

compose_args=(-d)
if [[ "${build_mode}" == true ]]; then
  compose_args+=(--build)
fi
if [[ "${with_deps}" == false ]]; then
  compose_args+=(--no-deps)
fi

log_info "Restarting service '${target_service}'"
if ! compose up "${compose_args[@]}" "${target_service}"; then
  if [[ "${target_service}" == "llm_runtime" && "${resolved_accelerator}" == "cpu" ]]; then
    log_warn "CPU vLLM builds require the PyTorch CPU wheel index. Current LLM_RUNTIME_CPU_TORCH_INDEX_URL=${LLM_RUNTIME_CPU_TORCH_INDEX_URL:-https://download.pytorch.org/whl/cpu}"
    log_warn "CPU llm_runtime failed with accelerator=${resolved_accelerator}, variant=${resolved_cpu_variant}, bind=${VLLM_CPU_OMP_THREADS_BIND_DEFAULT}. Try bind fallback order: 0-7, auto, nobind."
  fi
  die "Failed to restart service: ${target_service}"
fi

if [[ "${wait_mode}" == true ]]; then
  wait_for_service || exit 2
fi

exit 0
