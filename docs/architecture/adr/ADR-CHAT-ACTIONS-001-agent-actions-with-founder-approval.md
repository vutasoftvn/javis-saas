# ADR-CHAT-ACTIONS-001: Agent chat thực thi hành động nghiệp vụ sau khi founder duyệt

## Status
ACCEPTED 2026-09-27 (Lưu ý: ACCEPTED ≠ IMPLEMENTED ≠ WIRED ≠ VERIFIED ≠ PRODUCTION).
Spec: [`2026-09-27-chat-business-actions-design.md`](../../superpowers/specs/2026-09-27-chat-business-actions-design.md),
plan: [`2026-09-27-chat-business-actions.md`](../../superpowers/plans/2026-09-27-chat-business-actions.md).

Trạng thái triển khai: IMPLEMENTED + WIRED ở code (apps/cosa, services/company, frontend) và
có test đơn vị/tích hợp với model giả. **Chưa VERIFIED** trên stack chạy thật (company + worker +
model thật) — xem nhật ký triển khai trong roadmap `2026-09-27-cosa-comprehensive-review-and-roadmap.md`.

## Context

Plan Startup OS 2026-09-18 chốt nguyên tắc "Onboard inform, not control": tạo Goal và triage
discovery Project là quyết định của Founder, nên `startup_os.goal.create` và
`startup_os.project.triage` KHÔNG được đăng ký cho agent và company không mở delegation cho hai
endpoint đó. Hệ quả: chat Co-Founder chỉ đọc được task/dự án; Founder hỏi "căn cứ OKR hãy thiết lập
mục tiêu" thì agent trả lời "không có công cụ", phải tự thao tác trên màn hình khác.

Cùng lúc, nhiều capability ghi đã có nhưng không agent nào dùng, và API OKR của company
(`/operations/objectives`, `/operations/key-results`) chưa có capability nào bọc.

## Decision

1. **Bậc hành động T0–T3** là một nguồn sự thật: `apps/cosa/capabilities/access_matrix.py`.
   T0 đọc, T1 nháp/hoàn tác được, T2 ghi thật vào dữ liệu nội bộ, T3 ra ngoài/không hoàn tác.
2. **Agent chat được đề xuất VÀ thực thi hành động T2** (tạo Goal, triage Project, tạo/check-in
   Key Result, chuyển trạng thái task, cập nhật hồ sơ khởi nghiệp) **chỉ sau khi founder bấm
   Duyệt ngay trong chat**. Quyết định vẫn thuộc founder; agent chỉ soạn tham số và thực thi.
   - Chat run gắn `REQUIRE_APPROVAL_CAPABILITIES_KEY = CHAT_T2_CAPABILITIES` vào metadata (và vào
     context khi resume). Policy engine chỉ SIẾT ALLOW → REQUIRE_APPROVAL (`RoleApproval("founder")`);
     DENY của company/tenant giữ nguyên.
   - Approval bind `run_id + tool_call_id + checkpoint_ref` (quy tắc 5); từ chối cũng resume run
     chat với quyết định "từ chối" để agent trả lời tiếp (tool không chạy).
3. **Company mở delegation theo từng endpoint**, đúng capability trong matrix
   (`AGENT_CAP` + `requireWorkspaceAccess/Write(..., { agentCapabilities })`). Agent đi qua
   membership/role của chính founder — không vượt quyền user (auditor vẫn bị chặn ghi).
4. **T3 không mở cho agent chat**: `engagement.message.send`, `finance.accounting_document.confirm`,
   thanh toán. `finance.transaction.record` là T2 nhưng chưa đưa vào spec chat cho tới khi founder
   chốt hạn mức (spec §8.3).
5. **CI chặn lệch pha** spec agent ↔ registry ↔ matrix ↔ `agent-capabilities.ts`
   (`tests/apps/cosa/test_access_matrix_parity.py`).

## Consequences

- Spec `cosa.agents.operations` lên 1.6.0 (autonomy L2 "execute with approval"); pin phía company
  (`AGENT_PROFILE_SPEC_VERSION/HASH`) cập nhật cùng.
- Mọi hành động T2 đi qua CapabilityGateway (audit, idempotency) như các capability khác.
- Môi trường dùng compliance thật (không `COSA_COMPLIANCE_MOCK`): deployment AI của workspace phải
  có capability binding cho capability mới (kể cả các capability đọc mà `business.read` dispatch
  tới), nếu không company trả 404 "out of scope" cho cả snapshot và run bị từ chối.
- **Live authorization ticket vẫn áp dụng** cho mọi capability ghi (gateway → company
  `/identity/agent-authorization/tickets`): chat run mang `agent_workforce_member_id` của AI member
  giữ profile trong Project team (resolve lại khi resume). Company chỉ cấp ticket khi capability có
  `core.capability_permission_bindings` và founder đã cấp grant cho AI member đó. Hiện migration chỉ
  seed binding cho `operations.task.list` ⇒ hành động T2 trong chat sẽ bị từ chối ở bước ticket cho
  tới khi có binding + grant — cố ý KHÔNG vượt qua lớp này (xem mục "Việc còn mở" trong nhật ký
  roadmap). Đây là quyết định quản trị riêng cần founder chốt.
- Thêm một bậc duyệt trong chat: founder phải phản hồi thẻ duyệt; hết hạn duyệt dùng cơ chế
  approval hiện hữu (spec §8.1 chưa chốt thời hạn riêng).

## Alternatives considered

- **Agent tự ghi không cần duyệt:** loại — vi phạm quy tắc 8 (hành động rủi ro cần approval qua code)
  và nguyên tắc founder quyết định.
- **Chỉ soạn nháp, founder tự áp dụng trên màn khác:** loại — chính là trải nghiệm đứt đoạn cần sửa;
  duyệt ngay trong chat giữ quyết định ở founder mà không bắt chuyển màn.
- **Nối từng capability đọc vào spec chat:** loại — schema tool quá dài cho model yếu; thay bằng
  một tool `business.read` dispatch theo domain, không thêm quyền mới.
