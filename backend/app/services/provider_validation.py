from __future__ import annotations

import json
from urllib import error, request


class ProviderValidationError(RuntimeError):
    pass


def validate_openai_compatible_model(*, api_base_url: str, api_key: str, model_id: str, timeout_seconds: float = 8.0) -> None:
    base_url = api_base_url.strip().rstrip("/")
    if not base_url:
        raise ProviderValidationError("api_base_url_required")

    req = request.Request(
        f"{base_url}/models",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        },
        method="GET",
    )

    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:  # noqa: S310
            body = response.read().decode("utf-8")
    except error.HTTPError as exc:  # pragma: no cover - exercised via tests with monkeypatching
        raise ProviderValidationError(f"provider_http_{exc.code}") from exc
    except error.URLError as exc:  # pragma: no cover
        raise ProviderValidationError("provider_unreachable") from exc

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ProviderValidationError("invalid_provider_response") from exc

    items = payload.get("data")
    if not isinstance(items, list):
        raise ProviderValidationError("invalid_provider_response")

    available_model_ids = {str(item.get("id", "")).strip() for item in items if isinstance(item, dict)}
    if model_id.strip() not in available_model_ids:
        raise ProviderValidationError("model_not_available")
