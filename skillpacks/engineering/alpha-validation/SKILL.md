---
name: engineering-alpha-validation
description: Kế hoạch kiểm thử nội bộ, danh mục kiểm tra độ ổn định (Sanity/Regression) trước khi bàn giao cho Release Owner.
---

# Kiểm Thử Alpha & Bàn Giao Kỹ Thuật (Alpha Validation)

## Mục đích & Giới hạn Quyền hạn
Thiết lập kế hoạch kiểm thử nội bộ (Alpha Test), danh mục kiểm tra độ ổn định và hồi quy (Sanity Checklist), đảm bảo phiên bản phần mềm đạt chất lượng trước khi bàn giao cho Release Owner phê duyệt kích hoạt pilot trong P3_BUILD_VALIDATE.

> **Quy tắc an toàn & Quản trị vòng đời:**
> Skillpack này CHỈ lập kế hoạch và báo cáo kiểm thử (`L0_OBSERVE`). Tuyệt đối KHÔNG có quyền tự ý release hoặc bypass quy trình duyệt của Release Owner.

## Triggers
- Kích hoạt khi bản build kỹ thuật hoàn thành và cần kiểm thử nghiệm thu nội bộ.

## Anti-triggers
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.

## Evidence Rules
- Báo cáo alpha validation phải liệt kê rõ kết quả pass/fail của toàn bộ test case kiểm thử tự động và thủ công.

## Quy trình thực hiện (Steps)
1. **Thiết lập Kế hoạch Alpha**: Xác định danh mục chức năng cốt lõi cần kiểm chứng độ ổn định.
2. **Thực thi Kiểm tra Sanity**: Kiểm tra các luồng chính (Happy path), xác thực tenant isolation, và bảo mật dữ liệu.
3. **Ghi nhận Khuyết tật (Bug Tracking)**: Phân loại mức độ nghiêm trọng (Blocker, Critical, Major, Minor).
4. **Đóng gói Báo cáo Bàn giao**: Tạo tài liệu tổng kết alpha validation gửi Release Owner xem xét.

## Allowed Tool Calls
Không có tool call trực tiếp (Artifact & Proposal only).

## Output Format
- **alpha-validation-report**: Báo cáo tổng kết kiểm thử nội bộ kèm trạng thái sẵn sàng phát hành.

## Fallback & Handoff
- Khi phát hiện lỗi Blocker, tạo Handoff yêu cầu đội ngũ kỹ thuật xử lý trước khi kích hoạt pilot.

## Eval Notes
- Suite: `evals/engineering/alpha-validation.yaml`
