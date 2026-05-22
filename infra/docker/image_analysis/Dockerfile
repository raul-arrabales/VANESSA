FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY image_analysis/requirements.txt /tmp/image-analysis-requirements.txt
COPY image_analysis/requirements-runtime.txt /tmp/image-analysis-runtime-requirements.txt

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
    fi \
    && pip install --no-cache-dir -r /tmp/image-analysis-requirements.txt \
    && if [ "${IMAGE_ANALYSIS_INSTALL_RUNTIME_DEPS}" = "1" ]; then \
        pip install --no-cache-dir -r /tmp/image-analysis-runtime-requirements.txt; \
    fi

ENV HF_HOME=/models/image_analysis/huggingface \
    TORCH_HOME=/models/image_analysis/torch \
    XDG_CACHE_HOME=/models/image_analysis/cache \
    MPLCONFIGDIR=/tmp/matplotlib

COPY image_analysis /app/image_analysis

EXPOSE 8090

CMD ["python", "-m", "image_analysis.app.main"]
