FROM python:3.12-slim

# ── System deps ────────────────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Python deps ───────────────────────────────────────────────────────────────────
COPY requirements.in .
RUN pip install --no-cache-dir -r requirements.in \
        PyMySQL>=1.1.0 \
        cryptography>=42.0.0 \
        httpx>=0.27.0

# ── Application source ────────────────────────────────────────────────────────────
COPY . .

# ── Runtime config ────────────────────────────────────────────────────────────────
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

EXPOSE 8081

CMD ["uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8081"]
