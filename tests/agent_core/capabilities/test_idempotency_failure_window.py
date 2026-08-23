from __future__ import annotations

import json
import os
import signal
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

from agent_core.contracts.capability import CapabilitySpec
from agent_core.governance.contracts import CapabilityRisk
from agent_core.capabilities.gateway import CapabilityGateway, GatewayExecutionRequest
from agent_core.capabilities.registry import CapabilityRegistry
from agent_core.runs.repository import InMemoryRunRepository

async def main():
    mode = sys.argv[1]  # "crash_before_local_commit" | "retry"
    remote_store_path = Path(sys.argv[2])
    output_result_path = Path(sys.argv[3])
    run_id = sys.argv[4]
    idempotency_key = sys.argv[5]

    remote_data = json.loads(remote_store_path.read_text(encoding="utf-8"))

    # Remote system mock API (vd. Stripe / Banking API)
    def remote_bank_transfer(payload, ctx):
        idem = payload["idempotency_key"]
        # Nếu remote system đã commit transaction này trước đó -> Reconcile kết quả cũ
        if idem in remote_data["transactions"]:
            return remote_data["transactions"][idem]
        
        # Tạo giao dịch mới & tăng commit count
        tx_id = f"bank_tx_{len(remote_data['transactions']) + 1}"
        result = {"tx_id": tx_id, "amount": payload["amount"], "status": "committed"}
        remote_data["transactions"][idem] = result
        remote_data["total_remote_commits"] += 1
        remote_store_path.write_text(json.dumps(remote_data, indent=2), encoding="utf-8")

        if mode == "crash_before_local_commit":
            # Master Guide §17.3: Process bị kill ngay sau khi Remote commit nhưng TRƯỚC khi COSA persist status hoàn tất
            os._exit(42)  # Hard process crash

        return result

    spec = CapabilitySpec(
        id="bank.payout.send",
        risk=CapabilityRisk.LOW,
        input_schema={
            "type": "object",
            "required": ["amount", "idempotency_key"],
            "properties": {
                "amount": {"type": "number"},
                "idempotency_key": {"type": "string"},
            },
        },
    )

    registry = CapabilityRegistry()
    registry.register(spec, remote_bank_transfer)
    repo = InMemoryRunRepository()
    gateway = CapabilityGateway(registry=registry, repository=repo)

    req = GatewayExecutionRequest(
        run_id=run_id,
        capability_id="bank.payout.send",
        input_payload={"amount": 5000, "idempotency_key": idempotency_key},
        idempotency_key=idempotency_key,
    )

    res = await gateway.execute(req)

    output_result_path.write_text(
        json.dumps({
            "status": res.status,
            "output_payload": res.output_payload,
            "cached_idempotency": res.cached_idempotency,
        }, indent=2),
        encoding="utf-8"
    )

if __name__ == "__main__":
    asyncio.run(main())
"""


def test_idempotency_failure_window_remote_commit_and_crash_recovery(tmp_path: Path):
    """Test kịch bản Crash Failure Window theo Master Guide §17.3:
    1. Invoke external write.
    2. Remote system commits side effect (ghi transaction).
    3. COSA process crash/bị kill TRƯỚC khi lưu completed status.
    4. Restart/retry cùng idempotency_key ở process mới.
    5. Không phát sinh duplicate side effect ở Remote system (commits == 1).
    6. COSA reconcile và trả về đúng kết quả ban đầu.
    """
    remote_store_file = tmp_path / "remote_bank_system.json"
    worker_script_file = tmp_path / "gateway_worker.py"
    output_result_file = tmp_path / "execution_result.json"

    worker_script_file.write_text(_WORKER_SCRIPT, encoding="utf-8")

    initial_remote = {
        "total_remote_commits": 0,
        "transactions": {},
    }
    remote_store_file.write_text(json.dumps(initial_remote, indent=2), encoding="utf-8")

    run_id = "run_fail_window_1001"
    idempotency_key = "idem_bank_transfer_9999"

    env = dict(os.environ)
    env["PYTHONPATH"] = f"{Path.cwd() / 'packages'}:{Path.cwd()}"

    # Bước 1, 2, 3: Chạy process 1 và crash ngay sau khi remote system commit
    proc1 = subprocess.run(
        [
            sys.executable,
            str(worker_script_file),
            "crash_before_local_commit",
            str(remote_store_file),
            str(output_result_file),
            run_id,
            idempotency_key,
        ],
        capture_output=True,
        text=True,
        env=env,
    )

    # Process 1 phải bị crash (exit code 42 do os._exit)
    assert proc1.returncode == 42

    # Verify: Remote system đã commit 1 transaction
    remote_after_crash = json.loads(remote_store_file.read_text(encoding="utf-8"))
    assert remote_after_crash["total_remote_commits"] == 1
    assert idempotency_key in remote_after_crash["transactions"]
    first_tx_id = remote_after_crash["transactions"][idempotency_key]["tx_id"]

    # Bước 4: Restart process 2 (mô phỏng retry sau crash với cùng idempotency_key)
    proc2 = subprocess.run(
        [
            sys.executable,
            str(worker_script_file),
            "retry",
            str(remote_store_file),
            str(output_result_file),
            run_id,
            idempotency_key,
        ],
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )

    # Process 2 phải hoàn thành trơn tru
    assert proc2.returncode == 0, f"Process 2 failed: {proc2.stderr}"

    # Bước 5: Verify Remote system KHÔNG sinh side-effect thứ hai (vẫn đúng 1 commit)
    remote_final = json.loads(remote_store_file.read_text(encoding="utf-8"))
    assert remote_final["total_remote_commits"] == 1, "Duplicate side effect detected in remote system!"

    # Bước 6: Verify kết quả trả về đúng tx_id của lần commit đầu tiên
    result_final = json.loads(output_result_file.read_text(encoding="utf-8"))
    assert result_final["status"] == "completed"
    assert result_final["output_payload"]["tx_id"] == first_tx_id
    assert result_final["output_payload"]["amount"] == 5000
