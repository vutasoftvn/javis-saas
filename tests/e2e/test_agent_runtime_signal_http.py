"""E2E HTTP test chứng minh contract runtime-signal COSA → Company THẬT.

Publisher (`apps/cosa/events/runtime_signal.py`) gửi
`POST /events/internal/agent-runtime-signal` với
`Authorization: Bearer <service-token>` tới Company service (Encore/TypeScript)
thật. Test này gọi đúng route đó trên process Company THẬT — không dùng
MockTransport/ASGITransport/monkeypatch — kiểm tra success + idempotency +
reject route cũ/thiếu token.
"""

from __future__ import annotations

import os
import time
import uuid
from datetime import UTC, datetime

import httpx

from tests.e2e.conftest import CompanyServiceHandle, count_runtime_source_signals

_SERVICE_TOKEN = os.environ.get("COSA_WORKER_SERVICE_TOKEN", "dev-worker-service-token")


def _signal_envelope(workspace_id: str, source_kind: str, source_id: str, sequence: int) -> dict:
    return {
        "signal": {
            "workspaceId": workspace_id,
            "sourceKind": source_kind,
            "sourceId": source_id,
            "sequence": sequence,
            "state": "COMPLETED",
            "observedAt": datetime.now(UTC).isoformat(),
            "correlationId": f"corr_{uuid.uuid4().hex[:12]}",
            "payloadHash": "sha256:" + "0" * 64,
        }
    }


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def test_agent_runtime_signal_http_contract(real_company_service: CompanyServiceHandle) -> None:
    base_url = real_company_service.base_url
    client = httpx.Client(base_url=base_url, timeout=10.0)

    # `operating.runtime_source_signals.workspace_id` là bigint không có FK tới
    # bảng workspace (xem migration 33), nên một workspace_id dạng số duy nhất
    # là đủ hợp lệ cho projection — không cần route test-session.
    workspace_id = str(9_000_000_000_000 + int(time.time()))

    source_kind = "run"
    source_id = f"e2e_run_{int(time.time())}"
    sequence = 1
    envelope = _signal_envelope(workspace_id, source_kind, source_id, sequence)

    # 1. Route canonical + token đúng → success.
    resp = client.post(
        "/events/internal/agent-runtime-signal",
        json=envelope,
        headers=_auth_headers(_SERVICE_TOKEN),
    )
    assert resp.status_code == 200, resp.text

    # 2. Lặp lại cùng source identity → idempotent, không tạo duplicate projection.
    resp2 = client.post(
        "/events/internal/agent-runtime-signal",
        json=envelope,
        headers=_auth_headers(_SERVICE_TOKEN),
    )
    assert resp2.status_code == 200, resp2.text

    # 3. Route cũ (số nhiều) → 404, không còn route alias.
    old_route = client.post(
        "/events/agent-runtime-signals",
        json=envelope,
        headers=_auth_headers(_SERVICE_TOKEN),
    )
    assert old_route.status_code == 404

    # 4. Thiếu service token → reject.
    missing = client.post(
        "/events/internal/agent-runtime-signal",
        json=envelope,
        headers={"Content-Type": "application/json"},
    )
    assert missing.status_code == 401

    # 5. Token sai → reject.
    wrong = client.post(
        "/events/internal/agent-runtime-signal",
        json=envelope,
        headers=_auth_headers("wrong-service-token"),
    )
    assert wrong.status_code == 401

    # 6. Chứng minh durable idempotent projection: gửi 2 lần cùng identity nhưng
    # chỉ đúng 1 hàng được lưu (unique constraint migration 33).
    assert count_runtime_source_signals(workspace_id, source_kind, source_id, sequence) == 1
