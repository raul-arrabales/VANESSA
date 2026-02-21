FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN if [ -f /app/requirements.txt ]; then pip install --no-cache-dir -r /app/requirements.txt; fi
COPY backend/ /app/backend/
EXPOSE 5000
CMD ["sh", "-c", "cd /app/backend && flask --app app.app run --host=0.0.0.0 --port=5000 --debug"]
