from __future__ import annotations

import pytest

from app.application import modelops_access_service
from app.services.modelops_common import ModelOpsError


def test_build_scope_assignment_request_requires_model_ids_array() -> None:
    request = modelops_access_service.build_scope_assignment_request({"scope": "user", "model_ids": ["a", "b"]})
    assert request == {"scope": "user", "model_ids": ["a", "b"]}

    with pytest.raises(ModelOpsError) as exc_info:
        modelops_access_service.build_scope_assignment_request({"scope": "user", "model_ids": "a"})

    assert exc_info.value.code == "invalid_model_ids"
