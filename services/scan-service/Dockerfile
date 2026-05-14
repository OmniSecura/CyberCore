FROM python:3.12-slim

# ── System deps ───────────────────────────────────────────────────────────────
# build-essential is needed by some checkov / cryptography native extensions.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libffi-dev \
        git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Python deps ───────────────────────────────────────────────────────────────
# PyMySQL is required by the mysql+pymysql SQLAlchemy driver.
COPY requirements.in .
RUN pip install --no-cache-dir -r requirements.in \
        PyMySQL>=1.1.0 \
        cryptography>=42.0.0

# ── Application source ────────────────────────────────────────────────────────
COPY . .

# ── Runtime config ────────────────────────────────────────────────────────────
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

EXPOSE 8082

CMD ["uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8082"]
