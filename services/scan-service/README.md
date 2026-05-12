# Scan Service

FastAPI microservice na porcie **8085** odpowiedzialny za przyjmowanie zadań skanowania SAST, kolejkowanie ich przez Celery/Redis i zwracanie wyników przez REST API.

---

## Zależności zewnętrzne

Przed uruchomieniem scan serwisu **muszą być aktywne**:

| Serwis | Domyślny adres | Rola |
|--------|---------------|------|
| MySQL | `localhost:3306` | Baza danych skanów |
| Redis | `localhost:6379` | Broker Celery + cache wyników |
| Auth Service | `localhost:8000` | Weryfikacja tokenów JWT (`/api/v1/users/me`) |
| Organization Service | `localhost:8081` | Sprawdzanie uprawnień (`scans.run` / `scans.view` / `scans.manage`) |

Scan Worker musi być uruchomiony **osobno** — bez niego zadania trafią do kolejki Redis ale nigdy się nie wykonają.

---

## Krok po kroku

### 1. Uruchom MySQL i Redis

Lokalnie (Docker):

```bash
docker run -d --name cybercore-mysql \
  -e MYSQL_USER=cybercore \
  -e MYSQL_PASSWORD=secret \
  -e MYSQL_DATABASE=cybercore \
  -e MYSQL_ROOT_PASSWORD=rootsecret \
  -p 3306:3306 \
  mysql:8

docker run -d --name cybercore-redis \
  -p 6379:6379 \
  redis:7-alpine
```

### 2. Utwórz tabele w bazie

Wykonaj pliki SQL w tej kolejności (najpierw jobs, potem findings — FK zależność):

```bash
mysql -u cybercore -p cybercore < database/sql/tables/scans/scan_jobs.sql
mysql -u cybercore -p cybercore < database/sql/tables/scans/scan_findings.sql
```

Alternatywnie ustaw `DB_CREATE_TABLES=true` — serwis sam stworzy tabele przy starcie przez SQLAlchemy.

### 3. Zainstaluj zależności scan serwisu

```bash
cd services/scan-service
pip install -r requirements.in
```

### 4. Ustaw zmienne środowiskowe scan serwisu

```bash
# Baza danych
export DB_CONNECTOR=mysql
export AUTH_USERNAME=cybercore
export AUTH_PASSWORD=secret
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_DB=cybercore

# Redis / Celery
export CELERY_BROKER_URL=redis://localhost:6379/0
export CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Adresy innych serwisów
export AUTH_SERVICE_URL=http://localhost:8000
export ORG_SERVICE_URL=http://localhost:8081

# CORS (frontend)
export ALLOWED_ORIGINS=http://localhost:3000

# Folder na uploadowane ZIPy
export SCAN_UPLOAD_DIR=/tmp/cybercore/uploads

# Opcjonalne: tworzenie tabel przy starcie zamiast ręcznego SQL
export DB_CREATE_TABLES=true
```

### 5. Uruchom scan serwis

```bash
cd services/scan-service
python -m uvicorn src.server:app --host 0.0.0.0 --port 8085 --reload
```

Swagger UI dostępny pod: `http://localhost:8085/docs`

### 6. Zainstaluj zależności scan workera

```bash
cd workers/scan-worker
pip install -r requirements.txt
```

> Wymaga zainstalowanego `git` w systemie (do klonowania repozytoriów).
> Na Ubuntu/Debian: `apt install git`

Worker instaluje też `bandit` i `semgrep` automatycznie przez `requirements.txt`.

### 7. Ustaw zmienne środowiskowe scan workera

Worker łączy się z **tą samą bazą** co serwis i **tym samym Redis**:

```bash
# Baza danych (identyczne jak w scan serwisie)
export DB_CONNECTOR=mysql
export AUTH_USERNAME=cybercore
export AUTH_PASSWORD=secret
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_DB=cybercore

# Redis / Celery (identyczne jak w scan serwisie)
export CELERY_BROKER_URL=redis://localhost:6379/0
export CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Katalogi robocze workera
export SCAN_WORKSPACE_DIR=/tmp/cybercore/scans
export SCAN_UPLOAD_DIR=/tmp/cybercore/uploads
```

### 8. Uruchom scan workera

```bash
cd workers/scan-worker
python -m celery -A src.celery_app:celery_app worker \
  --loglevel=INFO \
  --queues=sast \
  --concurrency=2 \
  --hostname=scan-worker@%h
```

Lub przez skrypt:

```bash
python start_worker.py
```

---

## Kolejność uruchamiania (podsumowanie)

```
1. MySQL           ← baza danych
2. Redis           ← broker kolejki
3. Auth Service    ← weryfikacja JWT
4. Org Service     ← sprawdzanie uprawnień
5. Scan Service    ← REST API (port 8085)
6. Scan Worker     ← wykonuje skany w tle
```

---

## Zmienne środowiskowe — pełna lista

### Scan Service

