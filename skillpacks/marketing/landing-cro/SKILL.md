---
name: marketing-landing-cro
description: Kiểm toán tỷ lệ chuyển đổi (CRO) của landing page và đề xuất thiết kế A/B test, không tự triển khai thay đổi trang.
---

# Kiểm Toán CRO Landing Page & Đề Xuất A/B Test (Landing CRO)

## Mục đích & Giới hạn Quyền hạn
Kiểm toán landing page hiện có theo các nguyên tắc conversion-rate-optimization (rõ ràng thông điệp, giảm ma sát, độ tin cậy, CTA) và đề xuất thiết kế A/B test có giả thuyết cụ thể để kiểm chứng cải thiện, trong giai đoạn P5_OPERATE_GROWTH.

> **Quy tắc an toàn & Quản trị vòng đời:**
> Skillpack này CHỈ đưa ra khuyến nghị phân tích và tạo dự thảo artifact. Skillpack này đề xuất thiết kế A/B test — **không bao giờ tự triển khai (deploy) thay đổi trang**, không tự ý đăng công khai bất kỳ nội dung nào, và không tự thay đổi lifecycle stage.

## Triggers
- Kích hoạt khi cần kiểm toán một landing page cụ thể để tìm điểm ma sát ảnh hưởng đến tỷ lệ chuyển đổi.
- Kích hoạt khi cần đề xuất thiết kế thử nghiệm A/B cho một giả thuyết cải thiện landing page.
- Kích hoạt khi chuẩn bị hồ sơ cho stage gate G5 nhằm chứng minh landing page đã được tối ưu có căn cứ.

## Anti-triggers
- Không kích hoạt khi cần trực tiếp sửa mã nguồn hoặc cấu hình CMS của trang (đây là việc của kỹ thuật, agent này chỉ đề xuất).
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.
- Không kích hoạt để tự động triển khai (deploy) biến thể trang lên môi trường production.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.

## Evidence Rules
- Mọi nhận định về điểm ma sát (friction point) phải gắn với bằng chứng cụ thể (heatmap, session recording, dữ liệu funnel, phản hồi người dùng); không suy diễn từ cảm tính thiết kế.
- Mọi bằng chứng trích xuất được tạo dưới dạng `candidate` và phải qua phê duyệt của Founder trước khi gate evaluation ghi nhận.

## Quy trình thực hiện (Steps)
1. **Kiểm toán Landing Page**: Rà soát cấu trúc trang theo checklist CRO (thông điệp giá trị, độ rõ ràng CTA, tín hiệu tin cậy, tốc độ tải, mobile friction).
2. **Tổng hợp Điểm Ma sát**: Liệt kê các điểm ma sát phát hiện được, gắn với bằng chứng dữ liệu tương ứng.
3. **Xây dựng Giả thuyết A/B Test**: Với mỗi điểm ma sát ưu tiên, xây dựng giả thuyết thử nghiệm rõ ràng (biến thể, chỉ số thành công, cỡ mẫu ước tính).
4. **Đóng gói Artifacts**: Tạo bản nháp `landing-cro-audit` và `ab-test-design-proposal` để Founder xem xét và phê duyệt trước khi bất kỳ ai triển khai thay đổi thật.

## Allowed Tool Calls
Không có tool call trực tiếp (Artifact & Proposal only).

## Output Format
- **landing-cro-audit**: Báo cáo kiểm toán điểm ma sát của landing page kèm bằng chứng và mức độ ưu tiên.
- **ab-test-design-proposal**: Đề xuất thiết kế A/B test (biến thể, giả thuyết, chỉ số thành công, cỡ mẫu) — chỉ là dự thảo, chờ người có thẩm quyền triển khai.

## Fallback & Handoff
- Khi thiếu dữ liệu hành vi người dùng (heatmap, session recording), tạo thông báo Handoff đề xuất Founder thu thập thêm dữ liệu trước khi hoàn tất kiểm toán.

## Eval Notes
- Suite: `evals/marketing/landing-cro.yaml`
