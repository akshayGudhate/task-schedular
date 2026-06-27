.PHONY: install dev dev-scheduler dev-executor start start-scheduler start-executor stop

install:
	pip3 install -r scheduler/requirements.txt
	pip3 install -r executor/requirements.txt

dev-scheduler:
	-lsof -ti :8080 | xargs kill -9 2>/dev/null || true
	@sleep 0.5
	python3 -m uvicorn app.main:app --app-dir scheduler --port 8080 --reload

dev-executor:
	-lsof -ti :8090 | xargs kill -9 2>/dev/null || true
	@sleep 0.5
	python3 -m uvicorn app.main:app --app-dir executor --port 8090 --reload

dev:
	-lsof -ti :8080 | xargs kill -9 2>/dev/null || true
	-lsof -ti :8090 | xargs kill -9 2>/dev/null || true
	@sleep 0.5
	python3 -m uvicorn app.main:app --app-dir scheduler --port 8080 --reload & \
	python3 -m uvicorn app.main:app --app-dir executor --port 8090 --reload & \
	wait

start-scheduler:
	-lsof -ti :8080 | xargs kill -9 2>/dev/null || true
	@sleep 0.5
	python3 -m uvicorn app.main:app --app-dir scheduler --port 8080

start-executor:
	-lsof -ti :8090 | xargs kill -9 2>/dev/null || true
	@sleep 0.5
	python3 -m uvicorn app.main:app --app-dir executor --port 8090

start:
	-lsof -ti :8080 | xargs kill -9 2>/dev/null || true
	-lsof -ti :8090 | xargs kill -9 2>/dev/null || true
	@sleep 0.5
	python3 -m uvicorn app.main:app --app-dir scheduler --port 8080 & \
	python3 -m uvicorn app.main:app --app-dir executor --port 8090 & \
	wait

stop:
	-lsof -ti :8080 | xargs kill -9 2>/dev/null || true
	-lsof -ti :8090 | xargs kill -9 2>/dev/null || true
