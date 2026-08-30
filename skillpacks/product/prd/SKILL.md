---
name: product-prd
description: Xây dựng tài liệu yêu cầu sản phẩm (PRD) hoàn chỉnh gồm bài toán, phạm vi tính năng, phi chức năng và tiêu chí nghiệm thu.
---

# Tài Liệu Yêu Cầu Sản Phẩm (Product Requirements Document - PRD)

## Mục đích & Giới hạn Quyền hạn
Xây dựng tài liệu đặc tả yêu cầu sản phẩm (PRD) có tính hành động cao cho giai đoạn P3_BUILD_VALIDATE. Định hình rõ nét phạm vi MVP / tính năng chính, bài toán khách hàng, các ràng buộc phi chức năng (bảo mật, hiệu năng), và tiêu chuẩn bàn giao phát triển.

> **Quy tắc an toàn & Quản trị vòng đời:**
> Skillpack này CHỈ tạo tài liệu đặc tả (Artifact/Proposal). Tuyệt đối không tự thực hiện mã nguồn hay triển khai hạ tầng.

## Triggers
- Kích hoạt khi bắt đầu chuẩn bị phát triển tính năng hoặc giải pháp trong giai đoạn P3_BUILD_VALIDATE.
- Kích hoạt khi cần chuẩn bị tài liệu kỹ thuật chuyển giao cho đội ngũ kỹ thuật.

## Anti-triggers
- Không kích hoạt khi chưa có giả định giải pháp và định vị cốt lõi từ giai đoạn P2.
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.

## Evidence Rules
- PRD phải liên kết với các bằng chứng vấn đề (Problem Evidence) và giả định giải pháp (Solution Hypotheses) đã được xác nhận ở P1/P2.
- Khi thiếu kết nối trực tiếp với code repository bên ngoài, skillpack phải fallback tạo ra bản nháp Artifact PRD hoàn chỉnh nội tại trong COSA workspace.

## Quy trình thực hiện (Steps)
1. **Tổng hợp Bài toán & Mục tiêu**: Nêu rõ bài toán, đối tượng sử dụng (Persona) và chỉ số thành công cốt lõi.
2. **Xác định Phạm vi (Scope & Non-Goals)**: Phân định ranh giới rõ ràng giữa những gì thuộc phiên bản này và những gì hoãn lại.
3. **Mô tả Yêu cầu Chức năng**: Chi tiết từng luồng người dùng (User flows) và quy tắc nghiệp vụ.
4. **Xác định Ràng buộc Phi chức năng**: Yêu cầu về hiệu năng, độ sẵn sàng, phân quyền đa người thuê (multi-tenancy) và bảo mật dữ liệu.
5. **Tiêu chí Nghiệm thu (Release Criteria)**: Thiết lập điều kiện tiên quyết trước khi đưa vào thử nghiệm pilot.

## Allowed Tool Calls
Không có tool call trực tiếp (Artifact & Proposal only).

## Output Format
- **prd-document**: Văn bản PRD đầy đủ theo cấu trúc chuẩn Markdown.

## Fallback & Handoff
- Khi không có kho code liên kết, fallback tạo bản nháp PRD cục bộ và gửi đề xuất Founder phê duyệt.

## Eval Notes
- Suite: `evals/product/prd.yaml`
