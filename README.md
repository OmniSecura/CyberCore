# CyberCore 🛡️

> **Open-source platform for cybersecurity monitoring, vulnerability scanning, and threat detection.**  
> Built for developers, security teams, and sysadmins who want full control over their security stack — without sending their data to third parties.

---

## What is CyberCore?

CyberCore is a self-hosted, modular cybersecurity platform. It combines static code analysis, dynamic application testing, real-time system monitoring, and centralized log management into one coherent system — deployable on your own infrastructure in minutes.

Think of it as your own private security operations center (SOC), minus the six-figure enterprise license.

---

## Architecture Overview

```
cybercore/
├── services/
│   ├── auth-service/          # Identity, MFA, OAuth2
│   ├── tenant-service/        # Multi-tenant management
│   ├── scan-service/          # Unified scan orchestrator
│   ├── sast-service/          # Static Application Security Testing
│   ├── dast-service/          # Dynamic Application Security Testing
│   ├── log-service/           # Centralized log ingestion & API
│   ├── agent-service/         # Receives data from system agents
│   ├── alert-service/          # Alerting & notification engine
│   └── organization-service/  # Creating/managing organizations and projects
├── workers/
│   ├── scan-worker/           # Celery — runs bandit, semgrep, ZAP
│   ├── log-consumer/          # Kafka consumer → TimescaleDB
│   └── ml-worker/             # Anomaly detection engine
├── shared/
│   ├── cybercore-commons/     # Shared Pydantic schemas, enums, error codes
│   └── cybercore-db/          # SQLAlchemy base models
├── sdks/
│   ├── cyberlog-python/       # pip install cyberlog
│   ├── cyberlog-js/           # npm install cyberlog
│   └── cyberlog-go/           # go get cyberlog
├── agent/
│   ├── core/                  # C++ — network sniffer, process monitor
│   └── orchestrator/          # Python — dispatches data to agent-service
├── dashboard/                 # React frontend
└── k8s/                       # Helm charts & Kubernetes manifests
```

Every component is independently deployable. Use only what you need.

---

## Services

### 🔐 Auth Service
Full identity management built for security-first applications.

- User registration with **email, first name, last name**
- Password confirmation on signup (enter twice)
- Strong password policy: minimum 12 characters, uppercase, lowercase, number, special character
- **Multi-Factor Authentication (MFA)** — TOTP (Google Authenticator, Authy)
- **OAuth2 / Social login** — Google, GitHub (extensible)
- Every user receives a **unique UUID** upon registration
- JWT-based sessions with refresh token rotation
- Rate limiting on all auth endpoints (brute-force protection)
- Account lockout after repeated failed attempts

---

### 🔬 Scan Service
The unified scan orchestrator — the central nervous system of CyberCore's security scanning.

All scan types (SAST, DAST, agent scans) report their results through this service, which normalizes them into a **single, consistent format** regardless of the underlying tool. This means your dashboard, alerts, and reports always look the same whether the finding came from Semgrep, ZAP, or a custom scanner.

**Unified finding format:**
```json
{
  "scan_id": "uuid",
  "scan_type": "SAST | DAST | AGENT",
  "severity": "CRITICAL | HIGH | MEDIUM | LOW | INFO",
  "title": "SQL Injection in user input handler",
  "description": "...",
  "location": { "file": "app/db.py", "line": 42 },
  "remediation": "Use parameterized queries",
  "tool": "semgrep",
  "confidence": 0.93,
  "created_at": "2025-01-01T00:00:00Z"
}
```

---

### 🧪 SAST Service
Static Application Security Testing — finds vulnerabilities in your code before it runs.

**Input methods:**
- Upload a single file
- Upload a zip archive (folder)
- Provide a **public Git repository URL**
- Provide a **private Git repository URL** (with token-based authentication — GitHub PAT, GitLab token)

**Recommended scanning tools (all open-source):**

