from __future__ import annotations

import base64

from image_analysis.app import main as service


ONE_PIXEL_PNG = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


def _payload(*, tasks: list[str] | None = None) -> dict[str, object]:
    return {
        "image": {"data_base64": ONE_PIXEL_PNG, "mime_type": "image/png"},
        "tasks": tasks or ["license_plate_recognition"],
        "runtime": {
            "task_defaults": {
                "plate_detector": "plate-detector",
                "plate_ocr": "plate-ocr",
                "object_detector": "object-detector",
                "captioner": "captioner",
            }
        },
    }


def test_analyze_rejects_invalid_base64() -> None:
    payload = _payload()
    payload["image"] = {"data_base64": "not-base64", "mime_type": "image/png"}

    result, status = service._analyze(payload)

    assert status == 400
    assert result["error"] == "invalid_image"


def test_analyze_rejects_unknown_task() -> None:
    result, status = service._analyze(_payload(tasks=["unknown"]))

    assert status == 400
    assert result["error"] == "invalid_tasks"


def test_fake_mode_returns_plate_objects_and_caption(monkeypatch) -> None:
    monkeypatch.setenv("IMAGE_ANALYSIS_FAKE_MODE", "1")
    monkeypatch.setattr(service, "Image", None)

    result, status = service._analyze(_payload(tasks=["license_plate_recognition", "object_detection", "captioning"]))

    assert status == 200
    assert result["license_plates"][0]["text"] == "LOCAL123"
    assert result["license_plates"][0]["plate_detector_model_id"] == "plate-detector"
    assert result["objects"][0]["label"] == "vehicle"
    assert result["caption"]["text"]
    assert "warnings" not in result


def test_empty_detection_runtime_still_returns_requested_sections(monkeypatch) -> None:
    monkeypatch.delenv("IMAGE_ANALYSIS_FAKE_MODE", raising=False)
    monkeypatch.setattr(service, "Image", None)

    result, status = service._analyze_local(_payload(tasks=["license_plate_recognition", "object_detection"]))

    assert status == 200
    assert result["license_plates"] == []
    assert result["objects"] == []
    assert result["warnings"][0]["code"] == "image_runtime_unavailable"


def test_gateway_routes_requested_tasks_and_aggregates_worker_results(monkeypatch) -> None:
    calls: list[tuple[str, list[str]]] = []

    def worker(role: str, payload: dict[str, object], tasks: list[str]):
        calls.append((role, tasks))
        if role == service.ROLE_ANPR:
            return {"image": {"width": 1, "height": 1}, "license_plates": [{"text": "ABC123"}]}, 200, None
        if role == service.ROLE_OBJECTS:
            return {"image": {"width": 1, "height": 1}, "objects": [{"label": "car"}]}, 200, None
        return {"image": {"width": 1, "height": 1}, "caption": {"text": "A car."}}, 200, None

    monkeypatch.delenv("IMAGE_ANALYSIS_FAKE_MODE", raising=False)
    monkeypatch.setattr(service, "_decode_image", lambda _payload: (b"", 1, 1, object(), None))
    monkeypatch.setattr(service, "_gateway_worker_analyze", worker)

    result, status = service._analyze(_payload(tasks=["license_plate_recognition", "object_detection", "captioning"]))

    assert status == 200
    assert calls == [
        (service.ROLE_ANPR, ["license_plate_recognition"]),
        (service.ROLE_OBJECTS, ["object_detection"]),
        (service.ROLE_CAPTIONING, ["captioning"]),
    ]
    assert result["license_plates"] == [{"text": "ABC123"}]
    assert result["objects"] == [{"label": "car"}]
    assert result["caption"] == {"text": "A car."}
    assert "warnings" not in result


def test_gateway_worker_failure_preserves_other_task_results(monkeypatch) -> None:
    def worker(role: str, payload: dict[str, object], tasks: list[str]):
        if role == service.ROLE_OBJECTS:
            return None, 0, "connection refused"
        return {"image": {"width": 1, "height": 1}, "caption": {"text": "A test image."}}, 200, None

    monkeypatch.delenv("IMAGE_ANALYSIS_FAKE_MODE", raising=False)
    monkeypatch.setattr(service, "_decode_image", lambda _payload: (b"", 1, 1, object(), None))
    monkeypatch.setattr(service, "_gateway_worker_analyze", worker)

    result, status = service._analyze(_payload(tasks=["object_detection", "captioning"]))

    assert status == 200
    assert result["objects"] == []
    assert result["caption"] == {"text": "A test image."}
    assert result["warnings"][0]["code"] == "object_worker_unavailable"
    assert ONE_PIXEL_PNG not in str(result["warnings"])


def test_gateway_resources_aggregate_workers(monkeypatch) -> None:
    def resources(role: str):
        return service._resources_for_role(role), None

    monkeypatch.delenv("IMAGE_ANALYSIS_FAKE_MODE", raising=False)
    monkeypatch.setattr(service, "_resources_from_worker", resources)

    payload = service._resources_payload_for_role(service.ROLE_GATEWAY)

    task_keys = {resource["metadata"]["task_key"] for resource in payload["resources"]}
    assert task_keys == {"image_plate_detection", "image_plate_ocr", "object_detection", "image_captioning"}
    assert "warnings" not in payload


