#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib/common.sh"

service_name=""
tail_lines="${LOG_TAIL_LINES}"
follow_mode=false

usage() {
  cat <<USAGE
Usage: $(basename "$0") [--service <name>] [--tail <n>] [--follow]

Shows logs for all services or a single service.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --service)
      [[ $# -ge 2 ]] || die "--service requires a value"
      service_name="$2"
      shift 2
      ;;
    --tail)
      [[ $# -ge 2 ]] || die "--tail requires a value"
      tail_lines="$2"
      shift 2
      ;;
    --follow)
      follow_mode=true
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

[[ "${tail_lines}" =~ ^[0-9]+$ ]] || die "--tail must be an integer"
require_prerequisites

if [[ -n "${service_name}" ]] && ! is_valid_service "${service_name}"; then
  die "Invalid service: ${service_name}. Valid services: ${SERVICES[*]}"
fi

if [[ "${follow_mode}" == true ]]; then
  if [[ -n "${service_name}" ]]; then
    compose logs --no-color --tail "${tail_lines}" --follow "${service_name}" || die "Failed to stream logs"
  else
    compose logs --no-color --tail "${tail_lines}" --follow || die "Failed to stream logs"
  fi
else
  if [[ -n "${service_name}" ]]; then
    compose logs --no-color --tail "${tail_lines}" "${service_name}" || die "Failed to fetch logs"
  else
    compose logs --no-color --tail "${tail_lines}" || die "Failed to fetch logs"
  fi
fi
