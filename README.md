# Task Automation & Scheduling System

A microservice backend for scheduling tasks, triggering webhooks, and handling async execution with retries.

---

## Services

| Service | Port | Description |
|---|---|---|
| Scheduler | `8080` | Accepts tasks via API, fires webhooks at scheduled time, handles retries |
| Executor | `8090` | Receives webhooks, processes them sync or async, records outcomes |
| Scheduler DB | `5432` | PostgreSQL — tasks and attempt history |
| Executor DB | `5433` | PostgreSQL — webhook execution records |
| scheduler-migrate | — | Runs Goose migrations on scheduler DB at startup |
| executor-migrate | — | Runs Goose migrations on executor DB at startup |

---

## Prerequisites

- Docker Desktop v29+
- Python 3.11+
- `make`

---

## Quick Start

### 1. Clone the repo
```bash
git clone git@github.com:akshayGudhate/fortinet.git
cd fortinet
```

### 2. Set up environment
```bash
cp .env.example .env
# fill in your DB credentials — never commit .env
```

### 3. Run

**Option A — Full Docker (recommended)**
```bash
make docker-build
make docker-up        # DBs → migrations → services, in order
```

**Option B — Local dev (Python local, DB in Docker)**
```bash
make db               # start databases in Docker
make migrate          # run migrations
make install          # install Python deps
make dev              # start both services with hot reload
```

---

## Verify

```bash
docker ps
```

```
scheduler         0.0.0.0:8080   Up
executor          0.0.0.0:8090   Up
scheduler-db      0.0.0.0:5432   Up (healthy)
executor-db       0.0.0.0:5433   Up (healthy)
scheduler-migrate —              Exited (0)
executor-migrate  —              Exited (0)
```

```bash
curl http://localhost:8080/health
curl http://localhost:8090/health
```

---

## API Endpoints

### Scheduler — `http://localhost:8080`

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness check |
| `POST` | `/tasks` | Create a scheduled task |
| `GET` | `/tasks` | List tasks (filter by status, paginate) |
| `GET` | `/tasks/{task_id}` | Get task + full attempt history |
| `PATCH` | `/tasks/{task_id}/cancel` | Cancel a task (CREATED or PENDING only) |

### Executor — `http://localhost:8090`

| Method | Path | Mode | Description |
|---|---|---|---|
| `GET` | `/health` | — | Liveness check |
| `POST` | `/send-welcome` | Sync 200 | Send welcome email |
| `POST` | `/security-alert` | Sync 200 | Dispatch security alert |
| `POST` | `/notify-admin` | Async 202 | Notify admin on new signup |
| `POST` | `/daily-report` | Async 202 | Trigger daily summary report |
| `GET` | `/status/{execution_id}` | — | Poll async execution status |

**Async flow:** `POST /notify-admin` or `POST /daily-report` returns `202` with a `check_url`.
Poll `GET /status/{execution_id}` until `status` is `COMPLETED` or `FAILED`.

---

## Task Lifecycle

```
POST /tasks
    │
    ▼
CREATED ──────────────────────────────────────────► CANCELLED
    │  (scheduled via APScheduler DateTrigger)
    ▼
RUNNING
    │
    ├── 2xx (sync)  ──────────────────────────────► SUCCESS
    │
    ├── 202 (async) → poll check_url every POLL_INTERVAL_SECONDS
    │       ├── COMPLETED ────────────────────────► SUCCESS
    │       └── FAILED    ──► RETRYING (if retries remain) or FAILED
    │
    └── non-2xx / timeout
            ├── retries remain → RETRYING ──► RUNNING (exponential backoff: 60s, 120s, 240s…)
            └── retries exhausted ────────────────► FAILED
```

Every attempt (including retries) is recorded with `http_status`, `duration_ms`, and `response_body`.
Retrieve them via `GET /tasks/{task_id}` (the `attempts` array).

---

## Commands

