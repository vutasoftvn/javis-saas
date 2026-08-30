# COSA — Master plan: Workspace-canonical, Runtime Fabric, Vault, AI Workforce

**Nguồn sự thật audit:** [`../reports/2026-08-29-cosa-code-first-workspace-local-cloud-readiness-audit.md`](../reports/2026-08-29-cosa-code-first-workspace-local-cloud-readiness-audit.md)
**Ngày:** 2026-08-29 · **Commit rà soát:** `d6fe04e1`
**Trạng thái:** Khung chương trình đã chốt hướng — mỗi milestone có spec chi tiết riêng trong [`2026-08-29-cosa-workspace-canonical/`](./2026-08-29-cosa-workspace-canonical/)

---

## Context

Audit code-first ngày 2026-08-29 kết luận: COSA đúng hướng "AI work environment" ở mức kiến
trúc thành phần, nhưng **chưa thành sản phẩm end-to-end** vì tồn tại nhiều nguồn sự thật song
song và hợp đồng giữa các lớp lệch nhau. Đối chiếu code trong phiên brainstorming 2026-08-29
(ba luồng rà soát độc lập + verify Flutter trực tiếp) xác nhận: **gần như toàn bộ phát hiện
của audit chính xác tới file:line**, gồm nhiều lỗ hổng cross-tenant khai thác được ngay
(CAS webhook fail-open + reprocess endpoint public, legal approval chỉ check prefix chuỗi,
cross-workspace mutation ở accounting/reconciliation/workforce, token đi sai trust boundary).

**Mục tiêu chương trình:** đưa `Workspace` thành aggregate root và tenant duy nhất; xóa
`Company` khỏi ownership/tenancy/auth/policy; dựng Workspace Runtime Fabric ba chế độ
(`LOCAL_ONLY` → `REMOTE_ACCESS` → `CLOUD_CONTINUITY`); Workspace Vault độc lập cho từng
workspace; Snowflake generator được quản trị; workforce UI phản ánh AgentSpec/capability thật.

**Kết quả kỳ vọng:** pass test matrix §10 của audit ở phạm vi release công bố; local-first
chạy độc lập; không còn public unauthenticated internal mutation; một local host vận hành
nhiều Workspace Vault không leak dữ liệu.

## Quan hệ với tài liệu trước

- [`./2026-08-29-cosa-workspace-canonical/M0-contract-freeze.md`](./2026-08-29-cosa-workspace-canonical/M0-contract-freeze.md)
  đã chốt hướng workspace-first nhưng phạm vi hẹp (tenancy + project link). Audit 2026-08-29
  mở rộng lớn: Runtime Fabric, Vault vật lý, Snowflake registry, slug contract, execution
  lease, Cloud Continuity, workforce model. Master plan này bao trùm và thay thế phạm vi
  triển khai của spec 2026-08-27.
- Quyết định kiến trúc D-01…D-09 (§0 audit) và target model §4–§7 đã được Founder duyệt qua
  review 2026-08-29 — **không mở lại**, chỉ triển khai.

## Quyết định đã chốt (phiên brainstorming 2026-08-29)

| # | Quyết định | Hệ quả |
|---|---|---|
| C-1 | Plan phủ **toàn bộ §9.0–§9.7** dạng master plan chia milestone M0–M7 | Gồm cả Remote Access + Cloud Continuity |
| C-2 | **Pre-launch, ~0 dữ liệu prod thật** | M2 cut thẳng model ID canonical + reset fixture; KHÔNG cần batched FK-rewrite migration, `workspace_id_map`, shadow read comparison, reconciliation report cho dữ liệu thật. Vẫn giữ guard code chống hai-ID về sau |
| C-3 | **Managed generator registry ngay** (M2) — control-plane là authority duy nhất | Registry cấp slot + lease + fencing + clock-regression policy cho generator ở `services/cosa` (+ cloud workspace runtime khi Cloud Continuity). Process authoritative không start nếu thiếu/trùng slot. Local `services/company` / AgentOS **không** chạy Snowflake generator |
| C-4 | **Theo đúng thứ tự audit**: §9.0 contract freeze + contract tests TRƯỚC, rồi §9.1 P0 | M0 là gate cứng chặn M1; không tách P0 ship song song |
| C-5 | **ID model hybrid** (thay cho "mọi thứ Snowflake") | `SpineId` = Snowflake `BIGINT` — workspace, project, legal entity, workforce member, SOP definition, lifecycle/approval record. `LeafId` = UUIDv7 — knowledge doc/chunk, run, conversation, artifact, memory item, bank transaction, ingestion object (cardinality cao, runtime sinh, hay offline). Cả hai time-ordered; serialize dạng string. Làm rõ D-06, không đảo ngược |
| C-6 | **Mọi SpineId chỉ tạo được khi online** | Tạo workspace, project, legal entity, workforce member, SOP definition = bước provisioning qua control-plane `services/cosa` (authority mint ID duy nhất). Local **không bao giờ** sinh SpineId; offline "tạo …" báo `unavailable`, KHÔNG queue bằng ID tạm. Vận hành offline (chạy agent, sửa nội dung, sinh LeafId) vẫn bình thường. **Bỏ hoàn toàn đường sinh SpineId offline** ⇒ không cần zone bit / per-workspace local slot. Supersede audit §4.5 bullet "node đã kích hoạt có thể sinh ID khi offline" (chỉ còn đúng cho LeafId/UUIDv7) và bullet "local-only tự mint workspace ID rồi platform adopt" |

## Guardrails (mọi milestone — audit §12)

