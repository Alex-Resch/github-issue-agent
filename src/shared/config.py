from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # GitHub
    GITHUB_WEBHOOK_SECRET: str = ""
    GITHUB_TOKEN: str = ""

    # Anthropic
    ANTHROPIC_API_KEY: str = ""

    # Gmail
    EMAIL_FROM: str = "agent@example.com"
    EMAIL_FROM_NAME: str = "GitHub Issue Agent"
    EMAIL_TO: str = "your-email@example.com"
    EMAIL_TO_NAME: str = "Developer"
    GMAIL_APP_PASSWORD: str = ""

    # Scoring threshold — issues below this score are skipped
    MIN_SCORE_TO_NOTIFY: int = 40

    # Polling
    REPOS: list[str] = [
        "pydantic/pydantic-ai",
        "567-labs/instructor",
        "a2aproject/a2a-python",
        "PrefectHQ/fastmcp",
    ]
    POLL_INTERVAL_MINUTES: int = 20


settings = Settings()
