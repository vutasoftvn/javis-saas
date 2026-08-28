# Customer Engagement — Implementation Overview (P0–P4, gated rollout)

> **For agentic workers:** đây là tài liệu điều phối. Mỗi phase có plan chi tiết riêng
> (`2026-08-28-customer-engagement-p{0..4}.md`) với task bite-sized theo
> `superpowers:subagent-driven-development`. Đọc file này trước để nắm phân kỳ + rollout gate,
> rồi thực thi theo plan của phase tương ứng.

**Goal:** Xây domain **Customer Engagement** native cho COSA (support / success / sales-assist) —
inbox, hội thoại khách ↔ doanh nghiệp đa kênh, human takeover, Decision Request cho quyết định có
thẩm quyền, và agent chỉ tự hành trong phạm vi policy — theo mô hình **human-led, agent-augmented**.

**Architecture:** Customer Engagement là aggregate mới trong `services/company/commercial` (Encore/TS,
Drizzle, Postgres), tham chiếu CRM `sales.*` / `commercial.*` bằng workspace-scoped ref, **không** nhân
bản CRM. State vận hành hội thoại (thread / message / assignment / outcome / decision request) do
Company Service sở hữu; nó phát business fact qua transactional outbox hiện có
(`integration.event_outbox` + relay). Agent Platform (`packages/agent_core` + `apps/cosa`) chỉ nhận
context đã lọc qua capability và trả reasoning/artifact; mọi side effect của agent đi qua
Capability + Governance + Approval + Audit. Deterministic automation (routing/SLA/label) là code
xác định trong `commercial`, không phải LLM.

**Tech Stack:** TypeScript strict, Encore, Drizzle ORM, PostgreSQL 16, Vitest (integration-style, real
DB). Python 3.11, pytest (cho capability + agent spec + eval, từ P1). Không thêm broker.

**Spec:** [`docs/superpowers/specs/2026-08-28-customer-engagement-human-agent-design.md`](../specs/2026-08-28-customer-engagement-human-agent-design.md) (Proposed).
Chatwoot chỉ là tham chiếu mô hình — **không** dependency (không self-host / fork / gọi API / phụ thuộc runtime).

---

## Đối chiếu spec ↔ code thật (đã explore 2026-08-28)

Phần kiến trúc nền của spec **chính xác**, tái dùng nguyên trạng — không phản biện:

| Spec giả định | Xác minh |
| --- | --- |
| CRM `sales.accounts/contacts/sales_leads/sales_opportunities/customers`, `commercial.invoices/subscriptions` | Khớp — `services/company/shared/db/schema/commercial.ts` |
| `WorkforceMember` hợp nhất người + agent (`member_type HUMAN\|AI_AGENT`, `manager_member_id`, `agent_spec_id`) | Khớp — `shared/db/schema/identity.ts` |
| `TenantContext` server-authoritative; query ràng `id AND workspace_id` | Khớp — `requireWorkspaceAccess()`, `commercial/services/*.service.ts` |
| Event envelope (`eventId`, `eventType` `domain.entity.action.vN`, `correlationId/causationId`, `actor{kind,id}`, `classification`); `restricted` ⇒ payload chỉ ID/ref/hash | Khớp — `shared/events/envelope.ts` (regex `^[a-z0-9_]*(id\|ref\|hash\|count)$`) |
| Transactional outbox `appendOutboxEvent(tx, …)` cùng transaction + relay (claim token / backoff / DLQ) | Khớp — `shared/events/outbox.repository.ts`, `company/events/outbox-relay.service.ts` |
| Capability gateway + registry + governance xác định + durable approval bind `(run_id, tool_call_id, checkpoint_ref)` | Khớp — `packages/agent_core/capabilities/`, `apps/cosa/policies/evaluator.py` |
| Event intake → trigger rule → reference-only run; promotion gate (eval evidence / action boundary / human approval) | Khớp — `apps/cosa/events/`, `trigger_promotion.py` |
| Migration numbered `.up.sql`, `make services-migrate-company` | Khớp (chỉ `.up.sql`, **không** có `.down.sql` trong repo) |

Khác biệt phải xử lý:

| Vấn đề | Thực tế | Xử lý |
| --- | --- | --- |
| `makeBusinessEvent` hard-code `producer.service = "company.operations"` (`shared/events/envelope.ts:7`) | Không có override | **P0 Task 1** thêm `producer?` vào `BusinessEventInput` |
| Customer 360 read API | Chưa có — chỉ single-entity CRUD | **P0** build aggregation trong `commercial` |
| Trùng tên `conversation_*` | `packages/agent_core/conversations/` đã có `agent_conversation.conversations/messages` (chat agent↔user nội bộ, khác hẳn) | Prefix mọi aggregate mới `engagement_*` |
| Event backbone consumer | `zero production consumer` tính đến 2026-08-25; evidence re-check trong `TriggerPolicyService` còn tùy chọn; dispatch qua `HttpControlPlaneSchedulerClient` đồng bộ, chưa durable `scheduled_tasks` | Vá trong **P4 acceptance gate**; không chặn xây/test P4 trong test env |
| Runtime kernel | Mặc định `ManualToolLoopKernel`; OpenAI Agents SDK opt-in | P1 tham chiếu đúng kernel |
| Agent spec | Hard-code `apps/cosa/agents/specs.py` + `seed.py` | P1 thêm Copilot spec cứng thứ tư, version/hash-pinned |

