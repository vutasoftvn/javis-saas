---
name: sales-design-partner-selection
description: Tuyển chọn, đánh giá tiêu chuẩn và thiết lập cam kết song phương với khách hàng đối tác thiết kế (Design Partners) cho giai đoạn thử nghiệm pilot.
---

# Lựa Chọn Đối Tác Thiết Kế & Thẩm Định Pilot (Design Partner Selection)

## Mục đích & Giới hạn Quyền hạn
Xác định tiêu chí tuyển chọn, thang chấm điểm phù hợp (qualification rubric), và mẫu cam kết song phương (mutual commitments) cho các Design Partners tham gia chương trình pilot trong giai đoạn P2_SOLUTION_VALIDATION.

> **Quy tắc an toàn & Quản trị vòng đời:**
> Skillpack này CHỈ tạo hồ sơ phân tích và bản nháp cam kết (`design-partner-profile`, `design-partner-commitment`). Tuyệt đối không tự ý gửi email/tin nhắn ra bên ngoài, không tự kích hoạt pilot, và không tự ký hợp đồng pháp lý.

## Triggers
- Kích hoạt khi cần lập danh sách và thẩm định ứng viên Design Partner cho dự án.
- Kích hoạt khi chuẩn bị hồ sơ bằng chứng đối tác thiết kế để đáp ứng điều kiện tiên quyết kích hoạt Pilot Run.

## Anti-triggers
- Không kích hoạt khi cần gửi tin nhắn tương tác trực tiếp với khách hàng (yêu cầu phê duyệt qua Handoff).
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.

## Evidence Rules
- Mỗi Design Partner được phê duyệt phải có hồ sơ thẩm định chi tiết, ghi nhận mức độ đau đớn của vấn đề, ngân sách, và cam kết nguồn lực từ phía khách hàng.
- Bằng chứng đối tác thiết kế (`design-partner-profile`, `design-partner-commitment`) phải được Founder duyệt (`status = approved`) để được sử dụng trong `PilotRun.designPartnerEvidenceRefs`.

## Quy trình thực hiện (Steps)
1. **Thiết lập Tiêu chí Thẩm định**: Xây dựng rubric đánh giá (ICP fit, urgency, willingness to give feedback, executive sponsor).
2. **Đánh giá Danh sách Ứng viên**: Chấm điểm các khách hàng tiềm năng và xếp hạng mức độ phù hợp cho chương trình pilot.
3. **Dự thảo Cam kết Song phương**: Xác định trách nhiệm của startup (tính năng, SLA hỗ trợ) và trách nhiệm của khách hàng (giờ test, phản hồi hàng tuần, case study).
4. **Đóng gói Hồ sơ**: Tạo bản nháp `design-partner-profile` và `design-partner-commitment` trình Founder phê duyệt.

## Allowed Tool Calls
Không có tool call trực tiếp (Artifact & Proposal only).

## Output Format
- **design-partner-profile**: Hồ sơ chi tiết đối tác, điểm đánh giá rubric, persona người dùng trực tiếp và bối cảnh nghiệp vụ.
- **design-partner-commitment**: Bản ghi nhớ cam kết song phương về thời gian, khối lượng thử nghiệm và tiêu chí thành công.

## Fallback & Handoff
- Nếu chưa có đủ ứng viên đạt chuẩn ICP, tạo thông báo Handoff đề xuất mở rộng kênh tìm kiếm qua `sales.prospecting`.

## Eval Notes
- Suite: `evals/sales/design-partner-selection.yaml`
