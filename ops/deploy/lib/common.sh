#!/usr/bin/env bash
set -euo pipefail

COMMON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(cd "${COMMON_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${DEPLOY_DIR}/../.." && pwd)"
MODE_DIR="${DEPLOY_DIR}/modes"
LAUNCHER_ENV_DIR="${DEPLOY_DIR}/env"
LOCAL_STAGING_DIR="${REPO_ROOT}/ops/local-staging"
INFRA_DIR="${REPO_ROOT}/infra"

capture_env_override() {
  local var_name="$1"
  local shadow_name="__ORIG_${var_name}"
  if [[ -v "${var_name}" ]]; then
    printf -v "${shadow_name}" '%s' "${!var_name}"
    export "${shadow_name}"
  fi
}

restore_env_override() {
  local var_name="$1"
  local shadow_name="__ORIG_${var_name}"
  if [[ -v "${shadow_name}" ]]; then
    printf -v "${var_name}" '%s' "${!shadow_name}"
    export "${var_name}"
    unset "${shadow_name}"
  fi
}

normalize_deployment_mode() {
  local value="${1:-local_staging}"
  value="$(printf '%s' "${value}" | tr '[:upper:]' '[:lower:]' | tr '-' '_' | xargs)"
  case "${value}" in
    local_staging|cloud_compose|lan_server)
      printf '%s\n' "${value}"
      ;;
    *)
      printf 'invalid\n'
      ;;
  esac
}

deployment_mode_file_stem() {
  printf '%s\n' "${VANESSA_DEPLOYMENT_MODE}" | tr '_' '-'
}

