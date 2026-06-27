# Task Automation & Scheduling System

A microservice backend for scheduling tasks, triggering webhooks, and handling async execution with retries.

---

## Services

| Service | Port | Description |
|---|---|---|
| Scheduler | `8080` | Accepts tasks, fires webhooks at scheduled time, handles retries |
| Executor | `8090` | Receives webhooks, processes them sync or async |
| Scheduler DB | `5432` | PostgreSQL — stores tasks and attempt history |
| Executor DB | `5433` | PostgreSQL — stores webhook execution records |

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
make docker-up
```

**Option B — Local dev (Python local, DB in Docker)**
```bash
make db       # start databases in Docker
make install  # install Python deps
make dev      # start both services with hot reload
```

---

## Verify

```bash
docker ps
```

```
scheduler     0.0.0.0:8080   Up
executor      0.0.0.0:8090   Up
scheduler-db  0.0.0.0:5432   Up (healthy)
executor-db   0.0.0.0:5433   Up (healthy)
```

```bash
curl http://localhost:8080/health
curl http://localhost:8090/health
```

---

## Commands

### # ─── Local Dev ─── #
```bash
make install          # install Python deps for both services
make dev              # run both with hot reload
make dev-scheduler    # scheduler only → :8080
make dev-executor     # executor only  → :8090
make stop             # kill both services
```

### # ─── Database Only ─── #
```bash
make db               # start both postgres containers
make db-stop          # stop containers (data preserved)
make db-logs          # tail database logs
```

### # ─── Full Docker ─── #
```bash
make docker-build     # build images
make docker-up        # start all 4 containers
make docker-logs      # tail service logs
make docker-down      # stop everything + wipe volumes
```

---

## API Docs

Swagger UI — auto-generated, available once services are running:

| Service | URL |
|---|---|
| Scheduler | http://localhost:8080/docs |
| Executor | http://localhost:8090/docs |

Postman collection also available — `Fortinet.postman_collection.json`

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
│   ├── requirements.txt
│   ├── run.py                        # validates env + starts uvicorn
│   └── app/
│       ├── main.py                   # app wiring — lifespan, middleware, router
│       ├── state_machine.py          # task status transition guard
│       ├── api/
│       │   └── routes.py             # all HTTP routes
│       ├── core/
│       │   ├── config.py             # pydantic settings
│       │   ├── errors.py             # exception hierarchy + handlers
│       │   └── logging.py            # structlog setup
│       ├── db/
│       │   └── database.py           # asyncpg connection pool
│       ├── middleware/
│       │   ├── request_id.py         # X-Request-ID + structured logging per request
│       │   ├── security.py           # secure response headers
│       │   └── setup.py              # registers all middleware on the app
│       └── models/
│           ├── task.py               # Task + TaskStatus + RecurrenceType
│           └── task_attempt.py       # TaskAttempt + AttemptStatus
└── executor/
    ├── Dockerfile
    ├── requirements.txt
    ├── run.py
    └── app/
        ├── main.py
        ├── api/
        │   └── routes.py
        ├── core/
        │   ├── config.py
        │   ├── errors.py
        │   └── logging.py
        ├── middleware/
        │   ├── request_id.py
        │   ├── security.py
        │   └── setup.py
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| Framework | FastAPI 0.115 |
| Config | pydantic-settings 2.x |
| Database | PostgreSQL 16 |
| DB Driver | asyncpg 0.29 |
| Logging | structlog 24.4 |
| Scheduler | APScheduler 3.x *(coming soon)* |
| HTTP Client | httpx 0.27 *(coming soon)* |
| Containers | Docker + docker compose v2 |
