# Production Event-Intake Wiring + Trigger Governance — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Steps dùng `- [ ]`.

**Goal:** Làm cho vòng lặp lõi **event → inbox → trigger → run** chạy được ở production. P0 để `event_intake_deps=None` ngoài test — endpoint `/agent/internal/events` hiện trả 500 "not configured" ở production. Plan này dựng tất cả dependency production + rule store bền + admin endpoint enable-rule gated bởi `can_enable_trigger`.

**Architecture:** `build_cosa_agent_plane()` dựng `event_intake_deps` production khi có `AGENT_CORE_DATABASE_URL`: `LocalServiceAuth` (HMAC), asyncpg pool (`db`), `TriggerPolicyService(PostgresTriggerRuleStore, RegistryBackedCapabilityChecker, PostgresRunCounter, evidence_store=PostgresPromotionEvidenceRepository, fingerprint_provider=SpecFingerprintProvider)`, `LocalExecutionPlaneScheduleClient` (qua `resolve_execution_plane_url()`). `event_inbox` thêm cột `aggregate_type`/`aggregate_id` để rate-limit theo aggregate/ngày. Admin `POST /agent/events/rules/{id}/enable` chạy `can_enable_trigger` trước khi bật.

**Tech Stack:** Python 3.11, asyncpg (raw, khớp `apps/cosa/events/inbox.py`), SQLAlchemy (evidence/registry đã có), FastAPI, pytest. PostgreSQL 16.

**Spec:** `2026-08-28-event-driven-agent-operating-model-design.md` §3.3 (trigger rules), DoD #5/#8. Đóng gap phát hiện trong closeout.

## Global Constraints