def test_worker_rejects_unsupported_task() -> None:
    result, status = service._analyze_for_role(_payload(tasks=["captioning"]), service.ROLE_OBJECTS)

    assert status == 400
    assert result["error"] == "invalid_tasks"


def test_florence2_transformers_patch_adds_missing_forced_bos_token_id() -> None:
    class DummyPretrainedConfig:
        pass

    service._patch_florence2_transformers_config(DummyPretrainedConfig)

    assert DummyPretrainedConfig.forced_bos_token_id is None


def test_florence2_model_patch_adds_missing_attention_flags() -> None:
    class NestedModel:
        pass

    class DummyLanguageModel:
        model = NestedModel()

    class DummyModel:
        language_model = DummyLanguageModel()

    model = DummyModel()
    service._patch_florence2_model_compat(model)

    assert model._supports_sdpa is False
    assert model._supports_flash_attn_2 is False
    assert DummyModel.language_model._supports_sdpa is False
    assert DummyModel.language_model._supports_flash_attn_2 is False
    assert DummyModel.language_model.model._supports_sdpa is False
    assert DummyModel.language_model.model._supports_flash_attn_2 is False


def test_florence2_model_class_patch_adds_missing_attention_flags() -> None:
    class DummyPretrainedModel:
        pass

    service._patch_florence2_transformers_model(DummyPretrainedModel)

    assert DummyPretrainedModel._supports_sdpa is False
    assert DummyPretrainedModel._supports_flash_attn_2 is False


def test_florence2_tokenizer_patch_adds_missing_special_tokens_property() -> None:
    class DummyTokenizerBase:
        pass

    class DummyTokenizer(DummyTokenizerBase):
        special_tokens_map = {"additional_special_tokens": ["<extra>"]}

    service._patch_florence2_transformers_tokenizer(DummyTokenizerBase)

    assert DummyTokenizer().additional_special_tokens == ["<extra>"]


def test_caption_image_is_square_padded_and_resized_when_needed(monkeypatch) -> None:
    if service.Image is None:
        return

    monkeypatch.setenv("IMAGE_ANALYSIS_FLORENCE_IMAGE_SIZE", "8")
    image = service.Image.new("RGB", (4, 2), (255, 255, 255))

    result = service._square_caption_image(image)

    assert result.size == (8, 8)


def test_caption_generation_defaults_are_cpu_friendly(monkeypatch) -> None:
    monkeypatch.delenv("IMAGE_ANALYSIS_FLORENCE_IMAGE_SIZE", raising=False)
    monkeypatch.delenv("IMAGE_ANALYSIS_FLORENCE_MAX_NEW_TOKENS", raising=False)
    monkeypatch.delenv("IMAGE_ANALYSIS_FLORENCE_NUM_BEAMS", raising=False)

    assert service._caption_image_size() == 512
    assert service._caption_max_tokens({"options": {}}) == 48
    assert service._caption_num_beams() == 1


def test_heavy_model_prepare_releases_alternate_model_by_default(monkeypatch) -> None:
    monkeypatch.delenv("IMAGE_ANALYSIS_KEEP_HEAVY_MODELS_LOADED", raising=False)
    monkeypatch.setattr(service, "_release_torch_memory", lambda: None)
    monkeypatch.setattr(service, "_OBJECT_DETECTOR", object())
    monkeypatch.setattr(service, "_CAPTIONER", (object(), object()))

    service._prepare_heavy_model("captioning")

    assert service._OBJECT_DETECTOR is None
    assert service._CAPTIONER is not None


def test_heavy_model_prepare_can_keep_models_loaded(monkeypatch) -> None:
    monkeypatch.setenv("IMAGE_ANALYSIS_KEEP_HEAVY_MODELS_LOADED", "1")
    monkeypatch.setattr(service, "_release_torch_memory", lambda: None)
    object_detector = object()
    captioner = (object(), object())
    monkeypatch.setattr(service, "_OBJECT_DETECTOR", object_detector)
    monkeypatch.setattr(service, "_CAPTIONER", captioner)

    service._prepare_heavy_model("captioning")

    assert service._OBJECT_DETECTOR is object_detector
    assert service._CAPTIONER is captioner


def test_caption_token_embeddings_are_resized_for_processor_tokens() -> None:
    class DummyTokenizer:
        def __len__(self) -> int:
            return 7

    class DummyProcessor:
        tokenizer = DummyTokenizer()

    class DummyEmbeddings:
        num_embeddings = 5

    class DummyModel:
        resized_to: int | None = None

        def get_input_embeddings(self):
            return DummyEmbeddings()

        def resize_token_embeddings(self, token_count: int) -> None:
            self.resized_to = token_count

    model = DummyModel()

    service._resize_caption_token_embeddings(model, DummyProcessor())

    assert model.resized_to == 7


def test_malformed_image_is_rejected_when_decoder_is_available(monkeypatch) -> None:
    class BrokenImage:
        @staticmethod
        def open(_source):
            raise ValueError("broken image")

    payload = _payload()
    payload["image"] = {
        "data_base64": base64.b64encode(b"not an image").decode("ascii"),
        "mime_type": "image/png",
    }
    monkeypatch.setattr(service, "Image", BrokenImage)

    result, status = service._analyze(payload)

    assert status == 400
    assert result["error"] == "invalid_image"
