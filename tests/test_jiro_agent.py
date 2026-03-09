from __future__ import annotations

from src.jiro_agent import JiroAgent
from tests.conftest import make_issue


class _FakeClient:
    def __init__(self) -> None:
        self._issues = {
            "PARENT-1": make_issue(
                key="PARENT-1",
                summary="Payments reliability initiative",
                issue_type="Epic",
                description="Goal: Improve payment stability and reduce retry failures.",
            ),
            "SUB-1": make_issue(
                key="SUB-1",
                summary="Fix flaky payment tests",
                parent_key="PARENT-1",
                status="In Progress",
                priority="High",
            ),
            "SUB-2": make_issue(
                key="SUB-2",
                summary="Analyze prod payment incident",
                parent_key="PARENT-1",
                status="In Review",
                issue_type="Bug",
                priority="Highest",
            ),
        }

    def search_issues(self, jql: str, max_results: int = 20):
        if "assignee = currentUser()" in jql:
            return [self._issues["SUB-1"]]
        if "reporter = currentUser()" in jql:
            return [self._issues["SUB-2"]]
        if 'parent = "PARENT-1"' in jql:
            return [self._issues["SUB-1"], self._issues["SUB-2"]]
        return []

    def get_issue(self, issue_key: str):
        return self._issues[issue_key]

    def get_issue_comments(self, issue_key: str):
        return []


def test_triage_includes_parent_summaries_for_assignee_or_reporter_children(settings):
    agent = JiroAgent(settings)
    agent._client = _FakeClient()  # type: ignore[assignment]

    report = agent.triage()

    assert len(report.parent_summaries) == 1
    summary = report.parent_summaries[0]
    assert summary.parent_key == "PARENT-1"
    assert "improve payment stability" in summary.goal.lower()
    assert any("SUB-1" in item for item in summary.progress)
    assert any("SUB-2" in item for item in summary.progress)
