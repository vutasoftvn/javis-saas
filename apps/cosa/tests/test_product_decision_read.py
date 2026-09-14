from __future__ import annotations

from typing import Any

import pytest

from apps.cosa.capabilities.product_decision_read import create_product_decision_read_handler


class _FakeCompanyServiceClient:
    """Stub tối giản cho CompanyServiceClient — chỉ ghi lại lời gọi .get() và trả
    về snapshot đã canned sẵn, không thực hiện HTTP thật."""

    def __init__(self, snapshot: dict[str, Any]) -> None:
        self._snapshot = snapshot
        self.calls: list[dict[str, Any]] = []

    async def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        self.calls.append({"path": path, "params": params, "headers": headers})
        return self._snapshot


_CANNED_SNAPSHOT = {
    "dossierId": "dossier-123",
    "revision": 3,
    "evidenceRefs": ["evidence-1", "evidence-2"],
    "assumptions": ["assumption-1"],
    "status": "FOUNDER_REVIEWED",
    # Trường lạ không thuộc output_schema — phải bị lọc bỏ, không passthrough.
    "internalRawInterviewText": "should never leak",
    "rawEvidenceBlob": {"secret": "should never leak"},
}


@pytest.mark.asyncio
async def test_handler_uses_ctx_project_and_workspace_scope() -> None:
    fake_client = _FakeCompanyServiceClient(_CANNED_SNAPSHOT)
    handler = create_product_decision_read_handler(fake_client)
    ctx: dict[str, Any] = {"project_id": "project-A", "workspace_id": "workspace-1"}

    result = await handler({"project_id": "project-A"}, ctx)

    assert len(fake_client.calls) == 1
    call = fake_client.calls[0]
    assert call["path"] == "/operations/projects/project-A/product-decision-dossier"
    assert call["headers"] == {"X-Workspace-Id": "workspace-1"}

    assert result == {
        "dossierId": "dossier-123",
        "revision": 3,
        "evidenceRefs": ["evidence-1", "evidence-2"],
        "assumptions": ["assumption-1"],
        "status": "FOUNDER_REVIEWED",
    }
    assert "internalRawInterviewText" not in result
    assert "rawEvidenceBlob" not in result


@pytest.mark.asyncio
async def test_handler_rejects_args_project_id_mismatching_ctx_scope() -> None:
    """Fix 2: ctx.project_id ("A") luôn thắng — model không được đọc dossier
    của Project khác ("B") bằng cách truyền args["project_id"] khác scope run.
    """
    fake_client = _FakeCompanyServiceClient(_CANNED_SNAPSHOT)
    handler = create_product_decision_read_handler(fake_client)
    ctx: dict[str, Any] = {"project_id": "project-A", "workspace_id": "workspace-1"}

    with pytest.raises(ValueError, match="project_id trong args không khớp"):
        await handler({"project_id": "project-B"}, ctx)

    # Quan trọng nhất: không được thực hiện bất kỳ lời gọi Company nào tới
    # scope của Project B — request bị chặn trước khi đọc dữ liệu.
    assert fake_client.calls == []


@pytest.mark.asyncio
async def test_handler_rejects_args_workspace_id_override_of_ctx() -> None:
    """workspace_id luôn lấy từ ctx — args không có quyền ghi đè, kể cả khi
    args cố tình truyền workspace_id khác."""
    fake_client = _FakeCompanyServiceClient(_CANNED_SNAPSHOT)
    handler = create_product_decision_read_handler(fake_client)
    ctx: dict[str, Any] = {"project_id": "project-A", "workspace_id": "workspace-1"}

    result = await handler({"project_id": "project-A", "workspace_id": "workspace-EVIL"}, ctx)

    call = fake_client.calls[0]
    assert call["headers"] == {"X-Workspace-Id": "workspace-1"}
    assert result["dossierId"] == "dossier-123"


@pytest.mark.asyncio
async def test_handler_raises_when_ctx_missing_project_id_and_no_args_fallback() -> None:
    fake_client = _FakeCompanyServiceClient(_CANNED_SNAPSHOT)
    handler = create_product_decision_read_handler(fake_client)
    ctx: dict[str, Any] = {"workspace_id": "workspace-1"}

    with pytest.raises(ValueError, match="thiếu project_id"):
        await handler({}, ctx)


@pytest.mark.asyncio
async def test_handler_raises_when_ctx_missing_workspace_id() -> None:
    fake_client = _FakeCompanyServiceClient(_CANNED_SNAPSHOT)
    handler = create_product_decision_read_handler(fake_client)
    ctx: dict[str, Any] = {"project_id": "project-A"}

    with pytest.raises(ValueError, match="thiếu workspace_id"):
        await handler({"project_id": "project-A"}, ctx)
