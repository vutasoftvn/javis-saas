# Legacy → Canonical Schema Reconciliation (Evidence)

**Vai trò của tài liệu này:** Chỉ ghi nhận bằng chứng (table/column/constraint/data còn thiếu, trùng lặp, hoặc đã lỗi thời) để phục vụ Epic `DB-FINAL-CUTOVER`. **`DB_FINAL_CUTOVER.md` là authority kiến trúc duy nhất — tài liệu này không mở lại, không thay thế, không tranh luận với quyết định đã khóa trong đó.** Không sửa migration path, không chạy baseline reset, không đổi deployment, không đụng `legacy/` deletion, `deploy-app`, root `docker-compose.yml`, production migration runner, hay VPS.

## Taxonomy

| Nhãn | Ý nghĩa |
|---|---|
| **PROMOTED** | Legacy có, canonical owner đã có tương đương xác nhận bằng migration/schema file thật. |
| **NEW_CANONICAL** | Functionality được kiến trúc mới chủ động thêm, **không cần** có "tổ tiên" trong legacy mới được tồn tại — không ép vào PROMOTE/RETIRE. |
| **MISSING** | Legacy có, canonical owner tương ứng chưa có — cần xác nhận còn requirement thật hay không trước khi promote. |
| **RETIRE** | Legacy có nhưng không còn consumer nào cần (đã tự dropped trong lịch sử, hoặc xác nhận dead feature). |
| **MIGRATE_DATA** | Cấu trúc đã PROMOTED nhưng dữ liệu lịch sử (nếu cần giữ) chưa có đường di chuyển. |
| **UNKNOWN** | Không đủ bằng chứng tĩnh để phân loại — luôn kèm lý do cụ thể + bước xác minh tiếp theo. **Không bao giờ dùng "quá nhiều migration" làm lý do.** |

---

## 1. COSA Control Plane

Nguồn legacy: `legacy/backend/alembic_control_plane/versions/c9a1f0b2e3d4_unify_central_control_plane_schema.py`. Nguồn canonical: `services/cosa/migrations/1-9_*.sql`.

### Legacy-mapped (có tổ tiên trong Alembic control-plane)

| Legacy (`cosa` schema, Alembic) | Canonical (`services/cosa`) | Classification | Ghi chú |
|---|---|---|---|
| `platform_users` (1 bảng, `full_name`/`avatar_url` inline) | `cosa.users` + `cosa.profiles` (tách) | PROMOTED (cấu trúc khác) | Tách bảng, không phải đổi tên — join 1 bảng ở legacy cần thành join 2 bảng ở canonical. |
| `company_memberships.platform_role` (string tự do, default `'member'`) | `cosa.company_memberships.role_id` (FK → `cosa.roles`, default `'user'`) | PROMOTED (cấu trúc khác) | Canonical có bảng `roles` chuẩn hóa; legacy chỉ có string tự do — giá trị default khác nhau, không có trong tập role canonical. |
| `companies`, `licenses`, `plans`, `company_entitlements` | `cosa.companies`, `cosa.licenses`, `cosa.plans`, `cosa.company_entitlements` | PROMOTED | Cấu trúc giống hệt. |
| `plans` seed data: `free`, `starter`, `pro`, `enterprise` | `cosa.plans` seed data: chỉ `starter` | MIGRATE_DATA | Fresh-bootstrap canonical thiếu 3/4 tier. Cần xác nhận còn cần `free`/`pro`/`enterprise` không trước khi thêm seed. |
| `projects_registry`, `project_stage_history`, `project_outcomes`, `project_metrics`, `programs`, `cohorts`, `program_participants`, `project_program_links`, `company_web_apps`, `domains`, `form_submissions`, `deployments`, `user_sessions` | *(không có trong `services/cosa/migrations/1-9`)* | UNKNOWN | Lý do: 13 bảng project-tracking/programs/marketing/session không xuất hiện ở bất kỳ migration `services/cosa` nào đã đọc. Bước xác minh: người có bối cảnh nghiệp vụ xác nhận các domain này hiện chạy qua `services/company/{operations,strategy}` hay thực sự chưa có nơi thay thế — trước khi gán PROMOTED/MISSING/RETIRE. |

