import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from src.poll.issues import poll_all_repos
from src.shared.config import settings
from src.poll.comments import poll_all_comments_repos


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def poll_loop() -> None:  # pragma: no cover
    """Continuously poll repos at the configured interval."""
    while True:
        try:
            await poll_all_repos()
        except Exception as e:
            logger.error(f"Poll failed: {e}")
        await asyncio.sleep(settings.POLL_INTERVAL_MINUTES * 60)


async def comments_poll_loop() -> None:  # pragma: no cover
    """Continuously poll comments at the configured interval."""
    while True:
        try:
            await poll_all_comments_repos()
        except Exception as e:
            logger.error(f"Poll failed: {e}")
        await asyncio.sleep(settings.POLL_INTERVAL_MINUTES * 60)


@asynccontextmanager
async def lifespan(app: FastAPI):  # pragma: no cover
    task1 = asyncio.create_task(poll_loop())
    task2 = asyncio.create_task(comments_poll_loop())
    logger.info(f"Polling started — interval: {settings.POLL_INTERVAL_MINUTES} minutes")
    yield
    task1.cancel()
    task2.cancel()


app = FastAPI(title="GitHub Issue Agent", version="1.1.0", lifespan=lifespan)


@app.get("/health")
async def health():
    return JSONResponse({"status": "ok", "repos": settings.REPOS})
