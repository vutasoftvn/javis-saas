---
name: operations-twelve-week-year
description: Soạn dự thảo kế hoạch 12 tuần, đề xuất cam kết chiến thuật hàng tuần và cách tính điểm kỷ luật thực thi để con người nhập vào hệ thống.
---

# Hệ Thống Thực Thi 12 Week Year (12WY)

## Mục đích & Giới hạn Quyền hạn
Soạn dự thảo kế hoạch thực thi theo chu kỳ 12 tuần, đề xuất cam kết chiến thuật hàng tuần và cách tính điểm kỷ luật thực thi.

> **Quy tắc an toàn & Quản trị vòng đời:**
> Skillpack này CHỈ tạo dự thảo/đề xuất dạng văn bản. Hiện tại **chưa có agent capability nào** để tự tạo chu kỳ, kế hoạch tuần hoặc ghi nhận cam kết vào hệ thống Company (`services/company/operations/handlers/twelve-week-year.handler.ts` chỉ có API cho con người/UI gọi trực tiếp) — mọi việc nhập liệu thật phải do con người thực hiện qua giao diện quản lý.

## Triggers
- Kích hoạt khi cần soạn dự thảo kế hoạch 12 tuần mới.
- Kích hoạt khi cần đề xuất cam kết chiến thuật hàng tuần và cách chấm điểm kỷ luật thực thi.

## Anti-triggers
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.
- Không kích hoạt để tự tạo/cập nhật chu kỳ, kế hoạch hoặc điểm số trong hệ thống — không có capability nào cho việc này.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.

## Evidence Rules
- Đề xuất cam kết chiến thuật hàng tuần phải liên kết với mục tiêu trọng tâm của chu kỳ 12 tuần.

## Quy trình thực hiện (Steps)
1. **Triết lý**: Xem 12 tuần tương đương 1 năm trọn vẹn; trọng tâm là Điểm số thực thi (Execution Score) hàng tuần, không chỉ kết quả đầu ra.
2. **Soạn dự thảo kế hoạch**: Đề xuất ngày bắt đầu/kết thúc và mục tiêu trọng tâm cho chu kỳ 12 tuần.
3. **Đề xuất cam kết tuần**: Liệt kê các chiến thuật hàng tuần liên kết với mục tiêu trọng tâm.
4. **Đề xuất cách chấm điểm**: Mô tả công thức tính tỷ lệ % kỷ luật (số chiến thuật hoàn thành / số cam kết) để con người áp dụng khi nhập liệu; mục tiêu tham khảo là tối thiểu 85%.

## Allowed Tool Calls
Không có tool call trực tiếp (Artifact & Proposal only).

## Output Format
- **twelve-week-plan-draft**: Dự thảo kế hoạch 12 tuần kèm mục tiêu trọng tâm và khung thời gian.
- **weekly-commitment-proposal**: Đề xuất cam kết chiến thuật tuần và công thức tính điểm kỷ luật.

## Fallback & Handoff
- Khi cần tạo/cập nhật chu kỳ, kế hoạch hoặc điểm số thật trong hệ thống, tạo Handoff yêu cầu người dùng thực hiện qua giao diện quản lý — agent chưa có capability ghi dữ liệu này.

## Eval Notes
- Suite: `evals/operations/twelve-week-year.yaml`
