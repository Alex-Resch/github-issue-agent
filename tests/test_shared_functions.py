import pytest
import respx
from httpx import Response

from src.shared.functions import fetch, fetch_repo_info

REPO = "pydantic/pydantic-ai"


@pytest.mark.asyncio
async def test_fetch_returns_response():
    with respx.mock:
        respx.get("https://api.github.com/repos/pydantic/pydantic-ai").mock(
            return_value=Response(200, json={"name": "pydantic-ai"})
        )
        response = await fetch(f"/repos/{REPO}", params=None)
        assert response.status_code == 200
        assert response.json()["name"] == "pydantic-ai"


@pytest.mark.asyncio
async def test_fetch_repo_info(sample_repo):
    with respx.mock:
        respx.get(f"https://api.github.com/repos/{REPO}").mock(
            return_value=Response(
                200,
                json={
                    "name": "pydantic-ai",
                    "full_name": REPO,
                    "html_url": f"https://github.com/{REPO}",
                    "description": "AI Agent Framework",
                    "language": "Python",
                    "stargazers_count": 17000,
                    "open_issues_count": 372,
                },
            )
        )
        repo = await fetch_repo_info(REPO)
        assert repo is not None
        assert repo.full_name == REPO
        assert repo.stargazers_count == 17000


@pytest.mark.asyncio
async def test_fetch_repo_info_returns_none_on_error():
    with respx.mock:
        respx.get(f"https://api.github.com/repos/{REPO}").mock(
            return_value=Response(404)
        )
        repo = await fetch_repo_info(REPO)
        assert repo is None
