from __future__ import annotations

from src.comment_engine import draft_comment
from src.models import CommentType, RiskFinding, RiskReport, RiskSeverity, RiskType

from tests.conftest import make_comment, make_issue


def test_status_update_contains_key():
    issue = make_issue(key="PROJ-42", status="In Progress")
    draft = draft_comment(issue, [], CommentType.STATUS_UPDATE)

    assert "PROJ-42" in draft.body
    assert draft.comment_type == CommentType.STATUS_UPDATE


def test_status_update_includes_risks():
    issue = make_issue(key="PROJ-42")
    risk = RiskReport(
        issue_key="PROJ-42",
        summary="Test",
        findings=[RiskFinding(
            risk_type=RiskType.VAGUE_DESCRIPTION,
            severity=RiskSeverity.HIGH,
            explanation="Description too vague.",
            recommended_action="Expand it.",
        )],
    )
    draft = draft_comment(issue, [], CommentType.STATUS_UPDATE, risk_report=risk)

    assert "Description too vague" in draft.body


def test_blocker_update_format():
    issue = make_issue(key="PROJ-10", status="Blocked")
    comments = [make_comment(body="Blocked on external team delivering the API.")]
    draft = draft_comment(issue, comments, CommentType.BLOCKER_UPDATE)

    assert "Blocker update" in draft.body
    assert "PROJ-10" in draft.body
    assert "Impact" in draft.body
    assert "What I need" in draft.body


def test_clarification_request_with_risks():
    issue = make_issue(key="PROJ-20")
    risk = RiskReport(
        issue_key="PROJ-20",
        summary="Test",
        findings=[
            RiskFinding(
                risk_type=RiskType.MISSING_ACCEPTANCE_CRITERIA,
                severity=RiskSeverity.MEDIUM,
                explanation="No AC.",
                recommended_action="Ask for AC.",
            ),
        ],
    )
    draft = draft_comment(issue, [], CommentType.CLARIFICATION_REQUEST, risk_report=risk)

    assert "acceptance criteria" in draft.body.lower()
    assert "Clarification needed" in draft.body


def test_ready_for_review_format():
    issue = make_issue(key="PROJ-30", status="In Review")
    draft = draft_comment(issue, [], CommentType.READY_FOR_REVIEW)

    assert "Ready for review" in draft.body
    assert "What changed" in draft.body
    assert "How to test" in draft.body


def test_blocker_update_extracts_context_from_comments():
    issue = make_issue(key="PROJ-15", status="Blocked")
    comments = [make_comment(body="We are waiting on the infra team to provision the database.")]
    draft = draft_comment(issue, comments, CommentType.BLOCKER_UPDATE)

    assert "waiting on" in draft.body.lower() or "infra" in draft.body.lower()


def test_all_comment_types_produce_nonempty_body():
    issue = make_issue(key="PROJ-99")
    for ct in CommentType:
        draft = draft_comment(issue, [], ct)
        assert len(draft.body) > 20, f"Empty body for {ct}"
