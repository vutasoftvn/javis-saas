# PHẦN 3 — Task contract slice Frontend ↔ Company Service

**Ngày:** 2026-08-28
**Phần của:** [dev-readiness-remediation-remaining](./2026-08-28-dev-readiness-remediation-remaining.md) · doc gốc §6
**Nhánh đề xuất:** `remediation/part3-task-contract-slice`
**Phụ thuộc:** PHẦN 1 (tenant isolation dùng chung)

## Context

Doc gốc §6: Company Service là owner của business API; Flutter chỉ gọi route đã có owner + DTO +
authorization contract rõ ràng; test hợp đồng phải gọi Company Service **thật** trên DB
disposable chứ không chỉ `MockClient`.

Hiện trạng đã kiểm:

- `frontend/lib/core/network/api_client.dart` — `_getHeaders()` **đã** tự gắn `Authorization: Bearer`
  và `X-Workspace-Id` từ `SecureStorageService` cho mọi request `requiresAuth`. Có
  `normalizeEndpoint()` (legacy normalizer): `/tasks*` → `/operations/tasks*`, `/sales/*` →
  `/commercial/*`, `/finance/*` & `/legal/*` → `/finance-legal/*`.
- `frontend/lib/modules/tasks/services/task_service.dart` — đã trỏ thẳng `/operations/tasks`,
  nhưng: (a) truyền `workspaceId` qua **query string** + **body** kèm fallback `?? '1'` thay vì
  chỉ dựa header `X-Workspace-Id`; (b) endpoint status là `POST /operations/tasks/:id/status`;
  (c) nuốt lỗi (`catch → return []/null`), không phân biệt 401/403/404/DTO lệch.
- Chưa có contract test chạy với Company Service thật.

## Trình tự (doc gốc §6)

### 3a. Inventory endpoint Flutter (deliverable tài liệu)

Tạo `docs/implementation/frontend-endpoint-inventory-2026-08-28.md`:

- Quét `frontend/lib/**/services/*.dart` + `frontend/lib/modules/**/services/*.dart` +
  `api_client.dart::normalizeEndpoint`.
- Bảng có version mỗi endpoint: `method | path (sau normalize) | request DTO | response DTO |
  auth | X-Workspace-Id? | owner service (operations/commercial/finance-legal/identity/agent) |
  parity status (OK / MISSING / DTO-MISMATCH / LEGACY-ONLY)`.
- Đánh dấu rõ các nhóm chưa có parity: `/strategy/*`, `/okrs/*`, `/projects/*`, `/validation/*`,
  AI, portfolio — **không** sửa trong PHẦN 3, chỉ ghi nhận.
- Không sửa route ở bước này.

### 3b. Slice Task (chỉ list / get / create / update-status)

`frontend/lib/modules/tasks/services/task_service.dart`:

1. Bỏ truyền `workspaceId` qua query string; dựa hoàn toàn vào header `X-Workspace-Id` do
   `ApiClient` gắn. Nếu Company Service `listTasksService` vẫn cần `workspaceId` trong query
   (`operations/handlers/task.handler.ts`), thống nhất **một** nguồn: ưu tiên header, chỉnh
   handler nhận `X-Workspace-Id` cho list (giống get/update sau PHẦN 1) và bỏ query param.
2. Bỏ fallback `?? '1'`: không có `workspace_id` trong secure storage → ném lỗi rõ ràng
   (`StateError`/typed exception), không mặc định workspace 1.
3. Không nuốt lỗi: map status code → kết quả typed (`401/403` → auth error, `404` → not found,
   `200` nhưng DTO thiếu field bắt buộc → parse error). Cho phép caller phân biệt.
4. Đồng bộ request/response DTO với schema `services/company/operations` hiện tại
   (`Task` interface trong `operations/services/task.service.ts`): field name, kiểu, optional.
5. Thêm `getTask(id)` → `GET /operations/tasks/:id` (hiện chưa có trong service Flutter) khớp
   `getTaskService(id, ctx)`.
6. Cập nhật `frontend/test/task_service_test.dart` cho DTO/route/luồng lỗi mới (vẫn dùng
   `MockClient` cho unit test client-shape).

### 3c. Contract test thật (backend)

Thêm `services/company/tests/operations/task-contract.test.ts` (Postgres disposable + Encore):

- Gọi endpoint Company Service thật qua HTTP client Encore, không mock.
- Ca kiểm:
  - `POST /operations/tasks` (thiếu `X-Workspace-Id`) → `401/400`, không tạo row.
  - `POST` hợp lệ → `200/201`, response DTO đúng field Flutter đọc (`id`, `title`, `status`,
    `priority`, `workspaceId`, `createdAt`, ...).
  - `GET /operations/tasks` → shape `{ tasks: [...] }` đúng như `TaskService.getTasksList()` parse.
  - `GET /operations/tasks/:id` cross-workspace (user A, task B) → `404` (dựa PHẦN 1).
  - `POST /operations/tasks/:id/status` với status không hợp lệ → `400`; hợp lệ → `200` + DTO.
  - Route sai (`/tasks` chưa normalize phía server) → `404` — chứng minh test bắt được route lệch.
- Nếu chưa có helper seed 2 workspace, thêm vào `services/company/tests/helpers/`.

### 3d. Dọn route legacy

- Chỉ khi 3b + 3c xanh: rà `normalizeEndpoint()` — nhánh `/tasks*` → `/operations/tasks*` giữ
  hay bỏ tuỳ còn consumer (`grep -rn "'/tasks" frontend/lib`). Nếu mọi caller đã dùng
  `/operations/tasks` trực tiếp → xoá nhánh normalize `/tasks`, ghi migration note trong inventory.
- Không đụng nhánh `/sales`, `/finance`, `/legal` (ngoài phạm vi slice Task).

## Verify

```text
cd frontend && flutter analyze && flutter test
cd services/company && npm run typecheck && make services-test   # gồm task-contract.test.ts trên Postgres disposable
```

## Definition of Done (ánh xạ doc gốc §6)

- [ ] `frontend-endpoint-inventory-2026-08-28.md` tồn tại, có version + parity status mọi endpoint Flutter.
- [ ] Flutter gửi `Authorization` + `X-Workspace-Id` cho mọi request tenant-bound của slice Task
      (không còn `workspaceId` query + fallback `'1'`).
- [ ] Contract test gọi Company Service thật (không `MockClient`) trên DB disposable.
- [ ] Test chứng minh: route thiếu, header thiếu, status code, DTO lệch → test đỏ.
- [ ] Cùng test chứng minh user A không đọc/ghi task workspace B.
- [ ] Không thêm mapping `/strategy/*` hay `/okrs/*` để biến 404 thành route khác semantics.
- [ ] Route legacy `/tasks` chỉ bị bỏ khi không còn consumer, có migration note.
- [ ] `flutter analyze/test` + `services/company` typecheck & `make services-test` xanh.
