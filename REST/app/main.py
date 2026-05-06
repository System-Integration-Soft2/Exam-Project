from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.utils.config import Settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.settings = Settings()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/healthz")
def healthz():
    """Liveness probe."""
    return {"status": "ok"}
