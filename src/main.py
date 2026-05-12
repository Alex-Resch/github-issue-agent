import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from config import settings
from poller import poll_all_repos

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def poll_loop() -> None:
    """Continuously poll repos at the configured interval."""
    while True:
        try:
            await poll_all_repos()
        except Exception as e:
            logger.error(f"Poll failed: {e}")
        await asyncio.sleep(settings.POLL_INTERVAL_MINUTES * 60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(poll_loop())
    logger.info(f"Polling started — interval: {settings.POLL_INTERVAL_MINUTES} minutes")
    yield
    task.cancel()


app = FastAPI(title="GitHub Issue Agent", version="2.0.0", lifespan=lifespan)


@app.get("/health")
async def health():
    return JSONResponse({"status": "ok", "repos": settings.REPOS})
