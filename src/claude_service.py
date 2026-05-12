import logging
import instructor
import anthropic

from config import settings
from models import IssueEvaluation, Issue, Repository

logger = logging.getLogger(__name__)
client = instructor.from_anthropic(
    anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
)

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1024

SYSTEM_PROMPT = """You are a senior open-source developer who evaluates GitHub feature request issues
to decide whether it's worth opening a Pull Request or investigating further.

Every issue you evaluate was opened by a maintainer of the repository. Carefully evaluate
whether they want external contributors to implement this, or whether their message implies
they or someone specific will do it themselves. If there is any indication they plan to
implement it themselves or have someone specific in mind, give this issue a score of 0.

Also give a score of 0 if the maintainer signals this is not an immediate priority —
for example if they want to discuss it further, it's planned for a future milestone,
or the timing is unclear.
"""


def build_user_prompt(repo: Repository, issue: Issue) -> str:
    return f"""Evaluate this GitHub feature request:

**Repository:** {repo.full_name}
**Description:** {repo.description or "No description"}
**Language:** {repo.language or "Unknown"}
**Stars:** {repo.stargazers_count:,}
**Open Issues:** {repo.open_issues_count:,}

**Issue #{issue.number}: {issue.title}**
**Author:** {issue.user.login}
**Labels:** {", ".join(label.name for label in issue.labels) or "None"}
**Body:** {issue.body or "(no description provided)"}
"""


async def evaluate_issue_opened(repo: Repository, issue: Issue) -> IssueEvaluation:
    return await client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_user_prompt(repo, issue)}],
        response_model=IssueEvaluation,
    )
