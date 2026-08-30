from __future__ import annotations

import hashlib

import pytest
from pydantic import ValidationError

from apps.cosa.compliance.data_egress_context import DirectMessageDataAccess


def test_direct_message_context_hashes_server_content() -> None:
    context = DirectMessageDataAccess.from_message(
        message_id="msg_1",
        content="confidential plan",
        categories=frozenset({"BUSINESS_CONFIDENTIAL"}),
        subject_reference=None,
    )
    assert context.source_ref == "conversation_message:msg_1"
    assert context.source_hash == hashlib.sha256(b"confidential plan").hexdigest()


def test_direct_message_context_rejects_empty_categories() -> None:
    with pytest.raises(ValidationError):
        DirectMessageDataAccess.from_message(
            message_id="msg_2",
            content="hello",
            categories=frozenset(),
            subject_reference=None,
        )


@pytest.mark.parametrize("category", ["PERSONAL", "SENSITIVE_PERSONAL"])
def test_direct_message_context_rejects_personal_categories_without_subject_reference(
    category: str,
) -> None:
    with pytest.raises(ValidationError):
        DirectMessageDataAccess.from_message(
            message_id="msg_3",
            content="contains PII",
            categories=frozenset({category}),
            subject_reference=None,
        )


@pytest.mark.parametrize("category", ["PERSONAL", "SENSITIVE_PERSONAL"])
def test_direct_message_context_accepts_personal_categories_with_subject_reference(
    category: str,
) -> None:
    context = DirectMessageDataAccess.from_message(
        message_id="msg_4",
        content="contains PII",
        categories=frozenset({category}),
        subject_reference="contact:123",
    )
    assert context.subject_reference == "contact:123"


def test_direct_message_context_is_frozen() -> None:
    context = DirectMessageDataAccess.from_message(
        message_id="msg_5",
        content="hello",
        categories=frozenset({"NON_PERSONAL"}),
        subject_reference=None,
    )
    with pytest.raises(ValidationError):
        context.subject_reference = "contact:1"
