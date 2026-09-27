"""Fallback model lúc chạy theo `WorkspaceModelPolicy.fallback_profile_ids`.

Route được bind lúc bắt đầu run (`run_core.run_kernel`), nhưng lỗi provider
(hết hạn mức, sai key, provider sập) chỉ xuất hiện khi gọi model. `FallbackModel`
bọc model chính: gọi lỗi thuộc nhóm cho phép thì chuyển sang profile kế tiếp
trong allowlist fallback của policy (chỉ profile ACTIVE, client dựng lazy). Lỗi
rate-limit không fallback ngay (thử lại muộn hơn mới đúng); lỗi khác (input,
tool, max turns) raise nguyên trạng.

Stream chỉ được fallback khi CHƯA phát event nào — đã phát một phần thì chuyển
model giữa chừng sẽ ghép 2 câu trả lời khác nhau, nên raise.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from typing import Any

from agents.models.interface import Model as SdkModel

from apps.cosa.worker.provider_errors import classify_run_error

__all__ = ["FALLBACK_ERROR_CODES", "FallbackModel", "ModelFactory"]

logger = logging.getLogger(__name__)

# Mã lỗi (apps/cosa/worker/provider_errors.py) cho phép chuyển model.
FALLBACK_ERROR_CODES = frozenset(
    {"provider_insufficient_balance", "provider_auth", "provider_unavailable"}
)

ModelFactory = Callable[[], Awaitable[SdkModel]]
FallbackCallback = Callable[[str, str, str], None]


def _error_code(exc: BaseException) -> str:
    # Tên class của litellm (AuthenticationError, ServiceUnavailableError,
    # APIConnectionError…) là tín hiệu chắc hơn message nên ghép cả hai.
    return classify_run_error(f"{type(exc).__name__}: {exc}").code


class FallbackModel(SdkModel):
    def __init__(
        self,
        primary: SdkModel,
        *,
        primary_profile_id: str,
        fallbacks: Sequence[tuple[str, ModelFactory]],
        on_fallback: FallbackCallback | None = None,
    ) -> None:
        self._primary_profile_id = primary_profile_id
        self._chain: list[tuple[str, ModelFactory]] = [
            (primary_profile_id, self._const(primary)),
            *fallbacks,
        ]
        self._models: dict[str, SdkModel] = {primary_profile_id: primary}
        self._on_fallback = on_fallback
        # Profile đang dùng — sau khi fallback, các lượt gọi sau trong cùng run
        # đi thẳng tới profile đã hoạt động thay vì thử lại primary hỏng.
        self._active_index = 0
        self.fallback_events: list[dict[str, str]] = []

    @staticmethod
    def _const(model: SdkModel) -> ModelFactory:
        async def _get() -> SdkModel:
            return model

        return _get

    async def _model_at(self, index: int) -> SdkModel | None:
        profile_id, factory = self._chain[index]
        if profile_id in self._models:
            return self._models[profile_id]
        try:
            model = await factory()
        except Exception as exc:
            logger.warning("fallback profile=%s unavailable: %s", profile_id, type(exc).__name__)
            return None
        self._models[profile_id] = model
        return model

    def _record(self, from_index: int, to_index: int, code: str) -> None:
        from_id = self._chain[from_index][0]
        to_id = self._chain[to_index][0]
        self.fallback_events.append({"from": from_id, "to": to_id, "reason": code})
        logger.warning("model.fallback from=%s to=%s reason=%s", from_id, to_id, code)
        if self._on_fallback is not None:
            self._on_fallback(from_id, to_id, code)

    async def _next_index(self, current: int, exc: BaseException) -> int | None:
        """Index profile kế tiếp dựng được, hoặc None nếu phải raise `exc`."""
        code = _error_code(exc)
        if code not in FALLBACK_ERROR_CODES:
            return None
        for nxt in range(current + 1, len(self._chain)):
            if await self._model_at(nxt) is not None:
                self._record(current, nxt, code)
                return nxt
        return None

    async def get_response(self, *args: Any, **kwargs: Any) -> Any:
        index = self._active_index
        while True:
            model = await self._model_at(index)
            if model is None:  # chỉ xảy ra với fallback; primary luôn có sẵn
                raise RuntimeError("fallback model unavailable")
            try:
                response = await model.get_response(*args, **kwargs)
            except Exception as exc:
                nxt = await self._next_index(index, exc)
                if nxt is None:
                    raise
                index = nxt
                continue
            self._active_index = index
            return response

    async def stream_response(self, *args: Any, **kwargs: Any) -> AsyncIterator[Any]:
        index = self._active_index
        while True:
            model = await self._model_at(index)
            if model is None:
                raise RuntimeError("fallback model unavailable")
            started = False
            try:
                async for event in model.stream_response(*args, **kwargs):
                    started = True
                    yield event
            except Exception as exc:
                nxt = None if started else await self._next_index(index, exc)
                if nxt is None:
                    raise
                index = nxt
                continue
            self._active_index = index
            return

    async def close(self) -> None:
        for model in self._models.values():
            close = getattr(model, "close", None)
            if close is not None:
                await close()
