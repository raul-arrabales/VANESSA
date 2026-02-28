from __future__ import annotations

from dataclasses import dataclass

from .runtime_profile_service import internet_allowed, resolve_runtime_profile


@dataclass(frozen=True)
class ConnectivityPolicyError(RuntimeError):
    code: str
    message: str
    status_code: int = 403

    def __str__(self) -> str:
        return self.message


def get_effective_runtime_profile(database_url: str) -> str:
    return resolve_runtime_profile(database_url)


def assert_internet_allowed(database_url: str, operation: str) -> None:
    runtime_profile = get_effective_runtime_profile(database_url)
    if internet_allowed(runtime_profile):
        return

    normalized_operation = operation.strip() or "Requested operation"
    raise ConnectivityPolicyError(
        code="runtime_profile_blocks_internet",
        message=(
            f"{normalized_operation} disabled for runtime profile "
            f"'{runtime_profile}'"
        ),
    )
