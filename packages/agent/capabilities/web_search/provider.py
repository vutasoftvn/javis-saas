from __future__ import annotations

import logging
import os
import re
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

__all__ = [
    "NullWebSearchProvider",
    "WebSearchProvider",
    "WebSearchResult",
    "build_web_search_provider",
    "sanitize_excerpt",
]


def sanitize_excerpt(text: str, max_length: int = 4096) -> str:
    """Sanitize raw excerpt by stripping scripts, styles, HTML tags, and truncating to max_length."""
    if not text:
        return ""
    # Strip script and style blocks
    cleaned = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # Strip HTML tags
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    # Normalize whitespaces
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length] + "..."
    return cleaned


class WebSearchResult(BaseModel):
    """Structured result item from web search with provenance and safety tags."""

    url: str
    title: str
    snippet: str = ""
    published_at: datetime | None = None
    raw_excerpt: str = ""
    provider: str = "tavily"
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    untrusted: bool = True
    source_url: str = ""

    def __init__(self, **data: Any) -> None:
        if "source_url" not in data and "url" in data:
            data["source_url"] = data["url"]
        if data.get("raw_excerpt"):
            data["raw_excerpt"] = sanitize_excerpt(data["raw_excerpt"])
        super().__init__(**data)


@runtime_checkable
class WebSearchProvider(Protocol):
    """Abstract protocol for web search provider implementations."""

    async def search(
        self,
        query: str,
        *,
        max_results: int = 5,
        allow_domains: list[str] | None = None,
        deny_domains: list[str] | None = None,
    ) -> list[WebSearchResult]:
        """Execute a search query and return normalized results."""
        ...


class NullWebSearchProvider:
    """Fallback provider returning empty results."""

    async def search(
        self,
        query: str,
        *,
        max_results: int = 5,
        allow_domains: list[str] | None = None,
        deny_domains: list[str] | None = None,
    ) -> list[WebSearchResult]:
        return []


def _is_staging_or_prod() -> bool:
    env = (
        os.environ.get("APP_ENV")
        or os.environ.get("NODE_ENV")
        or os.environ.get("ENVIRONMENT")
        or "development"
    ).lower()
    return env in ("staging", "prod", "production")


def build_web_search_provider(
    *,
    provider_type: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    timeout: float = 10.0,
) -> WebSearchProvider:
    """Factory to construct the configured WebSearchProvider.

    Reads WEB_SEARCH_PROVIDER environment variable ('tavily' default).
    Fails fast in staging/production if required API key is missing.
    In development/test, warns and falls back to NullWebSearchProvider if key is omitted.
    """
    provider_name = (
        (provider_type or os.environ.get("WEB_SEARCH_PROVIDER", "tavily")).strip().lower()
    )

    if provider_name in ("null", "none", "disabled"):
        return NullWebSearchProvider()

    if provider_name == "tavily":
        resolved_key = api_key or os.environ.get("TAVILY_API_KEY")
        if not resolved_key:
            if _is_staging_or_prod():
                raise RuntimeError(
                    "TAVILY_API_KEY is required in staging/production environments when WEB_SEARCH_PROVIDER=tavily"
                )
            logger.warning(
                "TAVILY_API_KEY not configured in development environment. "
                "Falling back to NullWebSearchProvider."
            )
            return NullWebSearchProvider()

        from agent.capabilities.web_search.tavily import TavilyWebSearchProvider

        return TavilyWebSearchProvider(
            api_key=resolved_key,
            base_url=base_url or os.environ.get("TAVILY_BASE_URL", "https://api.tavily.com"),
            timeout=timeout,
        )

    raise ValueError(
        f"Unknown web search provider: '{provider_name}' — supported: 'tavily', 'null'"
    )
