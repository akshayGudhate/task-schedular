# Task Automation & Scheduling System

A microservice backend for scheduling tasks, triggering webhooks, and handling async execution with retries.

---

## Services

| Service | Port | Description |
|---|---|---|
| Scheduler | `8080` | Accepts tasks, fires webhooks at scheduled time, handles retries |
| Executor | `8090` | Receives webhooks, processes them sync or async |

---

## Quick Start

### 1. Clone and enter the project
```bash
git clone git@github.com:akshayGudhate/fortinet.git
cd fortinet
```

### 2. Set up environment
```bash
cp .env.example .env
# edit .env with your DB credentials if needed
```

### 3. Install dependencies
```bash
make install
```

### 4. Run in dev mode (hot reload)
```bash
make dev
```

---

## Commands

### Install
```bash
make install           # install deps for both services
```

### Development (hot reload on file save)
```bash
make dev               # run both services
make dev-scheduler     # scheduler only  → http://localhost:8080
make dev-executor      # executor only   → http://localhost:8090
```

### Production (no reload)
```bash
make start             # run both services
make start-scheduler   # scheduler only
make start-executor    # executor only
```

### Stop
```bash
make stop              # kill both ports (8080 + 8090)
```

---

## API Docs

Once running, Swagger UI is available at:

- Scheduler → http://localhost:8080/docs
- Executor  → http://localhost:8090/docs

---

## Health Check

```bash
curl http://localhost:8080/health   # scheduler
curl http://localhost:8090/health   # executor
```

---

## Project Structure

```
fortinet/
├── Makefile                  # all run commands live here
├── .env.example              # environment variable template
├── scheduler/                # schedular app
│   ├── app/
│   │   └── main.py
│   └── requirements.txt
└── executor/                 # executor app
    ├── app/
    │   └── main.py
    └── requirements.txt
```

---

## Tech Stack

- Python + FastAPI
- PostgreSQL