import httpx
import logging

from src.shared.config import settings
from src.shared.models import Repository


logger = logging.getLogger(__name__)


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
