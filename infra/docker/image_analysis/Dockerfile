# syntax=docker/dockerfile:1.7

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY image_analysis/requirements.txt /tmp/image-analysis-requirements.txt
RUN --mount=type=cache,id=vanessa-image-analysis-pip,target=/root/.cache/pip \
    pip install -r /tmp/image-analysis-requirements.txt

ENV HF_HOME=/models/image_analysis/huggingface \
    TORCH_HOME=/models/image_analysis/torch \
    XDG_CACHE_HOME=/models/image_analysis/cache \
    MPLCONFIGDIR=/tmp/matplotlib


FROM base AS gateway

COPY image_analysis /app/image_analysis

EXPOSE 8090

CMD ["python", "-m", "image_analysis.app.main"]


FROM base AS runtime-base

ARG IMAGE_ANALYSIS_INSTALL_RUNTIME_DEPS=0
RUN if [ "${IMAGE_ANALYSIS_INSTALL_RUNTIME_DEPS}" = "1" ]; then \
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


FROM runtime-base AS anpr

ARG IMAGE_ANALYSIS_INSTALL_RUNTIME_DEPS=0
COPY image_analysis/requirements-anpr.txt /tmp/image-analysis-anpr-requirements.txt
RUN --mount=type=cache,id=vanessa-image-analysis-pip,target=/root/.cache/pip \
    if [ "${IMAGE_ANALYSIS_INSTALL_RUNTIME_DEPS}" = "1" ]; then \
        pip install -r /tmp/image-analysis-anpr-requirements.txt; \
    fi

COPY image_analysis /app/image_analysis

EXPOSE 8090

CMD ["python", "-m", "image_analysis.app.main"]


FROM runtime-base AS objects

ARG IMAGE_ANALYSIS_INSTALL_RUNTIME_DEPS=0
COPY image_analysis/requirements-objects.txt /tmp/image-analysis-objects-requirements.txt
RUN --mount=type=cache,id=vanessa-image-analysis-pip,target=/root/.cache/pip \
    if [ "${IMAGE_ANALYSIS_INSTALL_RUNTIME_DEPS}" = "1" ]; then \
        pip install -r /tmp/image-analysis-objects-requirements.txt; \
    fi

COPY image_analysis /app/image_analysis

EXPOSE 8090

CMD ["python", "-m", "image_analysis.app.main"]


FROM runtime-base AS captioning

ARG IMAGE_ANALYSIS_INSTALL_RUNTIME_DEPS=0
COPY image_analysis/requirements-captioning.txt /tmp/image-analysis-captioning-requirements.txt
RUN --mount=type=cache,id=vanessa-image-analysis-pip,target=/root/.cache/pip \
    if [ "${IMAGE_ANALYSIS_INSTALL_RUNTIME_DEPS}" = "1" ]; then \
        pip install -r /tmp/image-analysis-captioning-requirements.txt; \
    fi

COPY image_analysis /app/image_analysis

EXPOSE 8090

CMD ["python", "-m", "image_analysis.app.main"]


FROM runtime-base AS all

ARG IMAGE_ANALYSIS_INSTALL_RUNTIME_DEPS=0
COPY image_analysis/requirements-runtime.txt /tmp/image-analysis-runtime-requirements.txt
RUN --mount=type=cache,id=vanessa-image-analysis-pip,target=/root/.cache/pip \
    if [ "${IMAGE_ANALYSIS_INSTALL_RUNTIME_DEPS}" = "1" ]; then \
        pip install -r /tmp/image-analysis-runtime-requirements.txt; \
    fi

COPY image_analysis /app/image_analysis

EXPOSE 8090

CMD ["python", "-m", "image_analysis.app.main"]
