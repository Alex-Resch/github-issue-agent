import hashlib
import hmac
import json
import logging

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from config import settings
from models import GitHubIssueEvent
from claude_service import evaluate_issue_opened
from email_service import send_evaluation_email

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="GitHub Issue Agent", version="1.0.0")


def verify_github_signature(payload: bytes, signature: str) -> bool:
    """Verify the HMAC-SHA256 signature from GitHub."""
    if not settings.GITHUB_WEBHOOK_SECRET:
        return True
    expected = (
        "sha256="
        + hmac.new(
            settings.GITHUB_WEBHOOK_SECRET.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
    )
    return hmac.compare_digest(expected, signature)


def is_feature_request(event: GitHubIssueEvent) -> bool:
    """
    Determine whether an issue is a feature request.
    Checks labels first, then falls back to title keyword matching.
    """
    feature_labels = {
        "feature",
        "feature request",
        "feature-request",
        "enhancement",
        "type: feature",
    }
    issue_labels = {label.name.lower() for label in event.issue.labels}

    if issue_labels & feature_labels:
        return True

    feature_keywords = [
        "feature request",
        "feature:",
        "[feature]",
        "add support",
        "would be great if",
    ]
    return any(kw in event.issue.title.lower() for kw in feature_keywords)


def skipped(reason: str) -> JSONResponse:
    """Return a standardised skipped response."""
    return JSONResponse({"skipped": True, "reason": reason})


async def is_maintainer(event: GitHubIssueEvent) -> bool:
    """Determine whether the issue was opened by a maintainer or owner."""
    repo = event.repository.full_name
    username = event.issue.user.login

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.github.com/repos/{repo}/collaborators/{username}/permission",
            headers={
                "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
                "Accept": "application/vnd.github+json",
            },
        )

    if response.status_code != 200:
        return False

    permission = response.json().get("role_name", "")
    return permission in {"admin", "maintain", "owner"}


async def validate(
    payload: bytes,
    event: GitHubIssueEvent,
    x_hub_signature_256: str = Header(None),
    x_github_event: str = Header(None),
):
    """
    Validate and filter an incoming GitHub webhook request.

    Performs the following checks in order:
    1. Verifies the HMAC-SHA256 signature if a webhook secret is configured.
    2. Ensures the event type is 'issues'.
    3. Ensures the action is 'opened'.
    4. Ensures the issue is a feature request (by label or title keyword).
    5. Ensures the issue was opened by a maintainer.

    Returns True if all checks pass, or a skipped JSONResponse if the
    request should be ignored, or raises an HTTPException on auth failure.
    """
    if settings.GITHUB_WEBHOOK_SECRET:
        if not x_hub_signature_256:
            raise HTTPException(status_code=401, detail="Missing signature header")
        if not verify_github_signature(payload, x_hub_signature_256):
            raise HTTPException(status_code=401, detail="Invalid signature")

    if x_github_event != "issues":
        return skipped(f"Event '{x_github_event}' is not relevant")

    if event.action != "opened":
        return skipped(f"Action '{event.action}' is not 'opened'")

    if not is_feature_request(event):
        logger.info(f"Skipping issue #{event.issue.number} — not a feature request")
        return skipped("Not a feature request")

    if not await is_maintainer(event):
        return skipped("Not a maintainer")
    return True


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/webhook/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: str = Header(None),
    x_github_event: str = Header(None),
):
    """Receive and process GitHub issue webhook events."""
    payload = await request.body()
    event = GitHubIssueEvent(**json.loads(payload))

    result = await validate(payload, event, x_hub_signature_256, x_github_event)
    if result is not True:
        return result

    logger.info(f"Evaluating issue #{event.issue.number}: {event.issue.title}")

    evaluation = await evaluate_issue_opened(event)
    await send_evaluation_email(event, evaluation)

    logger.info(f"Evaluation complete. Score: {evaluation.score}/100")
    return JSONResponse({"success": True, "score": evaluation.score})
