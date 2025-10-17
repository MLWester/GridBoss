from __future__ import annotations


class EmailError(Exception):
    """Base class for email-related errors."""


class EmailTemplateError(EmailError):
    """Raised when an email template cannot be loaded or rendered."""


class EmailConfigurationError(EmailError):
    """Raised when email configuration is incomplete or invalid."""


class EmailDeliveryError(EmailError):
    """Raised when an email provider fails to deliver a message."""
