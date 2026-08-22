# Phase 12 — Production Hardening

> Chi tiết thực thi cho Phase 12 (cuối cùng) của `docs/architecture/COSA_IMPLEMENTATION_ROADMAP_2026-08-22.md`. Mục tiêu: security review toàn hệ thống theo đúng checklist đã tích luỹ xuyên suốt roadmap, performance baseline, và tài liệu vận hành cuối — không giới thiệu tính năng mới ở phase này.

## 12a. Security review

**Task — checklist đối chiếu ngược từng nguyên tắc đã đặt ra ở các phase trước, không lặp lại phân tích từ đầu:**

1. **Forbidden directions (§3.1, đã liệt kê trong roadmap tổng mục "KHÔNG được làm")** — chạy grep xác nhận từng điều:
   - `grep -r "cosa_core" services/ agentos/` → không có kết quả (không ai tái tạo `backend/cosa_core/`).
   - `grep -rn "legacy" services/realtime_agent/` → không có kết quả (đã fix ở Phase 3b/6b).
   - `grep -rn "legacy" agentos/orchestration/adk/` → không có kết quả (đã fix ở Phase 9b).
   - Rà `frontend/lib/` xác nhận không có import trực tiếp package DB nào (ví dụ postgres driver, ORM client) — Flutter chỉ gọi HTTP.
   - Rà `agentos/tools/clusters/*.py` xác nhận không handler nào chứa raw SQL/business logic thay vì gọi `services/` API.
2. **Trace redaction coverage (§7.4, Phase 0a)** — chạy lại bộ test redaction với danh sách pattern mở rộng hơn ban đầu (thêm các pattern phát sinh trong quá trình implement Phase 1-11, ví dụ token riêng của connector ở Phase 10b) — cập nhật `agentos/core/redaction.py` nếu phát hiện thiếu.
3. **No silent no-op (§14.3 + nguyên tắc chung đã áp dụng ở Phase 7B cho Memory)** — rà lại toàn bộ provider/adapter được thêm trong Phase 7-10 (Memory, Knowledge, Connector) xác nhận đều fail loudly khi thiếu dependency, không có nhánh nào "return im lặng".
4. **Tenant isolation** — chạy lại toàn bộ test isolation đã viết rải rác ở Phase 1a, 2d, 4b, 7C (cross-workspace/cross-company) như 1 bộ suite riêng, xác nhận 100% pass đồng thời (không chỉ pass riêng lẻ từng phase).
5. **Governance bypass check** — xác nhận không có code path nào gọi tool mà bỏ qua `evaluate_access()` (Phase 1c/10a): grep tìm mọi nơi gọi `handler(` trực tiếp trong `agentos/tools/` mà không qua `Executor`/`ToolRegistry` chuẩn.
6. **Approval integrity** — xác nhận không thể tạo `approval_id` giả hoặc replay quyết định approval cũ (test double-decision đã có ở Phase 8a, chạy lại + thêm test brute-force approval_id không hợp lệ).
7. **Secret/credential handling (Phase 10b connector)** — xác nhận vault/secret store không log token, `.env`/config file không commit secret thật (rà `git log` cho các file config đã sửa trong toàn bộ roadmap).

**Acceptance:**
- [ ] Toàn bộ 7 mục checklist trên có kết quả PASS ghi lại (không phải "đã kiểm tra bằng mắt", phải có lệnh/test cụ thể chạy được lại).
- [ ] Danh sách vi phạm phát hiện được (nếu có) đã fix hoặc có issue tracking rõ ràng trước khi coi Phase 12a hoàn tất.

## 12b. Performance baseline & optimization

**Task:**
1. Đo baseline cho các luồng chính bằng công cụ load test đã có trong repo (kiểm tra `infra/`/`tests/` xem đã có script load test nào chưa trước khi viết mới):
   - Chat message latency (p50/p99) — từ lúc gửi message tới `message.delta` đầu tiên xuất hiện.
   - Tool call latency (p50/p99) — riêng cho tool `risk_level=low` (không cần approval) vs tool cần approval (đo tới lúc `approval.required` xuất hiện, không tính thời gian chờ người duyệt).
   - Knowledge retrieval latency (Phase 7D) — từ query tới có kết quả citation.
   - Context building time (Phase 4c/7D) — thời gian `ContextBuilder.build()` với memory+knowledge+skill đầy đủ.
   - Approval pause/resume round-trip (Phase 8a) — từ lúc gọi decision API tới lúc run tiếp tục thực thi bước kế tiếp.
