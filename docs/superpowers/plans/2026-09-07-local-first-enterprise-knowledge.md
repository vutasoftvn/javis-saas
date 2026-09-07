# Local-first Enterprise Knowledge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Phát hành Vault Document API và Knowledge ingestion local-first, có version/provenance, đọc theo role/ACL và context an toàn cho founder/member.

**Architecture:** Workspace Runtime Node là nơi duy nhất giữ file gốc, quarantine, document metadata, ingestion state, markdown/chunk/embedding và retrieval index. `services/cosa` tại execution plane chỉ điều phối durable task local; Platform Control Plane chỉ nhận telemetry aggregate đã redact. Vault document version là nguồn lifecycle/ACL, Knowledge source là projection dẫn xuất có provenance; agent gọi một capability GraphQL read-only, typed và đã áp quyền thay vì đọc DB hoặc filesystem.

**Tech Stack:** FastAPI/Pydantic/Python 3.11, PostgreSQL + pgvector + RLS, local persistent volume, asyncio, Encore.ts/TypeScript/Drizzle scheduler, Flutter/Dart/GetX, pytest, Vitest, Flutter test.

**Spec:** [Local-first Enterprise Knowledge design](../specs/2026-09-07-local-first-enterprise-knowledge-design.md)

## Global Constraints

- Không dùng S3, MinIO, cloud bucket hay `boto3` làm storage authority/dependency cho local workspace. Adapter cloud chỉ có thể thêm sau một spec riêng.
- Raw file, filename, local path/object key, markdown, chunk và embedding không rời Workspace Runtime Node; platform telemetry chỉ mang ID, state, kích thước bucketed và error code allowlist.
- Agent runtime không đọc filesystem/Agent DB/Company DB trực tiếp. Chat chỉ nhận tri thức qua capability `knowledge.enterprise.read`.
- GraphQL chỉ chạy trên Workspace Runtime Node qua persisted `operationId`; endpoint không nhận raw query text từ agent, không có mutation và resolver luôn nhận principal/workspace/policy snapshot đã xác thực.
- Workspace lấy từ `AuthenticatedIdentity`/delegation đã cross-check; không tin workspace từ query/body/path để định quyền.
- Mọi migration release là additive/expand; purge vật lý là job có retention/legal-hold, không xóa đồng bộ trong request.
- RLS phải fail-closed nếu `cosa.workspace_id` thiếu; application DB role không có `BYPASSRLS` và bảng phải `FORCE ROW LEVEL SECURITY`.
- Không thay các file đang dirty ngoài phạm vi task. Trước mỗi commit kiểm tra `git status`; mỗi task chỉ commit file của chính task khi test tương ứng pass.
- Không bật `KNOWLEDGE_INGESTION_ENABLED` hay `vaultSupported` cho tới Task 13 pass trên stack local thật.
- Model/provider routing theo founder UI được triển khai độc lập qua [Local-first Model Routing plan](2026-09-07-local-first-model-routing.md); không được mở setting model trước release evidence của plan đó.

## File map chính

| Vùng | File tạo/sửa | Trách nhiệm sau thay đổi |
|---|---|---|
| Data contract | `packages/agent/vault/models.py`, `packages/agent/knowledge/models.py`, migration 024–026 | Document/version/grant/provenance và RLS local.
| Local store | `apps/cosa/knowledge_ingestion/workspace_store.py`, `local_upload_routes.py` | Quarantine trên persistent volume, ticket durable, stream/atomic finalize.
| Ingestion | `apps/cosa/knowledge_ingestion/{handler,local_repository,permission}.py` | State/fencing local, scan/convert, publish projection.
| Runtime wiring | `apps/cosa/composition/{agent_plane,storage_factory}.py`, `apps/cosa/api/app.py`, `apps/cosa/worker/main.py` | Inject local store/scanner/sandbox/repository vào API và worker.
| Vault/knowledge API | `apps/cosa/api/{vault_routes,vault_schemas,knowledge_routes}.py` | REST commands/query có identity và ACL.
| Retrieval/capability | `packages/agent/knowledge/providers/postgres.py`, `apps/cosa/capabilities/knowledge_read.py` | Query auth-first và context citation.
| Local GraphQL read BFF | `apps/cosa/graphql/**`, `apps/cosa/api/graphql_routes.py` | Persisted read operations cho workspace context và knowledge search; resolver tự enforce quyền. |
| Execution scheduler | `services/cosa/handlers/document-ingestion.handler.ts`, `services/cosa/services/document-ingestion.service.ts` | Chỉ local execution-plane job/fencing; không public claim token.
| UI/contracts | `shared/contracts/mvp-surface.json`, `frontend/lib/modules/vault/**` | Surface thật, role-aware, không còn unavailable sau release gate.

---

### Task 1: Khóa ranh giới local-first và containment hiện tại

**Files:**
- Create: `tests/apps/cosa/knowledge_ingestion/test_local_first_boundary.py`
- Modify: `apps/cosa/config/planes.py`
- Modify: `apps/cosa/knowledge_ingestion/control_plane_client.py`
- Modify: `apps/cosa/api/knowledge_routes.py`
- Modify: `services/cosa/handlers/document-ingestion.handler.ts`
- Test: `tests/apps/cosa/knowledge_ingestion/test_local_first_boundary.py`, `services/cosa/tests/document-ingestion.test.ts`

**Interfaces:**
- Consumes: `resolve_execution_plane_url() -> str`, ADR-LOCAL-FIRST-001.
- Produces: `LocalDocumentIngestionClient(execution_plane_url: str)`; no ingestion call resolves `COSA_PLATFORM_CONTROL_PLANE_URL`.

- [x] **Step 1: Write the failing Python boundary tests.**

```python
def test_local_ingestion_client_uses_execution_plane(monkeypatch):
    monkeypatch.setenv("COSA_EXECUTION_PLANE_URL", "http://workspace.local:4001")
    monkeypatch.setenv("COSA_PLATFORM_CONTROL_PLANE_URL", "https://platform.example")
    client = LocalDocumentIngestionClient()
    assert client.base_url == "http://workspace.local:4001"

def test_platform_url_is_never_used_for_document_ingestion(monkeypatch):
    monkeypatch.setenv("COSA_PLATFORM_CONTROL_PLANE_URL", "https://platform.example")
    assert "platform.example" not in LocalDocumentIngestionClient().base_url
```

