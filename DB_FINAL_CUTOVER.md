# COSA / Javis SaaS — Final Structure, Database & Legacy Cutover

**Status:** SUPERSEDED (2026-08-25) — xem `COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md` (mục 29 "Reconciliation Addendum" ghi rõ lý do và 5 quyết định P0.1 đã chốt thay thế nội dung §3 của tài liệu này). Nội dung dưới đây giữ nguyên làm lịch sử/tham khảo evidence (Exit Matrix, Definition of Done gốc) — không xoá.

**Status gốc (lịch sử):** FINAL EXECUTION CONTRACT — không mở thêm vòng cleanup nền tảng  
**Audit base:** `main@77851c2e0ddd1a04568716fc0a8fc1b04da88f4d`  
**Date:** 2026-08-24  
**Epic duy nhất:** `DB-FINAL-CUTOVER`  
**Phạm vi:** `services/company`, `services/cosa`, `packages/agent_core`, `apps/cosa`, deployment, migrations, toàn bộ `legacy/`

---

## 0. Mục tiêu cuối cùng

Tài liệu này là **quyết định cấu trúc cuối** cho database, persistence và legacy. Nó thay thế các plan cleanup/promotion/salvage rời rạc trước đây.

Sau khi Epic này đóng:

1. `main` **không còn thư mục `legacy/`**.
2. Không production path, import, Docker mount, `PYTHONPATH`, migration hay schema canonical nào phụ thuộc legacy.
3. Chỉ còn ba storage ownership rõ ràng: **COSA Control Plane DB**, **Company DB**, **Agent Platform Storage**.
4. Không còn migration lịch sử mutable.
5. Không còn subsystem production được gọi durable/live nếu default vẫn là in-memory.
6. Không còn nhiều migration/deployment path cạnh tranh nhau.
7. Không tiếp tục tái thiết kế database nền tảng sau cutover, trừ khi có requirement production mới + ADR.

> **Nguyên tắc:** Không giữ legacy “để tham khảo”. Git đã là lịch sử. Thứ cần giữ phải được promote; thứ không cần phải retire/delete.

---

# 1. Kiến trúc đích — khóa cứng

## 1.1 COSA Control Plane DB

COSA là nguồn sự thật duy nhất cho:

- platform users / profiles;
- companies;
- company memberships;
- credential/authentication;
- platform/company roles;
- plans, licenses, entitlements;
- central policy thực sự cần ở platform level.

Canonical membership table:

```text
cosa.company_memberships
```

Không quay lại `company_roles` với semantics membership.

## 1.2 Company DB

Company DB chỉ giữ **business truth của một company/workspace**.

Canonical schemas cuối:

```text
core
operating
strategy
sales
commercial
finance
legal
```

Không phục hồi monolithic database hàng trăm bảng từ legacy.

Quy tắc:

- `workspace_id` là tenant key canonical;
- business actor dùng `*_member_id` → `core.workforce_members.id`;
- Company không là credential authority;
- Company không tự tạo company identity độc lập với COSA;
- services không query trực tiếp COSA DB.

## 1.3 Agent Platform Storage

Agent state không nằm trong Company business schemas.

Canonical ownership cuối:

### `agent_core`

- `runs`
- `run_checkpoints`
- `run_events`
- `run_tool_calls`
- `approvals`
- workflow definitions
- durable conversation/messages

### Governance

Governance temporal persistence phải thuộc canonical owner. Không được để canonical Python code đọc bảng được tạo bởi SQL nằm trong `legacy/`.

Kết quả cuối hợp lệ là một trong hai:

- fold governance state/history vào `agent_core.*`; hoặc
- giữ `agent_core_governance.*` như schema canonical riêng.

Dù chọn hình thức nào, migration phải ở `packages/agent_core/migrations/` hoặc canonical migration package tương đương.

### Memory

```text
agent_memory.agent_memories
```

### Knowledge

```text
knowledge.knowledge_sources
knowledge.knowledge_chunks
```

PgVector là canonical vector storage nếu semantic retrieval được bật.

---

# 2. Quyết định dứt điểm về `legacy/`

## 2.1 Trạng thái đích

**Sau Epic: repository không còn `legacy/` trên `main`.**

Không đổi tên thành `_archive`, `_old`, `deprecated`, `legacy2` hoặc giữ một archive code tree khác.

Lịch sử được giữ bằng:

1. Git tag trước cutover, ví dụ `pre-db-final-cutover`;
2. commit SHA trong tài liệu inventory;
3. requirement notes / ADR cho behavior đã retire;
4. migration mapping report cho dữ liệu cần chuyển.

## 2.2 Chỉ có ba trạng thái cho mọi asset legacy

| Trạng thái | Ý nghĩa | Kết quả |
|---|---|---|
| `PROMOTE` | Behavior/schema vẫn cần | chuyển sang canonical owner + test, sau đó xóa bản legacy |
| `RETIRE` | Không còn requirement/runtime consumer | capture lý do/requirement cần thiết, sau đó xóa |
| `MIGRATE-DATA-THEN-DELETE` | Cần dữ liệu lịch sử nhưng không cần code cũ | migrate/verify dữ liệu rồi xóa code + schema cũ |

**Không có trạng thái `KEEP FOR NOW`.**

---

# 3. Legacy Exit Matrix — quyết định cuối theo cây code

## 3.1 `legacy/backend/` → DELETE

### Hiện trạng cần xử lý trước khi xóa

- root/control-plane deployment vẫn còn đường tham chiếu Dockerfile/migration legacy;
- realtime agent còn mount `./legacy/backend:/app/backend` và `PYTHONPATH` fallback ở deployment path cũ;
- root Dockerfile/Alembic path cũ còn có khả năng tồn tại và từng nuốt migration error bằng `|| true`.

### Promote

Không promote backend framework cũ.

Chỉ chuyển những thứ sau nếu canonical owner chưa có:

- migration/data mapping thật sự cần cho COSA/Company baseline;
- secret/env requirement cần thiết;
- smoke test contract của realtime integration.

### Cutover

1. COSA/Company dùng migration canonical mới.
2. Realtime agent chỉ gọi service qua HTTP/canonical client.
3. Xóa legacy volume mounts.
4. Xóa legacy `PYTHONPATH`/`.env` fallback.
5. Xóa root Dockerfile/deploy path trỏ backend cũ.
6. Smoke LiveKit/realtime pass.
7. **Delete `legacy/backend/`.**

---

## 3.2 `legacy/agent_runtime_archive/agentos/` → PROMOTE chọn lọc, rồi DELETE

### Bắt buộc promote

- governance SQL/schema đang còn được canonical code sử dụng;
- memory persistence schema;
- knowledge/pgvector persistence schema;
- data migration logic/shape cần thiết để chuyển historical governance state.

### Không promote nguyên khối

- runtime/kernel cũ đã có canonical kernel mới;
- duplicate workflow/runtime abstractions đã superseded;
- provider/executor code chỉ giữ nếu behavior test chứng minh canonical thiếu.

### Điều kiện xóa

- canonical migration tạo governance/memory/knowledge từ empty DB;
- real Postgres migration adapter pass;
- production composition dùng canonical stores;
- grep canonical code không còn string/path `agent_runtime_archive` hoặc `agentos/migrations`.

Sau đó **delete toàn bộ `legacy/agent_runtime_archive/`**.

---

## 3.3 `legacy/agent_runtime/agent_runtime/` → RETIRE/PROMOTE behavior, rồi DELETE

Không port folder-to-folder.

Inventory behavior cuối phải đối chiếu các nhóm:

- executor/tool loop;
- planner/provider routing;
- approval-aware dispatch;
- retry/idempotency behavior;
- audit/trace;
- redaction/sensitive-data filtering;
- tenant-policy adapter;
- stuck-loop detection;
- session/checkpoint behavior.

Mỗi behavior phải được đánh dấu:

```text
PROMOTED_TO=<canonical module + test>
hoặc
RETIRED_REASON=<requirement note/ADR>
```

Không còn dòng `UNKNOWN` trước delete.

Sau khi matrix 100% đóng: **delete**.

---

## 3.4 `legacy/agent_runtime/cosa_core/` + workforce → PROMOTE semantics cần thiết, rồi DELETE

Các semantics đã được xác định cần xem xét salvage:

- budget tracking/gating;
- cost/usage accounting;
- stuck-loop detection;
- approval-aware dispatch;
- extension/plugin manifest governance metadata;
- hierarchy/authority behavior chưa được biểu diễn bởi `workforce_members.manager_member_id`.

Quyết định cuối:

- hierarchy đơn giản dùng canonical workforce hierarchy, **không resurrect `agent_hierarchies` nếu không cần**;
- budget/cost phải persistent ở Agent Platform;
- approval đi qua canonical approvals/gateway;
- extension metadata đi vào canonical plugin/capability model nếu còn requirement.

