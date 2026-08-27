# MarkItDown Governed Knowledge Ingestion Phase A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cho phép người dùng được uỷ quyền upload PDF/DOCX/XLSX/PPTX/HTML/CSV/text và tạo knowledge candidate có version/provenance/review bằng MarkItDown, mà không cho client URL/object key, không cho converter network/plugins, và không đưa candidate vào agent retrieval.

**Architecture:** `services/cosa` sở hữu document-ingestion lifecycle, membership check và durable scheduling record; `apps/cosa` sở hữu upload broker, scanner/preflight, sandboxed MarkItDown adapter và worker handler; `packages/agent_core/knowledge` chỉ nhận normalized document/chunks versioned. Bản gốc ở object storage private; broker fetch bytes, scanner/preflight trước converter; converter trả Markdown/manifest; source được lưu `USER_CONTENT` + `review_pending`. Không có thay đổi retrieval trong phase này.

**Tech Stack:** Python 3.11/FastAPI/Pydantic/pytest; TypeScript/Encore/Drizzle/Vitest/PostgreSQL; S3-compatible private storage (MinIO cho development); MarkItDown `0.1.7` với selected extras; Docker Compose; existing COSA control-plane scheduler.

**Spec:** `docs/superpowers/specs/2026-08-27-markitdown-governed-knowledge-ingestion-design.md`

## Global Constraints

- `workspace_id` là product tenancy key duy nhất. API/browser/model không được supply object key, trusted MIME, scan result, source ID hoặc Workspace context cho worker.
- `packages/agent_core` không import `apps/*` hay `services/*`. `services/company` vẫn là source of truth cho business state; document ingestion không tạo task/workflow/policy.
- Pin đúng `markitdown[pdf,docx,pptx,xlsx]==0.1.7`; không cài `markitdown[all]`, không enable plugins và không dùng `markitdown-mcp`/`convert_uri()`/`convert_local()`.
- Phase A supports only PDF, DOCX, XLSX, PPTX, HTML, CSV and plain text. Generic ZIP, URI, email, media, OCR, cloud extractor and LLM-based extraction must reject explicitly.
- Normal agent worker image must not install parser packages. The conversion image is separate, no secrets, non-root, read-only dependencies, constrained CPU/memory/pids/time and egress deny; a production boot check must fail if the scanner/sandbox backend is test-only or unset.
- Every state change is idempotent and audited. Scheduler job payload is `{ task_type: "knowledge_ingestion", ingestion_id: "ing_..." }` only; it never includes an object URI, Markdown or raw file bytes.
- Knowledge candidate must use `authority_class="USER_CONTENT"` and source status `review_pending`. Do not call or modify `retrieve_citations()` in this plan because its current query does not enforce status/authority/access context.
- Use only sanitized, allowlisted `failure_code`/`warning_code` in API, queue, logs and metrics; raw source content, object keys, signed URLs, parser tracebacks and scanner bodies are forbidden outside protected storage.

## File Map

