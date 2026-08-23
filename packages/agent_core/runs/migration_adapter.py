from __future__ import annotations

from typing import Any, Optional
from datetime import datetime, timezone
from sqlalchemy import text

from agent_core.runs.models import (
    RunApprovalRecord,
    RunCheckpointRecord,
    RunEventRecord,
    RunRecord,
    RunToolCallRecord,
)
from agent_core.runs.repository import RunRepository


class GovernanceToCanonicalAdapter:
    """Adapter chuyển đổi dữ liệu lịch sử từ schema prototype `agent_core_governance.*`
    sang 5 bảng canonical `agent_core.*` theo Master Guide §12.
    
    Quy tắc Mapping:
    1. `agent_core_governance.spec_resolution_manifest_entries`
       -> Đưa vào `manifest_snapshot` của `agent_core.run_checkpoints`.
    2. `agent_core_governance.invocation_governance_state`
       -> `governance_state` của `agent_core.run_tool_calls`.
    3. `agent_core_governance.invocation_governance_history`
       -> `agent_core.run_events` (event_type: 'policy.evaluated').
    4. `agent_core_governance.approval_evidence`
       -> `agent_core.approvals` (với evidence object).
    """

    def __init__(self, db_session_factory: Any, target_repo: RunRepository) -> None:
        self._session_factory = db_session_factory
        self._target_repo = target_repo

    async def migrate_run(self, run_id: str) -> dict[str, int]:
        counts = {"manifest_entries": 0, "tool_calls": 0, "events": 0, "approvals": 0}

        async with self._session_factory() as session:
            # 1. Đọc manifest entries
            res_manifest = await session.execute(
                text(
                    """
                    SELECT spec_kind, spec_id, spec_version, definition_hash, pinned_at
                    FROM agent_core_governance.spec_resolution_manifest_entries
                    WHERE run_id = :run_id
                    """
                ),
                {"run_id": run_id},
            )
            manifest_rows = res_manifest.mappings().all()
            manifest_snapshot = {
                "entries": [
                    {
                        "spec_kind": r["spec_kind"],
                        "spec_id": r["spec_id"],
                        "spec_version": r["spec_version"],
                        "definition_hash": r["definition_hash"],
                    }
                    for r in manifest_rows
                ]
            }
            counts["manifest_entries"] = len(manifest_rows)

            # 2. Đọc governance states
            res_states = await session.execute(
                text(
                    """
                    SELECT tool_call_id, accumulated_outcome, accumulated_requirement,
                           version_no, last_updated_at
                    FROM agent_core_governance.invocation_governance_state
                    WHERE run_id = :run_id
                    """
                ),
                {"run_id": run_id},
            )
            state_rows = res_states.mappings().all()

            for s in state_rows:
                tool_call_id = s["tool_call_id"]
                capability_id = tool_call_id.split(":")[-1] if ":" in tool_call_id else tool_call_id
                
                # Check / Tạo ToolCallRecord
                tc = RunToolCallRecord(
                    tool_call_id=tool_call_id,
                    run_id=run_id,
                    capability_id=capability_id,
                    payload_hash="legacy_migrated",
                    status="completed" if s["accumulated_outcome"] == "ALLOW" else "waiting_approval",
                    governance_state={
                        "outcome": s["accumulated_outcome"],
                        "requirement": s["accumulated_requirement"],
                        "version_no": s["version_no"],
                    },
                )
                await self._target_repo.save_tool_call(tc)
                counts["tool_calls"] += 1

            # 3. Đọc governance history -> run_events
            res_history = await session.execute(
                text(
                    """
                    SELECT tool_call_id, observed_outcome, observed_requirement,
                           source, observed_at, sequence_no
                    FROM agent_core_governance.invocation_governance_history
                    WHERE run_id = :run_id
                    ORDER BY sequence_no ASC
                    """
                ),
                {"run_id": run_id},
            )
            history_rows = res_history.mappings().all()
            for h in history_rows:
                ev = RunEventRecord(
                    run_id=run_id,
                    event_type="policy.evaluated",
                    payload={
                        "tool_call_id": h["tool_call_id"],
                        "outcome": h["observed_outcome"],
                        "requirement": h["observed_requirement"],
                        "source": h["source"],
                    },
                )
                await self._target_repo.append_event(ev)
                counts["events"] += 1

            # 4. Đọc evidence -> approvals
            for s in state_rows:
                tool_call_id = s["tool_call_id"]
                res_evidence = await session.execute(
                    text(
                        """
                        SELECT id, approver, scope, decided_at, valid_until
                        FROM agent_core_governance.approval_evidence
                        WHERE scope = :scope
                        """
                    ),
                    {"scope": tool_call_id},
                )
                for ev_row in res_evidence.mappings().all():
                    appr = RunApprovalRecord(
                        approval_id=ev_row["id"],
                        run_id=run_id,
                        tool_call_id=tool_call_id,
                        checkpoint_ref=f"ckpt_migrated_{run_id}",
                        status="approved",
                        reviewer=ev_row["approver"],
                        evidence={
                            "approver": ev_row["approver"],
                            "scope": ev_row["scope"],
                            "decided_at": ev_row["decided_at"],
                            "valid_until": ev_row["valid_until"],
                        },
                    )
                    await self._target_repo.create_approval(appr)
                    counts["approvals"] += 1

        return counts
