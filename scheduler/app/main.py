from fastapi import FastAPI

# entry point for the scheduler service
app = FastAPI(title="Task Scheduler")


# just a pulse check — confirms the service is up and reachable
@app.get("/health")
def health():
    return {"status": "ok"}