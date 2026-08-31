# Full MVP Vault and Knowledge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a workspace-isolated Vault UI backed by durable document/version/ingestion/knowledge records and actual configured object storage, with no synthetic files, search results or graph nodes.

**Architecture:** The Agent Platform owns Vault metadata and knowledge state. The existing `WorkspaceObjectStore`, key/quota/host catalog, knowledge store and ingestion lifecycle are reused rather than replaced. This plan adds durable Vault document/version metadata that links each version to an actual object ref and optional knowledge source, completes workspace-scoped Postgres/RLS enforcement, and exposes FastAPI `/agent/vault/*` contracts. Flutter receives typed document, lifecycle and provenance data; direct legacy `/vault/*` calls and fabricated empty graph response maps are removed.

**Tech Stack:** Python/FastAPI/Pydantic, SQLAlchemy/PostgreSQL/pgvector, existing MinIO/S3-compatible ingestion store and local workspace store, Flutter/Dart/GetX, pytest and Flutter test.

**Spec:** `docs/superpowers/specs/2026-08-31-full-mvp-contract-first-truth-only-design.md`

## Global Constraints

- Complete the Foundation plan before enabling Vault capabilities.
- A document is visible only after a durable `vault.documents` record and referenced object version exist in the correct workspace. Search/retrieval is available only for real indexed sources.
- The configured production store is `S3DocumentObjectStore`/MinIO or another configured server-owned object store; local development may use `LocalFilesystemWorkspaceStore`. `InMemoryDocumentObjectStore` is test-only and production must fail closed when storage configuration is absent.
- All storage/read/search/retrieve APIs bind both `workspace_id` and document/object/source ID. Never accept a raw filesystem path or object key from Flutter.
- Document state uses the existing `DocumentState` machine; SOP procedural selection remains `ACTIVE` only. A failed ingestion stays failed and never produces a mocked document/search hit.
- Existing workspace object/key/backup behavior from M3 remains intact. This plan does not weaken traversal, symlink, checksum, encryption, quota, backup or cross-workspace guards.
- Migration number `023_vault_document_contract_and_rls` is reserved; it follows Workforce migration 022 and has a safe down file.

---

## File map

| File | Responsibility |
|---|---|
| `packages/agent/migrations/023_vault_document_contract_and_rls.sql` | Vault document/version metadata tables, tenant indexes/composite constraints and RLS policies |
| `packages/agent/migrations/023_vault_document_contract_and_rls.down.sql` | Reverses only new metadata/RLS policies after safe session cleanup |
| `packages/agent/vault/models.py` | Durable document/version/list/search record types |
| `packages/agent/vault/repository.py` | Workspace-bound document/version metadata operations and RLS session context |
| `packages/agent/vault/object_store.py` | Reuse exact `WorkspaceObjectStore` refs; add only an adapter required by real Vault metadata writes |
| `packages/agent/knowledge/providers/postgres.py` | Ensures every get/list/search query includes workspace and transaction RLS context |
| `apps/cosa/composition/agent_plane.py` | Wires durable Vault repository and configured object store; rejects missing production wiring |
| `apps/cosa/api/vault_schemas.py` | Pydantic DTOs for document/list/detail/search/version actions |
| `apps/cosa/api/vault_routes.py` | `/agent/vault/*` route family |
| `apps/cosa/api/app.py` | Registers Vault router |
| `apps/cosa/api/routes.py` | Reuses existing `/agent/knowledge/uploads/*` lifecycle as the only binary-upload path |
| `tests/agent/vault/test_repository.py` | Real database/RLS/document version tests |
| `tests/agent/knowledge/providers/test_postgres_knowledge_store.py` | Workspace-scoped vector/search regression tests |
| `tests/apps/cosa/test_vault_routes.py` | FastAPI response/auth/ingestion-state tests |
| `frontend/lib/modules/vault/models/vault_models.dart` | Typed document/version/search/graph DTOs |
| `frontend/lib/modules/vault/services/vault_mvp_service.dart` | Typed contract client |
| `frontend/lib/modules/vault/services/vault_service.dart` | Compatibility delegate with legacy `/vault/*` paths removed |
| `frontend/lib/modules/vault/controllers/vault_controller.dart` | Result-aware document/knowledge state |
| `frontend/lib/modules/vault/views/**/*.dart` | Honest empty, processing, failed, indexed and unavailable states |
| `frontend/test/vault_mvp_service_test.dart` | Client status/error tests |
| `frontend/test/vault_views_test.dart` | Vault lifecycle/search/graph widget tests |

