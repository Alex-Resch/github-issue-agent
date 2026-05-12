from pydantic_settings import BaseSettings


class Settings(BaseSettings):
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

    class Config:
        env_file = "../.env"
        env_file_encoding = "utf-8"


settings = Settings()
