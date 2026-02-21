FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN if [ -f /app/requirements.txt ]; then pip install --no-cache-dir -r /app/requirements.txt; fi
COPY agent_engine/ /app/agent_engine/
EXPOSE 7000
CMD ["python", "/app/agent_engine/app/main.py"]
