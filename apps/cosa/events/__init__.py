"""Local-first event-driven substrate for COSA."""

from apps.cosa.events.contracts import Envelope, validate_envelope
from apps.cosa.events.router import IntakeResult, PermissionDenied, Unauthenticated, handle_event
from apps.cosa.events.trigger_policy import (
    EventTriggerRule,
    PinnedSpecIdentity,
    TriggerDecision,
    TriggerPolicyService,
)

__all__ = [
    "Envelope",
    "EventTriggerRule",
    "IntakeResult",
    "PermissionDenied",
    "PinnedSpecIdentity",
    "TriggerDecision",
    "TriggerPolicyService",
    "Unauthenticated",
    "handle_event",
    "validate_envelope",
]
