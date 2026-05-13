from typing import List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Poll Models
# ---------------------------------------------------------------------------


class Comment(BaseModel):
    commenter: str
    issue_number: int
    body: str


class Label(BaseModel):
    name: str
    color: Optional[str] = None


class User(BaseModel):
    login: str
    html_url: str


class Issue(BaseModel):
    number: int
    title: str
    body: Optional[str] = ""
    html_url: str
    user: User
    labels: List[Label] = []
    state: str
    created_at: str


class Repository(BaseModel):
    name: str
    full_name: str
    html_url: str
    description: Optional[str] = ""
    language: Optional[str] = None
    stargazers_count: int = 0
    open_issues_count: int = 0


# ---------------------------------------------------------------------------
# Claude Evaluation Model
# ---------------------------------------------------------------------------


class IssueEvaluation(BaseModel):
    score: int = Field(
        description="Overall value of contributing to this issue. "
        "80–100: Highly impactful, "
        "well-scoped. 60–79: Interesting but requires more research. "
        "40–59: Possible but low priority. "
        "0–39: Not worth pursuing."
    )
    difficulty: str = Field(
        description="Implementation difficulty. One of: Low | Medium | High | Very High"
    )
    scope: str = Field(
        description="Size of the change required. One of: Minimal | Small | Medium | Large"
    )
    impression: str = Field(
        description="A single punchy sentence summarising the issue."
    )
    reasoning: str = Field(description="2–4 sentences explaining the score.")