## Task 1: Persist Vault document/version metadata and bind every query to workspace

**Files:**

- Create: `packages/agent/migrations/023_vault_document_contract_and_rls.sql`
- Create: `packages/agent/migrations/023_vault_document_contract_and_rls.down.sql`
- Create: `packages/agent/vault/models.py`
- Create: `packages/agent/vault/repository.py`
- Modify: `packages/agent/knowledge/providers/postgres.py`
- Test: `tests/agent/vault/test_repository.py`
- Test: `tests/agent/knowledge/providers/test_postgres_knowledge_store.py`

**Interfaces:**

- Produces `VaultDocumentRecord`, `VaultDocumentVersionRecord`, `VaultRepository.create_draft`, `append_version`, `get_document`, `list_documents`, `link_knowledge_source`, and `search_workspace`.
- All methods require `workspace_id` as their first business argument; no repository exposes `get_document(id)` without workspace.

- [ ] **Step 1: Write real-Postgres isolation/lifecycle tests.**

  ```python
  @pytest.mark.integration
  async def test_document_version_requires_its_workspace(agent_db, workspace_store) -> None:
      repo = VaultRepository(agent_db, workspace_store)
      doc = await repo.create_draft(workspace_id="1001", title="Customer notes", content=b"customer supplied notes", actor_id="user:1")
      assert (await repo.get_document("1001", doc.document_id)).state == DocumentState.QUARANTINED
      assert await repo.get_document("2002", doc.document_id) is None

  @pytest.mark.integration
  async def test_vector_search_never_returns_workspace_b_chunk(agent_db) -> None:
      await index_real_document(agent_db, workspace_id="1001", text="only A")
      await index_real_document(agent_db, workspace_id="2002", text="only B")
      assert all(hit.workspace_id == "1001" for hit in await search_real_index(agent_db, workspace_id="1001", query="only"))
  ```

- [ ] **Step 2: Run tests and verify the new metadata contract is absent.**

  Run: `PYTHONPATH=$(pwd) AGENT_MIGRATION_TEST_DATABASE_URL="$AGENT_MIGRATION_TEST_DATABASE_URL" python3 -m pytest tests/agent/vault/test_repository.py tests/agent/knowledge/providers/test_postgres_knowledge_store.py -q`

  Expected: FAIL for missing repository/migration; explicit real-database SKIP is allowed only when the environment cannot provide Postgres.

- [ ] **Step 3: Add metadata schema, indexes and RLS.**

  Create `vault.documents` and `vault.document_versions` with only server-owned identifiers and refs:

  ```sql
  CREATE TABLE vault.documents (
    document_id UUID PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    title TEXT NOT NULL CHECK (length(trim(title)) > 0),
    kind TEXT NOT NULL,
    state TEXT NOT NULL,
    current_version_id UUID NULL,
    knowledge_source_id UUID NULL,
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (workspace_id, document_id)
  );
  CREATE TABLE vault.document_versions (
    version_id UUID PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    document_id UUID NOT NULL,
    object_ref JSONB NOT NULL,
    checksum_sha256 TEXT NOT NULL,
    size_bytes BIGINT NOT NULL CHECK (size_bytes >= 0),
    source_uri TEXT NOT NULL,
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (workspace_id, version_id),
    FOREIGN KEY (workspace_id, document_id) REFERENCES vault.documents(workspace_id, document_id)
  );
  ```

  Add `(workspace_id, state, updated_at DESC)` and `(workspace_id, document_id)` indexes. Enable RLS on Vault and tenant-owned knowledge tables; policies compare `workspace_id` to `current_setting('cosa.workspace_id', true)`. The repository begins each transaction with `SET LOCAL cosa.workspace_id = :workspace_id` and resets naturally at transaction end. Keep explicit `WHERE workspace_id = :workspace_id` predicates as defense in depth.

- [ ] **Step 4: Implement repository writes against the real object store.**

  `create_draft` obtains UUIDs server-side, writes content through `WorkspaceObjectStore.put`, persists the returned structured `ObjectRef`, checksum and source URI, and records `QUARANTINED`. It never accepts a blob/object path. `append_version` requires a matching document workspace and expected current version; mismatches return conflict. `link_knowledge_source` runs only after the existing ingestion pipeline has produced an actual source ID and state. Do not index/return a document on failed ingestion.