### Local Dev
```bash
make install          # install Python deps for both services
make dev              # run both with hot reload
make dev-scheduler    # scheduler only → :8080
make dev-executor     # executor only  → :8090
make stop             # kill both services
```

### Database Only
```bash
make db               # start both postgres containers
make db-stop          # stop containers (data preserved)
make db-logs          # tail database logs
```

### Migrations
```bash
make migrate              # run pending migrations on both DBs
make migrate-scheduler    # scheduler DB only
make migrate-executor     # executor DB only
make migrate-down         # roll back last migration on both DBs
make migrate-status       # show applied / pending migrations
```

### Full Docker
```bash
make docker-build     # build images
make docker-up        # start all containers (runs migrations automatically)
make docker-logs      # tail service logs
make docker-down      # stop everything + wipe volumes
```

---

## API Docs

FastAPI serves interactive docs automatically once services are running.

| Service | Swagger UI | ReDoc | OpenAPI JSON |
|---|---|---|---|
| Scheduler | http://localhost:8080/docs | http://localhost:8080/redoc | http://localhost:8080/openapi.json |
| Executor | http://localhost:8090/docs | http://localhost:8090/redoc | http://localhost:8090/openapi.json |

---

## Database Access

**Terminal:**
```bash
docker exec -it scheduler-db psql -U $SCHEDULER_DB_USER -d $SCHEDULER_DB_NAME
docker exec -it executor-db  psql -U $EXECUTOR_DB_USER  -d $EXECUTOR_DB_NAME
```

**GUI (TablePlus / DBeaver / pgAdmin):**

| | Scheduler DB | Executor DB |
|---|---|---|
| Host | `localhost` | `localhost` |
| Port | `5432` | `5433` |
| User | `SCHEDULER_DB_USER` | `EXECUTOR_DB_USER` |
| Password | `SCHEDULER_DB_PASSWORD` | `EXECUTOR_DB_PASSWORD` |
| Database | `SCHEDULER_DB_NAME` | `EXECUTOR_DB_NAME` |

---

## Environment Variables

Copy `.env.example` to `.env`. Never commit `.env`.

### Scheduler

| Variable | Required | Default | Description |
|---|---|---|---|
| `SCHEDULER_DB_URL` | Yes | — | Full postgres connection string |
| `SCHEDULER_DB_USER` | Yes | — | Postgres user |
| `SCHEDULER_DB_PASSWORD` | Yes | — | Postgres password |
| `SCHEDULER_DB_NAME` | Yes | — | Database name |
| `EXECUTOR_BASE_URL` | Yes | — | Base URL of the executor service |
| `SCHEDULER_HOST` | No | `0.0.0.0` | Bind host |
| `SCHEDULER_PORT` | No | `8080` | Service port |
| `DEBUG` | No | `false` | Pretty logs + debug level |
| `CORS_ALLOW_ORIGINS` | No | `*` | Comma-separated allowed origins |
| `DB_POOL_MIN_SIZE` | No | `2` | Min DB connections |
| `DB_POOL_MAX_SIZE` | No | `10` | Max DB connections |
| `RETRY_BASE_DELAY_SECONDS` | No | `60` | First retry delay — doubles each time |
| `POLL_INTERVAL_SECONDS` | No | `5` | How often to poll async (202) webhooks |
| `POLL_MAX_ATTEMPTS` | No | `60` | Max poll attempts before giving up |
| `WEBHOOK_TIMEOUT_SECONDS` | No | `30` | HTTP timeout for outbound webhooks |
| `MISFIRE_GRACE_TIME_SECONDS` | No | `300` | How late a scheduled job can still fire |

### Executor