- [x] **Step 2: Run the focused Python test and record the expected failure.**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/knowledge_ingestion/test_local_first_boundary.py -q`

Expected: FAIL because `DocumentIngestionControlPlaneClient` resolves the platform URL.

- [x] **Step 3: Rename the client contract and make the URL explicit.**

```python
class LocalDocumentIngestionClient:
    def __init__(self, execution_plane_url: str | None = None, *, http_client: httpx.AsyncClient | None = None):
        self.base_url = (execution_plane_url or resolve_execution_plane_url()).rstrip("/")
        self._http_client = http_client
```

Replace imports/call sites. Do not retain a platform URL fallback. Keep worker service authentication and claim-token fencing only for calls to the local scheduler service.

- [x] **Step 4: Remove public exposure of worker fencing data and test it in Vitest.**

```ts
expect(response.body).not.toHaveProperty("claimToken");
expect(response.body).not.toHaveProperty("originalObjectKey");
```

`sanitizeRecordForPublic` must never return either field. Preserve a separate worker-only DTO only for a local worker endpoint protected by worker service auth.

- [x] **Step 5: Run the boundary tests.**

Run:

```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/knowledge_ingestion/test_local_first_boundary.py -q
cd services/cosa && npx vitest run tests/document-ingestion.test.ts
```

Expected: PASS; test output proves no document-ingestion request is addressed to the Platform URL.

- [x] **Step 6: Commit.**

```bash
git add apps/cosa/config/planes.py apps/cosa/knowledge_ingestion/control_plane_client.py \
  apps/cosa/api/knowledge_routes.py services/cosa/handlers/document-ingestion.handler.ts \
  tests/apps/cosa/knowledge_ingestion/test_local_first_boundary.py services/cosa/tests/document-ingestion.test.ts
git commit -m "refactor(knowledge): keep ingestion orchestration on local execution plane"
```

---

### Task 2: Thêm schema Vault version, policy grant và RLS fail-closed

**Files:**
- Create: `packages/agent/migrations/024_vault_access_policy_and_local_ingestion.sql`
- Create: `packages/agent/migrations/025_knowledge_vault_provenance_and_rls.sql`
- Modify: `packages/agent/vault/models.py`
- Modify: `packages/agent/vault/repository.py`
- Modify: `packages/agent/knowledge/models.py`
- Test: `tests/agent/vault/test_access_policy_repository.py`, `tests/agent/knowledge/test_vault_provenance.py`

**Interfaces:**
- Produces `VaultAccessGrant(subject_type, subject_id, permission)` and `VaultDocumentVersionRecord.classification`, `visibility`, `access_policy_version`.
- Produces `KnowledgeDocument.vault_document_id`, `vault_version_id`, `access_policy_version`.
- Consumes `set_config('cosa.workspace_id', workspace_id, true)` on every repository transaction.

- [ ] **Step 1: Write failing repository/model tests.**

```python
async def test_member_without_grant_cannot_list_document(postgres_vault_repo):
    doc = await postgres_vault_repo.create_draft("ws-a", "Board plan", created_by="founder")
    assert await postgres_vault_repo.list_authorized_documents("ws-a", "member-1", {"member"}) == []

async def test_published_knowledge_requires_same_vault_version(postgres_knowledge_store):
    with pytest.raises(ValueError, match="vault_version_id"):
        await postgres_knowledge_store.save_document(KnowledgeDocument(workspace_id="ws-a", title="x"))
```

- [ ] **Step 2: Run tests against disposable Postgres.**

Run: `AGENT_TEST_DATABASE_URL="$AGENT_TEST_DATABASE_URL" PYTHONPATH=. .venv/bin/python -m pytest tests/agent/vault/test_access_policy_repository.py tests/agent/knowledge/test_vault_provenance.py -q`

Expected: FAIL because grants/provenance and schema constraints do not exist.

- [ ] **Step 3: Write expand-only migrations.**

Create `vault.document_access_grants` with a unique `(workspace_id, document_id, subject_type, subject_id, permission)` key. Add `classification`, `visibility`, `access_policy_version`, `retention_until`, `legal_hold` to documents/versions. Add `vault_document_id`, `vault_version_id`, `access_policy_version` to `knowledge.knowledge_sources` and a FK to the Vault version. Enable and force RLS on all Vault and Knowledge tables.

```sql
CREATE POLICY vault_documents_workspace_isolation ON vault.documents
  FOR ALL
  USING (workspace_id = current_setting('cosa.workspace_id', true))
  WITH CHECK (workspace_id = current_setting('cosa.workspace_id', true));
ALTER TABLE vault.documents FORCE ROW LEVEL SECURITY;
```

Apply the same exact non-null policy shape to versions, grants, knowledge sources, chunks, source versions and embeddings. Do not preserve the existing `IS NULL OR = ''` bypass.

- [ ] **Step 4: Add typed records and repository methods.**

```python
async def grant_access(self, workspace_id: str, document_id: UUID, grant: VaultAccessGrant) -> None: ...
async def resolve_accessible_document_ids(self, workspace_id: str, principal_id: str, role_ids: set[str]) -> set[UUID]: ...
```

Every method sets the workspace transaction configuration before querying. Validate `classification` and `visibility` using `StrEnum`, never free text.

- [ ] **Step 5: Run migration, repository and tenancy gates.**

Run:

```bash
make migrate-agent-platform
PYTHONPATH=. .venv/bin/python -m pytest tests/agent/vault/test_access_policy_repository.py tests/agent/knowledge/test_vault_provenance.py -q
make tenancy-check
```

Expected: PASS; a query made without workspace setting sees zero rows rather than all rows.

- [ ] **Step 6: Commit.**

```bash
git add packages/agent/migrations/024_vault_access_policy_and_local_ingestion.sql \
  packages/agent/migrations/025_knowledge_vault_provenance_and_rls.sql packages/agent/vault \
  packages/agent/knowledge tests/agent/vault tests/agent/knowledge