### New canonical (Wave 7, `control_plane` schema — không có tổ tiên legacy, KHÔNG ép PROMOTE/RETIRE)

Theo ADR-CONTROLPLANE-001 (`docs/architecture/adr/ADR-CONTROLPLANE-001-...md`, trạng thái ACCEPTED nhưng "triển khai chưa bắt đầu, chờ review trước khi code Wave 7"), 12 bảng sau thay thế `packages/agent_core/runs/leases.py` (`RunLeaseManager`) và `packages/agent_core/coordination/scheduler.py` (`RunScheduler`) — 2 class Python in-memory không durable. Đây là functionality mới của kiến trúc, không cần chứng minh tồn tại trong legacy:

| Bảng (`control_plane` schema) | Origin | Decision authority | Migration owner | Legacy deletion dependency | Runtime verification |
|---|---|---|---|---|---|
| `control_plane.missions` | NEW_CANONICAL | ADR-CONTROLPLANE-001 | `services/cosa` | NONE | NOT YET VERIFIED |
| `control_plane.tasks` | NEW_CANONICAL | ADR-CONTROLPLANE-001 | `services/cosa` | NONE | NOT YET VERIFIED |
| `control_plane.assignments` | NEW_CANONICAL | ADR-CONTROLPLANE-001 | `services/cosa` | NONE | NOT YET VERIFIED |
| `control_plane.workers` | NEW_CANONICAL | ADR-CONTROLPLANE-001 | `services/cosa` | NONE | NOT YET VERIFIED |
| `control_plane.runtime_leases` | NEW_CANONICAL | ADR-CONTROLPLANE-001 | `services/cosa` | NONE | NOT YET VERIFIED |
| `control_plane.scheduled_tasks` | NEW_CANONICAL | ADR-CONTROLPLANE-001 | `services/cosa` | NONE | NOT YET VERIFIED |
| `control_plane.watches` | NEW_CANONICAL | ADR-CONTROLPLANE-001 | `services/cosa` | NONE | NOT YET VERIFIED |
| `control_plane.trigger_policies` | NEW_CANONICAL | ADR-CONTROLPLANE-001 | `services/cosa` | NONE | NOT YET VERIFIED |
| `control_plane.signal_observations` | NEW_CANONICAL | ADR-CONTROLPLANE-001 | `services/cosa` | NONE | NOT YET VERIFIED |
| `control_plane.delivery_policies` | NEW_CANONICAL | ADR-CONTROLPLANE-001 | `services/cosa` | NONE | NOT YET VERIFIED |
| `control_plane.delivery_attempts` | NEW_CANONICAL | ADR-CONTROLPLANE-001 | `services/cosa` | NONE | NOT YET VERIFIED |
| `control_plane.cost_ledger` | NEW_CANONICAL | ADR-CONTROLPLANE-001 | `services/cosa` | NONE | NOT YET VERIFIED |

"NOT YET VERIFIED" xác nhận bằng chính comment trong migration file (`6_control_plane_missions_tasks.up.sql:1-3`): *"KHÔNG có consumer production hiện tại — hạ tầng đón đầu theo yêu cầu người dùng, chưa verify được bằng Encore CLI/Postgres thật trong môi trường này."*

---

## 2. Agent Platform (governance / memory / knowledge) — PROMOTED, không re-audit

Theo chỉ đạo: Agent Platform chỉ coi là PROMOTED nếu fresh-bootstrap và cross-process test tiếp tục pass — không có bằng chứng mâu thuẫn mới xuất hiện trong phiên này, nên **không re-audit lại**. Bằng chứng đã có sẵn từ Phase 1 (`docs/superpowers/plans/2026-08-24-phase1-canonical-baseline.md`, commit `41b2d51`→`19adcf7`): 10 migration file (`packages/agent_core/migrations/001-010`), Python migration runner có checksum enforcement, git tag `pre-db-final-cutover`.

---

## 3. Company Business Schema — reconciliation bằng công cụ tự động, không đọc tay

### Phương pháp

Đã viết 2 script Python tạm thời (không commit, evidence-generation only) và chạy trên toàn bộ nguồn:

