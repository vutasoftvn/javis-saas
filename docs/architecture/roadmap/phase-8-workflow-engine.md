# Phase 8 — Workflow Engine: Pause/Resume & Deterministic Procedure

> Chi tiết thực thi cho Phase 8 của `docs/architecture/COSA_IMPLEMENTATION_ROADMAP_2026-08-22.md`. Mục tiêu: approval pause/resume phải resume đúng run đang chạy (không tạo run mới làm mất causal chain, §5.3), và có engine cho deterministic multi-step agent procedure (retry, parallel, compensation) tách biệt khỏi business state machine (`services/`) và multi-agent orchestration (ADK, Phase 9).

## Bối cảnh

- `agentos/workflows/` đã tồn tại (theo audit thư mục ở Phase 0) nhưng chưa rõ mức độ hoàn thiện thật — **task đầu tiên của phase này là verify code hiện có**, không giả định trống hay giả định đã đủ.
- Approval hiện có `agentos/core/approval.py` (`ApprovalService`, model `Approval` với lifecycle PENDING/APPROVED/DENIED) — Phase 8 xây trên nền này, không viết lại approval model.
- Phụ thuộc trực tiếp Phase 4 (Agent API có route `POST /agent/approvals/{approval_id}/decision`, RunEvent persistence) — pause/resume thật cần điểm vào từ API đó.

## 8.0 — Verify `agentos/workflows/` hiện có (làm trước tiên)

**Task:**
1. Đọc toàn bộ file trong `agentos/workflows/` — liệt kê class/function đã có, đối chiếu với mục tiêu Phase 8 bên dưới.
2. Chạy test hiện có (`tests/agentos/workflows/` nếu có) để biết baseline đang pass/fail.
3. Xác định: có sẵn khái niệm "step", "checkpoint", "resume from step N" chưa, hay chỉ có khung rỗng.

**Acceptance:**
- [ ] Có báo cáo ngắn (comment trong PR đầu tiên của phase, không cần file riêng) liệt kê chính xác cái gì đã có, cái gì phải viết mới — tránh viết đè lên code đang hoạt động.

## 8a. Approval Pause/Resume (đúng 1 run, không tạo run mới)

**Task:**
1. Khi `Executor` (hoặc `AgentRuntimeAdapter` implementation đang chạy, theo Protocol từ Phase 0b) gặp tool cần approval (`evaluate_access()` trả `REQUIRE_APPROVAL`, Phase 1c/3a):
   - Tạo `Approval` record (dùng `ApprovalService` hiện có) gắn với `run_id` hiện tại + `tool_call` cụ thể (tool name, input đã redact) + vị trí checkpoint trong sequence tool call (ví dụ index thứ mấy trong chuỗi tool đang thực thi).
   - Emit event `approval.required` qua RunEvent (Phase 4b) — client (Text Chat/Voice) nhận qua SSE.
   - **Dừng thực thi run tại đây, không raise lỗi, không đóng run** — trạng thái run chuyển sang `PAUSED` (thêm trạng thái này vào enum status của run nếu chưa có).
2. Khi `POST /agent/approvals/{approval_id}/decision` (Phase 4a) nhận quyết định:
   - Lookup `Approval` theo `approval_id`, xác nhận vẫn ở trạng thái PENDING (reject nếu đã resolve trước đó — tránh double-decision).
   - Nếu APPROVED: resume đúng `run_id` gốc tại đúng checkpoint đã lưu — tiếp tục thực thi tool call đó rồi các bước còn lại của cùng run, **không khởi tạo `AgentRun` mới**.
   - Nếu REJECTED: đánh dấu tool call đó là "denied", run tiếp tục hoặc dừng tuỳ logic nghiệp vụ của tool đó (một số tool có thể có bước xử lý khi bị từ chối, ví dụ thông báo lại cho agent để nó đề xuất phương án khác thay vì crash toàn bộ run).
   - Emit event `approval.resolved` rồi tiếp tục stream `tool.started/tool.completed/...` bình thường trên cùng `run_id`.
