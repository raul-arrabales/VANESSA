#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib/common.sh"

build_flag="--build"
timeout_seconds="${START_TIMEOUT_SECONDS}"
seed_sample_users=false

usage() {
  cat <<USAGE
Usage: $(basename "$0") [--no-build] [--timeout <seconds>] [--env-file <path>] [--seed-sample-users]

Starts the full VANESSA stack using Docker Compose and waits for readiness.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-build)
      build_flag=""
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
    --seed-sample-users)
      seed_sample_users=true
      shift
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
if [[ -n "${COMPOSE_ENV_FILE}" ]]; then
  [[ -f "${COMPOSE_ENV_FILE}" ]] || die "--env-file does not exist: ${COMPOSE_ENV_FILE}"
fi

require_prerequisites

log_info "Validating compose configuration"
if ! compose config >/dev/null; then
  die "Compose configuration is invalid"
fi

log_info "Starting VANESSA stack"
if [[ -n "${build_flag}" ]]; then
  if ! compose up -d --build; then
    log_warn "If the error includes 'parent snapshot ... does not exist', run moderate cleanup from ops/local-staging/README.md."
    die "Failed to start stack"
  fi
else
  if ! compose up -d; then
    log_warn "If the error includes 'parent snapshot ... does not exist', run moderate cleanup from ops/local-staging/README.md."
    die "Failed to start stack"
  fi
fi

log_info "Waiting for readiness (timeout: ${timeout_seconds}s)"
set +e
"${SCRIPT_DIR}/health.sh" --wait --timeout "${timeout_seconds}"
status=$?
set -e
if [[ ${status} -eq 0 ]]; then
  if [[ "${seed_sample_users}" == true ]]; then
    log_info "Seeding sample users for local manual testing"
    COMPOSE_FILE="${COMPOSE_FILE}" COMPOSE_ENV_FILE="${COMPOSE_ENV_FILE}" "${SCRIPT_DIR}/seed-users.sh" || die "Failed to seed sample users"
  fi
  log_info "Stack is ready"
  exit 0
fi

if [[ ${status} -eq 3 ]]; then
  log_error "Timeout or failing health checks while waiting for stack readiness"
  exit 2
fi

exit 1
