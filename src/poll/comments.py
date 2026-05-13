import logging
from datetime import datetime, timedelta, timezone
from httpx import Response

from src.claude_service import evaluate_issue_commented
from src.email_service import send_evaluation_email
from src.shared.config import settings
from src.shared.models import Issue, User, Label, Comment
from src.shared.functions import fetch_repo_info, fetch
from src.poll.issues import fetch_top_contributors

logger = logging.getLogger(__name__)


BOTS = {"claude", "copilot", "devin", "cursoragent"}


def validate(
    comment: Comment, top_contributors: set[str], seen_issues: set[int]
) -> bool:
    if comment.commenter not in top_contributors:
        logger.info(f"Skipping comment by {comment.commenter} — not a top contributor")
        return False

    if comment.issue_number in seen_issues:
        return False

    if comment.commenter.endswith("[bot]") or any(
        bot in comment.commenter for bot in BOTS
    ):
        return False
    return True


def convert_to_comments(response: Response) -> list[Comment]:
    comments: list[Comment] = []
    for user_comment in response.json():
        comment = Comment(
            commenter=user_comment["user"]["login"],
            issue_number=int(user_comment["issue_url"].split("/")[-1]),
            body=user_comment["body"],
        )
        comments.append(comment)
    return comments


async def fetch_new_comments(repo_full_name: str, since: datetime) -> list[Comment]:
    """Fetch all new comments on issues since the given datetime."""
    params = {
        "since": since.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sort": "created",
        "direction": "desc",
        "per_page": 50,
    }
    response = await fetch(
        url=f"/repos/{repo_full_name}/issues/comments", params=params
    )

    if response.status_code != 200:
        logger.error(
            f"Failed to fetch comments for {repo_full_name}: {response.status_code}"
        )
        return []

    return convert_to_comments(response)


async def fetch_issue(repo_full_name: str, issue_number: int) -> Issue | None:
    """Fetch a single issue by number."""
    response = await fetch(
        url=f"/repos/{repo_full_name}/issues/{issue_number}", params=None
    )

    if response.status_code != 200:
        logger.error(f"Failed to fetch issue #{issue_number}: {response.status_code}")
        return None

    data = response.json()

    if "pull_request" in data:
        return None

    return Issue(
        number=data["number"],
        title=data["title"],
        body=data.get("body", ""),
        html_url=data["html_url"],
        user=User(login=data["user"]["login"], html_url=data["user"]["html_url"]),
        labels=[
            Label(name=label["name"], color=label.get("color"))
            for label in data.get("labels", [])
        ],
        state=data["state"],
        created_at=data["created_at"],
    )


async def fetch_all_comments(repo_full_name: str, issue_number: int) -> list[Comment]:
    """Fetch all comments on a specific issue."""
    response = await fetch(
        url=f"/repos/{repo_full_name}/issues/{issue_number}/comments",
        params={"per_page": 100},
    )

    if response.status_code != 200:
        return []

    return convert_to_comments(response)


async def poll_all_comments_repos() -> None:
    """Poll all configured repos for new comments on issues."""
    since = datetime.now(timezone.utc) - timedelta(
        minutes=settings.POLL_INTERVAL_MINUTES + 1
    )

    for repo_full_name in settings.REPOS:
        logger.info(f"Polling comments for {repo_full_name}...")

        repo = await fetch_repo_info(repo_full_name)
        if not repo:
            continue

        top_contributors = await fetch_top_contributors(repo_full_name)
        new_comments = await fetch_new_comments(repo_full_name, since)
        logger.info(f"Found {len(new_comments)} new comment(s) in {repo_full_name}")

        seen_issues: set[int] = set()

        for comment in new_comments:
            is_valid = validate(comment, top_contributors, seen_issues)
            if not is_valid:
                continue

            seen_issues.add(comment.issue_number)

            issue = await fetch_issue(repo_full_name, comment.issue_number)
            if not issue:
                continue

            all_comments = await fetch_all_comments(
                repo_full_name, comment.issue_number
            )
            comments_text = "\n\n".join(
                f"**{comment.commenter}:** {comment.body}" for comment in all_comments
            )

            logger.info(
                f"Evaluating issue #{comment.issue_number} based on new comment by {comment.commenter}"
            )

            evaluation = await evaluate_issue_commented(repo, issue, comments_text)
            await send_evaluation_email(repo, issue, evaluation)
            logger.info(f"Done. Score: {evaluation.score}/100")
