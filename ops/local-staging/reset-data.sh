#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib/common.sh"

confirmed=false

usage() {
  cat <<USAGE
Usage: $(basename "$0") --yes

Stops stack and removes volumes to reset PostgreSQL and Weaviate data.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --yes)
      confirmed=true
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

if [[ "${confirmed}" != true ]]; then
  log_error "Refusing to reset data without --yes"
  usage
  exit 1
fi

log_warn "Resetting local data volumes (PostgreSQL + Weaviate)"
compose down -v || die "Failed to reset data volumes"
log_info "Data volumes removed"