| Variable | Required | Default | Description |
|---|---|---|---|
| `EXECUTOR_DB_URL` | Yes | — | Full postgres connection string |
| `EXECUTOR_DB_USER` | Yes | — | Postgres user |
| `EXECUTOR_DB_PASSWORD` | Yes | — | Postgres password |
| `EXECUTOR_DB_NAME` | Yes | — | Database name |
| `EXECUTOR_HOST` | No | `0.0.0.0` | Bind host |
| `EXECUTOR_PORT` | No | `8090` | Service port |
| `DEBUG` | No | `false` | Pretty logs + debug level |
| `CORS_ALLOW_ORIGINS` | No | `*` | Comma-separated allowed origins |
| `DB_POOL_MIN_SIZE` | No | `2` | Min DB connections |
| `DB_POOL_MAX_SIZE` | No | `10` | Max DB connections |
| `EXECUTION_TIMEOUT_SECONDS` | No | `300` | Max time to wait for a task to complete |

---

## Project Structure

```
fortinet/
├── docker-compose.yml
├── Makefile
├── .env.example
├── CLAUDE.md
├── docs/
│   ├── project-plan.md
│   ├── project-graph.md
│   ├── rules.md
│   └── agents.md
├── scheduler/
│   ├── Dockerfile
│   ├── Dockerfile.migrate
│   ├── requirements.txt
│   ├── run.py
│   ├── migrations/
│   │   ├── 00001_create_enums.sql
│   │   ├── 00002_create_tasks.sql
│   │   └── 00003_create_task_attempts.sql
│   └── app/
│       ├── main.py               # app wiring — lifespan, middleware, router
│       ├── state_machine.py      # task status transition guard
│       ├── api/
│       │   ├── routes.py         # top-level router — includes tasks + health
│       │   └── tasks.py          # POST/GET /tasks, GET /tasks/{id}, PATCH /tasks/{id}/cancel
│       ├── core/
│       │   ├── config.py         # pydantic-settings — raises on startup if required vars missing
│       │   ├── errors.py         # exception hierarchy + FastAPI error handlers
│       │   └── logging.py        # structlog JSON setup
│       ├── db/
│       │   └── database.py       # asyncpg singleton pool — get_pool / create_pool / close_pool
│       ├── middleware/
│       │   ├── request_id.py     # injects X-Request-ID, binds to structlog context
│       │   ├── security.py       # secure HTTP response headers
│       │   └── setup.py          # registers all middleware on the app
│       ├── models/
│       │   └── task.py           # enums (TaskStatus, RecurrenceType, AttemptStatus) + request/response models
│       └── services/
│           ├── scheduler_service.py  # APScheduler singleton — schedule_task / cancel_job / reload on startup
│           ├── webhook_service.py    # fire_webhook(), poll_execution() — httpx dispatch, 202 polling, retry logic, attempt recording
│           └── task_service.py       # all DB ops: tasks CRUD + attempt lifecycle
└── executor/
    ├── Dockerfile
    ├── Dockerfile.migrate
    ├── requirements.txt
    ├── run.py
    ├── migrations/
    │   ├── 00001_create_enums.sql
    │   └── 00002_create_executions.sql
    └── app/
        ├── main.py
        ├── api/
        │   ├── routes.py         # top-level router — includes webhooks, status, health
        │   ├── webhooks.py       # POST /send-welcome, /security-alert, /notify-admin, /daily-report
        │   └── status.py         # GET /status/{execution_id}
        ├── core/
        │   ├── config.py
        │   ├── errors.py
        │   └── logging.py
        ├── db/
        │   └── database.py       # asyncpg singleton pool
        ├── middleware/
        │   ├── request_id.py
        │   ├── security.py
        │   └── setup.py
        ├── models/
        │   └── execution.py      # ExecutionStatus enum + request/response models
        └── services/
            └── execution_service.py
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| Framework | FastAPI 0.128 |
| Config | pydantic-settings 2.x |
| Database | PostgreSQL 16 |
| DB Driver | asyncpg 0.29 |
| Migrations | Goose (pressly/goose) |
| Logging | structlog 24.4 |
| Security | secure 0.3 |
| Containers | Docker + docker compose v2 |