| File | Responsibility |
| --- | --- |
| `services/cosa/migrations/15_document_ingestions.up.sql` | Immutable schema for ingestion records/audit transitions and Workspace indexes. |
| `services/cosa/storage/control-plane-schema.ts` | Drizzle definitions for records and audit events. |
| `services/cosa/services/document-ingestion.service.ts` | Server-authoritative state transitions, idempotent queue registration, member/worker checks. |
| `services/cosa/handlers/document-ingestion.handler.ts` | Public creation/complete/read/review endpoints and worker-only claim/update endpoints. |
| `services/cosa/handlers/index.ts` | Re-export the new handler. |
| `services/cosa/tests/document-ingestion.test.ts` | Control-plane auth, state machine, idempotency and tenant tests. |
| `apps/cosa/knowledge_ingestion/contracts.py` | Pydantic contracts, allowlists, state/failure/warning enums and policy limits. |
| `apps/cosa/knowledge_ingestion/object_store.py` | Server-owned S3/MinIO object broker plus explicit in-memory test backend. |
| `apps/cosa/knowledge_ingestion/preflight.py` | MIME magic validation, bounded stream/hash and Office ZIP safety checks. |
| `apps/cosa/knowledge_ingestion/scanner.py` | Scanner protocol, production configuration guard and fake test scanner. |
| `apps/cosa/knowledge_ingestion/conversion_sandbox.py` | Sandbox protocol; test implementation and production readiness guard. |
| `apps/cosa/knowledge_ingestion/markitdown_converter.py` | The only MarkItDown call site: selected stream, plugins disabled, bounded output and manifest. |
| `apps/cosa/knowledge_ingestion/normalization.py` | Markdown normalizer and deterministic heading/worksheet/slide anchor chunker. |
| `apps/cosa/knowledge_ingestion/control_plane_client.py` | Typed worker client for `services/cosa` ingestion endpoints. |
| `apps/cosa/knowledge_ingestion/handler.py` | One idempotent end-to-end ingestion job handler. |
| `apps/cosa/api/schemas.py` | Upload-ticket, complete-upload, ingestion-status and review DTOs; no public object ref. |
| `apps/cosa/api/routes.py` | Membership-bound FastAPI routes that call the broker/control-plane, never MarkItDown. |
| `apps/cosa/worker/main.py` | Dispatch `knowledge_ingestion` without a run lease, retaining scheduled-task fencing heartbeat. |
| `apps/cosa/requirements.ingestion.txt` | Pinned parser/runtime dependencies kept out of API/agent worker requirements. |
| `apps/cosa/Dockerfile.ingestion-worker` | Dedicated conversion worker image with non-root user and readiness validation. |
| `docker-compose.yml` | `cosa-ingestion-worker` development service and explicit non-production isolation warning/config. |
| `tests/apps/cosa/knowledge_ingestion/` | Unit/vertical tests for broker, preflight, converter, normalizer, job and API contracts. |
| `tests/apps/cosa/worker/test_main.py` | Regression for non-run ingestion task dispatch and scheduler completion/fencing. |
| `tests/agent_core/knowledge/test_document_candidate.py` | Agent Core persistence/provenance regression for candidate sources. |

---

## Task 1: Create immutable control-plane lifecycle and authorization boundary

**Files:**

- Create: `services/cosa/migrations/15_document_ingestions.up.sql`
- Modify: `services/cosa/storage/control-plane-schema.ts`
- Create: `services/cosa/services/document-ingestion.service.ts`
- Create: `services/cosa/handlers/document-ingestion.handler.ts`
- Modify: `services/cosa/handlers/index.ts`
- Create: `services/cosa/tests/document-ingestion.test.ts`

**Interfaces:**

- `DocumentIngestionState = "UPLOADING" | "QUARANTINED" | "QUEUED" | "VALIDATING" | "CONVERTING" | "REVIEW_PENDING" | "PUBLISHED" | "REJECTED" | "FAILED" | "EXPIRED"`.
- `createDocumentIngestion({ workspaceId, createdBy, originalFilename, declaredMediaType, idempotencyKey }): DocumentIngestionRecord` creates only `UPLOADING`; it has no object key from caller.
- `completeUpload({ ingestionId, actorId, detectedMediaType, sizeBytes, sourceSha256, objectKey })` accepts `objectKey` only from the internal broker and changes `UPLOADING → QUARANTINED → QUEUED` atomically.
- `transitionDocumentIngestionForWorker({ ingestionId, claimToken, expectedStates, nextState, patch })` uses row lock/CAS; public callers cannot invoke it.
- `reviewDocumentIngestion({ ingestionId, reviewerId, decision, reason })` permits only `REVIEW_PENDING → PUBLISHED|REJECTED` and writes immutable audit event.

- [ ] **Step 1: Write failing state/auth tests**

  Cover: member of Workspace A creates a record; non-member and Workspace B receive non-enumerating authorization failure; duplicate `(workspace_id, created_by, idempotency_key)` returns same record; illegal state transition fails; a worker-only endpoint rejects platform JWT; reviewer cannot publish before `REVIEW_PENDING`; audit contains old/new state and reason but never object key.

