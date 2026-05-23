# Image Generation Service

`image_generation` is an optional local provider for VANESSA image generation and image editing. It is selected through the platform control plane as capability `image_generation` with provider family `image_generation_local` and adapter `image_generation_http`.

## Runtime Layout

- Compose gateway service: `image_generation`
- Private worker services: `image_generation_text_to_image`, `image_generation_plate_logo`
- Optional profile: `image_generation`
- Gateway port: `8094`
- Model mount: `models/image_generation:/models/image_generation`
- Backend seed env: `IMAGE_GENERATION_URL=http://image_generation:8094`

The gateway exposes:

- `GET /health`
- `GET /v1/resources`
- `POST /v1/generate`

Worker startup is launch-time configurable with `IMAGE_GENERATION_WORKERS`, defaulting to `text_to_image,plate_logo`. Use `none` to start only the gateway and advertise no resources.

## Tasks

- `text_to_image`: generates an image from `prompt`, optional `negative_prompt`, and generation options. The default worker model is `segmind/tiny-sd`, loaded with Diffusers. It is CPU-capable but slow, so default local settings keep image size and step count conservative.
- `license_plate_logo_replacement`: replaces detected license plate regions with a supplied logo using `car_image`, `logo_image`, and `plate_boxes` from image-analysis plate detection output.

Image payload bytes must not be logged, stored, or included in telemetry. The provider returns generated or modified bytes directly to the caller.

## ModelOps Binding

`image_generation` uses `resource_policy.selection_mode="task_defaults"`:

- `generator` maps to ModelOps task key `image_text_to_image`.
- `plate_logo_processor` maps to provider-native resource key `image_plate_logo_replacement`.

When `IMAGE_GENERATION_URL` is configured and the provider advertises complete task groups from `/v1/resources`, backend bootstrap registers the text-to-image generator as a platform-owned ModelOps record, binds provider-native processor resources directly, and adds the complete task defaults to local deployment profiles.
