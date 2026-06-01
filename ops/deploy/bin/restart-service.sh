#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/../lib/common.sh"

target_service=""
build_mode=auto
wait_mode=true
with_deps=false
timeout_seconds=90

usage() {
  cat <<USAGE
Usage: $(basename "$0") --service <name> [--build|--no-build] [--with-deps] [--no-wait] [--timeout <seconds>] [--env-file <path>]

Rebuilds/restarts a single VANESSA service for faster iteration.
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
    frontend) http_ok "$(frontend_probe_url)" ;;
    backend) http_ok "$(backend_probe_url)" ;;
    agent_engine) http_ok "$(agent_engine_probe_url)" ;;
    sandbox) http_ok "$(sandbox_probe_url)" ;;
    mcp_gateway) http_ok "$(mcp_gateway_probe_url)" ;;
    kws) http_ok "$(kws_probe_url)" ;;
    llm) http_ok "$(llm_probe_url)" ;;
    llm_runtime_inference) llm_runtime_internal_http_ok "llm_runtime_inference" "/health" ;;
    llm_runtime_embeddings) llm_runtime_internal_http_ok "llm_runtime_embeddings" "/health" ;;
    llama_cpp) llama_cpp_internal_http_ok "/v1/models" ;;
    qdrant) qdrant_internal_http_ok "/healthz" ;;
    image_analysis) image_analysis_internal_http_ok "/health" ;;
    image_analysis_anpr) image_analysis_worker_internal_http_ok "image_analysis_anpr" "8091" "/health" ;;
    image_analysis_objects) image_analysis_worker_internal_http_ok "image_analysis_objects" "8092" "/health" ;;
    image_analysis_captioning) image_analysis_worker_internal_http_ok "image_analysis_captioning" "8093" "/health" ;;
    image_generation) image_generation_internal_http_ok "/health" ;;
    image_generation_text_to_image) image_generation_worker_internal_http_ok "image_generation_text_to_image" "8095" "/health" ;;
    image_generation_plate_logo) image_generation_worker_internal_http_ok "image_generation_plate_logo" "8096" "/health" ;;
    searxng) searxng_internal_http_ok "/" ;;
    weaviate) http_ok "$(weaviate_probe_url)" ;;
    postgres) tcp_ok "$(host_probe_host "${POSTGRES_BIND_HOST:-127.0.0.1}")" "${POSTGRES_PUBLISHED_PORT:-5432}" ;;
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
    --build)
      build_mode=true
      shift
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

reload_runtime_env_context
require_prerequisites

resolved_accelerator="$(resolve_llm_runtime_accelerator)"
resolved_cpu_variant="$(resolve_llm_runtime_cpu_variant)"
validate_llm_runtime_support || true
log_info "Resolved local runtime accelerator: ${resolved_accelerator}"
if [[ "${resolved_accelerator}" == "cpu" ]]; then
  log_info "Resolved local runtime CPU variant: ${resolved_cpu_variant}"
  log_info "Resolved local runtime CPU thread binding: ${VLLM_CPU_OMP_THREADS_BIND_DEFAULT}"
fi

if [[ ( "${target_service}" == "llm_runtime_inference" || "${target_service}" == "llm_runtime_embeddings" ) && "${LLM_RUNTIME_CPU_SUPPORTED:-true}" == "false" ]]; then
  if llm_runtime_disable_local_requested && ! llm_routing_requires_local_runtime; then
    die "${target_service} is unsupported on this CPU host and has been disabled for non-local routing."
  fi
  die "${target_service} is unsupported on this CPU host. Use a compatible AVX2/AVX512 CPU or an NVIDIA GPU host."
fi

if [[ "${target_service}" == "llm_runtime_inference" ]]; then
  validate_llm_inference_local_model_path
fi
if [[ "${target_service}" == "llm_runtime_embeddings" ]]; then
  validate_llm_embeddings_local_model_path
fi
if [[ "${target_service}" == "llm" ]]; then
  validate_all_llm_local_model_paths
fi
if [[ "${target_service}" == "llama_cpp" ]]; then
  llama_cpp_enabled_requested || die "llama_cpp is disabled. Add llama_cpp to VANESSA_ENABLED_OPTIONAL_SERVICES to enable the optional llama.cpp runtime."
  validate_llama_cpp_model_path
fi
if [[ "${target_service}" == "qdrant" ]]; then
  qdrant_enabled_requested || die "qdrant is disabled. Add qdrant to VANESSA_ENABLED_OPTIONAL_SERVICES to enable the optional Qdrant runtime."
fi
if [[ "${target_service}" == "searxng" ]]; then
  web_search_enabled_requested || die "searxng is disabled. Add web_search to VANESSA_ENABLED_OPTIONAL_SERVICES to enable the optional web-search runtime."
