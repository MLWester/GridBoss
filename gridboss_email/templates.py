from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from .errors import EmailTemplateError
from .models import EmailTemplate

TEMPLATES_DIR = Path(__file__).parent / "templates"
DEFAULT_LOCALE = "en"


def _template_path(template_id: str, locale: str) -> Path:
    locale_dir = TEMPLATES_DIR / locale
    return locale_dir / f"{template_id}.json"


@lru_cache(maxsize=64)
def load_email_template(template_id: str, locale: str = DEFAULT_LOCALE) -> EmailTemplate:
    """Load an email template for the requested locale, falling back to English."""
    candidate_paths = [
        _template_path(template_id, locale),
    ]
    if locale != DEFAULT_LOCALE:
        candidate_paths.append(_template_path(template_id, DEFAULT_LOCALE))

    for path in candidate_paths:
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                raise EmailTemplateError(f"Failed to load template {template_id}") from exc

            try:
                subject = data["subject"]
                html_body = data["html"]
                text_body = data["text"]
            except KeyError as exc:
                raise EmailTemplateError(
                    f"Template {template_id} is missing required fields"
                ) from exc
            return EmailTemplate(subject=subject, html_body=html_body, text_body=text_body)

    raise EmailTemplateError(f"Template {template_id} not found for locale {locale}")
