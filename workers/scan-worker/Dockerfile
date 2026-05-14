FROM python:3.12-slim

# ── System deps + Node.js 20 ──────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        git curl ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# ── Gitleaks (secret scanner) ─────────────────────────────────────────────────
ARG GITLEAKS_VERSION=8.18.4
RUN curl -sSfL \
      "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz" \
    | tar -xz -C /usr/local/bin gitleaks \
    && chmod +x /usr/local/bin/gitleaks

# ── gosec (Go security analyser) ──────────────────────────────────────────────
ARG GOSEC_VERSION=2.21.4
RUN curl -sSfL \
      "https://github.com/securego/gosec/releases/download/v${GOSEC_VERSION}/gosec_${GOSEC_VERSION}_linux_amd64.tar.gz" \
    | tar -xz -C /usr/local/bin gosec \
    && chmod +x /usr/local/bin/gosec

# ── Trivy (vuln scanner + IaC misconfig) ─────────────────────────────────────
RUN curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh \
    | sh -s -- -b /usr/local/bin

# ── Hadolint (Dockerfile linter) ─────────────────────────────────────────────
ARG HADOLINT_VERSION=2.12.0
RUN curl -sSfL \
      "https://github.com/hadolint/hadolint/releases/download/v${HADOLINT_VERSION}/hadolint-Linux-x86_64" \
      -o /usr/local/bin/hadolint \
    && chmod +x /usr/local/bin/hadolint


WORKDIR /app

# ── Python deps (includes pip-audit, bandit, semgrep, celery, SQLAlchemy) ────
# PyMySQL is required by the mysql+pymysql SQLAlchemy driver.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
        PyMySQL>=1.1.0 \
        cryptography>=42.0.0

COPY . .

ENV SCAN_WORKSPACE_DIR=/tmp/cybercore/scans
ENV SCAN_UPLOAD_DIR=/tmp/cybercore/uploads

CMD ["python", "-m", "celery", "-A", "src.celery_app:celery_app", "worker", \
     "--loglevel=INFO", "--queues=sast", "--concurrency=2", "--hostname=scan-worker@%h"]