1. **Legacy extractor** (`legacy/backend/alembic/versions/*.py`, 84 file): parse bằng `ast` module (không phải đọc tay), chỉ quét thân hàm `upgrade()`, dựng revision-chain topological order từ `revision`/`down_revision` (kể cả `AnnAssign` — bug đã fix trong lúc viết: script gốc bỏ sót revision khai báo kiểu `revision: str = "..."`, chỉ bắt được 9/84 file trước khi fix). Kết quả: **273 bảng** business thật (không lẫn test-fixture noise như `mytable`/`table_b` từng thấy khi grep `__tablename__` thô ở lần trước — noise đó nằm trong file test, không nằm trong migration thật).
2. **Canonical extractor** (`services/company/{identity,operations,commercial,finance-legal}/migrations/*.up.sql`, 39 file, 1229 dòng + `services/company/shared/db/schema/*.ts`, 774 dòng): parse bằng regex có paren-depth-aware column splitting, theo thứ tự file numeric (`1_`, `2_`, ... mỗi domain). Kết quả: 57 bảng SQL, trong đó 50 "alive" (khớp chính xác với 50 bảng Drizzle — cross-check tự xác nhận tool đúng).
3. So khớp tên bảng (exact rồi fuzzy substring) giữa 273 bảng legacy và toàn bộ canonical alive set (`services/company` 50 + `packages/agent_core` 25 + `services/cosa` 20) → phân loại.

Output đầy đủ: [`docs/architecture/generated/COMPANY_SCHEMA_INVENTORY.json`](generated/COMPANY_SCHEMA_INVENTORY.json) (273 bảng legacy, mỗi bảng có: schema origin, `created_by`/`dropped_by` migration file, toàn bộ column/constraint/mutation timeline, classification, reason, next_step).

**Cross-check tự xác nhận tool đáng tin:** tool phát hiện độc lập đúng bug đã biết từ trước (`docs/architecture/DB_FINAL_CUTOVER_LEGACY_MANIFEST.md`) — `core.users` → renamed → `core.user_projections` (migration `identity/5_identity_projection_rework.up.sql`), khớp 100% với ghi nhận cũ.

### Kết quả phân loại (273 bảng legacy business)

| Classification | Số lượng | Ghi chú |
|---|---|---|
| **PROMOTED** | 36 | 33 → `services/company` (exact tên bảng khớp 1 trong 50 bảng alive), 2 → `services/cosa` (`companies`, `licenses` — trùng tên với control-plane), 1 → `packages/agent_core`. |
| **RETIRE** | 6 | Bảng được legacy tự tạo rồi tự xóa trong chính lịch sử migration của nó (self-retired) — không phải ứng viên promote. |
| **UNKNOWN** | 231 | 38 có candidate tên gần giống (fuzzy match) cần người xác nhận có phải cùng khái niệm không; 193 không khớp tên nào ở cả 3 canonical owner đã quét. |
| **MISSING** | 0 | Không có bảng nào được tool tự tin gán MISSING — mọi trường hợp không khớp exact đều xuống UNKNOWN vì cần xác nhận người trước khi kết luận "còn cần". |
| **MIGRATE_DATA** | 0 | Không phát hiện case tĩnh nào — xem seed-data gap ở mục COSA (`plans`) là ví dụ MIGRATE_DATA thật đã phát hiện được ở phần control-plane. |

### 231 UNKNOWN — nhóm theo chủ đề (không phải 231 mục rời rạc)

| Nhóm chủ đề | Số bảng | Ví dụ |
|---|---|---|
| Khác (không rơi vào nhóm nào bên dưới) | 88 | `agents`, `ai_runs`, `approval_requests`, `artifacts`, `audit_logs`, `outcomes`... |
| `agent_*` | 19 | `agent_aliases`, `agent_budgets`, `agent_definitions`, `agent_events`, `agent_hierarchies`... |
| `validation_*` | 13 | `validation_assumptions`, `validation_experiments`, `validation_hypotheses`... |
| `project_*` | 12 | `project_funding_awards`, `project_compliance_obligations`, `project_stage_history`... |
| `policy_*` | 10 | `policy_programs`, `policy_applications`, `policy_eligibility_rules`... |
| `marketing_*` | 8 | `marketing_campaigns`, `marketing_metrics`, `marketing_experiments`... |
| `platform_*` | 8 | `platform_agent_runs`, `platform_inbox`, `platform_prompt_templates`... |
| `strategy_*` | 5 | `strategy_analyses`, `strategy_canvases`, `strategy_foundations`... |
| `workflow_*` | 5 | `workflow_definitions`, `workflow_runs`, `workflow_approvals`... |
| `memory_*` | 5 | `memory_candidates`, `memory_promotions`, `memory_sync_records`... |
| Còn lại (portfolio/stage/founder/skill/knowledge/cycle/runtime/...) | ~58 | Xem đầy đủ trong JSON. |

