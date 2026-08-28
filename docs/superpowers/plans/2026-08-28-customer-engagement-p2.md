# Customer Engagement — P2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Kênh khách hàng **thật** đầu tiên hoạt động hai chiều (inbound + outbound) sau `ChannelAdapter`
contract của P0, cộng **đồng bộ CRM** (link thread ↔ Contact/Account, không merge). Chứng minh: xác thực
chữ ký trên raw request, dedupe theo provider delivery id, ghi command + outbox **atomically**, ack
nhanh, outbound qua connector grant + `secret_ref`, retry/backoff/DLQ có visibility cho WorkforceMember.

**Kênh tham chiếu:** **Zalo OA** (sản phẩm VN-first — SLA seed đã dùng `Asia/Ho_Chi_Minh` +
`holiday_calendar: "VN"`). Mọi phần provider-specific gói trong **một** adapter + **một** webhook handler
+ **một** connector config; web chat / email / WhatsApp / Facebook sau này = lặp lại Task 2/5/6 với
adapter mới, **không** đụng schema (Task 1) hay relay core (Task 6). Nếu chủ sở hữu chốt kênh khác
(§17.1), thay "zalo" bằng tên đó — cấu trúc plan không đổi.

**Architecture:** Webhook đến `services/company/commercial` (Encore `api.raw` để lấy raw bytes) →
`adapter.verifyInbound(rawReq)` (HMAC theo `verification_config` của endpoint) → dedupe
(`engagement_channel_inbound_events` + `engagement_messages.external_message_id`) → resolve endpoint →
find/create thread theo `external_conversation_ref` → `resolveContact` (P0, inline, rẻ) hoặc review item
/ auto-create theo cờ → insert inbound message + `appendOutboxEvent(engagement.message.received.v1)` **cùng
transaction** → **200 OK nhanh**. Enrichment nặng chạy async. Outbound: `engagement-delivery-relay` (P0)
với `channel_type != "api"` → gọi `services/cosa` `POST /cosa/connectors/assert` lấy `secretRef` →
`resolveChannelSecret(secretRef)` → `adapter.sendOutbound(cmd, token)`; adapter **không bao giờ** thấy
`secret_ref`, **không** persist token.

**Tech Stack:** TypeScript strict + Encore (`api.raw`) + Drizzle + Vitest, `services/company` +
`services/cosa` (control plane, đã có connector lifecycle). Không thêm broker.

**Spec:** [`docs/superpowers/specs/2026-08-28-customer-engagement-human-agent-design.md`](../specs/2026-08-28-customer-engagement-human-agent-design.md) —
P2 phủ §9 (Channel Adapter đa kênh không phụ thuộc provider), §5.2 (identity resolution / link, không
merge), §8.4 (`billing.*` vẫn deny; P2 chỉ inbound/outbound message + link CRM), §13 P2.

**Overview:** [`2026-08-28-customer-engagement-overview.md`](./2026-08-28-customer-engagement-overview.md).
**Tiền đề:** [P0](./2026-08-28-customer-engagement-p0.md) landed — dùng `ChannelAdapter` contract
(`channel-adapters/contract.ts`), `engagement_channel_endpoints`, `engagement_outbound_deliveries` +
`engagement-delivery-relay.service.ts`, `resolveContact` / `engagement_identity_review_items`,
`recordInboundMessage` logic, event builder `company.commercial`. [P1](./2026-08-28-customer-engagement-p1.md)
landed nhưng **không** phải phụ thuộc của P2.

## Global Constraints

