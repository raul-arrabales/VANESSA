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

readonly SERVICES=(frontend backend llm agent_engine sandbox weaviate postgres)

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
  if [[ "${COMPOSE_FILE}" = /* ]]; then
    printf '%s\n' "${COMPOSE_FILE}"
  else
    printf '%s\n' "${REPO_ROOT}/${COMPOSE_FILE}"
  fi
}

compose() {
  local compose_path
  compose_path="$(resolve_compose_file)"

  local -a cmd=(docker compose -f "${compose_path}")
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
