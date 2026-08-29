# Runbook: Gia Cố Vòng Lặp Tự Hành & Điều Phối Bất Đồng Bộ (Autonomous Loop Hardening)

**Tài liệu tham chiếu:** `skillpacks/operations/loop-hardening/SKILL.md`  
**Chương trình:** [Chương trình tích hợp marketingskills + makerskills vào COSA](../integrations/2026-08-28-marketingskills-makerskills-program.md)  
**Mục đích:** Quy chuẩn kỹ thuật chi tiết về tính lũy đẳng (Idempotency), khóa thực thi phân tán (RunLease), hàng đợi gộp tác vụ (Coalescing Queue), kiểm soát lỗi, và các mẫu kiểm thử tự động.

---

## 1. Nghiêm Cấm Anti-Patterns Trong Môi Trường Tự Hành

> [!CAUTION]
> **Các hành vi bị nghiêm cấm tuyệt đối:**
> 1. **Self-Wakeup trong LLM Prompt:** Tuyệt đối không yêu cầu LLM tự gọi lại chính mình sau một khoảng thời gian chờ hoặc chạy vòng lặp `while True` bên trong prompt.
> 2. **Local Cron / Process Sleep:** Tuyệt đối không chạy lệnh `sleep` hoặc cài đặt cron daemon cục bộ trong container của agent.
> 3. **Non-Atomic Read-Then-Act:** Không kiểm tra trạng thái rồi mới ghi nếu không có khóa phân tán hoặc ràng buộc nguyên tử (Atomic Constraint) ở tầng cơ sở dữ liệu.

---

## 2. Ba Trụ Cột Kỹ Thuật Gia Cố (Hardening Pillars)

### 2.1. Tính Lũy Đẳng Nguyên Tử (`IdempotencyClaimService`)
- **Tài liệu tham chiếu mã nguồn:** `packages/agent/capabilities/idempotency.py`
- **Cơ chế:**
  - Khóa định danh duy nhất cho mỗi yêu cầu: `idempotency_key = hash(tenant_id, scope_kind, scope_key, capability_id, payload_hash)`.
  - Thực hiện đặt chỗ (Claim Reservation) nguyên tử bằng lệnh `INSERT ... ON CONFLICT DO NOTHING`.
  - Trả về các trạng thái xử lý rõ ràng:
    - `CLAIMED`: Worker giành quyền thực thi tác vụ.
    - `CACHED_COMPLETED`: Tác vụ đã hoàn tất trước đó, trả lại kết quả đã lưu trữ, không chạy lại handler.
    - `IN_PROGRESS`: Một worker khác đang xử lý, trả về thông báo chờ hoặc từ chối trùng lặp.
    - `RETRIED`: Lần chạy trước thất bại và đã đủ điều kiện an toàn để thử lại.

### 2.2. Khóa Thực Thi Phân Tán & Nhịp Tim (`RunLeaseManager`)
- **Tài liệu tham chiếu mã nguồn:** `packages/agent/runs/leases.py`
- **Cơ chế:**
  - Khóa thực thi phân tán (`RunLease`) ngăn chặn hiện tượng hai worker cùng xử lý một Run (Split-Brain).
  - Cấu hình mặc định: `default_lease_ttl_sec = 60s`, `heartbeat_interval_sec = 30s`.
  - Worker phải gửi nhịp tim (Heartbeat) định kỳ để gia hạn `expires_at`.
  - Nếu worker bị crash đột ngột, sau 60 giây lease sẽ hết hạn để worker khác có thể thu hồi (`acquire_lease`) và khôi phục trạng thái từ checkpoint gần nhất.

