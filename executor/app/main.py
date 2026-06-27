from fastapi import FastAPI

# entry point for the executor service
app = FastAPI(title="Task Executor")


# just a pulse check — confirms the service is up and reachable
@app.get("/health")
def health():
    return {"status": "ok"}
