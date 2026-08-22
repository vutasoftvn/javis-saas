# Pre-Frontend Integration Readiness Report

**Ngày lập:** 2026-08-22
**Phạm vi khảo sát:** toàn bộ dự án trừ nội dung UI của `frontend/` (chỉ đọc `frontend/lib/core/network/api_client.dart` và các lời gọi `ApiClient.*` để đối chiếu endpoint, không phân tích UI/UX).
**Tài liệu liên quan:** `docs/architecture/adr/ADR-012-legacy-backend-agentos-services-integration-plan.md`, `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md` (mục "Newly-tracked capability families" + "migration status"), `docs/architecture/reports/2026-08-22-services-cluster-readiness.md`.

## 0. Cập nhật quan trọng (cùng ngày, sau khi báo cáo lần đầu được viết)

Mục §1 bên dưới ban đầu khẳng định `legacy/backend` là "hệ đang phục vụ traffic thật" — khẳng định này **sai**, đã kiểm chứng trực tiếp bằng build thật: commit gần nhất (`5c5bc85`) tách `backend/` cũ thành **6 thư mục** `legacy/{backend,agent_runtime,platform,business,domains,entrypoints}` mà không cập nhật Docker build. Thử build `brain-api` cho thấy thiếu import xuyên 6 thư mục (`workforce`/`cosa_core`/`agent_runtime`/`core`/`platform_core`/`business`/`business_core`/`regulations`/`founder_os`, tổng cộng ~42 import cross-directory).

**Quyết định đã chốt cùng người dùng (2026-08-22):** không cố khôi phục lại monolith 6-mảnh này. `legacy/backend` được "đóng băng tại chỗ" — giữ nguyên làm tài liệu tham khảo khi trích logic, nhưng không đầu tư công sức làm nó chạy lại hoàn chỉnh. `docker-compose.yml` đã gate `migrate`/`migrate-control-plane`/`brain-api`/`agent-worker` sau `--profile legacy` — mặc định `docker compose up` chỉ chạy phần đã xác nhận hoạt động (`postgres`/`minio`/`livekit`/`realtime-agent`/`realtime-agent-cloud`). Hướng đi tiếp theo: trích riêng LLM Gateway/OAuth/n8n/Sandbox thành adapter cho `agentos/` (xem ADR-012 Decision), không resurrect toàn bộ.

**Bài học rộng hơn:** nhiều tài liệu trong repo (ownership map, ghi chú "Phase 1: done" của chính `services/operations`, bản nháp đầu của ADR-012) khẳng định điều gì đó là canonical/đang chạy/đã xong nhưng sai khi đối chiếu build/grep thật. Tài liệu ở đây đáng tin cho *ý định và quyết định*, không đáng tin cho *trạng thái đang chạy* — cần build/grep xác minh trước khi dựa vào bất kỳ khẳng định "canonical/done" nào để ra quyết định mới. **Kết luận cập nhật: hiện không có backend nào được xác nhận chạy được end-to-end** — cả 3 hệ đều chưa sẵn sàng phục vụ frontend theo cách khác nhau.

## 1. Phát hiện cốt lõi: 3 hệ backend, chỉ 1 hệ đang phục vụ traffic thật (⚠️ xem cập nhật §0 — hiện cũng đang gãy hạ tầng)

| Hệ | Vai trò hiện tại | Bằng chứng |
|---|---|---|
| `legacy/backend` (FastAPI) | **Đang chạy thật** — `brain-api` (:8000) + `agent-worker` qua `docker-compose.yml` root | README trước đây không nhắc tới nhưng docker-compose vẫn định nghĩa đủ service, healthcheck |
| `agentos/` (Python Agent Core) | Runtime mới, **inert** — chưa wire vào bất kỳ entrypoint sản xuất nào | `ADR-AGENTOS-001`: "production traffic keeps flowing through cosa_core/workforce; agentos/ is inert... until a later phase explicitly cuts traffic over" |
| `services/` (Encore, 4 cluster) | Business Core mới, Phase 1 **parity-tested độc lập**, chưa có consumer thật | Plan `services/operations`: "No existing consumer calls services/tasks or services/okr over HTTP today" |

`docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md` (trước khi cập nhật trong phiên này) chỉ mô tả `legacy/backend` (`backend/workforce/...`) là canonical — không hề nhắc tới `agentos/`/`services/`. Đã bổ sung 2 mục mới vào file này (xem §Newly-tracked capability families, §migration status) để không còn "capability mồ côi".

## 2. Đối chiếu endpoint frontend cần vs endpoint `services/` đã có (Phase 4 audit)

Quét toàn bộ lời gọi `ApiClient.get/post/put/patch/delete(...)` trong `frontend/lib` (48 file, ~200+ lời gọi), thu được **31 namespace endpoint gốc** frontend đang dùng:

```
/admin /agent /agents /ai /artifacts /auth /business /channels /cofounder
/connectors /devices /execution /legal /marketing /okrs /org /outcomes
/platform /plugins /policy-programs /projects /runs /runtime /skills
/strategy /tasks /tech-radar /vault /workflows /workforce /workspace /workspaces
```

`ApiClient.normalizeEndpoint()` chỉ biết rewrite **4 trong 31** namespace này sang route `services/` thật:
- `/auth/*` → `/identity/*`
- `/tasks*` → `/operations/tasks*`
- `/strategy/*` → `/operations/*`
- `/marketing/*` → `/commercial/marketing/*` — **nhưng domain Marketing chưa được port vào `services/commercial`** (xem readiness report cluster) → route này sẽ 404 dù có mapping.

`/sales/*` cũng có rule rewrite nhưng **không xuất hiện trong danh sách 31 namespace thực tế đang được gọi** — cho thấy màn hình CRM/Sales trong frontend hiện chưa gọi qua `ApiClient` (hoặc chưa build), rule tồn tại "đón đầu".

**27 namespace còn lại** (`/admin`, `/agent`, `/agents`, `/ai`, `/artifacts`, `/business`, `/channels`, `/cofounder`, `/connectors`, `/devices`, `/execution`, `/legal`, `/okrs`, `/org`, `/outcomes`, `/platform`, `/plugins`, `/policy-programs`, `/projects`, `/runs`, `/runtime`, `/skills`, `/tech-radar`, `/vault`, `/workflows`, `/workforce`, `/workspace`, `/workspaces`) **không được `normalizeEndpoint()` rewrite** — nếu `baseUrl` là `:4000`, các request này đi thẳng `http://localhost:4000/admin/...` v.v., và **không có route nào như vậy trong 4 cluster `services/`** (đã xác nhận qua danh sách tool/route ở `agentos/tools/clusters/*.py` và migration plan từng cluster). Chúng chỉ tồn tại ở `legacy/backend`.

Ngay cả 2 namespace tưởng đã có ở `services/finance-legal` cũng lệch tên: frontend gọi `/legal/obligations`, `/legal/checklist`, nhưng route thật trong `services/finance-legal` là `/finance-legal/legal/obligations`, `/finance-legal/legal/checklists` (theo `agentos/tools/clusters/finance_tools.py`) — `normalizeEndpoint()` không có rule cho `/legal/` nên request này cũng sẽ đi sai.

**Kết luận:** nếu kết nối `frontend/` vào `:4000` ngay bây giờ, đa số màn hình (ước lượng 27/31 ≈ 87% namespace) sẽ gọi vào route không tồn tại. Đây là bằng chứng cụ thể nhất cho khuyến nghị "chưa sẵn sàng cắt hẳn sang `services/`".

## 3. Gap kỹ thuật trong `agentos/` (đã xử lý một phần trong phiên này)

