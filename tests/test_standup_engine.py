from __future__ import annotations

from src.standup_engine import generate_standup

from tests.conftest import make_comment, make_issue


def test_active_recent_issue_appears_in_yesterday(settings):
    issue = make_issue(key="ACT-1", status="In Progress", updated_days_ago=0)
    report = generate_standup([issue], {}, settings)

    keys = [i.issue_key for i in report.yesterday]
    assert "ACT-1" in keys


def test_old_issue_not_in_yesterday(settings):
    issue = make_issue(key="OLD-1", status="In Progress", updated_days_ago=5)
    report = generate_standup([issue], {}, settings)

    keys = [i.issue_key for i in report.yesterday]
    assert "OLD-1" not in keys


def test_active_issue_in_today(settings):
    issue = make_issue(key="TODAY-1", status="In Progress", updated_days_ago=0)
    report = generate_standup([issue], {}, settings)

    keys = [i.issue_key for i in report.today]
    assert "TODAY-1" in keys


def test_blocked_issue_not_in_today(settings):
    issue = make_issue(key="BLK-1", status="Blocked", updated_days_ago=0)
    report = generate_standup([issue], {}, settings)

    keys = [i.issue_key for i in report.today]
    assert "BLK-1" not in keys


def test_blocked_issue_in_blockers(settings):
    issue = make_issue(key="BLK-2", status="Blocked")
    report = generate_standup([issue], {}, settings)

    keys = [i.issue_key for i in report.blockers]
    assert "BLK-2" in keys


def test_blocker_from_comment(settings):
    issue = make_issue(key="BLK-3", status="In Progress")
    comments = {"BLK-3": [make_comment(body="This is blocked on the external API team.")]}
    report = generate_standup([issue], comments, settings)

    keys = [i.issue_key for i in report.blockers]
    assert "BLK-3" in keys


def test_done_issue_in_yesterday(settings):
    issue = make_issue(key="DONE-1", status="Done", updated_days_ago=0)
    report = generate_standup([issue], {}, settings)

    keys = [i.issue_key for i in report.yesterday]
    assert "DONE-1" in keys


def test_done_issue_not_in_today(settings):
    issue = make_issue(key="DONE-2", status="Done", updated_days_ago=0)
    report = generate_standup([issue], {}, settings)

    keys = [i.issue_key for i in report.today]
    assert "DONE-2" not in keys


def test_high_priority_backlog_in_today(settings):
    issue = make_issue(key="HP-1", priority="High", status="To Do", updated_days_ago=3)
    report = generate_standup([issue], {}, settings)

    keys = [i.issue_key for i in report.today]
    assert "HP-1" in keys


def test_stale_tickets_generate_note(settings):
    issues = [
        make_issue(key="S-1", updated_days_ago=10),
        make_issue(key="S-2", updated_days_ago=7),
    ]
    report = generate_standup(issues, {}, settings)

    assert any("2 ticket(s)" in n for n in report.notes)


def test_empty_issues_generates_note(settings):
    report = generate_standup([], {}, settings)

    assert any("No open issues" in n for n in report.notes)


def test_standup_report_has_timestamp(settings):
    report = generate_standup([], {}, settings)
    assert report.generated_at is not None
