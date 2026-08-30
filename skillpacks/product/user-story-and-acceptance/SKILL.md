---
name: product-user-story-and-acceptance
description: Phân rã tính năng thành các User Story chi tiết kèm tiêu chí nghiệm thu theo cú pháp Given-When-Then.
---

# User Stories & Tiêu Chí Nghiệm Thu (User Story & Acceptance Criteria)

## Mục đích & Giới hạn Quyền hạn
Chuyển hóa các yêu cầu từ PRD thành các User Stories cụ thể, kèm theo tiêu chuẩn nghiệm thu chặt chẽ (Given-When-Then), các trường hợp ngoại lệ (Edge cases), và kịch bản xử lý lỗi cho các tác vụ kỹ thuật trong P3_BUILD_VALIDATE.

> **Quy tắc an toàn & Quản trị vòng đời:**
> Skillpack này CHỈ tạo tài liệu đặc tả User Stories. Không tự ý sửa đổi Jira/GitHub issues hoặc mã nguồn.

## Triggers
- Kích hoạt khi cần phân rã tính năng từ PRD sang danh sách đầu việc chi tiết cho kỹ thuật.

## Anti-triggers
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.

## Evidence Rules
- Mỗi câu chuyện phải liên kết trực tiếp với mục tiêu nghiệp vụ được xác lập trong PRD.

## Quy trình thực hiện (Steps)
1. **Phân rã Tính năng**: Chia nhỏ tính năng lớn (Epic) thành các lát cắt câu chuyện người dùng độc lập (Invest criteria).
2. **Viết Cấu trúc Story**: Áp dụng mẫu `As a [persona], I want [action], So that [value]`.
3. **Thiết lập Acceptance Criteria**: Viết các kịch bản kiểm thử theo chuẩn Given-When-Then cho đường dẫn chính (Happy path) và đường dẫn phụ/lỗi (Error path).
4. **Định danh Edge Cases**: Liệt kê các trường hợp ngoại biên (mất mạng, dữ liệu rỗng, vượt hạn mức).

## Allowed Tool Calls
Không có tool call trực tiếp (Artifact & Proposal only).

## Output Format
- **user-stories-spec**: Danh sách User Stories chi tiết kèm Acceptance Criteria và bảng ma trận kiểm thử.

## Fallback & Handoff
- Khi PRD chưa rõ ràng, tạo Handoff đề xuất làm rõ yêu cầu với Product Owner.

## Eval Notes
- Suite: `evals/product/user-story-and-acceptance.yaml`
