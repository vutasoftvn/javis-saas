# Dọn dẹp tài liệu, chuẩn hóa đặt tên, làm phẳng cấu trúc backend, và rà soát đồng bộ Backend/Frontend/DB — Implementation Plan

> **For agentic workers:** Plan này được lập qua chế độ plan mode, xác nhận bởi user, thực thi trực tiếp trong quá trình cùng phiên (không dùng `superpowers:executing-plans` riêng). Ghi lại tại đây để lưu vào dự án theo yêu cầu của user, dùng làm tài liệu tham chiếu nếu cần tiếp tục ở phiên sau.

**Goal:** (1) Dọn rác tài liệu `.md` tích tụ ngoài `markdown/`; (2) chuẩn hóa vài tên file/hàm còn mang số version thay vì mô tả chức năng; (3) bỏ lớp bọc thư mục `backend/app/` không cần thiết — đưa toàn bộ thư mục con lên thẳng `backend/`; (4) rà soát và sửa các điểm lệch giữa API backend, schema DB, và UI frontend.

**Bối cảnh:** `backend/core/` và `backend/agent_runtime/` đã nằm ngang hàng `backend/app/` từ trước; import tuyệt đối `from core...`, `from agent_runtime...` chạy được vì dev container bind-mount toàn bộ `backend/` vào `/app` (`docker-compose.yml` service `brain-api`: `volumes: - ./backend:/app`) — nghĩa là `backend/` vốn dĩ đã là package root thật sự, `app/` chỉ là một lớp bọc thừa cho phần lớn code. Việc làm phẳng còn sửa luôn một lỗi có sẵn: `Dockerfile`/`Dockerfile.api`/`Dockerfile.worker` hiện chỉ `COPY app/` — không copy `backend/core/`, `backend/agent_runtime/` vào image build thật (chỉ chạy được nhờ bind-mount trong dev) — build production hiện đang thiếu module.

---

## Phần 1 — Dọn dẹp file .md (ngoài `markdown/`)

**Xóa hẳn (~84 file, đã xác nhận an toàn bằng khảo sát trực tiếp):**
- [x] `docs/architecture/archive/` (26 file) — tự đánh dấu "superseded" trong commit gần nhất.
- [x] `.superpowers/sdd/` (55 file: progress/brief/report của task đã xong, không track git).
- [x] `.pytest_cache/README.md`, `backend/.pytest_cache/README.md`, `services/realtime_agent/.pytest_cache/README.md` (3 file sinh tự động).

**Giữ, chỉ gộp vị trí:**
- [x] `docs/adr/` (34 file, hệ mã `ADR-AGENT-*`/`ADR-EXEC-*`/`ADR-FIN-*`/`ADR-MEM-*`/`ADR-V13-*`) — đã kiểm chứng KHÔNG trùng với `docs/architecture/adr/` (hệ mã `ADR-006`…`ADR-011`) → gộp `git mv docs/adr/*.md docs/architecture/adr/`, xóa `docs/adr/` rỗng.

**Giữ nguyên (~197 file, không đụng):** CLAUDE.md, README.md, DEPLOYMENT.md, `.agents/rules/*`, `.agents/skills/*`, plan/spec/report trong `docs/superpowers/`, `docs/inventory/`, `docs/agent-platform/`, `docs/architecture/*.md` (non-archive), toàn bộ `backend/**/prompts`, `backend/business/packs/**` (SKILL.md, body.md, normalized.md — dữ liệu hệ thống COSA đọc lúc runtime, không phải doc rác), README hạ tầng (`deploy/`, `infra/`, `landing/`, `services/realtime_agent/`).

---

## Phần 2 — Chuẩn hóa tên file/hàm theo version

| Việc | File | Ghi chú |
|---|---|---|
| [x] Đổi tên method | `review_service.py::_v13_composition()` → `_build_review_composition()` | An toàn — private, 3 call site cùng file |
| [x] Đổi tên method | `deepseek_harness.py::_new_harness()` → `_create_harness_instance()` | An toàn — private |
| [x] Đổi tên function + sửa import | `tool_dispatch.py` gọi `invoke_tool_legacy()` từ `workforce/tools/invocation/service.py` → đổi thành `invoke_tool_via_spec()`, cập nhật 2 call site | Cần cẩn thận |
| [x] Đổi tên test file | `test_v13_router_gates.py` → `test_router_feature_guards.py`; `test_strategy_v12_models.py` → `test_strategy_model_fields.py`; `test_review_v13_composition.py` → `test_review_composition.py` | An toàn |
| [x] Giữ, chỉ ghi chú | `platform/core/backup_service.py` | Xác nhận 0 tham chiếu bằng grep — theo user đây là placeholder cho tính năng backup sắp làm, giữ nguyên + thêm docstring ngắn "chưa wire vào router, chờ triển khai" |