git commit -m "feat(vault): add local document access policy and provenance"
```

---

### Task 3: Xây local persistent quarantine store và upload ticket durable

**Files:**
- Create: `apps/cosa/knowledge_ingestion/workspace_store.py`
- Create: `packages/agent/migrations/026_local_upload_tickets.sql`
- Modify: `apps/cosa/knowledge_ingestion/contracts.py`
- Modify: `apps/cosa/api/middleware.py`
- Test: `tests/apps/cosa/knowledge_ingestion/test_workspace_store.py`

**Interfaces:**
- Produces `WorkspaceDocumentStore.issue_ticket()`, `write_upload_stream()`, `finalize_upload()`, `promote_to_vault()`, `purge_version()`.
- `WorkspaceDocumentStore` receives `root: Path`, `upload_ticket_repository`, never an S3/boto client.

- [ ] **Step 1: Write failing filesystem tests using `tmp_path`.**

```python
async def test_ticket_survives_store_recreation(tmp_path, ticket_repo):
    store = WorkspaceDocumentStore(tmp_path, ticket_repo)
    ticket = await store.issue_ticket(workspace_id="ws-a", upload_id="up-1", max_bytes=1024)
    recreated = WorkspaceDocumentStore(tmp_path, ticket_repo)
    await recreated.write_upload_stream("ws-a", "up-1", ticket.secret, [b"hello"])
    assert (await recreated.finalize_upload("ws-a", "up-1")).source_sha256

async def test_workspace_b_cannot_use_workspace_a_ticket(tmp_path, ticket_repo):
    ticket = await WorkspaceDocumentStore(tmp_path, ticket_repo).issue_ticket("ws-a", "up-1", 1024)
    with pytest.raises(UploadTicketNotFound):
        await store.write_upload_stream("ws-b", "up-1", ticket.secret, [b"x"])
```

- [ ] **Step 2: Run the test.**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/knowledge_ingestion/test_workspace_store.py -q`

Expected: FAIL because the only existing stores are in-memory and S3-compatible.

- [ ] **Step 3: Implement storage with safe local filesystem semantics.**

Use a configured absolute `COSA_WORKSPACE_STORAGE_ROOT`; reject a relative root, symlink path, `..`, invalid workspace ID or path outside root. Persist only a SHA-256 hash of the random ticket secret, expiry, max bytes and generated relative quarantine path in `agent.local_upload_tickets`. Stream to `*.partial`, enforce byte limit while streaming, `fsync`, then atomically `os.replace` into `quarantine/<workspace>/<upload>/<random>`. Set mode `0o600`; never return local path/object key to client.

```python
async def promote_to_vault(self, workspace_id: str, version_id: str, quarantine_ref: str) -> LocalObjectRef:
    source = self._resolve_workspace_ref(workspace_id, quarantine_ref)
    target = self._vault_path(workspace_id, version_id)
    await asyncio.to_thread(shutil.copyfile, source, target)
    return LocalObjectRef(relative_ref=str(target.relative_to(self._root)))
```

Recompute SHA-256 after copy and reject a mismatch before marking a version publishable.

- [ ] **Step 4: Delete S3 as an available production path.**

Remove `S3DocumentObjectStore` from composition/configuration and tests that present it as production-capable. Preserve no `boto3` fallback. `InMemoryDocumentObjectStore` remains test-only and must expose `is_test_double = True`.

- [ ] **Step 5: Run focused safety tests.**

Run:

```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/knowledge_ingestion/test_workspace_store.py \
  tests/apps/cosa/knowledge_ingestion/test_preflight.py -q
```

Expected: PASS; ticket works across store restart, symlink/traversal is rejected and no test invokes S3.

- [ ] **Step 6: Commit.**

```bash
git add apps/cosa/knowledge_ingestion packages/agent/migrations/026_local_upload_tickets.sql \
  tests/apps/cosa/knowledge_ingestion/test_workspace_store.py
git commit -m "feat(knowledge): store workspace uploads on local persistent volume"
```

---

### Task 4: Wire local storage, scanner and isolated converter into API and worker

**Files:**
- Create: `apps/cosa/knowledge_ingestion/dependencies.py`
- Modify: `apps/cosa/composition/agent_plane.py`
- Modify: `apps/cosa/composition/storage_factory.py`
- Modify: `apps/cosa/api/app.py`
- Modify: `apps/cosa/worker/main.py`
- Modify: `apps/cosa/knowledge_ingestion/handler.py`
- Test: `tests/apps/cosa/test_knowledge_production_wiring.py`, `tests/apps/cosa/worker/test_knowledge_ingestion_dispatch.py`

**Interfaces:**
- Produces `KnowledgeIngestionDependencies(store, scanner, sandbox, repository, service)`.
- `CosaAgentPlane.knowledge_ingestion_deps` is non-null for a local runtime with ingestion enabled.

- [ ] **Step 1: Add failing production wiring tests.**

```python
def test_production_rejects_missing_local_ingestion_dependencies(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(RuntimeError, match="knowledge ingestion dependencies"):
        build_knowledge_ingestion_dependencies()

async def test_worker_passes_all_dependencies_to_handler(plane, scheduled_task, mocker):
    handler = mocker.patch("apps.cosa.knowledge_ingestion.handler.execute_knowledge_ingestion_task")
    await dispatch_one_task(plane, scheduled_task)
    assert handler.call_args.kwargs["object_store"] is plane.knowledge_ingestion_deps.store
    assert handler.call_args.kwargs["sandbox"] is plane.knowledge_ingestion_deps.sandbox
```

- [ ] **Step 2: Run the tests.**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/test_knowledge_production_wiring.py tests/apps/cosa/worker/test_knowledge_ingestion_dispatch.py -q`

Expected: FAIL because app state and worker currently omit the local store, scanner and sandbox.

- [ ] **Step 3: Build a single dependency factory.**

```python
@dataclass(frozen=True)
class KnowledgeIngestionDependencies:
    store: WorkspaceDocumentStore
    scanner: DocumentMalwareScanner
    sandbox: DocumentConversionSandbox
    repository: LocalIngestionRepository
    service: KnowledgeIngestionService

