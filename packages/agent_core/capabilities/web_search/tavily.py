from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Optional
from urllib.parse import urlparse
import httpx
from agent_core.capabilities.web_search.provider import WebSearchResult, sanitize_excerpt

logger = logging.getLogger(__name__)

__all__ = ["TavilyWebSearchProvider"]


def _domain_matches(url: str, domain_pattern: str) -> bool:
    """Check if URL host matches domain pattern (exact match or subdomain)."""
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        target = domain_pattern.strip().lower()
        if host == target or host.endswith("." + target):
            return True
        return False
    except Exception:
        return False


class TavilyWebSearchProvider:
    """Production adapter for Tavily search API."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.tavily.com",
        timeout: float = 10.0,
        max_retries: int = 3,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._client = client

    async def search(
        self,
        query: str,
        *,
        max_results: int = 5,
        allow_domains: Optional[list[str]] = None,
        deny_domains: Optional[list[str]] = None,
    ) -> list[WebSearchResult]:
        """Execute Tavily search query with domain filtering and retry handling."""
        if not query or not query.strip():
            return []

        payload: dict[str, Any] = {
            "api_key": self.api_key,
            "query": query.strip(),
            "max_results": max_results,
            "include_raw_content": True,
        }

        # If include_domains supported by Tavily
        if allow_domains:
            payload["include_domains"] = [d.strip() for d in allow_domains if d.strip()]
        if deny_domains:
            payload["exclude_domains"] = [d.strip() for d in deny_domains if d.strip()]

        url = f"{self.base_url}/search"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        should_close_client = False
        client = self._client
        if client is None:
            client = httpx.AsyncClient(timeout=self.timeout)
            should_close_client = True

        try:
            attempts = 0
            while attempts < self.max_retries:
                attempts += 1
                try:
                    response = await client.post(url, json=payload, headers=headers)
                    if response.status_code == 429:
                        retry_after_hdr = response.headers.get("Retry-After")
                        delay = 1.0 * (2 ** (attempts - 1))
                        if retry_after_hdr:
                            try:
                                delay = float(retry_after_hdr)
                            except ValueError:
                                pass
                        logger.warning(
                            f"Tavily API rate limited (429). Retrying in {delay:.2f}s (attempt {attempts}/{self.max_retries})."
                        )
                        if attempts < self.max_retries:
                            await asyncio.sleep(delay)
                            continue
                        response.raise_for_status()

                    if response.status_code >= 500:
                        delay = 1.0 * (2 ** (attempts - 1))
                        logger.warning(
                            f"Tavily API server error ({response.status_code}). Retrying in {delay:.2f}s (attempt {attempts}/{self.max_retries})."
                        )
                        if attempts < self.max_retries:
                            await asyncio.sleep(delay)
                            continue
                        response.raise_for_status()

                    response.raise_for_status()
                    data = response.json()
                    return self._parse_results(
                        data,
                        allow_domains=allow_domains,
                        deny_domains=deny_domains,
                        max_results=max_results,
                    )
                except httpx.TimeoutException as te:
                    logger.warning(f"Tavily API timeout on attempt {attempts}/{self.max_retries}: {te}")
                    if attempts < self.max_retries:
                        await asyncio.sleep(1.0 * attempts)
                        continue
                    raise RuntimeError(f"Tavily web search timed out after {self.timeout}s: {te}") from te
                except httpx.HTTPStatusError as hse:
                    if attempts >= self.max_retries:
                        raise RuntimeError(
                            f"Tavily web search failed with HTTP {hse.response.status_code}: {hse.response.text}"
                        ) from hse
        finally:
            if should_close_client:
                await client.aclose()

        return []

    def _parse_results(
        self,
        data: dict[str, Any],
        *,
        allow_domains: Optional[list[str]] = None,
        deny_domains: Optional[list[str]] = None,
        max_results: int = 5,
    ) -> list[WebSearchResult]:
        raw_items = data.get("results", [])
        if not isinstance(raw_items, list):
            return []

        parsed: list[WebSearchResult] = []
        now = datetime.now(timezone.utc)

        for item in raw_items:
            if not isinstance(item, dict):
                continue

            item_url = str(item.get("url") or "").strip()
            if not item_url:
                continue

            # Enforce allowlist / denylist post-filtering for extra safety
            if allow_domains:
                if not any(_domain_matches(item_url, d) for d in allow_domains):
                    continue

            if deny_domains:
                if any(_domain_matches(item_url, d) for d in deny_domains):
                    continue

            title = str(item.get("title") or "").strip() or "Untitled"
            snippet = str(item.get("content") or "").strip()
            raw_content = str(item.get("raw_content") or snippet)

            published_at: Optional[datetime] = None
            raw_pub_date = item.get("published_date")
            if raw_pub_date and isinstance(raw_pub_date, str):
                try:
                    published_at = datetime.fromisoformat(raw_pub_date.replace("Z", "+00:00"))
                except Exception:
                    published_at = None

            result = WebSearchResult(
                url=item_url,
                source_url=item_url,
                title=title,
                snippet=snippet,
                raw_excerpt=sanitize_excerpt(raw_content),
                published_at=published_at,
                provider="tavily",
                retrieved_at=now,
                untrusted=True,
            )
            parsed.append(result)
            if len(parsed) >= max_results:
                break

        return parsed
