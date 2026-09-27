"""Sổ cái usage LLM + kiểm soát ngân sách theo workspace/profile (review 2026-09-27, G-3).

- `UsageLedger`: ghi token/chi phí mỗi lần kernel chạy xong theo profile THẬT
  đã dùng (route, kể cả fallback) — không theo `spec.model_policy`.
- `check_usage_budget`: chạy TRƯỚC khi dựng model client. Chặn khi:
  * workspace vượt quota token tháng (`COSA_WORKSPACE_MONTHLY_TOKEN_QUOTA`,
    không đặt = không giới hạn);
  * profile có `budget_usd_limit` và chi phí từ đầu tháng đã chạm ngưỡng.
  Profile có budget nhưng model không có giá (LiteLLM không biết) thì fail
  closed — không thể enforce ngân sách tiền cho thứ không định giá được.

Chi phí là ƯỚC TÍNH theo bảng giá LiteLLM (`litellm.cost_per_token`), đủ cho
quota/cảnh báo; không phải số hoá đơn của nhà cung cấp.
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Protocol

from pydantic import BaseModel, Field
from sqlalchemy import text

from apps.cosa.models.contracts import ProviderType, ResolvedModelRoute

__all__ = [
    "InMemoryUsageLedger",
    "PostgresUsageLedger",
    "UsageBudgetExceeded",
    "UsageEntry",
    "UsageLedger",
    "check_usage_budget",
    "estimate_cost_usd",
    "month_start",
    "usage_from_result",
]

logger = logging.getLogger(__name__)

_LITELLM_PREFIX: dict[ProviderType, str] = {
    ProviderType.ANTHROPIC_API: "anthropic",
    ProviderType.OPENAI_API: "openai",
    ProviderType.OPENROUTER_API: "openrouter",
    ProviderType.DEEPSEEK_API: "deepseek",
}


class UsageEntry(BaseModel):
    usage_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workspace_id: str
    project_id: str | None = None
    run_id: str
    agent_spec_id: str | None = None
    profile_id: str
    provider_type: str | None = None
    model_id: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: Decimal | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class UsageBudgetExceeded(Exception):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


class UsageLedger(Protocol):
    async def record(self, entry: UsageEntry) -> UsageEntry: ...

    async def total_tokens(self, workspace_id: str, since: datetime) -> int: ...

    async def total_cost_usd(
        self, workspace_id: str, since: datetime, profile_id: str | None = None
    ) -> Decimal: ...


class InMemoryUsageLedger:
    def __init__(self) -> None:
        self.entries: list[UsageEntry] = []

    async def record(self, entry: UsageEntry) -> UsageEntry:
        self.entries.append(entry)
        return entry

    def _scope(self, workspace_id: str, since: datetime, profile_id: str | None):
        return [
            e
            for e in self.entries
            if e.workspace_id == workspace_id
            and e.created_at >= since
            and (profile_id is None or e.profile_id == profile_id)
        ]

    async def total_tokens(self, workspace_id: str, since: datetime) -> int:
        return sum(
            e.prompt_tokens + e.completion_tokens for e in self._scope(workspace_id, since, None)
        )

    async def total_cost_usd(
        self, workspace_id: str, since: datetime, profile_id: str | None = None
    ) -> Decimal:
        return sum(
            (e.cost_usd or Decimal(0) for e in self._scope(workspace_id, since, profile_id)),
            Decimal(0),
        )


class PostgresUsageLedger:
    def __init__(self, session_factory: Any) -> None:
        if session_factory is None:
            raise ValueError("PostgresUsageLedger requires a session_factory")
        self._session_factory = session_factory

    async def record(self, entry: UsageEntry) -> UsageEntry:
        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO models.run_usage (
                        usage_id, workspace_id, project_id, run_id, agent_spec_id, profile_id,
                        provider_type, model_id, prompt_tokens, completion_tokens, cost_usd,
                        created_at
                    ) VALUES (
                        :usage_id, :workspace_id, :project_id, :run_id, :agent_spec_id,
                        :profile_id, :provider_type, :model_id, :prompt_tokens,
                        :completion_tokens, :cost_usd, :created_at
                    )
                    """
                ),
                entry.model_dump(),
            )
            await session.commit()
        return entry

    async def total_tokens(self, workspace_id: str, since: datetime) -> int:
        async with self._session_factory() as session:
            res = await session.execute(
                text(
                    """
                    SELECT COALESCE(SUM(prompt_tokens + completion_tokens), 0) AS n
                    FROM models.run_usage
                    WHERE workspace_id = :workspace_id AND created_at >= :since
                    """
                ),
                {"workspace_id": workspace_id, "since": since},
            )
            return int(res.scalar_one())

    async def total_cost_usd(
        self, workspace_id: str, since: datetime, profile_id: str | None = None
    ) -> Decimal:
        async with self._session_factory() as session:
            res = await session.execute(
                text(
                    """
                    SELECT COALESCE(SUM(cost_usd), 0) AS c
                    FROM models.run_usage
                    WHERE workspace_id = :workspace_id AND created_at >= :since
                      AND (CAST(:profile_id AS text) IS NULL OR profile_id = :profile_id)
                    """
                ),
                {"workspace_id": workspace_id, "since": since, "profile_id": profile_id},
            )
            return Decimal(res.scalar_one())


