#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib/common.sh"

usage() {
  cat <<USAGE
Usage: $(basename "$0") [docker compose args...]

Runs docker compose with the same CPU/GPU override resolution used by local-staging scripts.
Use this instead of raw 'docker compose -f infra/docker-compose.yml' for local staging work.
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

require_prerequisites
compose "$@"