def build_knowledge_ingestion_dependencies(database_url: str) -> KnowledgeIngestionDependencies: ...
```

In production require a real scanner adapter and a remote/isolated converter adapter, then call both `assert_production_scanner_ready` and `assert_production_conversion_ready`. Do not accept `FakeDocumentMalwareScanner` or `InProcessConversionSandbox` in production.

- [ ] **Step 4: Inject exactly one dependency instance per process lifecycle.**

Set `app.state.knowledge_ingestion_deps` and expose the same instance from `CosaAgentPlane`; close resources at shutdown. Worker dispatch must pass all five dependencies explicitly. `/ready` reports not-ready when the feature flag is enabled but any required dependency is absent.

- [ ] **Step 5: Run wiring and worker regression tests.**

Run:

```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/test_knowledge_production_wiring.py \
  tests/apps/cosa/worker/test_knowledge_ingestion_dispatch.py tests/apps/cosa/knowledge_ingestion -q
```

Expected: PASS; production cannot quietly use an in-process converter or fake scanner.

- [ ] **Step 6: Commit.**

```bash
git add apps/cosa/composition apps/cosa/api/app.py apps/cosa/worker/main.py \
  apps/cosa/knowledge_ingestion tests/apps/cosa/test_knowledge_production_wiring.py \
  tests/apps/cosa/worker/test_knowledge_ingestion_dispatch.py
git commit -m "feat(knowledge): wire local ingestion dependencies into runtime"
```

---

### Task 5: Make ingestion/version lifecycle local, fenced and idempotent

**Files:**
- Create: `apps/cosa/knowledge_ingestion/local_repository.py`
- Modify: `apps/cosa/knowledge_ingestion/handler.py`
- Modify: `apps/cosa/worker/main.py`
- Modify: `packages/agent/vault/lifecycle.py`
- Test: `tests/apps/cosa/knowledge_ingestion/test_local_repository.py`, `tests/apps/cosa/knowledge_ingestion/test_handler.py`

**Interfaces:**
- Produces `LocalIngestionRepository.claim()`, `record_candidate()`, `reject()`, `publish()`.
- Consumes scheduler claim token and maps it to a local ingestion attempt; returns no raw storage ref to API callers.

- [ ] **Step 1: Write failing idempotency/retry tests.**

```python
async def test_two_workers_only_one_claims_queued_upload(repo):
    first, second = await asyncio.gather(
        repo.claim("ws-a", "up-1", "task-token-a"), repo.claim("ws-a", "up-1", "task-token-b")
    )
    assert [first.claimed, second.claimed].count(True) == 1

async def test_retry_does_not_duplicate_chunks_or_version(handler_fixture):
    await execute_knowledge_ingestion_task(**handler_fixture)
    await execute_knowledge_ingestion_task(**handler_fixture)
    assert await handler_fixture["knowledge_service"].count_versions("ws-a", "doc-1") == 1
```

- [ ] **Step 2: Run the tests.**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/knowledge_ingestion/test_local_repository.py tests/apps/cosa/knowledge_ingestion/test_handler.py -q`

Expected: FAIL because state is currently owned by the platform-oriented client.

- [ ] **Step 3: Persist local state transitions and map them to Vault version lifecycle.**

`LocalIngestionRepository` must atomically lock by `(workspace_id, upload_id)`, compare the expected state, persist attempt/claim token hash and append a sanitized audit event. `record_candidate` writes `knowledge_source_id` and provenance before moving to `REVIEW_PENDING`. `publish` first copies and verifies quarantine content into Vault, then writes `PUBLISHED` for the version and source in one transaction boundary where practical; failed copy leaves the source non-published.

- [ ] **Step 4: Keep scheduler payload reference-only.**

```python
input_payload={"task_type": "knowledge_ingestion", "workspace_id": workspace_id, "upload_id": upload_id}
```

Do not place content, filename, local object ref, ticket secret or markdown in `scheduled_tasks`.

- [ ] **Step 5: Run state-machine and regression tests.**

Run:

```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/knowledge_ingestion/test_local_repository.py \
  tests/apps/cosa/knowledge_ingestion/test_handler.py tests/agent/vault/test_lifecycle.py -q
```

Expected: PASS; duplicate/reclaimed task cannot produce a second source version.

- [ ] **Step 6: Commit.**

```bash
git add apps/cosa/knowledge_ingestion apps/cosa/worker/main.py packages/agent/vault/lifecycle.py \
  tests/apps/cosa/knowledge_ingestion/test_local_repository.py tests/apps/cosa/knowledge_ingestion/test_handler.py
git commit -m "feat(knowledge): persist local fenced ingestion lifecycle"
```

---

### Task 6: Implement a reusable authorization resolver and review/publish policy

**Files:**
- Create: `apps/cosa/knowledge_ingestion/authorization.py`
- Modify: `apps/cosa/auth/dependency.py`
- Modify: `apps/cosa/api/vault_routes.py`
- Modify: `apps/cosa/api/knowledge_routes.py`
- Modify: `services/cosa/handlers/document-ingestion.handler.ts`
- Test: `tests/apps/cosa/knowledge_ingestion/test_authorization.py`, `tests/apps/cosa/api/test_vault_permissions.py`, `services/cosa/tests/document-ingestion.test.ts`

**Interfaces:**
- Produces `KnowledgeAuthorization.resolve(identity, document_id) -> KnowledgeAccessDecision`.
- `KnowledgeAccessDecision` has `discover`, `read`, `download`, `manage`, `review`, `publish`; false decisions are explicit and auditable.

- [ ] **Step 1: Write the role matrix tests.**

```python
@pytest.mark.parametrize(("role", "expected"), [("founder", True), ("member", False)])
async def test_restricted_document_read(role, expected, authorization, restricted_doc):
    decision = await authorization.resolve(identity(role), restricted_doc.document_id)
    assert decision.read is expected

async def test_member_can_read_only_directly_granted_document(authorization, private_doc):
    await grant_user(private_doc, "member-1", "read")
    assert (await authorization.resolve(identity("member", "member-1"), private_doc.document_id)).read
```

