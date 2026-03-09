from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.config import Settings
from src.models import Issue, IssueComment


@pytest.fixture
def settings() -> Settings:
    return Settings(
        jira_base_url="https://test.atlassian.net",
        jira_email="test@test.com",
        jira_api_token="fake-token",
        stale_days=5,
        default_max_results=20,
    )


def make_issue(
    key: str = "TEST-1",
    summary: str = "Test issue",
    status: str = "In Progress",
    priority: str = "Medium",
    description: str = "A detailed description of the work to be done with enough content to pass length checks.",
    updated_days_ago: int = 0,
    labels: list[str] | None = None,
    subtask_keys: list[str] | None = None,
    linked_issue_keys: list[str] | None = None,
    story_points: float | None = None,
) -> Issue:
    now = datetime.now(timezone.utc)
    return Issue(
        key=key,
        summary=summary,
        status=status,
        priority=priority,
        description=description,
        created=now - timedelta(days=updated_days_ago + 5),
        updated=now - timedelta(days=updated_days_ago),
        labels=labels or [],
        subtask_keys=subtask_keys or [],
        linked_issue_keys=linked_issue_keys or [],
        story_points=story_points,
    )


def make_comment(
    body: str = "This is a comment.",
    author: str = "someone",
    days_ago: int = 0,
) -> IssueComment:
    now = datetime.now(timezone.utc)
    return IssueComment(
        id="comment-1",
        author=author,
        body=body,
        created=now - timedelta(days=days_ago),
    )
