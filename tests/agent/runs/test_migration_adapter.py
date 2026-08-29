from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from agent.runs.migration_adapter import GovernanceToCanonicalAdapter
from agent.runs.repository import InMemoryRunRepository


@pytest.mark.asyncio
async def test_migration_adapter_maps_legacy_tables_to_canonical_records():
    # Giả lập database session trả về dữ liệu mẫu từ 4 bảng agent_governance.*
    mock_session = AsyncMock()

    manifest_rows = [
        MagicMock(
            __getitem__=lambda self, k: {
                "spec_kind": "agent",
                "spec_id": "finance_agent",
                "spec_version": "1.0.0",
                "definition_hash": "hash_agent_123",
                "pinned_at": "2026-08-23T10:00:00Z",
            }[k]
        )
    ]

    state_rows = [
        MagicMock(
            __getitem__=lambda self, k: {
                "tool_call_id": "run_mig_1:finance.invoice.send",
                "accumulated_outcome": "REQUIRE_APPROVAL",
                "accumulated_requirement": {"kind": "role_approval", "role": "founder"},
                "version_no": 1,
                "last_updated_at": "2026-08-23T10:05:00Z",
            }[k]
        )
    ]

    history_rows = [
        MagicMock(
            __getitem__=lambda self, k: {
                "tool_call_id": "run_mig_1:finance.invoice.send",
                "observed_outcome": "REQUIRE_APPROVAL",
                "observed_requirement": {"kind": "role_approval", "role": "founder"},
                "source": "ToolCallStep",
                "observed_at": "2026-08-23T10:05:00Z",
                "sequence_no": 1,
            }[k]
        )
    ]

    evidence_rows = [
        MagicMock(
            __getitem__=lambda self, k: {
                "id": "ev_mig_99",
                "approver": "founder_1",
                "scope": "run_mig_1:finance.invoice.send",
                "decided_at": "2026-08-23T10:10:00Z",
                "valid_until": None,
            }[k]
        )
    ]

    # Cấu hình mock execute trả về tương ứng từng câu query
    async def mock_execute(statement, params=None):
        stmt_str = str(statement)
        mock_res = MagicMock()
        if "spec_resolution_manifest_entries" in stmt_str:
            mock_res.mappings.return_value.all.return_value = manifest_rows
        elif "invocation_governance_state" in stmt_str:
            mock_res.mappings.return_value.all.return_value = state_rows
        elif "invocation_governance_history" in stmt_str:
            mock_res.mappings.return_value.all.return_value = history_rows
        elif "approval_evidence" in stmt_str:
            mock_res.mappings.return_value.all.return_value = evidence_rows
        else:
            mock_res.mappings.return_value.all.return_value = []
        return mock_res

    mock_session.execute = mock_execute

    class MockSessionFactory:
        def __call__(self):
            class SessionContext:
                async def __aenter__(self):
                    return mock_session

                async def __aexit__(self, *args):
                    pass

            return SessionContext()

    target_repo = InMemoryRunRepository()
    adapter = GovernanceToCanonicalAdapter(
        db_session_factory=MockSessionFactory(),
        target_repo=target_repo,
    )

    counts = await adapter.migrate_run("run_mig_1")

    assert counts["manifest_entries"] == 1
    assert counts["tool_calls"] == 1
    assert counts["events"] == 1
    assert counts["approvals"] == 1

    # Kiểm tra tool_call được tạo
    tc = await target_repo.get_tool_call("run_mig_1:finance.invoice.send")
    assert tc is not None
    assert tc.capability_id == "finance.invoice.send"
    assert tc.governance_state["outcome"] == "REQUIRE_APPROVAL"

    # Kiểm tra event được tạo
    events = await target_repo.list_events("run_mig_1")
    assert len(events) == 1
    assert events[0].event_type == "policy.evaluated"

    # Kiểm tra approval được tạo
    appr = await target_repo.get_approval("ev_mig_99")
    assert appr is not None
    assert appr.reviewer == "founder_1"
    assert appr.status == "approved"
