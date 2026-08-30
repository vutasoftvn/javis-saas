---
name: engineering-vertical-slice
description: Định nghĩa kiến trúc lát cắt dọc xuyên suốt từ UI, Backend API đến Cơ sở dữ liệu và hạ tầng kiểm thử.
---

# Kiến Trúc Lát Cắt Dọc (Vertical Slice Architecture)

## Mục đích & Giới hạn Quyền hạn
Thiết lập kế hoạch kiến trúc lát cắt dọc (Vertical Slice) cho một tính năng cốt lõi, bao gồm: Frontend component, Backend endpoint, Data schema & migrations, và Integration tests. Phân tách rõ ràng giữa hợp đồng giả lập (stubs) và hợp đồng triển khai thật (real implementations) trong giai đoạn P3_BUILD_VALIDATE.

> **Quy tắc an toàn & Quản trị vòng đời:**
> Skillpack này mang tính quan sát và tư vấn cấu trúc (`L0_OBSERVE`). Tuyệt đối KHÔNG có quyền tự deploy (`engineering.deploy` không tồn tại trong agent plane).

## Triggers
- Kích hoạt khi cần thiết kế hoặc thẩm định lát cắt dọc tính năng đầu tiên cho giải pháp.

## Anti-triggers
- Không kích hoạt khi cần deploy hệ thống lên production/staging.
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.

## Evidence Rules
- Bản thiết kế phải xác định rõ các điểm kiểm thử tự động (Unit, Widget/E2E, API integration).

## Quy trình thực hiện (Steps)
1. **Xác định Ranh giới Lát cắt**: Chọn luồng giá trị mỏng nhất mang lại trải nghiệm hoàn chỉnh cho người dùng.
2. **Thiết kế Schema & Models**: Định nghĩa cấu trúc bảng dữ liệu, migration scripts và DTOs.
3. **Thiết kế API Handlers & Services**: Đặc tả HTTP endpoints, status codes và validation logic.
4. **Thiết kế UI Components**: Xác định trạng thái giao diện (Loading, Data, Error, Empty).
5. **Kế hoạch Kiểm thử & Fallbacks**: Xác định test coverage và kế hoạch stubbing cho các dependency bên ngoài.

## Allowed Tool Calls
Không có tool call trực tiếp (Artifact & Proposal only).

## Output Format
- **vertical-slice-design**: Bản vẽ kiến trúc lát cắt dọc chi tiết kèm danh mục tệp tin và checklist kiểm thử.

## Fallback & Handoff
- Khi có xung đột kiến trúc với hạ tầng hiện hữu, tạo Handoff đề xuất Tech Lead xem xét.

## Eval Notes
- Suite: `evals/engineering/vertical-slice.yaml`
