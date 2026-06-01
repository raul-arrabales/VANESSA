#!/usr/bin/env bash
set -euo pipefail

export VANESSA_DEPLOYMENT_MODE="${VANESSA_DEPLOYMENT_MODE:-local_staging}"

LOCAL_COMMON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${LOCAL_COMMON_DIR}/../../deploy/lib/common.sh"
