from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
import pytest


# Script thực thi trong Subprocess độc lập hoàn toàn
_WORKER_SCRIPT = """
import sys
import json
import asyncio
from pathlib import Path

from agent_core.workflows.engine import WorkflowEngine
from agent_core.workflows.schema import WorkflowSpec, WorkflowStepSpec, StepType
from agent_core.workflows.models import Workflow, WorkflowStatus, StepStatus
from agent_core.workflows.steps import DeterministicStep

async def main():
    storage_file = Path(sys.argv[1])
    run_id = sys.argv[2]
    
    data = json.loads(storage_file.read_text(encoding="utf-8"))
    run_info = data["runs"][run_id]
    
    # Đọc checkpoint đã lưu từ process trước
    checkpoints = data["checkpoints"].get(run_id, {})
    latest_step = list(checkpoints.keys())[-1]
    saved_state = checkpoints[latest_step]
    
    # Tái tạo Workflow instance từ checkpoint
    workflow = Workflow(
        id=run_id,
        name="multi_step_process_flow",
        status=WorkflowStatus.RUNNING,
        completed_steps=run_info["completed_steps"],
        checkpoints=checkpoints,
        state=saved_state,
    )
    
    # Định nghĩa các step
    async def step1_fetch(state):
        data["step1_executions"] = data.get("step1_executions", 0) + 1
        return {"fetched_items": [10, 20, 30]}

    async def step2_compute(state):
        data["step2_executions"] = data.get("step2_executions", 0) + 1
        total = sum(state.get("fetched_items", []))
        return {"total_sum": total}

    async def step3_finalize(state):
        data["step3_executions"] = data.get("step3_executions", 0) + 1
        return {"status": "SUCCESS", "report_id": f"rep_{state.get('total_sum')}"}

    custom_builders = {
        "step_1": lambda s: DeterministicStep("step_1", step1_fetch),
        "step_2": lambda s: DeterministicStep("step_2", step2_compute),
        "step_3": lambda s: DeterministicStep("step_3", step3_finalize),
    }

    spec = WorkflowSpec(
        id="multi_step_process_flow",
        steps=[
            WorkflowStepSpec(id="step_1", type=StepType.DETERMINISTIC),
            WorkflowStepSpec(id="step_2", type=StepType.DETERMINISTIC, depends_on=["step_1"]),
            WorkflowStepSpec(id="step_3", type=StepType.DETERMINISTIC, depends_on=["step_2"]),
        ],
    )

    engine = WorkflowEngine()
    resumed = await engine.execute_spec(spec, initial_state={}, custom_step_builders=custom_builders, workflow=workflow)

    # Cập nhật kết quả vào file storage
    data["runs"][run_id]["status"] = resumed.status.value
    data["runs"][run_id]["completed_steps"] = resumed.completed_steps
    data["runs"][run_id]["final_state"] = resumed.state
    data["runs"][run_id]["final_output"] = resumed.state.get("report_id")
    storage_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    
    print(f"RESUME_SUCCESS:{resumed.status.value}")

if __name__ == "__main__":
    asyncio.run(main())
"""


def test_cross_process_durable_checkpoint_resume(tmp_path: Path):
    """Test khép kín Gap 'Serving = No test yếu hơn tên gọi' theo Master Guide §11.
    
    Quy trình:
    1. Process chính (Parent): Khởi chạy và thực thi Step 1, ghi Checkpoint vào Storage, mô phỏng crash/pause.
    2. Process phụ (Subprocess độc lập): Được spawn qua `subprocess.run(sys.executable...)`,
       đọc Checkpoint từ Storage, resume và hoàn thành Step 2, Step 3.
    3. Parent verify: Step 1 không bị chạy lại (executions == 1), Step 2 và Step 3 hoàn tất đúng logic.
    """
    storage_file = tmp_path / "durable_run_storage.json"
    worker_script_file = tmp_path / "worker.py"
    worker_script_file.write_text(_WORKER_SCRIPT, encoding="utf-8")

    run_id = "run_proc_resume_101"

    # 1. Process chính chuẩn bị trạng thái sau khi hoàn thành Step 1 (simulate checkpoint after crash)
    initial_storage = {
        "step1_executions": 1,
        "step2_executions": 0,
        "step3_executions": 0,
        "runs": {
            run_id: {
                "run_id": run_id,
                "status": "WAITING_APPROVAL",
                "completed_steps": ["step_1"],
            }
        },
        "checkpoints": {
            run_id: {
                "step_1": {
                    "workspace_id": "ws_alpha",
                    "fetched_items": [10, 20, 30],
                }
            }
        },
    }
    storage_file.write_text(json.dumps(initial_storage, indent=2), encoding="utf-8")

    # 2. Spawn Subprocess Python độc lập hoàn toàn để resume
    env = dict(os.environ)
    env["PYTHONPATH"] = f"{Path.cwd() / 'packages'}:{Path.cwd()}"

    proc = subprocess.run(
        [sys.executable, str(worker_script_file), str(storage_file), run_id],
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )

    # Kiểm tra subprocess hoàn tất không lỗi
    assert proc.returncode == 0, f"Subprocess failed with stderr:\n{proc.stderr}"
    assert "RESUME_SUCCESS:COMPLETED" in proc.stdout

    # 3. Đọc dữ liệu từ persistent storage và verify
    final_data = json.loads(storage_file.read_text(encoding="utf-8"))

    # Step 1 KHÔNG bị re-execute trong subprocess
    assert final_data["step1_executions"] == 1, "Step 1 was re-executed during resume!"
    # Step 2 và Step 3 đã thực thi trong subprocess
    assert final_data["step2_executions"] == 1
    assert final_data["step3_executions"] == 1

    run_record = final_data["runs"][run_id]
    assert run_record["status"] == "COMPLETED"
    assert run_record["completed_steps"] == ["step_1", "step_2", "step_3"]
    assert run_record["final_state"]["total_sum"] == 60
    assert run_record["final_output"] == "rep_60"
