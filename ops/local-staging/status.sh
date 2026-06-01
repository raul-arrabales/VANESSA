#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
export VANESSA_DEPLOYMENT_MODE=local_staging
exec "${SCRIPT_DIR}/../deploy/bin/status.sh" "$@"
