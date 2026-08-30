---
name: customer-success-lifecycle
description: Đề xuất playbook vòng đời khách hàng (onboarding, adoption, renewal, expansion) dựa trên tín hiệu sức khỏe tài khoản trong giai đoạn Operate & Growth.
---

# Playbook Vòng Đời Khách Hàng (Customer Success Lifecycle)

## Mục đích & Giới hạn Quyền hạn
Đề xuất playbook hành động theo từng giai đoạn vòng đời khách hàng (onboarding, adoption, renewal, expansion, at-risk) dựa trên tín hiệu sức khỏe tài khoản (product usage, hỗ trợ, phản hồi), phục vụ đội Customer Success trong giai đoạn P5_OPERATE_GROWTH.

> **Quy tắc an toàn & Quản trị vòng đời:**
> Skillpack này CHỈ đưa ra dự thảo artifact (`lifecycle-playbook-proposal`, `account-task-proposal`). Skillpack này TUYỆT ĐỐI KHÔNG tự động kích hoạt (auto-trigger) bất kỳ hành động tài khoản nào — bao gồm upsell, downgrade hay hủy hợp đồng (cancellation) — mà chỉ đề xuất playbook/task cụ thể để con người thực thi. Skillpack này KHÔNG được sử dụng thuộc tính bảo vệ/nhạy cảm của khách hàng (chủng tộc, tôn giáo, giới tính, tình trạng sức khỏe, hoặc thuộc tính cá nhân nhạy cảm tương tự) để suy ra tín hiệu sức khỏe tài khoản (health signal).

## Triggers
- Kích hoạt khi cần đề xuất playbook cho một tài khoản khách hàng cụ thể đang chuyển giai đoạn vòng đời (onboarding → adoption → renewal/expansion).
- Kích hoạt khi phát hiện tín hiệu rủi ro (at-risk) từ dữ liệu sử dụng hoặc hỗ trợ và cần đề xuất task can thiệp.

## Anti-triggers
- Không kích hoạt khi cần tự động thực hiện hành động tài khoản (upsell, downgrade, cancellation) — mọi hành động này phải do con người thực thi sau khi xem xét đề xuất.
- Không kích hoạt khi dữ liệu đầu vào chứa hoặc yêu cầu dùng thuộc tính bảo vệ/nhạy cảm của khách hàng để suy ra tín hiệu sức khỏe.
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.

## Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.
- `account_health_signals`: Tín hiệu sức khỏe tài khoản (product usage, ticket hỗ trợ, khảo sát hài lòng, tần suất đăng nhập) — không bao gồm thuộc tính bảo vệ/nhạy cảm.

## Evidence Rules
- Mọi tín hiệu sức khỏe dùng để đề xuất playbook phải xuất phát từ dữ liệu hành vi/sử dụng/hỗ trợ đã ghi nhận, không suy diễn từ thuộc tính cá nhân nhạy cảm.
- Nếu dữ liệu health signal không đầy đủ hoặc lỗi thời, gắn nhãn giả định (`assumption`) và giảm mức độ tin cậy của đề xuất tương ứng.
- Mọi bằng chứng trích xuất được tạo dưới dạng `candidate` và phải qua phê duyệt của Customer Success Lead/Founder trước khi ghi nhận chính thức.

## Quy trình thực hiện (Steps)
1. **Xác định Giai đoạn Vòng đời**: Xác định tài khoản đang ở giai đoạn nào (onboarding/adoption/renewal/expansion/at-risk) dựa trên tín hiệu sức khỏe hợp lệ.
2. **Rà soát Tín hiệu**: Kiểm tra `account_health_signals` để đảm bảo không chứa thuộc tính bảo vệ/nhạy cảm; loại bỏ nếu phát hiện.
3. **Đề xuất Playbook**: Xây dựng playbook hành động phù hợp giai đoạn (ví dụ: checklist onboarding, chiến dịch adoption, kịch bản renewal, đề xuất intervention khi at-risk).
4. **Soạn Task Đề xuất**: Liệt kê các task cụ thể kèm người thực thi đề xuất (đội CS/Founder), không tự động kích hoạt hành động tài khoản nào.
5. **Đóng gói Artifacts**: Tạo bản nháp `lifecycle-playbook-proposal` và `account-task-proposal` để Customer Success Lead/Founder xem xét và phê duyệt.

## Allowed Tool Calls
Không có tool call trực tiếp (Artifact & Proposal only).

## Output Format
- **lifecycle-playbook-proposal**: Giai đoạn vòng đời hiện tại, tín hiệu sức khỏe đã dùng, và playbook hành động đề xuất theo giai đoạn.
- **account-task-proposal**: Danh sách task cụ thể (không tự kích hoạt) kèm người thực thi đề xuất, mức ưu tiên và lý do dựa trên tín hiệu sức khỏe.

## Fallback & Handoff
- Khi tín hiệu sức khỏe không đủ để xác định giai đoạn vòng đời hoặc mức độ rủi ro, tạo thông báo Handoff đề xuất Customer Success Lead xác minh thủ công qua trao đổi trực tiếp với khách hàng.

## Eval Notes
- Suite: `evals/customer-success/lifecycle.yaml`