| Tool | Language Coverage | Best For |
|------|-------------------|----------|
| [Semgrep](https://semgrep.dev) | Python, JS, Go, Java, Ruby, C/C++, and more | Custom rules, fast scanning, OWASP coverage |
| [Bandit](https://bandit.readthedocs.io) | Python only | Deep Python security checks |
| [Gosec](https://github.com/securego/gosec) | Go only | Go-specific vulnerability patterns |
| [ESLint Security](https://github.com/eslint-community/eslint-plugin-security) | JavaScript/TypeScript | JS injection, prototype pollution |
| [Gitleaks](https://gitleaks.io) | All | Secret/credential detection in code history |

Recommended default: **Semgrep** as the primary engine with Bandit as a secondary pass for Python projects. Gitleaks runs on every scan automatically to catch accidentally committed secrets.

---

### 🌐 DAST Service
Dynamic Application Security Testing — attacks your running application the same way a real attacker would.

**What it can do:**

- **Crawling** — automatic discovery of endpoints, forms, and API routes
- **Injection testing** — SQL injection, command injection, LDAP injection
- **XSS scanning** — reflected, stored, and DOM-based cross-site scripting
- **Authentication testing** — broken auth, session fixation, insecure cookies
- **IDOR detection** — tests for insecure direct object references across authenticated sessions
- **SSRF probing** — detects server-side request forgery vectors
- **Security headers audit** — checks for missing CSP, HSTS, X-Frame-Options
- **TLS/SSL analysis** — weak ciphers, expired certificates, misconfigured protocols
- **API fuzzing** — tests REST/GraphQL endpoints with malformed and boundary inputs
- **Rate limit bypass attempts** — validates that your rate limiting actually works

**Underlying engine:** [OWASP ZAP](https://www.zaproxy.org/) (industry standard, actively maintained, extensible via plugins)

> ⚠️ Only scan applications you own or have explicit written permission to test. CyberCore includes safeguards to prevent accidental scanning of out-of-scope targets.

---

### 📋 Log Service
Centralized log ingestion with project-based isolation — like a self-hosted Datadog Logs, but yours.

**How it works:**

1. Create a **project** in the dashboard
2. Generate an **API key** for that project
3. Initialize `CyberLogCore` in your application with that key
4. Logs appear in your project — isolated from all other projects

```python
# Python example
from cyberlog import CyberLogCore

log = CyberLogCore(api_key="ccl_your_key_here", project="my-backend")

log.info("User logged in", user_id="abc123")
log.error("Payment failed", order_id="xyz", amount=99.99)
log.warning("Rate limit approaching", endpoint="/api/v1/scan")
```

```javascript
// JavaScript example
import { CyberLogCore } from 'cyberlog';

const log = new CyberLogCore({ apiKey: 'ccl_your_key_here', project: 'my-frontend' });

log.info('Component mounted', { page: 'dashboard' });
log.error('API call failed', { status: 500, url: '/api/scans' });
```

**Features:**
- Project-based isolation — each API key only sees its own logs
- Structured logging with arbitrary metadata fields
- Log levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- Full-text search across log messages and metadata
- Retention policies per project
- Webhook alerts on `ERROR` / `CRITICAL` level events
- SDKs: Python, JavaScript, Go

---

### 🤖 Agent Service
Receives telemetry from the CyberCore Agent running on monitored machines and turns raw data into actionable alerts.

**What the agent collects:**

- Running processes and unusual process trees
- Network connections (open ports, suspicious outbound connections)
- File system changes in sensitive directories
- CPU/RAM/disk anomalies that may indicate cryptomining or DoS
- Failed login attempts and privilege escalation events
- DNS queries (detecting C2 beaconing patterns)
- Loaded kernel modules

**The agent-service:**
- Ingests this telemetry stream
- Runs it through the **ML anomaly detection worker** (baseline + deviation scoring)
- Generates alerts for the responsible admin or user
- Supports **multi-machine management** — one admin can monitor a fleet of machines
- Integrates with the alert-service for notifications (email, webhook, Slack)

---

### 🚨 Alert Service
Unified notification layer for all CyberCore events.

- Configurable severity thresholds (e.g., only alert on HIGH and above)
- Notification channels: email, webhook, Slack, Discord, Telegram
- Alert deduplication (don't get 200 emails for the same issue)
- Escalation policies — if alert isn't acknowledged in N minutes, escalate to next contact

---

## Quick Start

### Prerequisites
- Docker and Docker Compose
- 8 GB RAM minimum (16 GB recommended for full stack)
- Git

### Run the core stack

```bash
git clone https://github.com/yourname/cybercore.git
cd cybercore

cp .env.example .env
# Edit .env — set POSTGRES_PASSWORD, JWT_SECRET etc.

docker compose --profile core up
```

Dashboard available at: `http://localhost:3000`

### Run with scanning enabled

```bash
docker compose --profile core --profile scanning up
```

### Run the full stack

```bash
docker compose --profile full up
```

---

## Configuration

All configuration is done via environment variables. Copy `.env.example` to `.env` and adjust:

```bash
# Required
POSTGRES_PASSWORD=change_me_in_production
JWT_SECRET=change_me_in_production_use_64_char_random_string
ENVIRONMENT=development

# Optional — OAuth (for Google login)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# Optional — notifications
SMTP_HOST=
SMTP_PORT=587
SLACK_WEBHOOK_URL=
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend services | Python / FastAPI |
| Task queue | Celery + Redis |
| Message streaming | Apache Kafka |
| Primary database | PostgreSQL |
| Time-series data | TimescaleDB |
| Cache | Redis |
| Frontend | React |
| Container orchestration | Docker Compose (dev), Kubernetes/k3s (prod) |
| Package management | Helm |
| CI/CD | GitHub Actions |
| GitOps | Argo CD |
| Monitoring | Prometheus + Grafana |
| Logging | Loki |
| Tracing | Jaeger |
| System agent | C++ (core) + Python (orchestrator) |

---

## Deployment

### Local development
Docker Compose with profile-based selective startup (see Quick Start above).

### Production (self-hosted)
Kubernetes via Helm charts located in `k8s/`. Tested on k3s (lightweight Kubernetes — ideal for a home server or VPS).

```bash
# Install on your cluster
helm install cybercore ./k8s/cybercore \
  --namespace cybercore \
  --create-namespace \
  -f values.production.yaml
```

### Recommended infrastructure
- **Dev/staging:** k3s on a local machine or Hetzner VPS (~€35/month for a capable node)
- **Production:** AWS EKS or Hetzner Cloud with managed load balancer
- **EU-based hosting recommended** for GDPR compliance if serving European users

---

## Roadmap

- [ ] SAST support for more languages (Rust, PHP, C#)
- [ ] DAST authenticated scan flows (log in as a user, then test)
- [ ] Agent for Windows (currently Linux/macOS)
- [ ] ML-based code vulnerability detection (beyond rule-based)
- [ ] Compliance reports (OWASP Top 10, CWE/SANS 25)
- [ ] Integrations: Jira, GitHub Issues, PagerDuty
- [ ] Mobile app for alert management
- [ ] Self-updating agent via agent-service

---

## Contributing

CyberCore is in active development. Contributions are welcome.

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Commit with conventional commits: `git commit -m "feat(sast): add PHP scanning support"`
4. Open a pull request against `main`

Please read `CONTRIBUTING.md` before submitting a PR. All security-related contributions go through an additional review process.

---

## Security

Found a vulnerability in CyberCore itself? Please do **not** open a public issue.

Report it privately via email to: `security@cybercore.dev` (or update this with your actual contact).

We aim to respond within 48 hours and will credit responsible disclosure in the changelog.

---

## License

MIT License — see `LICENSE` for details.

You are free to use, modify, and distribute CyberCore, including for commercial purposes.  
The CyberCore name and logo are separate trademarks.

---

<p align="center">
  Built with the belief that security tooling shouldn't require an enterprise contract.
</p>