from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
import pytest


_WORKER_SCRIPT = """
import sys
import os
import json
import asyncio
from pathlib import Path

from agent.runs.models import RunRecord, RunCheckpointRecord, RunToolCallRecord, RunApprovalRecord
from agent.runs.repository import InMemoryRunRepository
from agent.capabilities.approval_service import DurableApprovalService

async def main():
    storage_file = Path(sys.argv[1])
    run_id = sys.argv[2]
    tool_call_id = sys.argv[3]
    checkpoint_ref = sys.argv[4]

    data = json.loads(storage_file.read_text(encoding="utf-8"))

    # Tái tạo In-Memory repository từ persistent disk store
    repo = InMemoryRunRepository()
    
    run_data = data["runs"][run_id]
    await repo.create_run(RunRecord(**run_data))

    ckpt_data = data["checkpoints"][checkpoint_ref]
    await repo.save_checkpoint(RunCheckpointRecord(**ckpt_data))

    tc_data = data["tool_calls"][tool_call_id]
    await repo.save_tool_call(RunToolCallRecord(**tc_data))

    appr_data = data["approvals"][data["approval_id"]]
    await repo.create_approval(RunApprovalRecord(**appr_data))

    service = DurableApprovalService(repository=repo)

    # Thẩm định an toàn trước khi resume
    resume_result = await service.verify_and_prepare_resume(
        run_id=run_id,
        tool_call_id=tool_call_id,
        checkpoint_ref=checkpoint_ref,
        ambient_context={"tenant_status": "active", "principal_status": "active"},
    )

    if not resume_result.can_resume:
        print(f"RESUME_FAILED:{resume_result.reason}")
        sys.exit(1)

    # Thực thi tiếp sau khi approval hợp lệ
    data["runs"][run_id]["status"] = "COMPLETED"
    data["runs"][run_id]["resumed_by_process_pid"] = os.getpid()
    data["runs"][run_id]["verified_reviewer"] = resume_result.approval_record.reviewer
    storage_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    print(f"APPROVAL_RESUME_SUCCESS:{run_id}")

if __name__ == "__main__":
    asyncio.run(main())
"""


def test_cross_process_approval_survival_and_resume(tmp_path: Path):
    """Test approval tồn tại và resume được qua process thật độc lập theo Master Guide §18."""
    storage_file = tmp_path / "approval_durable_storage.json"
    worker_script_file = tmp_path / "approval_worker.py"
    worker_script_file.write_text(_WORKER_SCRIPT, encoding="utf-8")

    run_id = "run_proc_appr_88"
    tool_call_id = "call_payout_proc_88"
    checkpoint_ref = "ckpt_payout_proc_88"
    approval_id = f"appr_{run_id}_{tool_call_id}"

    # 1. Process chính mô phỏng trạng thái WAITING_APPROVAL đã lưu bền vững
    initial_storage = {
        "approval_id": approval_id,
        "runs": {
            run_id: {
                "run_id": run_id,
                "principal": "agent_alpha",
                "root_executable_id": "payout_agent",
                "status": "waiting_approval",
            }
        },
        "checkpoints": {
            checkpoint_ref: {
                "checkpoint_ref": checkpoint_ref,
                "run_id": run_id,
                "sequence_no": 1,
                "step_name": "payout_step",
                "serialized_state": {"amount": 50000, "vendor": "Acme Corp"},
            }
        },
        "tool_calls": {
            tool_call_id: {
                "tool_call_id": tool_call_id,
                "run_id": run_id,
                "checkpoint_ref": checkpoint_ref,
                "capability_id": "bank.payout.send",
                "payload_hash": "hash_payload_50000",
                "input_payload": {"amount": 50000, "vendor": "Acme Corp"},
                "status": "waiting_approval",
            }
        },
        "approvals": {
            approval_id: {
                "approval_id": approval_id,
                "run_id": run_id,
                "tool_call_id": tool_call_id,
                "checkpoint_ref": checkpoint_ref,
                "status": "approved",  # Reviewer đã phê duyệt
                "reviewer": "founder_ceo",
                "action": "bank.payout.send",
                "subject": "Payout $50,000 to Acme Corp",
                "requirement": {"kind": "role_approval", "role": "founder"},
                "evidence": {"signature": "founder_cryptographic_signature_v1"},
            }
        },
    }
    storage_file.write_text(json.dumps(initial_storage, indent=2), encoding="utf-8")

    # 2. Spawn Subprocess Python độc lập hoàn toàn để load approval và resume
    env = dict(os.environ)
    env["PYTHONPATH"] = f"{Path.cwd() / 'packages'}:{Path.cwd()}"

    proc = subprocess.run(
        [
            sys.executable,
            str(worker_script_file),
            str(storage_file),
            run_id,
            tool_call_id,
            checkpoint_ref,
        ],
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )

    assert proc.returncode == 0, f"Subprocess failed with stderr:\n{proc.stderr}"
    assert "APPROVAL_RESUME_SUCCESS:run_proc_appr_88" in proc.stdout

    # 3. Verify kết quả từ storage
    final_data = json.loads(storage_file.read_text(encoding="utf-8"))
    assert final_data["runs"][run_id]["status"] == "COMPLETED"
    assert final_data["runs"][run_id]["verified_reviewer"] == "founder_ceo"
    assert final_data["runs"][run_id]["resumed_by_process_pid"] != os.getpid()
