from __future__ import annotations

from src.config import Settings
from src.models import (
    BlockerItem,
    Issue,
    IssueComment,
    PrioritySummaryItem,
    StaleTicketItem,
    SuggestedAction,
    TriageReport,
)
from src.risk_engine import assess_risks
from src.utils import days_ago, text_contains_any


DEFAULT_JQL = (
    "assignee = currentUser() AND resolution = Unresolved "
    "ORDER BY priority DESC, updated DESC"
)

PRIORITY_ORDER = {
    "Highest": 0,
    "High": 1,
    "Medium": 2,
    "Low": 3,
    "Lowest": 4,
}

BLOCKER_STATUS_TERMS = [
    "blocked",
    "waiting",
    "pending",
    "on hold",
]

BLOCKER_TEXT_TERMS = [
    "blocked",
    "waiting",
    "dependency",
    "dependent on",
    "pending review",
    "awaiting",
    "external team",
    "product clarification",
]


def build_triage_report(
    issues: list[Issue],
    comments_by_key: dict[str, list[IssueComment]],
    settings: Settings,
) -> TriageReport:
    priority_summary = _build_priority_summary(issues, comments_by_key, settings)
    blockers = _find_blockers(issues, comments_by_key)
    stale = _find_stale_tickets(issues, settings)
    actions = _suggest_actions(issues, comments_by_key, settings)

    return TriageReport(
        total_issues=len(issues),
        priority_summary=priority_summary,
        blockers=blockers,
        stale_tickets=stale,
        suggested_actions=actions,
    )


def _build_priority_summary(
    issues: list[Issue],
    comments_by_key: dict[str, list[IssueComment]],
    settings: Settings,
) -> list[PrioritySummaryItem]:
    items: list[PrioritySummaryItem] = []
    for issue in issues:
        has_blockers = _has_blocker_signals(issue, comments_by_key.get(issue.key, []))
        items.append(PrioritySummaryItem(
            issue_key=issue.key,
            summary=issue.summary,
            priority=issue.priority,
            status=issue.status,
            days_since_update=days_ago(issue.updated),
            has_blockers=has_blockers,
        ))

    items.sort(key=lambda x: (
        PRIORITY_ORDER.get(x.priority, 99),
        -x.has_blockers,
        -x.days_since_update,
    ))
    return items


def _find_blockers(
    issues: list[Issue],
    comments_by_key: dict[str, list[IssueComment]],
) -> list[BlockerItem]:
    blockers: list[BlockerItem] = []
    for issue in issues:
        status_match = text_contains_any(issue.status, BLOCKER_STATUS_TERMS)
        if status_match:
            blockers.append(BlockerItem(
                issue_key=issue.key,
                summary=issue.summary,
                signal=status_match,
                source="status",
            ))
            continue

        desc_match = text_contains_any(issue.description or "", BLOCKER_TEXT_TERMS)
        if desc_match:
            blockers.append(BlockerItem(
                issue_key=issue.key,
                summary=issue.summary,
                signal=desc_match,
                source="description",
            ))
            continue

        comments = comments_by_key.get(issue.key, [])
        for comment in comments[:3]:
            comment_match = text_contains_any(comment.body, BLOCKER_TEXT_TERMS)
            if comment_match:
                blockers.append(BlockerItem(
                    issue_key=issue.key,
                    summary=issue.summary,
                    signal=comment_match,
                    source="comment",
                ))
                break

    return blockers


def _find_stale_tickets(issues: list[Issue], settings: Settings) -> list[StaleTicketItem]:
    stale: list[StaleTicketItem] = []
    for issue in issues:
        age = days_ago(issue.updated)
        if age >= settings.stale_days:
            stale.append(StaleTicketItem(
                issue_key=issue.key,
                summary=issue.summary,
                days_since_update=age,
                status=issue.status,
            ))
    stale.sort(key=lambda x: x.days_since_update, reverse=True)
    return stale


def _suggest_actions(
    issues: list[Issue],
    comments_by_key: dict[str, list[IssueComment]],
    settings: Settings,
) -> list[SuggestedAction]:
    actions: list[SuggestedAction] = []
    for issue in issues:
        comments = comments_by_key.get(issue.key, [])
        risk_report = assess_risks(issue, comments, settings)

        for finding in risk_report.findings:
            urgency = "high" if finding.severity.value == "high" else "medium"
            actions.append(SuggestedAction(
                issue_key=issue.key,
                action=finding.recommended_action,
                reason=finding.explanation,
                urgency=urgency,
            ))

        if _is_waiting_on_others(issue, comments) and not _has_recent_comment(comments, max_days=3):
            actions.append(SuggestedAction(
                issue_key=issue.key,
                action="Follow up on pending action — no recent comments.",
                reason="Ticket appears to be waiting on someone else with no recent activity.",
                urgency="medium",
            ))

        if (
            issue.priority in ("Highest", "High")
            and issue.status.lower() in ("to do", "open", "new", "backlog")
        ):
            actions.append(SuggestedAction(
                issue_key=issue.key,
                action="High-priority ticket still in backlog — start or re-prioritize.",
                reason=f"Priority is {issue.priority} but status is '{issue.status}'.",
                urgency="high",
            ))

    actions.sort(key=lambda x: {"high": 0, "medium": 1, "low": 2}[x.urgency])
    return actions


def _has_blocker_signals(issue: Issue, comments: list[IssueComment]) -> bool:
    if text_contains_any(issue.status, BLOCKER_STATUS_TERMS):
        return True
    if text_contains_any(issue.description or "", BLOCKER_TEXT_TERMS):
        return True
    for comment in comments[:3]:
        if text_contains_any(comment.body, BLOCKER_TEXT_TERMS):
            return True
    return False


def _is_waiting_on_others(issue: Issue, comments: list[IssueComment]) -> bool:
    waiting_signals = ["waiting", "pending", "awaiting", "blocked"]
    if text_contains_any(issue.status, waiting_signals):
        return True
    for comment in comments[:3]:
        if text_contains_any(comment.body, waiting_signals):
            return True
    return False


def _has_recent_comment(comments: list[IssueComment], max_days: int) -> bool:
    if not comments:
        return False
    return days_ago(comments[0].created) <= max_days
