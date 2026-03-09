from __future__ import annotations

from src.models import (
    CommentDraft,
    CommentType,
    Issue,
    IssueComment,
    RiskReport,
    RiskType,
)
from src.utils import truncate


def draft_comment(
    issue: Issue,
    comments: list[IssueComment],
    comment_type: CommentType,
    risk_report: RiskReport | None = None,
) -> CommentDraft:
    generators = {
        CommentType.STATUS_UPDATE: _draft_status_update,
        CommentType.BLOCKER_UPDATE: _draft_blocker_update,
        CommentType.CLARIFICATION_REQUEST: _draft_clarification_request,
        CommentType.READY_FOR_REVIEW: _draft_ready_for_review,
    }

    generator = generators[comment_type]
    body = generator(issue, comments, risk_report)

    return CommentDraft(
        issue_key=issue.key,
        comment_type=comment_type,
        body=body,
    )


def _draft_status_update(
    issue: Issue,
    comments: list[IssueComment],
    risk_report: RiskReport | None,
) -> str:
    lines: list[str] = []
    lines.append(f"**Status update — {issue.key}**")
    lines.append("")

    lines.append(f"Current status: *{issue.status}*")
    lines.append("")

    lines.append("**Done:**")
    lines.append("- [describe what has been completed]")
    lines.append("")

    lines.append("**In progress:**")
    lines.append("- [describe current work]")
    lines.append("")

    pending = _infer_pending_items(issue, comments)
    if pending:
        lines.append("**Pending:**")
        for item in pending:
            lines.append(f"- {item}")
        lines.append("")

    if risk_report and risk_report.has_risks:
        lines.append("**Risks / open items:**")
        for finding in risk_report.findings[:3]:
            lines.append(f"- {finding.explanation}")
        lines.append("")

    lines.append("Will update when there's meaningful progress.")

    return "\n".join(lines)


def _draft_blocker_update(
    issue: Issue,
    comments: list[IssueComment],
    risk_report: RiskReport | None,
) -> str:
    lines: list[str] = []
    lines.append(f"**Blocker update — {issue.key}**")
    lines.append("")

    blocker_context = _extract_blocker_context(issue, comments)
    if blocker_context:
        lines.append(f"Blocked on: {blocker_context}")
    else:
        lines.append("Blocked on: [describe what is blocking this work]")
    lines.append("")

    lines.append("**Impact:**")
    lines.append("- [describe impact on timeline or dependent work]")
    lines.append("")

    lines.append("**What I need:**")
    lines.append("- [specific ask to unblock — who, what, by when]")
    lines.append("")

    lines.append("**Workaround:**")
    lines.append("- [if any, describe; otherwise state 'None identified']")

    return "\n".join(lines)


def _draft_clarification_request(
    issue: Issue,
    comments: list[IssueComment],
    risk_report: RiskReport | None,
) -> str:
    lines: list[str] = []
    lines.append(f"**Clarification needed — {issue.key}**")
    lines.append("")

    lines.append(f"Working on: *{truncate(issue.summary, 80)}*")
    lines.append("")

    questions = _infer_clarification_questions(issue, risk_report)
    if questions:
        lines.append("Before I proceed, I need clarity on:")
        for i, q in enumerate(questions, 1):
            lines.append(f"{i}. {q}")
    else:
        lines.append("Before I proceed, I need clarity on:")
        lines.append("1. [specific question about requirements]")
        lines.append("2. [specific question about scope or constraints]")

    lines.append("")
    lines.append("This is blocking implementation progress. Tagging [person] for input.")

    return "\n".join(lines)


def _draft_ready_for_review(
    issue: Issue,
    comments: list[IssueComment],
    risk_report: RiskReport | None,
) -> str:
    lines: list[str] = []
    lines.append(f"**Ready for review — {issue.key}**")
    lines.append("")

    lines.append("**What changed:**")
    lines.append("- [summarize the implementation]")
    lines.append("")

    lines.append("**How to test:**")
    lines.append("- [describe testing steps or link to test plan]")
    lines.append("")

    lines.append("**Risks / things to watch:**")
    if risk_report and risk_report.has_risks:
        for finding in risk_report.findings[:3]:
            lines.append(f"- {finding.explanation}")
    else:
        lines.append("- [note any deployment risks or monitoring needs]")

    lines.append("")
    lines.append("PR: [link]")
    lines.append("Requesting review from: [reviewer]")

    return "\n".join(lines)


def _infer_pending_items(issue: Issue, comments: list[IssueComment]) -> list[str]:
    """Infer pending work items from ticket context."""
    items: list[str] = []

    if issue.linked_issue_keys:
        items.append(f"Waiting on linked issues: {', '.join(issue.linked_issue_keys[:3])}")

    recent_waiting = False
    for c in comments[:3]:
        lower = c.body.lower()
        if any(term in lower for term in ("waiting", "pending", "blocked")):
            recent_waiting = True
            break

    if recent_waiting:
        items.append("Waiting on external input (see recent comments)")

    return items


def _extract_blocker_context(issue: Issue, comments: list[IssueComment]) -> str | None:
    """Try to extract a blocker description from recent context."""
    blocker_terms = ["blocked", "blocking", "waiting on", "depends on", "dependent on"]
    for c in comments[:5]:
        lower = c.body.lower()
        for term in blocker_terms:
            if term in lower:
                snippet = c.body[:200].strip()
                return truncate(snippet, 150)
    return None


def _infer_clarification_questions(
    issue: Issue,
    risk_report: RiskReport | None,
) -> list[str]:
    questions: list[str] = []

    if risk_report:
        for finding in risk_report.findings:
            if finding.risk_type == RiskType.MISSING_ACCEPTANCE_CRITERIA:
                questions.append("What are the acceptance criteria for this ticket?")
            elif finding.risk_type == RiskType.VAGUE_DESCRIPTION:
                questions.append("Can you provide more detail on the expected scope and behavior?")
            elif finding.risk_type == RiskType.UNCLEAR_DEPENDENCY:
                questions.append("What is the status of the dependency? Who owns unblocking it?")
            elif finding.risk_type == RiskType.OVERSIZED_SCOPE:
                questions.append("Should this be broken into smaller deliverables?")

    return questions[:4]