Mỗi bảng trong danh sách trên **đã có** `reason` + `next_step` cụ thể trong JSON (không phải "quá nhiều để đọc"), ví dụ điển hình:

```json
"public.agent_definitions": {
  "classification": "UNKNOWN",
  "reason": "No exact or fuzzy name match in services/company, services/cosa, or packages/agent_core canonical schemas scanned by this tool.",
  "next_step": "Domain owner review required: confirm whether functionality was intentionally dropped (-> RETIRE), moved under an unrelated name (-> PROMOTED), or is a genuine gap (-> MISSING). If still unresolved, use DB-runtime verification gate to introspect a real bootstrapped DB before deciding."
}
```

### 38 UNKNOWN có fuzzy-candidate — đã rà tay, phân theo độ tin cậy

Đã đọc thủ công toàn bộ 38 mục (dùng dữ liệu JSON đã trích xuất, không cần thêm DB). Phát hiện **bug trong chính bộ so khớp fuzzy**: 3 candidate (`form_submissions`, `unified_permissions`, `agent_tool_permissions` → `missions`) là **false positive thuần túy chuỗi con** — `"mission"` nằm trong `"sub-MISSION-s"` và `"per-MISSION-s"`, không liên quan gì tới khái niệm `missions`. Đã loại 3 mục này khỏi danh sách candidate thật (vẫn giữ UNKNOWN, nhưng reason sửa thành "fuzzy match là string-matching artifact, không phải candidate thật").

| Độ tin cậy | Số lượng | Ví dụ | Ghi chú |
|---|---|---|---|
| **Đáng chú ý nhất — trùng khái niệm rõ** | 1 | `public.cost_ledger_entries` ↔ `control_plane.cost_ledger` (NEW_CANONICAL) | Legacy đã có cost ledger cho LLM usage; canonical Wave 7 độc lập xây lại `cost_ledger` mới (NEW_CANONICAL, chưa runtime-verify). Đáng để người có bối cảnh xác nhận: đây là promote thật hay canonical đang xây lại từ đầu song song. |
| **Có khả năng cùng khái niệm, cần xác nhận cột** | ~14 | `chat_messages`↔`messages`, `chatbot_conversations`↔`conversations`, `workspace_members`↔`workspace_memberships`, `pending_approvals`/`email_approvals`/`workflow_approvals`/`agent_approvals`↔`approvals`, `customer_interviews`/`validation_interview_sessions`↔`interviews`, `validation_assumptions`↔`assumptions`, `validation_experiments`↔`experiments`, `attachments`↔`message_attachments` | Tên khác nhưng domain hợp lý trùng — 4 loại "approvals" khác nhau khả năng đã hợp nhất thành 1 bảng `agent_core.approvals` (khớp triết lý "một danh tính duy nhất" trong CLAUDE.md) nhưng đây là suy luận, chưa xác nhận bằng cột. |
| **Khả năng false positive — domain khác nhau dù tên gần giống** | ~15 | `marketing_experiments`↔`experiments` (marketing ≠ strategy), `founder_profiles`↔`profiles` (business founder profile ≠ `cosa.profiles` platform identity), `methodology_plans`↔`plans` (methodology stage plan ≠ `cosa.plans` pricing tier), `workspace_secrets`↔`workspaces`, `agent_plans`/`agent_plan_steps`↔`plans` (agent execution plan ≠ pricing plan) | Trùng từ nhưng khái niệm nghiệp vụ khác — không nên gộp chỉ vì tên gần giống. |
| **7 bảng "*_runs" fuzzy vào `runs`** | 7 | `outcome_runs`, `run_steps`, `workflow_runs`, `ai_runs`, `agent_runs`, `platform_agent_runs`, `model_runs_audit` | Có khả năng nhiều bảng trong số này đã hợp nhất về `agent_core.runs` (durable run substrate) đúng tinh thần "một run substrate duy nhất", nhưng khẳng định 7:1 mapping mà không so cột là quá vội — để UNKNOWN, next_step: so cột từng bảng khi có DB-runtime gate đầy đủ (mục 5 hiện bị chặn giữa chừng bởi 2 BLOCKER, chưa tới được toàn bộ `agent_core` context để so). |
| **False positive do bug matcher (đã sửa reason)** | 3 | `form_submissions`, `unified_permissions`, `agent_tool_permissions` (đều fuzzy nhầm vào `missions`) | Chuỗi con trùng ngẫu nhiên, không phải candidate thật. |