- [ ] **Step 2: Run role matrix tests.**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/knowledge_ingestion/test_authorization.py tests/apps/cosa/api/test_vault_permissions.py -q`

Expected: FAIL because current routes only check membership/operator status.

- [ ] **Step 3: Implement deterministic grant resolution.**

Resolve founder/co-founder/admin workspace policy first, then explicit user/team/role grants, then classification policy. Return a decision with `policy_version` and a stable denial code; do not infer permission from document title, prompt text or client-provided role. Unauthorized document IDs return `404` from public routes.

- [ ] **Step 4: Gate every mutation.**

Require `manage` for ACL, archive and purge; `review` plus assigned grant for review; `publish` for publication. Upload creates a private document for a member unless an authorized manager explicitly requests workspace/role visibility. Mirror this rule in the local execution-plane handler; plain membership is insufficient.

- [ ] **Step 5: Run API and TypeScript policy tests.**

Run:

```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/knowledge_ingestion/test_authorization.py tests/apps/cosa/api/test_vault_permissions.py -q
cd services/cosa && npx vitest run tests/document-ingestion.test.ts
```

Expected: PASS; founder has workspace-wide read, member cannot enumerate or review another member's source.

- [ ] **Step 6: Commit.**

```bash
git add apps/cosa/knowledge_ingestion/authorization.py apps/cosa/auth/dependency.py \
  apps/cosa/api/vault_routes.py apps/cosa/api/knowledge_routes.py \
  services/cosa/handlers/document-ingestion.handler.ts tests/apps/cosa/knowledge_ingestion/test_authorization.py \
  tests/apps/cosa/api/test_vault_permissions.py services/cosa/tests/document-ingestion.test.ts
git commit -m "feat(vault): enforce role and document grants"
```

---

### Task 7: Reopen Vault REST API with real local semantics

**Files:**
- Modify: `apps/cosa/api/vault_schemas.py`
- Modify: `apps/cosa/api/vault_routes.py`
- Create: `tests/apps/cosa/api/test_vault_document_routes.py`
- Modify: `tests/apps/cosa/api/test_vault_routes.py`

**Interfaces:**
- Produces `POST /agent/vault/documents`, `PUT /agent/vault/uploads/{upload_id}/content`, `POST /agent/vault/uploads/{upload_id}/complete`, detail/list/review/publish/archive/purge routes.
- Consumes `KnowledgeAuthorization`, `WorkspaceDocumentStore`, `LocalIngestionRepository`.

- [ ] **Step 1: Replace 501-only tests with real contract tests.**

```python
async def test_create_upload_then_complete_queues_local_ingestion(client, founder_headers):
    created = await client.post("/agent/vault/documents", headers=founder_headers, json={"title": "Plan", "media_type": "text/plain"})
    assert created.status_code == 201
    upload = await client.put(created.json()["upload_url"], content=b"local plan")
    assert upload.status_code == 204
    complete = await client.post(f"/agent/vault/uploads/{created.json()['upload_id']}/complete", headers=founder_headers)
    assert complete.json()["state"] == "QUEUED"
```

- [ ] **Step 2: Run route tests to establish the failure.**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/api/test_vault_document_routes.py tests/apps/cosa/api/test_vault_routes.py -q`

Expected: FAIL because all Vault routes return `501`.

- [ ] **Step 3: Add strict schemas and stream endpoint.**

`CreateDocumentRequest` must accept title, media type, classification and requested visibility; it must not accept workspace, object path, checksum or size. The upload endpoint authenticates the one-time ticket plus workspace and uses `request.stream()`, never `await request.body()`. Return opaque upload URL and expiry only.

- [ ] **Step 4: Implement list/detail and lifecycle commands.**

List/detail query repository methods already scoped by authorization. Review/publish commands include reason and idempotency key. Archive/purge schedule background durable work and return `202`; never delete a file in the HTTP request. Keep legacy `/agent/vault/retrieval/query` unavailable until Task 8 introduces the authorized contract.

- [ ] **Step 5: Run route/auth regression.**

Run:

```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/api/test_vault_document_routes.py \
  tests/apps/cosa/api/test_vault_permissions.py tests/apps/cosa/api/test_vault_routes.py -q
make route-auth-allowlist-check
```

Expected: PASS; no response exposes local paths, ticket secrets, object refs or fencing tokens.

- [ ] **Step 6: Commit.**

```bash
git add apps/cosa/api/vault_schemas.py apps/cosa/api/vault_routes.py \
  tests/apps/cosa/api/test_vault_document_routes.py tests/apps/cosa/api/test_vault_routes.py
git commit -m "feat(vault): add local document upload and lifecycle API"
```

---

### Task 8: Build authorization-first retrieval and citations

**Files:**
- Modify: `packages/agent/knowledge/providers/postgres.py`
- Modify: `packages/agent/knowledge/service.py`
- Modify: `apps/cosa/capabilities/knowledge_read.py`
- Create: `apps/cosa/capabilities/enterprise_knowledge_read.py`
- Modify: `apps/cosa/composition/capability_registration.py`
- Create: `tests/agent/knowledge/test_authorized_retrieval.py`
- Create: `tests/apps/cosa/capabilities/test_enterprise_knowledge_read.py`

**Interfaces:**
- Produces `retrieve_authorized_citations(workspace_id, principal_id, role_ids, query, limit) -> list[CitationProvenance]`.
- Produces capability id `knowledge.enterprise.read`.

- [ ] **Step 1: Write leakage tests before ranking tests.**

```python
async def test_retrieval_never_returns_restricted_chunk_to_member(store):
    await store.save_published_chunk("ws-a", "restricted", "quarterly salary table")
    results = await store.retrieve_authorized_citations("ws-a", "member-1", {"member"}, "salary", 5)
    assert results == []

async def test_founder_receives_citation_with_version_provenance(store):
    results = await store.retrieve_authorized_citations("ws-a", "founder-1", {"founder"}, "salary", 5)
    assert results[0].vault_version_id is not None
```

- [ ] **Step 2: Run focused retrieval tests.**

Run: `AGENT_TEST_DATABASE_URL="$AGENT_TEST_DATABASE_URL" PYTHONPATH=. .venv/bin/python -m pytest tests/agent/knowledge/test_authorized_retrieval.py tests/apps/cosa/capabilities/test_enterprise_knowledge_read.py -q`