**KHÔNG đổi:** migration alembic (`v13_0NN_*.py`), feature flag constants (`FLAG_..._V12/V13_1`), 4 entrypoint `main.py/full_main.py/worker_main.py/central_main.py` (vai trò deploy khác nhau), `legacy_facade.py` (deprecation pattern chủ đích).

---

## Phần 3 — Làm phẳng cấu trúc backend: bỏ lớp bọc `app/`

Thay đổi lớn nhất và rủi ro cao nhất trong plan — thực hiện như MỘT bước atomic (script hóa toàn bộ, không sửa tay từng file), test lại toàn diện ngay sau đó. Phạm vi thực đo được bằng grep: **897 file, 3471 dòng import** dùng tiền tố `from app.` / `import app.`.

### 3.1 Giải quyết va chạm tên trước khi gộp
`backend/core/` (domain model nghiệp vụ) và `backend/app/core/` (auth/audit/feature_flags/tool_registry/tenancy — hạ tầng dùng chung) sẽ va tên nếu gộp thẳng.
- [x] Đổi `backend/core/` → `backend/business_core/` (19 dòng import: `from core.X` → `from business_core.X`). Tên khớp thẳng thuật ngữ "Business Core" đã có sẵn trong CLAUDE.md.
- [x] `backend/app/core/` giữ tên `core/` sau khi lên cấp (435 dòng import `from app.core.X` → `from core.X`) — đổi tên phần ít tham chiếu hơn để giảm rủi ro.

### 3.2 Di chuyển thư mục
- [x] `git mv` từng thư mục con của `backend/app/` lên thẳng `backend/` (giữ nguyên tên, chỉ đổi vị trí):
```
backend/app/bootstrap    → backend/bootstrap
backend/app/business     → backend/business
backend/app/core         → backend/core   (sau khi core cũ đã đổi thành business_core)
backend/app/db           → backend/db
backend/app/founder_os   → backend/founder_os
backend/app/integrations → backend/integrations
backend/app/platform     → backend/platform
backend/app/scripts      → backend/scripts
backend/app/tests        → backend/tests
backend/app/workforce    → backend/workforce
backend/app/main.py, full_main.py, worker_main.py, central_main.py → backend/*.py
```
- [x] Xóa `backend/app/` rỗng sau cùng.

### 3.3 Codemod import (chạy script, không sửa tay)
- [x] Toàn bộ `backend/**/*.py`: `from app.` → `from `; `import app.` → `import ` — thực tế 946 file, 536 dòng bổ sung dạng import lồng trong hàm (không anchor `^`) bị bỏ sót ở lượt quét đầu, đã quét lại không anchor và xử lý hết bằng script Python (không dùng sed để tránh escape lỗi).
- [x] `from core.` → `from business_core.` áp dụng có chọn lọc theo tên submodule (base/finance/learning/legal/marketing/organization/sales/strategy/tasks/validation) để không đụng vào `core/` mới (kernel hạ tầng) — 35+ file.
- [x] **Phát sinh ngoài kế hoạch ban đầu:** `backend/app/platform/` khi lên cấp thành `backend/platform/` va chạm với module chuẩn `platform` của Python (`platform.system()`...) vì entrypoint chạy từ `backend/` nên package cục bộ che khuất stdlib — ảnh hưởng mọi thư viện bên thứ 3 gọi `import platform` nội bộ. Đã đổi thành `backend/platform_core/` (194 dòng import cập nhật) và xác minh `import platform` vẫn trả về stdlib đúng sau khi sửa.
- [x] Xử lý các dòng `"app.X"` dạng chuỗi (mock.patch, monkeypatch.setattr, sys.modules.get, importlib.import_module, uvicorn.run, program_class_path) — 73 file, không bị script import-statement bắt được vì là string literal.
- [x] Verify: `grep -rEn "\bfrom app\.|\bimport app\." backend --include="*.py"` (trừ `.venv`) trả về rỗng; `from main import app` (biến FastAPI, không phải module) không bị đụng.

