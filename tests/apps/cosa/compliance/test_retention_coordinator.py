from __future__ import annotations

from dataclasses import dataclass

import pytest

from apps.cosa.compliance.retention_coordinator import (
    RetentionCoordinator,
    RetentionTargets,
)


@dataclass
class FakeSubjectRequest:
    request_id: str
    subject_reference_hash: str
    legal_hold: bool = False


class FakeRightsClient:
    def __init__(self, request: FakeSubjectRequest) -> None:
        self.request = request

    async def get_request(self, request_id: str) -> FakeSubjectRequest:
        return self.request


class FakeLocator:
    def __init__(self, targets: RetentionTargets) -> None:
        self.targets = targets

    async def find_targets(self, subject_hash: str) -> RetentionTargets:
        return self.targets


class FakeObjectStore:
    def __init__(self) -> None:
        self.deleted_refs: list[str] = []

    async def delete_many(self, refs: list[str]) -> None:
        self.deleted_refs.extend(refs)


class FakeMemoryStore:
    def __init__(self) -> None:
        self.deleted_scope_ids: list[str] = []

    async def delete_subject_scope(self, scope_id: str) -> None:
        self.deleted_scope_ids.append(scope_id)


class FakeIndex:
    def __init__(self) -> None:
        self.deleted_document_ids: list[str] = []

    async def delete_documents(self, doc_ids: list[str]) -> None:
        self.deleted_document_ids.extend(doc_ids)


@pytest.mark.asyncio
async def test_retention_purges_object_memory_and_index_without_hold() -> None:
    delete_request_id = "req_123"
    request = FakeSubjectRequest(
        request_id=delete_request_id,
        subject_reference_hash="subject_hash_1",
        legal_hold=False,
    )
    targets = RetentionTargets(
        object_refs=["workspaces/1/source.pdf"],
        document_ids=["doc_1"],
    )

    fake_object_store = FakeObjectStore()
    fake_memory_store = FakeMemoryStore()
    fake_index = FakeIndex()

    coordinator = RetentionCoordinator(
        rights_client=FakeRightsClient(request),
        locator=FakeLocator(targets),
        object_store=fake_object_store,
        memory_service=fake_memory_store,
        knowledge_index=fake_index,
    )

    result = await coordinator.execute(delete_request_id)
    assert result.status == "PURGED"
    assert fake_object_store.deleted_refs == ["workspaces/1/source.pdf"]
    assert fake_memory_store.deleted_scope_ids == ["subject_hash_1"]
    assert fake_index.deleted_document_ids == ["doc_1"]


@pytest.mark.asyncio
async def test_retention_holds_when_legal_hold_active() -> None:
    delete_request_id = "req_hold"
    request = FakeSubjectRequest(
        request_id=delete_request_id,
        subject_reference_hash="subject_hash_1",
        legal_hold=True,
    )
    targets = RetentionTargets(
        object_refs=["workspaces/1/source.pdf"],
        document_ids=["doc_1"],
    )

    fake_object_store = FakeObjectStore()
    fake_memory_store = FakeMemoryStore()
    fake_index = FakeIndex()

    coordinator = RetentionCoordinator(
        rights_client=FakeRightsClient(request),
        locator=FakeLocator(targets),
        object_store=fake_object_store,
        memory_service=fake_memory_store,
        knowledge_index=fake_index,
    )

    result = await coordinator.execute(delete_request_id)
    assert result.status == "HELD"
    assert fake_object_store.deleted_refs == []
    assert fake_memory_store.deleted_scope_ids == []
    assert fake_index.deleted_document_ids == []
