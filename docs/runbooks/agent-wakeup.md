# Runbook: Agent wakeup theo sự kiện (Dự án C)

Mục đích: khi một task WGA bị `blocked` (hoặc founder yêu cầu thủ công), người phụ trách được đánh thức để chạy một run **chỉ đọc**; nếu run thất bại, việc leo thang đi lên quản lý theo org chart rồi dừng ở "operator" (v1: chỉ là một dòng log WARNING, xem mục "Operator trong v1"). Thiết kế: [Dự án C](../superpowers/plans/2026-10-05-agent-structure-C-org-chart-heartbeat.md), kế hoạch: [impl plan](../superpowers/plans/2026-10-12-agent-structure-C-org-chart-wakeup-impl.md).

## Cờ và biến

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `AGENT_WAKEUP_ENABLED` | tắt | Bật toàn bộ wakeup (sweep, route thủ công, handler). Đọc lúc gọi; đổi biến rồi khởi động lại worker. |
| `AGENT_WAKEUP_MAX_PER_DAY` | 20 | Số wakeup tối đa trong 24 giờ cho mỗi assignment (rate cap). |
| `AGENT_WAKEUP_DEBOUNCE_SEC` | 30 | Độ trễ `run_at`; các sự kiện trong khoảng này gộp vào một lần chạy (coalescing key `wake:{ws}:{canonical_assignment}:{project}`). |
| `AGENT_WAKEUP_HOP_CAP` | 3 | Số bước leo thang tối đa; chạm trần thì dừng ở operator (chỉ log WARNING trong v1). |

Cờ chỉ bật khi `AGENT_WAKEUP_ENABLED` bằng đúng chuỗi `1`; các giá trị khác (như `true`) im lặng bị coi là tắt. Cờ **mặc định tắt**. Khuyến cáo: chỉ bật ở workspace/môi trường dev trước. Tắt cờ giữa chừng: handler thoát sớm, không chạy và không lên lịch mới; các hàng sổ cái chưa xử lý được giữ nguyên.

**Run wakeup v1 CHỈ ĐỌC** (`READ_ONLY_RUN_KEY`); không có quyền ghi nào được mở thêm. Org chart chỉ là đường leo thang, không nới capability hay autonomy của ai.

## Ánh xạ functional_key -> profile

`WAKE_PROFILE_BY_FUNCTIONAL_KEY` trong `apps/cosa/worker/wakeup_service.py`:

| functional_key | profile |
|---|---|
| `cashflow_planner` | finance |
| `accounting_document_specialist` | finance |
| `campaign_planner` | marketing |
| `founder_office_orchestrator` | operations |

Vắng trong bảng = không đánh thức được (`no_executable_profile`). Mở rộng: thêm cặp vào dict (profile phải có trong `AGENT_PROFILE_SPECS`) và thêm test.

## Autonomy thực tế

Ngưỡng `MIN_WAKE_AUTONOMY = L2`. Autonomy thật của spec: finance = L1, marketing = L0, operations = L2. Hệ quả: **hiện chỉ `founder_office_orchestrator` (operations) đánh thức được**; các key finance/marketing bị chặn `autonomy_below_minimum`. Muốn bật thêm phải đổi hằng `MIN_WAKE_AUTONOMY` hoặc autonomy của spec: đó là quyết định sản phẩm, không phải thao tác vận hành.

## Lý do của WakeOutcome

`status` là `scheduled`, `duplicate`, `suppressed` hoặc `operator`.

| reason | Nghĩa |
|---|---|
| `flag_off` | `AGENT_WAKEUP_ENABLED` tắt. |
| `invalid_assignment_id` | id không phải UUID. Mọi dạng UUID (hoa, không gạch, `{}`, `urn:uuid:`) được chuẩn hoá về chữ thường có gạch ngang trước khi vào sổ cái/rate cap/coalescing key; route thủ công trả 422. |
| `assignment_not_found` | assignment không tồn tại trong workspace. |
| `assignment_not_active` | assignment đã RETIRED/không ACTIVE. |
| `employee_not_active` | nhân viên (agent instance) gắn với assignment không ACTIVE. |
| `no_executable_profile` | functional_key không có trong bảng ánh xạ. |
| `autonomy_below_minimum` | autonomy của profile thấp hơn L2. |
| `hop_cap_reached` | số bước leo thang vượt/chạm trần; leo thang dừng, `status=operator` hoặc `suppressed`. |
| `rate_cap` | đã đủ `AGENT_WAKEUP_MAX_PER_DAY` trong 24 giờ. |
| `schedule_failed` | ghi sổ cái được nhưng schedule lỗi; hàng vẫn chưa xử lý, lần wakeup kế của cùng (assignment, project) sẽ nhặt lại. |
| `duplicate` (status) | khoá dedup là `(workspace, assignment, source_ref)`: cùng `source_ref` cho cùng assignment đã có trong sổ cái thì không đánh thức lần hai. Khoá KHÔNG gồm project và không có cửa sổ thời gian. |
| `no_manager` (status `operator`) | không còn quản lý hợp lệ ở trên: dừng ở operator (v1: chỉ log WARNING, không thông báo/hàng đợi/sổ cái). |

