---
name: finance-runway-forecast
description: Dự báo thời gian tồn tại của dòng tiền (runway), tỷ lệ đốt tiền (burn
  rate) và các kịch bản tài chính cho dự án.
---

# Runway Forecast & Cash Flow Projection

## Mục đích & Giới hạn Quyền hạn
Dự báo thời gian tồn tại của dòng tiền (runway), tỷ lệ đốt tiền (burn rate) và các kịch bản tài chính cho dự án.

> **Quy tắc an toàn & Quản trị vòng đời:**
> Không tự thay đổi project lifecycle stage, không tự phê duyệt evidence/gate, không tự gọi external provider. Khi action cần quyền hoặc evidence đủ chuẩn, tạo proposal/handoff với ID evidence/artifact liên quan.

## Triggers
- Kích hoạt khi cần thực hiện nghiệp vụ `finance.runway-forecast` trong giai đoạn P0_DISCOVERY, P1_PROBLEM_VALIDATION.

## Anti-triggers
- Không kích hoạt ngoài phạm vi dự án hoặc khi thiếu ngữ cảnh `workspace_id` và `project_id`.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.

## Evidence Rules
- Tuân thủ nguyên tắc anti-self-validation: Mọi bằng chứng trích xuất được tạo dưới dạng `candidate` và phải qua phê duyệt của Founder/Admin trước khi gate evaluation ghi nhận.

## Quy trình thực hiện (Steps)
1. **Thu thập ngữ cảnh**: Đọc dữ liệu dự án và đối chiếu với chính sách giai đoạn hiện tại.
2. **Xử lý chuyên môn**: Thực hiện phân tích, trích xuất thông tin hoặc lập kế hoạch theo chuẩn.
3. **Đóng gói kết quả**: Tạo bản nháp artifact hoặc đề xuất (proposal) có bằng chứng dẫn chiếu.
4. **Bàn giao kiểm duyệt**: Trình duyệt qua kênh Human Handoff nếu cần hành động có side-effect.

## Allowed Tool Calls
Không có công cụ trực tiếp (Artifact/Proposal only).

## Output Format
- Trả về cấu trúc Markdown tiêu chuẩn gồm: Tóm tắt nhận định, Bằng chứng đối chiếu (Evidence citations), Đề xuất hành động (Proposal), và Rủi ro tồn đọng.

## Fallback & Handoff
- Khi thiếu dữ liệu hoặc không đủ điều kiện an toàn, tạo thông báo Handoff đề xuất người dùng bổ sung thông tin.

## Eval Notes
- Suite: `evals/finance/runway-forecast.yaml`