Expected: FAIL because current query filters only workspace and content.

- [ ] **Step 3: Query only already-authorized, published versions.**

Build the allowed document set in SQL by joining Vault version state, current grants/classification policy and the current principal/role IDs. Apply that CTE before `ILIKE` or pgvector distance ordering. Return no title/score/count for denied sources. Filter out archived/purged versions even if old chunks remain during asynchronous deletion.

- [ ] **Step 4: Make capability output prompt-safe and attributable.**

```python
return {
    "citations": [
        {"document_id": c.document_id, "vault_version_id": c.vault_version_id,
         "chunk_id": c.chunk_id, "section": c.page_or_section, "snippet": c.snippet,
         "score": c.similarity_score}
        for c in citations
    ],
    "policy_version": decision.policy_version,
}
```

Declare retrieved text as untrusted reference material in the capability description; no chunk may grant instructions or capability authority to the model.

- [ ] **Step 5: Run retrieval, tenancy and capability tests.**

Run:

```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/agent/knowledge/test_authorized_retrieval.py \
  tests/apps/cosa/capabilities/test_enterprise_knowledge_read.py -q
make tenancy-check
```

Expected: PASS; member cannot retrieve a denied source even when its chunk is the strongest lexical/semantic match.

- [ ] **Step 6: Commit.**

```bash
git add packages/agent/knowledge apps/cosa/capabilities apps/cosa/composition/capability_registration.py \
  tests/agent/knowledge/test_authorized_retrieval.py tests/apps/cosa/capabilities/test_enterprise_knowledge_read.py
git commit -m "feat(knowledge): retrieve published citations with authorization"
```

---

### Task 9: Expose persisted local GraphQL reads for workspace context

**Files:**
- Create: `apps/cosa/graphql/schema.py`
- Create: `apps/cosa/graphql/persisted_operations.py`
- Create: `apps/cosa/graphql/resolvers.py`
- Create: `apps/cosa/api/graphql_routes.py`
- Modify: `apps/cosa/api/app.py`
- Create: `tests/apps/cosa/graphql/test_workspace_context.py`
- Create: `tests/apps/cosa/api/test_graphql_routes.py`

**Interfaces:**
- Produces `POST /agent/graphql` accepting `GraphQLRequest(operation_id: Literal["workspaceContext", "enterpriseKnowledgeSearch"], variables: dict)`.
- Produces `execute_persisted_operation(operation_id, variables, identity) -> dict`; it does not accept a GraphQL document string.
- Consumes `KnowledgeAuthorization`, `retrieve_authorized_citations` and read-only Company service capability adapters.

- [ ] **Step 1: Write failing persisted-operation tests.**

```python
async def test_founder_workspace_context_includes_permitted_business_and_knowledge(graphql_client, founder_headers):
    response = await graphql_client.post("/agent/graphql", headers=founder_headers, json={
        "operationId": "workspaceContext", "variables": {"question": "rủi ro quý này"},
    })
    assert response.status_code == 200
    assert response.json()["data"]["workspaceContext"]["citations"]

async def test_member_cannot_submit_raw_query_or_see_denied_source(graphql_client, member_headers):
    raw = await graphql_client.post("/agent/graphql", headers=member_headers, json={"query": "{ secrets }"})
    assert raw.status_code == 422
    result = await graphql_client.post("/agent/graphql", headers=member_headers, json={
        "operationId": "enterpriseKnowledgeSearch", "variables": {"query": "lương"},
    })
    assert result.json()["data"]["enterpriseKnowledgeSearch"]["citations"] == []
```

- [ ] **Step 2: Run the GraphQL tests.**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/graphql/test_workspace_context.py tests/apps/cosa/api/test_graphql_routes.py -q`

Expected: FAIL because no local GraphQL BFF or persisted-operation registry exists.

- [ ] **Step 3: Define only typed, read-only persisted operations.**

```python
PERSISTED_OPERATIONS: dict[str, PersistedOperation] = {
    "workspaceContext": WorkspaceContextOperation(),
    "enterpriseKnowledgeSearch": EnterpriseKnowledgeSearchOperation(),
}

async def execute_persisted_operation(
    operation_id: str, variables: dict[str, object], identity: AuthenticatedIdentity
) -> dict[str, object]:
    operation = PERSISTED_OPERATIONS.get(operation_id)
    if operation is None:
        raise HTTPException(status_code=404, detail="operation not found")
    return await operation.execute(variables, identity)
```

`WorkspaceContextOperation` calls read-only, capability-backed business adapters and authorized knowledge retrieval. `EnterpriseKnowledgeSearchOperation` calls only `retrieve_authorized_citations`. Each resolver passes identity workspace/principal/role into the service; it never trusts a workspace variable and never opens local storage paths.

- [ ] **Step 4: Add GraphQL guardrails and audit.**

Reject `query`, `mutation`, `subscription`, unknown operation IDs, unknown variables, oversized string variables and depth/selection inputs because selection is server-owned. Make the route `POST` only; limit page size to 20. Audit operation ID, principal, policy version, returned citation IDs and duration, never returned text or business payload. No mutation resolver is registered.

- [ ] **Step 5: Run authorization and GraphQL regression tests.**

Run:

```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/graphql/test_workspace_context.py \
  tests/apps/cosa/api/test_graphql_routes.py tests/agent/knowledge/test_authorized_retrieval.py -q
make route-auth-allowlist-check
```

Expected: PASS; founder receives only workspace-local authorized context, member has no source enumeration path, and raw GraphQL is rejected.

- [ ] **Step 6: Commit.**

```bash
git add apps/cosa/graphql apps/cosa/api/graphql_routes.py apps/cosa/api/app.py \
  tests/apps/cosa/graphql/test_workspace_context.py tests/apps/cosa/api/test_graphql_routes.py
