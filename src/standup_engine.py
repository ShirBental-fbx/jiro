from __future__ import annotations

from src.config import Settings
from src.models import (
    Issue,
    IssueComment,
    StandupItem,
    StandupReport,
)
from src.utils import days_ago, text_contains_any, truncate


ACTIVE_STATUSES = ["in progress", "in review", "code review", "in development", "dev"]
DONE_STATUSES = ["done", "closed", "resolved", "released", "completed"]
BLOCKED_STATUSES = ["blocked", "waiting", "pending", "on hold"]

BLOCKER_TERMS = [
    "blocked",
    "waiting on",
    "dependency",
    "pending review",
    "awaiting",
    "external team",
]


def generate_standup(
    issues: list[Issue],
    comments_by_key: dict[str, list[IssueComment]],
    settings: Settings,
) -> StandupReport:
    yesterday = _build_yesterday(issues, comments_by_key)
    today = _build_today(issues, comments_by_key, settings)
    blockers = _build_blockers(issues, comments_by_key)
    notes = _build_notes(issues, settings)

    return StandupReport(
        yesterday=yesterday,
        today=today,
        blockers=blockers,
        notes=notes,
    )


def _build_yesterday(
    issues: list[Issue],
    comments_by_key: dict[str, list[IssueComment]],
) -> list[StandupItem]:
    """Tickets that had recent activity (updated in last 1-2 days) and are in active or done states."""
    items: list[StandupItem] = []

    for issue in issues:
        age = days_ago(issue.updated)
        if age > 2:
            continue

        status_lower = issue.status.lower()
        comments = comments_by_key.get(issue.key, [])
        recent_comment = _most_recent_comment_text(comments, max_days=2)

        if any(s in status_lower for s in DONE_STATUSES):
            items.append(StandupItem(
                issue_key=issue.key,
                summary=issue.summary,
                detail="Completed / moved to done.",
            ))
        elif any(s in status_lower for s in ACTIVE_STATUSES):
            detail = "Worked on this."
            if recent_comment:
                detail = f"Worked on this. Latest: {truncate(recent_comment, 80)}"
            items.append(StandupItem(
                issue_key=issue.key,
                summary=issue.summary,
                detail=detail,
            ))
        elif age <= 1:
            items.append(StandupItem(
                issue_key=issue.key,
                summary=issue.summary,
                detail=f"Updated (status: {issue.status}).",
            ))

    return items


def _build_today(
    issues: list[Issue],
    comments_by_key: dict[str, list[IssueComment]],
    settings: Settings,
) -> list[StandupItem]:
    """Tickets likely to be worked on today: active, high priority unstarted, or recently unblocked."""
    items: list[StandupItem] = []

    for issue in issues:
        status_lower = issue.status.lower()
        comments = comments_by_key.get(issue.key, [])

        if any(s in status_lower for s in DONE_STATUSES):
            continue

        if any(s in status_lower for s in BLOCKED_STATUSES):
            continue

        if any(s in status_lower for s in ACTIVE_STATUSES):
            items.append(StandupItem(
                issue_key=issue.key,
                summary=issue.summary,
                detail="Continue working on this.",
            ))
        elif issue.priority in ("Highest", "High") and status_lower in ("to do", "open", "new", "backlog"):
            items.append(StandupItem(
                issue_key=issue.key,
                summary=issue.summary,
                detail=f"High priority ({issue.priority}), needs to be started.",
            ))

    return items


def _build_blockers(
    issues: list[Issue],
    comments_by_key: dict[str, list[IssueComment]],
) -> list[StandupItem]:
    items: list[StandupItem] = []

    for issue in issues:
        status_lower = issue.status.lower()
        comments = comments_by_key.get(issue.key, [])

        if any(s in status_lower for s in BLOCKED_STATUSES):
            blocker_detail = _extract_blocker_detail(issue, comments)
            items.append(StandupItem(
                issue_key=issue.key,
                summary=issue.summary,
                detail=blocker_detail or f"Status: {issue.status}",
            ))
            continue

        for c in comments[:3]:
            match = text_contains_any(c.body, BLOCKER_TERMS)
            if match:
                items.append(StandupItem(
                    issue_key=issue.key,
                    summary=issue.summary,
                    detail=f"Recent comment mentions: \"{match}\"",
                ))
                break

    return items


def _build_notes(issues: list[Issue], settings: Settings) -> list[str]:
    notes: list[str] = []

    stale_count = sum(1 for i in issues if days_ago(i.updated) >= settings.stale_days)
    if stale_count > 0:
        notes.append(f"{stale_count} ticket(s) have not been updated in {settings.stale_days}+ days.")

    if not issues:
        notes.append("No open issues found — verify your JQL query.")

    active = [i for i in issues if any(s in i.status.lower() for s in ACTIVE_STATUSES)]
    if len(active) > 5:
        notes.append(f"You have {len(active)} tickets in active states — consider limiting WIP.")

    return notes


def _most_recent_comment_text(comments: list[IssueComment], max_days: int) -> str | None:
    if not comments:
        return None
    if days_ago(comments[0].created) <= max_days:
        return comments[0].body
    return None


def _extract_blocker_detail(issue: Issue, comments: list[IssueComment]) -> str | None:
    for c in comments[:3]:
        match = text_contains_any(c.body, BLOCKER_TERMS)
        if match:
            return truncate(c.body, 100)
    desc_match = text_contains_any(issue.description or "", BLOCKER_TERMS)
    if desc_match:
        return f"Description mentions: \"{desc_match}\""
    return None
