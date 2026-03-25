#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib/common.sh"

restart_services=true

usage() {
  cat <<USAGE
Usage: $(basename "$0") [--no-restart]

Reads the backend-owned local model slot assignment for vLLM providers,
syncs infra/.env.local startup defaults for the split local runtimes,
and optionally restarts llm + llm_runtime_inference + llm_runtime_embeddings.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-restart)
      restart_services=false
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

query_slot() {
  local provider_key="$1"
  compose exec -T postgres psql -U vanessa -d vanessa -At -F $'\t' -c "
    SELECT
      COALESCE(i.config_json->>'loaded_managed_model_id', ''),
      COALESCE(i.config_json->>'loaded_managed_model_name', ''),
      COALESCE(i.config_json->>'loaded_runtime_model_id', ''),
      COALESCE(i.config_json->>'loaded_local_path', ''),
      COALESCE(i.config_json->>'load_state', '')
    FROM platform_provider_instances i
    WHERE i.provider_key = '${provider_key}'
    ORDER BY i.slug ASC
    LIMIT 1
  "
}

upsert_env_var() {
  local file_path="$1"
  local key="$2"
  local value="$3"
  local temp_file
  temp_file="$(mktemp)"
  if [[ -f "${file_path}" ]]; then
    awk -v key="${key}" -v value="${value}" '
      BEGIN { updated = 0 }
      index($0, key "=") == 1 {
        print key "=" value
        updated = 1
        next
      }
      { print }
      END {
        if (updated == 0) {
          print key "=" value
        }
      }
    ' "${file_path}" > "${temp_file}"
  else
    printf '%s=%s\n' "${key}" "${value}" > "${temp_file}"
  fi
  mv "${temp_file}" "${file_path}"
}

IFS=$'\t' read -r llm_managed_id llm_managed_name llm_runtime_id llm_local_path llm_load_state <<< "$(query_slot "vllm_local")"
IFS=$'\t' read -r embeddings_managed_id embeddings_managed_name embeddings_runtime_id embeddings_local_path embeddings_load_state <<< "$(query_slot "vllm_embeddings_local")"

effective_inference_local_path="${llm_local_path:-}"
effective_embeddings_local_path="${embeddings_local_path:-}"
effective_llm_runtime_id="${llm_runtime_id:-${effective_inference_local_path}}"
effective_embeddings_runtime_id="${embeddings_runtime_id:-${effective_embeddings_local_path}}"

if [[ -n "${effective_inference_local_path}" && "${effective_inference_local_path}" != /models/llm/* ]]; then
  die "Loaded llm_inference local model path must stay under /models/llm for local staging: ${effective_inference_local_path}"
fi

if [[ -n "${effective_embeddings_local_path}" && "${effective_embeddings_local_path}" != /models/llm/* ]]; then
  die "Loaded embeddings local model path must stay under /models/llm for local staging: ${effective_embeddings_local_path}"
fi

infra_env_file="${REPO_ROOT}/infra/.env.local"
touch "${infra_env_file}"

upsert_env_var "${infra_env_file}" "LLM_LOCAL_MODEL_PATH" "${effective_inference_local_path}"
upsert_env_var "${infra_env_file}" "LLM_INFERENCE_LOCAL_MODEL_PATH" "${effective_inference_local_path}"
upsert_env_var "${infra_env_file}" "LLM_EMBEDDINGS_LOCAL_MODEL_PATH" "${effective_embeddings_local_path}"
upsert_env_var "${infra_env_file}" "LLM_LOCAL_UPSTREAM_MODEL" "${effective_llm_runtime_id}"
upsert_env_var "${infra_env_file}" "LLM_LOCAL_EMBEDDINGS_UPSTREAM_MODEL" "${effective_embeddings_runtime_id}"

log_info "Synced infra/.env.local with backend-owned local slot intent"
log_info "LLM_INFERENCE_LOCAL_MODEL_PATH=${effective_inference_local_path:-<empty>}"
log_info "LLM_EMBEDDINGS_LOCAL_MODEL_PATH=${effective_embeddings_local_path:-<empty>}"
log_info "LLM_LOCAL_UPSTREAM_MODEL=${effective_llm_runtime_id}"
log_info "LLM_LOCAL_EMBEDDINGS_UPSTREAM_MODEL=${effective_embeddings_runtime_id}"

if [[ -z "${effective_inference_local_path}" && -z "${effective_embeddings_local_path}" ]]; then
  log_warn "Both local runtime slots are empty. Restarting will bring the split runtimes up without a startup model."
fi

if [[ "${restart_services}" == true ]]; then
  log_info "Restarting llm_runtime_inference, llm_runtime_embeddings, and llm to apply the reconciled startup defaults"
  compose up -d llm_runtime_inference llm_runtime_embeddings llm || die "Failed to restart split local runtimes and llm"
fi
