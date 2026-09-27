"""Adapter Gmail REST API (đọc) — xem `read_adapter.py`."""

from agent_integrations.gmail.read_adapter import (
    GMAIL_API_BASE_URL,
    MAX_RESULTS_LIMIT,
    SNIPPET_MAX_LENGTH,
    EmailReadAdapter,
    EmailSummary,
    GmailApiError,
    GmailReadAdapter,
    GmailReauthRequiredError,
    GmailRetryableError,
)

__all__ = [
    "GMAIL_API_BASE_URL",
    "MAX_RESULTS_LIMIT",
    "SNIPPET_MAX_LENGTH",
    "EmailReadAdapter",
    "EmailSummary",
    "GmailApiError",
    "GmailReadAdapter",
    "GmailReauthRequiredError",
    "GmailRetryableError",
]
