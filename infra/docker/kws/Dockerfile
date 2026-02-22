FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN if [ -f /app/requirements.txt ]; then pip install --no-cache-dir -r /app/requirements.txt; fi

COPY kws/ /app/kws/

EXPOSE 10400

CMD ["python", "/app/kws/app/main.py"]