- [ ] **Step 2: Run the red test**

  ```bash
  cd services/cosa && npx vitest run tests/document-ingestion.test.ts
  ```

  Expected: test file/contracts do not exist and lifecycle endpoints are unavailable.

- [ ] **Step 3: Implement schema, service and endpoints**

  Add `control_plane.document_ingestions` with opaque text ID, Workspace/creator, private object key nullable until broker completion, filename, declared/detected type, size, SHA-256, state, idempotency key, knowledge source ID, converter fields, manifest JSON, failure code and timestamps. Add `document_ingestion_audit_events` append-only with ingestion ID, actor kind/ID, old/new state, reason/failure code and timestamp. Enforce uniqueness on `(workspace_id, created_by, idempotency_key)` and index `(workspace_id, state, created_at)`.

  Public handlers must call the same `verifyWorkspaceMembership` pattern used by connector handlers. Worker handlers must call `requireWorkerServiceAuth`. Allow transitions only through a local transition table, not by accepting arbitrary state strings. Schedule exactly one existing scheduler task with coalescing key `knowledge-ingestion:<ingestion-id>` after the broker has stored/verifed the object.

- [ ] **Step 4: Run control-plane regression**

  ```bash
  cd services/cosa && npx vitest run tests/document-ingestion.test.ts tests/worker-ingress.test.ts && npm run typecheck
  ```

  Expected: state transitions are CAS/idempotent, membership and worker separation are enforced, and existing worker ingress stays green.

- [ ] **Step 5: Commit**

  ```bash
  git add services/cosa/migrations/15_document_ingestions.up.sql services/cosa/storage/control-plane-schema.ts services/cosa/services/document-ingestion.service.ts services/cosa/handlers/document-ingestion.handler.ts services/cosa/handlers/index.ts services/cosa/tests/document-ingestion.test.ts
  git commit -m "feat: add governed document ingestion lifecycle"
  ```

## Task 2: Define untrusted document contracts and a server-owned upload broker

**Files:**

- Create: `apps/cosa/knowledge_ingestion/__init__.py`
- Create: `apps/cosa/knowledge_ingestion/contracts.py`
- Create: `apps/cosa/knowledge_ingestion/object_store.py`
- Modify: `apps/cosa/api/schemas.py`
- Modify: `apps/cosa/api/routes.py`
- Create: `tests/apps/cosa/knowledge_ingestion/test_object_store.py`
- Create: `tests/apps/cosa/knowledge_ingestion/test_api_contracts.py`

**Interfaces:**

- `DocumentObjectStore.issue_upload_ticket(ingestion_id, workspace_id, media_type, max_bytes) -> UploadTicket` returns a short-lived signed target with immutable key; no `object_ref` input.
- `DocumentObjectStore.finalize_upload(ingestion_id, workspace_id) -> QuarantinedObject` returns the server-derived key, byte count, SHA-256 and detected MIME after bounded read.
- `CreateKnowledgeUploadRequest` contains only `file_name`, `declared_media_type` and `idempotency_key`; `CompleteKnowledgeUploadRequest` contains `ingestion_id` only.
- `MessageAttachmentCreate.object_ref` remains backward-compatible for chat only and is never accepted by these knowledge routes.

- [ ] **Step 1: Write failing broker/API tests**

  Assert generated key is random, server-owned and scoped under `quarantine/<workspace>/<ingestion>/`; clients cannot select a key, URI or final checksum; expired ticket cannot finalize; a forged/other-workspace ingestion ID returns non-enumerating failure; finalization detects a MIME mismatch and size overrun. Assert public DTO/response omits object key and signed target after creation.

- [ ] **Step 2: Run the red tests**

  ```bash
  PYTHONPATH=$(pwd) .venv/bin/pytest tests/apps/cosa/knowledge_ingestion/test_object_store.py tests/apps/cosa/knowledge_ingestion/test_api_contracts.py -q
  ```

  Expected: module/routes and server-owned upload contract do not exist.

