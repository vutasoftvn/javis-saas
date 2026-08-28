---
name: operations-loop-hardening
description: Hướng dẫn gia cố vòng lặp tự hành (Loop Hardening), kiểm soát lũy đẳng (Idempotency), khóa phân tán (RunLease) và chống tự đánh thức trong prompt.
---

# Quy Trình Gia Cố Vòng Lặp Tự Hành & Điều Phối Bất Đồng Bộ (Autonomous Loop Hardening)

## 1. Mục Tiêu (Objective)
Thiết lập các tiêu chuẩn gia cố kỹ thuật (Hardening Standards) cho các tác vụ tự hành chạy nền hoặc theo chu kỳ, đảm bảo tính lũy đẳng (Idempotency) của các hành động ghi, kiểm soát khóa thực thi phân tán chống phân mảnh (Distributed RunLeases), và chống các mẫu thiết kế lỗi (Anti-patterns) như tự kích hoạt cron nội bộ trong prompt. Quy trình và mã kiểm thử chi tiết được ghi nhận tại `docs/runbooks/loop-hardening.md`.

## 2. Khi Nào Dùng & Khi Nào Không Dùng (When to use & When NOT to use)
- **Khi nào dùng**:
  - Khi thiết kế hoặc cấu hình các tác vụ định kỳ tự động (Scheduled Tasks, Background Workers, Polling Services).
  - Khi cần bảo đảm một tác vụ gọi công cụ (tool call) có side-effect kinh doanh chỉ được thực thi duy nhất 1 lần (Exactly-once execution via Idempotency).
  - Khi kiểm toán độ an toàn của hệ thống trước khi đưa các luồng tự hành lên môi trường production.
- **Khi nào KHÔNG dùng**:
  - Khi chỉ quản lý danh sách công việc tác vụ thông thường của người dùng (dùng `tasks`).
  - Khi thực hiện tổng kết tuần của founder (dùng `core.weekly-review`).

## 3. Điều Kiện Tiên Quyết (Prerequisites)
- Hiểu rõ cơ chế điều phối của COSA Agent Core:
  - `IdempotencyClaimService` (`packages/agent_core/capabilities/idempotency.py`)
  - `RunLeaseManager` (`packages/agent_core/runs/leases.py`)
  - `RunScheduler` (`packages/agent_core/coordination/scheduler.py`)

## 4. Các Bước Tất Định (Deterministic Steps)
1. **Kiểm Soát Tính Lũy Đẳng Cho Tác Vụ Ghi (Atomic Idempotency Reservation)**:
   - Mọi hành động có side-effect (ghi dữ liệu, thanh toán, gửi thông báo) bắt buộc phải tạo `idempotency_key` tất định dựa trên `(tenant_id, scope_kind, scope_key, capability_id, payload_hash)`.
   - Trước khi thực thi handler, Gateway gọi `IdempotencyClaimService.try_claim()`. Nếu nhận `CACHED_COMPLETED` hoặc `IN_PROGRESS`, trả lại kết quả đã lưu hoặc từ chối chạy trùng lặp.
2. **Khóa Thực Thi Phân Tán & Cơ Chế Nhịp Tim (Distributed RunLease & Heartbeat)**:
   - Worker nhận thực thi một Run phải lấy khóa qua `RunLeaseManager.acquire_lease(run_id, worker_id)`.
   - Duy trì nhịp tim (Heartbeat) định kỳ 30 giây để gia hạn lease (`expires_at`). Nếu worker bị crash, lease tự động hết hạn để worker khác thu hồi và phục hồi trạng thái.
3. **Gộp Tác Vụ & Chống Quá Tải Hàng Đợi (Work Queue Coalescing)**:
   - Các tác vụ lập lịch tương tự nhau phát sinh trong cùng một khoảng thời gian phải dùng chung `coalescing_key` qua `RunScheduler.schedule()`.
   - Hệ thống tự động gộp (coalesce) payload thay vì xếp chồng hàng trăm job trùng lặp.
4. **Hạn Mức Thử Lại & Ngắt Mạch Khẩn Cấp (Retry Budget & Circuit Breaker)**:
   - Giới hạn số lần thử lại tối đa (`max_attempts: 5`). Áp dụng thuật toán Exponential Backoff kèm ngẫu nhiên hóa (Jitter).
   - Khi tỷ lệ lỗi vượt quá ngưỡng cho phép trong 5 phút, Circuit Breaker tự động chuyển sang trạng thái `OPEN` để ngừng phát lệnh và thông báo cho người quản trị.