**Kết luận mục này:** không có mục nào trong 38 được tự tin nâng cấp thành PROMOTED — vẫn giữ nguyên UNKNOWN, nhưng đã thu hẹp về đúng 1 mục thật sự đáng ưu tiên hỏi người (`cost_ledger_entries`) thay vì để phẳng 38 mục ngang hàng nhau.

**Bối cảnh liên quan (trích dẫn, không phải kết luận của tài liệu này):** `DB_FINAL_CUTOVER.md` §1.2 đã ghi rõ *"Không phục hồi monolithic database hàng trăm bảng từ legacy"* — nghĩa là một phần lớn trong 231 UNKNOWN có khả năng là RETIRE-by-design theo chủ đích kiến trúc mới, nhưng tài liệu này **không tự gán RETIRE** cho từng bảng cụ thể vì đó là quyết định cần xác nhận per-table (RETIRE đòi hỏi xác nhận "không còn consumer", không suy diễn từ 1 câu định hướng chung).

---

## 4. BLOCKER — Fresh-bootstrap `services/cosa` không chạy được tuần tự trên DB rỗng

**Bằng chứng chính xác:**

- `services/cosa/migrations/1_create_control_plane.up.sql:61-69` — tạo thẳng bảng `cosa.company_memberships`.
- `services/cosa/migrations/5_rename_company_roles.up.sql:1` — `ALTER TABLE cosa.company_roles RENAME TO company_memberships;`, giả định tồn tại bảng `cosa.company_roles`.
- **Hệ quả:** chạy tuần tự `1 → 5` trên DB rỗng → lỗi `relation "cosa.company_roles" does not exist"`. Chain lịch sử không còn coherent: migration 1 đã viết lại theo target state mới, migration 5 vẫn mô tả transition từ state cũ.
- Đã ghi nhận trước đó ở `docs/architecture/DB_FINAL_CUTOVER_LEGACY_MANIFEST.md` (Phase 1 Gate A, 2026-08-24), commit `19adcf7`.

**Không sửa migration 5 trong phạm vi tài liệu này.** Theo đúng chỉ đạo: vá lẻ từng migration (`IF EXISTS` trên 5, rồi 4, rồi 7...) sẽ biến lịch sử migration thành một tập compatibility hack khó hiểu. Việc sửa đúng thuộc về **canonical baseline reset một lần** đã quy định tại `DB_FINAL_CUTOVER.md` §5.3 — thay chain lịch sử không coherent bằng snapshot schema đích (`BASELINE V1`), sau đó mọi migration về sau immutable + additive. Baseline reset **chưa thực hiện** trong tài liệu này vì còn phụ thuộc trạng thái production data/VPS chưa xác minh được (ngoài phạm vi công việc hiện tại — không SSH, không đụng VPS).

---

## 5. DB-runtime verification gate — ĐÃ CHẠY (một phần), container throwaway cục bộ

Đã chạy gate này bằng container Postgres **throwaway, tách biệt hoàn toàn** khỏi `cosa_postgres` (container dev đang chạy sẵn, không đụng vào) — `docker run` tạm trên port `55432`, 3 database rỗng (`company_test`, `cosa_test`, `agent_core_test`), bootstrap bằng đúng migration runner canonical (`node scripts/migrate.mjs`, `python -m packages.agent_core.scripts.migrate`), rồi `docker rm -f` xóa sạch ngay sau khi introspect xong. Không đụng VPS, không đụng root `docker-compose.yml`, không đụng migration path production.

### Kết quả