Sau characterization/regression: **delete `cosa_core` và workforce legacy**.

---

## 3.5 `legacy/business/`, `legacy/domains/`, `legacy/entrypoints/` → RETIRE, trừ behavior được chứng minh thiếu

Business CRUD/schema canonical đã nằm ở `services/company`.

Không port các bảng chỉ vì chúng từng tồn tại.

Trước khi delete:

1. inventory runtime consumers = 0;
2. map domain → canonical replacement hoặc RETIRED;
3. với business rule quan trọng chưa port: capture requirement note trước;
4. regression/golden-path tests pass.

Sau đó **delete toàn bộ**.

---

## 3.6 `legacy/platform/` → RETIRE/PROMOTE requirement, rồi DELETE

`policy_funding` đã có precedent đúng: capture requirement rồi delete khi zero runtime consumer.

Áp dụng cùng pattern cho phần platform legacy còn lại:

- platform concern còn dùng → promote sang `services/cosa`;
- business concern → `services/company`;
- agent concern → `packages/agent_core` / `apps/cosa`;
- không còn consumer/requirement → retire.

Kết thúc: **delete `legacy/platform/`**.

---

# 4. Không giữ migration archive trong một thư mục legacy mới

Không chuyển migrations cũ sang `legacy/migrations_pre_baseline`.

Thay vào đó:

1. tag repository trước cutover;
2. tạo `docs/architecture/DB_FINAL_CUTOVER_LEGACY_MANIFEST.md` ghi commit/path/hash của migration lịch sử;
3. tạo baseline canonical mới;
4. xóa migration cũ khỏi active migration tree nếu baseline reset được chấp nhận;
5. Git history là archive duy nhất của source cũ.

Như vậy tránh tái tạo một `legacy/` khác dưới tên mới.

---

# 5. Migration policy cuối — không chỉnh mãi

## 5.1 Migration immutable

Từ cutover trở đi:

> Migration đã merge/chạy ở bất kỳ environment nào không được sửa nội dung.

Mọi thay đổi = migration mới.

## 5.2 Checksum bắt buộc

Migration registry:

```text
service
filename
sha256
applied_at
```

Nếu `(service, filename)` đã applied mà SHA hiện tại khác:

```text
FAIL HARD
```

## 5.3 Canonical baseline reset một lần

Vì hiện tại lịch sử Company/COSA có contradiction do migration cũ đã bị mutate, không tiếp tục vá migration 1/4/5.

Tạo baseline mới từ **schema đích**:

```text
Company baseline
COSA baseline
Agent Platform baseline
```

Baseline không được sinh từ việc replay một chain đang sai.

### Nếu chưa có production data cần giữ

- reset dev/staging một lần;
- apply baseline;
- seed canonical data;
- verify.

### Nếu đã có data cần giữ

- export;
- transform/reconcile;
- import vào baseline DB;
- compare counts/invariants;
- cutover;
- không chạy destructive reset trực tiếp.

---

# 6. Company DB — chốt identity và tenant structure

## 6.1 User projection

Company không giữ password authority.

Canonical:

```text
core.user_projections
```

## 6.2 Workspace membership

Unique DB-level:

```text
(workspace_id, user_id)
```

Role lấy từ COSA membership sync.

## 6.3 Workforce invariant — sửa cho đủ hai chiều

DB CHECK cuối:

```text
HUMAN:
  human_user_id IS NOT NULL
  agent_spec_id IS NULL
  agent_spec_version IS NULL

AI_AGENT:
  human_user_id IS NULL
  agent_spec_id IS NOT NULL
  agent_spec_version IS NOT NULL
```

Không chỉ cấm field đối nghịch; phải bắt buộc identity field đúng loại.

## 6.4 Manager invariant

`manager_member_id`:

- không được self-reference;
- manager phải tồn tại;
- manager phải cùng `workspace_id`.

DB-level nếu có thể; nếu không thì transaction validation + integration test bắt buộc.

## 6.5 Đóng direct workspace creation

Workspace là projection của COSA company.

Do đó direct `POST /identity/workspaces`:

- internal-only cho migration/test; hoặc
- xóa khỏi exposed API.

Không cho business client tự tạo workspace ngoài sync flow.

## 6.6 Workforce/workspace API auth

