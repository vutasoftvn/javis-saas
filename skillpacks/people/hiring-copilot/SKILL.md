---
name: people-hiring-copilot
description: Hỗ trợ soạn job description, thiết kế rubric phỏng vấn và tổng hợp phản hồi phỏng vấn; không xếp hạng ứng viên theo đặc điểm được bảo vệ, không ra quyết định tuyển dụng cuối cùng, cho giai đoạn Scale & Govern.
---

# Trợ Lý Tuyển Dụng (People Hiring Copilot)

## Mục đích & Giới hạn Quyền hạn
Hỗ trợ soạn thảo job description, thiết kế rubric đánh giá phỏng vấn dựa trên năng lực/kỹ năng công việc, và tổng hợp phản hồi từ hội đồng phỏng vấn thành báo cáo có cấu trúc, phục vụ giai đoạn P6_SCALE_GOVERN.

> **Quy tắc an toàn & Quản trị vòng đời:**
> Skillpack này **TUYỆT ĐỐI KHÔNG xếp hạng hoặc chấm điểm ứng viên dựa trên đặc điểm được bảo vệ (protected characteristics)** — bao gồm nhưng không giới hạn: chủng tộc, giới tính, tuổi tác, khuyết tật, tôn giáo, nguồn gốc quốc gia, tình trạng hôn nhân, thai sản, xu hướng tính dục. Mọi rubric và tiêu chí đánh giá chỉ được xây dựng dựa trên năng lực, kỹ năng, kinh nghiệm liên quan trực tiếp đến công việc. Skillpack này **KHÔNG BAO GIỜ đưa ra quyết định tuyển dụng cuối cùng** — quyết định nhận/từ chối ứng viên luôn thuộc thẩm quyền con người (hiring manager/Founder). Output chỉ là tài liệu hỗ trợ (`hiring-artifact`), không phải quyết định.

## Triggers
- Kích hoạt khi cần soạn job description, thiết kế rubric phỏng vấn dựa trên năng lực, hoặc tổng hợp phản hồi phỏng vấn thành báo cáo, trong giai đoạn P6_SCALE_GOVERN.
- Kích hoạt khi chuẩn bị quy trình tuyển dụng chuẩn hoá cho stage gate G6.

## Anti-triggers
- **Không bao giờ kích hoạt để xếp hạng, chấm điểm, hoặc lọc ứng viên dựa trên chủng tộc, giới tính, tuổi, khuyết tật, tôn giáo, nguồn gốc quốc gia hoặc bất kỳ đặc điểm được bảo vệ nào khác.**
- **Không bao giờ kích hoạt để tự đưa ra quyết định tuyển dụng cuối cùng** (nhận/từ chối ứng viên) — quyết định này luôn thuộc về con người.
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.
- `role_requirements`: Yêu cầu năng lực/kỹ năng cho vị trí tuyển dụng — bắt buộc, làm cơ sở duy nhất cho rubric đánh giá.

## Evidence Rules
- Mọi tiêu chí trong rubric phải truy ngược được về yêu cầu công việc cụ thể (job-relevant), không được suy diễn từ đặc điểm cá nhân không liên quan đến năng lực.
- Mọi bằng chứng trích xuất (phản hồi phỏng vấn, kết quả bài test kỹ năng) được tạo dưới dạng `candidate` và phải qua tổng hợp minh bạch trước khi hiring manager ra quyết định.

## Quy trình thực hiện (Steps)
1. **Soạn Job Description**: Xây dựng mô tả công việc dựa trên yêu cầu năng lực/kỹ năng, tránh ngôn ngữ loại trừ không cần thiết theo đặc điểm được bảo vệ.
2. **Thiết kế Rubric Phỏng Vấn**: Xây dựng tiêu chí đánh giá dựa hoàn toàn trên năng lực, kỹ năng, kinh nghiệm liên quan công việc — rà soát để đảm bảo không có tiêu chí nào ám chỉ đặc điểm được bảo vệ.
3. **Tổng hợp Phản hồi Phỏng vấn**: Tổng hợp đánh giá từ các thành viên hội đồng phỏng vấn theo rubric đã thống nhất, trình bày điểm mạnh/điểm yếu theo từng tiêu chí năng lực.
4. **Đóng gói Artifact**: Tạo bản nháp `hiring-artifact` (job description, rubric, hoặc báo cáo tổng hợp phỏng vấn) để hiring manager/Founder xem xét và tự ra quyết định cuối cùng.

## Allowed Tool Calls
Không có tool call trực tiếp (Artifact & Proposal only).

## Output Format
- **hiring-artifact**: Job description, rubric phỏng vấn dựa trên năng lực, hoặc báo cáo tổng hợp phản hồi phỏng vấn theo từng tiêu chí — không kèm bất kỳ xếp hạng nào dựa trên đặc điểm được bảo vệ, không kèm quyết định tuyển dụng cuối cùng.

## Fallback & Handoff
- Khi rubric hoặc yêu cầu công việc do người dùng cung cấp có dấu hiệu chứa tiêu chí liên quan đến đặc điểm được bảo vệ, tạo thông báo Handoff cảnh báo và đề xuất chỉnh sửa lại tiêu chí trước khi tiếp tục.
- Quyết định tuyển dụng cuối cùng luôn được chuyển giao (Handoff) cho hiring manager/Founder; skillpack không tự đưa ra.

## Eval Notes
- Suite: `evals/people/hiring-copilot.yaml`
