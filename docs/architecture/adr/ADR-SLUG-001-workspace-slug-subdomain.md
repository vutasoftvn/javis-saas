# ADR-SLUG-001: Workspace slug & subdomain contract

## Status
ACCEPTED 2026-08-29 (Lưu ý: ACCEPTED ≠ IMPLEMENTED ≠ WIRED ≠ VERIFIED ≠ PRODUCTION).
Spec cho **M2 §6** của [master plan M0–M7](../plans/2026-08-29-cosa-workspace-canonical-master-plan.md).

## Context

`services/cosa` hiện chỉ có `platform_workspaces.workspace_name` — text, **không unique**, không phải
DNS identity. Chương trình workspace-canonical cần: subdomain ổn định cho Remote Access / public page,
giữ chỗ atomically khi nhiều workspace đăng ký cùng lúc, và rename không phá vỡ link cũ.
[Readiness audit §4.6](../reports/2026-08-29-cosa-code-first-workspace-local-cloud-readiness-audit.md).

## Decision

### 1. `name` vs `slug`

| | `name` | `slug` |
|---|---|---|
| Vai trò | display | DNS label / routing identity |
| Charset | Unicode | `[a-z0-9-]`, bắt đầu/kết thúc bằng `[a-z0-9]` |
| Mutable | có | có (tạo redirect history) |
| Unique | không | **có, toàn cầu** khi workspace link platform |
| Bắt buộc | có | nullable khi `LOCAL_ONLY` chưa link platform |

`name` **không bao giờ** được dùng làm DNS identity. `workspace_id` **không đổi** khi slug đổi.

### 2. Bảng `workspace_slugs` (Control Plane — `services/cosa/storage/schema.ts`)

```
workspace_id      BIGINT   NOT NULL            -- SpineId
slug              TEXT     NOT NULL            -- normalized, lowercase
status            TEXT     NOT NULL            -- ACTIVE | REDIRECT | RELEASED
redirect_to_slug  TEXT     NULL               -- chỉ khi status = REDIRECT
reserved_at       TIMESTAMPTZ NOT NULL
released_at       TIMESTAMPTZ NULL
UNIQUE INDEX ON (slug)                         -- cơ chế giữ chỗ atomic
INDEX ON (workspace_id)
```

- Reservation = atomic `INSERT` dựa vào `UNIQUE(slug)`. Conflict ⇒ trả gợi ý slug khác, không ghi đè.
- Một workspace có đúng **một** row `ACTIVE` tại một thời điểm; các row `REDIRECT` là lịch sử rename
  trong retention window (mặc định 180 ngày) rồi chuyển `RELEASED`.
- `RELEASED` slug có thể được workspace khác nhận lại sau retention.

### 3. Normalization (thứ tự cố định)

1. Unicode NFKC.
2. `toLowerCase()`.
3. `trim()`.
4. Thay mọi run khoảng trắng bằng `-`.
5. Bỏ mọi ký tự ngoài `[a-z0-9-]`.
6. Collapse `-{2,}` → `-`.
7. Trim `-` ở hai đầu.
8. Reject nếu: rỗng sau normalize · trùng reserved list · độ dài < 3 hoặc > 63 · đã tồn tại row `ACTIVE`/`REDIRECT`.

Slug default derive từ `name` theo quy trình trên; user chỉnh được trước khi chốt.

### 4. Reserved list

```
admin, api, app, apps, www, mail, smtp, imap, pop, ftp, ns1, ns2, dns,
support, help, status, docs, blog, about, legal, privacy, terms, security,
static, assets, cdn, img, images, media, files, download, downloads,
auth, login, logout, signup, register, account, accounts, billing, pay, payment, payments,
dashboard, console, portal, internal, system, root, superuser, test, staging, dev, demo,
cosa, platform, control, controlplane, workspace, workspaces, runtime, vault, gateway, relay
```

(Chốt danh sách này; thêm mục mới qua PR sửa ADR + hằng số dùng chung.)

### 5. Rename

- Tạo row `REDIRECT` cho slug cũ trỏ `redirect_to_slug = <slug mới>`; slug mới thành `ACTIVE`.
- `workspace_id` giữ nguyên. Redirect phục vụ trong retention window; hết window ⇒ `RELEASED`.
- Không cho rename sang slug đang `ACTIVE`/`REDIRECT` của workspace khác.

### 6. `custom_domain` + LadiPage connector

- Là **integration record** tham chiếu `workspace_id` + active slug. KHÔNG phải tenant identity.
- Public custom-domain / LadiPage implementation **ngoài phạm vi** cho tới khi slug/ownership contract
  hoàn tất (master plan "Ngoài phạm vi").

## Consequences

- **+** Subdomain ổn định, giữ chỗ atomic, rename an toàn.
- **+** `workspace_id` bất biến — link nội bộ / audit không vỡ khi đổi slug.
- **−** Thêm một bảng + reservation flow trong đăng ký (M2).

## Relates

- [M0 §6](../plans/2026-08-29-cosa-workspace-canonical/M0-contract-freeze.md),
  [M2 §6](../plans/2026-08-29-cosa-workspace-canonical/M2-workspace-canonical.md).
- [ADR-ID-MODEL-001](./ADR-ID-MODEL-001-spine-snowflake-leaf-uuidv7.md) — `workspace_id` là SpineId.
