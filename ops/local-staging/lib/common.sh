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

readonly SERVICES=(frontend backend llm llm_runtime agent_engine sandbox kws weaviate postgres)

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

compose_file_args() {
  local resolved_accelerator="${RESOLVED_LLM_RUNTIME_ACCELERATOR:-$(resolve_llm_runtime_accelerator)}"
  local compose_files="${COMPOSE_FILE}"

  if [[ "${resolved_accelerator}" == "gpu" ]]; then
    compose_files="${compose_files}:infra/docker-compose.gpu.override.yml"
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
  export RESOLVED_LLM_RUNTIME_ACCELERATOR
  export LLM_RUNTIME_ACCELERATOR="${RESOLVED_LLM_RUNTIME_ACCELERATOR}"

  local -a cmd=(docker compose)
  local compose_path
  while IFS= read -r -d '' compose_path; do
    cmd+=(-f "${compose_path}")
  done < <(compose_file_args)
  if [[ -n "${COMPOSE_ENV_FILE}" ]]; then
    cmd+=(--env-file "${COMPOSE_ENV_FILE}")
  fi

  "${cmd[@]}" "$@"
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
