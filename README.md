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

| Variable | Required | Default | Description |
|---|---|---|---|
| `SCHEDULER_DB_URL` | Yes | — | Full postgres connection string |
| `SCHEDULER_DB_USER` | Yes | — | Postgres user |
| `SCHEDULER_DB_PASSWORD` | Yes | — | Postgres password |
| `SCHEDULER_DB_NAME` | Yes | — | Database name |
| `EXECUTOR_DB_URL` | Yes | — | Full postgres connection string |
| `EXECUTOR_DB_USER` | Yes | — | Postgres user |
| `EXECUTOR_DB_PASSWORD` | Yes | — | Postgres password |
| `EXECUTOR_DB_NAME` | Yes | — | Database name |
| `SCHEDULER_HOST` | No | `0.0.0.0` | Bind host |
| `SCHEDULER_PORT` | No | `8080` | Service port |
| `EXECUTOR_HOST` | No | `0.0.0.0` | Bind host |
| `EXECUTOR_PORT` | No | `8090` | Service port |
| `APP_VERSION` | No | `1.0.0` | Version string |

---

## Project Structure

```
fortinet/
├── docker-compose.yml                # all 4 containers
├── Makefile                          # all dev and docker commands
├── .env.example                      # env template — copy to .env
├── .cursorrules                      # Cursor IDE coding rules
├── CLAUDE.md                         # Claude Code instructions
├── Fortinet.postman_collection.json  # Postman collection
├── docs/
│   ├── project-plan.md               # commit-by-commit build plan
│   ├── project-graph.md              # module dependency map
│   ├── rules.md                      # security and coding rules
│   └── agents.md                     # Claude agent definitions
├── scheduler/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── run.py                        # validates env + starts uvicorn
│   └── app/
│       ├── main.py                   # FastAPI app + /health
│       └── core/
│           └── config.py             # pydantic settings + env validation
└── executor/
    ├── Dockerfile
    ├── requirements.txt
    ├── run.py
    └── app/
        ├── main.py
        └── core/
            └── config.py
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| Framework | FastAPI 0.115 |
| Config | pydantic-settings 2.x |
| Database | PostgreSQL 16 |
| ORM | SQLAlchemy 2.0 async *(coming soon)* |
| Scheduler | APScheduler 3.x *(coming soon)* |
| Logging | structlog *(coming soon)* |
| Containers | Docker + docker compose v2 |