source_env_file_if_present() {
  local file_path="$1"
  if [[ -f "${file_path}" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "${file_path}"
    set +a
  fi
}

source_runtime_env_file_if_present() {
  local file_path="$1"
  if [[ -n "${file_path}" && -f "${file_path}" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "${file_path}"
    set +a
  fi
}

load_runtime_env_layers() {
  runtime_env_base_path="$(runtime_env_path "${VANESSA_RUNTIME_ENV_BASE_FILE}")"
  runtime_env_mode_path="$(runtime_env_path "${VANESSA_RUNTIME_ENV_MODE_FILE}")"
  runtime_env_legacy_override_path="$(runtime_env_path "${VANESSA_RUNTIME_ENV_LEGACY_OVERRIDE_FILE}")"
  runtime_env_cli_override_path=""
  if [[ -n "${COMPOSE_ENV_FILE}" ]]; then
    if [[ "${COMPOSE_ENV_FILE}" = /* ]]; then
      runtime_env_cli_override_path="${COMPOSE_ENV_FILE}"
    else
      runtime_env_cli_override_path="${REPO_ROOT}/${COMPOSE_ENV_FILE}"
    fi
  fi

  source_runtime_env_file_if_present "${runtime_env_base_path}"
  source_runtime_env_file_if_present "${runtime_env_mode_path}"
  source_runtime_env_file_if_present "${runtime_env_legacy_override_path}"
  source_runtime_env_file_if_present "${runtime_env_cli_override_path}"
}

VANESSA_DEPLOYMENT_MODE="$(normalize_deployment_mode "${VANESSA_DEPLOYMENT_MODE:-local_staging}")"
[[ "${VANESSA_DEPLOYMENT_MODE}" != "invalid" ]] || {
  printf '[ERROR] Invalid VANESSA_DEPLOYMENT_MODE: %s\n' "${VANESSA_DEPLOYMENT_MODE:-}" >&2
  exit 1
}
readonly VANESSA_DEPLOYMENT_MODE

DEPLOYMENT_MODE_FILE_STEM="$(deployment_mode_file_stem)"
readonly DEPLOYMENT_MODE_FILE_STEM

for override_var in \
  COMPOSE_FILE \
  START_TIMEOUT_SECONDS \
  LOG_TAIL_LINES \
  COMPOSE_ENV_FILE \
  LLM_RUNTIME_ACCELERATOR \
  LLM_RUNTIME_CPU_VARIANT \
  LLM_RUNTIME_DISABLE_LOCAL_ON_UNSUPPORTED_CPU \
  LLM_INFERENCE_LOCAL_MODEL_PATH \
  LLM_EMBEDDINGS_LOCAL_MODEL_PATH \
  LLM_ROUTING_MODE \
  LLM_REQUEST_TIMEOUT_SECONDS \
  VANESSA_ENABLED_OPTIONAL_SERVICES \
  VANESSA_RUNTIME_ENV_BASE_FILE \
  VANESSA_RUNTIME_ENV_MODE_FILE \
  VANESSA_RUNTIME_ENV_LEGACY_OVERRIDE_FILE \
  VANESSA_RUNTIME_ENV_ACTIVE_FILE
do
  capture_env_override "${override_var}"
done

MODE_DESCRIPTOR_FILE="${MODE_DIR}/${DEPLOYMENT_MODE_FILE_STEM}.env"
[[ -f "${MODE_DESCRIPTOR_FILE}" ]] || {
  printf '[ERROR] Missing deployment mode descriptor: %s\n' "${MODE_DESCRIPTOR_FILE}" >&2
  exit 1
}
source_env_file_if_present "${MODE_DESCRIPTOR_FILE}"

CANONICAL_LAUNCHER_ENV_FILE="${LAUNCHER_ENV_DIR}/${DEPLOYMENT_MODE_FILE_STEM}.env"
source_env_file_if_present "${CANONICAL_LAUNCHER_ENV_FILE}"
if [[ "${VANESSA_DEPLOYMENT_MODE}" == "local_staging" ]]; then
  source_env_file_if_present "${LOCAL_STAGING_DIR}/.env.local"
fi

for override_var in \
  COMPOSE_FILE \
  START_TIMEOUT_SECONDS \
  LOG_TAIL_LINES \
  COMPOSE_ENV_FILE \
  LLM_RUNTIME_ACCELERATOR \
  LLM_RUNTIME_CPU_VARIANT \
  LLM_RUNTIME_DISABLE_LOCAL_ON_UNSUPPORTED_CPU \
  LLM_INFERENCE_LOCAL_MODEL_PATH \
  LLM_EMBEDDINGS_LOCAL_MODEL_PATH \
  LLM_ROUTING_MODE \
  LLM_REQUEST_TIMEOUT_SECONDS \
  VANESSA_ENABLED_OPTIONAL_SERVICES \
  VANESSA_RUNTIME_ENV_BASE_FILE \
  VANESSA_RUNTIME_ENV_MODE_FILE \
  VANESSA_RUNTIME_ENV_LEGACY_OVERRIDE_FILE \
  VANESSA_RUNTIME_ENV_ACTIVE_FILE
do
  restore_env_override "${override_var}"
done

COMPOSE_FILE="${COMPOSE_FILE:-${VANESSA_MODE_COMPOSE_FILES:-infra/docker-compose.yml:infra/docker-compose.${DEPLOYMENT_MODE_FILE_STEM}.override.yml}}"
START_TIMEOUT_SECONDS="${START_TIMEOUT_SECONDS:-180}"
LOG_TAIL_LINES="${LOG_TAIL_LINES:-200}"
COMPOSE_ENV_FILE="${COMPOSE_ENV_FILE:-}"
LLM_RUNTIME_ACCELERATOR="${LLM_RUNTIME_ACCELERATOR:-auto}"
LLM_RUNTIME_CPU_VARIANT="${LLM_RUNTIME_CPU_VARIANT:-auto}"
LLM_RUNTIME_DISABLE_LOCAL_ON_UNSUPPORTED_CPU="${LLM_RUNTIME_DISABLE_LOCAL_ON_UNSUPPORTED_CPU:-false}"
LLM_LOCAL_MODEL_PATH="${LLM_LOCAL_MODEL_PATH:-/models/llm/Qwen--Qwen2.5-0.5B-Instruct}"
LLM_INFERENCE_LOCAL_MODEL_PATH="${LLM_INFERENCE_LOCAL_MODEL_PATH:-${LLM_LOCAL_MODEL_PATH}}"
LLM_EMBEDDINGS_LOCAL_MODEL_PATH="${LLM_EMBEDDINGS_LOCAL_MODEL_PATH:-}"
VLLM_CPU_OMP_THREADS_BIND_DEFAULT="${VLLM_CPU_OMP_THREADS_BIND:-0-7}"
VANESSA_ALLOWED_OPTIONAL_SERVICES="${VANESSA_ALLOWED_OPTIONAL_SERVICES:-llama_cpp,qdrant,image_analysis,image_generation,web_search,kws}"
VANESSA_ENABLED_OPTIONAL_SERVICES="${VANESSA_ENABLED_OPTIONAL_SERVICES:-${VANESSA_DEFAULT_OPTIONAL_SERVICES:-web_search}}"
VANESSA_ALLOW_SAMPLE_USER_SEEDING="${VANESSA_ALLOW_SAMPLE_USER_SEEDING:-false}"
VANESSA_RUNTIME_ENV_BASE_FILE="${VANESSA_RUNTIME_ENV_BASE_FILE:-.env.example}"
VANESSA_RUNTIME_ENV_MODE_FILE="${VANESSA_RUNTIME_ENV_MODE_FILE:-env/${DEPLOYMENT_MODE_FILE_STEM}.env}"
VANESSA_RUNTIME_ENV_LEGACY_OVERRIDE_FILE="${VANESSA_RUNTIME_ENV_LEGACY_OVERRIDE_FILE:-.env.local}"
VANESSA_RUNTIME_ENV_ACTIVE_FILE="${VANESSA_RUNTIME_ENV_ACTIVE_FILE:-/tmp/vanessa-runtime-${DEPLOYMENT_MODE_FILE_STEM}.active.env}"

runtime_env_path() {
  local relative_or_absolute="$1"
  if [[ -z "${relative_or_absolute}" ]]; then
    return 0
  fi
  if [[ "${relative_or_absolute}" = /* ]]; then
    printf '%s\n' "${relative_or_absolute}"
  else
    printf '%s\n' "${INFRA_DIR}/${relative_or_absolute}"
  fi
}

load_runtime_env_layers

SERVICE_REGISTRY_FILE="${LOCAL_STAGING_DIR}/services.txt"
if [[ ! -f "${SERVICE_REGISTRY_FILE}" ]]; then
  printf '[ERROR] Missing service registry: %s\n' "${SERVICE_REGISTRY_FILE}" >&2
  exit 1
fi
mapfile -t SERVICES < <(grep -v '^[[:space:]]*#' "${SERVICE_REGISTRY_FILE}" | sed '/^[[:space:]]*$/d')
readonly SERVICE_REGISTRY_FILE
readonly SERVICES

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

service_list_contains() {
  local needle="$1"
  local haystack="$2"
  local normalized_haystack
  normalized_haystack="$(printf '%s' "${haystack}" | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]')"
  [[ ",${normalized_haystack}," == *",${needle},"* ]]
}

optional_service_enabled() {
  local service_key="$1"
  service_list_contains "${service_key}" "${VANESSA_ENABLED_OPTIONAL_SERVICES}"
}

validate_optional_services_config() {
  local allowed=" ${VANESSA_ALLOWED_OPTIONAL_SERVICES//,/ } "
  local raw normalized old_ifs item seen=" "
  raw="${VANESSA_ENABLED_OPTIONAL_SERVICES:-}"
  normalized="$(printf '%s' "${raw}" | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]')"
  [[ -z "${normalized}" ]] && return 0

  old_ifs="${IFS}"
  IFS=','
  for item in ${normalized}; do
    [[ -n "${item}" ]] || continue
    case " ${allowed} " in
      *" ${item} "*) ;;
      *) IFS="${old_ifs}"; die "Invalid VANESSA_ENABLED_OPTIONAL_SERVICES entry '${item}'. Allowed values: ${VANESSA_ALLOWED_OPTIONAL_SERVICES}" ;;
    esac
    if [[ "${seen}" == *" ${item} "* ]]; then
      IFS="${old_ifs}"
      die "Duplicate VANESSA_ENABLED_OPTIONAL_SERVICES entry '${item}'"
    fi
    seen="${seen}${item} "
  done
  IFS="${old_ifs}"
}

default_optional_service_url() {
  case "$1" in
    llama_cpp) printf '%s\n' "${LLAMA_CPP_URL_DEFAULT:-http://llama_cpp:8080}" ;;
    qdrant) printf '%s\n' "${QDRANT_URL_DEFAULT:-http://qdrant:6333}" ;;
    image_analysis) printf '%s\n' "${IMAGE_ANALYSIS_URL_DEFAULT:-http://image_analysis:8090}" ;;
    image_generation) printf '%s\n' "${IMAGE_GENERATION_URL_DEFAULT:-http://image_generation:8094}" ;;
    web_search) printf '%s\n' "${WEB_SEARCH_URL_DEFAULT:-http://searxng:8080}" ;;
    *) printf '\n' ;;
  esac
}

write_runtime_activation_env() {
  local active_file="${VANESSA_RUNTIME_ENV_ACTIVE_FILE}"
  mkdir -p "$(dirname "${active_file}")"
  : > "${active_file}"
  printf 'VANESSA_DEPLOYMENT_MODE=%s\n' "${VANESSA_DEPLOYMENT_MODE}" >> "${active_file}"

  local llama_cpp_url="${LLAMA_CPP_URL:-}"
  local qdrant_url="${QDRANT_URL:-}"
  local image_analysis_url="${IMAGE_ANALYSIS_URL:-}"
  local image_generation_url="${IMAGE_GENERATION_URL:-}"
  local web_search_url="${WEB_SEARCH_URL:-}"
  local kws_enabled_value="false"
  local web_search_enabled_value="false"

  if optional_service_enabled "llama_cpp"; then
    [[ -n "${llama_cpp_url}" ]] || llama_cpp_url="$(default_optional_service_url "llama_cpp")"
  else
    llama_cpp_url=""
  fi
  if optional_service_enabled "qdrant"; then
    [[ -n "${qdrant_url}" ]] || qdrant_url="$(default_optional_service_url "qdrant")"
  else
    qdrant_url=""
  fi
  if optional_service_enabled "image_analysis"; then
    [[ -n "${image_analysis_url}" ]] || image_analysis_url="$(default_optional_service_url "image_analysis")"
  else
    image_analysis_url=""
  fi
  if optional_service_enabled "image_generation"; then
    [[ -n "${image_generation_url}" ]] || image_generation_url="$(default_optional_service_url "image_generation")"
  else
    image_generation_url=""
  fi
  if optional_service_enabled "web_search"; then
    web_search_enabled_value="true"
    [[ -n "${web_search_url}" ]] || web_search_url="$(default_optional_service_url "web_search")"
  else
    web_search_url=""
  fi
  if optional_service_enabled "kws"; then
    kws_enabled_value="true"
  fi

  printf 'LLAMA_CPP_URL=%s\n' "${llama_cpp_url}" >> "${active_file}"
  printf 'QDRANT_URL=%s\n' "${qdrant_url}" >> "${active_file}"
  printf 'IMAGE_ANALYSIS_URL=%s\n' "${image_analysis_url}" >> "${active_file}"
  printf 'IMAGE_GENERATION_URL=%s\n' "${image_generation_url}" >> "${active_file}"
  printf 'WEB_SEARCH_ENABLED=%s\n' "${web_search_enabled_value}" >> "${active_file}"
  printf 'WEB_SEARCH_URL=%s\n' "${web_search_url}" >> "${active_file}"
  printf 'KWS_ENABLED=%s\n' "${kws_enabled_value}" >> "${active_file}"
}

validate_optional_services_config
write_runtime_activation_env

reload_runtime_env_context() {
  load_runtime_env_layers
  validate_optional_services_config
  write_runtime_activation_env
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
      die "CPU host does not advertise avx2 or avx512f; local split runtimes are unsupported on this machine."
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
  local service_name="$1"
  local path="$2"
  compose exec -T "${service_name}" python -c "import sys, urllib.request; sys.exit(0 if 200 <= getattr(urllib.request.urlopen('http://127.0.0.1:8000${path}', timeout=3), 'status', 500) < 400 else 1)" >/dev/null 2>&1
}

llama_cpp_enabled_requested() {
  optional_service_enabled "llama_cpp"
}

llama_cpp_internal_http_ok() {
  local path="$1"
  compose exec -T llama_cpp python -c "import sys, urllib.request; sys.exit(0 if 200 <= getattr(urllib.request.urlopen('http://127.0.0.1:8080${path}', timeout=3), 'status', 500) < 400 else 1)" >/dev/null 2>&1
}

qdrant_enabled_requested() {
  optional_service_enabled "qdrant"
}

image_analysis_enabled_requested() {
  optional_service_enabled "image_analysis"
}

image_generation_enabled_requested() {
  optional_service_enabled "image_generation"
}

kws_enabled_requested() {
  optional_service_enabled "kws"
}

web_search_enabled_requested() {
  optional_service_enabled "web_search"
}

image_analysis_workers_raw() {
  local raw="${IMAGE_ANALYSIS_WORKERS:-anpr,objects,captioning}"
  raw="$(printf '%s' "${raw}" | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]')"
  printf '%s\n' "${raw:-anpr,objects,captioning}"
}

image_analysis_worker_role_for_service() {
  case "$1" in
    image_analysis_anpr) printf 'anpr\n' ;;
    image_analysis_objects) printf 'objects\n' ;;
    image_analysis_captioning) printf 'captioning\n' ;;
    *) return 1 ;;
  esac
}

image_analysis_worker_service_for_role() {
  case "$1" in
    anpr) printf 'image_analysis_anpr\n' ;;
    objects) printf 'image_analysis_objects\n' ;;
    captioning) printf 'image_analysis_captioning\n' ;;
    *) return 1 ;;
  esac
}

image_analysis_worker_roles() {
  local raw
  raw="$(image_analysis_workers_raw)"
  [[ "${raw}" == "none" ]] && return 0

  local old_ifs="${IFS}"
  local item
  local emitted=" "
  IFS=','
  for item in ${raw}; do
    [[ -n "${item}" ]] || continue
    case "${item}" in
      anpr|objects|captioning)
        if [[ "${emitted}" != *" ${item} "* ]]; then
          printf '%s\n' "${item}"
          emitted="${emitted}${item} "
        fi
        ;;
    esac
  done
  IFS="${old_ifs}"
}

image_analysis_worker_enabled() {
  local role="$1"
  local enabled_role
  while IFS= read -r enabled_role; do
    [[ "${enabled_role}" == "${role}" ]] && return 0
  done < <(image_analysis_worker_roles)
  return 1
}

image_analysis_selected_services() {
  printf 'image_analysis\n'
  local role
  while IFS= read -r role; do
    image_analysis_worker_service_for_role "${role}"
  done < <(image_analysis_worker_roles)
}

validate_image_analysis_worker_selection() {
  local raw
  raw="$(image_analysis_workers_raw)"
  [[ "${raw}" == "none" ]] && return 0

  local old_ifs="${IFS}"
  local item
  local invalid=()
  local valid_count=0
  IFS=','
  for item in ${raw}; do
    [[ -n "${item}" ]] || continue
    case "${item}" in
      anpr|objects|captioning)
        valid_count=$((valid_count + 1))
        ;;
      *)
        invalid+=("${item}")
        ;;
    esac
  done
  IFS="${old_ifs}"

  if (( ${#invalid[@]} > 0 )); then
    die "Invalid IMAGE_ANALYSIS_WORKERS=${IMAGE_ANALYSIS_WORKERS:-}. Valid values are comma-separated anpr,objects,captioning or none."
  fi
  if (( valid_count == 0 )); then
    die "IMAGE_ANALYSIS_WORKERS must include at least one worker or be set to none."
  fi
}

qdrant_internal_http_ok() {
  local path="$1"
  compose exec -T qdrant python -c "import sys, urllib.request; sys.exit(0 if 200 <= getattr(urllib.request.urlopen('http://127.0.0.1:6333${path}', timeout=3), 'status', 500) < 400 else 1)" >/dev/null 2>&1
}

image_analysis_internal_http_ok() {
  local path="$1"
  compose exec -T image_analysis python -c "import sys, urllib.request; sys.exit(0 if 200 <= getattr(urllib.request.urlopen('http://127.0.0.1:8090${path}', timeout=3), 'status', 500) < 400 else 1)" >/dev/null 2>&1
}

image_analysis_worker_internal_http_ok() {
  local service_name="$1"
  local port="$2"
  local path="$3"
  compose exec -T "${service_name}" python -c "import sys, urllib.request; sys.exit(0 if 200 <= getattr(urllib.request.urlopen('http://127.0.0.1:${port}${path}', timeout=3), 'status', 500) < 400 else 1)" >/dev/null 2>&1
}

image_generation_workers_raw() {
  local raw="${IMAGE_GENERATION_WORKERS:-text_to_image,plate_logo}"
  raw="$(printf '%s' "${raw}" | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]')"
  printf '%s\n' "${raw:-text_to_image,plate_logo}"
}

image_generation_worker_role_for_service() {
  case "$1" in
    image_generation_text_to_image) printf 'text_to_image\n' ;;
    image_generation_plate_logo) printf 'plate_logo\n' ;;
    *) return 1 ;;
  esac
}

image_generation_worker_service_for_role() {
  case "$1" in
    text_to_image) printf 'image_generation_text_to_image\n' ;;
    plate_logo) printf 'image_generation_plate_logo\n' ;;
    *) return 1 ;;
  esac
}

image_generation_worker_roles() {
  local raw
  raw="$(image_generation_workers_raw)"
  [[ "${raw}" == "none" ]] && return 0

  local old_ifs="${IFS}"
  local item
  local emitted=" "
  IFS=','
  for item in ${raw}; do
    [[ -n "${item}" ]] || continue
    case "${item}" in
      text_to_image|plate_logo)
        if [[ "${emitted}" != *" ${item} "* ]]; then
          printf '%s\n' "${item}"
          emitted="${emitted}${item} "
        fi
        ;;
    esac
  done
  IFS="${old_ifs}"
}

image_generation_worker_enabled() {
  local role="$1"
  local enabled_role
  while IFS= read -r enabled_role; do
    [[ "${enabled_role}" == "${role}" ]] && return 0
  done < <(image_generation_worker_roles)
  return 1
}

image_generation_selected_services() {
  printf 'image_generation\n'
  local role
  while IFS= read -r role; do
    image_generation_worker_service_for_role "${role}"
  done < <(image_generation_worker_roles)
}

validate_image_generation_worker_selection() {
  local raw
  raw="$(image_generation_workers_raw)"
  [[ "${raw}" == "none" ]] && return 0

  local old_ifs="${IFS}"
  local item
  local invalid=()
  local valid_count=0
  IFS=','
  for item in ${raw}; do
    [[ -n "${item}" ]] || continue
    case "${item}" in
      text_to_image|plate_logo)
        valid_count=$((valid_count + 1))
        ;;
      *)
        invalid+=("${item}")
        ;;
    esac
  done
  IFS="${old_ifs}"

  if (( ${#invalid[@]} > 0 )); then
    die "Invalid IMAGE_GENERATION_WORKERS=${IMAGE_GENERATION_WORKERS:-}. Valid values are comma-separated text_to_image,plate_logo or none."
  fi
  if (( valid_count == 0 )); then
    die "IMAGE_GENERATION_WORKERS must include at least one worker or be set to none."
  fi
}

image_generation_internal_http_ok() {
  local path="$1"
  compose exec -T image_generation python -c "import sys, urllib.request; sys.exit(0 if 200 <= getattr(urllib.request.urlopen('http://127.0.0.1:8094${path}', timeout=3), 'status', 500) < 400 else 1)" >/dev/null 2>&1
}

image_generation_worker_internal_http_ok() {
  local service_name="$1"
  local port="$2"
  local path="$3"
  compose exec -T "${service_name}" python -c "import sys, urllib.request; sys.exit(0 if 200 <= getattr(urllib.request.urlopen('http://127.0.0.1:${port}${path}', timeout=3), 'status', 500) < 400 else 1)" >/dev/null 2>&1
}

searxng_internal_http_ok() {
  local path="$1"
  compose exec -T searxng python -c "import sys, urllib.request; sys.exit(0 if 200 <= getattr(urllib.request.urlopen('http://127.0.0.1:8080${path}', timeout=3), 'status', 500) < 400 else 1)" >/dev/null 2>&1
}

mcp_gateway_internal_http_ok() {
  local path="$1"
  compose exec -T mcp_gateway python -c "import sys, urllib.request; sys.exit(0 if 200 <= getattr(urllib.request.urlopen('http://127.0.0.1:8080${path}', timeout=3), 'status', 500) < 400 else 1)" >/dev/null 2>&1
}

resolve_llm_local_model_host_path() {
  local model_path="${1:-${LLM_LOCAL_MODEL_PATH:-/models/llm/Qwen--Qwen2.5-0.5B-Instruct}}"
  if [[ "${model_path}" == /models/llm/* ]]; then
    printf '%s\n' "${REPO_ROOT}/models/llm/${model_path#/models/llm/}"
    return 0
  fi
  printf '%s\n' "${model_path}"
}

validate_llm_local_model_path() {
  local env_name="${1:-LLM_LOCAL_MODEL_PATH}"
  local model_path="${2:-${LLM_LOCAL_MODEL_PATH:-/models/llm/Qwen--Qwen2.5-0.5B-Instruct}}"
  if [[ -z "${model_path}" ]]; then
    return 0
  fi
  local host_model_path
  host_model_path="$(resolve_llm_local_model_host_path "${model_path}")"

  if [[ ! -d "${host_model_path}" ]]; then
    die "Configured ${env_name}=${model_path} does not exist on host at ${host_model_path}."
  fi

  if [[ ! -f "${host_model_path}/config.json" && ! -f "${host_model_path}/params.json" ]]; then
    die "Configured ${env_name}=${model_path} is missing config.json or params.json at ${host_model_path}."
  fi
}

validate_llm_inference_local_model_path() {
  validate_llm_local_model_path "LLM_INFERENCE_LOCAL_MODEL_PATH" "${LLM_INFERENCE_LOCAL_MODEL_PATH}"
}

validate_llm_embeddings_local_model_path() {
  validate_llm_local_model_path "LLM_EMBEDDINGS_LOCAL_MODEL_PATH" "${LLM_EMBEDDINGS_LOCAL_MODEL_PATH}"
}

validate_all_llm_local_model_paths() {
  validate_llm_inference_local_model_path
  validate_llm_embeddings_local_model_path
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
  [[ -n "${model_path}" ]] || die "LLAMA_CPP_MODEL_PATH must be set when VANESSA_ENABLED_OPTIONAL_SERVICES includes llama_cpp."

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
  export VANESSA_DEPLOYMENT_MODE
  export VANESSA_RUNTIME_ENV_BASE_FILE
  export VANESSA_RUNTIME_ENV_MODE_FILE
  export VANESSA_RUNTIME_ENV_LEGACY_OVERRIDE_FILE
  export VANESSA_RUNTIME_ENV_ACTIVE_FILE

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
    log_warn "Local llm runtime CPU support is unavailable on this host."
    if llm_runtime_disable_local_requested; then
      log_warn "LLM_RUNTIME_DISABLE_LOCAL_ON_UNSUPPORTED_CPU is enabled; local-only routing must be disabled to run without local runtimes."
    fi
  fi

  local -a cmd=(docker compose)
  if llama_cpp_enabled_requested; then
    cmd+=(--profile llama_cpp)
  fi
  if qdrant_enabled_requested; then
    cmd+=(--profile qdrant)
  fi
  if image_analysis_enabled_requested; then
    cmd+=(--profile image_analysis)
  fi
  if image_generation_enabled_requested; then
    cmd+=(--profile image_generation)
  fi
  if kws_enabled_requested; then
    cmd+=(--profile kws)
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
    if [[ "${service}" == "searxng" ]] && ! web_search_enabled_requested; then
      continue
    fi
    if [[ "${service}" == "image_analysis" ]] && ! image_analysis_enabled_requested; then
      continue
    fi
    if [[ "${service}" == image_analysis_* ]] && ! image_analysis_enabled_requested; then
      continue
    fi
    if [[ "${service}" == image_analysis_* ]]; then
      local role
      role="$(image_analysis_worker_role_for_service "${service}")"
      if ! image_analysis_worker_enabled "${role}"; then
        continue
      fi
    fi
    if [[ "${service}" == "image_generation" ]] && ! image_generation_enabled_requested; then
      continue
    fi
    if [[ "${service}" == image_generation_* ]] && ! image_generation_enabled_requested; then
      continue
    fi
    if [[ "${service}" == image_generation_* ]]; then
      local generation_role
      generation_role="$(image_generation_worker_role_for_service "${service}")"
      if ! image_generation_worker_enabled "${generation_role}"; then
        continue
      fi
    fi
    if [[ "${service}" == "kws" ]] && ! kws_enabled_requested; then
      continue
    fi
    services_to_start+=("${service}")
  done

  local cpu_supported="${LLM_RUNTIME_CPU_SUPPORTED:-true}"
  if [[ "${cpu_supported}" == "false" ]] && llm_runtime_disable_local_requested && ! llm_routing_requires_local_runtime; then
    for service in "${services_to_start[@]}"; do
      if [[ "${service}" != "llm_runtime_inference" && "${service}" != "llm_runtime_embeddings" ]]; then
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

host_probe_host() {
  local bind_host="$1"
  case "${bind_host}" in
    ""|"0.0.0.0"|"::") printf '127.0.0.1\n' ;;
    *) printf '%s\n' "${bind_host}" ;;
  esac
}

frontend_probe_url() { printf 'http://%s:%s/\n' "$(host_probe_host "${FRONTEND_BIND_HOST:-127.0.0.1}")" "${FRONTEND_PUBLISHED_PORT:-3000}"; }
backend_probe_url() { printf 'http://%s:%s/health\n' "$(host_probe_host "${BACKEND_BIND_HOST:-127.0.0.1}")" "${BACKEND_PUBLISHED_PORT:-5000}"; }
agent_engine_probe_url() { printf 'http://%s:%s/health\n' "$(host_probe_host "${AGENT_ENGINE_BIND_HOST:-127.0.0.1}")" "${AGENT_ENGINE_PUBLISHED_PORT:-7000}"; }
sandbox_probe_url() { printf 'http://%s:%s/health\n' "$(host_probe_host "${SANDBOX_BIND_HOST:-127.0.0.1}")" "${SANDBOX_PUBLISHED_PORT:-6000}"; }
kws_probe_url() { printf 'http://%s:%s/health\n' "$(host_probe_host "${KWS_BIND_HOST:-127.0.0.1}")" "${KWS_PUBLISHED_PORT:-10400}"; }
llm_probe_url() { printf 'http://%s:%s/health\n' "$(host_probe_host "${LLM_BIND_HOST:-127.0.0.1}")" "${LLM_PUBLISHED_PORT:-8000}"; }
llm_models_probe_url() { printf 'http://%s:%s/v1/models\n' "$(host_probe_host "${LLM_BIND_HOST:-127.0.0.1}")" "${LLM_PUBLISHED_PORT:-8000}"; }
mcp_gateway_probe_url() { printf 'http://%s:%s/health\n' "$(host_probe_host "${MCP_GATEWAY_BIND_HOST:-127.0.0.1}")" "${MCP_GATEWAY_PUBLISHED_PORT:-6100}"; }
weaviate_probe_url() { printf 'http://%s:%s/v1/.well-known/live\n' "$(host_probe_host "${WEAVIATE_BIND_HOST:-127.0.0.1}")" "${WEAVIATE_PUBLISHED_PORT:-8080}"; }
runtime_profile_probe_url() { printf 'http://%s:%s/v1/runtime/profile\n' "$(host_probe_host "${BACKEND_BIND_HOST:-127.0.0.1}")" "${BACKEND_PUBLISHED_PORT:-5000}"; }
