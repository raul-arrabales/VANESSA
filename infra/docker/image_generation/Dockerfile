# syntax=docker/dockerfile:1.7

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY image_generation/requirements.txt /tmp/image-generation-requirements.txt
RUN --mount=type=cache,id=vanessa-image-generation-pip,target=/root/.cache/pip \
    pip install -r /tmp/image-generation-requirements.txt

ENV HF_HOME=/models/image_generation/huggingface \
    TORCH_HOME=/models/image_generation/torch \
    XDG_CACHE_HOME=/models/image_generation/cache \
    MPLCONFIGDIR=/tmp/matplotlib


FROM base AS gateway

COPY image_generation /app/image_generation

EXPOSE 8094

CMD ["python", "-m", "image_generation.app.main"]


FROM base AS runtime-base

ARG IMAGE_GENERATION_INSTALL_RUNTIME_DEPS=0
RUN if [ "${IMAGE_GENERATION_INSTALL_RUNTIME_DEPS}" = "1" ]; then \
        apt-get update \
        && apt-get install -y --no-install-recommends \
            libgl1 \
            libglib2.0-0 \
            libsm6 \
            libxext6 \
            libxrender1 \
            libxcb1 \
        && rm -rf /var/lib/apt/lists/*; \
    fi


FROM runtime-base AS text-to-image

ARG IMAGE_GENERATION_INSTALL_RUNTIME_DEPS=0
COPY image_generation/requirements-text-to-image.txt /tmp/image-generation-text-to-image-requirements.txt
RUN --mount=type=cache,id=vanessa-image-generation-pip,target=/root/.cache/pip \
    if [ "${IMAGE_GENERATION_INSTALL_RUNTIME_DEPS}" = "1" ]; then \
        pip install -r /tmp/image-generation-text-to-image-requirements.txt; \
    fi

COPY image_generation /app/image_generation

EXPOSE 8094

CMD ["python", "-m", "image_generation.app.main"]


FROM runtime-base AS plate-logo

ARG IMAGE_GENERATION_INSTALL_RUNTIME_DEPS=0
COPY image_generation/requirements-plate-logo.txt /tmp/image-generation-plate-logo-requirements.txt
RUN --mount=type=cache,id=vanessa-image-generation-pip,target=/root/.cache/pip \
    if [ "${IMAGE_GENERATION_INSTALL_RUNTIME_DEPS}" = "1" ]; then \
        pip install -r /tmp/image-generation-plate-logo-requirements.txt; \
    fi

COPY image_generation /app/image_generation

EXPOSE 8094

CMD ["python", "-m", "image_generation.app.main"]


FROM runtime-base AS all

ARG IMAGE_GENERATION_INSTALL_RUNTIME_DEPS=0
COPY image_generation/requirements-runtime.txt /tmp/image-generation-runtime-requirements.txt
RUN --mount=type=cache,id=vanessa-image-generation-pip,target=/root/.cache/pip \
    if [ "${IMAGE_GENERATION_INSTALL_RUNTIME_DEPS}" = "1" ]; then \
        pip install -r /tmp/image-generation-runtime-requirements.txt; \
    fi

COPY image_generation /app/image_generation

EXPOSE 8094

CMD ["python", "-m", "image_generation.app.main"]
