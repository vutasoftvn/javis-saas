---
name: operations-sop-builder
description: Xây dựng tài liệu Standard Operating Procedure (SOP) từ một workflow lặp lại đã tồn tại trong vận hành, cho giai đoạn Scale & Govern.
---

# SOP Builder (Operations SOP Builder)

## Mục đích & Giới hạn Quyền hạn
Chuyển hoá một quy trình vận hành đã lặp lại nhiều lần (repeatable workflow) đang chạy trong thực tế thành tài liệu SOP có cấu trúc: mục tiêu, phạm vi, các bước thực hiện, vai trò/trách nhiệm, tiêu chí hoàn thành và điểm kiểm soát chất lượng, phục vụ giai đoạn P6_SCALE_GOVERN.

> **Quy tắc an toàn & Quản trị vòng đời:**
> Skillpack này CHỈ tạo dự thảo tài liệu (`sop-draft`). Tuyệt đối không tự ý ban hành SOP có hiệu lực, không tự thay đổi quy trình vận hành thật, và không tự thay đổi lifecycle stage. Mọi SOP bắt buộc phải có một **process owner được nêu tên cụ thể** (named process owner) chịu trách nhiệm phê duyệt và duy trì tài liệu; thiếu process owner là lý do từ chối tạo SOP hoàn chỉnh.

## Triggers
- Kích hoạt khi cần chuẩn hoá một workflow vận hành đã lặp lại thành tài liệu SOP chính thức trong giai đoạn P6_SCALE_GOVERN.
- Kích hoạt khi chuẩn bị hồ sơ cho stage gate G6 nhằm chứng minh khả năng vận hành có kiểm soát khi mở rộng quy mô.

## Anti-triggers
- Không kích hoạt khi workflow chưa từng chạy thực tế (không có bằng chứng lặp lại) — trường hợp này thuộc `operations.automation-design` hoặc thiết kế quy trình mới, không phải chuẩn hoá SOP.
- Không kích hoạt khi không xác định được `process_owner` cụ thể.
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.
- `process_owner`: Tên/vai trò người chịu trách nhiệm sở hữu quy trình — bắt buộc, không được để trống hoặc gán cho AI.

## Evidence Rules
- Bắt buộc liên kết SOP với bằng chứng vận hành thực tế: log thực thi, runbook nội bộ, phỏng vấn người thực hiện quy trình, hoặc dữ liệu tần suất lặp lại.
- Mọi bằng chứng trích xuất được tạo dưới dạng `candidate` và phải qua phê duyệt của process owner trước khi SOP được coi là chính thức.

## Quy trình thực hiện (Steps)
1. **Xác định phạm vi & Process Owner**: Ghi rõ tên workflow, tần suất chạy, và process owner chịu trách nhiệm — nếu không có process owner, dừng lại và tạo handoff.
2. **Thu thập bước thực hiện thực tế**: Đối chiếu log/runbook/phỏng vấn để liệt kê từng bước theo đúng thứ tự thực thi thật, không suy diễn.
3. **Cấu trúc hoá SOP**: Soạn mục tiêu, phạm vi áp dụng, vai trò/trách nhiệm (RACI tối giản), các bước, tiêu chí hoàn thành, và điểm kiểm soát chất lượng.
4. **Đóng gói Artifact**: Tạo bản nháp `sop-draft` kèm danh sách bằng chứng nguồn để process owner xem xét và phê duyệt.

## Allowed Tool Calls
Không có tool call trực tiếp (Artifact & Proposal only).

## Output Format
- **sop-draft**: Tài liệu SOP có cấu trúc gồm mục tiêu, phạm vi, process owner nêu tên, các bước thực hiện, vai trò/trách nhiệm, tiêu chí hoàn thành, điểm kiểm soát chất lượng.

## Fallback & Handoff
- Khi không xác định được process owner hoặc thiếu bằng chứng vận hành thực tế đủ tin cậy, tạo thông báo Handoff đề xuất Founder/quản lý vận hành chỉ định process owner và cung cấp thêm bằng chứng trước khi tiếp tục.

## Eval Notes
- Suite: `evals/operations/sop-builder.yaml`