- [ ] **Step 3: Implement broker and thin API routes**

  Define allowlisted MIME/size policy in `contracts.py`: text/CSV/HTML ≤10 MiB; PDF/DOCX/XLSX/PPTX ≤25 MiB. Implement an in-memory object store only for tests and an S3-compatible MinIO backend for deployment using credentials scoped to quarantine/normalized prefixes. `issue_upload_ticket` fixes key, content-length range and short expiration. `finalize_upload` performs authoritative HEAD/read/hash/type sniff before invoking Task 1 completion endpoint.

  FastAPI authenticates the existing identity, creates a control-plane record, calls broker issue/finalize and returns only safe status data. It must not import MarkItDown, open caller paths, fetch URL, accept bytes through JSON or enqueue raw payload. Feature flag remains off by default until Task 7 readiness gate passes.

- [ ] **Step 4: Run API and tenancy regression**

  ```bash
  PYTHONPATH=$(pwd) .venv/bin/pytest tests/apps/cosa/knowledge_ingestion/test_object_store.py tests/apps/cosa/knowledge_ingestion/test_api_contracts.py tests/apps/cosa/test_tenant_isolation.py -q
  ```

  Expected: no public route leaks private references and cross-Workspace finalization is denied.

- [ ] **Step 5: Commit**

  ```bash
  git add apps/cosa/knowledge_ingestion/__init__.py apps/cosa/knowledge_ingestion/contracts.py apps/cosa/knowledge_ingestion/object_store.py apps/cosa/api/schemas.py apps/cosa/api/routes.py tests/apps/cosa/knowledge_ingestion/test_object_store.py tests/apps/cosa/knowledge_ingestion/test_api_contracts.py
  git commit -m "feat: add private knowledge document upload boundary"
  ```

## Task 3: Enforce scanner, MIME and Office archive preflight before conversion

**Files:**

- Create: `apps/cosa/knowledge_ingestion/preflight.py`
- Create: `apps/cosa/knowledge_ingestion/scanner.py`
- Create: `tests/apps/cosa/knowledge_ingestion/test_preflight.py`
- Create: `tests/apps/cosa/knowledge_ingestion/test_scanner.py`

**Interfaces:**

- `validate_quarantined_object(obj: QuarantinedObject) -> ValidatedDocument` emits only allowed detected MIME and source SHA-256.
- `preflight_office_archive(stream) -> ArchiveSafetyReport` enforces max 1,000 members, 100 MiB total expanded bytes, 50 MiB/member and 20:1 expansion ratio without extracting files to host filesystem.
- `DocumentMalwareScanner.scan(stream, document) -> ScanVerdict` returns `clean`, `infected` or `unavailable`; only `clean` proceeds.
- Failure codes are fixed enum: `unsupported_media_type`, `mime_mismatch`, `file_too_large`, `archive_limit_exceeded`, `malware_detected`, `scanner_unavailable`, `checksum_mismatch`.

- [ ] **Step 1: Write malicious-input tests first**

  Build tiny fixture streams in test code for spoofed extension/MIME, invalid PDF magic, HTML over limit, ZIP-derived office archive with excessive members, uncompressed-size/ratio bomb, generic ZIP and scanner `infected`/`unavailable`. Assert neither test invokes converter nor writes knowledge on every rejection path.

- [ ] **Step 2: Run the red tests**

  ```bash
  PYTHONPATH=$(pwd) .venv/bin/pytest tests/apps/cosa/knowledge_ingestion/test_preflight.py tests/apps/cosa/knowledge_ingestion/test_scanner.py -q
  ```

  Expected: validation/scanner guards do not exist.

- [ ] **Step 3: Implement bounded validation**

  Sniff magic bytes and compare against declared type only for diagnostics. Reject all URI-like inputs, generic archives and values outside the exact allowlist before any parser import. Use a bounded reader that hashes while reading and rejects when byte count exceeds policy. For DOCX/XLSX/PPTX inspect central directory and compressed/uncompressed metadata without extracting, then rewind/create a bounded conversion stream. Require a production scanner adapter configured by explicit environment; test fake scanner is rejected by production readiness validation.

