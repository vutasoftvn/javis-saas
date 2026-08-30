---
name: marketing-content-strategy
description: Xây dựng chiến lược content pillar và lịch nội dung bám sát ICP và bằng chứng kênh phân phối.
---

# Chiến Lược Content Pillar & Lịch Nội Dung (Content Strategy)

## Mục đích & Giới hạn Quyền hạn
Xây dựng khung content pillar (trụ cột nội dung) bám sát ICP (Ideal Customer Profile) đã xác lập, đề xuất lịch nội dung (content calendar) theo kênh phân phối, và ưu tiên chủ đề dựa trên bằng chứng nhu cầu khách hàng trong giai đoạn P5_OPERATE_GROWTH.

> **Quy tắc an toàn & Quản trị vòng đời:**
> Skillpack này CHỈ đưa ra khuyến nghị phân tích và tạo dự thảo artifact. Tuyệt đối không tự ý đăng công khai nội dung lên bất kỳ kênh nào, không tự ý lên lịch xuất bản tự động, và không tự thay đổi lifecycle stage.

## Triggers
- Kích hoạt khi cần xây dựng hoặc cập nhật content pillar cho một giai đoạn tăng trưởng cụ thể.
- Kích hoạt khi cần đề xuất lịch nội dung theo kênh phân phối dựa trên ICP đã có.
- Kích hoạt khi chuẩn bị hồ sơ cho stage gate G5 nhằm chứng minh chiến lược nội dung có căn cứ dữ liệu.

## Anti-triggers
- Không kích hoạt khi cần soạn thảo copy chi tiết cho một tài sản cụ thể (dùng `marketing.copywriting`).
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.
- Không kích hoạt để tự động đăng bài hoặc lên lịch xuất bản qua hệ thống bên ngoài.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.

## Evidence Rules
- Mọi trụ cột nội dung đề xuất phải gắn với bằng chứng ICP (persona, pain point, JTBD) hoặc dữ liệu hiệu suất kênh hiện có; không được đề xuất chủ đề chỉ dựa trên suy đoán chủ quan.
- Mọi bằng chứng trích xuất được tạo dưới dạng `candidate` và phải qua phê duyệt của Founder trước khi gate evaluation ghi nhận.

## Quy trình thực hiện (Steps)
1. **Rà soát ICP & Bằng chứng kênh**: Tổng hợp persona, pain point và dữ liệu hiệu suất từng kênh phân phối hiện có.
2. **Xác định Content Pillar**: Đề xuất 3-5 trụ cột nội dung phản ánh trực tiếp nhu cầu và ngôn ngữ của khách hàng mục tiêu.
3. **Thiết kế Lịch Nội Dung**: Phân bổ chủ đề theo pillar vào lịch nội dung theo kênh và tần suất đề xuất.
4. **Ưu tiên hóa**: Xếp hạng chủ đề theo mức độ liên quan đến bằng chứng nhu cầu và tiềm năng chuyển đổi.
5. **Đóng gói Artifacts**: Tạo bản nháp `content-pillar-framework` và `content-calendar-proposal` để Founder xem xét.

## Allowed Tool Calls
Không có tool call trực tiếp (Artifact & Proposal only).

## Output Format
- **content-pillar-framework**: Khung trụ cột nội dung gắn với ICP và bằng chứng nhu cầu tương ứng.
- **content-calendar-proposal**: Lịch nội dung đề xuất theo kênh, tần suất và mức độ ưu tiên.

## Fallback & Handoff
- Khi thiếu dữ liệu ICP hoặc dữ liệu hiệu suất kênh, tạo thông báo Handoff đề xuất Founder bổ sung nghiên cứu khách hàng hoặc dữ liệu phân tích kênh trước khi hoàn tất chiến lược.

## Eval Notes
- Suite: `evals/marketing/content-strategy.yaml`