- [ ] **Step 5: Verify migration apply/rollback and focused tests.**

  Run:

  ```bash
  PYTHONPATH=$(pwd) AGENT_MIGRATION_DATABASE_URL="$AGENT_MIGRATION_DATABASE_URL" python3 -m packages.agent.scripts.migrate
  PYTHONPATH=$(pwd) AGENT_MIGRATION_DATABASE_URL="$AGENT_MIGRATION_DATABASE_URL" python3 -m packages.agent.scripts.migrate --down 1
  PYTHONPATH=$(pwd) AGENT_MIGRATION_DATABASE_URL="$AGENT_MIGRATION_DATABASE_URL" python3 -m packages.agent.scripts.migrate
  PYTHONPATH=$(pwd) python3 -m pytest tests/agent/vault/test_repository.py tests/agent/knowledge/providers/test_postgres_knowledge_store.py -q
  ```

  Expected: all succeed; cross-workspace document/get/search attempts return no data/404 rather than another tenant's metadata.

- [ ] **Step 6: Commit durable Vault metadata.**

  ```bash
  git add packages/agent/migrations/023_vault_document_contract_and_rls.* packages/agent/vault packages/agent/knowledge/providers/postgres.py tests/agent/vault tests/agent/knowledge/providers/test_postgres_knowledge_store.py
  git commit -m "feat: persist workspace vault documents"
  ```

## Task 2: Wire real storage/ingestion and expose canonical Vault routes

**Files:**

- Modify: `apps/cosa/composition/agent_plane.py`
- Create: `apps/cosa/api/vault_schemas.py`
- Create: `apps/cosa/api/vault_routes.py`
- Modify: `apps/cosa/api/app.py`
- Modify: `apps/cosa/api/routes.py`
- Test: `tests/apps/cosa/test_vault_routes.py`
- Test: `tests/apps/cosa/test_knowledge_production_wiring.py`

**Interfaces:**

- Produces canonical routes:

  ```text
  GET    /agent/vault/documents
  POST   /agent/vault/documents
  GET    /agent/vault/documents/:documentId
  PUT    /agent/vault/documents/:documentId
  GET    /agent/vault/documents/:documentId/versions
  GET    /agent/vault/knowledge
  GET    /agent/vault/knowledge/:sourceId/backlinks
  GET    /agent/vault/search
  GET    /agent/vault/graph
  POST   /agent/vault/documents/:documentId/promote
  ```

- Existing `POST /agent/knowledge/uploads` and completion/review routes remain the binary upload/ingestion path; they create/link a Vault document after durable finalize, not an in-memory record.

- [ ] **Step 1: Write failing API tests for each truth state.**

  ```python
  async def test_failed_ingestion_is_returned_as_failed_not_as_searchable_document(client, identity, failed_document) -> None:
      response = await client.get(f"/agent/vault/documents/{failed_document.document_id}", headers=identity.headers)
      assert response.status_code == 200
      assert response.json()["data"]["state"] == "FAILED"
      search = await client.get("/agent/vault/search?q=failed", headers=identity.headers)
      assert search.json()["data"] == []
      assert search.json()["meta"]["data_state"] == "empty"

  async def test_vault_route_rejects_raw_path_and_other_workspace(client, identity_b, document_a) -> None:
      response = await client.get("/agent/vault/documents/../../etc/passwd", headers=identity_b.headers)
      assert response.status_code in {400, 404}
  ```

- [ ] **Step 2: Run route tests and verify missing routes fail.**

  Run: `PYTHONPATH=$(pwd) python3 -m pytest tests/apps/cosa/test_vault_routes.py -q`

  Expected: FAIL before `vault_routes.py` is registered.

- [ ] **Step 3: Wire production dependencies and routes.**

  Add `vault_repository` and `workspace_object_store` to `CosaAgentPlane`; production composition selects configured `S3DocumentObjectStore`/MinIO for ingestion and the configured durable workspace store for version content. If required endpoint/credentials/bucket configuration is absent in staging/production, startup fails; it must not select `InMemoryDocumentObjectStore`. Tests inject in-memory stores directly and only inside test setup.

  Each Vault route obtains `AuthenticatedIdentity`, uses its `workspace_id`, and returns `mvp_list`/`mvp_item` with `agent_db` and `object_store` source refs. Graph nodes/edges are generated from actual persisted document-version/backlink relations; a failure is `ApiFailure`, not `{nodes: [], edges: []}`. Promotion validates the existing lifecycle transition and real review requirements before updating state.

