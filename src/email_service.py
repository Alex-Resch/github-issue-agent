import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import settings
from models import IssueEvaluation, Issue, Repository

logger = logging.getLogger(__name__)


def score_badge(score: int) -> str:
    if score >= 80:
        return "🟢 High Priority"
    elif score >= 60:
        return "🟡 Worth Exploring"
    elif score >= 40:
        return "🟠 Low Priority"
    else:
        return "🔴 Skip"


def build_html_email(
    repo: Repository, issue: Issue, ev: IssueEvaluation, badge: str
) -> str:
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
    .score-meta h2 {{ margin: 0 0 4px; font-size: 16px; }}
    .score-meta p {{ margin: 0; color: #57606a; font-size: 14px; }}
    table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
    td {{ padding: 8px 0; border-bottom: 1px solid #c8ccd0; font-size: 14px; vertical-align: top; }}
    td:first-child {{ width: 140px; color: #57606a; font-weight: 500; }}
    .reasoning {{ background: #f6f8fa; border-left: 3px solid #0969da; border-radius: 4px; padding: 12px 16px; font-size: 14px; color: #24292f; line-height: 1.6; margin: 16px 0; }}
    .btn {{ display: inline-block; background: #0969da; color: #ffffff !important; padding: 10px 20px; border-radius: 6px;
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

      <table cellpadding="0" cellspacing="0" style="width: auto; margin-bottom: 24px; border: none;">
        <tr>
          <td style="padding: 0; border: none; vertical-align: middle;">
            <div style="width: 72px; height: 72px; border-radius: 36px; background: #0969da;
                        color: #ffffff; font-size: 24px; font-weight: 700;
                        text-align: center; line-height: 72px;">
              {ev.score}
            </div>
          </td>
          <td style="padding: 0 0 0 16px; border: none; vertical-align: middle;">
            <div class="score-meta">
              <h2>{badge}</h2>
              <p>{ev.impression}</p>
            </div>
          </td>
        </tr>
      </table>

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

      <a class="btn" href="{issue.html_url}" target="_blank" style="color: #ffffff !important;">View Issue on GitHub →</a>
    </div>
    <div class="footer">
      Sent by your GitHub Issue Agent · {repo.html_url}
    </div>
  </div>
</body>
</html>"""


def build_text_email(
    repo: Repository, issue: Issue, ev: IssueEvaluation, badge: str
) -> str:
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


def _send_smtp(msg: MIMEMultipart) -> None:
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(settings.EMAIL_FROM, settings.GMAIL_APP_PASSWORD)
        server.sendmail(settings.EMAIL_FROM, settings.EMAIL_TO, msg.as_string())


async def send_evaluation_email(
    repo: Repository, issue: Issue, ev: IssueEvaluation
) -> None:
    if ev.score < settings.MIN_SCORE_TO_NOTIFY:
        logger.info(
            f"Score {ev.score} below threshold {settings.MIN_SCORE_TO_NOTIFY} — skipping email. reason: {ev.reasoning}"
        )
        return

    badge = score_badge(ev.score)
    subject = (
        f"[{badge}] {repo.name} #{issue.number} — {issue.title} (Score: {ev.score}/100)"
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = settings.EMAIL_TO
    msg.attach(MIMEText(build_text_email(repo, issue, ev, badge), "plain"))
    msg.attach(MIMEText(build_html_email(repo, issue, ev, badge), "html"))

    await asyncio.get_event_loop().run_in_executor(None, _send_smtp, msg)

    logger.info(f"Email sent for issue #{issue.number} (score: {ev.score})")
