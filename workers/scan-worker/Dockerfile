FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV SCAN_WORKSPACE_DIR=/tmp/cybercore/scans
ENV SCAN_UPLOAD_DIR=/tmp/cybercore/uploads

CMD ["python", "-m", "celery", "-A", "src.celery_app:celery_app", "worker", "--loglevel=INFO", "--queues=sast", "--concurrency=2", "--hostname=scan-worker@%h"]
