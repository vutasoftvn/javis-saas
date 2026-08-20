from typing import Any, Dict
import re

SENSITIVE_KEYS = re.compile(r'(password|secret|api_?key|token|auth|credential)', re.IGNORECASE)

def redact_payload(payload: Any) -> Any:
    """
    Recursively redact sensitive information from event payloads.
    """
    if isinstance(payload, dict):
        redacted = {}
        for k, v in payload.items():
            if SENSITIVE_KEYS.search(k):
                redacted[k] = "[REDACTED]"
            else:
                redacted[k] = redact_payload(v)
        return redacted
    elif isinstance(payload, list):
        return [redact_payload(item) for item in payload]
    return payload