- [ ] **Step 4: Run security regression**

  ```bash
  PYTHONPATH=$(pwd) .venv/bin/pytest tests/apps/cosa/knowledge_ingestion/test_preflight.py tests/apps/cosa/knowledge_ingestion/test_scanner.py -q
  ```

  Expected: each hostile input is terminally rejected with its allowlisted code and a clean supported fixture returns `ValidatedDocument`.

- [ ] **Step 5: Commit**

  ```bash
  git add apps/cosa/knowledge_ingestion/preflight.py apps/cosa/knowledge_ingestion/scanner.py tests/apps/cosa/knowledge_ingestion/test_preflight.py tests/apps/cosa/knowledge_ingestion/test_scanner.py
  git commit -m "feat: harden document ingestion preflight"
  ```

## Task 4: Add an isolated, pinned MarkItDown conversion adapter

**Files:**

- Create: `apps/cosa/requirements.ingestion.txt`
- Create: `apps/cosa/knowledge_ingestion/conversion_sandbox.py`
- Create: `apps/cosa/knowledge_ingestion/markitdown_converter.py`
- Create: `apps/cosa/Dockerfile.ingestion-worker`
- Modify: `docker-compose.yml`
- Create: `tests/apps/cosa/knowledge_ingestion/test_markitdown_converter.py`
- Create: `tests/apps/cosa/knowledge_ingestion/test_conversion_sandbox.py`

**Interfaces:**

- `SafeMarkItDownConverter.convert(document: ValidatedDocument) -> ConversionResult` has Markdown, title, package version, `markitdown-safe-v1`, output SHA-256 and warning enums.
- `DocumentConversionSandbox.run(document, converter_profile) -> ConversionResult` is the only process boundary invoked by job handler.
- Converter must instantiate `MarkItDown(enable_plugins=False)` and call `convert_stream()` with server-built stream metadata only.
- `assert_production_conversion_ready()` rejects local/test sandbox, disabled scanner, missing resource limits or absent egress-deny attestation.

- [ ] **Step 1: Write conversion and denial tests**

  Use small checked-in/inline legal fixtures for text, HTML, CSV and one fixture each PDF/DOCX/XLSX/PPTX. Assert nonempty normalized Markdown, package/version manifest, deterministic output hash and bounded output. Mock `MarkItDown` and assert `convert_uri`, `convert_local`, plugins and generic `requests` are never called. Assert sandbox readiness rejects a test/subprocess backend in production mode and converter timeout/output overflow emits allowlisted failure codes.

- [ ] **Step 2: Run the red tests**

  ```bash
  PYTHONPATH=$(pwd) .venv/bin/pytest tests/apps/cosa/knowledge_ingestion/test_markitdown_converter.py tests/apps/cosa/knowledge_ingestion/test_conversion_sandbox.py -q
  ```

  Expected: parser profile/image and safe call site are absent.

- [ ] **Step 3: Implement the sealed adapter and image**

  Put exactly `markitdown[pdf,docx,pptx,xlsx]==0.1.7` in `requirements.ingestion.txt`; add only explicit support libraries needed by broker/sandbox, with locked image digest/SBOM emitted by CI. Keep it out of `apps/cosa/requirements.txt`. The adapter takes a prevalidated bounded stream, disables plugins, supplies server-calculated `StreamInfo`, caps output at 10 MiB and maps parser errors to sanitized code.

  The dedicated Dockerfile runs non-root, has a read-only root filesystem and no model/connector secrets. The Compose service is development-only and must document that it is not a production network isolation control; production deployment requires an orchestrator/network-policy egress-deny attestation consumed by readiness check.

- [ ] **Step 4: Run converter and image contract regression**

  ```bash
  PYTHONPATH=$(pwd) .venv/bin/pytest tests/apps/cosa/knowledge_ingestion/test_markitdown_converter.py tests/apps/cosa/knowledge_ingestion/test_conversion_sandbox.py -q
  docker compose config --quiet
  ```

  Expected: supported fixtures convert, forbidden APIs are unreachable, production guard fail-closes under test config, and Compose syntax is valid.

