from __future__ import annotations

from src.parent_summary_engine import extract_goal_from_description, generate_parent_summary
from tests.conftest import make_issue


def test_extract_goal_from_goal_section():
    description = """
Goal:
Reduce lead processing latency in ingestion pipeline by removing redundant normalization passes.

Context:
This impacts partner webhook flow.
""".strip()
    goal = extract_goal_from_description(description)
    assert "reduce lead processing latency" in goal.lower()


def test_extract_goal_from_overview_section():
    description = """
## Overview
Stabilize outbound reporting so retries are idempotent and duplicate sends are prevented.
""".strip()
    goal = extract_goal_from_description(description)
    assert "stabilize outbound reporting" in goal.lower()


def test_extract_goal_fallback_first_meaningful_sentence():
    description = "Investigate stale partner sync behavior and ship a safe retry strategy. Extra notes follow."
    goal = extract_goal_from_description(description)
    assert goal.startswith("Investigate stale partner sync behavior")


def test_generate_parent_summary_uses_top_active_tasks():
    parent = make_issue(
        key="PARENT-1",
        summary="Parent initiative",
        description="Goal: Improve checkout reliability for direct draw flow.",
        issue_type="Epic",
    )
    children = [
        make_issue(key="CH-1", summary="Add retry middleware", status="In Progress", priority="High"),
        make_issue(key="CH-2", summary="Create dashboards", status="In Review", priority="Medium"),
        make_issue(key="CH-3", summary="Backfill historic errors", status="To Do", priority="Highest"),
        make_issue(key="CH-4", summary="Write runbook", status="In Development", priority="Low"),
    ]

    report = generate_parent_summary(parent, children)

    assert "improve checkout reliability" in report.goal.lower()
    assert report.health == "Active"
    assert "Backfill historic errors" in report.overview
    assert "Add retry middleware" in report.overview
    assert "Create dashboards" in report.overview
    assert "CH-1" not in report.overview
    assert "CH-2" not in report.overview
    assert "CH-3" not in report.overview
    assert "CH-4" not in report.overview
    assert len(report.progress) == 3
    assert any("CH-1 — Add retry middleware" in item for item in report.progress)
    assert any("(In Progress)" in item for item in report.progress)


def test_generate_parent_summary_with_no_active_children():
    parent = make_issue(
        key="PARENT-2",
        summary="Parent initiative",
        description="Context: Standardize integration test setup across services.",
        issue_type="Epic",
    )
    children = [
        make_issue(key="C-1", status="Done"),
        make_issue(key="C-2", status="Blocked"),
    ]

    report = generate_parent_summary(parent, children)
    assert "standardize integration test setup" in report.goal.lower()
    assert "No active child tasks" in report.overview
    assert report.health == "Queued"
    assert len(report.progress) == 1


def test_parent_goal_falls_back_to_summary_when_description_missing():
    parent = make_issue(
        key="PARENT-3",
        summary="Tech Debt",
        description="",
        issue_type="Epic",
    )
    report = generate_parent_summary(parent, [])
    assert report.goal == "Address technical debt in the system."


def test_health_stalled_when_has_stale_tasks():
    parent = make_issue(
        key="PARENT-4",
        summary="Parent initiative",
        description="Goal: Improve data quality.",
        issue_type="Epic",
    )
    children = [
        make_issue(key="S-1", status="To Do", updated_days_ago=8),
        make_issue(key="S-2", status="In Progress", updated_days_ago=0),
    ]
    report = generate_parent_summary(parent, children)
    assert report.health == "Stalled"


def test_cr_status_is_treated_as_active_child_task():
    parent = make_issue(
        key="PARENT-5",
        summary="Parent initiative",
        description="Goal: Improve API reliability.",
        issue_type="Epic",
    )
    children = [
        make_issue(key="CR-1", summary="Review API fixes", status="CR", priority="High"),
        make_issue(key="TODO-1", summary="Queue migration", status="To Do", priority="Medium"),
    ]
    report = generate_parent_summary(parent, children)
    assert "Review API fixes" in report.overview
    assert "CR-1" not in report.overview


def test_progress_line_uses_key_summary_status_format():
    parent = make_issue(
        key="PARENT-6",
        summary="Parent initiative",
        description="Goal: Improve API reliability.",
        issue_type="Epic",
    )
    children = [
        make_issue(key="NYE-111", summary="Implement PaymentPlanChangedEvent", status="CR"),
    ]
    report = generate_parent_summary(parent, children)
    assert report.progress[0] == "NYE-111 — Implement PaymentPlanChangedEvent (CR)"
