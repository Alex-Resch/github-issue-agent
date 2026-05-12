import logging

import httpx

from config import settings
from models import GitHubIssueEvent, IssueEvaluation

logger = logging.getLogger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
http_client = httpx.AsyncClient(timeout=30)


def score_badge(score: int) -> str:
    if score >= 80:
        return "🟢 High Priority"
    elif score >= 60:
        return "🟡 Worth Exploring"
    elif score >= 40:
        return "🟠 Low Priority"
    else:
        return "🔴 Skip"


def build_html_email(event: GitHubIssueEvent, ev: IssueEvaluation, badge: str) -> str:
    repo = event.repository
    issue = event.issue

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f6f8fa; margin: 0; padding: 24px; }}
    .card {{ background: #fff; border-radius: 8px; border: 1px solid #e1e4e8; max-width: 640px; margin: 0 auto; overflow: hidden; }}
    .header {{ background: #24292f; color: #fff; padding: 20px 28px; }}
    .header h1 {{ margin: 0 0 4px; font-size: 18px; }}
    .header p {{ margin: 0; opacity: 0.7; font-size: 13px; }}
    .body {{ padding: 24px 28px; }}
    .score-row {{ display: flex; align-items: center; gap: 16px; margin-bottom: 24px; }}
    .score-circle {{ width: 72px; height: 72px; border-radius: 50%; background: #0969da; color: #fff;
                     display: flex; align-items: center; justify-content: center; font-size: 22px; font-weight: 700; flex-shrink: 0; }}
    .score-meta h2 {{ margin: 0 0 4px; font-size: 16px; }}
    .score-meta p {{ margin: 0; color: #57606a; font-size: 14px; }}
    table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
    td {{ padding: 8px 0; border-bottom: 1px solid #f0f0f0; font-size: 14px; vertical-align: top; }}
    td:first-child {{ width: 140px; color: #57606a; font-weight: 500; }}
    .reasoning {{ background: #f6f8fa; border-left: 3px solid #0969da; border-radius: 4px; padding: 12px 16px; font-size: 14px; color: #24292f; line-height: 1.6; margin: 16px 0; }}
    .btn {{ display: inline-block; background: #0969da; color: #fff; padding: 10px 20px; border-radius: 6px;
            text-decoration: none; font-size: 14px; font-weight: 500; margin-top: 20px; }}
    .footer {{ padding: 16px 28px; border-top: 1px solid #e1e4e8; font-size: 12px; color: #8c959f; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <h1>📦 {repo.full_name}</h1>
      <p>New feature request detected by your Issue Agent</p>
    </div>
    <div class="body">
      <div class="score-row">
        <div class="score-circle">{ev.score}</div>
        <div class="score-meta">
          <h2>{badge}</h2>
          <p>{ev.impression}</p>
        </div>
      </div>

      <table>
        <tr><td>Issue</td><td><strong>#{issue.number}</strong> — {issue.title}</td></tr>
        <tr><td>Author</td><td>{issue.user.login}</td></tr>
        <tr><td>Difficulty</td><td>{ev.difficulty}</td></tr>
        <tr><td>Scope</td><td>{ev.scope}</td></tr>
        <tr><td>Labels</td><td>{", ".join(label.name for label in issue.labels) or "None"}</td></tr>
        <tr><td>Stars</td><td>{repo.stargazers_count:,}</td></tr>
        <tr><td>Language</td><td>{repo.language or "Unknown"}</td></tr>
      </table>

      <div class="reasoning">
        <strong>🧠 Reasoning</strong><br/><br/>
        {ev.reasoning}
      </div>

      <a class="btn" href="{issue.html_url}" target="_blank">View Issue on GitHub →</a>
    </div>
    <div class="footer">
      Sent by your GitHub Issue Agent · {repo.html_url}
    </div>
  </div>
</body>
</html>"""


def build_text_email(event: GitHubIssueEvent, ev: IssueEvaluation, badge: str) -> str:
    repo = event.repository
    issue = event.issue
    return f"""GitHub Issue Agent — New Feature Request

Repo:        {repo.full_name}
Issue:       #{issue.number} — {issue.title}
Author:      {issue.user.login}
Link:        {issue.html_url}

SCORE:       {ev.score}/100  {badge}
Difficulty:  {ev.difficulty}
Scope:       {ev.scope}
Impression:  {ev.impression}

Reasoning:
{ev.reasoning}
"""


async def send_evaluation_email(event: GitHubIssueEvent, ev: IssueEvaluation) -> None:
    if ev.score < settings.MIN_SCORE_TO_NOTIFY:
        logger.info(
            f"Score {ev.score} below threshold {settings.MIN_SCORE_TO_NOTIFY} — skipping email"
        )
        return

    badge = score_badge(ev.score)
    repo = event.repository
    issue = event.issue
    subject = (
        f"[{badge}] {repo.name} #{issue.number} — {issue.title} (Score: {ev.score}/100)"
    )

    payload = {
        "sender": {"name": settings.EMAIL_FROM_NAME, "email": settings.EMAIL_FROM},
        "to": [{"email": settings.EMAIL_TO, "name": settings.EMAIL_TO_NAME}],
        "subject": subject,
        "htmlContent": build_html_email(event, ev, badge),
        "textContent": build_text_email(event, ev, badge),
    }

    try:
        response = await http_client.post(
            BREVO_API_URL,
            headers={
                "api-key": settings.BREVO_API_KEY,
                "content-type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        logger.error(f"Brevo API error {e.response.status_code}: {e.response.text}")
        raise

    logger.info(f"Email sent for issue #{issue.number} (score: {ev.score})")
