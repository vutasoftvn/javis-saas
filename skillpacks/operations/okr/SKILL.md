---
name: operations-okr
description: Soạn dự thảo chu kỳ OKR, phân rã mục tiêu (Objectives) và đề xuất cách đo lường kết quả then chốt (Key Results) để con người nhập vào hệ thống.
---

# Quản Lý & Căn Chỉnh OKR (Objectives & Key Results)

## Mục đích & Giới hạn Quyền hạn
Soạn dự thảo chu kỳ OKR, phân rã Objective và đề xuất Key Result đo lường được, dựa trên định hướng chiến lược hiện có.

> **Quy tắc an toàn & Quản trị vòng đời:**
> Skillpack này CHỈ tạo dự thảo/đề xuất dạng văn bản. Hiện tại **chưa có agent capability nào** để tự tạo chu kỳ OKR, Objective, Key Result hoặc ghi nhận check-in vào hệ thống Company (`services/company/operations/handlers/okr.handler.ts` chỉ có API cho con người/UI gọi trực tiếp) — mọi việc nhập liệu thật phải do con người thực hiện qua giao diện quản lý OKR.

## Triggers
- Kích hoạt khi cần soạn dự thảo chu kỳ OKR mới hoặc phân rã Objective thành Key Result.
- Kích hoạt khi cần đề xuất cách đo lường tiến độ Key Result dựa trên báo cáo thực tế.

## Anti-triggers
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.
- Không kích hoạt để tự tạo/cập nhật OKR trong hệ thống — không có capability nào cho việc này.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc (nếu OKR gắn với một dự án cụ thể).

## Evidence Rules
- Đề xuất Key Result phải nêu rõ giá trị khởi đầu, giá trị mục tiêu và nguồn số liệu tham chiếu (nếu có).

## Quy trình thực hiện (Steps)
1. **Nguyên tắc thiết lập**: Objective định tính, truyền cảm hứng, ngắn gọn, có thời hạn (thường theo Quý); mỗi Objective có 2-5 Key Result định lượng.
2. **Soạn dự thảo chu kỳ**: Đề xuất khung thời gian và các Objective ứng viên dựa trên định hướng chiến lược.
3. **Phân rã Key Result**: Với mỗi Objective, đề xuất Key Result có `startValue`, `targetValue` rõ ràng.
4. **Đề xuất cách tính điểm**: Mô tả công thức đo tiến độ tổng thể (tỷ lệ hoàn thành trung bình 0.0–1.0) để con người áp dụng khi nhập liệu.

## Allowed Tool Calls
Không có tool call trực tiếp (Artifact & Proposal only).

## Output Format
- **okr-cycle-draft**: Dự thảo chu kỳ OKR gồm khung thời gian và danh sách Objective đề xuất.
- **key-result-proposal**: Đề xuất Key Result kèm giá trị khởi đầu/mục tiêu và nguồn số liệu.

## Fallback & Handoff
- Khi cần tạo/cập nhật OKR thật trong hệ thống, tạo Handoff yêu cầu người dùng thực hiện qua giao diện quản lý OKR — agent chưa có capability ghi dữ liệu này.

## Eval Notes
- Suite: `evals/operations/okr.yaml`
