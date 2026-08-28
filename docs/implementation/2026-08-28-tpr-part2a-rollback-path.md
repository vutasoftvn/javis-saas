# Part 2A — Rollback path + Migration Gate E

**Master:** [`2026-08-28-test-prod-readiness.md`](./2026-08-28-test-prod-readiness.md)
**Phụ thuộc:** Milestone 1 xong (nhánh đã merge, staging chạy)
**Ước lượng:** 1–2 ngày
**Nhánh:** `tpr/part2a-rollback-path`

## Mục tiêu

Trước cutover prod, phải có **đường lùi rõ ràng**: hoặc rollback về trạng thái an toàn được, hoặc quyết định chính thức chấp nhận cutover không đảo ngược kèm compensating control. Đồng thời đóng **Migration Gate E** (`.down.sql` chạy được).

## Trạng thái hiện tại (verify bằng code)

- `docs/operations/rollback_pre_cutover.md` đánh dấu "CRITICAL KNOWN RISK": legacy `brain-api` gãy — `ModuleNotFoundError: No module named 'full_main'` sau restructure 2026-08-22. Nếu COSA API lỗi sớm ở prod và cần lùi về legacy → legacy không chạy.
- `COSA_FINAL_INTEGRATION` plan Phase 10 = xoá legacy. Legacy chỉ còn vai trò "rollback contingency".
- `docs/operations/migrations.md`: Gate E (`.down.sql` test) = chưa verify. Có `.down.sql` cho các migration? → cần kiểm (`ls services/*/migrations/*.down.sql packages/agent_core/migrations/*down*`).
- Đã có `docs/operations/disaster-recovery.md`, `docs/operations/rollback_pre_cutover.md`.

## Thay đổi cụ thể

### 2A.1 Quyết định rollback strategy (ADR)

Viết `docs/architecture/adr/ADR-CUTOVER-001-rollback-strategy.md`. Hai phương án — **khuyến nghị (B)**:

- **(A) Sửa legacy `brain-api`** để rollback được: fix import `full_main`, chạy `docker compose up brain-api` xanh, `/ready` 200. Ước lượng 2–4h. Nhược: kéo dài vòng đời legacy, mâu thuẫn Phase 10.
- **(B) Chấp nhận cutover không đảo ngược về legacy**, thay bằng compensating control:
  - Blue-green trên **chính COSA**: giữ version N-1 (image tag cũ) sẵn sàng; rollback = đổi tag + redeploy (api + worker), migration backward-compatible (xem 2A.2).
  - Staging soak ≥ 48h với golden-path xanh trước khi promote.
  - DB backup đầy đủ + PITR (Part 2E) làm lưới an toàn cuối.
  - Feature-flag/kill-switch cho dispatch (worker ngừng claim task mới) để "đóng băng" hệ thống khi sự cố.

ADR chốt (B), liệt kê điều kiện tiên quyết, cập nhật `rollback_pre_cutover.md` trỏ ADR này.

### 2A.2 Migration backward-compatibility rule

- Quy ước: mỗi release chỉ chứa migration **expand** (thêm cột nullable/bảng/index), **không** `DROP`/`NOT NULL`/rename trong cùng release với code dùng nó. `DROP` đi ở release sau (expand → migrate code → contract).
- Ghi vào `docs/operations/migrations.md` mục "Backward-compatible migration policy".
- Thêm check trong `schema-fingerprint`/CI hoặc review checklist: phát hiện `DROP COLUMN`/`DROP TABLE`/`ALTER ... SET NOT NULL` trong migration mới → cảnh báo.

### 2A.3 Migration Gate E — `.down.sql`

- Kiểm mọi migration có `.down.sql` tương ứng. Thiếu → viết (ít nhất cho N=10 migration gần nhất mỗi hệ).
- `scripts/test-migration-rollback.mjs`: trên Postgres disposable → `migrate-all` (up) → apply `.down.sql` N bước cuối → re-apply up → so `schema-fingerprint` khớp golden.
- CI job `migration-rollback` (chỉ chạy PR vào `main` + `workflow_dispatch`, không mỗi push).

### 2A.4 Runbook cutover

`docs/runbooks/prod-cutover.md`: các bước có thứ tự (backup → migrate → deploy version N → smoke golden-path → theo dõi 30' → promote / rollback), tiêu chí abort, lệnh rollback cụ thể (đổi image tag, restart), ai bấm nút.

## Reuse

- `docs/operations/rollback_pre_cutover.md`, `disaster-recovery.md`.
- `scripts/schema-fingerprint.mjs` (Part 1F) cho verify round-trip.
- `make deploy` / `deploy-preflight` / `deploy-app` (đã hỗ trợ đổi tag + restart).
- Golden-path smoke (Part 1D) làm tiêu chí pass/abort.

## Test / verify

- CI job `migration-rollback` xanh: up → down N → up → fingerprint khớp.
- Trên staging: thực thi runbook cutover 1 lần đầy đủ (bao gồm bước rollback giả định: đổi về image N-1, golden-path vẫn xanh).
- ADR review + approve.

## Definition of Done

- [ ] `ADR-CUTOVER-001` chốt strategy (khuyến nghị B) + điều kiện tiên quyết.
- [ ] Backward-compatible migration policy ghi vào `migrations.md` + check trong CI/review.
- [ ] Mọi migration (≥ N=10 gần nhất) có `.down.sql`; job `migration-rollback` xanh (Gate E = VERIFIED).
- [ ] `docs/runbooks/prod-cutover.md` hoàn chỉnh, đã diễn tập 1 lần trên staging.

## Rủi ro

- Nếu chọn (B), một migration contract lỡ lọt vào cùng release code → rollback gãy. Mitigation: policy + CI check + review gate.
- `.down.sql` ít khi được test kỹ → có thể sai; job round-trip fingerprint là bảo hiểm.
