# Business Agent Evals & Durability Verification

## 1. Overview & Objective

Tài liệu này tổng hợp bộ tiêu chuẩn đánh giá (Evals) và kiểm chứng độ bền (Durability) cho các Business Agents trong hệ thống COSA (Operations, Finance, Marketing, Customer Support Copilot & Autopilot) theo kế hoạch `2026-09-05-business-agents-runtime.md` (Task R4).

Bảo đảm:
1. **Business Correctness**: Khác biệt thực tế theo ngữ cảnh (project facts, knowledge snapshot).
2. **Policy & Governance Enforcement**: Zero tool calls khi bị rule deny; từ chối khi policy stale sau approval checkpoint.
3. **Truthful Outcome (F05)**: Run chỉ hoàn tất khi có artifact/evidence thật; output rỗng hoặc lỗi persist đều coi là thất bại; task WGA giữ `in_progress` kèm `completion_pending` nếu thiếu bằng chứng đo lường.
4. **Subprocess Durability**: Độ bền qua restart thực tế giữa các OS process độc lập (chứng minh bằng PIDs khác biệt).

---

## 2. Table-Driven Eval Cases (`test_business_agent_evals.py`)

| Case ID | Scenario | Expected Behavior | Verification Assertions |
|---|---|---|---|
| `EVAL-01` | **Same Input, Different Project Facts** | Cùng một câu prompt của user nhưng ngữ cảnh giai đoạn dự án khác nhau (P0 vs P5) phải tạo ra đề xuất hành động nghiệp vụ khác nhau. | `p0_proposal != p5_proposal`, đề xuất tương ứng `conduct_customer_interviews` vs `prepare_scale_architecture`. |
| `EVAL-02` | **Denied Rule Zero Tool Calls** | Khi policy engine hoặc tenant policy từ chối quyền thực thi capability, gateway không được phép gọi bất kỳ tool nào. | `gateway.execute.assert_not_awaited()`, `invoked_calls == 0`. |
| `EVAL-03` | **Malformed Model Output** | Khi model trả về output rỗng hoặc không khớp schema, `resolve_run_outcome` không được ngầm coi là thành công. | `resolve_run_outcome("COMPLETED", False, True) == "failed"`. |
| `EVAL-04` | **Founder Takeover Zero Sends** | Khi founder/human operator bật chế độ takeover trên thread, toàn bộ hành động tự động gửi tin nhắn bị chặn lại lập tức. | `delivered_message_count == 0`, status = `suppressed`. |
| `EVAL-05` | **Stale Policy After Approval** | Nếu policy của workspace thay đổi (thu hồi quyền) trong lúc checkpoint đang chờ duyệt, khi resume phải re-validate và từ chối thực thi. | `is_valid_on_resume is False`. |
| `EVAL-06` | **Artifact Failure Not Completed** | Dù model chạy xong nhưng việc lưu trữ artifact vào repository thất bại (disk full / db error), run không được báo completed. | `resolve_run_outcome("COMPLETED", True, False) == "failed"`. |
| `EVAL-07` | **No Metric Evidence Task Pending** | Hoàn thành task WGA mà chưa có S3 validateTaskCompletion hoặc thiếu bằng chứng metric phải giữ task ở trạng thái `in_progress` kèm note `completion_pending`. | `toStatus == "in_progress"`, `note == "completion_pending"`. |

---

## 3. Cross-Process Restart & Durability (`test_event_approval_restart.py`)

Kiểm chứng tính toàn vẹn và độ bền của cơ chế Approval Checkpoint qua restart thật:

```python
assert first_worker_pid != resumed_worker_pid
assert delivered_message_count == 1
assert completed_run_ids == [original_run_id]
assert approval_checkpoint_after_restart == approval_checkpoint_before_restart
```

- **Process A**: Nhận task, phát hiện hành động cần duyệt (`WAITING_APPROVAL`), persist checkpoint vào PostgreSQL/store rồi kết thúc process.
- **Process B**: Khởi động với PID mới, khôi phục checkpoint, kiểm tra policy và hoàn tất việc gửi tin.
- **Takeover Invariant**: Nếu founder kích hoạt takeover trước khi Process B resume, `delivered_message_count == 0`.
- **Company State Invariant**: Không tự ý re-enable autopilot nếu trạng thái đã bị disabled trên Company service.
