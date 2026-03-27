from __future__ import annotations

import pytest

from app.application import modelops_testing_service
from app.services.modelops_common import ModelOpsError


def test_parse_model_test_request_requires_inputs_object() -> None:
    with pytest.raises(ModelOpsError) as exc_info:
        modelops_testing_service.parse_model_test_request({"inputs": "hello"})

    assert exc_info.value.code == "invalid_payload"

    inputs, provider_instance_id = modelops_testing_service.parse_model_test_request(
        {"inputs": {"prompt": "hello"}, "provider_instance_id": "provider-1"}
    )
    assert inputs == {"prompt": "hello"}
    assert provider_instance_id == "provider-1"


def test_parse_validation_request_accepts_none_and_dict() -> None:
    assert modelops_testing_service.parse_validation_request(None) is None
    assert modelops_testing_service.parse_validation_request({"test_run_id": "run-1"}) == "run-1"
