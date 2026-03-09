from __future__ import annotations

from src.triage_engine import build_triage_report

from tests.conftest import make_comment, make_issue


def test_priority_ordering(settings):
    issues = [
        make_issue(key="LOW-1", priority="Low", summary="Low pri"),
        make_issue(key="HIGH-1", priority="High", summary="High pri"),
        make_issue(key="CRIT-1", priority="Highest", summary="Critical"),
    ]
    report = build_triage_report(issues, {}, settings)

    keys = [item.issue_key for item in report.priority_summary]
    assert keys[0] == "CRIT-1"
    assert keys[1] == "HIGH-1"
    assert keys[2] == "LOW-1"


def test_blocker_detected_from_status(settings):
    issues = [make_issue(key="BLK-1", status="Blocked", summary="Blocked ticket")]
    report = build_triage_report(issues, {}, settings)

    assert len(report.blockers) == 1
    assert report.blockers[0].source == "status"
    assert report.blockers[0].issue_key == "BLK-1"


def test_blocker_detected_from_description(settings):
    issues = [make_issue(
        key="BLK-2",
        status="In Progress",
        description="This is blocked by the external team delivering the API.",
    )]
    report = build_triage_report(issues, {}, settings)

    assert len(report.blockers) == 1
    assert report.blockers[0].source == "description"


def test_blocker_detected_from_comment(settings):
    issues = [make_issue(key="BLK-3", status="In Progress")]
    comments = {"BLK-3": [make_comment(body="We are waiting on the dependency from platform team.")]}
    report = build_triage_report(issues, comments, settings)

    assert len(report.blockers) == 1
    assert report.blockers[0].source == "comment"


def test_stale_ticket_detection(settings):
    issues = [
        make_issue(key="FRESH-1", updated_days_ago=1),
        make_issue(key="STALE-1", updated_days_ago=10),
        make_issue(key="STALE-2", updated_days_ago=6),
    ]
    report = build_triage_report(issues, {}, settings)

    stale_keys = {t.issue_key for t in report.stale_tickets}
    assert "STALE-1" in stale_keys
    assert "STALE-2" in stale_keys
    assert "FRESH-1" not in stale_keys


def test_stale_tickets_sorted_by_age(settings):
    issues = [
        make_issue(key="S1", updated_days_ago=6),
        make_issue(key="S2", updated_days_ago=20),
        make_issue(key="S3", updated_days_ago=10),
    ]
    report = build_triage_report(issues, {}, settings)

    ages = [t.days_since_update for t in report.stale_tickets]
    assert ages == sorted(ages, reverse=True)


def test_high_priority_backlog_generates_action(settings):
    issues = [make_issue(key="HP-1", priority="High", status="To Do")]
    report = build_triage_report(issues, {}, settings)

    action_keys = [a.issue_key for a in report.suggested_actions]
    assert "HP-1" in action_keys
    high_actions = [a for a in report.suggested_actions if a.issue_key == "HP-1" and a.urgency == "high"]
    assert len(high_actions) >= 1


def test_total_issues_count(settings):
    issues = [make_issue(key=f"T-{i}") for i in range(5)]
    report = build_triage_report(issues, {}, settings)
    assert report.total_issues == 5


def test_no_blocker_on_clean_ticket(settings):
    issues = [make_issue(key="CLEAN-1", status="In Progress", description="Normal work happening here.")]
    report = build_triage_report(issues, {}, settings)
    assert len(report.blockers) == 0


def test_triage_includes_workflow_health(settings):
    issues = [
        make_issue(key="WF-1", parent_key="PROD-10"),
        make_issue(key="WF-2", issue_type="Task"),
    ]
    report = build_triage_report(issues, {}, settings)

    assert report.workflow_health is not None
    assert report.workflow_health.product_coverage_pct == 50.0
    assert len(report.workflow_health.orphan_tasks) == 1


def test_triage_work_origin_breakdown(settings):
    issues = [
        make_issue(key="WFO-1", issue_type="Bug"),
        make_issue(key="WFO-2", epic_key="EPIC-9"),
        make_issue(key="WFO-3", labels=["techdebt"]),
    ]
    report = build_triage_report(issues, {}, settings)

    breakdown = {item.origin.value: item.count for item in report.workflow_health.work_origin_breakdown}
    assert breakdown["bug_production"] == 1
    assert breakdown["product_epic"] == 1
    assert breakdown["adhoc_engineering"] == 1
