# load .env if it exists, fall back to defaults if not
-include .env
export

SCHEDULER_PORT ?= 8080
EXECUTOR_PORT ?= 8090

.PHONY: install dev dev-scheduler dev-executor start start-scheduler start-executor stop db db-stop db-logs docker-up docker-down docker-build docker-logs migrate migrate-scheduler migrate-executor migrate-down migrate-status

# ─── Local Dev ─── #

install:
	pip3 install -r scheduler/requirements.txt
	pip3 install -r executor/requirements.txt

dev-scheduler:
	-lsof -ti :$(SCHEDULER_PORT) | xargs kill -9 2>/dev/null || true
	@sleep 0.5
	cd scheduler && python3 run.py

dev-executor:
	-lsof -ti :$(EXECUTOR_PORT) | xargs kill -9 2>/dev/null || true
	@sleep 0.5
	cd executor && python3 run.py

dev:
	-lsof -ti :$(SCHEDULER_PORT) | xargs kill -9 2>/dev/null || true
	-lsof -ti :$(EXECUTOR_PORT) | xargs kill -9 2>/dev/null || true
	@sleep 0.5
	cd scheduler && python3 run.py & \
	cd executor && python3 run.py & \
	wait

stop:
	-lsof -ti :$(SCHEDULER_PORT) | xargs kill -9 2>/dev/null || true
	-lsof -ti :$(EXECUTOR_PORT) | xargs kill -9 2>/dev/null || true

# ─── Database Only ─── #

db:
	docker compose up -d scheduler-db executor-db

db-stop:
	docker compose down

db-logs:
	docker compose logs -f scheduler-db executor-db

# ─── Migrations ─── #

migrate:
	docker compose run --rm scheduler-migrate
	docker compose run --rm executor-migrate

migrate-scheduler:
	docker compose run --rm scheduler-migrate

migrate-executor:
	docker compose run --rm executor-migrate

migrate-down:
	docker compose run --rm scheduler-migrate down
	docker compose run --rm executor-migrate down

migrate-status:
	docker compose run --rm scheduler-migrate status
	docker compose run --rm executor-migrate status

# ─── Full Docker ─── #

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down -v

docker-logs:
	docker compose logs -f scheduler executor
