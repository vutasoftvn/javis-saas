from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RetentionTargets:
    object_refs: list[str] = field(default_factory=list)
    document_ids: list[str] = field(default_factory=list)


@dataclass
class RetentionExecutionResult:
    status: str  # "PURGED", "HELD", "FAILED"
    tombstone_ref: str | None = None
    reasons: list[str] = field(default_factory=list)


class RetentionCoordinator:
    def __init__(
        self,
        rights_client: Any,
        locator: Any,
        object_store: Any,
        memory_service: Any,
        knowledge_index: Any,
    ) -> None:
        self._rights_client = rights_client
        self._locator = locator
        self._object_store = object_store
        self._memory_service = memory_service
        self._knowledge_index = knowledge_index

    async def execute(self, request_id: str) -> RetentionExecutionResult:
        request = await self._rights_client.get_request(request_id)
        subject_hash = request.subject_reference_hash
        targets = await self._locator.find_targets(subject_hash)

        if getattr(request, "legal_hold", False):
            tombstone_ref = f"tombstone_hold_{request_id}"
            return RetentionExecutionResult(
                status="HELD",
                tombstone_ref=tombstone_ref,
                reasons=["LEGAL_HOLD_ACTIVE"],
            )

        # P1.2 — trước đây các bước xoá này bị hasattr-guard: 1 backend thiếu
        # đúng method (chưa implement, refactor, wiring sai) sẽ ÂM THẦM bỏ
        # qua bước xoá đó mà result vẫn trả status="PURGED" — báo cáo SAI cho
        # 1 yêu cầu xoá dữ liệu chủ thể (right-to-erasure). Không hasattr-
        # guard optional interface cho dependency BẮT BUỘC (constructor
        # param, không phải `| None`): nếu backend không hỗ trợ, để
        # AttributeError raise thẳng thay vì báo "đã xoá" trong khi chưa xoá.
        if targets.object_refs:
            await self._object_store.delete_many(targets.object_refs)

        await self._memory_service.delete_subject_scope(subject_hash)

        if targets.document_ids:
            await self._knowledge_index.delete_documents(targets.document_ids)

        tombstone_ref = f"tombstone_purged_{request_id}"
        return RetentionExecutionResult(
            status="PURGED",
            tombstone_ref=tombstone_ref,
        )