### 2.3. Hàng Đợi Gộp Tác Vụ Lập Lịch (`RunScheduler`)
- **Tài liệu tham chiếu mã nguồn:** `packages/agent/coordination/scheduler.py`
- **Cơ chế:**
  - Gom các tác vụ cùng bản chất phát sinh liên tiếp bằng `coalescing_key`.
  - Nếu đã có một bản ghi đang ở trạng thái `scheduled` với cùng `coalescing_key`, `RunScheduler` tự động gộp (coalesce) dữ liệu `input_payload` mới vào bản ghi hiện có thay vì tạo thêm hàng chục tác vụ trùng lặp.
  - Quản lý số lần thử lại với `claim_token`, `attempt_count` và trần `max_attempts: 5`.

---

## 3. Mẫu Kiểm Thử Tự Động (Hardening Test Template)

Dưới đây là mẫu kiểm thử chuẩn sử dụng `pytest` và `asyncio` để xác minh tính lũy đẳng và cơ chế gộp tác vụ:

```python
import pytest
import asyncio
from datetime import datetime, timezone
from packages.agent.coordination.scheduler import RunScheduler
from packages.agent.runs.leases import RunLeaseManager
from packages.agent.capabilities.idempotency import (
    IdempotencyClaimService,
    IdempotencyOutcome,
)
from packages.agent.runs.repository import InMemoryRunRepository


@pytest.mark.asyncio
async def test_scheduler_coalescing_deduplication():
    """Xác minh RunScheduler tự động gộp các tác vụ có cùng coalescing_key."""
    scheduler = RunScheduler()
    coalesce_key = "sync_marketing_context_tenant_123"

    # Lập lịch task 1
    task1 = await scheduler.schedule(
        target_spec_id="marketing.context-sync",
        input_payload={"page": 1, "status": "init"},
        coalescing_key=coalesce_key,
    )

    # Lập lịch task 2 trùng coalescing_key
    task2 = await scheduler.schedule(
        target_spec_id="marketing.context-sync",
        input_payload={"page": 2, "updated": True},
        coalescing_key=coalesce_key,
    )

    # Kỳ vọng: Task được gộp thành 1 task_id duy nhất và payload được cập nhật
    assert task1.task_id == task2.task_id
    assert task1.input_payload["page"] == 2
    assert task1.input_payload["status"] == "init"
    assert task1.input_payload["updated"] is True


@pytest.mark.asyncio
async def test_distributed_run_lease_heartbeat_expiry():
    """Xác minh RunLease tự động giải phóng khi worker mất kết nối quá thời gian TTL."""
    lease_manager = RunLeaseManager(default_lease_ttl_sec=1)
    run_id = "run_test_hardening_001"

    # Worker 1 lấy lease
    res1 = await lease_manager.acquire_lease(run_id=run_id, worker_id="worker_A", ttl_sec=1)
    assert res1.success is True

    # Worker 2 cố lấy lease ngay lập tức -> Thất bại
    res2 = await lease_manager.acquire_lease(run_id=run_id, worker_id="worker_B", ttl_sec=1)
    assert res2.success is False

    # Chờ lease hết hạn
    await asyncio.sleep(1.1)

    # Worker 2 thử lại sau khi worker 1 hết hạn -> Thành công
    res3 = await lease_manager.acquire_lease(run_id=run_id, worker_id="worker_B", ttl_sec=1)
    assert res3.success is True
    assert res3.lease.worker_id == "worker_B"
```

---

## 4. Danh Mục Kiểm Tra Cổng Ngắt Khẩn Cấp (Emergency Bail-Out Checklist)

Trước khi kích hoạt bất kỳ vòng lặp tự hành nào, đội ngũ phát triển phải xác nhận:
- [ ] Đã cấu hình giới hạn số lần retry tối đa (`max_attempts <= 5`).
- [ ] Đã có trường `coalescing_key` cho mọi tác vụ được trigger từ sự kiện webhook/sự kiện hệ thống.
- [ ] Đã tích hợp `IdempotencyClaimService` cho mọi tool call có side-effect ghi.
- [ ] Đã cấu hình trần chi phí token / ngân sách API hàng ngày theo từng Workspace.
- [ ] Đã thiết lập nút ngắt khẩn cấp (Emergency Kill Switch) trên giao diện Workspace Settings.
