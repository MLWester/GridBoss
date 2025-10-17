"""Utilities for sanitizing user-provided content."""

from __future__ import annotations

import re

import bleach

ALLOWED_TAGS = ["a", "strong", "em", "ul", "ol", "li", "p", "br"]
ALLOWED_ATTRIBUTES = {"a": ["href", "title"]}
ALLOWED_PROTOCOLS = ["http", "https", "mailto"]
SCRIPT_STYLE_PATTERN = re.compile(r"<\s*(script|style)[^>]*>.*?<\s*/\s*\1\s*>", re.IGNORECASE | re.DOTALL)


def sanitize_league_description(value: str | None) -> str | None:
    """Sanitize a league description while preserving supported formatting."""

    if value is None:
        return None

    stripped = value.strip()
    if not stripped:
        return None

    without_scripts = SCRIPT_STYLE_PATTERN.sub("", stripped)

    cleaned = bleach.clean(
        without_scripts,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )
    normalized = cleaned.strip()
    return normalized if normalized else None

