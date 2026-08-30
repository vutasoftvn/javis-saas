---
name: operations-automation-design
description: Thiết kế (không thực thi) một automation cho quy trình vận hành, bắt buộc có process owner, exception path và rollback plan, cho giai đoạn Scale & Govern.
---

# Thiết Kế Automation (Operations Automation Design)

## Mục đích & Giới hạn Quyền hạn
Thiết kế đề xuất tự động hoá cho một quy trình vận hành đã được chuẩn hoá (thường sau khi đã có SOP), xác định phạm vi tự động hoá, luồng ngoại lệ (exception path) và kế hoạch rollback/compensation, phục vụ giai đoạn P6_SCALE_GOVERN.

> **Quy tắc an toàn & Quản trị vòng đời:**
> Skillpack này **CHỈ thiết kế, KHÔNG BAO GIỜ tự thực thi automation**. Đây là ranh giới tuyệt đối: mọi output là tài liệu thiết kế (`automation-design-proposal`), không phải một automation đang chạy. Skillpack này không được cấp bất kỳ tool automation-execute nào và không tự triển khai automation vào hệ thống production. Mọi đề xuất bắt buộc phải có đủ ba trường: **process owner nêu tên cụ thể**, **exception path** (đường xử lý khi automation gặp trường hợp ngoại lệ hoặc lỗi), và **rollback/compensation plan** (kế hoạch hoàn tác khi automation gây lỗi). Thiếu bất kỳ trường nào trong ba trường này, đề xuất bị coi là không hoàn chỉnh và phải trả về Handoff.

## Triggers
- Kích hoạt khi cần đánh giá và thiết kế phương án tự động hoá cho một quy trình vận hành đã lặp lại/đã có SOP, trong giai đoạn P6_SCALE_GOVERN.
- Kích hoạt khi chuẩn bị hồ sơ cho stage gate G6 để chứng minh khả năng mở rộng vận hành có kiểm soát rủi ro.

## Anti-triggers
- Không kích hoạt để **thực thi** một automation đã thiết kế — thực thi luôn thuộc trách nhiệm con người/hệ thống engineering qua Capability Layer được phê duyệt riêng, không thuộc skillpack này.
- Không kích hoạt khi không thể xác định process owner, exception path, hoặc rollback plan.
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.
- `process_owner`: Người chịu trách nhiệm phê duyệt và vận hành automation — bắt buộc.

## Evidence Rules
- Bắt buộc liên kết thiết kế automation với SOP nguồn hoặc bằng chứng vận hành thực tế của quy trình được tự động hoá.
- Mọi bằng chứng trích xuất được tạo dưới dạng `candidate` và phải qua phê duyệt của process owner và kỹ thuật trước khi triển khai thật.

## Quy trình thực hiện (Steps)
1. **Xác định phạm vi automation**: Mô tả quy trình nguồn, ranh giới tự động hoá (bước nào tự động, bước nào vẫn cần con người).
2. **Named Process Owner**: Ghi rõ tên/vai trò người chịu trách nhiệm phê duyệt và giám sát automation sau khi triển khai.
3. **Exception Path**: Thiết kế đường xử lý cụ thể khi automation gặp input bất thường, lỗi hệ thống, hoặc trường hợp ngoài phạm vi thiết kế — không được để "rơi vào im lặng" (silent failure).
4. **Rollback / Compensation Plan**: Thiết kế kế hoạch hoàn tác cụ thể (dữ liệu, trạng thái, thông báo liên quan) nếu automation gây lỗi sau khi đã chạy.
5. **Đóng gói Artifact**: Tạo bản nháp `automation-design-proposal` với đầy đủ ba trường bắt buộc để process owner và kỹ thuật xem xét trước khi bất kỳ ai triển khai thật.

## Allowed Tool Calls
Không có tool call trực tiếp (Artifact & Proposal only).

## Output Format
- **automation-design-proposal**: Gồm các trường bắt buộc — `process_owner` (nêu tên cụ thể), `exception_path` (mô tả xử lý ngoại lệ), `rollback_plan` (kế hoạch hoàn tác/compensation), phạm vi automation, và ghi chú rõ ràng "thiết kế này chưa được thực thi, cần phê duyệt và triển khai riêng qua Capability Layer".

## Fallback & Handoff
- Khi thiếu process owner, exception path, hoặc rollback plan, tạo thông báo Handoff yêu cầu bổ sung trước khi hoàn thiện đề xuất — không tự suy diễn hoặc điền mặc định cho các trường này.

## Eval Notes
- Suite: `evals/operations/automation-design.yaml`
