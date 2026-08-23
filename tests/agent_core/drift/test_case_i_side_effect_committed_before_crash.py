from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


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
    mode = sys.argv[1]  # "crash" | "retry"
    remote_store_path = Path(sys.argv[2])
    output_result_path = Path(sys.argv[3])
    run_id = sys.argv[4]
    idempotency_key = sys.argv[5]

    remote_data = json.loads(remote_store_path.read_text(encoding="utf-8"))

    def remote_order_fulfillment(payload, ctx):
        idem = payload["idempotency_key"]
        if idem in remote_data["orders"]:
            return remote_data["orders"][idem]

        order_id = f"ord_{len(remote_data['orders']) + 1}"
        record = {"order_id": order_id, "item": payload["item"], "status": "committed"}
        remote_data["orders"][idem] = record
        remote_data["total_fulfillments"] += 1
        remote_store_path.write_text(json.dumps(remote_data, indent=2), encoding="utf-8")

        if mode == "crash":
            # Kill process immediately after remote write commits
            os._exit(33)

        return record

    spec = CapabilitySpec(
        id="ecommerce.order.fulfill",
        risk=CapabilityRisk.LOW,
        input_schema={
            "type": "object",
            "required": ["item", "idempotency_key"],
            "properties": {
                "item": {"type": "string"},
                "idempotency_key": {"type": "string"},
            },
        },
    )

    registry = CapabilityRegistry()
    registry.register(spec, remote_order_fulfillment)
    repo = InMemoryRunRepository()
    gateway = CapabilityGateway(registry=registry, repository=repo)

    req = GatewayExecutionRequest(
        run_id=run_id,
        capability_id="ecommerce.order.fulfill",
        input_payload={"item": "MacBook Pro M3", "idempotency_key": idempotency_key},
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


def test_case_i_side_effect_committed_before_crash_recovery(tmp_path: Path):
    """Case I: Side-effect committed before crash (Master Guide §41.1 Case I).
    
    Kịch bản & Invariant:
    1. Gọi capability ghi tác động ra hệ thống bên ngoài.
    2. Hệ thống remote commit thành công giao dịch.
    3. Tiến trình COSA bị crash (os._exit) ngay trước khi ghi nhận trạng thái local completed.
    4. Khởi động lại và retry cùng idempotency_key.
    5. Invariant: Remote system KHÔNG ĐƯỢC sinh side effect thứ 2 (total_fulfillments = 1),
       và COSA reconcile được đúng kết quả gốc đã commit.
    """
    remote_store_file = tmp_path / "remote_ecommerce.json"
    worker_script_file = tmp_path / "worker_case_i.py"
    output_result_file = tmp_path / "result_case_i.json"

    worker_script_file.write_text(_WORKER_SCRIPT, encoding="utf-8")

    initial_remote = {
        "total_fulfillments": 0,
        "orders": {},
    }
    remote_store_file.write_text(json.dumps(initial_remote, indent=2), encoding="utf-8")

    run_id = "run_case_i_crash"
    idempotency_key = "idem_order_fulfill_5555"

    env = dict(os.environ)
    env["PYTHONPATH"] = f"{Path.cwd() / 'packages'}:{Path.cwd()}"

    # 1. Chạy process 1 và crash (exit code 33)
    proc1 = subprocess.run(
        [
            sys.executable,
            str(worker_script_file),
            "crash",
            str(remote_store_file),
            str(output_result_file),
            run_id,
            idempotency_key,
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc1.returncode == 33

    # Verify: Remote đã commit 1 order
    remote_crashed = json.loads(remote_store_file.read_text(encoding="utf-8"))
    assert remote_crashed["total_fulfillments"] == 1
    committed_order_id = remote_crashed["orders"][idempotency_key]["order_id"]

    # 2. Chạy process 2 (mô phỏng restart & retry)
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
    assert proc2.returncode == 0, f"Process 2 failed: {proc2.stderr}"

    # 3. Verify: Không có duplicate side effect
    remote_final = json.loads(remote_store_file.read_text(encoding="utf-8"))
    assert remote_final["total_fulfillments"] == 1

    # 4. Verify: COSA reconcile đúng order_id ban đầu
    res_final = json.loads(output_result_file.read_text(encoding="utf-8"))
    assert res_final["status"] == "completed"
    assert res_final["output_payload"]["order_id"] == committed_order_id
