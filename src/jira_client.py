from __future__ import annotations

from datetime import datetime, timezone

import requests

from src.config import Settings
from src.models import Issue, IssueComment


REQUEST_TIMEOUT = 15

ISSUE_FIELDS = [
    "summary",
    "status",
    "priority",
    "assignee",
    "reporter",
    "issuetype",
    "description",
    "labels",
    "components",
    "created",
    "updated",
    "resolution",
    "parent",
    "subtasks",
    "issuelinks",
    "customfield_10016",  # story points (common field id)
    "sprint",
]


class JiraClientError(Exception):
    """Raised when a Jira API request fails."""

    def __init__(self, message: str, status_code: int | None = None):
        self.status_code = status_code
        super().__init__(message)


class JiraClient:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._session = requests.Session()
        self._session.auth = (settings.jira_email, settings.jira_api_token)
        self._session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
        })
        self._base = f"{settings.jira_base_url}/rest/api/3"

    def search_issues(self, jql: str, max_results: int | None = None) -> list[Issue]:
        max_results = max_results or self._settings.default_max_results
        payload = {
            "jql": jql,
            "maxResults": max_results,
            "fields": ISSUE_FIELDS,
        }
        data = self._post("/search", payload)
        return [self._parse_issue(raw) for raw in data.get("issues", [])]

    def get_issue(self, issue_key: str) -> Issue:
        data = self._get(f"/issue/{issue_key}", params={"fields": ",".join(ISSUE_FIELDS)})
        return self._parse_issue(data)

    def get_issue_comments(self, issue_key: str) -> list[IssueComment]:
        data = self._get(f"/issue/{issue_key}/comment", params={"orderBy": "-created"})
        return [self._parse_comment(raw) for raw in data.get("comments", [])]

    # ----- HTTP helpers -----

    def _get(self, path: str, params: dict | None = None) -> dict:
        url = f"{self._base}{path}"
        try:
            resp = self._session.get(url, params=params, timeout=REQUEST_TIMEOUT)
        except requests.RequestException as exc:
            raise JiraClientError(f"Request failed: {exc}") from exc
        self._check_response(resp)
        return resp.json()

    def _post(self, path: str, payload: dict) -> dict:
        url = f"{self._base}{path}"
        try:
            resp = self._session.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        except requests.RequestException as exc:
            raise JiraClientError(f"Request failed: {exc}") from exc
        self._check_response(resp)
        return resp.json()

    def _check_response(self, resp: requests.Response) -> None:
        if resp.status_code == 401:
            raise JiraClientError("Authentication failed. Check JIRA_EMAIL and JIRA_API_TOKEN.", 401)
        if resp.status_code == 403:
            raise JiraClientError("Permission denied. Your token may lack the required scopes.", 403)
        if resp.status_code == 404:
            raise JiraClientError(f"Not found: {resp.url}", 404)
        if not resp.ok:
            body = resp.text[:500]
            raise JiraClientError(f"Jira API error {resp.status_code}: {body}", resp.status_code)

    # ----- Response parsing -----

    @staticmethod
    def _parse_issue(raw: dict) -> Issue:
        fields = raw.get("fields", {})
        return Issue(
            key=raw["key"],
            summary=fields.get("summary", ""),
            status=_nested_name(fields, "status"),
            priority=_nested_name(fields, "priority") or "Medium",
            assignee=_nested_display(fields, "assignee"),
            reporter=_nested_display(fields, "reporter"),
            issue_type=_nested_name(fields, "issuetype") or "Task",
            description=_extract_description(fields.get("description")),
            labels=fields.get("labels", []),
            components=[c.get("name", "") for c in fields.get("components", [])],
            created=_parse_datetime(fields.get("created")),
            updated=_parse_datetime(fields.get("updated")),
            resolution=_nested_name(fields, "resolution"),
            parent_key=_safe_key(fields.get("parent")),
            subtask_keys=[s["key"] for s in fields.get("subtasks", [])],
            linked_issue_keys=_extract_linked_keys(fields.get("issuelinks", [])),
            story_points=fields.get("customfield_10016"),
            sprint_name=_extract_sprint_name(fields.get("sprint")),
        )

    @staticmethod
    def _parse_comment(raw: dict) -> IssueComment:
        return IssueComment(
            id=raw.get("id", ""),
            author=_nested_display_direct(raw, "author"),
            body=_extract_description(raw.get("body")),
            created=_parse_datetime(raw.get("created")) or datetime.now(timezone.utc),
        )


# ---------------------------------------------------------------------------
# Field extraction helpers
# ---------------------------------------------------------------------------

def _nested_name(fields: dict, key: str) -> str:
    obj = fields.get(key)
    if isinstance(obj, dict):
        return obj.get("name", "")
    return ""


def _nested_display(fields: dict, key: str) -> str | None:
    obj = fields.get(key)
    if isinstance(obj, dict):
        return obj.get("displayName") or obj.get("name")
    return None


def _nested_display_direct(raw: dict, key: str) -> str:
    obj = raw.get(key)
    if isinstance(obj, dict):
        return obj.get("displayName") or obj.get("name", "unknown")
    return "unknown"


def _safe_key(obj: dict | None) -> str | None:
    if isinstance(obj, dict):
        return obj.get("key")
    return None


def _parse_datetime(val: str | None) -> datetime | None:
    if not val:
        return None
    try:
        return datetime.fromisoformat(val.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _extract_description(body: object) -> str:
    """Extract plain text from Jira Cloud ADF (Atlassian Document Format) or plain string."""
    if isinstance(body, str):
        return body
    if not isinstance(body, dict):
        return ""
    return _adf_to_text(body)


def _adf_to_text(node: dict) -> str:
    """Recursively extract text from an ADF document tree."""
    if node.get("type") == "text":
        return node.get("text", "")
    parts: list[str] = []
    for child in node.get("content", []):
        parts.append(_adf_to_text(child))
    text = "".join(parts)
    if node.get("type") in ("paragraph", "heading", "bulletList", "orderedList", "listItem"):
        text = text.strip() + "\n"
    return text


def _extract_linked_keys(links: list[dict]) -> list[str]:
    keys: list[str] = []
    for link in links:
        inward = link.get("inwardIssue")
        outward = link.get("outwardIssue")
        if isinstance(inward, dict) and "key" in inward:
            keys.append(inward["key"])
        if isinstance(outward, dict) and "key" in outward:
            keys.append(outward["key"])
    return keys


def _extract_sprint_name(sprint: object) -> str | None:
    if isinstance(sprint, dict):
        return sprint.get("name")
    if isinstance(sprint, list) and sprint:
        last = sprint[-1]
        if isinstance(last, dict):
            return last.get("name")
    return None
