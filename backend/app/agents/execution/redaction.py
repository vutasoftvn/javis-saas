import os
import re
from typing import Optional

# Pre-compiled regex patterns for common secrets and tokens
PATTERNS = [
    (re.compile(r"sk-[a-zA-Z0-9_\-]{20,}", re.IGNORECASE), "[REDACTED_API_KEY]"),
    (re.compile(r"Bearer\s+[a-zA-Z0-9_\-\.]{20,}", re.IGNORECASE), "Bearer [REDACTED_TOKEN]"),
    (re.compile(r"AKIA[0-9A-Z]{16}", re.IGNORECASE), "[REDACTED_AWS_KEY]"),
    (re.compile(r"(https?://[^:]+:)([^@]+)(@)", re.IGNORECASE), r"\1[REDACTED_PASSWORD]\3"),
    (re.compile(r"(postgres(?:ql)?://[^:]+:)([^@]+)(@)", re.IGNORECASE), r"\1[REDACTED_PASSWORD]\3"),
]

# Sensitive env keys whose values should be masked if present
SENSITIVE_ENV_KEYS = [
    "MASTER_SECRET_KEY",
    "JWT_SECRET",
    "DEEPSEEK_API_KEY",
    "OPENROUTER_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "OPEN_SANDBOX_API_KEY",
    "MINIO_SECRET_KEY",
    "LIVEKIT_API_SECRET",
    "LIVEKIT_LOCAL_API_SECRET",
]


def redact(text: Optional[str]) -> str:
    """Mask secret tokens, credentials, and sensitive environment variables from text."""
    if not text:
        return ""

    result = str(text)

    # 1. Regex pattern replacements
    for pattern, replacement in PATTERNS:
        result = pattern.sub(replacement, result)

    # 2. Environment variable values masking
    for key in SENSITIVE_ENV_KEYS:
        val = os.environ.get(key)
        if val and len(val) >= 6:
            result = result.replace(val, f"[REDACTED_{key}]")

    return result