| Canonical owner | Bootstrap trên DB rỗng | Bằng chứng |
|---|---|---|
| `packages/agent_core` | **PASS** — cả 10 migration (001-010) áp thành công | Xác nhận sống lại đúng claim Phase 1 ("PROMOTED, đã xong") — không có bằng chứng mâu thuẫn mới, giữ nguyên không re-audit sâu hơn. |
| `services/cosa` | **FAIL đúng như BLOCKER đã ghi ở mục 4** | `Error: failed to apply cosa/5_rename_company_roles.up.sql: relation "cosa.company_roles" does not exist` — dừng ở migration 5/9, 4 bảng đầu (`cosa.companies/company_agent_policy/company_entitlements/company_memberships/licenses/plans/profiles/roles/users`) được tạo. |
| `services/company` | **FAIL — một BLOCKER thứ hai, cùng dạng, mới phát hiện qua chạy thật** | Xem mục 4b bên dưới. |

### 4b. BLOCKER thứ hai (mới phát hiện qua DB-runtime gate) — `services/company` identity chain cũng không coherent

Cùng loại lỗi với migration 5 của `cosa` (mục 4), nhưng ở `services/company/identity`:

- `identity/1_create_workspace_user.up.sql:13` — tạo thẳng `core.user_projections` (không phải `core.users`).
- `identity/1_create_workspace_user.up.sql:25` — tạo thẳng `core.workspace_memberships` (không phải `core.workspace_members`).
- `identity/4_snowflake_ids.up.sql:4,7` — vẫn tham chiếu `core.users`, `core.workspace_members` (tên cũ) → **lỗi thật khi chạy**: `relation "core.users" does not exist`.
- `identity/5_identity_projection_rework.up.sql:6,14` — vẫn còn `ALTER TABLE core.users RENAME TO user_projections` và `ALTER TABLE core.workspace_members RENAME TO workspace_memberships` — sẽ **cũng fail** với lý do tương tự nếu migration 4 không chặn trước (không chạy tới được vì dừng ở 4).

Cùng một nguyên nhân gốc như mục 4: migration 1 đã bị viết lại theo target state mới, các migration sau (4 và 5) vẫn mô tả transition từ state cũ chưa từng tồn tại trên một DB bootstrap từ đầu. Đã ghi nhận một phần trong `DB_FINAL_CUTOVER_LEGACY_MANIFEST.md` (chỉ nêu migration 4, chưa nêu migration 5 cũng cùng lỗi) — nay xác nhận đầy đủ hơn bằng chạy thật.

**Không sửa trong phạm vi tài liệu này** — cùng lý do như mục 4: thuộc về canonical baseline reset (`DB_FINAL_CUTOVER.md` §5.3), không vá lẻ từng migration.

### Column-level fidelity spot-check (3 bảng, không so hết 36 vì tốn thời gian không cần thiết cho tài liệu evidence)

| Bảng | Kết quả |
|---|---|
| Legacy `public.run_events` (12 cột, `id`/`run_id` BigInteger, `payload_jsonb`, `sequence` Integer nullable, `event_key` varchar) vs canonical `agent_core.run_events` | **Khác cấu trúc thật, không phải 1:1** — canonical dùng `event_id`/`run_id` là `varchar(64)` (string identity, không phải BigInteger), `sequence_no` bigint not-null với sequence generator, `payload` (không phải `payload_jsonb`), thêm `correlation_id`. Khớp với công việc "harden exact invocation identity" đã làm ở agent_core (commit `c56d5fb`) — đây là redesign có chủ đích, không phải bug, nhưng khẳng định: PROMOTED ở mức khái niệm, KHÔNG đồng nghĩa cấu trúc cột giống nhau. |
| `cosa.plans` seed data (live) | Xác nhận đúng: chỉ có 1 row `starter` — khớp 100% với MIGRATE_DATA gap đã ghi ở mục 1. |
| `core.workspaces` (live) | Khớp với Drizzle declaration đã parse tĩnh (`identity.ts`) — không phát hiện lệch. |

