---
name: people-culture-operating-principles
description: Soạn thảo/duy trì tài liệu văn hoá và nguyên tắc vận hành (culture & operating principles), cần con người phê duyệt trước khi áp dụng, cho giai đoạn Scale & Govern.
---

# Văn Hoá & Nguyên Tắc Vận Hành (People Culture Operating Principles)

## Mục đích & Giới hạn Quyền hạn
Soạn thảo hoặc cập nhật tài liệu văn hoá công ty và nguyên tắc vận hành (operating principles) — giá trị cốt lõi, chuẩn mực hành vi, cách ra quyết định — dựa trên bằng chứng thực tiễn đã quan sát được trong tổ chức, phục vụ giai đoạn P6_SCALE_GOVERN.

> **Quy tắc an toàn & Quản trị vòng đời:**
> Skillpack này CHỈ tạo dự thảo tài liệu (`culture-principles-draft`). Tuyệt đối không tự ban hành hoặc áp dụng tài liệu văn hoá/nguyên tắc vận hành chính thức — **mọi bản thảo bắt buộc phải được con người (Founder/leadership) phê duyệt trước khi được coi là chính thức và phổ biến trong tổ chức**. Không tự ý gửi thông báo áp dụng ra toàn công ty, không tự thay đổi lifecycle stage, không tự phê duyệt chính bản thảo do mình tạo ra (no self-approval).

## Triggers
- Kích hoạt khi cần soạn mới hoặc cập nhật tài liệu văn hoá/nguyên tắc vận hành dựa trên thực tiễn tổ chức đã quan sát, trong giai đoạn P6_SCALE_GOVERN.
- Kích hoạt khi chuẩn bị hồ sơ cho stage gate G6 nhằm chứng minh tổ chức có nền tảng văn hoá vận hành rõ ràng khi mở rộng quy mô.

## Anti-triggers
- Không kích hoạt để tự ban hành hoặc phổ biến chính thức tài liệu văn hoá mà chưa qua phê duyệt của con người.
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.
- Không kích hoạt để tự phê duyệt bản thảo do chính skillpack tạo ra.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.
- `approving_stakeholder`: Người/nhóm có thẩm quyền phê duyệt tài liệu văn hoá trước khi áp dụng — bắt buộc.

## Evidence Rules
- Bắt buộc liên kết nội dung với bằng chứng thực tiễn quan sát được trong tổ chức (quyết định thực tế đã ra, phản hồi nhân sự, sự kiện văn hoá đã diễn ra), không tự bịa đặt giá trị chưa từng được thể hiện.
- Mọi bằng chứng trích xuất được tạo dưới dạng `candidate` và phải qua phê duyệt của Founder/leadership trước khi tài liệu được coi là chính thức.

## Quy trình thực hiện (Steps)
1. **Thu thập bằng chứng thực tiễn**: Tổng hợp các quyết định, hành vi, và chuẩn mực đã thực sự diễn ra trong tổ chức làm cơ sở.
2. **Soạn thảo giá trị cốt lõi & nguyên tắc vận hành**: Diễn đạt thành các nguyên tắc rõ ràng, cụ thể, có thể áp dụng vào tình huống ra quyết định thực tế (không chỉ là khẩu hiệu trừu tượng).
3. **Đối chiếu tính nhất quán**: Kiểm tra nguyên tắc mới không mâu thuẫn với các quyết định/chính sách đã ban hành trước đó.
4. **Đóng gói Artifact**: Tạo bản nháp `culture-principles-draft` kèm bằng chứng nguồn, gửi cho `approving_stakeholder` xem xét và phê duyệt trước khi áp dụng.

## Allowed Tool Calls
Không có tool call trực tiếp (Artifact & Proposal only).

## Output Format
- **culture-principles-draft**: Tài liệu giá trị cốt lõi và nguyên tắc vận hành, kèm bằng chứng thực tiễn nguồn, và trạng thái rõ ràng "chưa được phê duyệt, cần con người xác nhận trước khi áp dụng".

## Fallback & Handoff
- Khi thiếu bằng chứng thực tiễn đủ để soạn thảo, tạo Handoff đề xuất Founder cung cấp thêm ví dụ/tình huống thực tế.
- Sau khi hoàn thành bản thảo, luôn tạo Handoff gửi `approving_stakeholder` phê duyệt — skillpack không tự coi bản thảo là chính thức.

## Eval Notes
- Suite: `evals/people/culture-operating-principles.yaml`