git commit -m "feat(agent): add local persisted GraphQL workspace read context"
```

---

### Task 10: Bind founder chat context to the governed GraphQL capability

**Files:**
- Modify: `apps/cosa/agents/specs.py`
- Modify: `apps/cosa/worker/handlers.py`
- Modify: `packages/agent_integrations/openai_agents_sdk/kernel.py`
- Create: `apps/cosa/capabilities/workspace_context_read.py`
- Modify: `apps/cosa/composition/capability_registration.py`
- Modify: `tests/apps/cosa/worker/test_handlers.py`
- Create: `tests/apps/cosa/test_founder_knowledge_context.py`

**Interfaces:**
- Consumes exact capability ref `workspace.context.read` through AgentSpec/gateway; that capability executes persisted local GraphQL operations and may use `knowledge.enterprise.read` internally.
- Produces a role-scoped read context and citations in run artifacts/events without direct repository access from kernel.

- [ ] **Step 1: Write a failing founder/member run test.**

```python
async def test_founder_assistant_can_request_workspace_knowledge_via_gateway(run_fixture):
    result = await run_fixture.run(profile="founder_assistant", role="founder", prompt="Tóm tắt kế hoạch quý")
    assert "workspace.context.read" in result.capability_invocations

async def test_member_run_context_excludes_denied_citation(run_fixture):
    result = await run_fixture.run(profile="founder_assistant", role="member", prompt="Lương ban điều hành")
    assert "quarterly salary table" not in result.prompt_context
```

- [ ] **Step 2: Run the run tests.**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/test_founder_knowledge_context.py tests/apps/cosa/worker/test_handlers.py -q`

Expected: FAIL because `founder_assistant` aliases the Operations spec without the enterprise knowledge capability.

- [ ] **Step 3: Add the capability through the existing registry/gateway path.**

Create `workspace.context.read` as a gateway capability whose input is `{operation_id, variables}` and whose handler calls `execute_persisted_operation`. Do not instantiate a GraphQL client, repository or store inside kernel code. The gateway context must carry authenticated principal, workspace and role IDs from the durable run payload. Create a distinct founder spec only if the product role genuinely differs; otherwise add this exact capability ref to the already-resolved spec according to policy.

- [ ] **Step 4: Persist an audit-safe context record.**

Record run ID, principal, policy version and citation IDs; do not persist full retrieved text in event payload/log. The client response shows citations only when caller still passes authorization at read time.

- [ ] **Step 5: Run run, kernel and capability regressions.**

Run:

```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/test_founder_knowledge_context.py \
  tests/apps/cosa/worker/test_handlers.py tests/agent/kernel/test_openai_agents_kernel.py -q
```

Expected: PASS; the model has no direct storage/DB tool and context remains role-filtered.

- [ ] **Step 6: Commit.**

```bash
git add apps/cosa/agents/specs.py apps/cosa/worker/handlers.py packages/agent_integrations/openai_agents_sdk/kernel.py \
  tests/apps/cosa/test_founder_knowledge_context.py tests/apps/cosa/worker/test_handlers.py
git commit -m "feat(agent): provide governed GraphQL context to founder chat"
```

---

### Task 11: Add retention, revoke and physical purge without stale retrieval

**Files:**
- Create: `apps/cosa/knowledge_ingestion/purge.py`
- Modify: `apps/cosa/knowledge_ingestion/local_repository.py`
- Modify: `apps/cosa/worker/main.py`
- Modify: `apps/cosa/api/vault_routes.py`
- Create: `tests/apps/cosa/knowledge_ingestion/test_purge.py`
- Test: `tests/apps/cosa/api/test_vault_document_routes.py`

**Interfaces:**
- Produces `request_purge() -> PurgeRequest`, `execute_purge_task()` and `revoke_access()`.
- Consumes `legal_hold`, `retention_until`, local storage ref and source/version IDs.

- [ ] **Step 1: Write failing revoke/purge tests.**

```python
async def test_revoke_removes_chunk_from_retrieval_before_physical_delete(stack):
    await stack.revoke_access("ws-a", "doc-1", "member-1")
    assert await stack.retrieve_as("member-1", "plan") == []

async def test_legal_hold_blocks_purge(stack):
    await stack.set_legal_hold("ws-a", "doc-1", True)
    with pytest.raises(PurgeBlocked, match="legal hold"):
        await stack.request_purge("ws-a", "doc-1", "founder-1")
```

- [ ] **Step 2: Run the test.**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/knowledge_ingestion/test_purge.py -q`

Expected: FAIL because there is no durable purge flow.

- [ ] **Step 3: Implement two-stage purge.**

On request, authorize `manage`, set document/version to `PURGE_PENDING` and immediately exclude it in retrieval SQL. Scheduler then removes embeddings/chunks/source rows, deletes local Vault/quarantine file with a workspace-bound reference, and writes `PURGED` audit event. Failed delete retries safely; no retry may resurrect a source.

- [ ] **Step 4: Add archive/version replacement behavior.**

Publishing a newer version switches only the document's active published version after source persistence and authorization metadata are committed. Archive preserves audit/provenance but excludes the version from retrieval.

- [ ] **Step 5: Run purge, retrieval and API tests.**

Run:

```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/knowledge_ingestion/test_purge.py \
  tests/agent/knowledge/test_authorized_retrieval.py tests/apps/cosa/api/test_vault_document_routes.py -q
```

Expected: PASS; revocation and purge remove results immediately, while physical cleanup remains durable/retryable.

- [ ] **Step 6: Commit.**

```bash
git add apps/cosa/knowledge_ingestion/purge.py apps/cosa/knowledge_ingestion/local_repository.py \
  apps/cosa/worker/main.py apps/cosa/api/vault_routes.py tests/apps/cosa/knowledge_ingestion/test_purge.py
git commit -m "feat(vault): revoke and purge local knowledge safely"
```

---

### Task 12: Release the frontend only after backend contract and capability gate

**Files:**
- Modify: `shared/contracts/mvp-surface.json`
- Regenerate: `apps/cosa/api/mvp_contracts_generated.py`, `frontend/lib/core/network/mvp_endpoints.g.dart`
- Modify: `frontend/lib/modules/vault/controllers/vault_controller.dart`
- Modify: `frontend/lib/modules/vault/views/vault_view.dart`
- Create: `frontend/lib/modules/vault/services/vault_service.dart`
- Modify: `frontend/test/modules/vault/vault_view_test.dart`
- Create: `frontend/test/modules/vault/vault_service_test.dart`

**Interfaces:**
- Consumes the real Vault API only through `MvpRequestClient`.
- Produces status/list/upload/review UI that never renders a source forbidden by backend.

- [ ] **Step 1: Write failing frontend contract and role-state tests.**

```dart
testWidgets('member sees only documents returned by the authorized backend', (tester) async {
  fakeVaultService.documents = [memberDocument];
  await tester.pumpWidget(const MaterialApp(home: VaultView()));
  expect(find.text('Board plan'), findsNothing);
  expect(find.text(memberDocument.title), findsOneWidget);
});