- [ ] **Step 5: Commit**

  ```bash
  git add apps/cosa/requirements.ingestion.txt apps/cosa/knowledge_ingestion/conversion_sandbox.py apps/cosa/knowledge_ingestion/markitdown_converter.py apps/cosa/Dockerfile.ingestion-worker docker-compose.yml tests/apps/cosa/knowledge_ingestion/test_markitdown_converter.py tests/apps/cosa/knowledge_ingestion/test_conversion_sandbox.py
  git commit -m "feat: add isolated MarkItDown converter"
  ```

## Task 5: Normalize converted Markdown into a review-only knowledge candidate

**Files:**

- Create: `apps/cosa/knowledge_ingestion/normalization.py`
- Modify: `packages/agent_core/knowledge/models.py`
- Modify: `packages/agent_core/knowledge/service.py`
- Modify: `packages/agent_core/knowledge/providers/postgres.py`
- Create: `tests/apps/cosa/knowledge_ingestion/test_normalization.py`
- Create: `tests/agent_core/knowledge/test_document_candidate.py`

**Interfaces:**

- `normalize_conversion(result, document) -> NormalizedKnowledgeCandidate` returns Markdown, `DocumentExtractionManifest`, deterministic anchors and chunks.
- `KnowledgeIngestionService.ingest_normalized_document(document: KnowledgeDocument) -> KnowledgeDocument` persists a caller-built normalized document; `ingest_raw_text()` stays backward compatible and never creates a candidate automatically.
- New status literals include `review_pending`, `published`, `rejected` while preserving existing `pending`, `processing`, `completed`, `failed` data.
- Candidate metadata requires `ingestion_id`, `source_sha256`, `markdown_sha256`, `converter_name`, `converter_version`, `converter_profile`, `manifest_schema_version`, scan verdict and warning codes.

- [ ] **Step 1: Write failing provenance and compatibility tests**

  Given headings, table and blank sections, assert anchor IDs/order and chunks never cross a heading unless a deterministic split reason is recorded. Assert DOCX/XLSX/PPTX labels use heading/worksheet/slide semantics rather than fabricated page numbers. Assert `ingest_normalized_document` stores `USER_CONTENT/review_pending`, source version parser fields and required metadata. Re-run existing raw-text ingestion tests to prove their default completed behavior is unchanged.

- [ ] **Step 2: Run the red tests**

  ```bash
  PYTHONPATH=$(pwd) .venv/bin/pytest tests/apps/cosa/knowledge_ingestion/test_normalization.py tests/agent_core/knowledge/test_document_candidate.py tests/agent_core/knowledge/providers/test_postgres_knowledge_store.py -q
  ```

  Expected: normalized document API, manifest and new statuses are not represented consistently.

- [ ] **Step 3: Implement normalizer and persistence metadata**

  Normalize line endings/encoding, retain Markdown tables/code blocks, create heading/worksheet/slide anchors and chunk with `document-section-v1`. Extend the models with validated status literals/metadata helpers rather than adding app-specific imports. Persist parser name/version from converter metadata into `knowledge.source_versions.ingestion_run_id/parser_name/parser_version` and keep exact source/version history. The source status remains `review_pending`; no retrieval method is touched.

- [ ] **Step 4: Run knowledge regression**

  ```bash
  PYTHONPATH=$(pwd) .venv/bin/pytest tests/apps/cosa/knowledge_ingestion/test_normalization.py tests/agent_core/knowledge/test_document_candidate.py tests/agent_core/knowledge/providers/test_postgres_knowledge_store.py tests/agent_core/knowledge/test_snapshot_repository.py -q
  ```

  Expected: candidate provenance survives Postgres/in-memory persistence and existing snapshots/raw ingestion remain compatible.

- [ ] **Step 5: Commit**

  ```bash
  git add apps/cosa/knowledge_ingestion/normalization.py packages/agent_core/knowledge/models.py packages/agent_core/knowledge/service.py packages/agent_core/knowledge/providers/postgres.py tests/apps/cosa/knowledge_ingestion/test_normalization.py tests/agent_core/knowledge/test_document_candidate.py
  git commit -m "feat: persist reviewable document knowledge candidates"
  ```

