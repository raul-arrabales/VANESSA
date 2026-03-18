#!/usr/bin/env bash
set -euo pipefail

COMMON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_STAGING_DIR="$(cd "${COMMON_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${LOCAL_STAGING_DIR}/../.." && pwd)"

LOCAL_ENV_FILE="${LOCAL_STAGING_DIR}/.env.local"
if [[ -f "${LOCAL_ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${LOCAL_ENV_FILE}"
  set +a
fi

COMPOSE_FILE="${COMPOSE_FILE:-infra/docker-compose.yml}"
START_TIMEOUT_SECONDS="${START_TIMEOUT_SECONDS:-180}"
LOG_TAIL_LINES="${LOG_TAIL_LINES:-200}"
COMPOSE_ENV_FILE="${COMPOSE_ENV_FILE:-}"
LLM_RUNTIME_ACCELERATOR="${LLM_RUNTIME_ACCELERATOR:-auto}"
LLM_RUNTIME_CPU_VARIANT="${LLM_RUNTIME_CPU_VARIANT:-auto}"
LLM_RUNTIME_DISABLE_LOCAL_ON_UNSUPPORTED_CPU="${LLM_RUNTIME_DISABLE_LOCAL_ON_UNSUPPORTED_CPU:-false}"
LLM_LOCAL_MODEL_PATH="${LLM_LOCAL_MODEL_PATH:-/models/llm/Qwen--Qwen2.5-0.5B-Instruct}"
VLLM_CPU_OMP_THREADS_BIND_DEFAULT="${VLLM_CPU_OMP_THREADS_BIND:-0-7}"

readonly SERVICES=(frontend backend llm llm_runtime llama_cpp qdrant mcp_gateway agent_engine sandbox kws weaviate postgres)

now_ts() {
  date +"%Y-%m-%dT%H:%M:%S%z"
}

log_info() {
  printf '[%s] [INFO] %s\n' "$(now_ts)" "$*"
}

log_warn() {
  printf '[%s] [WARN] %s\n' "$(now_ts)" "$*" >&2
}

log_error() {
  printf '[%s] [ERROR] %s\n' "$(now_ts)" "$*" >&2
}

die() {
  log_error "$*"
  exit 1
}

resolve_compose_file() {
  local compose_file="$1"
  if [[ "${compose_file}" = /* ]]; then
    printf '%s\n' "${compose_file}"
  else
    printf '%s\n' "${REPO_ROOT}/${compose_file}"
  fi
}

detect_llm_runtime_accelerator() {
  if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; then
    printf 'gpu\n'
    return 0
  fi
  printf 'cpu\n'
}

docker_has_nvidia_runtime() {
  local runtimes
  runtimes="$(docker info --format '{{json .Runtimes}}' 2>/dev/null || true)"
  [[ "${runtimes}" == *'"nvidia"'* ]]
}

detect_low_capability_nvidia_gpu() {
  local query_output
  query_output="$(nvidia-smi --query-gpu=name,compute_cap --format=csv,noheader 2>/dev/null || true)"
  [[ -n "${query_output}" ]] || return 1

  local line gpu_name compute_cap major_cap minor_cap
  while IFS= read -r line; do
    [[ -n "${line}" ]] || continue
    gpu_name="$(printf '%s' "${line}" | cut -d',' -f1 | xargs)"
    compute_cap="$(printf '%s' "${line}" | cut -d',' -f2 | xargs)"
    [[ "${compute_cap}" =~ ^[0-9]+\.[0-9]+$ ]] || continue
    major_cap="${compute_cap%%.*}"
    minor_cap="${compute_cap#*.}"
    if (( major_cap < 6 )); then
      printf '%s,%s\n' "${gpu_name}" "${major_cap}.${minor_cap}"
      return 0
    fi
  done <<< "${query_output}"

  return 1
}

validate_docker_gpu_runtime() {
  if ! command -v nvidia-smi >/dev/null 2>&1 || ! nvidia-smi -L >/dev/null 2>&1; then
    die "LLM runtime accelerator is set to gpu, but NVIDIA drivers are not available on the host."
  fi

  if ! docker_has_nvidia_runtime; then
    die "LLM runtime accelerator resolved to gpu, but Docker does not advertise an NVIDIA runtime. Install/configure nvidia-container-toolkit and restart Docker."
  fi

  local low_capability_gpu
  low_capability_gpu="$(detect_low_capability_nvidia_gpu || true)"
  if [[ -n "${low_capability_gpu}" ]]; then
    local gpu_name="${low_capability_gpu%%,*}"
    local compute_cap="${low_capability_gpu#*,}"
    die "LLM runtime accelerator resolved to gpu, but detected GPU '${gpu_name}' has compute capability ${compute_cap}. The shipped CUDA 12 vLLM image requires a newer NVIDIA GPU; use CPU mode or a newer GPU."
  fi
}

cpu_has_flag() {
  local flag="$1"
  lscpu 2>/dev/null | tr '[:upper:]' '[:lower:]' | tr ' ' '\n' | grep -qx "${flag}"
}

resolve_llm_runtime_accelerator() {
  local requested="${LLM_RUNTIME_ACCELERATOR:-auto}"
  requested="$(printf '%s' "${requested}" | tr '[:upper:]' '[:lower:]')"
  case "${requested}" in
    cpu|gpu)
      printf '%s\n' "${requested}"
      ;;
    auto|"")
      detect_llm_runtime_accelerator
      ;;
    *)
      die "Invalid LLM_RUNTIME_ACCELERATOR: ${LLM_RUNTIME_ACCELERATOR}. Valid values: auto, cpu, gpu"
      ;;
  esac
}

detect_llm_runtime_cpu_variant() {
  if cpu_has_flag avx512f; then
    printf 'avx512\n'
    return 0
  fi
  if cpu_has_flag avx2; then
    printf 'avx2\n'
    return 0
  fi
  printf 'unsupported\n'
}

resolve_llm_runtime_cpu_variant() {
  local requested="${LLM_RUNTIME_CPU_VARIANT:-auto}"
  requested="$(printf '%s' "${requested}" | tr '[:upper:]' '[:lower:]')"
  case "${requested}" in
    avx2|avx512)
      printf '%s\n' "${requested}"
      ;;
    auto|"")
      detect_llm_runtime_cpu_variant
      ;;
    *)
      die "Invalid LLM_RUNTIME_CPU_VARIANT: ${LLM_RUNTIME_CPU_VARIANT}. Valid values: auto, avx2, avx512"
      ;;
  esac
}

llm_runtime_disable_local_requested() {
  local value="${LLM_RUNTIME_DISABLE_LOCAL_ON_UNSUPPORTED_CPU:-false}"
  value="$(printf '%s' "${value}" | tr '[:upper:]' '[:lower:]')"
  [[ "${value}" == "1" || "${value}" == "true" || "${value}" == "yes" || "${value}" == "on" ]]
}

llm_routing_requires_local_runtime() {
  local routing_mode="${LLM_ROUTING_MODE:-local_only}"
  routing_mode="$(printf '%s' "${routing_mode}" | tr '[:upper:]' '[:lower:]')"
  [[ "${routing_mode}" == "local_only" ]]
}

validate_llm_runtime_support() {
  local accelerator="${RESOLVED_LLM_RUNTIME_ACCELERATOR:-$(resolve_llm_runtime_accelerator)}"

  if [[ "${accelerator}" == "gpu" ]]; then
    validate_docker_gpu_runtime
    export LLM_RUNTIME_CPU_SUPPORTED=true
    return 0
  fi

  local variant="${RESOLVED_LLM_RUNTIME_CPU_VARIANT:-$(resolve_llm_runtime_cpu_variant)}"
  if [[ "${variant}" == "unsupported" ]]; then
    export LLM_RUNTIME_CPU_SUPPORTED=false
    if llm_routing_requires_local_runtime && ! llm_runtime_disable_local_requested; then
      die "CPU host does not advertise avx2 or avx512f; local llm_runtime is unsupported on this machine."
    fi
    return 1
  fi

  export LLM_RUNTIME_CPU_SUPPORTED=true
  return 0
}

max_host_cpu_index() {
  lscpu -p=cpu 2>/dev/null | grep -v '^#' | awk 'max < $1 { max = $1 } END { if (NR == 0) { print "-1" } else { print max } }'
}

resolve_llm_cpu_thread_binding() {
  if [[ "${VLLM_CPU_OMP_THREADS_BIND+x}" == "x" && -z "${VLLM_CPU_OMP_THREADS_BIND}" ]]; then
    printf '\n'
    return 0
  fi

  printf '%s\n' "${VLLM_CPU_OMP_THREADS_BIND_DEFAULT}"
}

validate_llm_cpu_thread_binding() {
  local accelerator="${RESOLVED_LLM_RUNTIME_ACCELERATOR:-$(resolve_llm_runtime_accelerator)}"
  [[ "${accelerator}" == "cpu" ]] || return 0

  local binding
  binding="$(resolve_llm_cpu_thread_binding)"

  if [[ -z "${binding}" ]]; then
    die "Invalid VLLM_CPU_OMP_THREADS_BIND='' for CPU runtime. Use 0-7, auto, or nobind."
  fi

  case "${binding}" in
    auto|nobind)
      return 0
      ;;
  esac

  if ! [[ "${binding}" =~ ^[0-9,\|-]+$ ]]; then
    die "Invalid VLLM_CPU_OMP_THREADS_BIND='${binding}' for CPU runtime. Use 0-7, auto, nobind, or a CPU set like 0-3|4-7."
  fi

  local max_cpu
  max_cpu="$(max_host_cpu_index)"
  [[ "${max_cpu}" =~ ^[0-9]+$ ]] || die "Unable to determine host CPU topology for VLLM_CPU_OMP_THREADS_BIND validation."

  local rank_set part start end
  local old_ifs="${IFS}"
  IFS='|'
  for rank_set in ${binding}; do
    IFS=','
    for part in ${rank_set}; do
      if [[ "${part}" =~ ^[0-9]+-[0-9]+$ ]]; then
        start="${part%-*}"
        end="${part#*-}"
        if (( start > end )); then
          IFS="${old_ifs}"
          die "Invalid VLLM_CPU_OMP_THREADS_BIND='${binding}': range '${part}' is reversed."
        fi
        if (( end > max_cpu )); then
          IFS="${old_ifs}"
          die "Invalid VLLM_CPU_OMP_THREADS_BIND='${binding}': CPU '${end}' exceeds host max CPU index ${max_cpu}."
        fi
      elif [[ "${part}" =~ ^[0-9]+$ ]]; then
        if (( part > max_cpu )); then
          IFS="${old_ifs}"
          die "Invalid VLLM_CPU_OMP_THREADS_BIND='${binding}': CPU '${part}' exceeds host max CPU index ${max_cpu}."
        fi
      else
        IFS="${old_ifs}"
        die "Invalid VLLM_CPU_OMP_THREADS_BIND='${binding}'. Use 0-7, auto, nobind, or a CPU set like 0-3|4-7."
      fi
    done
  done
  IFS="${old_ifs}"
}

llm_runtime_internal_http_ok() {
  local path="$1"
  compose exec -T llm_runtime python -c "import sys, urllib.request; sys.exit(0 if 200 <= getattr(urllib.request.urlopen('http://127.0.0.1:8000${path}', timeout=3), 'status', 500) < 400 else 1)" >/dev/null 2>&1
}

llama_cpp_enabled_requested() {
  [[ -n "${LLAMA_CPP_URL:-}" ]]
}

llama_cpp_internal_http_ok() {
  local path="$1"
  compose exec -T llama_cpp python -c "import sys, urllib.request; sys.exit(0 if 200 <= getattr(urllib.request.urlopen('http://127.0.0.1:8080${path}', timeout=3), 'status', 500) < 400 else 1)" >/dev/null 2>&1
}

qdrant_enabled_requested() {
  [[ -n "${QDRANT_URL:-}" ]]
}

qdrant_internal_http_ok() {
  local path="$1"
  compose exec -T qdrant python -c "import sys, urllib.request; sys.exit(0 if 200 <= getattr(urllib.request.urlopen('http://127.0.0.1:6333${path}', timeout=3), 'status', 500) < 400 else 1)" >/dev/null 2>&1
}

mcp_gateway_enabled_requested() {
  [[ -n "${MCP_GATEWAY_URL:-}" ]]
}

mcp_gateway_internal_http_ok() {
  local path="$1"
  compose exec -T mcp_gateway python -c "import sys, urllib.request; sys.exit(0 if 200 <= getattr(urllib.request.urlopen('http://127.0.0.1:6100${path}', timeout=3), 'status', 500) < 400 else 1)" >/dev/null 2>&1
}

resolve_llm_local_model_host_path() {
  local model_path="${LLM_LOCAL_MODEL_PATH:-/models/llm/Qwen--Qwen2.5-0.5B-Instruct}"
  if [[ "${model_path}" == /models/llm/* ]]; then
    printf '%s\n' "${REPO_ROOT}/models/llm/${model_path#/models/llm/}"
    return 0
  fi
  printf '%s\n' "${model_path}"
}

validate_llm_local_model_path() {
  local model_path="${LLM_LOCAL_MODEL_PATH:-/models/llm/Qwen--Qwen2.5-0.5B-Instruct}"
  local host_model_path
  host_model_path="$(resolve_llm_local_model_host_path)"

  if [[ ! -d "${host_model_path}" ]]; then
    die "Configured LLM_LOCAL_MODEL_PATH=${model_path} does not exist on host at ${host_model_path}."
  fi

  if [[ ! -f "${host_model_path}/config.json" && ! -f "${host_model_path}/params.json" ]]; then
    die "Configured LLM_LOCAL_MODEL_PATH=${model_path} is missing config.json or params.json at ${host_model_path}."
  fi
}

resolve_llama_cpp_model_host_path() {
  local model_path="${LLAMA_CPP_MODEL_PATH:-}"
  if [[ "${model_path}" == /models/llm/* ]]; then
    printf '%s\n' "${REPO_ROOT}/models/llm/${model_path#/models/llm/}"
    return 0
  fi
  printf '%s\n' "${model_path}"
}

validate_llama_cpp_model_path() {
  local model_path="${LLAMA_CPP_MODEL_PATH:-}"
  [[ -n "${model_path}" ]] || die "LLAMA_CPP_MODEL_PATH must be set when LLAMA_CPP_URL enables the llama.cpp runtime."

  local host_model_path
  host_model_path="$(resolve_llama_cpp_model_host_path)"
  if [[ ! -f "${host_model_path}" ]]; then
    die "Configured LLAMA_CPP_MODEL_PATH=${model_path} does not exist on host at ${host_model_path}."
  fi
}

compose_file_args() {
  local resolved_accelerator="${RESOLVED_LLM_RUNTIME_ACCELERATOR:-$(resolve_llm_runtime_accelerator)}"
  local compose_files="${COMPOSE_FILE}"

  if [[ "${resolved_accelerator}" == "gpu" ]]; then
    compose_files="${compose_files}:infra/docker-compose.gpu.override.yml"
  else
    compose_files="${compose_files}:infra/docker-compose.cpu.override.yml"
  fi

  local compose_file
  local old_ifs="${IFS}"
  IFS=':'
  for compose_file in ${compose_files}; do
    [[ -n "${compose_file}" ]] || continue
    printf '%s\0' "$(resolve_compose_file "${compose_file}")"
  done
  IFS="${old_ifs}"
}

compose() {
  RESOLVED_LLM_RUNTIME_ACCELERATOR="${RESOLVED_LLM_RUNTIME_ACCELERATOR:-$(resolve_llm_runtime_accelerator)}"
  RESOLVED_LLM_RUNTIME_CPU_VARIANT="${RESOLVED_LLM_RUNTIME_CPU_VARIANT:-$(resolve_llm_runtime_cpu_variant)}"
  export RESOLVED_LLM_RUNTIME_ACCELERATOR
  export RESOLVED_LLM_RUNTIME_CPU_VARIANT
  export LLM_RUNTIME_ACCELERATOR="${RESOLVED_LLM_RUNTIME_ACCELERATOR}"
  export LLM_RUNTIME_CPU_VARIANT="${RESOLVED_LLM_RUNTIME_CPU_VARIANT}"

  if [[ "${RESOLVED_LLM_RUNTIME_CPU_VARIANT}" == "avx512" ]]; then
    export LLM_RUNTIME_CPU_BUILD_DISABLE_AVX512=false
    export LLM_RUNTIME_CPU_BUILD_AVX2=false
    export LLM_RUNTIME_CPU_BUILD_AVX512=true
  elif [[ "${RESOLVED_LLM_RUNTIME_CPU_VARIANT}" == "avx2" ]]; then
    export LLM_RUNTIME_CPU_BUILD_DISABLE_AVX512=true
    export LLM_RUNTIME_CPU_BUILD_AVX2=true
    export LLM_RUNTIME_CPU_BUILD_AVX512=false
  else
    export LLM_RUNTIME_CPU_BUILD_DISABLE_AVX512=true
    export LLM_RUNTIME_CPU_BUILD_AVX2=false
    export LLM_RUNTIME_CPU_BUILD_AVX512=false
  fi

  if ! validate_llm_runtime_support; then
    log_warn "Local llm_runtime CPU support is unavailable on this host."
    if llm_runtime_disable_local_requested; then
      log_warn "LLM_RUNTIME_DISABLE_LOCAL_ON_UNSUPPORTED_CPU is enabled; local-only routing must be disabled to run without llm_runtime."
    fi
  fi

  local -a cmd=(docker compose)
  if llama_cpp_enabled_requested; then
    cmd+=(--profile llama_cpp)
  fi
  if qdrant_enabled_requested; then
    cmd+=(--profile qdrant)
  fi
  if mcp_gateway_enabled_requested; then
    cmd+=(--profile mcp_gateway)
  fi
  local compose_path
  while IFS= read -r -d '' compose_path; do
    cmd+=(-f "${compose_path}")
  done < <(compose_file_args)
  if [[ -n "${COMPOSE_ENV_FILE}" ]]; then
    cmd+=(--env-file "${COMPOSE_ENV_FILE}")
  fi

  "${cmd[@]}" "$@"
}

stack_services_for_start() {
  local -a services_to_start=()
  local service
  for service in "${SERVICES[@]}"; do
    if [[ "${service}" == "llama_cpp" ]] && ! llama_cpp_enabled_requested; then
      continue
    fi
    if [[ "${service}" == "qdrant" ]] && ! qdrant_enabled_requested; then
      continue
    fi
    if [[ "${service}" == "mcp_gateway" ]] && ! mcp_gateway_enabled_requested; then
      continue
    fi
    services_to_start+=("${service}")
  done

  local cpu_supported="${LLM_RUNTIME_CPU_SUPPORTED:-true}"
  if [[ "${cpu_supported}" == "false" ]] && llm_runtime_disable_local_requested && ! llm_routing_requires_local_runtime; then
    for service in "${services_to_start[@]}"; do
      if [[ "${service}" != "llm_runtime" ]]; then
        printf '%s\n' "${service}"
      fi
    done
    return 0
  fi

  printf '%s\n' "${services_to_start[@]}"
}

require_cmd() {
  local cmd_name="$1"
  command -v "${cmd_name}" >/dev/null 2>&1 || die "Missing required command: ${cmd_name}"
}

require_prerequisites() {
  require_cmd docker
  require_cmd curl

  docker compose version >/dev/null 2>&1 || die "Docker Compose plugin is required (docker compose)."

  if ! command -v nc >/dev/null 2>&1; then
    log_warn "'nc' not found. Falling back to bash /dev/tcp checks for PostgreSQL."
  fi
}

is_valid_service() {
  local target="$1"
  local svc
  for svc in "${SERVICES[@]}"; do
    if [[ "${svc}" == "${target}" ]]; then
      return 0
    fi
  done
  return 1
}
