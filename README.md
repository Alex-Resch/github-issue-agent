# GitHub Issue Agent

Monitors configured GitHub repos for actionable open-source contribution opportunities.
Polls for new feature request issues opened by top 5 contributors and new comments from top 5 contributors on existing issues.
Passes issue details and comments to Claude, which scores each opportunity 0–100 based on how worthwhile it would be to open a PR.
Sends a structured Gmail report for anything above your configured threshold.

## Architecture

```
Cloud Scheduler (every 20 min - so the container doesn't go idle)
        ↓
Cloud Run (FastAPI)
        ├──> Poll: new issues from top 5 contributors
        │       ├──> Filter: feature requests only
        │       └──> Claude API → Score (0–100) + analysis
        └──> Poll: new comments from top 5 contributors
                ├──> Fetch full issue + all comments
                └──> Claude API → Score (0–100) + analysis
                │
                └──> if score ≥ threshold → Send structured email with issue details, comment context, and Claude's analysis
```

## Setup

### 1. Clone & configure

```bash
cp .env.example .env
# Fill in all values in .env
```

### 2. Run locally

```bash
uv sync
uvicorn src.main:app --reload
```

### 3. Deploy to Cloud Run

Connect your GitHub repository via the Cloud Run console:

1. Go to **Cloud Run → Create Service → Connect Repository**
2. Select your repository and branch (`main`)
3. Set build type to **Dockerfile**
4. Add all environment variables from `.env`
5. Set **Ingress** to **All** (public)
6. Deploy

### 4. Set up Cloud Scheduler

Create a job to keep the container alive and trigger polling:

1. Go to **Cloud Scheduler → Create Job**
2. **Frequency:** `*/20 * * * *`
3. **Target:** HTTP GET `https://your-cloud-run-url/health`

## Configuration

| Variable | Description |
|---|---|
| `GITHUB_TOKEN` | GitHub personal access token (repo scope) |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `EMAIL_FROM` | Gmail address to send from |
| `EMAIL_TO` | Your email address |
| `GMAIL_APP_PASSWORD` | Gmail app password (not your regular password) |
| `REPOS` | Comma-separated list of repos to monitor (e.g. `pydantic/pydantic-ai,567-labs/instructor`) |
| `POLL_INTERVAL_MINUTES` | Polling interval in minutes (default: `20`) |
| `MIN_SCORE_TO_NOTIFY` | Minimum score to trigger an email (default: `40`) |

## Feature Request Detection

An issue is treated as a feature request if **any** of the following match:

- **Labels:** `feature`, `feature request`, `feature-request`, `enhancement`, `type: feature`
- **Title keywords:** `feature request`, `feature:`, `[feature]`, `add support`, `would be great if`

## Scoring

Claude evaluates each issue on a 0–100 scale:

| Score | Meaning |
|---|---|
| 80–100 | 🟢 High Priority — highly impactful, well-scoped |
| 60–79 | 🟡 Worth Exploring — interesting but needs research |
| 40–59 | 🟠 Low Priority — possible but not urgent |
| 0–39 | 🔴 Skip — not worth pursuing |

Issues with a score below `MIN_SCORE_TO_NOTIFY` are logged but no email is sent.

## Running Tests

```bash
uv run pytest tests/ -v --cov=src
```