3. Correlation ID (Phase 1a/3d) phải giữ nguyên xuyên suốt: trước pause, trong lúc chờ, và sau resume — dùng để trace toàn bộ vòng đời 1 run kể cả khi có gián đoạn hàng giờ chờ người duyệt.

**Acceptance:**
- [ ] Test: tool cần approval → run chuyển `PAUSED`, có `approval.required` event đúng payload.
- [ ] Test: gọi decision API với APPROVED → cùng `run_id` tiếp tục, không có `run_id` mới nào được tạo — assert trực tiếp bằng cách đếm số `AgentRun` record trước/sau.
- [ ] Test: gọi decision API với REJECTED → tool không thực thi, run có xử lý hợp lý (không crash không rõ lý do).
- [ ] Test: gọi decision API 2 lần cho cùng `approval_id` → lần 2 bị reject với lỗi rõ ràng (không double-execute).
- [ ] Test: `correlation_id` giống hệt nhau ở mọi event trước và sau resume.

## 8b. Deterministic Multi-Step Workflow

**Task:**
1. Định nghĩa workflow bằng cấu trúc khai báo (YAML hoặc Pydantic model trong Python, chọn theo pattern nhất quán với `skillpacks/`/`agentos/profiles/` đã dùng YAML) tại `agentos/workflows/definitions/`:
```yaml
id: strategy.gate-evaluation-flow
steps:
  - id: fetch_evidence
    type: tool_call
    tool: strategy.evidence.list
  - id: evaluate_gate
    type: tool_call
    tool: strategy.gate_evaluation.create
    depends_on: [fetch_evidence]
  - id: notify_founder
    type: tool_call
    tool: notification.send
    depends_on: [evaluate_gate]
    on_failure: compensate_notify
  - id: compensate_notify
    type: tool_call
    tool: notification.retry_or_log
```
2. Execution engine (`agentos/workflows/engine.py`) đọc định nghĩa, thực thi theo `depends_on` (tuần tự khi phụ thuộc, song song khi các step không phụ thuộc lẫn nhau và không tranh chấp cùng 1 resource ghi).
3. `on_failure` trỏ tới step compensation — nếu step chính fail, engine tự động chạy step compensation tương ứng thay vì để toàn bộ workflow crash.
4. Mọi step `type: tool_call` đi qua đúng `evaluate_access()` (Phase 1c) như tool call bình thường — workflow không phải đường tắt bỏ qua governance.
5. Checkpoint sau mỗi step hoàn thành — nếu quá trình bị gián đoạn (server restart), workflow có thể resume từ step cuối cùng đã checkpoint thành công thay vì chạy lại từ đầu (đặc biệt quan trọng cho step không idempotent).

**Acceptance:**
- [ ] Test: workflow 3 step tuần tự chạy đúng thứ tự, đúng dependency.
- [ ] Test: 2 step độc lập (không `depends_on` nhau) chạy song song, có đo thời gian xác nhận không chạy tuần tự.
- [ ] Test: step chính fail → compensation step tự động chạy, có log/event ghi lại rõ ràng.
- [ ] Test: mỗi `tool_call` step trong workflow vẫn bị `evaluate_access()` chặn nếu risk cao và agent chưa đủ quyền (không bypass governance).
- [ ] Test: giả lập gián đoạn giữa workflow (kill process sau step 1) → resume tiếp tục từ step 2, không chạy lại step 1 nếu step 1 không idempotent và đã checkpoint xong.

## Dependency

8.0 làm trước tất cả (verify code có sẵn). 8a phụ thuộc Phase 4a (route decision) + Phase 4b (RunEvent persistence) + Phase 1c (evaluate_access trả REQUIRE_APPROVAL). 8b phụ thuộc 8a (dùng chung cơ chế approval/governance cho step `tool_call`) — có thể bắt đầu song song 8a nếu engine cơ bản (không cần approval) được làm trước, rồi tích hợp approval sau khi 8a xong.
