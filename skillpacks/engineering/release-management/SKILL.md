---
name: engineering-release-management
description: Quản trị quy trình phát hành, đánh nhãn Release Candidate, ghi chú phát hành (Release Notes) và quy trình khôi phục sự cố (Rollback Runbook).
---

# Quản Trị Phát Hành & Quy Trình Rollback (Release Management)

## Mục đích & Giới hạn Quyền hạn
Thiết lập kế hoạch phát hành phiên bản (Release Candidate), tạo ghi chú thay đổi (Release Notes), kế hoạch smoke test, và quy trình khôi phục phiên bản trước khi gặp sự cố (Rollback Runbook) trong giai đoạn P3_BUILD_VALIDATE.

> **Quy tắc an toàn & Quản trị vòng đời:**
> Skillpack này CHỈ chuẩn bị tài liệu quy trình (`rollback-runbook`, `release-notes`) và hoạt động ở chế độ `L0_OBSERVE`. Tuyệt đối KHÔNG có quyền tự động deploy (`engineering.deploy` không tồn tại) hay tự động kích hoạt phát hành (`engineering.release.execute` không tồn tại).

## Triggers
- Kích hoạt khi chuẩn bị tài liệu `rollbackArtifactRef` cho hồ sơ khởi tạo Pilot Run.
- Kích hoạt khi chuẩn bị gói phát hành cho Release Owner xem xét.

## Anti-triggers
- Không kích hoạt khi cần thao tác trực tiếp trên hạ tầng CI/CD.
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.

## Evidence Rules
- Bản nháp rollback runbook (`rollback-runbook`) được lưu trữ dưới dạng artifact để làm trường `rollbackArtifactRef` trong bản ghi `PilotRun`.

## Quy trình thực hiện (Steps)
1. **Tổng hợp Thay đổi (Changelog)**: Liệt kê các tính năng mới, bản vá lỗi và thay đổi cấu hình.
2. **Thiết lập Kịch bản Smoke Test**: Danh mục 5-10 bước kiểm tra nhanh sau khi triển khai.
3. **Xây dựng Quy trình Rollback**: Hướng dẫn chi tiết từng bước khôi phục code, rollback database migration và revert cấu hình khi có sự cố nghiêm trọng.
4. **Đóng gói Kế hoạch Bàn giao**: Tạo tài liệu `release-runbook` và `rollback-runbook` bàn giao cho Release Owner.

## Allowed Tool Calls
Không có tool call trực tiếp (Artifact & Proposal only).

## Output Format
- **rollback-runbook**: Cẩm nang quy trình xử lý và khôi phục khi phát sinh sự cố pilot.
- **release-notes**: Bản tóm tắt các tính năng phát hành cho người dùng.

## Fallback & Handoff
- Khi chưa có giải pháp rollback dữ liệu an toàn, tạo Handoff yêu cầu Database Administrator xem xét.

## Eval Notes
- Suite: `evals/engineering/release-management.yaml`