- [ ] **Step 4: Connect ingestion finalization to document metadata.**

  In the existing completion/review flow, after server-owned object finalize and successful metadata/scan steps, create or update exactly one Vault document/version in the same workspace. On scanner/converter/index failure, persist state/reason and return that state. Idempotency keys resolve to the same existing document/version rather than duplicate documents.

- [ ] **Step 5: Run API/wiring tests.**

  Run:

  ```bash
  PYTHONPATH=$(pwd) python3 -m pytest tests/apps/cosa/test_vault_routes.py tests/apps/cosa/test_knowledge_production_wiring.py tests/apps/cosa/knowledge_ingestion/test_api_contracts.py -q
  ```

  Expected: PASS. A real production composition cannot silently use in-memory storage.

- [ ] **Step 6: Commit the Agent Vault API.**

  ```bash
  git add apps/cosa/composition/agent_plane.py apps/cosa/api/vault_schemas.py apps/cosa/api/vault_routes.py apps/cosa/api/app.py apps/cosa/api/routes.py tests/apps/cosa/test_vault_routes.py tests/apps/cosa/test_knowledge_production_wiring.py
  git commit -m "feat: add canonical agent vault api"
  ```

## Task 3: Replace Flutter Vault legacy calls and fabricated fallback graph

**Files:**

- Create: `frontend/lib/modules/vault/models/vault_models.dart`
- Create: `frontend/lib/modules/vault/services/vault_mvp_service.dart`
- Modify: `frontend/lib/modules/vault/services/vault_service.dart`
- Modify: `frontend/lib/modules/vault/controllers/vault_controller.dart`
- Modify: `frontend/lib/modules/vault/views/vault_view.dart`
- Modify: `frontend/lib/modules/vault/views/widgets/vault_files_content_view.dart`
- Modify: `frontend/lib/modules/vault/views/widgets/vault_document_detail_view.dart`
- Modify: `frontend/lib/modules/vault/views/widgets/vault_knowledge_studio_panel.dart`
- Test: `frontend/test/vault_mvp_service_test.dart`
- Test: `frontend/test/vault_views_test.dart`

**Interfaces:**

- Consumes generated `MvpEndpoint.vault*` endpoints and `MvpRequestClient`.
- Produces typed `ApiResult` fields for documents, detail, knowledge, search and graph; no method returns a fake empty graph/map after an exception.

- [ ] **Step 1: Write failure/empty/processing widget tests.**

  ```dart
  test('vault network failure is unavailable, not a fabricated empty graph', () async {
    final result = await service.loadGraph();
    expect(result, isA<ApiFailure<VaultGraph>>());
    expect((result as ApiFailure<VaultGraph>).failure.code, ApiFailureCode.unavailable);
  });

  testWidgets('processing document cannot be opened as indexed knowledge', (tester) async {
    await tester.pumpWidget(VaultView.withState(VaultDocumentState.processing));
    expect(find.text('Đang xử lý và lập chỉ mục'), findsOneWidget);
    expect(find.text('Mở trong Knowledge Studio'), findsNothing);
  });
  ```

- [ ] **Step 2: Run tests and verify existing service fails them.**

  Run: `cd frontend && flutter test test/vault_mvp_service_test.dart test/vault_views_test.dart`

  Expected: FAIL while `/vault/*` paths and `{'nodes': [], 'edges': []}` catch fallback remain.

- [ ] **Step 3: Implement typed Vault client/model mapping.**

  `VaultMvpService` calls only `/agent/vault/*` and `/agent/knowledge/*` manifest entries. Treat document ID as opaque server ID, not a path. Remove raw path encoding routes, legacy `/vault/*` calls, broad exception catches that return empty data, and any request-side `brain_id` assumption. Binary content upload uses the documented server-issued ticket route; never uploads directly to an invented URL.

