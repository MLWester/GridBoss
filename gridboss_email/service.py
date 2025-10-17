from __future__ import annotations

from typing import Any

from .errors import EmailTemplateError
from .models import EmailContent, EmailEnvelope
from .templates import load_email_template


def render_email_content(
    envelope: EmailEnvelope,
    *,
    from_email: str,
) -> EmailContent:
    """Render the template referenced by the envelope using the supplied context."""
    template = load_email_template(envelope.template_id, envelope.locale)

    try:
        subject = template.subject.format(**envelope.context)
        html_body = template.html_body.format(**envelope.context)
        text_body = template.text_body.format(**envelope.context)
    except KeyError as exc:
        missing = exc.args[0]
        raise EmailTemplateError(
            f"Missing template context key '{missing}' for {envelope.template_id}"
        ) from exc

    return EmailContent(
        recipient=envelope.recipient,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        from_email=from_email,
    )
