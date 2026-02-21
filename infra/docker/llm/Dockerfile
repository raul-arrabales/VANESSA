FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn
EXPOSE 8000
CMD ["python", "-m", "http.server", "8000"]
