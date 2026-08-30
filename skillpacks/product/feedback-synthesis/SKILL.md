---
name: product-feedback-synthesis
description: Thu thập, phân loại và tổng hợp phản hồi từ khách hàng pilot thành các đề xuất cải tiến sản phẩm.
---

# Tổng Hợp & Phân Tích Phản Hồi Pilot (Feedback Synthesis)

## Mục đích & Giới hạn Quyền hạn
Thu thập, phân loại định tính và định lượng các ý kiến phản hồi từ các Design Partners trong quá trình chạy pilot ở giai đoạn P3_BUILD_VALIDATE. Phân tách rành mạch giữa Lỗi hệ thống (Bugs), Yêu cầu tính năng mới (Feature Requests), và Trải nghiệm người dùng (UX Friction).

> **Quy tắc an toàn & Quản trị vòng đời:**
> Skillpack này CHỈ tổng hợp thông tin và tạo báo cáo (`feedback-synthesis-report`). Tuyệt đối không tự ý thay đổi backlog đã chốt hay cam kết tính năng trực tiếp với khách hàng.

## Triggers
- Kích hoạt định kỳ hàng tuần trong thời gian chạy Pilot Run để cập nhật tiến độ và mức độ hài lòng của khách hàng.
- Kích hoạt khi chuẩn bị tài liệu đánh giá stage gate G3.

## Anti-triggers
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.

## Evidence Rules
- Mọi nhận định về mức độ hài lòng hoặc điểm nghẽn phải trích dẫn trực tiếp lời nói/ghi chép từ khách hàng đối tác thiết kế.

## Quy trình thực hiện (Steps)
1. **Thu thập Phản hồi**: Trích xuất các ghi chép phỏng vấn, ticket hỗ trợ và phản hồi chat từ khách hàng pilot.
2. **Phân loại & Định lượng**: Gán nhãn (Bug, UX, Feature, Praise) và đo lường tần suất xuất hiện.
3. **Phân tích Xu hướng**: Nhận diện các điểm ma sát lặp đi lặp lại và nguyên nhân gốc rễ.
4. **Đề xuất Hành động Cải tiến**: Lập danh sách đề xuất ưu tiên theo thang Impact/Effort để chuyển giao cho Product/Engineering.

## Allowed Tool Calls
Không có tool call trực tiếp (Artifact & Proposal only).

## Output Format
- **feedback-synthesis-report**: Báo cáo tổng hợp phản hồi định kỳ kèm biểu đồ phân loại và danh sách đề xuất hành động.

## Fallback & Handoff
- Khi phát hiện phản hồi tiêu cực nghiêm trọng có nguy cơ mất khách hàng pilot, tạo Handoff khẩn cấp gửi Founder.

## Eval Notes
- Suite: `evals/product/feedback-synthesis.yaml`
