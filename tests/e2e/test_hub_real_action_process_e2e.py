"""Hub real-action process E2E (plan 2026-09-20-governed-advisor-overlay-and-truthful-hub, Task 13).

Đúng các request mà Flutter `DirectAgentChatController` phát (`/agent/conversations`,
`/agent/conversations/{id}/messages`, `POST /operations/tasks`) chạy qua stack 4 plane thật:
chat tạo run durable Project-scoped, tạo task chỉ thành công khi Company trả task id, và retry
với cùng idempotency key không nhân đôi task.
"""

from __future__ import annotations

import time

import httpx
import pytest

from apps.cosa.agents.specs import COSA_FINANCE_AGENT_SPEC
from tests.e2e.seed import identity

pytestmark = pytest.mark.cross_plane

_TERMINAL = {"COMPLETED", "FAILED", "CANCELLED"}
_WAIT_S = 90.0


def _seed_compliance(company_url: str, workspace_id: str, founder_id: str) -> None:
    resp = httpx.post(
        f"{company_url}/finance-legal/ai-compliance/_e2e/seed",
        json={
            "scenario": "approved",
            "systemKey": COSA_FINANCE_AGENT_SPEC.id,
            "workspaceId": workspace_id,
            "founderMemberId": founder_id,
            "additionalBoundCapabilityIds": list(COSA_FINANCE_AGENT_SPEC.capability_refs),
        },
        timeout=30.0,
    )
    assert resp.status_code == 200, resp.text


def _worker_tail(stack, lines: int = 60) -> str:
    procs = stack.handles.procs if stack.handles else []
    out = []
    for proc in procs:
        if proc.name == "apps_cosa_worker":
            out.extend(l for l in proc.tail(400).splitlines() if "scheduled-tasks/poll" not in l)
    return "\n".join(out[-lines:])


def _wait_run(cluster, run_id: str) -> tuple | None:
    """Đọc bản ghi run durable (`agent.runs`) tới khi terminal — API không có GET run theo id."""
    import psycopg2

    deadline = time.monotonic() + _WAIT_S
    row: tuple | None = None
    while time.monotonic() < deadline:
        conn = psycopg2.connect(cluster.agent_app_url, connect_timeout=5)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT status, workspace_id, conversation_id FROM agent.runs WHERE run_id = %s",
                    (run_id,),
                )
                row = cur.fetchone()
        finally:
            conn.close()
        if row and str(row[0]).upper() in _TERMINAL:
            return row
        time.sleep(1.5)
    return row


@pytest.fixture
def hub(real_cosa_stack, disposable_cluster):
    seeded = identity.seed_workspace(real_cosa_stack, disposable_cluster)
    _seed_compliance(real_cosa_stack.company.base_url, seeded.workspace_id, seeded.owner_user_id)
    # Worker chỉ chạy profile vận hành mà Project đã kích hoạt (run-authority của Company).
    activated = real_cosa_stack.company.post(
        f"/operations/projects/{seeded.default_project_id}/startup-team/finance/activate",
        json={"expectedVersion": 1},
        token=seeded.owner_token,
        workspace_id=seeded.workspace_id,
    )
    assert activated.status_code == 200, activated.text
    return {
        "stack": real_cosa_stack,
        "agent_url": real_cosa_stack.agent.base_url,
        "company_url": real_cosa_stack.company.base_url,
        "workspace_id": seeded.workspace_id,
        "project_id": str(seeded.default_project_id),
        # ApiClient của Flutter luôn gửi cả Bearer lẫn X-Workspace-Id cho mọi plane.
        "headers": {
            "Authorization": f"Bearer {seeded.owner_token}",
            "X-Workspace-Id": seeded.workspace_id,
        },
        "company_headers": {
            "Authorization": f"Bearer {seeded.owner_token}",
            "X-Workspace-Id": seeded.workspace_id,
        },
    }


def _new_conversation(hub: dict) -> str:
    resp = httpx.post(
        f"{hub['agent_url']}/agent/conversations",
        json={
            "title": "finance",
            "active_agent_profile": "finance",
            "project_id": hub["project_id"],
        },
        headers=hub["headers"],
        timeout=15.0,
    )
    assert resp.status_code in (200, 201), resp.text
    body = resp.json()
    assert body["project_id"] == hub["project_id"]
    return str(body.get("conversation_id") or body["id"])


def test_direct_chat_creates_a_project_scoped_conversation_and_a_durable_run(hub, disposable_cluster):
    conversation_id = _new_conversation(hub)

    resp = httpx.post(
        f"{hub['agent_url']}/agent/conversations/{conversation_id}/messages",
        json={
            "content": "Runway còn bao lâu?",
            "role": "user",
            "project_id": hub["project_id"],
            "data_access": {"categories": ["NON_PERSONAL"], "subject_reference": None},
        },
        headers=hub["headers"],
        timeout=15.0,
    )
    assert resp.status_code in (200, 202), resp.text
    accepted = resp.json()
    run_id = accepted["run_id"]
    assert accepted["message_id"]

    row = _wait_run(disposable_cluster, run_id)
    assert row is not None, f"no durable run row\n{_worker_tail(hub['stack'])}"
    status, run_workspace, run_conversation = row
    # Run thật kết thúc ở trạng thái terminal do worker/model quyết định — không có câu trả lời
    # nào được sinh cục bộ; COMPLETED hay FAILED đều là kết quả thật của run này.
    assert str(status).upper() in _TERMINAL, row
    assert str(run_workspace) == hub["workspace_id"]
    assert run_conversation == conversation_id


def test_message_without_project_creates_no_run(hub):
    conversation_id = _new_conversation(hub)

    resp = httpx.post(
        f"{hub['agent_url']}/agent/conversations/{conversation_id}/messages",
        json={
            "content": "Không có Project",
            "role": "user",
            "data_access": {"categories": ["NON_PERSONAL"], "subject_reference": None},
        },
        headers=hub["headers"],
        timeout=15.0,
    )
    assert resp.status_code in (400, 404, 422), resp.text
    assert "run_id" not in resp.text


def test_task_creation_is_project_scoped_and_idempotent_on_retry(hub):
    key = f"hub-direct-chat-task:{hub['project_id']}:conv-1:msg-1"
    body = {
        "workspaceId": hub["workspace_id"],
        "title": "[CFO Advisor] Cắt giảm chi phí marketing",
        "projectId": hub["project_id"],
        "priority": "medium",
        "idempotencyKey": key,
    }

    def create() -> httpx.Response:
        return httpx.post(
            f"{hub['company_url']}/operations/tasks",
            json=body,
            headers=hub["company_headers"],
            timeout=15.0,
        )

    first = create()
    assert first.status_code in (200, 201), first.text
    retry = create()
    assert retry.status_code in (200, 201), retry.text
    assert retry.json()["id"] == first.json()["id"], "retry must not create a second task"
    assert first.json()["projectId"] == hub["project_id"]

    listing = httpx.get(
        f"{hub['company_url']}/operations/tasks", headers=hub["company_headers"], timeout=15.0
    )
    assert listing.status_code == 200, listing.text
    matching = [t for t in listing.json()["tasks"] if t["title"] == body["title"]]
    assert len(matching) == 1


def test_task_creation_without_project_fails_instead_of_claiming_success(hub):
    resp = httpx.post(
        f"{hub['company_url']}/operations/tasks",
        json={"workspaceId": hub["workspace_id"], "title": "Không có Project"},
        headers=hub["company_headers"],
        timeout=15.0,
    )
    assert resp.status_code in (400, 422), resp.text
