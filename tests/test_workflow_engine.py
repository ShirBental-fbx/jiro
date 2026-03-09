from __future__ import annotations

from src.models import WorkOrigin
from src.workflow_engine import analyze_workflow_health, classify_work_origin
from tests.conftest import make_issue


def test_orphan_tasks_detected_without_parent_or_epic():
    issues = [
        make_issue(key="A-1", issue_type="Task"),
        make_issue(key="A-2", issue_type="Task", parent_key="PROD-1"),
        make_issue(key="A-3", issue_type="Task", epic_key="EPIC-2"),
        make_issue(key="A-4", issue_type="Epic"),
    ]
    report = analyze_workflow_health(issues)

    orphan_keys = {item.issue_key for item in report.orphan_tasks}
    assert orphan_keys == {"A-1"}


def test_product_coverage_percentage_uses_parent_epic_and_product_labels():
    issues = [
        make_issue(key="P-1", parent_key="PROD-1"),
        make_issue(key="P-2", epic_key="EPIC-7"),
        make_issue(key="P-3", labels=["product"]),
        make_issue(key="P-4"),
    ]
    report = analyze_workflow_health(issues)

    assert report.product_coverage_pct == 75.0


def test_origin_classification_product_epic():
    issue = make_issue(key="O-1", epic_key="EPIC-1")
    assert classify_work_origin(issue) == WorkOrigin.PRODUCT_EPIC


def test_origin_classification_bug_production():
    issue = make_issue(key="O-2", issue_type="Bug", summary="Prod outage hotfix")
    assert classify_work_origin(issue) == WorkOrigin.BUG_PRODUCTION


def test_origin_classification_adhoc_engineering():
    issue = make_issue(key="O-3", issue_type="Task", labels=["techdebt"])
    assert classify_work_origin(issue) == WorkOrigin.ADHOC_ENGINEERING


def test_origin_breakdown_contains_counts():
    issues = [
        make_issue(key="B-1", epic_key="EPIC-1"),
        make_issue(key="B-2", issue_type="Bug"),
        make_issue(key="B-3", labels=["techdebt"]),
        make_issue(key="B-4", issue_type="Incident", summary="Production incident follow-up"),
    ]
    report = analyze_workflow_health(issues)
    counts = {item.origin: item.count for item in report.work_origin_breakdown}

    assert counts[WorkOrigin.PRODUCT_EPIC] == 1
    assert counts[WorkOrigin.BUG_PRODUCTION] == 2
    assert counts[WorkOrigin.ADHOC_ENGINEERING] == 1