def month_start(now: datetime | None = None) -> datetime:
    now = now or datetime.now(UTC)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def estimate_cost_usd(
    provider_type: ProviderType | str | None,
    model_id: str | None,
    prompt_tokens: int,
    completion_tokens: int,
) -> Decimal | None:
    """Chi phí ước tính theo bảng giá LiteLLM; None nếu không định giá được."""
    if not model_id:
        return None
    try:
        prefix = _LITELLM_PREFIX.get(ProviderType(provider_type)) if provider_type else None
    except ValueError:
        prefix = None
    candidates = [f"{prefix}/{model_id}"] if prefix else []
    candidates.append(model_id)
    try:
        import litellm
    except ImportError:  # pragma: no cover - litellm là dependency chuẩn
        return None
    for name in candidates:
        try:
            p_cost, c_cost = litellm.cost_per_token(
                model=name, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens
            )
        except Exception:
            continue
        return Decimal(str(p_cost)) + Decimal(str(c_cost))
    return None


def usage_from_result(result: Any) -> tuple[int, int]:
    usage = getattr(result, "usage", None) or {}
    if not isinstance(usage, dict):
        return 0, 0
    p = usage.get("prompt_tokens") or usage.get("input_tokens") or 0
    c = usage.get("completion_tokens") or usage.get("output_tokens") or 0
    try:
        return int(p), int(c)
    except (TypeError, ValueError):
        return 0, 0


def _workspace_token_quota() -> int | None:
    raw = os.environ.get("COSA_WORKSPACE_MONTHLY_TOKEN_QUOTA", "").strip()
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError:
        logger.error("COSA_WORKSPACE_MONTHLY_TOKEN_QUOTA không phải số nguyên: %r", raw)
        # Cấu hình sai không được biến thành "không giới hạn" âm thầm.
        return 0
    return max(value, 0)


async def check_usage_budget(
    ledger: UsageLedger | None,
    route: ResolvedModelRoute,
    *,
    profile_budget_usd: float | None,
    now: datetime | None = None,
) -> None:
    """Raise `UsageBudgetExceeded` nếu run mới sẽ vượt quota/ngân sách."""
    quota = _workspace_token_quota()
    budget = Decimal(str(profile_budget_usd)) if profile_budget_usd is not None else None
    if ledger is None:
        if quota is not None or budget is not None:
            # Có giới hạn mà không có sổ cái thì không kiểm được — fail closed.
            raise UsageBudgetExceeded(
                "usage_ledger_unavailable", "usage ledger not configured but a limit is set"
            )
        return
    since = month_start(now)
    if quota is not None:
        used = await ledger.total_tokens(route.workspace_id, since)
        if used >= quota:
            raise UsageBudgetExceeded(
                "workspace_token_quota_exceeded",
                f"workspace {route.workspace_id} used {used} tokens this month (quota {quota})",
            )
    if budget is not None:
        if estimate_cost_usd(route.provider_type, route.model_id, 1000, 1000) is None:
            raise UsageBudgetExceeded(
                "profile_budget_unpriced_model",
                f"profile {route.profile_id} has budget_usd_limit but model "
                f"{route.model_id} has no known price",
            )
        spent = await ledger.total_cost_usd(route.workspace_id, since, route.profile_id)
        if spent >= budget:
            raise UsageBudgetExceeded(
                "profile_budget_exceeded",
                f"profile {route.profile_id} spent ${spent} this month (limit ${budget})",
            )