Mọi exposed endpoint đọc/ghi:

```text
authenticated
+ membership verified
+ workspace scoped
```

Không endpoint tenant data nào chỉ nhận ID rồi query trực tiếp.

---

# 7. COSA Control Plane — chốt một lần

- credential authority duy nhất;
- `cosa.company_memberships` canonical;
- Company sync từ verified platform membership;
- không production fallback password trong code;
- không production fallback DB URL với credential mặc định;
- production missing secret → fail startup.

---

# 8. Agent Platform — hoàn tất durability thật

## 8.1 Run substrate

Giữ 5 bảng canonical hiện tại.

Production composition:

```text
PostgresRunRepository
```

Không default `InMemoryRunRepository`.

## 8.2 Cross-process durability test thật

Bắt buộc test với Postgres:

```text
process A → create run → checkpoint → die
process B → new connection → load Postgres → resume
```

Verify:

- completed step không chạy lại;
- idempotency giữ;
- approval binding giữ;
- final output đúng.

JSON temp file không được coi là database durability proof.

## 8.3 Governance

- move migration khỏi legacy;
- sửa adapter theo schema SQL thật;
- source Postgres thật → target Postgres thật;
- compare semantic outcome/history/evidence;
- cut write path sang canonical;
- drop legacy governance schema sau retention/migration verification.

## 8.4 Workflow definitions

Tạo durable repository.

Minimum:

```text
workflow_id
version
definition_hash
spec_data
created_at
deprecated_at nullable
```

`(workflow_id, version)` immutable.

## 8.5 Conversation/messages

Durable repository bắt buộc cho production.

Minimum:

```text
conversation_id
tenant_id
message_id
role
content/ref
metadata
created_at
```

Tenant filter bắt buộc ở mọi query.

## 8.6 Event replay

SSE/WebSocket subscriber có thể RAM.

**History/replay không được RAM.** Dùng `agent_core.run_events` hoặc durable event store canonical.

---

# 9. Memory + Knowledge — PROMOTE, không defer nữa

## 9.1 Memory

Canonical PostgreSQL store trong `packages/agent_core/memory`.

Schema:

```text
agent_memory.agent_memories
```

Production default không trả in-memory store.

## 9.2 Knowledge

Canonical pgvector store trong `packages/agent_core/knowledge`.

Schema:

```text
knowledge.knowledge_sources
knowledge.knowledge_chunks
```

Migration chuyển khỏi legacy.

Production default là Postgres/PgVector store.

---

# 10. Budget & cost — salvage semantics dứt điểm

Không port nguyên legacy table graph.

## 10.1 Persistent quota

```text
tenant/company
max_tokens_per_run
max_cost_per_run
max_daily_cost
hard_limit_action
effective_from
```

## 10.2 Durable usage/cost ledger

Minimum:

```text
run_id
tool_call_id nullable
provider
model
input_tokens
output_tokens
cost
currency
created_at
```

`max_daily_cost` phải thực sự aggregate durable spend và enforce.

Không để field tồn tại nhưng không được dùng.

---

# 11. Deployment — chỉ còn canonical path

## 11.1 Company

```text
migrate-company
→ verify-company-schema
→ start company
```

## 11.2 COSA

```text
migrate-cosa
→ verify-cosa-schema
→ start cosa
```

## 11.3 Agent Platform

```text
migrate-agent-platform
→ verify-agent-schema
→ start agent API/workers
```

### Xóa hoàn toàn

- root legacy Alembic production path;
- `alembic upgrade ... || true`;
- legacy Dockerfiles trong deploy path;
- legacy volume mounts;
- legacy `PYTHONPATH`;
- duplicate migration runners.

Migration fail = deployment fail.

---

# 12. Production database hardening

Tách roles:

### Migration role

Có DDL cần thiết.

### Runtime role

Chỉ CRUD cần thiết trên schema được cấp.

Runtime role không có:

- superuser;
- arbitrary CREATE/DROP/ALTER.

Production:

- không default password trong source;
- không public DB port không cần thiết;
- TLS cho managed DB;
- connection limit/pool rõ ràng;
- statement timeout;
- backup/PITR.

---

# 13. CI gates bắt buộc

## Gate A — fresh bootstrap

Tạo empty PostgreSQL rồi migrate riêng:

```text
Company → PASS
COSA → PASS
Agent Platform → PASS
```

## Gate B — rerun

Migration lần 2:

```text
0 change
0 error
```

