# Test Reliability — GetX Global State & SSE Reconnect — Design

Status: DRAFT (chờ user review)
Ngày: 2026-09-14
Phạm vi: sub-project #6/6 (cuối cùng) trong đợt audit "Ba blocker lớn nhất"
(2026-09-14) — P2. Các sub-project khác có spec riêng:
[#1 Schedule Project scope](2026-09-14-schedule-project-scope-design.md),
[#2 Python quality gates](2026-09-14-python-quality-gates-design.md),
[#3 Semantic Knowledge production wiring](2026-09-14-semantic-knowledge-production-wiring-design.md),
[#4 Hub Workforce/Approval Project scope](2026-09-14-hub-workforce-approval-project-scope-design.md),
[#5 Flutter financial data fabrication](2026-09-14-flutter-financial-data-fabrication-design.md).

## Vấn đề

Audit nêu 2 vấn đề độ tin cậy kiểm thử:

1. Full Flutter test mặc định có 1 failure do shared global GetX state;
   chạy riêng và chạy toàn bộ với `--concurrency=1` đều xanh (788 tests).
2. Test SSE restart cần PostgreSQL disposable; trong môi trường audit hiện
   tại kết nối localhost bị sandbox chặn nên recovery/restart, RLS thật và
   cross-plane deployment vẫn là chưa xác minh, không phải "đã pass".

**Xác nhận lại trong code (2026-09-14):**

- `cd frontend && flutter test` → đúng 1 fail: `test/modules/hologram_hub/
  widgets/top3_focus_widget_checklist_test.dart` ("Top3FocusWidget displays
  actions and uses selectedProjectId in navigation"), trong tổng 787 test.
  Chạy riêng file này → pass.
- **Nguyên nhân xác định được:** `AppShellController.
  ensureShellDependencies()` (`frontend/lib/core/shell/
  app_shell_controller.dart:35-59`) đăng ký 6 controller
  (`FeatureFlagsController`, `DashboardController`, `HologramHubController`,
  `FounderCommandCenterController`, `ChatPanelController`,
  `AppShellController`) với `Get.put(..., permanent: true)`. `Get.reset()`
  (dùng trong `setUp`/`tearDown` của test, dòng 12,18) **mặc định không xóa
  permanent binding** — state nội bộ (`.obs`) của các controller này rò rỉ
  giữa các test file chạy trong cùng process. 12 file test dùng
  `ensureShellDependencies()`, 61 file dùng `Get.reset()` (49 file còn lại
  không đăng ký permanent controller nên không bị ảnh hưởng).
- `make apps-cosa-test` (chạy toàn bộ) → 1 ERROR ở
  `tests/apps/cosa/test_sse_reconnect_e2e.py::
  test_project_activity_stream_reconnect_survives_process_restart`. Chạy
  riêng file này → 2 skipped (sạch).
- **Nguyên nhân nghi ngờ hợp lý nhất (chưa xác nhận bằng debug có kiểm
  soát):** `db_session_factory` (`tests/apps/cosa/conftest.py:42-56`) là
  fixture đồng bộ, teardown gọi `asyncio.run(engine.dispose())` bên trong
  `request.addfinalizer` — pattern này là nguồn lỗi kinh điển với
  `pytest-asyncio`: nếu 1 test async khác chạy trước đó trong cùng suite đã
  đóng/thay đổi event loop mặc định, `asyncio.run()` ở finalizer của fixture
  này (hoặc fixture khác dùng chung pattern) có thể raise `RuntimeError`,
  biến `SKIP` sạch (khi chạy riêng) thành `ERROR` (khi chạy trong suite đầy
  đủ có test async khác chạy trước).

## Kiến trúc

### GetX isolation

Thay vì chiến lược serial (`--concurrency=1`) như audit đề xuất làm
workaround, sửa tận gốc bằng helper dùng chung:

```dart
// frontend/test/support/getx_test_isolation.dart
void resetGetXForTest() {
  Get.deleteAll(force: true); // force:true mới xóa được permanent binding
  Get.reset();
}
```

Áp dụng cho đúng 12 file dùng `ensureShellDependencies()` — thay
`Get.reset()` trong `setUp`/`tearDown` bằng `resetGetXForTest()`. 49 file
`Get.reset()` còn lại không đăng ký permanent controller, không cần đổi
(tránh sửa lan man ngoài phạm vi vấn đề thật).

### SSE reconnect fixture

Đổi `db_session_factory` từ sync fixture + `asyncio.run()`-trong-finalizer
sang async fixture thật:

```python
@pytest_asyncio.fixture
async def db_session_factory(postgres_dsn):
    engine = create_async_engine(postgres_dsn)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    yield session_factory
    await engine.dispose()
```

Loại bỏ hoàn toàn việc gọi `asyncio.run()` lồng trong finalizer, tránh xung
đột event loop với test async khác chạy trước trong cùng suite. **Đây là
hướng thiết kế dựa trên phân tích root cause hợp lý nhất, nhưng cần xác
nhận bằng systematic-debugging trong lúc implement** (tái tạo lỗi có kiểm
soát: chạy 1 test async khác trước rồi chạy fixture này, xác nhận lỗi xuất
hiện và biến mất sau khi sửa) — không tuyên bố chắc chắn khi chưa tái tạo
được nguyên nhân.

## Testing

**GetX isolation:**

1. Sau khi áp `resetGetXForTest()` cho 12 file: `make frontend-test` (toàn
   bộ, concurrency mặc định) → 0 fail, không cần `--concurrency=1`.
2. Test riêng: chạy `top3_focus_widget_checklist_test.dart` **sau** 1 test
   khác cố tình mutate `HologramHubController`/`FounderCommandCenterController`
   state (thứ tự cố định) → assert state đã sạch khi test sau bắt đầu.
3. Chạy lại toàn bộ suite nhiều lần liên tiếp (vd 3 lần) để loại trừ flaky
   do thứ tự test không cố định giữa các lần chạy.

**SSE reconnect:**

4. Chạy `test_sse_reconnect_e2e.py` **trong cùng lệnh** với toàn bộ
   `apps-cosa-test` (không tách riêng) → kết quả là `SKIP` sạch (không
   `ERROR`) khi không có Postgres disposable thật.
5. Với Postgres disposable thật (`make e2e-cross-plane-smoke` hoặc tương
   đương): assert test **PASS thật** (không skip) — bằng chứng "recovery/
   restart qua process thật" theo CLAUDE.md quy tắc 6, khác với chỉ "không
   còn ERROR".
6. Test riêng cho chính fixture: dựng 2 fixture dùng `db_session_factory`
   liên tiếp trong cùng session test (mô phỏng tình huống gây lỗi ban đầu)
   → assert không còn `RuntimeError` liên quan event loop ở fixture thứ 2.

**Gate tổng hợp:** `make frontend-test` (không cờ `--concurrency=1`) và
`make apps-cosa-test` (chạy đầy đủ, không tách riêng file SSE) đều phải
xanh — đây là tiêu chí "CI xác định" audit yêu cầu.

## Ngoài phạm vi (out of scope)

- Đổi toàn bộ 61 file dùng `Get.reset()` sang `resetGetXForTest()` — chỉ 12
  file thực sự đăng ký permanent controller mới cần đổi.
- RLS thật và cross-plane deployment verification nhắc tới trong audit ("...
  vẫn là chưa xác minh") — đó là hệ quả của việc thiếu Postgres disposable
  trong môi trường audit, không phải việc cần sửa code; một khi fixture
  chạy đúng với Postgres thật (mục 5 phần Testing), việc verify RLS/
  cross-plane tự động có bằng chứng qua đúng cơ chế `make
  e2e-cross-plane-smoke` đã tồn tại, không cần cơ chế mới.