fi
if [[ "${target_service}" == "kws" ]]; then
  kws_enabled_requested || die "kws is disabled. Add kws to VANESSA_ENABLED_OPTIONAL_SERVICES to enable the optional wake-word runtime."
fi
if [[ "${target_service}" == "image_analysis" ]]; then
  image_analysis_enabled_requested || die "image_analysis is disabled. Add image_analysis to VANESSA_ENABLED_OPTIONAL_SERVICES to enable the optional image-analysis runtime."
  with_deps=true
fi
if [[ "${target_service}" == image_analysis_* ]]; then
  image_analysis_enabled_requested || die "${target_service} is disabled. Add image_analysis to VANESSA_ENABLED_OPTIONAL_SERVICES to enable the optional image-analysis runtime."
  validate_image_analysis_worker_selection
  worker_role="$(image_analysis_worker_role_for_service "${target_service}")"
  if ! image_analysis_worker_enabled "${worker_role}"; then
    die "${target_service} is disabled by IMAGE_ANALYSIS_WORKERS=${IMAGE_ANALYSIS_WORKERS:-anpr,objects,captioning}. Add '${worker_role}' to IMAGE_ANALYSIS_WORKERS to start it."
  fi
fi
if [[ "${target_service}" == "image_generation" ]]; then
  image_generation_enabled_requested || die "image_generation is disabled. Add image_generation to VANESSA_ENABLED_OPTIONAL_SERVICES to enable the optional image-generation runtime."
  with_deps=true
fi
if [[ "${target_service}" == image_generation_* ]]; then
  image_generation_enabled_requested || die "${target_service} is disabled. Add image_generation to VANESSA_ENABLED_OPTIONAL_SERVICES to enable the optional image-generation runtime."
  validate_image_generation_worker_selection
  generation_worker_role="$(image_generation_worker_role_for_service "${target_service}")"
  if ! image_generation_worker_enabled "${generation_worker_role}"; then
    die "${target_service} is disabled by IMAGE_GENERATION_WORKERS=${IMAGE_GENERATION_WORKERS:-text_to_image,plate_logo}. Add '${generation_worker_role}' to IMAGE_GENERATION_WORKERS to start it."
  fi
fi
if image_analysis_enabled_requested; then
  validate_image_analysis_worker_selection
fi
if image_generation_enabled_requested; then
  validate_image_generation_worker_selection
fi
validate_llm_cpu_thread_binding

if [[ "${build_mode}" == "auto" ]]; then
  if [[ "${target_service}" == image_analysis* ]]; then
    build_mode=false
    log_info "Image-analysis restart defaults to --no-build because worker images carry heavy ML dependencies. Pass --build when you need to rebuild them."
  elif [[ "${target_service}" == image_generation* ]]; then
    build_mode=false
    log_info "Image-generation restart defaults to --no-build because worker images can carry heavy ML dependencies. Pass --build when you need to rebuild them."
  else
    build_mode=true
  fi
fi

log_info "Validating compose configuration"
compose config >/dev/null || die "Compose configuration is invalid"

compose_args=(-d)
if [[ "${build_mode}" == true ]]; then
  compose_args+=(--build)
fi
if [[ "${with_deps}" == false ]]; then
  compose_args+=(--no-deps)
fi

compose_targets=("${target_service}")
if [[ "${target_service}" == "image_analysis" ]]; then
  mapfile -t compose_targets < <(image_analysis_selected_services)
fi
if [[ "${target_service}" == "image_generation" ]]; then
  mapfile -t compose_targets < <(image_generation_selected_services)
fi

log_info "Restarting service '${target_service}'"
if ! compose up "${compose_args[@]}" "${compose_targets[@]}"; then
  if [[ ( "${target_service}" == "llm_runtime_inference" || "${target_service}" == "llm_runtime_embeddings" ) && "${resolved_accelerator}" == "cpu" ]]; then
    log_warn "CPU vLLM builds require the PyTorch CPU wheel index. Current LLM_RUNTIME_CPU_TORCH_INDEX_URL=${LLM_RUNTIME_CPU_TORCH_INDEX_URL:-https://download.pytorch.org/whl/cpu}"
    log_warn "CPU ${target_service} failed with accelerator=${resolved_accelerator}, variant=${resolved_cpu_variant}, bind=${VLLM_CPU_OMP_THREADS_BIND_DEFAULT}. Try bind fallback order: 0-7, auto, nobind."
  fi
  die "Failed to restart service: ${target_service}"
fi

if [[ "${wait_mode}" == true ]]; then
  wait_for_service || exit 2
fi

exit 0