| Zmienna | Domyślna | Opis |
|---------|---------|------|
| `DB_CONNECTOR` | `sqlite` | `mysql` / `postgresql` / `sqlite` |
| `AUTH_USERNAME` | — | Użytkownik bazy (MySQL / PostgreSQL) |
| `AUTH_PASSWORD` | — | Hasło bazy (MySQL / PostgreSQL) |
| `MYSQL_HOST` | — | Host MySQL |
| `MYSQL_PORT` | `3306` | Port MySQL |
| `MYSQL_DB` | `database` | Nazwa bazy MySQL |
| `POSTGRES_HOST` | — | Host PostgreSQL (jeśli używasz PostgreSQL) |
| `POSTGRES_PORT` | `5432` | Port PostgreSQL |
| `POSTGRES_DB` | `database` | Nazwa bazy PostgreSQL |
| `DB_CREATE_TABLES` | `false` | `true` = twórz tabele przy starcie |
| `DB_ECHO` | `false` | `true` = loguj SQL do stdout |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Adres brokera Celery |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/0` | Backend wyników Celery |
| `AUTH_SERVICE_URL` | `http://localhost:8000` | Adres auth serwisu |
| `ORG_SERVICE_URL` | `http://localhost:8081` | Adres org serwisu |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | CORS, przecinkami |
| `SCAN_UPLOAD_DIR` | `/tmp/cybercore/uploads` | Folder na uploadowane ZIPy |

### Scan Worker

| Zmienna | Domyślna | Opis |
|---------|---------|------|
| `DB_CONNECTOR` | `sqlite` | Jak wyżej |
| `AUTH_USERNAME` | — | Jak wyżej |
| `AUTH_PASSWORD` | — | Jak wyżej |
| `MYSQL_HOST` | — | Jak wyżej |
| `MYSQL_PORT` | `3306` | Jak wyżej |
| `MYSQL_DB` | `database` | Jak wyżej |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Jak wyżej |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/0` | Jak wyżej |
| `SCAN_WORKSPACE_DIR` | `/tmp/cybercore/scans` | Tymczasowy katalog na klony/wypakowane ZIPy |
| `SCAN_UPLOAD_DIR` | `/tmp/cybercore/uploads` | Musi być taki sam jak w scan serwisie |

---

## API — szybki przegląd

Wszystkie endpointy wymagają aktywnej sesji (cookie `access_token`) oraz odpowiednich uprawnień w organizacji.

```
POST   /api/v1/organizations/{slug}/scans/git          # skan repo (scans.run)
POST   /api/v1/organizations/{slug}/scans/upload       # skan ZIPa (scans.run)
GET    /api/v1/organizations/{slug}/scans              # lista skanów (scans.view)
GET    /api/v1/organizations/{slug}/scans/{job_id}     # status + podsumowanie (scans.view)
GET    /api/v1/organizations/{slug}/scans/{job_id}/findings   # wyniki, filtrowane (scans.view)
POST   /api/v1/organizations/{slug}/scans/{job_id}/cancel     # anuluj (scans.manage)
DELETE /api/v1/organizations/{slug}/scans/{job_id}            # usuń (scans.manage)
```

### Przykład — skan repo przez curl

```bash
curl -X POST http://localhost:8085/api/v1/organizations/my-org/scans/git \
  -H "Content-Type: application/json" \
  -b "access_token=<twój_token>" \
  -d '{"name": "Test scan", "target_url": "https://github.com/user/repo"}'
```

Odpowiedź zwraca `job_id` — polluj status:

```bash
curl http://localhost:8085/api/v1/organizations/my-org/scans/<job_id> \
  -b "access_token=<twój_token>"
```

Gdy `status = "completed"` — pobierz wyniki:

```bash
curl "http://localhost:8085/api/v1/organizations/my-org/scans/<job_id>/findings?severity=high" \
  -b "access_token=<twój_token>"
```

---

## Statusy zadania skanowania

| Status | Opis |
|--------|------|
| `queued` | Zadanie w kolejce Redis, czeka na workera |
| `running` | Worker pobrał zadanie i aktywnie skanuje |
| `completed` | Skan zakończony, wyniki zapisane w bazie |
| `failed` | Worker napotkał nieodwracalny błąd |
| `cancelled` | Anulowane przez użytkownika |

---

## Docker

Oba kontenery wymagają dostępu do tej samej sieci Docker co MySQL i Redis.

```bash
# Scan Service
docker build -t cybercore-scan-service ./services/scan-service
docker run -d --name scan-service \
  -p 8085:8085 \
  -e DB_CONNECTOR=mysql \
  -e AUTH_USERNAME=cybercore \
  -e AUTH_PASSWORD=secret \
  -e MYSQL_HOST=mysql \
  -e MYSQL_DB=cybercore \
  -e CELERY_BROKER_URL=redis://redis:6379/0 \
  -e CELERY_RESULT_BACKEND=redis://redis:6379/0 \
  -e AUTH_SERVICE_URL=http://auth-service:8000 \
  -e ORG_SERVICE_URL=http://org-service:8081 \
  cybercore-scan-service

# Scan Worker
docker build -t cybercore-scan-worker ./workers/scan-worker
docker run -d --name scan-worker \
  -e DB_CONNECTOR=mysql \
  -e AUTH_USERNAME=cybercore \
  -e AUTH_PASSWORD=secret \
  -e MYSQL_HOST=mysql \
  -e MYSQL_DB=cybercore \
  -e CELERY_BROKER_URL=redis://redis:6379/0 \
  -e CELERY_RESULT_BACKEND=redis://redis:6379/0 \
  cybercore-scan-worker
```
