FROM python:3.12-slim

# ── System deps ───────────────────────────────────────────────────────────────
# build-essential / libffi-dev are required by argon2-cffi (native extension).
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Python deps ───────────────────────────────────────────────────────────────
# Install from the authoritative requirements.in.
# PyMySQL is added here because the DB_CONNECTOR=mysql driver (mysql+pymysql)
# is not listed in requirements.in (which ships the psycopg fallback).
# redis is the token-blacklist backend (also tracked in requirements.txt).
COPY requirements.in .
RUN pip install --no-cache-dir -r requirements.in \
        PyMySQL>=1.1.0 \
        cryptography>=42.0.0 \
        redis>=5.0.0

# ── Application source ────────────────────────────────────────────────────────
COPY . .

# ── Runtime config ────────────────────────────────────────────────────────────
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8000"]
