# scan-worker

Celery worker that executes SAST (Static Application Security Testing) scans.  
Triggered by **scan-service** via a Redis-backed task queue, runs all applicable security tools against a code target, and persists findings to PostgreSQL.

---

## How It Works

1. **scan-service** creates a `ScanJob` record and enqueues a Celery task
2. **scan-worker** picks up the task, clones the Git repo or extracts the uploaded ZIP
3. Language / project type is detected automatically from file extensions
4. All applicable tools run sequentially; results are deduplicated by fingerprint
5. Normalised findings are written to `scan_findings`; the job status is updated to `completed` (or `failed`)

---

## Tools

| Tool | Domain | Condition |
|------|--------|-----------|
| [Bandit](https://bandit.readthedocs.io) | Python SAST | Always |
| [Semgrep](https://semgrep.dev) | Multi-language SAST (OWASP, secrets, framework rules) | Always |
| [Gitleaks](https://gitleaks.io) | Secret / credential detection | Always |
| [Trivy](https://trivy.dev) | Dependency CVEs + IaC misconfigurations | Always |
| [Hadolint](https://github.com/hadolint/hadolint) | Dockerfile lint | If Dockerfile present |
| [pip-audit](https://github.com/pypa/pip-audit) | Python dependency CVEs | If `requirements*.txt` / `pyproject.toml` / `Pipfile` |
| [npm audit](https://docs.npmjs.com/cli/commands/npm-audit) | Node.js dependency CVEs | If `package.json` present |
| [gosec](https://github.com/securego/gosec) | Go security analysis | If `*.go` files present |

### Semgrep rulesets

Base (always applied):
- `p/owasp-top-ten`
- `p/secrets`
- `p/security-audit`

Language-specific (auto-detected):
- Python → `p/python`, `p/django`, `p/flask`
- JavaScript → `p/javascript`, `p/express`
- TypeScript → `p/typescript`, `p/express`
- Java → `p/java`
- Go → `p/go`
- PHP → `p/php`
- Ruby → `p/ruby`
- C/C++ → `p/c`
- Rust → `p/rust`

---

## Normalised Finding Format

Every tool output is parsed into a common structure before being stored:

```json
{
  "id": "uuid",
  "tool": "bandit | semgrep | gitleaks | trivy | hadolint | pip-audit | npm-audit | gosec",
  "rule_id": "B105",
  "severity": "critical | high | medium | low | info",
  "confidence": "high | medium | low | null",
  "title": "Hardcoded password string",
  "message": "Possible hardcoded password: 'secret123'",
  "file_path": "app/config.py",
  "line_start": 42,
  "line_end": null,
  "code_snippet": "password = 'secret123'",
  "cwe": "CWE-259",
  "owasp": "A07:2021 – Identification and Authentication Failures",
  "fingerprint": "sha256-hex-64-chars"
}
```

Findings are deduplicated by `fingerprint` before being persisted — the same issue found by multiple tools appears only once.

---

## Project Structure

```
scan-worker/
├── src/
│   ├── celery_app.py          # Celery application + Redis config
│   ├── global_settings.py     # Workspace / upload directory paths
│   ├── runners/               # One module per tool — subprocess invocation
│   │   ├── bandit_runner.py
│   │   ├── semgrep_runner.py
│   │   ├── gitleaks_runner.py
│   │   ├── trivy_runner.py
│   │   ├── hadolint_runner.py
│   │   ├── pip_audit_runner.py
│   │   ├── npm_audit_runner.py
│   │   └── gosec_runner.py
│   ├── parsers/               # One module per tool — raw output → normalised dicts
│   │   ├── bandit_parser.py
│   │   ├── semgrep_parser.py
│   │   ├── gitleaks_parser.py
│   │   ├── trivy_parser.py
│   │   ├── hadolint_parser.py
│   │   ├── pip_audit_parser.py
│   │   ├── npm_audit_parser.py
│   │   └── gosec_parser.py
│   ├── tasks/
│   │   └── sast.py            # Main Celery task — orchestrates all tools
│   ├── database/
│   │   ├── db_connection.py
│   │   └── models/
│   │       ├── ScanJob.py
│   │       └── ScanFinding.py
│   └── utils/
│       └── git_utils.py       # clone_repo, extract_zip, cleanup
├── requirements.txt
└── Dockerfile
```

---

## Local Setup (Windows)

### Python dependencies

```powershell
pip install -r requirements.txt
# includes: celery, bandit, semgrep, pip-audit
```

### Binary tools

```powershell
# Gitleaks
winget install gitleaks.gitleaks

# Trivy
winget install aquasecurity.trivy

# Hadolint
winget install hadolint.hadolint

# gosec  (only needed for Go projects)
winget install securego.gosec
```

> After winget install, open a **new terminal** so PATH changes take effect.

### Run the worker

```powershell
python -m celery -A src.celery_app worker -Q sast --loglevel=info
```

---

## Docker

The Dockerfile installs all binary tools at build time — no manual setup needed in containers.

```bash
docker build -t scan-worker .
docker run --env-file .env scan-worker
```

### Environment variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string (Celery broker + backend) |
| `SCAN_WORKSPACE_DIR` | Temp directory for cloned/extracted repos (default: `/tmp/cybercore/scans`) |
| `SCAN_UPLOAD_DIR` | Directory where scan-service stores uploaded ZIPs |

---

## Adding a New Tool

1. Create `src/runners/<tool>_runner.py` — `run(source_dir: Path) -> <raw output>`
2. Create `src/parsers/<tool>_parser.py` — `parse(raw, source_dir: Path) -> list[dict]`
3. Import both in `src/tasks/sast.py` and add a `collect(...)` call with any condition
4. Install the binary in `Dockerfile` and (optionally) `requirements.txt`
