# ADR-ID-MODEL-001: Hybrid ID model — SpineId (Snowflake) / LeafId (UUIDv7) + managed generator registry

## Status
ACCEPTED 2026-08-29 (Lưu ý: ACCEPTED ≠ IMPLEMENTED ≠ WIRED ≠ VERIFIED ≠ PRODUCTION).
Spec cho **M2** của [master plan M0–M7](../plans/2026-08-29-cosa-workspace-canonical-master-plan.md).
Làm rõ và một phần supersede audit §4.5.

## Context

[Readiness audit 2026-08-29](../reports/2026-08-29-cosa-code-first-workspace-local-cloud-readiness-audit.md)
phát hiện:

- `services/company/shared/services/snowflake.service.ts` và `services/cosa/services/snowflake.service.ts`
  đều đặt `NODE_ID = Math.floor(Math.random() * 1024)` lúc process start — không registry, không lease,
  không fencing ⇒ hai process có thể trùng node id ⇒ ID collision.
- `services/company/identity/services/sync.service.ts` sinh Snowflake local mới rồi lưu
  `platformWorkspaceId` làm mapping — một workspace có **hai** identity xuyên hai plane (trái D-06).
- Agent Core knowledge/run/conversation/artifact/memory dùng `uuid.uuid4()` (v4 — không time-ordered).
- Snowflake bị serialize lẫn lộn number/string ⇒ mất precision trên JS/Dart (mantissa 53-bit < 63-bit).

Phiên brainstorming 2026-08-29 chốt **C-3, C-5, C-6**: managed generator registry ngay ở M2;
ID model hybrid; mọi SpineId chỉ tạo được khi online.

## Decision

### 1. Hai loại ID

**`SpineId` = Snowflake `BIGINT`.** Dùng cho entity ít cardinality, ít tần suất, mà việc tạo là một
hành động **provisioning có chủ đích**:

| Entity | Ghi chú |
|---|---|
| `workspace` | Giữ nguyên xuyên local/cloud |
| `project` | Tạo qua control-plane provisioning (M4) |
| `legal_entity_profile` | |
| `workforce_member` | |
| `sop_definition`, `sop_version` | first-class resource (M3) |
| lifecycle transition record | workspace + project stage transition |
| approval record | `legal_verification_approvals` (M1) và tương tự |

**`LeafId` = UUIDv7** (lưu cột `uuid`, chuỗi canonical trên wire). Dùng cho entity cardinality cao do
runtime sinh liên tục, có thể **offline**:

| Entity | Ghi chú |
|---|---|
| `knowledge_document`, `knowledge_chunk` | v4 → v7, giữ kiểu `str` |
| `run`, `conversation`, `artifact`, `memory_item` | giữ prefix `run_`/`conv_`/`art_` nếu code phụ thuộc; phần UUID đổi v4→v7 |
| `bank_transaction` | |
| ingestion object | `apps/cosa/knowledge_ingestion/` |

Cả hai **time-ordered** và serialize dạng **string**.

**KHÔNG dùng SpineId/LeafId cho:** capability/spec ID (namespace + semver + content hash),
idempotency key, external provider ID, object URI, encryption key ref.

### 2. Snowflake generator — chỉ authoritative, luôn online

- Chỉ `services/cosa` (Control Plane) chạy generator. Cloud Workspace Runtime chạy generator **khi
  Cloud Continuity**, dưới lease của cùng registry.
- Local `services/company` / AgentOS **không** chạy generator — xin `SpineId` qua RPC
  `mintSpineId(kind)` tới Control Plane. Local offline ⇒ `APIError.unavailable`.
- Bỏ `NODE_ID = Math.random() * 1024`. Slot do registry cấp + lease + heartbeat + **fencing token**.
  Process authoritative **không start** nếu thiếu/trùng slot (fatal), trừ `NODE_ENV=test`/`dev`
  dùng stub deterministic.

### 3. Bit layout (versioned — không đổi âm thầm)

```
| 41 bit  | 1 bit      | 10 bit | 12 bit    |
| ms      | reserved=0 | slot   | sequence  |
| COSA epoch (~69 năm)   | (1024) | (4096/ms) |
```