### Gate còn lại chưa chạy (do 2 BLOCKER chặn giữa chừng)
- Không introspect được toàn bộ `services/company` (dừng ở identity/4, chưa tới `operations`/`strategy` domain — dù các domain đó tự nó không phụ thuộc bảng bị lỗi, migrate.mjs dừng ngay khi 1 file lỗi, không chạy tiếp domain khác).
- Không introspect được toàn bộ `services/cosa` (dừng ở migration 5/9, chưa tới `control_plane.*` NEW_CANONICAL — 12 bảng NEW_CANONICAL vẫn còn "NOT YET VERIFIED", **chưa verified được** vì gate bị chặn trước khi tới migration 6-9).
- Chưa so cột sâu cho 33/36 bảng PROMOTED còn lại.
- Muốn chạy tiếp cần: hoặc sửa 2 BLOCKER bằng baseline reset thật (ngoài phạm vi), hoặc bootstrap từng domain/schema riêng lẻ bỏ qua các file lỗi (không làm ở đây vì sẽ tạo state DB không đại diện cho thực tế production).

---

## Tổng kết cuối — chỉ liệt kê, không mở quyết định kiến trúc mới

### Confirmed blockers
- **`services/cosa` fresh-bootstrap không chạy được tuần tự trên DB rỗng** (mục 4, **xác nhận thật qua chạy migration trên Postgres throwaway**, mục 5) — migration 5 giả định bảng đã bị migration 1 loại bỏ. Fix đúng: canonical baseline reset (`DB_FINAL_CUTOVER.md` §5.3), chưa thực hiện, phụ thuộc trạng thái production/VPS chưa xác minh.
- **`services/company` fresh-bootstrap CŨNG không chạy được** (mục 4b, mới phát hiện qua chạy thật, không có trong ghi nhận cũ) — cùng lỗi dạng: `identity/1` đã tạo thẳng `core.user_projections`/`core.workspace_memberships`, nhưng `identity/4` và `identity/5` vẫn giả định tên cũ `core.users`/`core.workspace_members` tồn tại. Cùng venue fix: baseline reset §5.3, không vá lẻ.

### Confirmed gaps
- **Seed data thiếu** ở `cosa.plans`: canonical chỉ seed `starter`, legacy Alembic seed cả `free`/`starter`/`pro`/`enterprise` (mục 1, MIGRATE_DATA).
- **13 bảng COSA control-plane cũ** (`projects_registry`, `programs`, `cohorts`, `company_web_apps`, `domains`, `user_sessions`, ...) không có tương đương xác nhận trong `services/cosa/migrations/1-9` (mục 1, UNKNOWN).
- **12 bảng `control_plane.*` NEW_CANONICAL chưa được runtime-verify** — tự nhận trong chính comment migration là "KHÔNG có consumer production hiện tại" (mục 1).
- **231/273 bảng Company business legacy chưa xác nhận số phận** (mục 3) — mỗi bảng đã có reason + next_step cụ thể trong JSON, không phải một khối "chưa biết" chung chung.

### Unresolved items cần bằng chứng DB thật (không giải quyết được bằng static analysis)
- 38 bảng UNKNOWN có fuzzy-candidate — đã rà tay, thu hẹp còn **1 mục ưu tiên cao** (`cost_ledger_entries` ↔ NEW_CANONICAL `control_plane.cost_ledger`) + ~14 mục "có khả năng" + ~15 mục nhiều khả năng false positive domain khác nhau + 3 false positive do bug matcher (đã sửa) + 7 bảng "*_runs" nghi hợp nhất về `agent_core.runs` chưa xác nhận cột. Chi tiết đầy đủ ở mục 3.
- Column-level fidelity của 33/36 bảng PROMOTED còn lại (đã spot-check 3/36 qua DB-runtime gate — 1 trong 3 cho thấy redesign có chủ đích, không phải lỗi, nhưng xác nhận không nên coi PROMOTED = cấu trúc cột giống hệt).
- 12 bảng NEW_CANONICAL "NOT YET VERIFIED" **vẫn chưa verified được** — DB-runtime gate đã chạy nhưng bị chặn bởi BLOCKER migration 5 trước khi tới được migration 6-9 (nơi định nghĩa 12 bảng `control_plane.*`).
- Phần `services/company` domain `operations`/`strategy` chưa introspect được (migrate.mjs dừng ngay khi `identity/4` lỗi, không chạy tiếp domain khác).

### Không có quyết định kiến trúc mới nào được đưa ra trong tài liệu này.
