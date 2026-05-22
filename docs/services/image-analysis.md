# Image Analysis Service

`image_analysis` is an optional local provider for VANESSA image understanding. It is selected through the platform control plane as capability `image_analysis` with provider family `image_analysis_local` and adapter `image_analysis_http`.

The public provider remains a single gateway service. In local Docker deployments, the gateway delegates model execution to private task workers so ANPR, object detection, and captioning can isolate dependencies, model memory, startup cost, and runtime failures.

## Runtime

- Compose gateway service: `image_analysis`
- Private worker services: `image_analysis_anpr`, `image_analysis_objects`, `image_analysis_captioning`
- Optional profile: `image_analysis`
- Default port: `8090`
- Model mount: `models/image_analysis:/models/image_analysis`
- Backend seed env: `IMAGE_ANALYSIS_URL=http://image_analysis:8090`

The service exposes:

- `GET /health`
- `GET /v1/resources`
- `POST /v1/analyze`

`POST /v1/analyze` accepts JSON only. Callers provide `image.data_base64`, `image.mime_type`, and one or more tasks: `license_plate_recognition`, `object_detection`, or `captioning`. Backend, agent engine, and frontend-facing tools continue to call only the gateway URL; workers are private Compose services with no host-published ports.

Image bytes are transient request data. The service does not log image payloads by default, and backend/agent call records redact base64 image data.

Gateway worker URLs default to the Compose service names:

- `IMAGE_ANALYSIS_ANPR_URL=http://image_analysis_anpr:8091`
- `IMAGE_ANALYSIS_OBJECTS_URL=http://image_analysis_objects:8092`
- `IMAGE_ANALYSIS_CAPTIONING_URL=http://image_analysis_captioning:8093`

The gateway returns partial results with task-specific warnings if one requested worker is unavailable.

## Models

V1 defaults are local open-source models:

- Plate detection: `open-image-models` through `fast-alpr`
- Plate OCR: `fast-plate-ocr` through `fast-alpr`
- Object detection: RF-DETR
- Captioning: Florence-2, defaulting to `florence-community/Florence-2-base-ft`

CI and first-boot smoke tests can use `IMAGE_ANALYSIS_FAKE_MODE=1` for deterministic non-model output at the gateway. The image builds with only lightweight dependencies by default. Set `IMAGE_ANALYSIS_INSTALL_RUNTIME_DEPS=1` and rebuild when you want worker images to install their real task-specific runtime dependencies.

The Dockerfile uses separate build targets for the gateway and each task worker. Worker targets copy only their own requirements file before installing task dependencies, so changing object-detection dependencies does not invalidate the captioning or ANPR dependency cache on later rebuilds. Dependency install steps also use a shared BuildKit pip cache mount so large wheels such as Torch can be reused even when a dependency layer has to run again.

When real runtime dependencies are enabled, the Docker image also installs the small set of Debian shared libraries required by RF-DETR/OpenCV-style imports on `python:3.11-slim`.

The RF-DETR dependency currently requires Transformers 5.x, so the runtime requirements intentionally use `transformers>=5.1.0,<6.0.0` rather than the older Florence-2-era 4.x pin. The object worker also pins `torch==2.9.1` and `torchvision==0.24.1` so Docker builds do not drift into a different Torch/CUDA family from resolver churn.
RF-DETR runs on `cuda` when CUDA is available and otherwise falls back to `cpu`; override with `IMAGE_ANALYSIS_RFDETR_DEVICE` when you need to pin a device explicitly.
Florence-2 also requires `einops` and `timm` at runtime. Captioning is CPU-expensive, so the default local-staging settings use a 512px caption image, greedy decoding, and 48 generated tokens. Override `IMAGE_ANALYSIS_FLORENCE_IMAGE_SIZE`, `IMAGE_ANALYSIS_FLORENCE_NUM_BEAMS`, and `IMAGE_ANALYSIS_FLORENCE_MAX_NEW_TOKENS` when you want to trade latency for richer captions.

Each worker keeps only its own model family resident. Model caches are rooted under worker-specific subdirectories of the mounted model directory, such as `/models/image_analysis/objects` and `/models/image_analysis/captioning`. This lets rebuilt or restarted containers reuse downloaded model artifacts without mixing worker caches.
The backend provider timeout defaults to `IMAGE_ANALYSIS_REQUEST_TIMEOUT_SECONDS=300` because first-run real model loading can exceed normal LLM request timeouts.

The container split improves reliability and operability, but object detection accuracy still depends on the selected ModelOps resource and its task/model fit. Replacing or validating the detector model is a separate ModelOps concern.

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
