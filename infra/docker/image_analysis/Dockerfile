FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY image_analysis/requirements.txt /tmp/image-analysis-requirements.txt
RUN pip install --no-cache-dir -r /tmp/image-analysis-requirements.txt

COPY image_analysis /app/image_analysis

EXPOSE 8090

CMD ["python", "-m", "image_analysis.app.main"]
