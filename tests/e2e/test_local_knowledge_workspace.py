"""Task 13 (plan local-first-enterprise-knowledge) — chứng minh durability,
cách ly workspace, và không rò rỉ raw content sang platform control plane cho
toàn bộ luồng Vault/knowledge cục bộ, qua process THẬT (không phải instance
thứ hai trong cùng process — CLAUDE.md rule 6).

4 plane thật (company/cosa Encore, apps/cosa API uvicorn, worker) + disposable
Postgres, giống hệt hạ tầng `tests/e2e/test_cross_plane_smoke.py`. Riêng
`apps_cosa_api`/`apps_cosa_worker` được restart THẬT (kill + respawn, cùng
port) giữa lúc test đang chạy — company/cosa giữ nguyên vì chỉ Workspace
Runtime Node (2 process Python) là mục tiêu chứng minh durability, không phải
toàn bộ 4 plane.

Không mock transport (`scripts/check_mvp_e2e_purity.py`) — thiếu tiền đề
(Encore CLI, Postgres admin) thì fixture `pytest.fail`, không skip.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from tests.e2e.seed import identity
from tests.e2e.stack.disposable_postgres import DisposableCluster
from tests.e2e.stack.subprocess_stack import (
    StackHandles,
    boot_subprocess_stack,
    restart_api_and_worker,
    teardown_subprocess_stack,
)

pytestmark = pytest.mark.cross_plane

_TIMEOUT = 20.0


@pytest.fixture
def local_stack(disposable_cluster: DisposableCluster, tmp_path_factory: pytest.TempPathFactory):
    """Boot stack THẬT với `KNOWLEDGE_INGESTION_ENABLED=1` +
    `COSA_WORKSPACE_STORAGE_ROOT` trỏ 1 thư mục tmp riêng cho phiên test này —
    khác `real_cosa_stack` (conftest.py, session-scoped, không bật knowledge
    ingestion) nên cố tình KHÔNG tái dùng fixture đó."""
    storage_root = tmp_path_factory.mktemp("cosa-knowledge-e2e")
    extra_env = {
        "KNOWLEDGE_INGESTION_ENABLED": "1",
        "COSA_WORKSPACE_STORAGE_ROOT": str(storage_root),
    }
    handles = boot_subprocess_stack(disposable_cluster, extra_py_env=extra_env)
    try:
        yield handles, storage_root, extra_env
    finally:
        teardown_subprocess_stack(handles)


def _create_and_upload_document(
    handles: StackHandles, token: str, workspace_id: str, *, title: str, content: bytes
) -> dict:
    with httpx.Client(base_url=handles.apps_cosa_url, timeout=_TIMEOUT) as client:
        created = client.post(
            "/agent/vault/documents",
            json={"title": title, "media_type": "text/plain"},
            headers={"Authorization": f"Bearer {token}", "X-Workspace-Id": workspace_id},
        )
        assert created.status_code == 201, created.text
        upload = created.json()["data"]

        upload_resp = client.put(upload["upload_url"], content=content)
        assert upload_resp.status_code == 204, upload_resp.text

        return upload


def _complete_upload(handles: StackHandles, token: str, workspace_id: str, upload_id: str) -> dict:
    with httpx.Client(base_url=handles.apps_cosa_url, timeout=_TIMEOUT) as client:
        resp = client.post(
            f"/agent/vault/uploads/{upload_id}/complete",
            headers={"Authorization": f"Bearer {token}", "X-Workspace-Id": workspace_id},
        )
        assert resp.status_code == 200, resp.text
        return resp.json()["data"]


def _get_document(
    handles: StackHandles, token: str, workspace_id: str, document_id: str
) -> httpx.Response:
    with httpx.Client(base_url=handles.apps_cosa_url, timeout=_TIMEOUT) as client:
        return client.get(
            f"/agent/vault/documents/{document_id}",
            headers={"Authorization": f"Bearer {token}", "X-Workspace-Id": workspace_id},
        )


def test_local_upload_survives_api_and_worker_restart(local_stack, disposable_cluster) -> None:
    """Kịch bản chính (plan Step 1): tạo upload → restart API+worker THẬT
    (2 process mới, cùng port) → complete upload SAU restart vẫn hoạt động
    (chứng minh ticket không sống trong RAM của process cũ) → document vẫn
    truy vấn được với đúng state, không mất mát qua restart."""
    handles, _storage_root, extra_env = local_stack
    seeded = identity.seed_workspace(handles_as_stack(handles), disposable_cluster)

    upload = _create_and_upload_document(
        handles,
        seeded.owner_token,
        seeded.workspace_id,
        title="Quarter plan",
        content=b"Quarter plan",
    )

    handles = restart_api_and_worker(handles, disposable_cluster, extra_py_env=extra_env)

    completed = _complete_upload(
        handles, seeded.owner_token, seeded.workspace_id, upload["upload_id"]
    )
    assert completed["state"] == "QUEUED"

    detail = _get_document(handles, seeded.owner_token, seeded.workspace_id, upload["document_id"])
    assert detail.status_code == 200
    assert detail.json()["data"]["document_id"] == upload["document_id"]


def test_member_b_receives_no_leak_of_founder_only_document(
    local_stack, disposable_cluster
) -> None:
    """Kịch bản 2 (plan Step 1, mở rộng): member-b không nhận được title,
    snippet hay bất kỳ trường nào của 1 document PRIVATE do founder tạo —
    404 thẳng, không phải 200 với field rỗng (khác nhau về mặt rò rỉ tồn tại)."""
    handles, _storage_root, _extra_env = local_stack
    seeded = identity.seed_workspace(
        handles_as_stack(handles), disposable_cluster, with_member=True
    )
    assert seeded.member_token is not None

    upload = _create_and_upload_document(
        handles,
        seeded.owner_token,
        seeded.workspace_id,
        title="Board salary plan",
        content=b"executive salary details",
    )

    member_view = _get_document(
        handles, seeded.member_token, seeded.workspace_id, upload["document_id"]
    )
    assert member_view.status_code == 404
    assert "Board salary plan" not in member_view.text
    assert "salary" not in member_view.text.lower()


def test_raw_content_never_referenced_toward_platform_control_plane() -> None:
    """Kịch bản 3 (plan Step 1): raw file/chunk/embedding không bao giờ tới
    endpoint platform control plane. Không dựng "mock platform endpoint" (vi
    phạm `scripts/check_mvp_e2e_purity.py` — cấm transport giả ở tier E2E) —
    thay vào đó verify tĩnh, đọc code thật: không module nào trong knowledge
    ingestion pipeline / vault import `resolve_platform_control_plane_url`
    hay gọi HTTP tới platform control plane. ADR-LOCAL-FIRST-001 yêu cầu tách
    bạch tuyệt đối Workspace Runtime Node (execution plane, local) khỏi
    Platform Control Plane (VPS, identity/license/connector only)."""
    repo_root = Path(__file__).resolve().parents[2]
    scanned_dirs = [
        repo_root / "apps/cosa/knowledge_ingestion",
        repo_root / "apps/cosa/api/vault_routes.py",
        repo_root / "apps/cosa/graphql",
    ]

    # Chỉ bắt IMPORT/CALL thật (`resolve_platform_control_plane_url(` hoặc
    # `import resolve_platform_control_plane_url`) — KHÔNG bắt docstring giải
    # thích "không được dùng X" (vd. control_plane_client.py cố tình nêu tên
    # biến env bị cấm để giải thích lý do, không tự gọi nó).
    offenders: list[str] = []
    for target in scanned_dirs:
        files = [target] if target.is_file() else list(target.rglob("*.py"))
        for f in files:
            text = f.read_text(encoding="utf-8")
            if "resolve_platform_control_plane_url(" in text or (
                "import resolve_platform_control_plane_url" in text
            ):
                offenders.append(str(f.relative_to(repo_root)))

    assert offenders == [], (
        f"Knowledge ingestion/vault code không được reference platform control plane "
        f"(ADR-LOCAL-FIRST-001) — tìm thấy trong: {offenders}"
    )


def handles_as_stack(handles: StackHandles):
    """`tests.e2e.seed.identity.seed_workspace()` chỉ đọc `.company.base_url`/
    `.platform.base_url` từ tham số `stack` (duck-typed, xem docstring hàm
    đó) — không cần dựng cả `MvpStack` đầy đủ (kèm `agent`/`apps_cosa`
    ServiceClient không dùng tới) mỗi lần restart đổi `apps_cosa_url`."""
    from tests.e2e.mvp_stack import ServiceClient

    class _Stack:
        company = ServiceClient(base_url=handles.company_url)
        platform = ServiceClient(base_url=handles.cosa_url)

    return _Stack()
