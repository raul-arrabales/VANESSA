# Image Analysis Service

`image_analysis` is an optional local provider for VANESSA image understanding. It is selected through the platform control plane as capability `image_analysis` with provider family `image_analysis_local` and adapter `image_analysis_http`.

## Runtime

- Compose service: `image_analysis`
- Optional profile: `image_analysis`
- Default port: `8090`
- Model mount: `models/image_analysis:/models/image_analysis`
- Backend seed env: `IMAGE_ANALYSIS_URL=http://image_analysis:8090`

The service exposes:

- `GET /health`
- `GET /v1/resources`
- `POST /v1/analyze`

`POST /v1/analyze` accepts JSON only. Callers provide `image.data_base64`, `image.mime_type`, and one or more tasks: `license_plate_recognition`, `object_detection`, or `captioning`.

Image bytes are transient request data. The service does not log image payloads by default, and backend/agent call records redact base64 image data.

## Models

V1 defaults are local open-source models:

- Plate detection: `open-image-models` through `fast-alpr`
- Plate OCR: `fast-plate-ocr` through `fast-alpr`
- Object detection: RF-DETR
- Captioning: Florence-2

CI and first-boot smoke tests can use `IMAGE_ANALYSIS_FAKE_MODE=1` for deterministic non-model output. The image builds with only lightweight dependencies by default. Set `IMAGE_ANALYSIS_INSTALL_RUNTIME_DEPS=1` and rebuild when you want to install the real ANPR, RF-DETR, Florence, and Torch runtime dependencies.

The RF-DETR dependency currently requires Transformers 5.x, so the runtime requirements intentionally use `transformers>=5.1.0,<6.0.0` rather than the older Florence-2-era 4.x pin.
Florence-2 also requires `einops` and `timm` at runtime through its remote modeling code.
The backend provider timeout defaults to `IMAGE_ANALYSIS_REQUEST_TIMEOUT_SECONDS=300` because first-run real model loading can exceed normal LLM request timeouts.

## Control Plane Binding

`image_analysis` is ModelOps-governed and resource-bearing. Eligible ModelOps task keys are:

- `image_plate_detection`
- `image_plate_ocr`
- `object_detection`
- `image_captioning`

Bindings use:

```json
{
  "resource_policy": {
    "selection_mode": "task_defaults",
    "task_defaults": {
      "plate_detector": "plate-detector-model-id",
      "plate_ocr": "plate-ocr-model-id",
      "object_detector": "object-detector-model-id",
      "captioner": "caption-model-id"
    }
  }
}
```

There is no global `default_resource_id` for this capability.

When `IMAGE_ANALYSIS_URL` is configured and the provider advertises all four v1
resources from `/v1/resources`, backend bootstrap registers platform-owned
ModelOps records for those resources, validates them from provider inventory,
activates them, and binds them into local deployment profiles as task defaults.
Superadmins may still register image-analysis resources manually through
ModelOps using the task keys above.
