import re
from typing import NamedTuple


class _Pattern(NamedTuple):
    name: str
    regex: "re.Pattern[str]"


_PATTERNS = [
    _Pattern("openai_api_key", re.compile(r"sk-[A-Za-z0-9]{16,}")),
    _Pattern("google_api_key", re.compile(r"AIza[0-9A-Za-z\-_]{35}")),
    _Pattern("github_token", re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}")),
    _Pattern("slack_token", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    _Pattern("authorization_header", re.compile(r"(?i)authorization:\s*bearer\s+[A-Za-z0-9\-_.]+")),
    _Pattern("bearer_token", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9\-_.]{16,}")),
    _Pattern(
        "private_key_block",
        re.compile(
            r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----[\s\S]+?"
            r"-----END (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"
        ),
    ),
    _Pattern("connection_string_credentials", re.compile(r"[a-zA-Z][a-zA-Z0-9+.\-]*://[^\s:/@]+:[^\s@]+@\S+")),
    _Pattern("password_assignment", re.compile(r"(?i)\b(password|passwd|pwd)\s*[:=]\s*\S+")),
    _Pattern("session_cookie", re.compile(r"(?i)\bcookie:\s*\S+")),
    _Pattern(
        "generic_secret_assignment",
        re.compile(r"(?i)\b(api[_-]?key|access[_-]?token|refresh[_-]?token|secret[_-]?key)\s*[:=]\s*\S+"),
    ),
]

# Heuristic: 12 or 24 space-separated lowercase alphabetic words in a row -
# resembles a BIP-39 seed phrase. Imperfect (can false-positive on ordinary
# lowercase prose), but seed phrases must never leak into captured memory
# even at the cost of occasionally over-redacting (spec §179).
_SEED_PHRASE_RE = re.compile(r"(?:\b[a-z]+\b[ \t]+){23}\b[a-z]+\b|(?:\b[a-z]+\b[ \t]+){11}\b[a-z]+\b")


def redact_text(text: str) -> str:
    """Strip secrets from text before it is ever captured into Agent Memory
    (mCOSA V12.3 §179): API keys, access/refresh tokens, passwords, private
    keys, seed phrases, session cookies, authorization headers, connection
    strings with credentials. Secrets belong in the existing mCOSA Secret
    Vault, never Agent Memory.
    """
    if not text:
        return text

    redacted = text
    for pattern in _PATTERNS:
        redacted = pattern.regex.sub(f"[REDACTED:{pattern.name}]", redacted)
    redacted = _SEED_PHRASE_RE.sub("[REDACTED:seed_phrase]", redacted)
    return redacted
