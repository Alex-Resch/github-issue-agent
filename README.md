# GitHub Issue Agent

Evaluates incoming GitHub feature requests via Claude and sends a scored email report via Brevo.

## Architecture

```
GitHub Webhook → Cloud Run (FastAPI)
                    ├── Filter: feature requests only
                    ├── Claude API → Score (0–100) + analysis
                    └── Brevo → HTML email to you
```

## Setup

### 1. Clone & configure

```bash
cp .env.example .env
# Fill in all values in .env
```

### 2. Run locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 3. Deploy to Cloud Run

```bash
# Build and push image
gcloud builds submit --tag gcr.io/YOUR_PROJECT/issue-agent

# Deploy
gcloud run deploy issue-agent \
  --image gcr.io/YOUR_PROJECT/issue-agent \
  --platform managed \
  --region europe-west1 \
  --allow-unauthenticated \
  --set-env-vars ANTHROPIC_API_KEY=sk-ant-...,BREVO_API_KEY=xkeysib-...,EMAIL_TO=you@email.com,...
```

Your webhook URL will be: `https://issue-agent-xxxx-ew.a.run.app/webhook/github`

### 4. Configure GitHub Webhooks

For each repo you want to monitor:

1. Go to **Settings → Webhooks → Add webhook**
2. **Payload URL:** `https://your-cloud-run-url/webhook/github`
3. **Content type:** `application/json`
4. **Secret:** Same value as `GITHUB_WEBHOOK_SECRET` in your `.env`
5. **Events:** Select **"Issues"** only
6. Save

## Feature Request Detection

An issue is treated as a feature request if **any** of the following match:

- **Labels:** `feature`, `feature request`, `feature-request`, `enhancement`, `type: feature`
- **Title keywords:** `feature request`, `feature:`, `[feature]`, `add support`, `would be great if`

## Score Threshold

Set `MIN_SCORE_TO_NOTIFY` in `.env` to suppress emails for low-scoring issues. For example, `MIN_SCORE_TO_NOTIFY=60` means only issues scoring 60+ trigger an email.

## Email Fields

| Field | Description |
|---|---|
| Score | 0–100 composite value |
| Difficulty | Low / Medium / High / Very High |
| Scope | Minimal / Small / Medium / Large |
| Impression | One-sentence summary |
| Reasoning | 2–4 sentence explanation |
| Recommendation | Concrete next step |

## Project Structure

```
app/
  main.py              # FastAPI app + webhook handler
  config.py            # Environment settings
  models.py            # Pydantic models (GitHub payload + evaluation)
  services/
    claude_service.py  # Claude API evaluation
    email_service.py   # Brevo HTML email
Dockerfile
requirements.txt
.env.example
```
