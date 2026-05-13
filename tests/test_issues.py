import respx
from httpx import Response
import pytest

from src.poll.issues import validate
from src.shared.models import Issue, User, Label
from src.poll.issues import is_feature_request, fetch_top_contributors, fetch_new_issues


REPO = "pydantic/pydantic-ai"


@pytest.mark.parametrize(
    "labels",
    [
        ["enhancement"],
        ["feature"],
        ["feature request"],
        ["feature-request"],
        ["type: feature"],
        ["Enhancement"],  # case-insensitive
    ],
)
def test_feature_request_by_label(labels):
    assert is_feature_request(make_issue("Some title", labels=labels)) is True


@pytest.mark.parametrize(
    "title",
    [
        "feature request: add dark mode",
        "feature: add dark mode",
        "[feature] add dark mode",
        "add support for dark mode",
        "would be great if we had dark mode",
        "Feature Request: dark mode",  # case-insensitive
    ],
)
def test_feature_request_by_title(title):
    assert is_feature_request(make_issue(title)) is True


@pytest.mark.parametrize(
    "title,labels",
    [
        ("fix typo in README", []),
        ("", []),
        ("Some title", ["bug"]),
    ],
)
def test_not_feature_request(title, labels):
    assert is_feature_request(make_issue(title, labels=labels)) is False


def make_issue(title: str, login: str = "user", labels=None) -> Issue:
    if labels is None:
        labels = []
    return Issue(
        number=1,
        title=title,
        body="",
        html_url="https://github.com/test/repo/issues/1",
        user=User(login=login, html_url=f"https://github.com/{login}"),
        labels=[Label(name=label) for label in labels],
        state="open",
        created_at="2026-05-13T10:00:00Z",
    )


TOP_CONTRIBUTORS = {"samuelcolvin", "douewm", "dmontagu"}


def test_valid_feature_request_from_top_contributor():
    issue = make_issue("feature: add dark mode", "samuelcolvin", labels=["enhancement"])
    assert validate(issue, TOP_CONTRIBUTORS) is True


def test_skipped_not_feature_request():
    issue = make_issue("fix typo in README", "samuelcolvin")
    assert validate(issue, TOP_CONTRIBUTORS) is False


def test_skipped_not_top_contributor():
    issue = make_issue("feature: add dark mode", "unknown_user", labels=["enhancement"])
    assert validate(issue, TOP_CONTRIBUTORS) is False


def test_login_case_insensitive():
    issue = make_issue("feature: add dark mode", "SamuelColvin", labels=["enhancement"])
    assert validate(issue, TOP_CONTRIBUTORS) is True


@pytest.mark.asyncio
async def test_fetch_top_contributors():
    with respx.mock:
        respx.get(f"https://api.github.com/repos/{REPO}/contributors").mock(
            return_value=Response(
                200,
                json=[
                    {"login": "samuelcolvin"},
                    {"login": "DouweM"},
                ],
            )
        )
        result = await fetch_top_contributors(REPO)
        assert result == {"samuelcolvin", "douwem"}


@pytest.mark.asyncio
async def test_fetch_top_contributors_returns_empty_on_error():
    with respx.mock:
        respx.get(f"https://api.github.com/repos/{REPO}/contributors").mock(
            return_value=Response(403)
        )
        result = await fetch_top_contributors(REPO)
        assert result == set()


@pytest.mark.asyncio
async def test_fetch_new_issues_filters_pull_requests():
    with respx.mock:
        respx.get(f"https://api.github.com/repos/{REPO}/issues").mock(
            return_value=Response(
                200,
                json=[
                    {
                        "number": 1,
                        "title": "feature: add dark mode",
                        "body": "Would be great!",
                        "html_url": f"https://github.com/{REPO}/issues/1",
                        "user": {
                            "login": "samuelcolvin",
                            "html_url": "https://github.com/samuelcolvin",
                        },
                        "labels": [{"name": "enhancement", "color": "blue"}],
                        "state": "open",
                        "created_at": "2026-05-13T10:00:00Z",
                    },
                    {
                        "number": 2,
                        "title": "fix: some PR",
                        "body": "",
                        "html_url": f"https://github.com/{REPO}/pull/2",
                        "user": {
                            "login": "samuelcolvin",
                            "html_url": "https://github.com/samuelcolvin",
                        },
                        "labels": [],
                        "state": "open",
                        "created_at": "2026-05-13T10:00:00Z",
                        "pull_request": {},  # should be filtered
                    },
                ],
            )
        )
        from datetime import datetime, timezone, timedelta

        since = datetime.now(timezone.utc) - timedelta(hours=1)
        issues = await fetch_new_issues(REPO, since)
        assert len(issues) == 1
        assert issues[0].number == 1


@pytest.mark.asyncio
async def test_fetch_new_issues_returns_empty_on_error():
    with respx.mock:
        respx.get(f"https://api.github.com/repos/{REPO}/issues").mock(
            return_value=Response(403)
        )
        from datetime import datetime, timezone, timedelta

        since = datetime.now(timezone.utc) - timedelta(hours=1)
        issues = await fetch_new_issues(REPO, since)
        assert issues == []
