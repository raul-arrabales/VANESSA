FROM python:3.11-slim
WORKDIR /app
ENV PYTHONPATH=/app
COPY requirements.txt /app/requirements.txt
RUN if [ -f /app/requirements.txt ]; then pip install --no-cache-dir -r /app/requirements.txt; fi
COPY vanessa_shared/ /app/vanessa_shared/
COPY agent_engine/ /app/agent_engine/
EXPOSE 7000
CMD ["python", "-m", "agent_engine.app.main"]