- COSA epoch: `2024-01-01T00:00:00Z` (chốt trong hằng số `COSA_SNOWFLAKE_EPOCH_MS = 1704067200000`).
- Fleet authoritative nhỏ + luôn online ⇒ 1024 slot dư. Vấn đề cũ là `random()`, không phải số lượng slot.
- Layout version = `1`. Đổi layout ⇒ bump version + ADR mới.

### 4. Registry: slot + lease + fencing + clock-regression policy

Bảng `snowflake_generator_slots` (Control Plane — chi tiết schema ở [M2 spec §2](../plans/2026-08-29-cosa-workspace-canonical/M2-workspace-canonical.md)):

- `acquire(generator_id, runtime_role)` → `{ slot, fencing_token, lease_epoch }`.
  `UNIQUE (slot) WHERE lease_expires_at > now()` là cơ chế chống trùng.
- Heartbeat renew lease; mất heartbeat quá TTL ⇒ slot được thu hồi, generator cũ phải re-acquire epoch mới.
- **Clock regression:** persist `clock_checkpoint` (max ts đã phát) xuống đĩa; `now < clock_checkpoint`
  ⇒ virtual-clock advance trong drift budget (mặc định 5s), **không phát ID lùi**; vượt budget ⇒ alert + refuse.
- **Sequence exhaustion** trong 1ms ⇒ spin sang ms kế, không wrap.
- **Restart fencing:** mọi durable write mang `fencing_token`; store từ chối write với token cũ (dùng lại ở M6).

### 5. C-6 — SpineId chỉ tạo được khi online

Tạo workspace / project / legal entity / workforce member / SOP definition = bước provisioning qua
Control Plane (authority mint ID duy nhất). Local **không bao giờ** sinh SpineId. Offline "tạo …" trả
`APIError.unavailable`, **KHÔNG** queue bằng ID tạm. Vì bỏ hoàn toàn đường sinh SpineId offline ⇒
**không cần** zone bit / per-workspace local slot.

Vận hành offline (chạy agent, sửa nội dung, sinh LeafId) **không đổi** — LeafId sinh cục bộ, không lease,
không gọi Control Plane.

### 6. Wire serialization

- Mọi Snowflake qua JSON = **decimal string** (không JS/Dart `Number`). Rà `services/*` trả Snowflake
  dạng number ⇒ ép `.toString()`.
- UUIDv7 qua JSON = chuỗi canonical `xxxxxxxx-xxxx-7xxx-yxxx-xxxxxxxxxxxx`.

## Làm rõ D-06 (không đảo ngược)

> "persistent domain **resource** (spine) dùng Snowflake `BIGINT`; **record** cardinality cao do runtime
> sinh dùng UUIDv7; cùng `workspace_id` giữ nguyên xuyên local/cloud."

**Supersede audit §4.5:**
- Bullet "node đã kích hoạt có thể sinh ID khi offline" — chỉ còn đúng cho **LeafId/UUIDv7**.
- Bullet "local-only tự mint workspace ID rồi platform adopt" — **bỏ**. Workspace ID luôn platform-minted.

## Consequences

- **+** Một workspace identity duy nhất xuyên plane; hết mapping-ID.
- **+** Collision-free generator; restart giữ slot identity.
- **+** Leaf entity time-ordered (index locality tốt hơn v4).
- **−** Tạo workspace/project bắt buộc online — offline UX phải báo `unavailable` rõ ràng (chấp nhận, C-6).
- **−** Thêm một RPC hop cho mọi provisioning từ `services/company`.

## Relates

- Master: [M0 §5](../plans/2026-08-29-cosa-workspace-canonical/M0-contract-freeze.md),
  [M2 §2–§4](../plans/2026-08-29-cosa-workspace-canonical/M2-workspace-canonical.md).
- Reuse lease pattern: `services/cosa/services/control-plane-lease.service.ts`.
- Fencing tái dùng ở [M6 — Cloud Continuity](../plans/2026-08-29-cosa-workspace-canonical/M6-cloud-continuity.md) §2.
- Bổ sung, không supersede: `ADR-LOCAL-FIRST-001` (data residency), `ADR-CONTROLPLANE-001` (vị trí control-plane).