- **TDD**: test đỏ → xác nhận → implement → xanh → commit. Partial commit (`git commit <path>`).
- **An toàn working tree** (CLAUDE.md #10): `git fetch` trước commit; không `--force`.
- **`packages/agent_core` KHÔNG import `apps/` hay `services/`.** Rule store / deps builder ở `apps/cosa/`.
- **Không production fallback im lặng.** `event_intake_deps` production đòi `AGENT_CORE_DATABASE_URL`; thiếu → intake route trả 500 rõ ràng (đã có).
- **artifact_only rule** fire không cần evidence; **proposal/write** đòi evidence pass + fingerprint khớp (DoD #5). `write` thêm human approval.
- Migration: `ls packages/agent_core/migrations/` — hiện max `019` ⇒ `020_*`.
- Comment tiếng Việt cho why.

---

## File Structure

| File | Trách nhiệm |
| --- | --- |
| `packages/agent_core/migrations/020_event_trigger_rules.sql` | `event_trigger_rules` table + ALTER `event_inbox` ADD `aggregate_type`/`aggregate_id` + index |
| `apps/cosa/events/rule_store.py` | `PostgresTriggerRuleStore` (asyncpg) — `find()` + `get(rule_id)` + `upsert()` + `set_enabled()` |
| `apps/cosa/events/run_counter.py` | `PostgresRunCounter.today(ws, rule_id, aggregate_id)` — count `event_inbox` accepted theo aggregate/ngày |
| `apps/cosa/events/local_auth.py` | `LocalServiceAuth.verify(sig, raw_body)` HMAC-SHA256 keyed `COSA_LOCAL_SERVICE_SECRET` |
| `apps/cosa/events/capability_checker.py` | `RegistryBackedCapabilityChecker(cap_registry).has(ws, cap)` — coarse pre-filter (gateway enforce thật lúc run) |
| `apps/cosa/events/fingerprints.py` | `SpecFingerprintProvider(spec_registry).current(rule)` — definition_hash hiện tại của agent_spec |
| `apps/cosa/events/execution_plane_client.py` | `LocalExecutionPlaneScheduleClient.schedule_reference_task(rule, env)` → gọi scheduler tại `resolve_execution_plane_url()` |
| `apps/cosa/events/deps.py` | `EventIntakeDeps` dataclass + `build_event_intake_deps(*, database_url, spec_registry, capability_registry)` |
| `apps/cosa/events/inbox.py` | `record()` nhận thêm `aggregate_type`/`aggregate_id` |
| `apps/cosa/events/router.py` | truyền `aggregate_type`/`aggregate_id` từ `env` vào `inbox_store.record` |
| `apps/cosa/events/trigger_policy.py` | `resolve()` gọi `evidence_store.get()` (khớp repo hiện có) thay `.load()` |
| `apps/cosa/composition/agent_plane.py` | dựng `event_intake_deps` production khi `resolved_url` |
| `apps/cosa/api/event_rule_routes.py` | `GET/POST /agent/events/rules`, `POST /agent/events/rules/{id}/enable` (gated) |
| `apps/cosa/api/app.py` | mount router mới |
| `tests/apps/cosa/events/test_*` | rule store, run counter, local auth, deps build, enable endpoint |

---

## Task 1: Migration + inbox aggregate columns

**Files:** Create `packages/agent_core/migrations/020_event_trigger_rules.sql`; Modify `apps/cosa/events/inbox.py`, `apps/cosa/events/router.py`; Test `tests/apps/cosa/events/test_inbox_aggregate.py`

- [ ] **Step 1** Viết migration:
```sql
CREATE TABLE IF NOT EXISTS event_trigger_rules (
  rule_id           TEXT PRIMARY KEY,
  workspace_id      TEXT NOT NULL,
  event_type        TEXT NOT NULL,
  agent_spec_id     TEXT NOT NULL,
  agent_spec_version TEXT NOT NULL,
  agent_spec_hash   TEXT NOT NULL,
  mode              TEXT NOT NULL CHECK (mode IN ('artifact_only','proposal','write')),
  max_runs_per_aggregate_per_day INTEGER NOT NULL DEFAULT 1,
  required_capabilities JSONB NOT NULL DEFAULT '[]'::jsonb,
  aggregate_filter  JSONB,
  owner             TEXT NOT NULL DEFAULT 'operator',
  enabled           BOOLEAN NOT NULL DEFAULT false,
  eval_evidence_ref TEXT,
  event_schema_version INTEGER NOT NULL DEFAULT 1,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (workspace_id, event_type)
);
ALTER TABLE event_inbox
  ADD COLUMN IF NOT EXISTS aggregate_type TEXT,
  ADD COLUMN IF NOT EXISTS aggregate_id   TEXT;
CREATE INDEX IF NOT EXISTS idx_event_inbox_agg_day
  ON event_inbox (workspace_id, aggregate_id, received_at);
```
- [ ] **Step 2** Test đỏ `test_inbox_aggregate.py`: `record()` với `aggregate_type`/`aggregate_id` → SQL INSERT chứa 2 cột đó (dùng fake conn ghi lại query+args).
- [ ] **Step 3** `inbox.record()`: thêm param `aggregate_type=None`, `aggregate_id=None`; INSERT thêm 2 cột ($8,$9). `router.py`: `inbox_store.record(..., aggregate_type=env.aggregateType, aggregate_id=env.aggregateId)`.
- [ ] **Step 4** Chạy `python packages/agent_core/scripts/migrate.py` + `pytest tests/apps/cosa/events/test_inbox_aggregate.py tests/apps/cosa/test_local_event_intake.py -q` → xanh (cập nhật `InMemoryInboxStore.record` nhận 2 kwarg mới).
- [ ] **Step 5** Commit.

---

## Task 2: PostgresTriggerRuleStore + RunCounter + LocalAuth

**Files:** Create `apps/cosa/events/rule_store.py`, `run_counter.py`, `local_auth.py`; Test `tests/apps/cosa/events/test_rule_store.py`, `test_run_counter.py`, `test_local_auth.py`

**Interfaces:**
- `PostgresTriggerRuleStore(pool)` — `async find(workspace_id, event_type, aggregate) -> EventTriggerRule | None`; `async get(rule_id) -> EventTriggerRule | None`; `async upsert(rule) -> None`; `async set_enabled(rule_id, enabled: bool) -> None`. Map row → `EventTriggerRule` (parse `required_capabilities` JSON, build `PinnedSpecIdentity`).
- `PostgresRunCounter(pool)` — `async today(workspace_id, rule_id, aggregate_id) -> int` = `SELECT count(*) FROM event_inbox WHERE workspace_id=$1 AND aggregate_id=$2 AND outcome='accepted' AND received_at::date = current_date`. (rule_id không dùng — rate-limit theo aggregate/ngày across rules; ghi rõ trong docstring.)
- `LocalServiceAuth(secret)` — `verify(signature: str, raw_body: dict) -> bool` = `hmac.compare_digest(signature, hmac_sha256(secret, json.dumps(raw_body)))`; `sign(raw_body) -> str` (đối xứng, dùng cho test + relay).

- [ ] **Step 1** Test đỏ (3 file). `test_local_auth`: sign→verify round-trip; empty sig → False; tampered body → False. `test_rule_store` + `test_run_counter`: dùng asyncpg pool thật tới `AGENT_CORE_DATABASE_URL` (container `cosa_postgres` đang chạy) với `pytest.skip` nếu không set/connect được. Seed row, assert `find`/`today`.
- [ ] **Step 2** Implement 3 module.
- [ ] **Step 3** `pytest tests/apps/cosa/events/ -q` → xanh (rule_store/run_counter có thể skip nếu DB không reachable trong CI).
- [ ] **Step 4** Commit.

---

## Task 3: Capability checker + fingerprint provider + evidence wiring

**Files:** Create `apps/cosa/events/capability_checker.py`, `apps/cosa/events/fingerprints.py`; Modify `apps/cosa/events/trigger_policy.py`; Test `tests/apps/cosa/events/test_fingerprints.py`, `tests/apps/cosa/test_trigger_evidence_wiring.py`

**Interfaces:**
- `RegistryBackedCapabilityChecker(capability_registry)` — `has(workspace_id, capability) -> bool` = `capability in capability_registry` (coarse; gateway enforce thật lúc run). Docstring nêu rõ đây là pre-filter.
- `SpecFingerprintProvider(spec_registry)` — `async current(rule) -> dict[str,str]` = `{rule.agent_spec.id: (await spec_registry.get("agent", rule.agent_spec.id, rule.agent_spec.version)).definition_hash}` (nếu không tìm thấy → `{id: "<missing>"}` ⇒ stale).
- `trigger_policy.resolve()`: đổi `self.evidence_store.load(ref)` → `self.evidence_store.get(ref)` (khớp `PromotionEvidenceRepository` hiện có, `promotion_repository.py`).

- [ ] **Step 1** Test đỏ. `test_fingerprints`: registry có spec → trả đúng hash; không có → "<missing>". `test_trigger_evidence_wiring`: `TriggerPolicyService` với `InMemoryPromotionEvidenceRepository` + fake fingerprint provider — proposal rule + evidence stale → `policy_denied/stale_eval_evidence`; evidence fresh+pass → `accepted`; artifact_only rule không evidence → `accepted`.
- [ ] **Step 2** Implement + sửa `resolve()`.
- [ ] **Step 3** `pytest tests/apps/cosa/test_event_trigger_promotion.py tests/apps/cosa/test_trigger_evidence_wiring.py tests/apps/cosa/test_local_event_intake.py -q` → xanh.
- [ ] **Step 4** Commit.

---

## Task 4: execution-plane client + deps builder + agent_plane wiring

**Files:** Create `apps/cosa/events/execution_plane_client.py`, `apps/cosa/events/deps.py`; Modify `apps/cosa/composition/agent_plane.py`; Test `tests/apps/cosa/events/test_deps_build.py`, `tests/apps/cosa/composition/test_event_intake_deps_wiring.py`

**Interfaces:**
- `LocalExecutionPlaneScheduleClient(base_url, service_token, client=None)` — `async schedule_reference_task(rule, env) -> str`: POST tới `{base_url}/control-plane/internal/scheduled-tasks` (khớp `HttpControlPlaneSchedulerClient.schedule`) với `input_payload = {"kind":"event_trigger","workspace_id":env.workspaceId,"event_id":env.eventId,"correlation_id":env.correlationId,"agent_spec":{id,version,definition_hash},"aggregate_ref":{type,id},"mode":rule.mode}` (reference-only, KHÔNG raw payload). Trả `id` từ response.
- `@dataclass EventIntakeDeps`: `local_auth`, `db` (asyncpg pool wrapper có `.begin()`), `trigger_policy`, `execution_plane`, `caller_workspace_id: Optional[str] = None`.
- `async build_event_intake_deps(*, database_url, spec_registry, capability_registry) -> EventIntakeDeps`:
  - `pool = await asyncpg.create_pool(database_url.replace("postgresql+asyncpg://","postgresql://"))`
  - `db = _AsyncpgTx(pool)` — `.begin()` async ctx → acquire conn + `conn.transaction()`
  - `trigger_policy = TriggerPolicyService(PostgresTriggerRuleStore(pool), RegistryBackedCapabilityChecker(capability_registry), PostgresRunCounter(pool), evidence_store=PostgresPromotionEvidenceRepository(<sqlalchemy session factory>), fingerprint_provider=SpecFingerprintProvider(spec_registry), policy_version=os.environ.get("COSA_POLICY_VERSION","p1"))`
  - `execution_plane = LocalExecutionPlaneScheduleClient(resolve_execution_plane_url(), os.environ.get("COSA_WORKER_SERVICE_TOKEN",""))`
- `agent_plane.py`: khi `event_intake_deps is None and resolved_url` và không phải trong nhánh test-only → `event_intake_deps = await? ...`. **Lưu ý:** `build_cosa_agent_plane` là sync. `build_event_intake_deps` async (asyncpg.create_pool). Giải: lazy — `event_intake_deps` là một factory/coroutine chạy ở lifespan startup (`app.py`), hoặc dùng `asyncpg.create_pool` sync-friendly qua `anyio.from_thread`. **Chọn:** thêm `async def build_and_attach_event_intake_deps(plane, *, database_url)` gọi từ `app.py` lifespan sau `build_cosa_agent_plane()` (giống `seed_cosa_agent_specs`). `agent_plane.py` giữ `event_intake_deps=None` mặc định; `app.py` lifespan gán nếu `resolved_url`.

- [ ] **Step 1** Test đỏ. `test_deps_build`: `build_event_intake_deps` với DB reachable → `EventIntakeDeps` có đủ field đúng kiểu (skip nếu no DB). `test_event_intake_deps_wiring`: `create_cosa_app()` lifespan (injected plane) → nếu set `AGENT_CORE_DATABASE_URL` fake + monkeypatch `build_event_intake_deps` → `plane.event_intake_deps` không None.
- [ ] **Step 2** Implement client + deps + `_AsyncpgTx` + `app.py` lifespan hook.
- [ ] **Step 3** `pytest tests/apps/cosa/events/ tests/apps/cosa/test_app_lifecycle.py tests/apps/cosa/test_local_event_intake.py -q` → xanh.
- [ ] **Step 4** e2e thủ công (DB container): start app với `AGENT_CORE_DATABASE_URL` thật, POST một signed envelope tới `/agent/internal/events` → `202 {"outcome":"ignored_rule_disabled"}` (chưa có rule). Seed một `artifact_only` rule `enabled=true` → POST lại → `{"outcome":"accepted","scheduledTaskId":...}`.
- [ ] **Step 5** Commit.

---

## Task 5: Admin endpoint — create/enable trigger rule (gated)

**Files:** Create `apps/cosa/api/event_rule_routes.py`; Modify `apps/cosa/api/app.py`; Test `tests/apps/cosa/test_event_rule_admin.py`

**Interfaces:**
- `POST /agent/events/rules` — body: rule fields (event_type, agent_spec {id,version,hash}, mode, max_runs..., required_capabilities, aggregate_filter?, eval_evidence_ref?). `enabled` LUÔN false lúc tạo. → `PostgresTriggerRuleStore.upsert`. 201.
- `GET /agent/events/rules?workspace_id=` — list (không lộ gì nhạy cảm).
- `POST /agent/events/rules/{rule_id}/enable` — auth: operator; workspace check.
  - Load rule; nếu `mode == "artifact_only"` → `set_enabled(true)`, 200 `{status:"enabled"}`.
  - Ngược lại: `evidence = await evidence_store.get(rule.eval_evidence_ref)`, `fps = await fingerprint_provider.current(rule)`, `gate = can_enable_trigger(rule, evidence, fps, policy_version=...)`.
    - `not gate.allowed` → 422 `{status:"denied", reason: gate.reason}`.
    - `gate.allowed and gate.requires_human_approval` và request không có `approved_by` → 202 `{status:"pending_human_approval"}`.
    - còn lại → `set_enabled(true)`, 200 `{status:"enabled"}`.
- Deps lấy từ `plane.event_intake_deps.trigger_policy` (rule store + evidence store + fp provider ở trong đó — expose chúng trên `TriggerPolicyService` hoặc `EventIntakeDeps`).

- [ ] **Step 1** Test đỏ `test_event_rule_admin.py` (injected plane + in-memory stores):
```python
async def test_create_rule_is_always_disabled()
async def test_enable_artifact_only_rule_succeeds()
async def test_enable_write_rule_without_evidence_denied()      # 422 reason no_eval_evidence
async def test_enable_write_rule_with_valid_evidence_pending()  # 202 pending_human_approval
async def test_enable_write_rule_with_evidence_and_approval_enabled()  # 200
async def test_enable_proposal_rule_with_stale_evidence_denied()  # 422 stale_evidence
async def test_enable_rejected_cross_workspace()               # 403
```
- [ ] **Step 2** Implement router + expose `rule_store`/`evidence_store`/`fingerprint_provider` trên `EventIntakeDeps` (hoặc `TriggerPolicyService`).
- [ ] **Step 3** `pytest tests/apps/cosa/test_event_rule_admin.py -q` → xanh.
- [ ] **Step 4** Commit.

---

## Self-Review

| Yêu cầu | Task |
| --- | --- |
| `/agent/internal/events` hoạt động ở production (deps ≠ None) | Task 4 |
| Rule store bền (không mất qua restart) | Task 1 (table) + Task 2 (store) |
| Rate limit theo aggregate/ngày | Task 1 (cột) + Task 2 (`PostgresRunCounter`) |
| DoD #5 — drift ⇒ trigger reject | Task 3 (fingerprint + evidence trong `resolve()`) |
| artifact_only fire không cần evidence; write đòi human approval | Task 3 + Task 5 (`can_enable_trigger` ở enable endpoint) |
| Reference-only schedule (không raw payload lên scheduler) | Task 4 (`schedule_reference_task` payload) |
| Admin có thể tạo/enable rule an toàn | Task 5 |

**Type consistency:** `EventTriggerRule` (đã có `eval_evidence_ref`, `event_schema_version` từ closeout) — Task 1 table khớp field. `evidence_store.get()` khớp `PromotionEvidenceRepository`. `can_enable_trigger(rule, evidence, fps, *, policy_version)` khớp `trigger_promotion.py` (`94814de6`). `schedule_reference_task(rule, env)` khớp `router.py:65`.

**No placeholder:** DDL đầy đủ; interface + test-name cụ thể mỗi task; điểm sync/async (`build_cosa_agent_plane` sync vs asyncpg async) giải quyết bằng lifespan hook trong `app.py` (giống `seed_cosa_agent_specs`).

---

## Verification (end-to-end)

```
python packages/agent_core/scripts/migrate.py
PYTHONPATH=. .venv/bin/pytest tests/apps/cosa tests/agent_core -q
```
**e2e (DB container `cosa_postgres`):**
1. App start với `AGENT_CORE_DATABASE_URL` + `COSA_LOCAL_SERVICE_SECRET` → `plane.event_intake_deps` ≠ None.
2. `POST /agent/events/rules` tạo rule `operations.task.created.v1` mode `artifact_only` → 201, `enabled=false`.
3. `POST /agent/events/rules/{id}/enable` → 200 `enabled`.
4. Relay/thủ công: POST signed envelope `operations.task.created.v1` tới `/agent/internal/events` → `{"outcome":"accepted","scheduledTaskId":...}`; `event_inbox` có 1 row `outcome=accepted`; scheduled task payload chỉ chứa reference.
5. POST lại cùng `eventId` → `{"outcome":"duplicate"}`, không scheduled task thứ 2.
6. Tạo rule `mode=write` không evidence → `enable` trả 422 `no_eval_evidence`.
7. Gắn `eval_evidence_ref` tới `InMemoryPromotionEvidenceRepository` evidence pass + fingerprint khớp → `enable` trả 202 `pending_human_approval`; gửi lại với `approved_by` → 200.

---

## Execution Handoff

Sau plan này, vòng lặp event operating model chạy production. Còn lại (closeout khác): Task 5 P1-Task-2 TS scheduler, Task 6a metrics, Task 6b semantic retrieval, Task 6c DoD audit.
Không cho phép: deploy VPS, cài broker, xoá dữ liệu.