- **TDD bắt buộc** (CLAUDE.md #11); **an toàn working tree** (CLAUDE.md #10); comment "why" tiếng Việt.
- **Fail-closed** (kế thừa P0/P1): endpoint kênh chỉ chuyển `status='active'` khi có
  `verification_config_ref` phân giải được **và** `connector_key` có installation + authorization hợp lệ
  ở `services/cosa`. Thiếu ⇒ endpoint ở `pending` / `paused`, webhook trả `200` nhưng **drop** (không ghi
  message), relay **skip**.
- **Không tin dữ liệu client gửi** (§9.5): `verifyInbound` chạy trên **raw bytes** trước khi parse JSON;
  chữ ký sai / thiếu / timestamp lệch quá `skew` ⇒ `401`, **không** ghi gì.
- **Idempotency**: một provider `delivery id` / `message id` retry ⇒ **0** message trùng, **0** CRM
  effect trùng. Dedupe ở `engagement_channel_inbound_events` (raw) **và** partial unique
  `engagement_messages(workspace_id, external_message_id)` (P0).
- **Atomic ack**: verify → dedupe → `db.transaction`(insert message + `appendOutboxEvent`) → **rồi mới**
  `200`. Không gọi model / enrichment nặng / HTTP ngoài trong request webhook.
- **Không merge CRM** (§5.2.4): P2 chỉ **link** `contact_id`/`account_id` khi khớp chắc chắn (email
  verified exact) hoặc **tạo mới** Contact khi endpoint bật `auto_create_contact` và identity kênh là
  authoritative — **không bao giờ** merge 2 Contact/Account. Nhập nhằng ⇒ `engagement_identity_review_items`.
- **Secret**: worker/relay **không** giữ raw provider credential; Control Plane trả `secret_ref`;
  `resolveChannelSecret` là seam duy nhất phân giải ref → token, không log token, không persist.
- **`billing.*` / write nghiệp vụ khác vẫn deny** — P2 không mở gì ngoài inbound/outbound message + link
  CRM. Lead/Opportunity từ sales intent = P3.
- **Migration**: chỉ `.up.sql`. Sau P1 = `12_` ⇒ P2 dùng `13_` (xác nhận `ls` trước khi tạo).
  `make services-migrate-company` sau đó.

---

## File Structure

| File | Trách nhiệm |
| --- | --- |
| `services/company/shared/db/schema/customer-engagement.ts` | (Modify) `engagement_channel_inbound_events`; cột mới trên `engagement_threads` (`external_conversation_ref`) + `engagement_channel_endpoints` (`connector_key`, `inbound_routing_key`, `auto_create_contact`, `status` thêm `pending`/`paused`). |
| `services/company/commercial/migrations/13_engagement_channels.up.sql` | (Create). |
| `services/company/commercial/services/customer-engagement/channel-adapters/zalo-channel.adapter.ts` | (Create) `ZaloChannelAdapter implements ChannelAdapter`. |
| `services/company/commercial/services/customer-engagement/channel-adapters/registry.ts` | (Modify) thêm entry `zalo`. |
| `services/company/commercial/services/customer-engagement/channel-adapters/verification.ts` | (Create) `resolveVerificationConfig(ref)` + `verifyHmac(raw, config)`. |
| `services/company/commercial/services/customer-engagement/connector-grant.client.ts` | (Create) gọi `services/cosa` `/cosa/connectors/assert`. |
| `services/company/commercial/services/customer-engagement/channel-secret.ts` | (Create) `resolveChannelSecret(secretRef)` seam (Encore secret / env map ở P2 + TODO vault). |
| `services/company/commercial/services/customer-engagement/channel-inbound.service.ts` | (Create) `ingestInbound(channelType, rawReq)` — verify/dedupe/thread/message/outbox atomic. |
| `services/company/commercial/services/customer-engagement/channel-identity-sync.service.ts` | (Create) `linkThreadIdentity(threadId, signals, ctx)` — link / review-item / auto-create, no merge. |
| `services/company/commercial/services/customer-engagement/delivery-relay.service.ts` | (Modify) nhánh `channel_type != "api"`: connector assert → secret → `adapter.sendOutbound`; phân loại lỗi retryable/permanent. |
| `services/company/commercial/services/customer-engagement/housekeeping.service.ts` | (Modify) thêm pass `reconcileDeliveryStatus()` (gọi `adapter.getDeliveryStatus`). |
| `services/company/commercial/handlers/customer-engagement/channels/zalo.handler.ts` | (Create) `api.raw` webhook (verify challenge GET + event POST). |
| `services/company/commercial/handlers/customer-engagement/channel-admin.handler.ts` | (Create) CRUD endpoint (`expose:true`, RBAC): tạo endpoint, set verification config, activate/pause, list deliveries + errors. |
| `services/company/commercial/handlers/customer-engagement/index.ts` | (Modify) re-export. |
| `services/company/commercial/services/customer-engagement/rbac.ts` | (Modify) thêm `engagement.channel.manage`. |
| `services/cosa/handlers/workspace-connector.handler.ts` | (Verify/Modify) `assert` trả `secretRef` cho `action:"send"` — dùng nguyên nếu đủ; thêm test. |
| `services/company/commercial/tests/customer-engagement/channel-*.test.ts` | (Create) adapter / inbound / outbound / identity-sync / matrix. |
| `docs/operations/customer-engagement-channel-runbook.md` | (Create) onboard kênh mới, verification config format, DLQ triage. |
| `docs/architecture/customer-engagement-vocabulary.md` | (Modify) channel/endpoint states, delivery states, inbound-event outcomes. |

**Assumptions (verify trong repo):**
- `ChannelAdapter` interface (P0): `verifyInbound`, `normalizeInbound`, `sendOutbound`, `getDeliveryStatus`,
  `resolveExternalIdentity` — `channel-adapters/contract.ts`. P2 **mở rộng** `sendOutbound(cmd, secret: string)`
  (thêm tham số secret đã phân giải) — cập nhật contract + `ApiChannelAdapter` (secret bỏ qua).
- `engagement_outbound_deliveries` (P0): `status queued|sent|delivered|failed`, `claim_token`,
  `visibility_timeout_at`, `attempt_count`/`max_attempts`, `last_error`, `dead_letter_reason`,
  `external_message_id`, `channel_type`.
- `services/cosa` connector lifecycle **đã có**: `POST /cosa/connectors/install|authorize|grant|revoke|assert`
  (`services/cosa/handlers/workspace-connector.handler.ts`). `assert` gated `requireWorkerServiceAuth`,
  trả `{ ok, secretRef }`. Company gọi service-to-service (Encore) hoặc HTTP với worker service token.
- `api.raw({ expose, method, path }, async (req, resp) => {...})` — Encore raw endpoint, `req` là Node
  `IncomingMessage` (đọc raw body qua stream). Xác nhận version Encore hỗ trợ (`encore.dev ^1.58`).
- `resolveContact({ email?, phone?, emailVerified? }, threadId, ctx)` + `engagement_identity_review_items`
  (P0 Task 9).

---

### Task 1: Channel schema (dedupe + routing)

**Files:**
- Modify: `services/company/shared/db/schema/customer-engagement.ts`
- Create: `services/company/commercial/migrations/13_engagement_channels.up.sql`
- Test: `services/company/commercial/tests/customer-engagement/channel-schema.test.ts`

**Interfaces (Produces):** table object `engagementChannelInboundEvents`; cột mới.

- [ ] **Step 1: Xác nhận migration number** — `ls .../migrations | sort -V | tail -2` ⇒ `13_`.
- [ ] **Step 2: Test đỏ** — 3 bảng/cột: `engagement_channel_inbound_events` tồn tại + unique
  `(endpoint_id, provider_delivery_id)`; `engagement_threads.external_conversation_ref` + partial unique
  `(inbox_id, external_conversation_ref)`; `engagement_channel_endpoints.connector_key` NOT NULL default.
- [ ] **Step 3: Migration**

```sql
-- P2: kênh khách hàng thật — dedupe raw + routing + connector.
ALTER TABLE engagement.engagement_channel_endpoints
  ADD COLUMN connector_key TEXT NOT NULL DEFAULT '',        -- key ở services/cosa (install/authorize)
  ADD COLUMN inbound_routing_key TEXT,                      -- vd. Zalo OA id — map webhook → endpoint
  ADD COLUMN auto_create_contact BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN skew_seconds INTEGER NOT NULL DEFAULT 300;
-- status: 'active' | 'pending' | 'paused' (P0 default 'active' — P2 seed kênh thật ở 'pending')
CREATE UNIQUE INDEX uq_engagement_channel_endpoints_routing
  ON engagement.engagement_channel_endpoints(workspace_id, inbound_routing_key)
  WHERE inbound_routing_key IS NOT NULL;

ALTER TABLE engagement.engagement_threads
  ADD COLUMN external_conversation_ref TEXT;
CREATE UNIQUE INDEX uq_engagement_threads_external_conv
  ON engagement.engagement_threads(inbox_id, external_conversation_ref)
  WHERE external_conversation_ref IS NOT NULL;

CREATE TABLE engagement.engagement_channel_inbound_events (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  endpoint_id BIGINT NOT NULL,
  provider_delivery_id TEXT NOT NULL,          -- id gói tin thô của provider
  provider_message_id TEXT,                    -- id message (nếu tách biệt)
  received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  outcome TEXT NOT NULL DEFAULT 'accepted',    -- accepted | duplicate | rejected_signature | dropped_paused | error
  thread_id BIGINT,
  message_id BIGINT,
  error TEXT,
  raw_hash TEXT NOT NULL                       -- sha256(raw body) — audit, KHÔNG lưu raw body
);
CREATE UNIQUE INDEX uq_engagement_channel_inbound_events_dedupe
  ON engagement.engagement_channel_inbound_events(endpoint_id, provider_delivery_id);
CREATE INDEX idx_engagement_channel_inbound_events_ep
  ON engagement.engagement_channel_inbound_events(endpoint_id, received_at);
```

- [ ] **Step 4: Drizzle schema** — thêm `engagementChannelInboundEvents` + cột mới, export.
- [ ] **Step 5: Áp migration** — `make services-migrate-company`; `--check` clean.
- [ ] **Step 6: Chạy — xanh** + `npx tsc --noEmit`.
- [ ] **Step 7: Commit** `feat(engagement): P2 channel schema — inbound dedupe + external conversation routing`.

---

### Task 2: `ChannelAdapter.sendOutbound(cmd, secret)` contract + Zalo adapter

**Files:**
- Modify: `services/company/commercial/services/customer-engagement/channel-adapters/contract.ts`
- Modify: `.../channel-adapters/api-channel.adapter.ts` (bỏ qua tham số secret)
- Create: `.../channel-adapters/verification.ts`
- Create: `.../channel-adapters/zalo-channel.adapter.ts`
- Modify: `.../channel-adapters/registry.ts`
- Test: `.../tests/customer-engagement/channel-adapter-zalo.test.ts`

**Interfaces (Produces):**
- `contract.ts` — `sendOutbound(cmd: OutboundCommand, secret: string | null): Promise<DeliveryResult>`
  (thêm `secret`). `OutboundCommand` thêm `externalConversationRef: string | null`.
- `verification.ts`:
  - `type VerificationConfig = { scheme: "hmac_sha256"; secretRef: string; header: string; encoding: "hex" | "base64"; signedPayload: "raw" | "raw_plus_timestamp"; timestampHeader?: string; skewSeconds: number }`.
  - `resolveVerificationConfig(ref: string): Promise<VerificationConfig>` — phân giải từ Encore secret /
    store P2 (TODO vault). Không có ⇒ throw `APIError.failedPrecondition`.
  - `verifyHmac(rawBody: Buffer, headers: Record<string,string|undefined>, config: VerificationConfig): void` —
    tính HMAC, so sánh **hằng-thời-gian** (`crypto.timingSafeEqual`); kiểm timestamp skew; sai ⇒
    `APIError.unauthenticated("invalid channel signature")`.
- `zalo-channel.adapter.ts` — `ZaloChannelAdapter implements ChannelAdapter`, `channelType = "zalo"`:
  - `verifyInbound(raw)` — gọi `verifyHmac` với `VerificationConfig` của endpoint (scheme + header theo
    **tài liệu Zalo OA** — xác minh ở Step 1 spike); trả `VerifiedInbound { externalMessageId, senderRef,
    externalConversationRef, body, receivedAt }`.
  - `normalizeInbound(v)` → `{ body, senderRef, externalMessageId, externalConversationRef }`.
  - `sendOutbound(cmd, secret)` — POST tới Zalo OA send API với `access_token = secret`; map response →
    `{ status: "sent", externalMessageId }` hoặc `{ status: "failed", error, permanent: boolean }`
    (phân loại: 401/403/invalid token → `permanent`; 429/5xx/timeout → không permanent).
  - `getDeliveryStatus(externalMessageId)` — nếu Zalo hỗ trợ tra cứu → map; nếu không → trả `"unknown"`
    (reconcile sẽ coi `sent` cũ là `delivered` sau `T`).
  - `resolveExternalIdentity(senderRef)` — gọi Zalo OA get-profile với token → `{ name?, phone? }` (Zalo
    thường **không** trả email) → `{ phone? }`; không có ⇒ `{}`.

- [ ] **Step 1: Spike (bắt buộc, ghi lại)** — xác minh scheme chữ ký + shape webhook + send API + get
  profile của **Zalo OA** từ tài liệu chính thức; ghi vào `channel-runbook.md` (Task 11) dạng
  `VerificationConfig` cụ thể. Nếu khác `hmac_sha256` đơn giản → mở rộng `verification.ts` cho đúng scheme.
- [ ] **Step 2: Test đỏ** — fixtures: (a) body + chữ ký hợp lệ → `verifyInbound` OK, field đúng;
  (b) body sửa 1 byte → `unauthenticated`; (c) timestamp lệch > `skewSeconds` → `unauthenticated`;
  (d) `sendOutbound` với mock fetch 200 → `sent` + `externalMessageId`; 401 → `failed` + `permanent:true`;
  429 → `failed` + `permanent:false`.
- [ ] **Step 3: Implement** contract change + `verification.ts` + adapter + `registry` entry
  `zalo: new ZaloChannelAdapter()`. Cập nhật `ApiChannelAdapter.sendOutbound(cmd, _secret)`.
- [ ] **Step 4: Chạy — xanh** + `npx tsc --noEmit` (P0 relay call site cần thêm arg secret — sẽ sửa Task 6;
  tạm truyền `null` để typecheck qua, hoặc làm Task 6 ngay sau).
- [ ] **Step 5: Commit** `feat(engagement): ChannelAdapter secret-aware sendOutbound + Zalo OA adapter (HMAC verify, error classification)`.

---

### Task 3: Connector grant client + channel secret seam

**Files:**
- Create: `services/company/commercial/services/customer-engagement/connector-grant.client.ts`
- Create: `services/company/commercial/services/customer-engagement/channel-secret.ts`
- Test: `.../tests/customer-engagement/connector-grant.client.test.ts`
- (Verify) `services/cosa/handlers/workspace-connector.handler.ts` — thêm test `assert` cho `action:"send"`.

**Interfaces (Produces):**
- `connector-grant.client.ts`: `assertConnectorGrant({ workspaceId; conversationId; connectorKey; action: "send" }): Promise<{ ok: boolean; secretRef: string | null }>` —
  gọi `POST ${COSA_CONTROL_PLANE_URL}/cosa/connectors/assert` với worker service token
  (`COSA_WORKER_SERVICE_TOKEN` env, giống `connector_grant_client.py`). Lỗi mạng ⇒ `{ ok:false, secretRef:null }`
  (fail-closed: relay coi là chưa gửi được, retry).
- `channel-secret.ts`: `resolveChannelSecret(secretRef: string): Promise<string>` — P2: map `secretRef` →
  Encore secret / env (`CHANNEL_SECRET_<REF>`); không có ⇒ throw `APIError.failedPrecondition("secret not resolvable: <ref>")`.
  **TODO(P4+):** thay bằng vault client thật. Không log giá trị.

- [ ] **Step 1: Test đỏ** — mock HTTP: `assert` trả `{ ok:true, secretRef:"sr_1" }` → client trả đúng;
  `{ ok:false }` → `{ ok:false, secretRef:null }`; network error → `{ ok:false }` (không throw).
  `resolveChannelSecret("sr_1")` với env set → trả token; không set → `failedPrecondition`.
- [ ] **Step 2: đỏ → implement → xanh.**
- [ ] **Step 3: Test `services/cosa`** — `assertConnectorEndpoint` với grant `action:"send"` active →
  `{ ok:true, secretRef }`; grant revoked/expired → `{ ok:false }`. (Nếu handler đã có test tương đương,
  chỉ bổ sung case `send`.)
- [ ] **Step 4: Commit** `feat(engagement): connector-grant client + channel secret resolution seam (fail-closed)`.

---

### Task 4: Inbound ingest service (verify → dedupe → thread → message → outbox, atomic)

**Files:**
- Create: `services/company/commercial/services/customer-engagement/channel-inbound.service.ts`
- Test: `.../tests/customer-engagement/channel-inbound.service.test.ts`

**Interfaces (Produces):**
- `ingestInbound(channelType: string, ctxReq: { rawBody: Buffer; headers: Record<string,string|undefined> }): Promise<{ status: 200 | 401 | 200_dropped; threadId?: string; messageId?: string; outcome: string }>`:
  1. Tìm endpoint theo `inbound_routing_key` lấy từ raw (adapter cần expose `peekRoutingKey(raw)` hoặc
     verify trả kèm) — chưa map ⇒ `outcome:"error"`, `200` (không muốn provider retry vô ích) + log.
  2. `endpoint.status !== "active"` ⇒ ghi `engagement_channel_inbound_events(outcome:"dropped_paused")`,
     `200`, **không** message.
  3. `config = resolveVerificationConfig(endpoint.verification_config_ref)`;
     `adapter.verifyInbound({ rawBody, headers })` → `VerifiedInbound`. Fail ⇒ ghi
     `inbound_events(outcome:"rejected_signature")`, trả `401`.
  4. **Dedupe**: `insert engagement_channel_inbound_events (endpoint_id, provider_delivery_id, raw_hash, outcome:"accepted")`
     `onConflictDoNothing`; nếu conflict (đã có) ⇒ `outcome:"duplicate"`, `200`, trả `messageId` cũ nếu
     có. (Layer 2: unique `external_message_id` bên dưới.)
  5. `db.transaction`:
     - Find thread `(inbox_id, external_conversation_ref)`; không có ⇒ `openThread` (P0) + set
       `external_conversation_ref`, `active_mode:"team_queue"`.
     - `resolveContact({ email, phone }, threadId, ctxSystem)` từ `adapter.resolveExternalIdentity` (rẻ,
       chỉ DB lookup) — link `contact_id` nếu chắc chắn; nhập nhằng ⇒ review item; `auto_create_contact`
       ⇒ tạo Contact tối thiểu (Task 7 `linkThreadIdentity` — gọi trong tx).
     - Insert `engagement_messages` (`direction:"inbound", visibility:"customer", senderKind:"customer",
       external_message_id, retention_until = created_at + 365d`) — unique `(workspace_id, external_message_id)`
       conflict ⇒ coi là duplicate, rollback nhẹ, `200`.
     - Nếu thread `resolved` ⇒ reopen về `open` (P0 logic).
     - `appendOutboxEvent(tx, buildMessageReceivedEvent(...))`.
     - Update `inbound_events` row: `thread_id`, `message_id`, `outcome:"accepted"`.
  6. Trả `200` + ids.
  - **Không** gọi model / copilot / HTTP ngoài. Toàn bộ < vài trăm ms.
- Actor cho các thao tác hệ thống: `{ kind: "system", id: "channel:zalo" }`.

- [ ] **Step 1: Test đỏ** (real DB, mock adapter):
  - Valid → 1 thread mới + 1 message + 1 outbox event + `inbound_events(outcome:"accepted")`.
  - Cùng `provider_delivery_id` lần 2 → `outcome:"duplicate"`, message count vẫn 1, **không** outbox event thứ 2.
  - Chữ ký sai → `401`, 0 message, `inbound_events(outcome:"rejected_signature")`.
  - Endpoint `paused` → `200`, 0 message, `outcome:"dropped_paused"`.
  - `external_message_id` trùng nhưng `provider_delivery_id` mới → không tạo message trùng.
  - Inbound trên thread `resolved` → reopen `open`.
- [ ] **Step 2: đỏ → implement → xanh.**
- [ ] **Step 3: Commit** `feat(engagement): atomic inbound ingest — verify + double dedupe + thread/message/outbox in one tx`.

---

### Task 5: Zalo webhook handler (`api.raw`) + channel admin endpoints

**Files:**
- Create: `services/company/commercial/handlers/customer-engagement/channels/zalo.handler.ts`
- Create: `services/company/commercial/handlers/customer-engagement/channel-admin.handler.ts`
- Modify: `services/company/commercial/handlers/customer-engagement/index.ts`
- Modify: `services/company/commercial/services/customer-engagement/rbac.ts` (`engagement.channel.manage`)
- Test: `.../tests/customer-engagement/channel-webhook.test.ts`

**Interfaces — endpoints:**
- `zalo.handler.ts`:
  - `GET /commercial/engagement/channels/zalo/webhook` — provider verify challenge (echo token) nếu Zalo
    yêu cầu; else bỏ.
  - `POST /commercial/engagement/channels/zalo/webhook` — **`api.raw`**: đọc raw body (stream →
    `Buffer`), gọi `ingestInbound("zalo", { rawBody, headers })`, set `resp.statusCode` theo kết quả,
    `resp.end()`. **Bắt mọi exception** → `500` chỉ khi lỗi hạ tầng; lỗi verify → `401`; còn lại → `200`.
- `channel-admin.handler.ts` (`expose:true`, `requireWorkspaceAccess` + `requireEngagementPermission(ctx, "engagement.channel.manage")`):
  - `POST /commercial/engagement/channels` — tạo `engagement_channel_endpoints` (`status:"pending"`,
    `channel_type`, `connector_key`, `inbound_routing_key`, `verification_config_ref`, `auto_create_contact`).
  - `POST /commercial/engagement/channels/:id/activate` — **fail-closed**: `resolveVerificationConfig` OK
    **và** `assertConnectorGrant({ action:"send" })` OK ⇒ `status:"active"`; else `failedPrecondition`.
  - `POST /commercial/engagement/channels/:id/pause` — `status:"paused"`.
  - `GET /commercial/engagement/channels/:id/deliveries?status=failed` — list `engagement_outbound_deliveries`
    + `last_error` + `dead_letter_reason` cho WorkforceMember; kèm `retry` action.
  - `POST /commercial/engagement/deliveries/:id/retry` — reset `failed` (chưa quá `max_attempts` hard cap
    riêng cho manual) về `queued`, `attempt_count` giữ, ghi audit.

- [ ] **Step 1: Test đỏ** — qua handler: raw POST chữ ký hợp lệ → `200` + message tồn tại; sai → `401`;
  replay → `200` không dup; `activate` khi thiếu verification config → `failedPrecondition`; `deliveries`
  list trả row `failed` với `last_error`.
- [ ] **Step 2: đỏ → implement (handler mỏng, logic ở service) → xanh + `npx tsc --noEmit`.**
- [ ] **Step 3: Commit** `feat(engagement): Zalo raw webhook + channel admin (activate fail-closed, DLQ visibility)`.

---

### Task 6: Outbound relay — real provider path

**Files:**
- Modify: `services/company/commercial/services/customer-engagement/delivery-relay.service.ts`
- Test: `.../tests/customer-engagement/delivery-relay-provider.test.ts`

**Interfaces (behavior):** trong `deliveryRelayTick`, cho mỗi claimed delivery:
1. Load message + thread (scoped). **Ownership re-check (P0)**: `message.delivery_state !== "queued"` hoặc
   `thread.active_mode === "human_assigned"` (với message do automation/agent) ⇒ drop
   (`status:"failed", dead_letter_reason:"ownership_changed"`), **không** gọi provider.
2. `adapter = getChannelAdapter(delivery.channel_type)`.
3. Nếu `channel_type === "api"` ⇒ như P0 (`sendOutbound(cmd, null)`).
4. Nếu provider thật:
   - `endpoint` theo thread inbox → `{ ok, secretRef } = assertConnectorGrant({ workspaceId, conversationId: threadId, connectorKey: endpoint.connector_key, action: "send" })`.
     `!ok` ⇒ **không** đánh `failed` vĩnh viễn: `status:"queued"` + backoff (grant có thể được cấp lại);
     sau `N` lần liên tiếp `!ok` ⇒ `dead_letter_reason:"connector_grant_unavailable"`.
   - `token = await resolveChannelSecret(secretRef)`.
   - `res = await adapter.sendOutbound({ deliveryId, threadId, body, externalConversationRef, endpointProviderRef }, token)`.
   - `res.status === "sent"` ⇒ `status:"sent"`, `external_message_id = res.externalMessageId`, message
     `delivery_state:"sent"`, `appendOutboxEvent(buildMessageSentEvent)` (nếu P0 chưa phát lúc enqueue —
     xác nhận: P0 phát lúc `sendPublicMessage`; ở đây **không** phát lại).
   - `res.status === "failed" && res.permanent` ⇒ `status:"failed"`, `dead_letter_reason = res.error`,
     WorkforceMember thấy.
   - `res.status === "failed" && !res.permanent` ⇒ `status:"queued"` + exponential backoff (cap 300s);
     `attempt_count >= max_attempts` ⇒ `failed` + `dead_letter_reason`.
5. `token` chỉ tồn tại trong scope hàm; **không** log, **không** ghi DB.

- [ ] **Step 1: Test đỏ** (real DB, mock adapter + mock `assertConnectorGrant`/`resolveChannelSecret`):
  - happy: `queued` → tick → `sent` + `external_message_id`; message `delivery_state:"sent"`.
  - `assertConnectorGrant` `!ok` → vẫn `queued` + backoff; sau `N` lần → `dead_letter_reason:"connector_grant_unavailable"`.
  - `sendOutbound` permanent 401 → `failed` ngay + `dead_letter_reason`.
  - transient 429 → `queued` + `visibility_timeout_at` tăng; đủ `max_attempts` → `failed`.
  - takeover trước tick (message `cancelled`) → drop, không gọi adapter/connector.
- [ ] **Step 2: đỏ → implement → xanh.**
- [ ] **Step 3: Commit** `feat(engagement): outbound relay real-provider path — connector grant + secret + error classification + DLQ`.

---

### Task 7: CRM identity sync (link / review / auto-create — no merge)

**Files:**
- Create: `services/company/commercial/services/customer-engagement/channel-identity-sync.service.ts`
- Test: `.../tests/customer-engagement/channel-identity-sync.service.test.ts`

**Interfaces (Produces):**
- `linkThreadIdentity(threadId: string, signals: { email?: string; emailVerified?: boolean; phone?: string; externalUserRef?: string; externalUserName?: string }, ctx, opts: { autoCreateContact: boolean }): Promise<{ contactId: string | null; accountId: string | null; reviewItemId: string | null; created: boolean }>`:
  1. `resolveContact({ email, phone, emailVerified }, threadId, ctx)` (P0):
     - trả `contactId` ⇒ link `engagement_threads.contact_id`; backfill `account_id` từ
       `sales.contacts.account_id` nếu có; `created:false`.
     - trả `reviewItemId` (nhập nhằng / do_not_contact / unverified / conflict) ⇒ giữ thread contact
       null, trả `reviewItemId`.
  2. Không match + `opts.autoCreateContact` ⇒ **tạo mới** `sales.contacts` (reuse `createContactService`
     hoặc insert trực tiếp scoped): `name = externalUserName ?? phone ?? externalUserRef`,
     `phone`, `email` (chỉ nếu verified), `source = \`engagement:${channelType}\``, `account_id = null`.
     Link thread. `created:true`. **Không** merge, **không** đụng Contact khác.
  3. Không match + `!autoCreateContact` ⇒ `engagement_identity_review_items(reason:"no_match")`,
     contact null.
- `writeInteractionSummary(threadId, { summary, evidenceRefs }, ctx)` — insert
  `engagement_customer_interactions` (P0) khi thread `resolved` / có outcome; `retention_until = +365d`.
  (Gọi từ P0 `changeThreadStatus`→resolved hook hoặc housekeeping; P2 thêm hook.)

- [ ] **Step 1: Test đỏ** — 4 nhánh: verified email exact match → link + backfill account; ambiguous →
  review item, thread contact null; no match + `autoCreateContact:true` → Contact mới `source=engagement:zalo`,
  link, **không** contact khác thay đổi; no match + false → review item `no_match`.
- [ ] **Step 2: đỏ → implement → xanh.**
- [ ] **Step 3: Commit** `feat(engagement): channel CRM identity sync — link/review/auto-create, never merge`.

---

### Task 8: Delivery status reconcile + housekeeping

**Files:**
- Modify: `services/company/commercial/services/customer-engagement/housekeeping.service.ts`
- Test: `.../tests/customer-engagement/delivery-reconcile.test.ts`

**Interfaces:** `runHousekeepingTick` thêm `reconcileDelivery` vào kết quả:
- Với `engagement_outbound_deliveries` `status='sent' AND delivered_at IS NULL AND created_at < now() - interval '10 min'`:
  `s = adapter.getDeliveryStatus(external_message_id)` → `"delivered"` ⇒ `status:"delivered", delivered_at=now()`;
  `"failed"` ⇒ `status:"failed", dead_letter_reason:"provider_reported_failure"`; `"unknown"` sau `T` (vd.
  24h) ⇒ coi `delivered` (best-effort, ghi `dead_letter_reason` NULL, note `last_error:"assumed_delivered"`).
- Batch nhỏ, bounded; lỗi provider ⇒ giữ nguyên, thử lại tick sau.

- [ ] **Step 1: Test đỏ** — `sent` cũ + mock `getDeliveryStatus` → `delivered`/`failed`/`unknown→assumed`.
- [ ] **Step 2: đỏ → implement → xanh.**
- [ ] **Step 3: Commit** `feat(engagement): outbound delivery status reconcile in housekeeping tick`.

---

### Task 9: Control-plane connector wiring + seed helper

**Files:**
- Verify: `services/cosa/handlers/workspace-connector.handler.ts` (`install`/`authorize`/`grant`/`assert`).
- Create: `services/company/commercial/services/customer-engagement/channel-onboarding.ts` — helper gọi
  `services/cosa` để install + authorize connector cho endpoint (một chỗ, để admin handler / script dùng).
- Test: `.../tests/customer-engagement/channel-onboarding.test.ts` + `services/cosa` assert `send`.

**Interfaces (Produces):**
- `onboardChannelConnector({ workspaceId; connectorKey; providerConfigRef }, ctx): Promise<void>` —
  gọi `/cosa/connectors/install` + `/cosa/connectors/authorize` (secret_ref do Control Plane sinh/nhận).
  Idempotent. Sau bước này endpoint `activate` (Task 5) mới pass.
- Ghi rõ ràng buộc thứ tự: `onboardChannelConnector` → `channel-admin POST /channels` → `activate`.

- [ ] **Step 1: Test đỏ** — mock `services/cosa` HTTP: `onboardChannelConnector` gọi đúng 2 endpoint;
  `activate` (Task 5) fail trước khi onboard, pass sau.
- [ ] **Step 2: đỏ → implement → xanh.**
- [ ] **Step 3: Commit** `feat(engagement): channel connector onboarding helper (install + authorize via control plane)`.

---

### Task 10: P2 test matrix + provider sandbox drill

**Files:**
- Create: `services/company/commercial/tests/customer-engagement/channel-matrix.test.ts`
- Create: `docs/operations/customer-engagement-channel-drill.md` (kịch bản chạy tay với sandbox provider)

**Cases (map spec §9 + rollout gate overview):**

| Scenario | Assert |
| --- | --- |
| Chữ ký hợp lệ | inbound → 1 message + 1 outbox event; ack < ngưỡng; enrichment nặng không chạy trong request |
| Chữ ký sai / thiếu / timestamp lệch | `401`, 0 message, `inbound_events(outcome:"rejected_signature")` |
| Replay cùng `provider_delivery_id` | 0 message trùng, 0 outbox event trùng, 0 CRM effect trùng |
| `external_message_id` trùng khác delivery id | 0 message trùng (layer-2 dedupe) |
| Endpoint `paused` | `200`, drop, `outcome:"dropped_paused"`, relay skip outbound của endpoint đó |
| `activate` thiếu verification config / connector grant | `failedPrecondition` (fail-closed) |
| Outbound happy | `queued`→`sent` + `external_message_id`; token **không** xuất hiện trong DB/log |
| Outbound permanent error (401) | `failed` ngay + `dead_letter_reason`; WorkforceMember thấy qua `GET .../deliveries` |
| Outbound transient (429) | `queued` + backoff; đủ `max_attempts` → `failed` |
| Connector grant revoked giữa chừng | outbound `queued`→ sau N lần `dead_letter_reason:"connector_grant_unavailable"` |
| Human takeover trước tick | outbound bị drop trước khi gọi provider (P0 §8.4) |
| Internal note | không có đường ra channel; không trong export customer-facing |
| Identity: verified email exact | thread link `contact_id` + `account_id` backfill |
| Identity: ambiguous | `engagement_identity_review_items`, thread contact null, **không** merge |
| Identity: no match + `auto_create_contact` | Contact mới `source=engagement:zalo`, **không** Contact khác đổi |
| Reconcile | `sent` cũ → `delivered`/`failed` theo `getDeliveryStatus` |

- [ ] **Step 1: Viết `channel-matrix.test.ts`** (real DB, mock adapter + mock control-plane + mock provider fetch).
- [ ] **Step 2: Chạy**
  - `cd services/company && npx vitest run commercial/tests/customer-engagement/` — P0+P1+P2 xanh.
  - `cd services/company && npx tsc --noEmit`.
  - `npm test` (services/company) — không hồi quy.
- [ ] **Step 3: Sandbox drill (ghi lại kết quả)** — theo `channel-drill.md`: đăng ký OA sandbox, gửi tin
  thật vào webhook staging, gửi outbound thật; xác nhận signature verify + dedupe (retry provider) +
  outbox atomic + DLQ visibility. Đây là **rollout gate** production của P2.
- [ ] **Step 4: Commit** `test(engagement): P2 channel matrix + sandbox drill script`.

---

### Task 11: Channel runbook + vocabulary addendum

**Files:**
- Create: `docs/operations/customer-engagement-channel-runbook.md`
- Modify: `docs/architecture/customer-engagement-vocabulary.md`

- [ ] **Step 1: Runbook** — onboard kênh mới (checklist: viết adapter file → webhook handler → `VerificationConfig`
  → `onboardChannelConnector` → tạo endpoint `pending` → `activate` fail-closed); format `VerificationConfig`;
  DLQ triage (`GET .../deliveries?status=failed`, retry an toàn, `dead_letter_reason` nghĩa là gì);
  ranh giới: adapter provider-specific, mọi thứ khác dùng chung.
- [ ] **Step 2: Vocabulary** — thêm: endpoint `status` (`active|pending|paused`), delivery `status`
  (`queued|sent|delivered|failed`) + `dead_letter_reason` values, `engagement_channel_inbound_events.outcome`
  values, "adapter mới không đụng schema/relay core".
- [ ] **Step 3: Commit** `docs(engagement): P2 channel runbook + vocabulary (endpoint/delivery/inbound states)`.

---

## Self-Review

**Spec coverage:**
- §9 Channel Adapter (`verifyInbound`/`normalizeInbound`/`sendOutbound`/`getDeliveryStatus`/`resolveExternalIdentity`)
  → Task 2 (Zalo) + contract mở rộng secret-aware; `api`/P0 vẫn hợp lệ.
- §9.1 xác thực chữ ký/mTLS trên raw request → Task 2 `verification.ts` (raw bytes, timing-safe, skew),
  Task 5 `api.raw`.
- §9.2 dedupe theo delivery/message id trong inbox riêng adapter → Task 1 `engagement_channel_inbound_events`
  + Task 4 double dedupe.
- §9.3 ghi command + outbox atomically → Task 4 (`db.transaction`).
- §9.4 ack nhanh; model/enrichment/retry async → Task 4 (không HTTP ngoài trong request), Task 8 (reconcile async).
- §9.5 không tin client data → Task 2/4 (verify trước parse).
- §9 outbound: outbox riêng + idempotency + retry/backoff + `queued|sent|delivered|failed` + dead-letter +
  visibility → Task 6 + Task 5 (`GET .../deliveries`) + Task 8.
- §9 "worker không giữ raw credential; Control Plane trả `secret_ref`" → Task 3 (`connector-grant.client`
  + `channel-secret` seam), Task 6 (token scope hàm, không persist/log).
- §5.2 identity resolution (email verified khoá chính, phone phụ, review item, **không** merge) → Task 7.
- §5.2.5 sales intent → **P3** (không làm ở P2, ghi rõ).
- §13 P2 (agent đề xuất routing/labels/Lead, human approve) → **P3** (deterministic) / P1 (copilot signal);
  P2 chỉ inbound/outbound + link CRM.

**Gaps có chủ đích:**
- Chỉ 1 kênh (Zalo OA). Web chat / email / WhatsApp / Facebook = lặp Task 2/5/6/9 + entry runbook; không
  đụng Task 1/4 core. Thứ tự tiếp theo do §17.1 chốt.
- `resolveChannelSecret` P2 dùng Encore secret / env; vault thật = TODO(P4+), đã đánh dấu trong code + runbook.
- Attachment/media inbound (ảnh, file Zalo) → lưu metadata + `content_ref` (P0 `engagement_message_attachments`),
  tải byte thật + backup region automation lùi sau P2.
- `email_verified` thật trên `sales.contacts` — vẫn heuristic P1 cho tới P2 identity nâng cấp (ghi ở Task 7).
- Rate limit outbound theo provider (Zalo quota) — thêm ở P3/P4 nếu drill cho thấy cần.

**Placeholder scan:** 1 spike bắt buộc (Task 2 Step 1 — scheme chữ ký Zalo thật) ghi rõ là bước có
deliverable (`VerificationConfig` cụ thể trong runbook), không phải "TBD". `resolveChannelSecret` TODO
vault có chủ đích + đánh dấu. Còn lại interface + test đầy đủ.

**Type consistency:** `ChannelAdapter.sendOutbound(cmd, secret)` đổi ở contract + `ApiChannelAdapter` +
relay call site (Task 2/6). `OutboundCommand.externalConversationRef` khớp Task 2 ↔ Task 6.
`engagement_channel_inbound_events.outcome` values (`accepted|duplicate|rejected_signature|dropped_paused|error`)
khớp Task 1 ↔ 4 ↔ 10 ↔ 11. `dead_letter_reason` values (`ownership_changed|connector_grant_unavailable|
provider_reported_failure|<provider error>`) khớp Task 6 ↔ 8 ↔ 10 ↔ 11. `assertConnectorGrant` /
`resolveChannelSecret` / `resolveVerificationConfig` / `linkThreadIdentity` tên nhất quán.

---

## Execution Handoff

Sau khi P2 landed + sandbox drill đạt rollout gate: viết `2026-08-28-customer-engagement-p3.md`
(deterministic rule evaluator trong `services/company/commercial` — routing / SLA action / labels /
follow-up task / snooze-reopen / escalate / tạo Decision Request; điều kiện trên structured facts,
**không** LLM; delayed rule re-check state).
