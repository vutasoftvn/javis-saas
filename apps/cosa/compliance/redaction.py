from __future__ import annotations

import re
from typing import Any

EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_PATTERN = re.compile(r"(?:\+84|0)(?:3[2-9]|5[689]|7[06-9]|8[1-9]|9[0-9])[0-9]{7}")
CC_PATTERN = re.compile(r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b")


class Redactor:
    def sanitize(self, text: str) -> str:
        if not isinstance(text, str):
            return text
        text = EMAIL_PATTERN.sub("[EMAIL_REDACTED]", text)
        text = PHONE_PATTERN.sub("[PHONE_REDACTED]", text)
        text = CC_PATTERN.sub("[CARD_REDACTED]", text)
        return text

    def minimize(self, text: str, decision: Any = None) -> str:
        if decision and hasattr(decision, "minimization_required"):
            if not decision.minimization_required:
                return text
        return self.sanitize(text)