## Gate C — migration checksum

Mismatch SHA → fail.

## Gate D — schema fingerprint

Fingerprint:

- schemas;
- tables;
- columns/types/nullability;
- PK/FK;
- unique;
- checks;
- critical indexes.

Compare với canonical expected fingerprint.

## Gate E — real DB tests

Không mock DB cho:

- cross-tenant rejection;
- membership sync;
- run resume;
- governance migration adapter;
- approvals;
- idempotency;
- memory;
- knowledge pgvector;
- workflow durable storage.

## Gate F — backup/restore

Backup staging fixture → restore empty environment → migrate remaining versions → app boot → smoke pass.

---

# 14. CI/repository structure sau cutover

`main` phải protected.

Required checks:

- Company tests;
- COSA tests;
- Agent Core tests;
- migration bootstrap;
- schema fingerprint;
- tenant/security tests;
- frontend contract tests khi API đổi.

Xóa workflow/job tên/path `agentos` nếu không còn canonical owner tương ứng.

Không để CI test một folder đã bị delete/archive rồi gọi đó là production quality gate.

---

# 15. Tài liệu cuối phải phản ánh code thật

Cập nhật/replace:

- `db.md`;
- `COSA_CANONICAL_OWNERSHIP_MAP.md`;
- deployment docs;
- migration docs;
- legacy salvage inventory.

Không dùng status:

```text
Fully Promoted
Canonical Live
Completed
```

nếu chưa có persistence wiring + deploy verification thật.

Sau cutover, tạo đúng một document status matrix theo subsystem:

```text
CODE
SCHEMA
PERSISTENCE
DEPLOYED
PROD-VERIFIED
```

---

# 16. Thứ tự thực thi duy nhất

## Phase 0 — Freeze & tag

1. Freeze schema design.
2. Không sửa migration lịch sử nữa.
3. Tag `pre-db-final-cutover`.
4. Snapshot DB dev/staging.
5. Tạo legacy manifest từ commit/tag.

## Phase 1 — Canonical baseline

1. Company baseline.
2. COSA baseline.
3. Agent Platform baseline.
4. Checksum registry.
5. Fresh bootstrap CI.

## Phase 2 — Company/COSA identity & authorization

1. Workforce CHECK đầy đủ.
2. Manager same-workspace.
3. Close direct workspace creation.
4. Auth workforce/workspace endpoints.
5. Tenant boundary tests.

## Phase 3 — Agent durability

1. Postgres RunRepository prod default.
2. Real cross-process resume.
3. Durable workflow definitions.
4. Durable conversations.
5. Durable event replay.

## Phase 4 — Promote legacy storage assets

1. Governance migration/schema.
2. Real migration adapter.
3. Memory Postgres.
4. Knowledge pgvector.

## Phase 5 — Salvage runtime semantics

1. Budget.
2. Cost/usage.
3. Stuck-loop/dispatch/plugin metadata nếu canonical còn thiếu.
4. Characterization tests.

## Phase 6 — Legacy extermination

Theo Exit Matrix:

1. remove all imports/references;
2. remove Docker mounts/PYTHONPATH;
3. delete `legacy/backend`;
4. delete `legacy/agent_runtime_archive`;
5. delete `legacy/agent_runtime`;
6. delete remaining `legacy/business`, `domains`, `entrypoints`, `platform`;
7. delete empty `legacy/` directory;
8. CI grep guard: path/reference `legacy/` trong production code/deploy = fail.

## Phase 7 — Deployment cutover

1. canonical migration jobs only;
2. rebuild staging from empty;
3. restore test;
4. voice/realtime smoke;
5. app smoke;
6. prod cutover.

## Phase 8 — Lock

1. protect `main`;
2. update docs;
3. tag canonical baseline release;
4. close `DB-FINAL-CUTOVER`;
5. cấm mở thêm foundational cleanup plan nếu không có ADR + production requirement mới.

---

# 17. Legacy deletion gate — checklist bắt buộc

Không delete legacy trước khi checklist này đạt 100%, nhưng khi đạt thì **phải delete**, không giữ lại “phòng khi cần”.

