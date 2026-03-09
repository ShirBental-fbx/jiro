from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, field_validator


def _find_dotenv() -> Path | None:
    """Walk up from cwd looking for .env, stop at filesystem root."""
    current = Path.cwd()
    while True:
        candidate = current / ".env"
        if candidate.is_file():
            return candidate
        parent = current.parent
        if parent == current:
            return None
        current = parent


class Settings(BaseModel):
    jira_base_url: str
    jira_email: str
    jira_api_token: str
    stale_days: int = 5
    default_max_results: int = 20

    @field_validator("jira_base_url")
    @classmethod
    def strip_trailing_slash(cls, v: str) -> str:
        return v.rstrip("/")

    @field_validator("jira_base_url", "jira_email", "jira_api_token")
    @classmethod
    def must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be empty")
        return v.strip()


def load_settings() -> Settings:
    """Load settings from environment, with .env file support."""
    dotenv_path = _find_dotenv()
    if dotenv_path:
        load_dotenv(dotenv_path)

    missing = []
    for var in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"):
        if not os.getenv(var):
            missing.append(var)

    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}. "
            f"Copy .env.example to .env and fill in your values."
        )

    return Settings(
        jira_base_url=os.environ["JIRA_BASE_URL"],
        jira_email=os.environ["JIRA_EMAIL"],
        jira_api_token=os.environ["JIRA_API_TOKEN"],
        stale_days=int(os.getenv("JIRO_STALE_DAYS", "5")),
        default_max_results=int(os.getenv("JIRO_DEFAULT_MAX_RESULTS", "20")),
    )
