"""S1: đăng ký/đăng nhập thật -> workspace A & B -> cô lập tenant qua wire.

Toàn bộ assert đi qua HTTP thật vào `services/company` (Encore/TS). Không mock,
không transport giả — chỉ so sánh status code + body THẬT quan sát được.
"""

from __future__ import annotations

from tests.e2e.mvp_stack import MvpStack
from tests.e2e.seed import identity
from tests.e2e.seed.handles import SeededWorkspace


def run(stack: MvpStack, seeded: SeededWorkspace) -> None:
    company = stack.company

    # Workspace B độc lập: một session company riêng (owner khác + membership
    # `founder` riêng). KHÔNG tái dùng owner_token của A cho B vì company kiểm tra
    # membership server-side; một session/workspace tách biệt là đường sạch để
    # chứng minh cô lập tenant.
    _b_user_id, workspace_b_id, workspace_b_token = identity.create_company_session(
        company.base_url, display_name="E2E Owner B"
    )

    # 1. Member đọc list task ở workspace của chính mình -> 200.
    #    `services/company` không có middleware response-envelope: body là bare
    #    `{"tasks": [...]}` (xem operations/handlers/task.handler.ts::listTasks).
    r_list = company.get(
        "/operations/tasks",
        token=seeded.member_token,
        workspace_id=seeded.workspace_id,
    )
    assert r_list.status_code == 200, r_list.text
    list_body = r_list.json()
    assert "tasks" in list_body, list_body
    assert isinstance(list_body["tasks"], list), list_body

    # 2. Owner tạo 1 task ở workspace A. `createTask` nhận `workspaceId` trong
    #    body (CreateTaskParams), không qua header `X-Workspace-Id`. Response là
    #    bare `Task` với `id` dạng string.
    r_create = company.post(
        "/operations/tasks",
        json={"workspaceId": seeded.workspace_id, "title": "S1 isolation task"},
        token=seeded.owner_token,
        workspace_id=seeded.workspace_id,
    )
    assert r_create.status_code in (200, 201), r_create.text
    create_body = r_create.json()
    task_id = create_body["id"]
    assert create_body["workspaceId"] == seeded.workspace_id, create_body

    # 3. Đọc task đó nhưng với workspace B (token owner của B) -> 404.
    #    `getTaskService` lọc theo `(id, workspaceId)` nên task của A vô hình với
    #    B — `APIError.notFound` map ra HTTP 404, không leak cross-tenant.
    r_cross = company.get(
        f"/operations/tasks/{task_id}",
        token=workspace_b_token,
        workspace_id=workspace_b_id,
    )
    assert r_cross.status_code == 404, r_cross.text

    # 4. Không Authorization -> 401 (resolveTenantContext: APIError.unauthenticated).
    r_anon = company.get("/operations/tasks", workspace_id=seeded.workspace_id)
    assert r_anon.status_code == 401, r_anon.text

    # 5. Token member hợp lệ nhưng không thuộc workspace B -> 403
    #    (resolveTenantContext: APIError.permissionDenied vì thiếu membership).
    r_forbidden = company.get(
        "/operations/tasks",
        token=seeded.member_token,
        workspace_id=workspace_b_id,
    )
    assert r_forbidden.status_code == 403, r_forbidden.text