1. Không tạo thêm Company alias, `brain_id`, `workspace_uid` hay parallel tenancy source.
2. Không đổi máy móc mọi từ "company"; giữ thuật ngữ hợp lệ cho customer/counterparty trong CRM,
   chỉ xóa Company **aggregate** khỏi core.
3. Không biến central control plane thành shared business execution DB/runtime.
4. Row-prefix `workspace_id` ≠ physical isolation; Vault phải gồm file, key, cache, backup, sync state.
5. C-suite title không phải authorization/approval principal cho AI.
6. Không random node ID cho production Snowflake.
7. Không cloud-failover khi user chỉ bật Remote Access.
8. Không sync raw credentials; không generic last-write-wins cho dữ liệu critical (finance/legal/approval/lifecycle/policy).
9. Mỗi milestone có migration gate, contract tests, rollback checkpoint. Shadow comparison chỉ khi có dữ liệu thật (C-2).
10. Không tuyên bố "test hoàn thiện" chỉ dựa vào component tests đang xanh — readiness gate bám §10.
11. Tuân thủ CLAUDE.md: `APIError` không throw `Error` trần; internal endpoint `expose:false`;
    schema Drizzle tập trung ở `<app>/shared/db/schema/`; đổi schema phải có migration +
    `node scripts/migrate.mjs`; comment giải thích bằng tiếng Việt.

## Bản đồ milestone

| M | Tên | Audit § | Spec chi tiết | Phụ thuộc |
|---|---|---|---|---|
| M0 | Contract freeze | §9.0 | [M0-contract-freeze.md](./2026-08-29-cosa-workspace-canonical/M0-contract-freeze.md) | — (gate cứng) |
| M1 | P0 security & trust-boundary closure | §9.1 | [M1-p0-security.md](./2026-08-29-cosa-workspace-canonical/M1-p0-security.md) | M0 |
| M2 | Workspace canonical + Snowflake registry + slug | §9.2 | [M2-workspace-canonical.md](./2026-08-29-cosa-workspace-canonical/M2-workspace-canonical.md) | M0, M1 |
| M3 | Workspace Vault multi-workspace local | §9.3 | [M3-workspace-vault.md](./2026-08-29-cosa-workspace-canonical/M3-workspace-vault.md) | M2 |
| M4 | Workspace & Project lifecycle độc lập | §9.4 | [M4-lifecycle.md](./2026-08-29-cosa-workspace-canonical/M4-lifecycle.md) | M2 |
| M5 | Remote Access | §9.5 | [M5-remote-access.md](./2026-08-29-cosa-workspace-canonical/M5-remote-access.md) | M2, M4 |
| M6 | Cloud Continuity | §9.6 | [M6-cloud-continuity.md](./2026-08-29-cosa-workspace-canonical/M6-cloud-continuity.md) | M3, M5 |
| M7 | AI workforce & UI integration | §9.7 | [M7-workforce-ui.md](./2026-08-29-cosa-workspace-canonical/M7-workforce-ui.md) | M2, M4 |

Thứ tự thực thi: **M0 → M1 → M2 → {M3, M4 song song} → M5 → {M6, M7}**.
M7 có thể bắt đầu ngay sau M4; M6 cần cả M3 (Vault/key) lẫn M5 (relay/node registry).

## Test matrix tổng (audit §10)

| §10.x | Nhóm test | Milestone |
|---|---|---|
| 10.1 | Snowflake & slug | M0, M2 |
| 10.2 | Domain & Company migration (rút gọn theo C-2) | M2 |
| 10.3 | Multi-workspace Vault isolation | M3 |
| 10.4 | Auth & trust boundary | M1 |
| 10.5 | Remote Access & Cloud Continuity | M5, M6 |
| 10.6 | Security cross-tenant | M1 |
| 10.7 | Lifecycle & legal | M4 |
| 10.8 | AI workforce | M7 |
| 10.9 | API/UI contract | M7 |
| 10.10 | Recovery / performance / operability + runbook | Xuyên suốt |

## Verification baseline (mỗi milestone không được làm hồi quy)

- `services/cosa`: typecheck + 91/91 tests.
- `services/company`: typecheck + 415/415 tests.
- AgentOS/COSA Python targeted: 29/29.
- Flutter targeted widgets: 7/7; `flutter analyze --no-pub`: ≤ 7 lint infos.
- Sau schema change: `node scripts/migrate.mjs` (hoặc `make services-migrate-company` / `make services-migrate-cosa`).

## Definition of Ready / Done (audit §13)

**Ready để bắt đầu integrated test hoàn thiện:** M1 đóng; canonical enum/Snowflake/route
contract publish (M0); multi-workspace isolation harness ≥ 2 workspace; UI không còn
route/fallback che lỗi ở luồng đang test.

**Done cho Workspace foundation:** Workspace là tenant key duy nhất trong
auth/policy/license/entitlement/AgentOS; cùng Snowflake workspace ID xuyên local/cloud; một
local host vận hành nhiều Vault không leak; Workspace & Project lifecycle độc lập
concurrency-safe audit được; Workspace W0 tồn tại không cần legal entity; local-only chạy độc
lập, Remote Access không đổi data residency, Cloud Continuity failover có fencing + encrypted
sync; workforce UI phản ánh AgentSpec/capability thật; test matrix §10 pass ở phạm vi release.

## Ngoài phạm vi (audit §12)

Outcome-based pricing / "AI company tự trị" tầm nhìn 2030; full runtime stack mặc định mỗi
workspace (phương án C §6.1 — chỉ optional enterprise mode); generic cross-workspace blob
deduplication; tự động cấp quyền pháp lý cho AI C-suite; public custom-domain/LadiPage
implementation trước khi slug/ownership contract hoàn tất.
