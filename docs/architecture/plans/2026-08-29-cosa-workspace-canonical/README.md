# COSA Workspace-canonical — milestone specs

Chi tiết cho từng milestone của [master plan](../2026-08-29-cosa-workspace-canonical-master-plan.md).
Nguồn audit: [`../../reports/2026-08-29-cosa-code-first-workspace-local-cloud-readiness-audit.md`](../../reports/2026-08-29-cosa-code-first-workspace-local-cloud-readiness-audit.md).

| M | Spec | Audit § | Trạng thái |
|---|---|---|---|
| M0 | [M0-contract-freeze.md](./M0-contract-freeze.md) | §9.0 | ✅ DONE 2026-08-29 — vocabulary + ADR-ID-MODEL-001 + ADR-SLUG-001 + enum canonical (3 runtime) + route/company inventory + CI `contract-freeze` |
| M1 | [M1-p0-security.md](./M1-p0-security.md) | §9.1 | ✅ DONE — §1 (token trust-boundary split + AgentOS chấp nhận local session token + delegation shape), §2, §3, §4 (mọi mutation handler có auth hoặc `expose:false`; coa-mappings/regulation-versions/CAS-reprocess → internal; mark-workspace-synced verify token+membership), §5, §6, §7. Follow-up không-P0: quét disclosure GET, E2E `encore run` |
| M2 | [M2-workspace-canonical.md](./M2-workspace-canonical.md) | §9.2 | Đang làm — ✅ canonical Workspace columns, slug contract (§6), Agent Core UUIDv7 (§3), venture workspace dùng platform-minted ID (§4), Snowflake generator registry cosa (§2), company snowflake bỏ random node ID + bit layout v1 (§2). ⏳ company snowflake → RPC `mintSpineId` + boot wiring (§2), drop company tables + license rekey + auth cutover (§1/§5), folder rename (§7) |
| M3 | [M3-workspace-vault.md](./M3-workspace-vault.md) | §9.3 | Đang làm — ✅ `WorkspaceObjectStore` + `LocalFilesystemWorkspaceStore` (§2/§3/§6.9: path-security, cross-workspace isolation, checksum, no dedup; 26 neg tests); ✅ knowledge `get_document` bind workspace (§4 phần); ✅ per-workspace DEK + rotation + destroy (§6 key: `WorkspaceKeyManager`, AES-256-GCM, workspace_id AAD, rotation journal; 9 tests); ✅ Runtime Host Catalog + Vault manifest (§1: `HostCatalog`, dir tree + `manifest.json` key_ref-only, per-workspace runtime/sync mode; 10 tests); ✅ `brain_id` removal khỏi `frontend/lib/` (§7). ⏳ S3 store (§2), RLS policy + pool reset (§4), SOP lifecycle (§5), storage quota + key wiring (§6 phần còn), workspace switcher (§8), backup/export (§9) |
| M4 | [M4-lifecycle.md](./M4-lifecycle.md) | §9.4 | Chưa bắt đầu |
| M5 | [M5-remote-access.md](./M5-remote-access.md) | §9.5 | Chưa bắt đầu |
| M6 | [M6-cloud-continuity.md](./M6-cloud-continuity.md) | §9.6 | Chưa bắt đầu |
| M7 | [M7-workforce-ui.md](./M7-workforce-ui.md) | §9.7 | Chưa bắt đầu |

Thứ tự thực thi: **M0 → M1 → M2 → {M3, M4} → M5 → {M6, M7}**.

Mỗi milestone khi bắt đầu cần một implementation plan chi tiết (`superpowers:writing-plans`)
dựa trên spec tương ứng — spec ở đây định nghĩa phạm vi, deliverable, test plan, exit gate;
không thay thế bước lập plan thực thi.

## Quyết định đã chốt (brainstorming 2026-08-29)

- **C-1** phủ toàn bộ §9.0–§9.7 · **C-2** pre-launch ~0 dữ liệu thật (M2 cut thẳng, không
  batched migration) · **C-3** managed generator registry ở M2, control-plane là authority
  duy nhất · **C-4** theo đúng thứ tự audit (M0 trước M1) · **C-5** ID model hybrid: SpineId =
  Snowflake, LeafId = UUIDv7 · **C-6** mọi SpineId (workspace, project, legal entity, member,
  SOP) chỉ tạo được khi online qua control-plane; không sinh SpineId offline.

Chi tiết ID model: [M0 §5 / ADR-ID-MODEL-001](./M0-contract-freeze.md).