### 3.4 Cập nhật cấu hình/entrypoint ngoài mã Python
- [x] `backend/alembic/env.py`, `backend/alembic_control_plane/env.py` — tự động khớp bởi script 3.3 (indented import).
- [x] `backend/pytest.ini`: `testpaths = app/tests` → `testpaths = tests`.
- [x] `backend/Dockerfile`, `backend/Dockerfile.api`: `COPY app/ ./app/` + các COPY lẻ → `COPY . .`; thêm `.dockerignore` mới (`.venv/`, `__pycache__/`, `.pytest_cache/`, `storage/`, `.env`); CMD `uvicorn app.main:app` → `uvicorn main:app`.
- [x] `backend/Dockerfile.worker`: `COPY app/ ./app/` → `COPY . .`; CMD `python -m app.worker_main` → `python -m worker_main`.
- [x] `docker-compose.yml` (root): `--reload-dir app` → `--reload-dir .`, `uvicorn app.main:app` → `uvicorn main:app`.
- [x] `deploy/central_vps/docker-compose.yaml`, `deploy/self_host/docker-compose.yaml`: entrypoint + comment cập nhật.
- [x] **Phát sinh ngoài kế hoạch:** `Makefile` và `.github/workflows/quality.yml` cũng hardcode `backend/app/tests`, `backend/app` — đã sửa (`backend/tests`, `backend`), thêm `--glob '!backend/.venv/**'` vào rg check trong Makefile vì trước đây `backend/app` không đụng `.venv` (nằm ngoài `app/`) nhưng quét `backend/` giờ sẽ đụng nếu không loại trừ.

### 3.5 Xóa scaffold chết trong lúc dọn (đã verify 0 consumer bằng grep)
- [x] `backend/storage/sqlite/` (toàn bộ).
- [x] `backend/agent_runtime/events/sqlite_event_store.py`, `backend/agent_runtime/sessions/session_manager.py`, `backend/agent_runtime/sessions/base.py`.
- [x] Sửa `backend/agent_runtime/sessions/__init__.py` và `backend/agent_runtime/events/__init__.py` để chỉ export phần canonical còn lại.
- Phát hiện qua `tests/test_architectural_invariants.py::test_backend_app_has_no_direct_imports_of_frozen_runtime_scaffolds` (test kiểm tra kiến trúc thật, không phải giả định) — xác nhận việc xóa là đúng và cần thiết, không chỉ là dọn dẹp tùy ý.

### 3.6 Phát sinh: khôi phục tài liệu bị xóa nhầm ở Phần 1
- [x] `docs/architecture/archive/COSA_HARNESS_CONTRIBUTOR_EXTENSION_MAP.md` (đã xóa ở Phần 1 vì coi là "archive superseded") thực ra vẫn là nội dung governance sống, được `test_contributor_extension_map_forbids_parallel_runtime_scaffolds` kiểm tra thật — khôi phục về `docs/architecture/COSA_HARNESS_CONTRIBUTOR_EXTENSION_MAP.md` (đường dẫn chính thức, không phải archive), cập nhật path nội dung theo cấu trúc mới.
- [x] `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md` — cập nhật 28 tham chiếu `backend/app/...` → cấu trúc mới (`backend/core` → `backend/business_core`, `backend/app/platform/` → `backend/platform_core/`, còn lại bỏ `app/`).
- [x] `scripts/report_identity_consumers.py` (script thật ở root repo, không phải test) — hardcode `app.founder_os.tasks.models`, `app.platform.organization.models` để AST-match import — sửa thành `founder_os.tasks.models`, `platform_core.organization.models`; nếu không sửa, script sẽ báo sai (0 consumer) cho mọi lần chạy governance report sau này.

**KHÔNG động vào:** compatibility re-export shim `business/learning/models.py: from business_core.learning.models import Lesson` (tên mới sau 3.3) — có 6 call site đang sống phụ thuộc, cần một đợt migration riêng sau này.

---

## Phần 4 — Đồng bộ Backend ↔ Frontend ↔ Database

