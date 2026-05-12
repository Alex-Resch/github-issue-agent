import logging
from datetime import datetime, timedelta, timezone

import httpx

from config import settings
from models import Issue, Repository, User, Label
from claude_service import evaluate_issue_opened
from email_service import send_evaluation_email

logger = logging.getLogger(__name__)


def validate(issue: Issue, top_contributors: set[str]) -> bool:
    if not is_feature_request(issue):
        logger.info(f"Skipping #{issue.number} — not a feature request")
        return False

    if issue.user.login.lower() not in top_contributors:
        logger.info(f"Skipping #{issue.number} — not opened by top 5 contributors")
        return False
    return True


def is_feature_request(issue: Issue) -> bool:
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
    issue_labels = {label.name.lower() for label in issue.labels}

    if issue_labels & feature_labels:
        return True

    feature_keywords = [
        "feature request",
        "feature:",
        "[feature]",
        "add support",
        "would be great if",
    ]
    return any(kw in issue.title.lower() for kw in feature_keywords)


async def fetch_top_contributors(repo_full_name: str, top_n: int = 5) -> set[str]:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.github.com/repos/{repo_full_name}/contributors",
            headers={
                "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
                "Accept": "application/vnd.github+json",
            },
            params={"per_page": top_n},
        )
    if response.status_code != 200:
        return set()
    return {c["login"].lower() for c in response.json()}


async def fetch_repo_info(repo_full_name: str) -> Repository | None:
    """Fetch repository metadata from GitHub API."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.github.com/repos/{repo_full_name}",
            headers={
                "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
                "Accept": "application/vnd.github+json",
            },
        )

    if response.status_code != 200:
        logger.error(
            f"Failed to fetch repo info for {repo_full_name}: {response.status_code}"
        )
        return None

    data = response.json()
    return Repository(
        name=data["name"],
        full_name=data["full_name"],
        html_url=data["html_url"],
        description=data.get("description", ""),
        language=data.get("language"),
        stargazers_count=data.get("stargazers_count", 0),
        open_issues_count=data.get("open_issues_count", 0),
    )


async def fetch_new_issues(repo_full_name: str, since: datetime) -> list[Issue]:
    """Fetch issues opened since the given datetime."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.github.com/repos/{repo_full_name}/issues",
            headers={
                "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
                "Accept": "application/vnd.github+json",
            },
            params={
                "state": "open",
                "since": since.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "sort": "created",
                "direction": "desc",
                "per_page": 50,
            },
        )

    if response.status_code != 200:
        logger.error(
            f"Failed to fetch issues for {repo_full_name}: {response.status_code}"
        )
        return []

    issues = []
    for issue in response.json():
        issues.append(
            Issue(
                number=issue["number"],
                title=issue["title"],
                body=issue.get("body", ""),
                html_url=issue["html_url"],
                user=User(
                    login=issue["user"]["login"], html_url=issue["user"]["html_url"]
                ),
                labels=[
                    Label(name=label["name"], color=label.get("color"))
                    for label in issue.get("labels", [])
                ],
                state=issue["state"],
                created_at=issue["created_at"],
            )
        )
    return issues


async def poll_all_repos() -> None:
    """Poll all configured repos for new feature request issues."""
    since = datetime.now(timezone.utc) - timedelta(
        minutes=settings.POLL_INTERVAL_MINUTES + 1
    )

    for repo_full_name in settings.REPOS:
        logger.info(f"Polling {repo_full_name}...")

        repo = await fetch_repo_info(repo_full_name)
        if not repo:
            continue

        top_contributors = await fetch_top_contributors(repo_full_name)

        issues = await fetch_new_issues(repo_full_name, since)
        logger.info(f"Found {len(issues)} new issue(s) in {repo_full_name}")

        for issue in issues:
            is_valid = validate(issue, top_contributors)
            if not is_valid:
                continue
            logger.info(f"Evaluating #{issue.number}: {issue.title}")

            evaluation = await evaluate_issue_opened(repo, issue)
            await send_evaluation_email(repo, issue, evaluation)
            logger.info(f"Done. Score: {evaluation.score}/100")