## Task 6: Wire durable job execution, retry safety and review publication

**Files:**

- Create: `apps/cosa/knowledge_ingestion/control_plane_client.py`
- Create: `apps/cosa/knowledge_ingestion/handler.py`
- Modify: `apps/cosa/worker/main.py`
- Modify: `apps/cosa/api/schemas.py`
- Modify: `apps/cosa/api/routes.py`
- Modify: `services/cosa/services/document-ingestion.service.ts`
- Modify: `services/cosa/handlers/document-ingestion.handler.ts`
- Modify: `tests/apps/cosa/worker/test_main.py`
- Create: `tests/apps/cosa/knowledge_ingestion/test_handler.py`
- Modify: `services/cosa/tests/document-ingestion.test.ts`

**Interfaces:**

- `execute_knowledge_ingestion_task(payload: dict[str, str]) -> None` requires exactly `task_type` and `ingestion_id`.
- `DocumentIngestionControlPlaneClient.claim_for_conversion`, `record_candidate`, `mark_rejected_or_failed` send worker auth and claim token; they do not transport raw file bytes.
- `ReviewKnowledgeIngestionRequest { decision: "publish_reference" | "reject"; reason: str }`; `publish_reference` only publishes a candidate source, it does not create a KnowledgeSnapshot or enable retrieval.

- [ ] **Step 1: Write failure, retry and review tests**

  Assert `knowledge_ingestion` task dispatch succeeds without a run lease or `run_id`, but keeps task claim heartbeat/fencing. Assert duplicate scheduler poll/retry for the same ingestion/source SHA creates one knowledge source/version. Assert scan/type/parser terminal rejection sets `REJECTED`; transient store/control-plane error sets `FAILED` and scheduler retry has no leaked partial source. Assert review requires member/reviewer, only allows `REVIEW_PENDING`, records audit and does not change `KnowledgeStore.search_chunks` behavior.

- [ ] **Step 2: Run the red tests**

  ```bash
  PYTHONPATH=$(pwd) .venv/bin/pytest tests/apps/cosa/worker/test_main.py tests/apps/cosa/knowledge_ingestion/test_handler.py -q
  cd services/cosa && npx vitest run tests/document-ingestion.test.ts
  ```

  Expected: current worker rejects task with missing `run_id` and no candidate/review handler exists.

- [ ] **Step 3: Implement end-to-end stateful handler**

  Refactor `dispatch_one_task` into a run-bound path and a non-run ingestion path. The latter uses scheduled-task heartbeat/complete fencing but not `RunLeaseManager`; its idempotency is ingestion record CAS plus source SHA. The handler claims record, broker-loads bytes, scans/preflights, calls the sandbox converter, normalizes, persists candidate, then atomically records `REVIEW_PENDING` and source ID. On failure, map only known terminal violations to `REJECTED`; raise/record sanitized transient failure for scheduler retry.

  API review endpoint verifies Workspace membership and reviewer authorization policy, then uses control-plane transition. It returns a safe status response, not Markdown/object metadata. Explicitly preserve the prohibition on retrieval/agent prompt wiring.

- [ ] **Step 4: Run vertical regression**

  ```bash
  PYTHONPATH=$(pwd) .venv/bin/pytest tests/apps/cosa/worker/test_main.py tests/apps/cosa/knowledge_ingestion/test_handler.py tests/apps/cosa/knowledge_ingestion/test_api_contracts.py tests/agent_core/knowledge/test_document_candidate.py -q
  cd services/cosa && npx vitest run tests/document-ingestion.test.ts tests/worker-ingress.test.ts
  ```

  Expected: task lifecycle is fenced/idempotent, candidate remains inaccessible to retrieval and review transition is audited.

- [ ] **Step 5: Commit**

  ```bash
  git add apps/cosa/knowledge_ingestion/control_plane_client.py apps/cosa/knowledge_ingestion/handler.py apps/cosa/worker/main.py apps/cosa/api/schemas.py apps/cosa/api/routes.py services/cosa/services/document-ingestion.service.ts services/cosa/handlers/document-ingestion.handler.ts tests/apps/cosa/worker/test_main.py tests/apps/cosa/knowledge_ingestion/test_handler.py services/cosa/tests/document-ingestion.test.ts
  git commit -m "feat: execute governed document ingestion jobs"
  ```

