---
name: product-pilot-onboarding
description: Quy trình hướng dẫn tiếp nhận (Onboarding Runbook) cho khách hàng đối tác thiết kế tham gia thử nghiệm pilot.
---

# Quy Trình Onboarding Khách Hàng Pilot (Pilot Onboarding)

## Mục đích & Giới hạn Quyền hạn
Thiết lập tài liệu hướng dẫn và danh mục các bước tiếp nhận (Onboarding Runbook), hỗ trợ khởi tạo tenant, kích hoạt feature flags và đào tạo người dùng đối tác thiết kế tham gia chương trình pilot trong giai đoạn P3_BUILD_VALIDATE.

> **Quy tắc an toàn & Quản trị vòng đời:**
> Skillpack này CHỈ tạo tài liệu quy trình (`onboarding-runbook`). Tuyệt đối KHÔNG có quyền tự kích hoạt trạng thái pilot hay tự động gửi lời mời người dùng khi chưa có sự cho phép của Founder/Admin.

## Triggers
- Kích hoạt khi chuẩn bị tài liệu onboarding runbook cho hồ sơ Pilot Run.
- Kích hoạt khi tiếp nhận Design Partner mới vào thử nghiệm giải pháp.

## Anti-triggers
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.

## Evidence Rules
- Bản nháp onboarding runbook (`onboarding-runbook`) được lưu trữ dưới dạng artifact để làm trường `onboardingArtifactRef` trong bản ghi `PilotRun`.

## Quy trình thực hiện (Steps)
1. **Chuẩn bị Môi trường**: Liệt kê các bước cấp phát tài khoản tenant và phân quyền quản trị cho khách hàng.
2. **Kịch bản Kích hoạt (Activation Flow)**: Hướng dẫn người dùng hoàn tất các bước thiết lập cấu hình ban đầu.
3. **Kế hoạch Đào tạo & Hỗ trợ**: Lên lịch các buổi hướng dẫn sử dụng và bàn giao tài liệu.
4. **Đóng gói Onboarding Runbook**: Tạo tài liệu chi tiết bàn giao cho Founder/Admin và Release Owner.

## Allowed Tool Calls
Không có tool call trực tiếp (Artifact & Proposal only).

## Output Format
- **onboarding-runbook**: Cẩm nang hướng dẫn onboarding từng bước cho khách hàng pilot.

## Fallback & Handoff
- Khi có vướng mắc trong khâu cấp phát tenant, tạo Handoff yêu cầu Admin hỗ trợ.

## Eval Notes
- Suite: `evals/product/pilot-onboarding.yaml`
