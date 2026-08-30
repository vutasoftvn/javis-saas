---
name: ai-evaluation-design
description: Thiết kế bộ dữ liệu kiểm thử vàng (Golden Dataset), tiêu chí đánh giá chất lượng (Eval Rubrics) và đo lường độ chính xác/độ trễ/chi phí cho các tính năng AI.
---

# Thiết Kế Đánh Giá Tính Năng AI (AI Evaluation Design)

## Mục đích & Giới hạn Quyền hạn
Xây dựng khung đánh giá chất lượng cho các agent và tính năng AI trong giải pháp, bao gồm: Tập dữ liệu mẫu vàng (Golden Dataset), thang đo độ chuẩn xác (Accuracy/Precision/Recall), tiêu chí đo lường hallucination, độ trễ p95 và chi phí token trên mỗi tác vụ trong P3_BUILD_VALIDATE.

> **Quy tắc an toàn & Quản trị vòng đời:**
> Skillpack này CHỈ phân tích và thiết kế khung kiểm thử (`L0_OBSERVE`). Không tự ý thay đổi model provider hay bypass các bộ lọc an toàn của hệ thống.

## Triggers
- Kích hoạt khi xây dựng tính năng AI/Agent và cần thiết lập hệ thống benchmark chất lượng.

## Anti-triggers
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.

## Evidence Rules
- Mọi bài kiểm thử AI phải ghi nhận rõ số lượng test cases, tỷ lệ đạt/không đạt và chi phí ước tính.

## Quy trình thực hiện (Steps)
1. **Xác định Tiêu chí Đo lường**: Định nghĩa độ chính xác định lượng, độ liên quan (Relevance), và khả năng tuân thủ cấu trúc dữ liệu JSON.
2. **Xây dựng Golden Dataset**: Thu thập 50-100 mẫu input/output chuẩn đại diện cho các tình huống nghiệp vụ thực tế.
3. **Thiết kế Automated Evals**: Cấu hình các kịch bản kiểm tra tự động chạy qua framework `pytest` hoặc LLM-as-a-judge.
4. **Đóng gói AI Evaluation Plan**: Tạo tài liệu `ai-eval-spec` phục vụ đội ngũ phát triển.

## Allowed Tool Calls
Không có tool call trực tiếp (Artifact & Proposal only).

## Output Format
- **ai-evaluation-plan**: Kế hoạch đánh giá AI toàn diện kèm danh mục kiểm thử vàng.

## Fallback & Handoff
- Khi độ chính xác của mô hình không đạt ngưỡng chấp nhận (>90%), tạo Handoff đề xuất cải tiến prompt hoặc tinh chỉnh mô hình.

## Eval Notes
- Suite: `evals/ai/evaluation-design.yaml`
