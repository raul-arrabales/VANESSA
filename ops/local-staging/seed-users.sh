#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib/common.sh"

seed_timeout_seconds=60

: "${SAMPLE_SUPERADMIN_USERNAME:=sample-superadmin}"
: "${SAMPLE_SUPERADMIN_EMAIL:=sample-superadmin@local.test}"
: "${SAMPLE_SUPERADMIN_PASSWORD:=sample-superadmin-123}"
: "${SAMPLE_ADMIN_USERNAME:=sample-admin}"
: "${SAMPLE_ADMIN_EMAIL:=sample-admin@local.test}"
: "${SAMPLE_ADMIN_PASSWORD:=sample-admin-123}"
: "${SAMPLE_USER_USERNAME:=sample-user}"
: "${SAMPLE_USER_EMAIL:=sample-user@local.test}"
: "${SAMPLE_USER_PASSWORD:=sample-user-123}"

usage() {
  cat <<USAGE
Usage: $(basename "$0") [--timeout <seconds>]

Seeds one sample superadmin, admin, and user for local manual testing.
USAGE
}

wait_for_backend() {
  local timeout_seconds="$1"
  local backend_port="${BACKEND_PORT:-5000}"
  local backend_url="http://localhost:${backend_port}/health"
  local deadline=$((SECONDS + timeout_seconds))

  while (( SECONDS < deadline )); do
    if curl --silent --show-error --max-time 2 --fail "${backend_url}" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done

  return 1
}

validate_required_vars() {
  local value="$1"
  local name="$2"
  [[ -n "${value}" ]] || die "Missing required variable: ${name}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --timeout)
      [[ $# -ge 2 ]] || die "--timeout requires a value"
      seed_timeout_seconds="$2"
      shift 2
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

[[ "${seed_timeout_seconds}" =~ ^[0-9]+$ ]] || die "--timeout must be an integer"

validate_required_vars "${SAMPLE_SUPERADMIN_USERNAME}" "SAMPLE_SUPERADMIN_USERNAME"
validate_required_vars "${SAMPLE_SUPERADMIN_EMAIL}" "SAMPLE_SUPERADMIN_EMAIL"
validate_required_vars "${SAMPLE_SUPERADMIN_PASSWORD}" "SAMPLE_SUPERADMIN_PASSWORD"
validate_required_vars "${SAMPLE_ADMIN_USERNAME}" "SAMPLE_ADMIN_USERNAME"
validate_required_vars "${SAMPLE_ADMIN_EMAIL}" "SAMPLE_ADMIN_EMAIL"
validate_required_vars "${SAMPLE_ADMIN_PASSWORD}" "SAMPLE_ADMIN_PASSWORD"
validate_required_vars "${SAMPLE_USER_USERNAME}" "SAMPLE_USER_USERNAME"
validate_required_vars "${SAMPLE_USER_EMAIL}" "SAMPLE_USER_EMAIL"
validate_required_vars "${SAMPLE_USER_PASSWORD}" "SAMPLE_USER_PASSWORD"

require_prerequisites

log_info "Validating compose configuration"
compose config >/dev/null || die "Compose configuration is invalid"

log_info "Waiting for backend before seeding sample users"
if ! wait_for_backend "${seed_timeout_seconds}"; then
  die "Backend did not become healthy in ${seed_timeout_seconds}s; cannot seed sample users"
fi

log_info "Seeding sample users"
if ! compose exec -T \
  -e "SAMPLE_SUPERADMIN_USERNAME=${SAMPLE_SUPERADMIN_USERNAME}" \
  -e "SAMPLE_SUPERADMIN_EMAIL=${SAMPLE_SUPERADMIN_EMAIL}" \
  -e "SAMPLE_SUPERADMIN_PASSWORD=${SAMPLE_SUPERADMIN_PASSWORD}" \
  -e "SAMPLE_ADMIN_USERNAME=${SAMPLE_ADMIN_USERNAME}" \
  -e "SAMPLE_ADMIN_EMAIL=${SAMPLE_ADMIN_EMAIL}" \
  -e "SAMPLE_ADMIN_PASSWORD=${SAMPLE_ADMIN_PASSWORD}" \
  -e "SAMPLE_USER_USERNAME=${SAMPLE_USER_USERNAME}" \
  -e "SAMPLE_USER_EMAIL=${SAMPLE_USER_EMAIL}" \
  -e "SAMPLE_USER_PASSWORD=${SAMPLE_USER_PASSWORD}" \
  backend sh -lc 'cd /app/backend && python -' <<'PY'
import os

from app.config import get_auth_config
from app.db import get_connection
from app.repositories.users import create_user, find_user_by_identifier
from app.security import hash_password


def normalize(value: str) -> str:
    return value.strip().lower()


def ensure_user(database_url: str, *, username: str, email: str, password: str, role: str) -> None:
    normalized_username = normalize(username)
    normalized_email = normalize(email)

    existing = find_user_by_identifier(database_url, normalized_username)
    if existing is None:
        existing = find_user_by_identifier(database_url, normalized_email)

    if existing is None:
        create_user(
            database_url,
            email=normalized_email,
            username=normalized_username,
            password_hash=hash_password(password),
            role=role,
            is_active=True,
        )
        print(f"{normalized_username}: created")
        return

    fields = []
    params = []
    if str(existing.get("role", "")) != role:
        fields.append("role = %s")
        params.append(role)
    if not bool(existing.get("is_active", False)):
        fields.append("is_active = TRUE")

    if not fields:
        print(f"{normalized_username}: unchanged")
        return

    update_sql = f"UPDATE users SET {', '.join(fields)}, updated_at = NOW() WHERE id = %s"
    params.append(int(existing["id"]))
    with get_connection(database_url) as connection:
        connection.execute(update_sql, tuple(params))
    print(f"{normalized_username}: updated")


config = get_auth_config()
db_url = config.database_url

sample_users = [
    {
        "username": os.environ["SAMPLE_SUPERADMIN_USERNAME"],
        "email": os.environ["SAMPLE_SUPERADMIN_EMAIL"],
        "password": os.environ["SAMPLE_SUPERADMIN_PASSWORD"],
        "role": "superadmin",
    },
    {
        "username": os.environ["SAMPLE_ADMIN_USERNAME"],
        "email": os.environ["SAMPLE_ADMIN_EMAIL"],
        "password": os.environ["SAMPLE_ADMIN_PASSWORD"],
        "role": "admin",
    },
    {
        "username": os.environ["SAMPLE_USER_USERNAME"],
        "email": os.environ["SAMPLE_USER_EMAIL"],
        "password": os.environ["SAMPLE_USER_PASSWORD"],
        "role": "user",
    },
]

for sample in sample_users:
    ensure_user(
        db_url,
        username=sample["username"],
        email=sample["email"],
        password=sample["password"],
        role=sample["role"],
    )
PY
then
  log_error "Failed to run seed script inside backend; expected app package under /app/backend"
  die "Failed to seed sample users"
fi

log_info "Sample user seeding complete"