5. **Cơ Chế Ngắt Khẩn Cấp (Emergency Bail-Out Trigger)**:
   - Thiết lập điều kiện dừng tức thì khi: Phát hiện tiêu thụ chi phí/token vượt hạn mức (Budget Cap), phát hiện vòng lặp vô hạn, hoặc có lệnh can thiệp dừng khẩn cấp từ Workspace Admin.

## 5. Tool Calls Được Phép (Allowed Tool Calls)
Không có tool call runtime nào được khai báo cho skillpack này.
Quy trình được thực thi và kiểm thử thông qua các module chuẩn của agent_core.

## 6. Yêu Cầu Bằng Chứng (Evidence Requirements)
- Mọi thiết kế vòng lặp tự hành phải có bằng chứng kiểm thử đơn vị (Unit Test) và kiểm thử phục hồi sau sự cố (Recovery Test) theo mẫu chuẩn trong `docs/runbooks/loop-hardening.md`.

## 7. Safe Fallback & Nghiêm Cấm Anti-Patterns (Zero Self-Wakeup Policy)
- **Nghiêm cấm tuyệt đối các Anti-Patterns sau:**
  - **CẤM TỰ ĐÁNH THỨC TRONG PROMPT (No Self-Wakeup in LLM Prompts):** Nghiêm cấm chỉ thị cho model tự chạy vòng lặp vô hạn (ví dụ: *"Sau khi xong, hãy tự gọi lại chính mình sau 5 phút"*).
  - **CẤM CRON LOCAL / SLEEP:** Nghiêm cấm chạy lệnh `sleep` hoặc cấu hình cron local trực tiếp trong môi trường shell của container.
  - **Quy định chuẩn:** Toàn bộ việc lập lịch và kích hoạt lại phải do `RunScheduler` hoặc Durable Postgres Queue của hạ tầng AgentOS quản lý độc lập với ngữ cảnh của prompt.

## 8. Định Dạng Đầu Ra (Output Format)
```markdown
# Báo Cáo Đánh Giá An Toàn Vòng Lặp Tự Hành (Loop Hardening Audit)

## 1. Thông Tin Tác Vụ & Phạm Vi Điều Phối
- **Tên tác vụ / Service**: [Tên dịch vụ hoặc quy trình]
- **Loại điều phối**: `RunScheduler (Coalescing Queue)`
- **Coalescing Key**: `[prefix]_[tenant_id]_[entity_id]`

## 2. Kiểm Soát Tính Lũy Đẳng & Khóa Phân Tán
- **Idempotency Strategy**: `IdempotencyClaimService (INSERT ON CONFLICT DO NOTHING)`
- **Khóa phân tán (RunLease)**: TTL `[60s]`, Heartbeat Interval `[30s]`
- **Ngưỡng Retry**: Tối đa `[5]` lần, Exponential Backoff

## 3. Điều Kiện Dừng Khẩn Cấp (Bail-Out Triggers)
- [ ] Vượt trần ngân sách token ($X / ngày)
- [ ] Phát hiện lỗi liên tiếp 3 chu kỳ
- [ ] Tín hiệu dừng từ Workspace Admin
```

## 9. Xử Lý Lỗi & Edge Cases (Failure & Edge Case Handling)
- **Worker bị mất kết nối mạng đột ngột (Zombie Worker)**: Khi lease hết hạn, worker mới nhận quyền sở hữu run và tải lại checkpoint hợp lệ gần nhất, worker cũ bị hủy bỏ khi cố gắng cập nhật với lease token đã hết hạn.
- **Tắc nghẽn hàng đợi (Queue Jam)**: Kích hoạt cơ chế coalescing để nén các tác vụ chờ thành 1 bản ghi duy nhất.

## 10. Nguồn (Review Record)
```yaml
upstream:
  repository: coreyhaines31/makerskills
  commit: 33cb3870685a34522d91287869aef62170bdbcf7
  skill: loopify
  upstream_version: 1.0.0
  license: MIT
adaptation:
  kept:
    - Nguyên tắc thiết kế vòng lặp tự hành, Kiểm soát tính lũy đẳng, Cơ chế bail-out khẩn cấp
  changed:
    - Chuyển đổi từ mô hình cron cục bộ sang kiến trúc điều phối phân tán COSA
    - Chuẩn hóa sang cấu trúc 10 mục bắt buộc và định dạng markdown tiếng Việt
  added:
    - Tích hợp trực tiếp với IdempotencyClaimService, RunLeaseManager và RunScheduler
    - Nghiêm cấm tuyệt đối self-wakeup và cron local trong prompt
    - Mẫu kiểm thử phục hồi lỗi phân tán trong runbook
  excluded:
    - Loại bỏ các script shell cron và polling vô hạn không có heartbeat
```