- [x] **Endpoint fallback lỗi thời** — kiểm tra lại: `/api/v1/agents` (founder_os router) vẫn là route thật đang chạy (không chết) → fallback trong `agents_service.dart` hợp lệ, giữ nguyên, không sửa.
- [ ] **Không nhất quán query param vs path param** — Tasks dùng `?workspace_id=` (`task_service.dart`), Missions/Hub dùng path `/workspaces/{ws_id}/...`. ĐÃ KHÔNG làm trong đợt này: đây là thay đổi API contract công khai ảnh hưởng nhiều consumer (mobile, test khác), rủi ro cao hơn hẳn phần dọn cấu trúc — để lại làm việc riêng sau, có kiểm thử end-to-end đầy đủ.
- [x] **Router mount trùng** — `backend/platform_core/router.py`: xác nhận `/api/v1/founder-hub` (prefix cũ) không có consumer nào (backend lẫn frontend), route thật frontend dùng là mount `/api/v1` trực tiếp → xóa dòng mount trùng, giữ lại đúng 1 dòng.
- [ ] **Model Vault thiếu ở frontend** — migration `v13_062_vault_document_metadata.py` thêm field (`stage`, `dimension`, `regulatory_sensitivity`, `source_version`, `last_verified`) chưa có Dart model — chưa làm, cần xác nhận UI có thực sự cần hiển thị các field này trước khi thêm.

---

## Trình tự thực hiện

1. **Phần 1** (dọn .md) — làm trước, review bằng `git status`.
2. **Phần 2** (đổi tên version) — chạy test sau mỗi bước.
3. **Phần 3** (làm phẳng backend) — thực hiện atomic theo đúng thứ tự 3.1 → 3.2 → 3.3 → 3.4 → 3.5, commit riêng một lần. Sau khi xong: `docker-compose build brain-api agent-worker`, `docker-compose up -d postgres minio migrate brain-api agent-worker`, kiểm tra log, gọi thử `/health`/`/auth/me`, chạy `pytest` toàn bộ, chạy `alembic upgrade head`.
4. **Phần 4** — sau khi backend chạy ổn định trên cấu trúc mới, sửa router trùng + fallback endpoint, test tay UI Agents/Tasks trên Flutter dev.

## Acceptance criteria — kết quả thực tế

- [x] `git status` sạch cho Phần 1 (đã stage, chưa commit — chờ user xác nhận commit).
- [x] `grep -rEn "\bfrom app\.|\bimport app\." backend --include="*.py"` (trừ `.venv`) → rỗng.
- [x] `import full_main`, `import central_main`, `import worker_main` — cả 3 entrypoint import sạch, không lỗi.
- [x] `docker compose config --quiet` — hợp lệ.
- [x] `alembic -c alembic.ini heads` → `v13_062_vault_document_metadata (head)`; `alembic -c alembic_control_plane.ini heads` → `c9a1f0b2e3d4 (head)` — cả 2 lịch sử migration resolve đúng với cấu trúc mới.
- [~] `docker compose build brain-api` — KHÔNG build được trong sandbox này do không có network để pull base image `python:3.11-slim` (timeout ở bước pull, không phải lỗi trong Dockerfile/code). Cần user tự chạy `docker compose build` trên máy có mạng để xác nhận lần cuối trước khi deploy.
- [x] `pytest` toàn bộ backend: 1563/1566 pass (không tính 42 skip). 3 test fail còn lại là **flaky pre-existing**, không liên quan tới đợt dọn dẹp này:
  - `tests/agents/delegation/test_delegation_api.py::test_delegation_api_is_workspace_scoped_and_retry_is_append_only`
  - `tests/integrations/test_scope_filtered_workflow_queries.py::test_workflow_run_list_filters_to_selected_offering_without_leaking_other_offering`
  - `tests/test_tool_registry.py::test_every_tool_declares_whether_chat_can_use_it`
  Bằng chứng: cả 3 (và 1-2 test tương tự khác thay phiên nhau) đã có mặt trong danh sách 49 lỗi ở lần chạy pytest ĐẦU TIÊN — trước khi bất kỳ thay đổi cấu trúc nào được thực hiện. Số lượng/tập lỗi thay đổi giữa các lần chạy giống hệt nhau (5→4→3), đặc trưng của DB dev thật bị tích lũy trạng thái giữa các lần chạy test, không phải regression từ việc làm phẳng cấu trúc.
- [ ] Test tay UI Agents/Tasks/Hub trên Flutter dev — CHƯA làm (cần chạy Flutter dev app thật để xác nhận, ngoài khả năng của phiên này).
