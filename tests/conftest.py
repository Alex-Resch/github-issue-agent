import pytest
from src.shared.models import Issue, User, Label, Repository, Comment


@pytest.fixture
def sample_user() -> User:
    return User(login="samuelcolvin", html_url="https://github.com/samuelcolvin")


@pytest.fixture
def sample_labels() -> list[Label]:
    return [Label(name="enhancement", color="84b6eb")]


@pytest.fixture
def sample_issue(sample_user, sample_labels) -> Issue:
    return Issue(
        number=42,
        title="feat: add dark mode support",
        body="It would be great if we could add dark mode.",
        html_url="https://github.com/pydantic/pydantic-ai/issues/42",
        user=sample_user,
        labels=sample_labels,
        state="open",
        created_at="2026-05-13T10:00:00Z",
    )


@pytest.fixture
def sample_repo() -> Repository:
    return Repository(
        name="pydantic-ai",
        full_name="pydantic/pydantic-ai",
        html_url="https://github.com/pydantic/pydantic-ai",
        description="AI Agent Framework",
        language="Python",
        stargazers_count=17000,
        open_issues_count=372,
    )


@pytest.fixture
def sample_comment() -> Comment:
    return Comment(
        commenter="samuelcolvin",
        issue_number=42,
        body="Great idea, PRs welcome!",
    )