- [ ] **Step 4: Render lifecycle/provenance and actions honestly.**

  Show source type, version, checksum, observed timestamp and state. Render `empty` as an upload/create invitation with no sample file; render `FAILED` with server reason/retry action; render `not_connected` only when the provider contract returns it. Search results and graph deep-links reference returned source/document IDs only.

- [ ] **Step 5: Run focused Flutter checks and enable Vault manifest entries.**

  Run:

  ```bash
  cd frontend && flutter test test/vault_mvp_service_test.dart test/vault_views_test.dart
  cd frontend && flutter analyze
  node ../scripts/gen-mvp-contracts.mjs
  ```

  Expected: PASS; enable only implemented Vault/Knowledge IDs and update their acceptance ledger evidence.

- [ ] **Step 6: Commit Flutter Vault cutover.**

  ```bash
  git add frontend/lib/modules/vault frontend/test/vault_mvp_service_test.dart frontend/test/vault_views_test.dart shared/contracts/mvp-surface.json frontend/lib/core/network/mvp_endpoints.g.dart docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md
  git commit -m "feat: wire truthful vault ui"
  ```

## Task 4: Prove object-store, knowledge and UI isolation end-to-end

**Files:**

- Create: `tests/e2e/test_mvp_vault_http.py`
- Modify: `tests/e2e/conftest.py`
- Modify: `docs/architecture/generated/route-inventory.allowlist.json`
- Modify: `docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md`

**Interfaces:**

- Consumes actual Agent DB/object store/FastAPI service plus real workspace identities.
- Produces verified evidence for Vault document, ingestion, search and cross-workspace denial.

- [ ] **Step 1: Write the real-storage scenario.**

  ```python
  def test_uploaded_document_is_visible_only_after_real_indexing(real_mvp_stack, workspace_a, workspace_b, tmp_path):
      upload = real_mvp_stack.agent.begin_knowledge_upload(workspace_a, file_name="notes.txt", content=b"customer supplied evidence")
      finalized = real_mvp_stack.agent.complete_knowledge_upload(workspace_a, upload)
      assert finalized["state"] in {"QUEUED", "PROCESSING", "INDEXED"}
      real_mvp_stack.worker.run_knowledge_pipeline_until_terminal(finalized["ingestion_id"])
      document = real_mvp_stack.agent.find_vault_document(workspace_a, "notes.txt")
      assert document["data"]["state"] == "INDEXED"
      assert real_mvp_stack.agent.get_vault_document(workspace_b, document["data"]["document_id"]).status_code in {403, 404}
  ```

- [ ] **Step 2: Run the E2E test without an in-memory transport substitute.**

  Run: `PYTHONPATH=$(pwd) python3 -m pytest tests/e2e/test_mvp_vault_http.py -q`

  Expected: PASS with a configured local MinIO/filesystem and Postgres stack, or an explicit missing-prerequisite SKIP. Do not change the test to use `InMemoryDocumentObjectStore` to obtain a pass.

- [ ] **Step 3: Add hostile and unavailable assertions.**

  Assert cross-workspace list/get/search/backlink/graph denial, invalid object/path rejection, checksum mismatch failure, failed converter state, and unavailable object-store response. The response must never include a sample document, sample embedding or fabricated graph.

- [ ] **Step 4: Run gates and remove only Vault legacy ghosts.**

  Run:

  ```bash
  PYTHONPATH=$(pwd) python3 -m pytest tests/e2e/test_mvp_vault_http.py -q
  make mvp-surface-check
  make contract-freeze-check
  ```

  Remove only matching `/vault/*` entries after raw Flutter callers are removed and record command/SHA/result in the ledger.

- [ ] **Step 5: Commit verification evidence.**

  ```bash
  git add tests/e2e docs/architecture/generated docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md
  git commit -m "test: verify vault knowledge mvp flow"
  ```

## Completion gate

Run:

```bash
PYTHONPATH=$(pwd) python3 -m pytest tests/agent/vault tests/agent/knowledge/providers/test_postgres_knowledge_store.py tests/apps/cosa/test_vault_routes.py -q
cd frontend && flutter test test/vault_mvp_service_test.dart test/vault_views_test.dart
make mvp-surface-check
git diff --check
```

Vault is not complete if an API accepts a raw path/object key, uses an in-memory object store in normal runtime, returns a failed/processing document as indexed, returns a graph/search result after a failure, or exposes any workspace's metadata/content to another workspace.
