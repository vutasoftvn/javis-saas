from collections.abc import Callable
from typing import Optional


FUNCTION_KEYWORDS = {
    "LEGAL": {"legal", "compliance", "contract", "privacy", "law"},
    "MARKETING": {"marketing", "campaign", "seo", "content", "brand"},
    "SALES": {"sales", "lead", "pipeline", "prospect", "crm"},
    "TECH": {"tech", "code", "api", "deployment", "bug", "software"},
    "FINANCE": {"finance", "cash", "accounting", "book", "invoice", "budget"},
}


def route_function(text: str, classifier: Optional[Callable[[str], str]] = None) -> Optional[str]:
    tokens = {token.strip(".,:;!?()[]{}").lower() for token in text.split()}
    scores = {function: len(tokens & keywords) for function, keywords in FUNCTION_KEYWORDS.items()}
    highest = max(scores.values(), default=0)
    winners = [function for function, score in scores.items() if score == highest and score > 0]
    if len(winners) == 1:
        return winners[0]
    if classifier is None:
        return None
    classified = classifier(text).upper()
    return classified if classified in FUNCTION_KEYWORDS else None