```text
[ ] Mọi legacy top-level directory có PROMOTE/RETIRE mapping
[ ] Không item UNKNOWN / KEEP FOR NOW
[ ] Governance migration đã canonical
[ ] Memory migration/store đã canonical
[ ] Knowledge migration/store đã canonical
[ ] Budget/cost semantics đã canonical hoặc retire rõ ràng
[ ] Agent runtime behavior inventory 100% mapped
[ ] Business/domain legacy runtime consumers = 0
[ ] Realtime không mount legacy backend
[ ] Deploy không dùng legacy Docker/Alembic
[ ] PYTHONPATH không chứa legacy
[ ] CI không test legacy như active runtime
[ ] Grep imports/references legacy production path = 0
[ ] Data migration cần thiết đã verified
[ ] Git tag trước deletion tồn tại
[ ] Requirement notes cần giữ đã capture
[ ] Full regression + smoke pass
```

Sau checklist: `rm -rf legacy/` là một phần của Definition of Done, không phải tùy chọn.

---

# 18. Definition of Done — toàn Epic

```text
[ ] Company DB build từ zero
[ ] COSA DB build từ zero
[ ] Agent Platform build từ zero
[ ] Migration rerun no-op
[ ] Migration checksum active
[ ] Không mutable historical migration trong active tree
[ ] Company canonical 7-schema structure được khóa
[ ] COSA company_memberships canonical
[ ] Workforce HUMAN/AI_AGENT invariant đúng DB-level
[ ] manager cùng workspace
[ ] Direct workspace creation không còn public bypass
[ ] Workforce/workspace APIs auth + tenant scoped
[ ] Production RunRepository = Postgres
[ ] Cross-process Postgres resume pass
[ ] Workflow definitions durable
[ ] Conversation history durable
[ ] Event replay durable
[ ] Governance canonical migration + real DB adapter pass
[ ] Memory Postgres roundtrip pass
[ ] Knowledge pgvector roundtrip pass
[ ] Budget per-run + daily thực sự enforce
[ ] Cost/usage durable
[ ] Không canonical code cần legacy SQL/schema
[ ] Không production import legacy
[ ] Không deployment reference legacy
[ ] Không volume/PYTHONPATH legacy
[ ] `legacy/` không còn trên main
[ ] Migration failure làm deploy fail
[ ] Production secrets fail-closed
[ ] Runtime DB role không DDL
[ ] Backup/restore test pass
[ ] Fresh-bootstrap/schema-fingerprint CI required
[ ] main protected
[ ] docs khớp code thật
```

Nếu còn bất kỳ ô nào chưa tick:

> **Không tuyên bố cấu trúc/database/legacy đã hoàn tất.**

---

# 19. Cấu trúc repository mục tiêu sau cutover

```text
apps/
  cosa/

packages/
  agent_core/
    capabilities/
    contracts/
    coordination/
    governance/
    kernel/
    knowledge/
    memory/
    migrations/
    runs/
    workflows/
    ...

services/
  company/
    commercial/
    finance-legal/
    identity/
    operations/
    shared/
    scripts/

  cosa/
    migrations/
    services/
    storage/
    ...

  realtime_agent/

frontend/

docs/
  architecture/

# KHÔNG CÒN:
# legacy/
# agentos/
# production backend cũ
```

---

# 20. Quy tắc chống tái phát

Sau cutover, không mở lại các quyết định nền tảng này chỉ vì muốn “cleanup đẹp hơn”:

- `company_id` vs `workspace_id` trong Company DB;
- `organizations` wrapper 1:1;
- `users` vs `user_projections`;
- `company_roles` vs `company_memberships`;
- numeric agent-definition FK;
- duplicate validation domain;
- monolithic legacy business DB;
- in-memory production persistence;
- mutable migration;
- giữ code legacy cạnh production “để tham khảo”.

Thay đổi nền tảng chỉ được phép khi có đủ:

1. production requirement mới;
2. ADR;
3. compatibility/migration plan;
4. test chứng minh;
5. rollback/forward-recovery plan.

---

# 21. Kết quả cuối

Sau `DB-FINAL-CUTOVER`, kiến trúc chỉ còn:

```text
COSA Control Plane DB
  = identity / company / membership / license authority

Company DB
  = workspace-scoped business truth

Agent Platform Storage
  = run / governance / workflow / conversation / memory / knowledge / usage truth
```

Giữa ba ownership boundary:

- API/capability contracts;
- không ORM import chéo;
- không DB query chéo;
- không migration chéo owner;
- không legacy dependency.

**Đích cuối không phải “legacy đã archive”. Đích cuối là “legacy đã biến mất khỏi active repository vì mọi thứ đã được promote hoặc retire dứt điểm”.**
