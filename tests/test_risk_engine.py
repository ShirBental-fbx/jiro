from __future__ import annotations

from src.models import RiskSeverity, RiskType
from src.risk_engine import assess_risks

from tests.conftest import make_comment, make_issue


def test_empty_description_flags_vague(settings):
    issue = make_issue(description="")
    report = assess_risks(issue, [], settings)

    vague = [f for f in report.findings if f.risk_type == RiskType.VAGUE_DESCRIPTION]
    assert len(vague) == 1
    assert vague[0].severity == RiskSeverity.HIGH


def test_short_description_flags_vague(settings):
    issue = make_issue(description="Fix the bug.")
    report = assess_risks(issue, [], settings)

    vague = [f for f in report.findings if f.risk_type == RiskType.VAGUE_DESCRIPTION]
    assert len(vague) == 1
    assert vague[0].severity == RiskSeverity.HIGH


def test_medium_description_flags_medium(settings):
    issue = make_issue(description="x" * 150)
    report = assess_risks(issue, [], settings)

    vague = [f for f in report.findings if f.risk_type == RiskType.VAGUE_DESCRIPTION]
    assert len(vague) == 1
    assert vague[0].severity == RiskSeverity.MEDIUM


def test_long_description_no_vague_flag(settings):
    issue = make_issue(description="x" * 250)
    report = assess_risks(issue, [], settings)

    vague = [f for f in report.findings if f.risk_type == RiskType.VAGUE_DESCRIPTION]
    assert len(vague) == 0


def test_missing_acceptance_criteria(settings):
    issue = make_issue(description="Implement the feature as discussed in the meeting. " * 5)
    report = assess_risks(issue, [], settings)

    ac = [f for f in report.findings if f.risk_type == RiskType.MISSING_ACCEPTANCE_CRITERIA]
    assert len(ac) == 1


def test_acceptance_criteria_present(settings):
    issue = make_issue(description="Acceptance criteria:\n- User can log in\n- User sees dashboard")
    report = assess_risks(issue, [], settings)

    ac = [f for f in report.findings if f.risk_type == RiskType.MISSING_ACCEPTANCE_CRITERIA]
    assert len(ac) == 0


def test_stale_ticket_detected(settings):
    issue = make_issue(updated_days_ago=11)
    report = assess_risks(issue, [], settings)

    stale = [f for f in report.findings if f.risk_type == RiskType.STALE_TICKET]
    assert len(stale) == 1
    assert stale[0].severity == RiskSeverity.HIGH


def test_fresh_ticket_not_stale(settings):
    issue = make_issue(updated_days_ago=2)
    report = assess_risks(issue, [], settings)

    stale = [f for f in report.findings if f.risk_type == RiskType.STALE_TICKET]
    assert len(stale) == 0


def test_unclear_dependency_no_links(settings):
    issue = make_issue(description="This depends on the auth service being deployed first.")
    report = assess_risks(issue, [], settings)

    dep = [f for f in report.findings if f.risk_type == RiskType.UNCLEAR_DEPENDENCY]
    assert len(dep) == 1
    assert dep[0].severity == RiskSeverity.HIGH


def test_dependency_with_links_low_severity(settings):
    issue = make_issue(
        description="This depends on the auth service.",
        linked_issue_keys=["AUTH-42"],
    )
    report = assess_risks(issue, [], settings)

    dep = [f for f in report.findings if f.risk_type == RiskType.UNCLEAR_DEPENDENCY]
    assert len(dep) == 1
    assert dep[0].severity == RiskSeverity.LOW


def test_missing_owner_in_comments(settings):
    comment = make_comment(body="We are waiting on someone to provide the API spec.")
    issue = make_issue()
    report = assess_risks(issue, [comment], settings)

    owner = [f for f in report.findings if f.risk_type == RiskType.MISSING_OWNER]
    assert len(owner) == 1


def test_owner_mentioned_no_flag(settings):
    comment = make_comment(body="Waiting on @john to provide the API spec.")
    issue = make_issue()
    report = assess_risks(issue, [comment], settings)

    owner = [f for f in report.findings if f.risk_type == RiskType.MISSING_OWNER]
    assert len(owner) == 0


def test_oversized_scope_detected(settings):
    issue = make_issue(
        description="This is a full stack migration that additionally requires a backfill of all data.",
        subtask_keys=[],
    )
    report = assess_risks(issue, [], settings)

    scope = [f for f in report.findings if f.risk_type == RiskType.OVERSIZED_SCOPE]
    assert len(scope) == 1


def test_no_risks_on_clean_ticket(settings):
    issue = make_issue(
        description="Acceptance criteria:\n- Feature works as specified\n" + ("Detail. " * 50),
        updated_days_ago=1,
        story_points=3.0,
    )
    report = assess_risks(issue, [], settings)
    assert len(report.findings) == 0


def test_highest_severity_property(settings):
    issue = make_issue(description="", updated_days_ago=15)
    report = assess_risks(issue, [], settings)

    assert report.has_risks
    assert report.highest_severity == RiskSeverity.HIGH