| Gap | Trạng thái sau phiên này |
|---|---|
| Executor không kiểm tra PolicyEngine/ApprovalService trước khi gọi tool | **Đã sửa** — `agentos/core/executor.py` giờ evaluate `PermissionClass` của mỗi `ToolSpec` trước khi invoke; `REQUIRE_APPROVAL` dừng vòng lặp và tạo `Approval` (không tự động bỏ qua); `DENY` raise lỗi. `agentos/core/runtime.py` chuyển `AgentRun` sang `WAITING_APPROVAL`/`FAILED` tương ứng. 4 cluster tool (`operations_tools.py`, `commercial_tools.py`, `finance_tools.py`) đã gắn `permission_class` cho các hành động ghi dữ liệu (`MODIFY_BUSINESS_DATA`/`FINANCIAL_ACTION`). Test: `tests/agentos/test_executor.py` (+4 test case mới), toàn bộ `tests/agentos` (209 test) pass. |
| Trace/Memory chỉ in-memory, mất khi tiến trình dừng | **Trace: đã sửa** — thêm `agentos/core/trace_sink.py::SqliteTraceSink` (đúng CLAUDE.md §10: SQLite cho sessions/trace/cache), nối vào `AgentRuntime`/`factory.build_default_runtime()`, mặc định bật khi dùng factory thật. Test: `tests/agentos/test_trace_sink.py`. **Memory (PgVectorMemoryStore): chưa wire** — cần `session_factory` Postgres thật từ entrypoint gọi, không tự dựng kết nối giả trong phiên này; để lại làm việc tiếp theo rõ ràng thay vì fake. |
| Multi-agent delegation có hạ tầng nhưng chưa production-wired | Không đổi — chưa có use case nghiệp vụ thật cần nó (đúng khuyến nghị CLAUDE.md §18, không bật khi chưa cần). |
| 5 capability family (LLM Gateway, OAuth, n8n, Sandbox, Extensions) không có ở `services/`/`agentos/` | Không code trong phiên này (rủi ro cao, cần ADR riêng đã có — ADR-012) — đã ghi nhận owner + điều kiện migrate vào ownership map. |

## 4. Dọn dẹp tài liệu đã thực hiện

- Di chuyển vào `docs/architecture/_archive/`: `legacy_specs/mCOSA_V13_Focused_Company_Cycle_OS_Claude_Code_Implementation.md`, `legacy_specs/myiris.md`, `agent-platform/{CURRENT_ARCHITECTURE,GAP_ANALYSIS,IMPLEMENTATION_PLAN,MIGRATION_MAP}.md` — mỗi file có ghi chú đầu trang trỏ tài liệu hiện hành. **Giữ lại** `docs/agent-platform/ADK_INTEGRATION.md` tại chỗ cũ — nội dung đã được viết lại 2026-08-21+ để mô tả `AdkCofounderWorkflow` đã ship, không lỗi thời như 4 file kia (agent khảo sát ban đầu gộp nhầm cả 5 file vào "stale").
- README.md: bỏ link chết `docs/LOCAL_INSTALLATION_GUIDE.md`, thêm mục "Hai Hệ Backend Song Song" giải thích rõ `:8000` (legacy, đang chạy thật) vs `:4000` (đích, chưa có consumer).
- Hợp nhất trạng thái Phase 1 parity 4 cluster vào `docs/architecture/reports/2026-08-22-services-cluster-readiness.md` (không xoá 4 file plan gốc).
- `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md`: thêm bảng 5 capability family "mồ côi" + đoạn "migration status" giải thích tình trạng inert của `agentos/`+`services/`.
- ADR mới: `docs/architecture/adr/ADR-012-legacy-backend-agentos-services-integration-plan.md`.

## 5. Khuyến nghị trước khi kết nối Frontend thật sự

1. **Không point toàn bộ `frontend/` vào `:4000` ngay** — chỉ 4/31 namespace có route thật, và 1 trong 4 (`marketing`) trỏ vào domain chưa port.
2. Với từng namespace còn thiếu, quyết định theo ADR-012: (a) port sang `services/` nếu là business data thuần (vd `/okrs`, `/projects`, `/vault`), hay (b) giữ ở `legacy/backend` và thêm adapter Tool trong `agentos/` nếu là integration (LLM/OAuth/n8n/sandbox/extensions — namespace `/ai`, `/agent`, `/agents`, `/plugins`, `/channels`, `/connectors`, `/devices`, `/runtime`).
3. Sửa `normalizeEndpoint()` chỉ nên làm **sau** khi route đích thật sự tồn tại ở `services/` — tránh lặp lại tình trạng rule tồn tại nhưng route đích chưa port (như `/marketing/` hiện tại).
4. Trước khi tuyên bố "sẵn sàng nối frontend", cần ít nhất 1 test tích hợp thật: agent gọi tool → `services/` cluster → trả kết quả về, đi qua PolicyEngine/ApprovalService đã wire trong phiên này.
