#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib/common.sh"

json_mode=false

usage() {
  cat <<USAGE
Usage: $(basename "$0") [--json]

Shows Docker Compose service status for the VANESSA stack.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --json)
      json_mode=true
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

require_prerequisites

if [[ "${json_mode}" == true ]]; then
  if ! compose ps --format json; then
    die "Failed to fetch compose status in JSON format"
  fi
  exit 0
fi

if ! compose ps -a; then
  die "Failed to fetch compose status"
fi

total_services="$(compose config --services | wc -l | tr -d ' ')"
running_services="$(compose ps --status running --services | wc -l | tr -d ' ')"
exited_services="$(compose ps --status exited --services | wc -l | tr -d ' ')"

printf '\nSummary: running=%s exited=%s total=%s\n' "${running_services}" "${exited_services}" "${total_services}"