test('upload uses the opaque local upload URL from the server', () async {
  await service.upload(createdUpload, bytes);
  expect(recordedRequests.single.url.path, contains('/agent/vault/uploads/'));
});
```

- [ ] **Step 2: Run the frontend test.**

Run: `cd frontend && flutter test test/modules/vault/vault_view_test.dart test/modules/vault/vault_service_test.dart -r compact`

Expected: FAIL because the module remains intentionally unavailable.

- [ ] **Step 3: Generate and consume the canonical endpoint contract.**

Edit only `shared/contracts/mvp-surface.json`, mark endpoints enabled only after their backend tests are green, then run `node scripts/gen-mvp-contracts.mjs`. `VaultService` uses typed `MvpEndpoint`; no literal `/vault/*` legacy route and no guessed client-side permissions.

- [ ] **Step 4: Implement UI states truthfully.**

Show `UPLOADING`, `QUEUED`, `VALIDATING`, `REVIEW_PENDING`, `PUBLISHED`, `REJECTED`, `ARCHIVED`, `PURGE_PENDING`. Render review/publish/manage controls only when the backend response includes the corresponding action grant; a `403/404` refreshes the list rather than retaining stale document content.

- [ ] **Step 5: Run frontend and API contract gates.**

Run:

```bash
cd frontend && flutter test test/modules/vault/vault_view_test.dart test/modules/vault/vault_service_test.dart -r compact
cd .. && make frontend-api-contract-check
```

Expected: PASS; frontend cannot call retired fake routes or display fabricated retrieval results.

- [ ] **Step 6: Commit.**

```bash
git add shared/contracts/mvp-surface.json apps/cosa/api/mvp_contracts_generated.py \
  frontend/lib/core/network/mvp_endpoints.g.dart frontend/lib/modules/vault frontend/test/modules/vault
git commit -m "feat(frontend): release governed local Vault workspace"
```

---

### Task 13: Prove local durability, isolation and release readiness

**Files:**
- Create: `tests/e2e/test_local_knowledge_workspace.py`
- Create: `docs/operations/local-knowledge-runbook.md`
- Modify: `docker-compose.yml`
- Modify: `Makefile`
- Test: `tests/e2e/test_local_knowledge_workspace.py`

**Interfaces:**
- Produces `make local-knowledge-e2e` running disposable Postgres plus a mounted local storage directory and local execution plane.
- Produces a runbook with backup/restore, scanner outage, converter outage, disk-full, revoke/purge and node-restart procedures.

- [ ] **Step 1: Write the process-restart E2E test.**

```python
def test_local_upload_survives_api_and_worker_restart(local_stack):
    upload = local_stack.create_upload_as("founder", b"Quarter plan")
    local_stack.restart_api_and_worker()
    local_stack.complete_upload(upload.id)
    local_stack.wait_for_state(upload.id, "REVIEW_PENDING")
    local_stack.publish(upload.id)
    assert local_stack.retrieve_as("founder", "Quarter plan").citations
```

Add a second scenario proving `member-b` receives neither title, snippet, score nor citation of a founder-only document; add a third proving raw file, chunk and embedding never arrive at a mock platform endpoint.

- [ ] **Step 2: Run E2E and confirm failure before stack changes.**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/e2e/test_local_knowledge_workspace.py -q`

Expected: FAIL because compose/runtime has no persistent local knowledge volume and full wiring.

- [ ] **Step 3: Add a local storage volume and safe worker deployment configuration.**

Mount `COSA_WORKSPACE_STORAGE_ROOT` only into `cosa-api`, `cosa-worker` and the isolated conversion/scanner boundary of the same workspace runtime. Do not mount it into Platform Control Plane containers. Configure read-only where a component only needs reads, non-root users, disk quota/alert threshold and converter network deny. Keep the existing Compose development warning; production evidence must show actual OS/container enforcement rather than only environment attestations.

- [ ] **Step 4: Document operational recovery.**

The runbook specifies: backup local Postgres + Vault volume as a consistency pair; restore rehearsal; reject scanner-unavailable documents; restart-safe ticket/job behavior; disk-full fail-closed behavior; role revocation verification; and retention/legal-hold purge approval. It must explicitly state that copying the volume to Platform/VPS is not a recovery procedure.

- [ ] **Step 5: Run the complete release evidence suite.**

Run:

```bash
make local-knowledge-e2e
make agent-test
make apps-cosa-test
make services-test
make frontend-test
make frontend-analyze
make tenancy-check
make migration-compat-check
```

Expected: every command exits 0. If an environment prerequisite prevents a command, record the exact command, output, missing prerequisite and do not enable the feature flag.

- [ ] **Step 6: Commit.**

```bash
git add tests/e2e/test_local_knowledge_workspace.py docs/operations/local-knowledge-runbook.md docker-compose.yml Makefile
git commit -m "test(knowledge): verify local-first durability and authorization"
```

## Coverage self-review

| Design requirement | Implemented by |
|---|---|
| Local storage, no S3 authority | Tasks 1, 3, 4, 13 |
| Vault canonical version/provenance | Tasks 2, 5 |
| Founder all / member limited | Tasks 2, 6, 8, 9 |
| REST writes + audit | Tasks 5, 6, 7, 10 |
| Retrieval filtered before ranking | Task 8 |
| Agent uses local GraphQL but has no direct DB/filesystem read | Tasks 8, 9, 10 |
| Review/publish separation | Tasks 5, 6, 7 |
| Revocation, retention, purge | Task 11 |
| UI only after real backend | Task 12 |
| Real restart/durability evidence | Task 13 |

No task requires an S3 adapter, a cloud bucket, a raw document payload in scheduler, or a direct agent database/filesystem tool.