---

## Phân kỳ & rollout gate

Thứ tự phase **cố ý khác spec §13** để ưu tiên test-safety (human-invoked Copilot trước bất kỳ bề mặt
kênh/automation nào; autopilot event-driven sau cùng, sau feature flag).

| Phase | Deliverable chính | Test env | Production rollout gate |
| --- | --- | --- | --- |
| **P0** | Human Desk + engagement schema + outbox emit + RBAC + Decision Request (authority binding fail-closed, N-of-M approvers) + SLA snapshot/escalation + retention/legal-hold/DSR | full E2E + test matrix spec §15 | Test matrix xanh; tenant-isolation review; migration áp sạch DB mới; 7 authority key seeded + bound; `SLA_POLICY_SEED` + escalation routes bound; `retention_until` NOT NULL enforced |
| **P1** | Customer Support Copilot artifact-only, **human-invoked** từ Desk | eval suite + draft-quality review | Eval evidence tươi; capability chỉ read/draft; 0 auto-send trong test |
| **P2** | 1 channel adapter thật + inbound/outbound + CRM sync | provider sandbox E2E; dedupe/retry drill | Signature verify + dedupe + outbox atomic proven; DLQ visibility cho WorkforceMember |
| **P3** | Deterministic rule evaluator trong `commercial` | rule replay + delayed re-check tests | Rule versioned; delayed rule re-check state trước execute; **no LLM** trong condition |
| **P4** | Autopilot event-driven, **feature-flagged** | staging E2E qua event intake → durable run | **Acceptance gate P4** (bên dưới) đạt bằng bằng chứng vận hành |

### Acceptance gate P4 (điều kiện mở production cho autopilot event-driven)

Tất cả xác nhận **bằng bằng chứng vận hành thật**, không chỉ code review:

1. Event consumer chạy end-to-end trên staging: `engagement.*` outbox → intake → trigger rule → durable
   run → capability → audited action (hiện `zero production consumer` 2026-08-25 — phải vá).
2. Dispatch durable: chuyển event→run từ `HttpControlPlaneSchedulerClient` đồng bộ sang durable
   `scheduled_tasks` của `services/cosa` (claim token + retry backoff + DLQ).
3. Evidence re-check **bắt buộc**: wire `evidence_store` + `fingerprint_provider` vào
   `TriggerPolicyService` (`apps/cosa/events/trigger_policy.py`) — không còn tùy chọn.
4. Retry / DLQ cho cả outbox relay và run dispatch, có visibility cho operator.
5. Observability: p95 delivery latency + replay-duration histogram (gap ghi trong
   `docs/operations/event-backbone-capacity-review.md`) + dashboard containment/error/takeover.