2. Load test với ít nhất 100 user đồng thời (theo mục tiêu đã đặt trong roadmap tổng), quan sát: có bottleneck ở tầng nào (DB connection pool, SSE connection limit, model provider rate limit).
3. Nếu phát hiện hotspot vượt SLO tự đặt (ví dụ p99 chat latency > 3s), tối ưu điểm đó — không tối ưu preemptive những chỗ chưa đo thấy vấn đề.

**Acceptance:**
- [ ] Baseline 5 metric trên được đo và ghi lại (file kết quả trong `docs/architecture/reports/` hoặc vị trí tương ứng đã có trong repo).
- [ ] Load test 100 concurrent user chạy được, không crash server, không mất dữ liệu (đối chiếu số message gửi vs số message persist đúng).
- [ ] Mọi hotspot phát hiện được đều có action cụ thể (fix hoặc ghi nhận chấp nhận được với lý do rõ ràng), không để "biết mà không xử lý, không giải thích".

## 12c. Tài liệu vận hành cuối

**Task:**
1. `docs/architecture/COSA_IMPLEMENTATION_COMPLETE.md` — tóm tắt những gì đã xây theo đúng 13 phase (0-12), trạng thái CURRENT cuối cùng của từng phase (không phải kế hoạch nữa mà là báo cáo hoàn thành), link tới từng file `docs/architecture/roadmap/phase-*.md` tương ứng.
2. `docs/COSA_RUNBOOK.md` — hướng dẫn vận hành: cách deploy từng thành phần (Flutter, `services/` Encore, `agentos/` Python, `realtime_agent`), cách monitor (OTEL dashboard từ Phase 10d, eval dashboard từ Phase 10c), quy trình xử lý sự cố cơ bản (ví dụ: approval bị kẹt không resume, trace sink đầy, memory backend down).
3. `docs/ADDING_BUSINESS_FEATURE.md` — hướng dẫn ngắn cho kỹ sư tiếp theo, trỏ thẳng vào `COSA_FEATURE_IMPLEMENTATION_TREE.md` (Phase 11a) làm quy trình bắt buộc, kèm ví dụ thực tế đã làm ở Phase 2 (Strategy domain) như case study.
4. Dọn `README.md` ở root repo — xác nhận chỉ còn hướng dẫn khởi động/onboarding (theo đúng §0.1 guide gốc: "README không được là nơi định nghĩa canonical architecture"), xoá bỏ mọi phần mô tả kiến trúc chi tiết đã trùng với `docs/architecture/`.
5. Test runbook: đưa cho 1 người chưa từng động vào phần này của repo, để họ thử làm theo runbook mà không hỏi thêm — ghi nhận chỗ nào runbook thiếu, bổ sung.

**Acceptance:**
- [ ] 3 tài liệu mới tồn tại, đủ chi tiết để dùng thật (không phải placeholder).
- [ ] README root không còn nội dung kiến trúc trùng lặp với `docs/architecture/`.
- [ ] Runbook đã được ít nhất 1 người ngoài đội thực hiện ban đầu thử follow thành công.

## Dependency

12a nên làm cuối cùng trong 3 mục (sau khi toàn bộ Phase 1-11 đã hoàn tất, để checklist có ý nghĩa đối chiếu đầy đủ). 12b độc lập, có thể bắt đầu sớm hơn khi Phase 4 (Chat) và Phase 8 (Approval) đã ổn định, không cần chờ 12a. 12c nên làm sau cùng (cần nội dung thật từ 12a/12b để viết báo cáo hoàn thành chính xác).

## Sau Phase 12 — trạng thái roadmap

Khi Phase 12 hoàn tất, `docs/architecture/COSA_IMPLEMENTATION_ROADMAP_2026-08-22.md` chuyển từ "Active implementation plan" sang tài liệu lịch sử — `COSA_IMPLEMENTATION_COMPLETE.md` (12c) trở thành điểm tham chiếu hiện hành, và `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md` cần 1 lượt cập nhật cuối để phản ánh đúng operational status "Active/Live" cho mọi capability đã hoàn thành thay vì "Planned/Transitional".
