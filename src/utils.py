from __future__ import annotations

import re
from datetime import datetime, timezone


def days_ago(dt: datetime | None) -> int:
    """Return the number of calendar days between dt and now. Returns 9999 if dt is None."""
    if dt is None:
        return 9999
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return max(0, (now - dt).days)


def text_contains_any(text: str, terms: list[str]) -> str | None:
    """Return the first matching term found in text (case-insensitive), or None."""
    lower = text.lower()
    for term in terms:
        if term.lower() in lower:
            return term
    return None


def strip_jira_markup(text: str) -> str:
    """Rough strip of common Jira/ADF markup for plain-text analysis."""
    text = re.sub(r"\{[^}]+\}", "", text)
    text = re.sub(r"\[([^|]+)\|[^\]]+\]", r"\1", text)
    text = re.sub(r"[*_~^+\-]", "", text)
    text = re.sub(r"h[1-6]\.\s*", "", text)
    return text.strip()


def truncate(text: str, max_len: int = 120) -> str:
    """Truncate text to max_len, appending ellipsis if needed."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"
