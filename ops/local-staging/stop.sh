#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib/common.sh"

remove_volumes=false

usage() {
  cat <<USAGE
Usage: $(basename "$0") [--volumes]

Stops the VANESSA stack. Volumes are preserved by default.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --volumes)
      remove_volumes=true
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

if [[ "${remove_volumes}" == true ]]; then
  log_warn "Stopping stack and removing volumes"
  compose down -v || die "Failed to stop stack and remove volumes"
else
  log_info "Stopping stack (preserving volumes)"
  compose down || die "Failed to stop stack"
fi
