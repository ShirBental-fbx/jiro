from __future__ import annotations

import re

from src.config import Settings
from src.models import (
    Issue,
    IssueComment,
    RiskFinding,
    RiskReport,
    RiskSeverity,
    RiskType,
)
from src.utils import days_ago, text_contains_any


DEPENDENCY_TERMS = [
    "depends on",
    "dependent on",
    "dependency",
    "blocked by",
    "waiting on",
    "requires",
    "upstream",
    "downstream",
    "external team",
]

WAITING_TERMS = [
    "waiting on",
    "awaiting",
    "pending review",
    "need input from",
    "assigned to",
    "following up with",
    "reaching out to",
]

ACCEPTANCE_CRITERIA_SIGNALS = [
    "acceptance criteria",
    "ac:",
    "definition of done",
    "expected behavior",
    "given ",
    "when ",
    "then ",
]

SCOPE_TERMS = [
    "and also",
    "additionally",
    "phase 1",
    "phase 2",
    "multiple",
    "end-to-end",
    "full stack",
    "migration",
    "backfill",
    "refactor",
]

VAGUE_DESCRIPTION_THRESHOLD = 80
SHORT_DESCRIPTION_THRESHOLD = 200


def assess_risks(
    issue: Issue,
    comments: list[IssueComment],
    settings: Settings,
) -> RiskReport:
    findings: list[RiskFinding] = []

    findings.extend(_check_vague_description(issue))
    findings.extend(_check_missing_acceptance_criteria(issue))
    findings.extend(_check_unclear_dependency(issue, comments))
    findings.extend(_check_stale(issue, settings))
    findings.extend(_check_missing_owner(comments))
    findings.extend(_check_oversized_scope(issue))

    return RiskReport(
        issue_key=issue.key,
        summary=issue.summary,
        findings=findings,
    )


def _check_vague_description(issue: Issue) -> list[RiskFinding]:
    if not issue.has_description:
        return [RiskFinding(
            risk_type=RiskType.VAGUE_DESCRIPTION,
            severity=RiskSeverity.HIGH,
            explanation="Ticket has no description.",
            recommended_action="Add a description with context, scope, and expected outcome.",
        )]

    if issue.description_length < VAGUE_DESCRIPTION_THRESHOLD:
        return [RiskFinding(
            risk_type=RiskType.VAGUE_DESCRIPTION,
            severity=RiskSeverity.HIGH,
            explanation=f"Description is only {issue.description_length} characters — likely too vague to act on.",
            recommended_action="Expand the description with problem context, scope boundaries, and technical approach.",
        )]

    if issue.description_length < SHORT_DESCRIPTION_THRESHOLD:
        return [RiskFinding(
            risk_type=RiskType.VAGUE_DESCRIPTION,
            severity=RiskSeverity.MEDIUM,
            explanation=f"Description is {issue.description_length} characters — may lack sufficient detail.",
            recommended_action="Review whether the description covers scope, constraints, and expected behavior.",
        )]

    return []


def _check_missing_acceptance_criteria(issue: Issue) -> list[RiskFinding]:
    text = (issue.description or "").lower()
    if not text:
        return []

    has_ac = any(signal in text for signal in ACCEPTANCE_CRITERIA_SIGNALS)
    if has_ac:
        return []

    return [RiskFinding(
        risk_type=RiskType.MISSING_ACCEPTANCE_CRITERIA,
        severity=RiskSeverity.MEDIUM,
        explanation="No acceptance criteria detected in the description.",
        recommended_action="Ask product or the reporter to add explicit acceptance criteria.",
    )]


def _check_unclear_dependency(
    issue: Issue,
    comments: list[IssueComment],
) -> list[RiskFinding]:
    all_text = (issue.description or "") + " " + " ".join(c.body for c in comments)
    match = text_contains_any(all_text, DEPENDENCY_TERMS)
    if not match:
        return []

    has_linked = bool(issue.linked_issue_keys)

    if has_linked:
        return [RiskFinding(
            risk_type=RiskType.UNCLEAR_DEPENDENCY,
            severity=RiskSeverity.LOW,
            explanation=f"Dependency language found (\"{match}\") but linked issues exist — verify they're current.",
            recommended_action="Confirm linked issues reflect actual blocking dependencies.",
        )]

    return [RiskFinding(
        risk_type=RiskType.UNCLEAR_DEPENDENCY,
        severity=RiskSeverity.HIGH,
        explanation=f"Dependency language found (\"{match}\") but no linked issues. Dependency is implicit.",
        recommended_action="Link the blocking issue explicitly and confirm the dependency owner.",
    )]


def _check_stale(issue: Issue, settings: Settings) -> list[RiskFinding]:
    age = days_ago(issue.updated)
    threshold = settings.stale_days

    if age < threshold:
        return []

    severity = RiskSeverity.HIGH if age > threshold * 2 else RiskSeverity.MEDIUM
    return [RiskFinding(
        risk_type=RiskType.STALE_TICKET,
        severity=severity,
        explanation=f"Ticket has not been updated in {age} days (threshold: {threshold}).",
        recommended_action="Review whether this ticket is still relevant. Add a status comment or close it.",
    )]


def _check_missing_owner(comments: list[IssueComment]) -> list[RiskFinding]:
    if not comments:
        return []

    recent_comments = comments[:5]
    for comment in recent_comments:
        match = text_contains_any(comment.body, WAITING_TERMS)
        if match:
            has_mention = bool(re.search(r"@\w+|assigned to \w+", comment.body, re.IGNORECASE))
            if not has_mention:
                return [RiskFinding(
                    risk_type=RiskType.MISSING_OWNER,
                    severity=RiskSeverity.MEDIUM,
                    explanation=f"Comment indicates waiting (\"{match}\") but no explicit owner is mentioned.",
                    recommended_action="Identify who is responsible and @mention them in the ticket.",
                )]

    return []


def _check_oversized_scope(issue: Issue) -> list[RiskFinding]:
    text = (issue.summary + " " + (issue.description or "")).lower()

    scope_hits = sum(1 for term in SCOPE_TERMS if term in text)
    has_subtasks = bool(issue.subtask_keys)

    if scope_hits >= 2 and not has_subtasks:
        return [RiskFinding(
            risk_type=RiskType.OVERSIZED_SCOPE,
            severity=RiskSeverity.MEDIUM,
            explanation=f"Ticket references multiple scope indicators ({scope_hits} matches) with no subtasks.",
            recommended_action="Break this ticket into smaller, independently deliverable subtasks.",
        )]

    if issue.description_length > 2000 and not has_subtasks:
        return [RiskFinding(
            risk_type=RiskType.OVERSIZED_SCOPE,
            severity=RiskSeverity.LOW,
            explanation="Very long description without subtasks may indicate the ticket is too broad.",
            recommended_action="Consider whether this should be an epic with subtasks.",
        )]

    return []
