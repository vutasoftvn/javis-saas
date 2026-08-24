# Hướng dẫn: Thêm capability mới

## Khi nào cần

Khi agent cần thực hiện 1 side effect mới (đọc/ghi business data, gửi tin nhắn ra ngoài, hành động tài chính...). Theo CLAUDE.md quy tắc #1: business truth thuộc `services/*`, Agent Platform không tự ghi business DB trực tiếp.

## Các bước

1. **Trước tiên xác nhận capability CHƯA tồn tại** — grep `capability_id`/`CapabilitySpec` trong `packages/agent_core/capabilities/` và registry publish records. Ví dụ đã confirm trong phiên này: chỉ có `operations.task.list`, `operations.task.read`, `finance.payout.execute`, `finance.transaction.record` là capability thật đăng ký — nhiều recipe Wave 11 tham chiếu `web.search` nhưng KHÔNG tồn tại (ghi rõ trong `docs/recipes/*.md` thay vì giả định).
2. Nếu business logic thật (đọc/ghi DB) → viết ở `services/company/*` hoặc `services/cosa/*` (Encore/TypeScript) trước, expose endpoint `expose: false` (nội bộ) trừ khi cần public.
3. Viết `CapabilitySpec` (`packages/agent_core/contracts/capability.py`) mô tả input schema, risk level, idempotency requirement.
4. Nếu risk cao (deploy, xoá dữ liệu, gửi tin nhắn ra ngoài, đổi quyền, hành động tài chính — CLAUDE.md #8) → set governance policy yêu cầu `REQUIRE_APPROVAL`, KHÔNG để LLM tự quyết định qua prompt.
5. Đăng ký handler thật thực thi side effect (gọi HTTP client tới `services/*`) — chỉ `CapabilityGateway.execute()` được gọi handler này, không có execution path tắt nào khác.
6. Nếu cần exactly-once (thao tác không idempotent tự nhiên, vd charge tiền): đảm bảo `idempotency_key` được truyền và `IdempotencyClaimService` claim atomic trước khi gọi handler (xem `docs/features/idempotency.md`).
7. Viết test trong `agent_testkit/gateway_conformance/` — tối thiểu: happy path, approval-required path, idempotency-conflict path.
8. Viết `docs/features/<capability-domain>.md` nếu là domain mới, hoặc cập nhật file domain đã có.

## Không được làm

- Không hard-code authorization logic trong prompt/skill instructions — approval/governance luôn là code xác định (CLAUDE.md #5, #8).
- Không tạo Agent Profile mới chỉ để wrap 1 capability — capability không cần agent riêng (CLAUDE.md #3).
