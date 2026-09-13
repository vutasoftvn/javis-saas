from __future__ import annotations

from typing import Any

import pytest

from apps.cosa.capabilities.ai_governance_read import create_ai_governance_read_handler


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
    "revision": 2,
    "status": "CONFIRMED",
    "snapshotRef": "sha256:abc123",
    "policy": [{"id": "cosa.model_policy.default", "version": "1.0.0", "definitionHash": "deadbeef"}],
    "evaluators": [{"id": "eval.default", "version": "1.0.0", "definitionHash": "beadfeed"}],
    "observedAt": "2026-09-12T00:00:00.000Z",
    "riskSignals": [{"category": "POLICY_DRIFT", "severity": "LOW"}],
    "sourceRefs": [{"sourceRef": "source-1", "classification": "INTERNAL"}],
    # Trường lạ không thuộc output_schema — phải bị lọc bỏ, không passthrough.
    "signature": "sk-should-never-leak",
    "rawPrompt": "should never leak either",
}


@pytest.mark.asyncio
async def test_handler_uses_ctx_project_and_workspace_scope_with_real_dict_ctx() -> None:
    """Pipeline thật luôn truyền ctx dưới dạng dict thuần (không phải object) —
    test này dùng đúng dict thật, không phải fake object-shaped ctx, để chứng
    minh hành vi khớp thực tế runtime."""
    fake_client = _FakeCompanyServiceClient(_CANNED_SNAPSHOT)
    handler = create_ai_governance_read_handler(fake_client)
    ctx: dict[str, Any] = {"project_id": "project-A", "workspace_id": "workspace-1"}

    result = await handler({"project_id": "project-A"}, ctx)

    assert len(fake_client.calls) == 1
    call = fake_client.calls[0]
    assert call["path"] == "/operations/projects/project-A/ai-governance-dossier"
    assert call["headers"] == {"X-Workspace-Id": "workspace-1"}

    assert result == {
        "dossierId": "dossier-123",
        "revision": 2,
        "status": "CONFIRMED",
        "snapshotRef": "sha256:abc123",
        "policy": [{"id": "cosa.model_policy.default", "version": "1.0.0", "definitionHash": "deadbeef"}],
        "evaluators": [{"id": "eval.default", "version": "1.0.0", "definitionHash": "beadfeed"}],
        "observedAt": "2026-09-12T00:00:00.000Z",
        "riskSignals": [{"category": "POLICY_DRIFT", "severity": "LOW"}],
        "sourceRefs": [{"sourceRef": "source-1", "classification": "INTERNAL"}],
    }
    assert "signature" not in result
    assert "rawPrompt" not in result


@pytest.mark.asyncio
async def test_handler_rejects_args_project_id_mismatching_dict_ctx_scope() -> None:
    """dict-ctx-wins: ctx["project_id"] ("A") luôn thắng — model không được đọc
    dossier của Project khác ("B") bằng cách truyền args["project_id"] khác
    scope run, kể cả khi ctx là dict thuần (đúng shape thực tế của pipeline)."""
    fake_client = _FakeCompanyServiceClient(_CANNED_SNAPSHOT)
    handler = create_ai_governance_read_handler(fake_client)
    ctx: dict[str, Any] = {"project_id": "project-A", "workspace_id": "workspace-1"}

    with pytest.raises(ValueError, match="project_id trong args không khớp"):
        await handler({"project_id": "project-B"}, ctx)

    # Quan trọng nhất: không được thực hiện bất kỳ lời gọi Company nào tới
    # scope của Project B — request bị chặn trước khi đọc dữ liệu.
    assert fake_client.calls == []


@pytest.mark.asyncio
async def test_handler_rejects_args_workspace_id_override_of_dict_ctx() -> None:
    """workspace_id luôn lấy từ dict ctx — args không có quyền ghi đè, kể cả khi
    args cố tình truyền workspace_id khác."""
    fake_client = _FakeCompanyServiceClient(_CANNED_SNAPSHOT)
    handler = create_ai_governance_read_handler(fake_client)
    ctx: dict[str, Any] = {"project_id": "project-A", "workspace_id": "workspace-1"}

    result = await handler(
        {"project_id": "project-A", "workspace_id": "workspace-EVIL"}, ctx
    )

    call = fake_client.calls[0]
    assert call["headers"] == {"X-Workspace-Id": "workspace-1"}
    assert result["dossierId"] == "dossier-123"


@pytest.mark.asyncio
async def test_handler_raises_when_dict_ctx_missing_project_id_and_no_args_fallback() -> None:
    fake_client = _FakeCompanyServiceClient(_CANNED_SNAPSHOT)
    handler = create_ai_governance_read_handler(fake_client)
    ctx: dict[str, Any] = {"workspace_id": "workspace-1"}

    with pytest.raises(ValueError, match="thiếu project_id"):
        await handler({}, ctx)


@pytest.mark.asyncio
async def test_handler_raises_when_dict_ctx_missing_workspace_id() -> None:
    fake_client = _FakeCompanyServiceClient(_CANNED_SNAPSHOT)
    handler = create_ai_governance_read_handler(fake_client)
    ctx: dict[str, Any] = {"project_id": "project-A"}

    with pytest.raises(ValueError, match="thiếu workspace_id"):
        await handler({"project_id": "project-A"}, ctx)