6. Chaos/durability: test "resume sau restart" qua **process thật** (CLAUDE.md #6).
7. Containment / unsafe-proposal / policy-violation dưới ngưỡng đã định trong ≥1 chu kỳ quan sát.

Cho tới khi 7 điểm trên đạt: `engagement.autopilot.enabled` = **off** trên production, **on** ở test env.

---

## Global Constraints (áp cho mọi phase — mọi task ngầm bao gồm mục này)

- **TDD bắt buộc**: test đỏ → chạy xác nhận đỏ → implement tối thiểu → chạy xác nhận xanh → commit.
  Không tuyên bố xong khi chưa chạy test (CLAUDE.md #11).
- **An toàn working tree** (CLAUDE.md #10): `git status` trước thao tác có thể mất dữ liệu; không
  `--force` / `--no-verify` trừ khi được yêu cầu rõ; không tự xoá/archive file không liên quan.
- **Tenant**: mọi bảng mới `workspace_id BIGINT NOT NULL`; mọi query/update/link/delete ràng
  `id AND workspace_id`; link chéo CRM khác workspace bị chặn ở DB (composite constraint) lẫn service.
  Handler lấy workspace từ `requireWorkspaceAccess()` → `TenantContext`, **không** nhận `workspaceId`
  tin cậy từ body cho path có auth header.
- **Encore** (CLAUDE.md): lỗi qua `APIError` (`invalidArgument`/`unauthenticated`/`permissionDenied`/
  `notFound`/`alreadyExists`/`internal`) — không throw `Error` trần. Endpoint nội bộ giữa service:
  `expose: false`; chỉ client ngoài mới `expose: true`. Schema Drizzle tập trung ở
  `services/company/shared/db/schema/` — **không** rải trong `models/`. Handler chỉ parse input + gọi
  service; query/transaction ở service.
- **`packages/agent_core` KHÔNG import từ `apps/` hay `services/`.** Composition chỉ ở `apps/cosa/`.
- **Naming**: mọi aggregate Customer Engagement prefix `engagement_`.
- **State structured**: transition là command có validation + event đã version. Không
  `if "blocked" in text`. Không suy state từ nội dung message.
- **Event**: business fact past tense, phát qua `appendOutboxEvent(tx, …)` **cùng transaction** với
  state write. `restricted` ⇒ payload chỉ ID/ref/hash. Không nhúng token/secret/full transcript/PII thừa.
- **No chain-of-thought** trong transcript / internal note / approval / audit — chỉ summary + reason
  code + evidence ref.
- **Migration**: chỉ `.up.sql` (repo không dùng `.down.sql`); kiểm số cao nhất *ngay trước khi tạo*
  (`services/company/commercial/migrations/` hiện = **10** ⇒ file mới `11_...`). Sau khi thêm:
  `make services-migrate-company` (`node scripts/migrate.mjs`); `--check` để preflight.
- **Comment**: tiếng Việt cho "why"; identifier / log / error / trích tài liệu English giữ nguyên.
- **Risk cao cần approval qua code** (deploy, xoá dữ liệu, gửi tin ra ngoài, đổi quyền, hành động tài
  chính) — không qua prompt (CLAUDE.md #8).

---

## Câu hỏi spec §17 — trạng thái

| §17 | Chặn phase | Trạng thái |
| --- | --- | --- |
| 2, 7 — authority + dual/triple-control | **P0** | **ĐÃ CHỐT 2026-08-28** — 7 authority key + `approval_policy` N-of-M, fail-closed `pending_binding`→`enabled`. Xem [P0 plan §"P0 policy defaults"](./2026-08-28-customer-engagement-p0.md). |
| 4 — retention / residency / export-delete | **P0** | **ĐÃ CHỐT 2026-08-28** — `retention_until` NOT NULL, mặc định 365/90/730 ngày; legal hold record; DSR export (24h, loại internal note) + delete (suppress ngay, purge ≤30d, backup ≤35d); raw chỉ ở `workspace_home_region`. |
| 5 — SLA per tier + escalation ngoài giờ | **P0** | **ĐÃ CHỐT 2026-08-28** — `SLA_POLICY_SEED` standard/priority/vip; snapshot deadline trên thread; `engagement_escalation_routes` bind `WorkforceMember` (fail-closed). |
| 1 — kênh ngoài ship trước | **P2** | mở — mặc định web chat nếu chưa chốt |
| 3 — policy nào auto-reply, ngôn ngữ nào, knowledge source/version | **P4** | mở — input promotion gate |
| 6 — sales stage transition nào chỉ người / nào deterministic sau approval | **P3** | mở — input rule model |

### Nguyên tắc fail-closed (chốt 2026-08-28, áp mọi phase)

Không có authority `enabled` + đủ grant hợp lệ ⇒ **không cho approve/execute** Decision Request. Không có
escalation route bind tới `WorkforceMember` thật ⇒ **không bật inbox tier** cần route đó. Thiếu binding =
từ chối, không phải cảnh báo. `retention_until` không được null; không có "giữ vô thời hạn"; legal hold là
record riêng có hạn, không âm thầm kéo dài retention.

---

## Phase plan index

| Phase | File | Trạng thái |
| --- | --- | --- |
| P0 | `2026-08-28-customer-engagement-p0.md` | drafted (16 task) |
| P1 | `2026-08-28-customer-engagement-p1.md` | drafted (13 task) — Copilot artifact-only, human-invoked, không kích bằng event |
| P2 | `2026-08-28-customer-engagement-p2.md` | drafted (11 task) — kênh tham chiếu Zalo OA; adapter mới không đụng schema/relay core; §17.1 chốt kênh tiếp theo |
| P3 | `2026-08-28-customer-engagement-p3.md` | drafted (11 task) — rule evaluator typed/versioned, no-LLM guard, delayed re-check; thay pass SLA-escalation hardcode P0 bằng seeded rule |
| P4 | `2026-08-28-customer-engagement-p4.md` | drafted (12 task) — autopilot FAQ hẹp, durable approval checkpoint, 7-point Acceptance Gate ADR; production forced-off cho tới ADR ACCEPTED |

P1–P4 được viết chi tiết theo cùng cấu trúc bite-sized khi phase trước đã landed (interface names /
table columns ổn định), theo tiền lệ `2026-08-28-event-driven-agent-operating-model-p{0,1,2}.md`.
