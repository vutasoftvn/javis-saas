"""Local-first event-driven substrate for COSA."""
from apps.cosa.events.contracts import Envelope, validate_envelope
from apps.cosa.events.trigger_policy import EventTriggerRule, PinnedSpecIdentity, TriggerDecision, TriggerPolicyService
from apps.cosa.events.router import handle_event, Unauthenticated, PermissionDenied, IntakeResult

__all__ = [
    "Envelope",
    "validate_envelope",
    "EventTriggerRule",
    "PinnedSpecIdentity",
    "TriggerDecision",
    "TriggerPolicyService",
    "handle_event",
    "Unauthenticated",
    "PermissionDenied",
    "IntakeResult",
]
