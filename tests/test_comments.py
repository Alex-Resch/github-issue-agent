import pytest
import respx
from httpx import Response
from unittest.mock import MagicMock

from src.poll.comments import convert_to_comments
from src.shared.models import Comment
from src.poll.comments import validate, fetch_issue, fetch_all_comments


TOP_CONTRIBUTORS = {"samuelcolvin", "douewm"}
REPO = "pydantic/pydantic-ai"


def make_comment(commenter: str, issue_number: int = 1) -> Comment:
    return Comment(commenter=commenter, issue_number=issue_number, body="PRs welcome!")


def test_valid_comment_from_top_contributor():
    comment = make_comment("samuelcolvin")
    assert validate(comment, TOP_CONTRIBUTORS, set()) is True


def test_skipped_not_top_contributor():
    comment = make_comment("random_user")
    assert validate(comment, TOP_CONTRIBUTORS, set()) is False


def test_skipped_already_seen_issue():
    comment = make_comment("samuelcolvin", issue_number=42)
    assert validate(comment, TOP_CONTRIBUTORS, seen_issues={42}) is False


def test_skipped_bot_with_suffix():
    comment = make_comment("github-actions[bot]")
    assert validate(comment, TOP_CONTRIBUTORS, set()) is False


def test_skipped_known_bot():
    comment = make_comment("cursoragent")
    assert validate(comment, TOP_CONTRIBUTORS | {"cursoragent"}, set()) is False


def test_skipped_partial_bot_name():
    comment = make_comment("github-copilot")
    assert validate(comment, TOP_CONTRIBUTORS | {"github-copilot"}, set()) is False


def make_mock_response(data: list[dict]):
    mock = MagicMock()
    mock.json.return_value = data
    return mock


def test_converts_single_comment():
    response = make_mock_response(
        [
            {
                "user": {"login": "samuelcolvin"},
                "issue_url": "https://api.github.com/repos/pydantic/pydantic-ai/issues/42",
                "body": "PRs welcome!",
            }
        ]
    )
    comments = convert_to_comments(response)
    assert len(comments) == 1
    assert comments[0].commenter == "samuelcolvin"
    assert comments[0].issue_number == 42
    assert comments[0].body == "PRs welcome!"


def test_converts_multiple_comments():
    response = make_mock_response(
        [
            {
                "user": {"login": "samuelcolvin"},
                "issue_url": "https://api.github.com/repos/pydantic/pydantic-ai/issues/42",
                "body": "PRs welcome!",
            },
            {
                "user": {"login": "douewm"},
                "issue_url": "https://api.github.com/repos/pydantic/pydantic-ai/issues/43",
                "body": "Good idea.",
            },
        ]
    )
    comments = convert_to_comments(response)
    assert len(comments) == 2
    assert comments[1].issue_number == 43


def test_empty_response():
    response = make_mock_response([])
    comments = convert_to_comments(response)
    assert comments == []


@pytest.mark.asyncio
async def test_fetch_issue_returns_none_for_pr():
    with respx.mock:
        respx.get(f"https://api.github.com/repos/{REPO}/issues/1").mock(
            return_value=Response(
                200,
                json={
                    "number": 1,
                    "title": "fix: some PR",
                    "body": "",
                    "html_url": f"https://github.com/{REPO}/pull/1",
                    "user": {
                        "login": "samuelcolvin",
                        "html_url": "https://github.com/samuelcolvin",
                    },
                    "labels": [],
                    "state": "open",
                    "created_at": "2026-05-13T10:00:00Z",
                    "pull_request": {},
                },
            )
        )
        issue = await fetch_issue(REPO, 1)
        assert issue is None


@pytest.mark.asyncio
async def test_fetch_all_comments_returns_empty_on_error():
    with respx.mock:
        respx.get(f"https://api.github.com/repos/{REPO}/issues/1/comments").mock(
            return_value=Response(500)
        )
        comments = await fetch_all_comments(REPO, 1)
        assert comments == []


@pytest.mark.asyncio
async def test_fetch_new_comments_returns_empty_on_error():
    with respx.mock:
        respx.get(f"https://api.github.com/repos/{REPO}/issues/comments").mock(
            return_value=Response(404)
        )
        from datetime import datetime, timezone, timedelta
        from src.poll.comments import fetch_new_comments

        since = datetime.now(timezone.utc) - timedelta(hours=1)
        comments = await fetch_new_comments(REPO, since)
        assert comments == []


@pytest.mark.asyncio
async def test_fetch_issue_returns_none_on_error():
    with respx.mock:
        respx.get(f"https://api.github.com/repos/{REPO}/issues/1").mock(
            return_value=Response(404)
        )
        issue = await fetch_issue(REPO, 1)
        assert issue is None
