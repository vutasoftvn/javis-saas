---
name: operations-tasks
description: Phân rã mục tiêu thành công việc cụ thể, tạo task nháp kèm lý do và bằng chứng, và tra cứu trạng thái task hiện có.
---

# Điều Phối & Phân Rã Task (Task Orchestration & Decomposition)

## Mục đích & Giới hạn Quyền hạn
Chia nhỏ một mục tiêu lớn thành các đơn vị công việc cụ thể, tạo bản nháp task (draft) kèm lý do quyết định và bằng chứng dẫn chiếu, và tra cứu danh sách/trạng thái task hiện có.

> **Quy tắc an toàn & Quản trị vòng đời:**
> Skillpack này CHỈ được phép tạo task ở trạng thái nháp thông qua capability `operations.task.create_draft` — không tự ý đổi trạng thái task (`in_progress`, `done`, ...), không tự thay đổi project lifecycle stage, không tự phê duyệt evidence/gate. Việc cập nhật trạng thái task là hành động của con người qua giao diện quản lý tác vụ; agent không có capability nào cho việc này.

## Triggers
- Kích hoạt khi cần phân rã một mục tiêu/quyết định thành các công việc điều hành cụ thể.
- Kích hoạt khi cần tạo một task nháp có căn cứ bằng chứng để Founder/Admin xem xét.
- Kích hoạt khi cần tra cứu danh sách hoặc chi tiết task hiện có của dự án.

## Anti-triggers
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.
- Không kích hoạt để tự đổi trạng thái một task đã tồn tại (không có capability cho việc này — xem Fallback & Handoff).
- Không kích hoạt để tạo task không có `decision_reason` hoặc không có ít nhất một `evidence_refs`.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.
- `decision_reason`: Lý do quyết định tạo task, tối thiểu 5 ký tự — bắt buộc theo hợp đồng capability thật.
- `evidence_refs`: Danh sách tối thiểu 1 tham chiếu bằng chứng/tài liệu căn cứ cho task — bắt buộc theo hợp đồng capability thật.

## Evidence Rules
- Mọi task nháp phải dẫn chiếu ít nhất một `evidence_refs` thuộc cùng workspace; tham chiếu bằng chứng từ workspace khác bị từ chối.
- Không tự tạo bằng chứng để hợp thức hoá task của chính mình (anti-self-validation).

## Quy trình thực hiện (Steps)
1. **Phân rã mục tiêu**: Chia mục tiêu lớn thành các đơn vị công việc độc lập, mỗi đơn vị có tiêu đề bắt đầu bằng động từ hành động.
2. **Thu thập căn cứ**: Xác định `decision_reason` và các `evidence_refs` liên quan trong cùng workspace cho từng task.
3. **Tạo task nháp**: Gọi capability `operations.task.create_draft` với `project_id`, `title`, `priority`, `decision_reason`, `evidence_refs`.
4. **Tra cứu khi cần**: Dùng `operations.task.list`/`operations.task.read` để kiểm tra task đã tồn tại trước khi đề xuất tạo mới, tránh trùng lặp.

## Allowed Tool Calls
- `operations.task.create_draft` — tạo task nháp; luôn tạo ở trạng thái đề xuất, không tự kích hoạt (xem Required Context cho các trường bắt buộc).
- `operations.task.list` — liệt kê task theo dự án.
- `operations.task.read` — đọc chi tiết một task.

## Output Format
- **task-draft-proposal**: Task nháp kèm tiêu đề, mức ưu tiên, `decision_reason`, `evidence_refs` và trạng thái `todo` chờ con người xử lý.
- **task-list-summary**: Bảng tóm tắt task hiện có theo trạng thái, kèm liên kết task gốc.

## Fallback & Handoff
- Khi thiếu `decision_reason` hoặc `evidence_refs`, tạo Handoff yêu cầu người dùng bổ sung căn cứ trước khi đề xuất task.
- Khi cần đổi trạng thái một task đã tồn tại (`in_progress`, `waiting_approval`, `done`, huỷ...), tạo Handoff đề xuất Founder/Admin thực hiện trực tiếp qua giao diện quản lý tác vụ — skillpack này không có tool đổi trạng thái task.
  - Ngoại lệ hạ tầng (KHÔNG thuộc toolset skillpack này): với task do một AI member đảm nhận (materialize từ Execution Plan, WGA), worker `workspace_task_sweep` gọi capability `operations.task.advance` (`in_progress`/`done`/`blocked`) trực tiếp qua HTTP delegation — không qua kernel/skillpack. Agent trong skillpack này vẫn không tự đổi trạng thái.

## Eval Notes
- Suite: `evals/operations/tasks.yaml`