Khi leo thang, quản lý không đánh thức được vì các lý do tư cách (not_found, not_active, employee_not_active, no_executable_profile, autonomy_below_minimum) bị bỏ qua và việc leo tiếp lên quản lý kế (mỗi bước tăng hop nên luôn dừng).

## Operator trong v1

Trong v1, kết quả `operator` **chỉ** tạo một dòng log mức WARNING từ `apps/cosa/worker/agent_wakeup.py`; không có thông báo, hàng đợi, inbox hay hàng sổ cái nào. Mẫu để cảnh báo:

```
agent_wakeup failed (<failure>) ws=<workspace_id> assignment=<assignment_id> -> operator
```

Muốn biết có người cần can thiệp thì phải alert trên log này (lọc `agent_wakeup failed` và `-> operator`). Thông báo operator (queue/inbox/alert) nằm trong danh sách "Còn lại" của tài liệu thiết kế.

## Đọc sổ cái

```sql
SELECT wake_id, assignment_id, project_id, reason_kind, source_ref, hop, created_at, handled_at
FROM agent.workforce_wakeups
WHERE workspace_id = '<ws>'
ORDER BY created_at DESC;
```

Hàng `handled_at IS NULL` là chưa xử lý (đang chờ run, cờ đang tắt, hoặc schedule lỗi). `reason_kind`: `task_blocked`, `manual`, `wake_failed`; `hop` là số lần đã leo thang. Run wake có `principal = system:wake:<ws>` và run_id bắt đầu bằng `wake_`.

## API thủ công

`POST /agent/workforce/assignments/{assignment_id}/wakeups`, body `{ "project_id": "...", "reason": "..." }`. Chỉ `founder`/`co-founder` (403 nếu khác). Assignment ngoài workspace trả 404. Trả `{status, reason}` của `WakeOutcome`. `reason` chỉ được ghi log (cắt 80 ký tự), không vào sổ cái hay prompt. Cờ tắt trả `suppressed/flag_off`.

## Điểm kích hoạt trong v1

1. Sweep (`_maybe_escalate_blocked` trong `wga_run.py`): task `blocked` có `ownerAgentProfile` thuộc ánh xạ, đánh thức assignment ACTIVE cũ nhất có key tương ứng (`source_ref = task:<id>`).
2. Wake thất bại (run không COMPLETED hoặc lỗi): leo thang lên quản lý, `reason_kind=wake_failed`, `hop+1`.
3. Route thủ công ở trên.

## Hạn chế đã biết

- Dedup theo `(workspace, assignment, source_ref)`, không có cửa sổ thời gian và không gồm project: task bị blocked, được gỡ, rồi blocked lại sẽ **không** đánh thức lần hai vì `task:<id>` đã có trong sổ cái.
- Handler đọc `list_unhandled` với limit 20 mỗi lần thức dậy. Nếu nâng `AGENT_WAKEUP_MAX_PER_DAY` trên 20 thì các hàng vượt chờ sự kiện kế tiếp.
- CHECK `chk_workforce_assignments_no_self_report` được tạo `NOT VALID` nhưng vẫn được kiểm trên UPDATE của hàng đã có (một hàng tự báo cáo sẵn có sẽ làm retire lỗi). Trước khi bật: chạy kiểm dữ liệu (`reports_to_assignment_id = assignment_id`), hoặc lên kế hoạch migration VALIDATE sau.
- Route thủ công kiểm `project_id` bằng `verify_project_context` (project lạ/ngoài workspace trả 404, không ghi sổ cái, không schedule).
- Chưa có UI lịch sử wakeup, chưa có trần chi phí theo assignment (thay bằng rate cap), chưa có wakeup có quyền ghi. Xem mục "Còn lại" trong tài liệu thiết kế.