## Task 7: Add release controls, observability and verification gates

**Files:**

- Modify: `apps/cosa/knowledge_ingestion/contracts.py`
- Modify: `apps/cosa/knowledge_ingestion/conversion_sandbox.py`
- Modify: `apps/cosa/Dockerfile.ingestion-worker`
- Modify: `docker-compose.yml`
- Modify: `Makefile`
- Create: `tests/apps/cosa/knowledge_ingestion/test_production_readiness.py`
- Create: `tests/apps/cosa/knowledge_ingestion/test_end_to_end.py`
- Modify: `docs/features/knowledge.md`

**Interfaces:**

- `assert_production_ingestion_ready(environment) -> None` verifies storage prefix policy, scanner, sandbox egress-deny attestation, package profile/version and feature flag.
- Metrics event schema is `{ ingestion_id, workspace_id, state, detected_media_type, size_bytes, duration_ms, failure_code?, warning_codes? }`; it cannot carry content or object keys.
- `make knowledge-ingestion-test` executes the unit/vertical suite; `make verify-local` includes it once non-flaky.

- [ ] **Step 1: Write release-readiness and end-to-end tests**

  Test production rejection for fake scanner/sandbox, missing egress proof, missing pinned converter profile and feature flag enabled before readiness. End-to-end test with in-memory broker/scanner/sandbox proves a clean text/HTML fixture reaches `REVIEW_PENDING`; each adversarial fixture reaches terminal rejection and creates no chunk; cross-Workspace status/read/review remains denied. Assert metrics and error output do not contain a known secret string from the fixture.

- [ ] **Step 2: Run the red tests**

  ```bash
  PYTHONPATH=$(pwd) .venv/bin/pytest tests/apps/cosa/knowledge_ingestion/test_production_readiness.py tests/apps/cosa/knowledge_ingestion/test_end_to_end.py -q
  ```

  Expected: no startup gate, documented metrics contract or complete vertical test exists.

- [ ] **Step 3: Implement feature gate and operations documentation**

  Add one fail-closed feature flag checked at ticket issuance and worker start. Build readiness into the ingestion image entrypoint, never into a warning log. Emit structured sanitized metrics/state transitions. Add a Make target for the focused suite, but do not claim a developer Compose network alone provides production egress isolation. Update knowledge documentation with `review_pending`, no-retrieval rule, source/version manifest provenance, unpublish/retention runbook and Phase B prerequisites.

- [ ] **Step 4: Run full required verification**

  ```bash
  make knowledge-ingestion-test
  make boundary-check
  cd services/cosa && npm run typecheck && npx vitest run tests/document-ingestion.test.ts tests/worker-ingress.test.ts
  git diff --check
  ```

  Expected: focused unit, hostile-file, vertical, tenancy and boundary checks pass; TypeScript compiles; no trailing whitespace or malformed patch remains.

- [ ] **Step 5: Commit**

  ```bash
  git add apps/cosa/knowledge_ingestion/contracts.py apps/cosa/knowledge_ingestion/conversion_sandbox.py apps/cosa/Dockerfile.ingestion-worker docker-compose.yml Makefile tests/apps/cosa/knowledge_ingestion/test_production_readiness.py tests/apps/cosa/knowledge_ingestion/test_end_to_end.py docs/features/knowledge.md
  git commit -m "test: gate governed knowledge ingestion release"
  ```

## Post-Phase-A Handoff

Do not extend this branch into retrieval or business automation. Create a separate Phase B plan only after Phase A evidence is green. Phase B must add access-aware retrieval, authority/status/sensitivity enforcement before ranking, published KnowledgeSnapshot selection, citation anchors and evaluations. Process extraction may only create cited `ProcessKnowledgeProposal`; activation belongs to the relevant `services/company` owner and needs its own Capability Gateway/approval/audit plan.
