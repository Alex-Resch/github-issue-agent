import httpx
import logging

from httpx import Response

from src.shared.config import settings
from src.shared.models import Repository


logger = logging.getLogger(__name__)

BASE_GITHUB_URL = "https://api.github.com"


async def fetch_repo_info(repo_full_name: str) -> Repository | None:
    """Fetch repository metadata from GitHub API."""
    response = await fetch(url=f"/repos/{repo_full_name}", params=None)

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


async def fetch(url: str, params: dict | None) -> Response:
    """Send an authenticated GET request to the GitHub API."""
    async with httpx.AsyncClient() as client:
        return await client.get(
            BASE_GITHUB_URL + url,
            headers={
                "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
                "Accept": "application/vnd.github+json",
            },
            params=params,
        )
