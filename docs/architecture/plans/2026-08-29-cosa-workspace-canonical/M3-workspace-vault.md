# M3 — Workspace Vault multi-workspace local

**Audit:** §9.3, §6 · **Phụ thuộc:** M2 · **Master:** [../2026-08-29-cosa-workspace-canonical-master-plan.md](../2026-08-29-cosa-workspace-canonical-master-plan.md)

## Context

Multi-workspace local hiện chỉ ở mức "các bảng đã có `workspace_id`": memory, knowledge,
artifacts, runs, conversations trong `packages/agent_core` mang `workspace_id`; object
ingestion tạo key `quarantine/<workspace>/<ingestion>/...`
([apps/cosa/knowledge_ingestion/contracts.py:88](../../../../apps/cosa/knowledge_ingestion/contracts.py#L88)).
Nhưng:

- Chưa có local filesystem object-store; production path thiên về S3/MinIO.
- `KnowledgeDocument`/`KnowledgeChunk` default `uuid.uuid4()` (M2 §3 nâng lên UUIDv7 — LeafId,
  KHÔNG chuyển sang Snowflake; xem [M0 ADR-ID-MODEL-001](./M0-contract-freeze.md)).
- [packages/agent_core/knowledge/providers/postgres.py:186-252](../../../../packages/agent_core/knowledge/providers/postgres.py#L186-L252) —
  `get_document(doc_id)` query `WHERE id = :id`, **không** workspace context.
- Vault frontend còn nhét `brain_id` vào mọi path
  ([frontend/lib/modules/vault/services/vault_service.dart](../../../../frontend/lib/modules/vault/services/vault_service.dart)),
  trong khi backend đã drop ghost brain fields.
- Chưa có per-workspace encryption key / backup manifest / sync cursor / conflict area
  (per-workspace *quota* đã có một phần trong `budget_gate.py`).
- File gốc mới ở quarantine; chưa có lifecycle cho published document, SOP version, archive, trash.

Chọn **phương án B** (audit §6.1): Workspace Vault trên shared Runtime Host — file/key/sync/
quota/backup tách theo workspace; một local Postgres cluster dùng chung có `workspace_id` +
composite FK + Row-Level Security.

## Deliverables

### 1. Runtime Host Catalog + Vault manifest (audit §6.2)
Layout:

```
<COSA_DATA_ROOT>/
  host/{catalog, runtime-node, logs}/
  workspaces/<workspace_snowflake_id>/
    manifest.json                      # non-secret metadata, schema version, workspace id, checksums, key ref
    vault/{documents,sops,attachments,artifacts}/
    knowledge/{snapshots,indexes}/
    quarantine/ exports/ temp/
    sync/{outbox,inbox,conflicts,checkpoints}/
    backup/
```

- `manifest.json` KHÔNG chứa plaintext workspace key/token.
- Host catalog theo dõi workspace nào tồn tại, path root, runtime/sync mode (mỗi workspace độc lập).

### 2. `WorkspaceObjectStore` abstraction (audit §6.3)
Interface (business code không ghép raw path):

```
put(workspace_id, object_kind, object_id, version_id, stream)
get(workspace_id, object_ref)
archive(workspace_id, object_ref)
delete_after_retention(workspace_id, object_ref)
list_versions(workspace_id, object_id)
```

- `LocalFilesystemWorkspaceStore` (**mới**) cho managed local directory.
- `S3WorkspaceStore` cho local MinIO / cloud S3-compatible.
- Object key chuẩn: `workspaces/<workspace_id>/<kind>/<object_id>/versions/<version_id>/<blob>`.
- Migrate key hiện tại `quarantine/<workspace>/<ingestion>/...` → layout mới.
- **Không** dedup blob xuyên workspace (hash/refcount chung làm yếu isolation); dedup trong 1 workspace OK.
- Vị trí: `packages/agent_core/` (reusable, không import `services/company/*`) hoặc `apps/cosa/`
  nếu cần compose — theo CLAUDE.md 4 vùng.

### 3. Security invariants (audit §6.9)
- Không nhận raw absolute path từ client.
- Canonicalize path; chặn `..`, symlink/hardlink escape, case-fold collision.
- Mọi object metadata chứa `workspace_id` + checksum.
- delete/restore/version APIs bind `(workspace_id, object_id)`.
- knowledge/memory/artifact caches key theo workspace.
- temp/quarantine cleanup không đi ra ngoài workspace root.
- Cross-workspace export/search/citation/backup/restore có **negative tests bắt buộc**.

### 4. RLS + composite FK cho tenant-owned relational tables (audit §6.4)
- `workspace_id BIGINT NOT NULL` mọi tenant row (đã phần lớn có — verify).
- Lookup/mutation `(workspace_id, resource_id)`; composite unique/FK bảo đảm linked resources cùng workspace.
- RLS policy dùng transaction-local context:
  `USING (workspace_id = current_setting('cosa.workspace_id')::bigint)`.
- Connection pool reset `cosa.workspace_id` khi trả connection.
- Index bắt đầu bằng `workspace_id` cho query tenant-scoped.
- pgvector search bắt buộc filter workspace **trước** khi trả result.
- [packages/agent_core/knowledge/providers/postgres.py:186-252](../../../../packages/agent_core/knowledge/providers/postgres.py#L186-L252) —
  `get_document`, `get_chunk`, list, search: thêm tham số workspace context; query
  `WHERE id = :id AND workspace_id = :ws`. (`KnowledgeDocument`/`KnowledgeChunk` ID = LeafId
  UUIDv7 từ M2 §3 — không phải Snowflake; `sop_definition`/`sop_version` ID = SpineId Snowflake.)
- Per-workspace partition / vector index CHỈ mở khi đo được nhu cầu — không tạo động cho mọi workspace.

### 5. Document + SOP lifecycle first-class (audit §6.5)
Document lifecycle: `QUARANTINED → SCANNED → REVIEW_PENDING → PUBLISHED → ARCHIVED → PURGED`.
Sau publish: file nguồn copy có kiểm chứng từ quarantine vào Vault; `source_uri` chứa
workspace/object identity (không dùng URI thiếu workspace).

SOP là first-class resource:

```
SopDefinition   { id(Snowflake), workspace_id, title, owner_member_id,
                  status(DRAFT|REVIEW|ACTIVE|RETIRED), current_version_id, risk_class, approval_policy }
SopVersion      { id(Snowflake), workspace_id, sop_id, content_object_ref, normalized_object_ref,
                  checksum, effective_from, approved_by }
```

- Chỉ SOP `ACTIVE` được đưa vào procedural instructions/capability context. Draft/review KHÔNG
  được agent coi là policy đang hiệu lực.
- Schema: nơi knowledge/agent_core schema sống + migration.

### 6. Per-workspace DEK, key rotation, quota, cleanup (audit §6.6)
- Master device key trong OS Keychain/Keystore/Secure Enclave khi có.
- Mỗi workspace một Data Encryption Key; workspace DEK envelope-encrypt bởi device/user key.
- Object/backup/sync payload dùng workspace-scoped key + version.
- Switch workspace: unload key + cache + realtime subscription của workspace cũ.
- Key rotation: resumable re-encryption journal.
- Xóa workspace: destroy key sau retention/recovery window.
- Reuse per-workspace budget/quota: `packages/agent_core/.../budget_gate.py` (mở rộng cho storage quota).
- Threat model: local OS admin là riêng; nếu cần chống host admin ⇒ user-held passphrase/hardware
  key + chấp nhận giới hạn background automation (ghi rõ, không tự bật).

### 7. Bỏ `brain_id` khỏi frontend (audit §3.12, §9.3.8)
- [frontend/lib/modules/vault/services/vault_service.dart](../../../../frontend/lib/modules/vault/services/vault_service.dart) —
  bỏ `brain_id` khỏi mọi endpoint path (lines ~8-152); Workspace là knowledge/vault scope duy nhất.
- Rà `auth`, `chat`, `marketing` compatibility paths còn tham chiếu `brain_id` — xóa.
- Không thêm alias thay thế (guardrail 1).

### 8. Runtime workspace switcher + centralized invalidation (audit §6.7)
- `active_workspace_id` là **UI context**, không phải global backend state. Backend scheduler
  chạy tiếp workspace B khi user xem workspace A.
- Switch sequence: (1) chặn request mới của workspace cũ; (2) cancel/close realtime
  subscriptions + pending streams; (3) clear controllers, cached entitlement, knowledge
  results, role, project selection; (4) load membership + key + runtime status workspace mới;
  (5) set local session context; (6) refetch (không tái dùng object cache không có workspace key).
- Queue, compute budget, connector quota, agent concurrency, storage quota tách theo workspace.

### 9. Per-workspace backup/export/restore (audit §6.8)
Package: signed/encrypted manifest, schema version + workspace ID, relational snapshot filtered
theo workspace, encrypted object versions, knowledge/SOP version metadata, sync cursor/conflict
state, checksums + key-wrapping metadata.
- Backup/export/restore một workspace KHÔNG đọc/khóa workspace khác.
- Restore cùng ID: check collision/ownership. Clone: tạo Snowflake ID mới + rewrite internal
  references theo migration map.

## Test plan (audit §10.3)

- Một local installation tạo/mở/archive/restore nhiều workspace.
- Workspace A không đọc/list/search/cite/export object, SOP, knowledge, memory, artifact của B.
- Path traversal, symlink, hardlink, Unicode/case-fold escape bị chặn.
- Knowledge lookup bắt buộc workspace ID; vector search không leak result cross-workspace.
- Workspace switch clear cache, role, entitlement, project, realtime subscriptions.
- Background agent của B tiếp tục đúng context khi UI ở A.
- Storage/compute/connector quota của A không nghẽn B ngoài host-level policy.
- Backup A không chứa metadata/hash/key của B; restore A không khóa/mutate B.
- Key rotation resume; retention/key-destruction test.
- Chỉ SOP ACTIVE được dùng làm procedural instruction.

## Tiến độ

- [x] **`WorkspaceObjectStore` abstraction + `LocalFilesystemWorkspaceStore`** (§2, §3, §6.9) —
  `packages/agent_core/vault/object_store.py` (thuần, không import `services/*`). Key layout
  `workspaces/<id>/<kind>/<object_id>/versions/<version_id>/<blob>` + sidecar `meta.json`
  (`workspace_id` + sha256 + size + status). Bất biến an toàn: từ chối `..` / separator /
  absolute / leading-dot / khoảng trắng / null trong mọi segment; canonicalize + chặn symlink
  escape ra ngoài workspace root; case-fold collision; `get/archive/delete` bind
  `(workspace_id, ref)` — sai workspace ⇒ `VaultSecurityError`; checksum verify khi `get`;
  KHÔNG dedup xuyên workspace. Negative suite `tests/agent_core/vault/` (26).

- [x] **Knowledge `get_document` bind workspace** (§4 phần) —
  `KnowledgeStore.get_document(doc_id, workspace_id)`; Postgres query
  `WHERE id = :id AND workspace_id = :ws` (cả chunks); in-memory check `doc.workspace_id`;
  `KnowledgeIngestionService.update_document_ingest_status` + review route truyền
  `identity.workspace_id`. `search_chunks*` vốn đã filter workspace. Test
  `test_get_document_workspace_scope.py`.

- [x] **Bỏ `brain_id` khỏi `frontend/lib/`** (§7) — `grep -r brain_id frontend/lib` sạch.
  `vault_service` / `marketing_service` + `marketing_controller` / `chat_service` bỏ segment
  `/$brainId/` khỏi mọi endpoint path; controller bỏ `RxString brainId` + `setBrainId()` +
  plumbing. Workspace là scope duy nhất. flutter test 370/370.

- [x] **Runtime Host Catalog + per-workspace Vault manifest** (§1) —
  `packages/agent_core/vault/host_catalog.py` (`HostCatalog`, thuần, không import `services/*`).
  `register_workspace()` tạo cây thư mục cố định (`vault/{documents,sops,attachments,artifacts}`,
  `knowledge/{snapshots,indexes}`, `quarantine/exports/temp`, `sync/{outbox,inbox,conflicts,checkpoints}`,
  `backup`) + `manifest.json` (schema version, workspace id, `key_ref` = đường dẫn tương đối tới
  file DEK — KHÔNG chứa plaintext key/token; guard `_assert_no_secret`) + catalog entry trong
  `host/catalog/workspaces.json`. Idempotent (không ghi đè manifest đã có). `runtime_mode`/`sync_mode`
  độc lập từng workspace (`set_modes` chỉ đụng target). `deregister_workspace()` bỏ khỏi catalog,
  giữ file. Catalog persist qua atomic tmp-replace, đọc lại được bằng instance mới. `workspace_id`
  qua `_check_segment`. Test `tests/agent_core/vault/test_host_catalog.py` (10).

- [x] **Per-workspace backup / export / restore** (§9) —
  `packages/agent_core/vault/backup.py` (`WorkspaceBackup(catalog, keys)`, thuần).
  `export_workspace()` đóng gói `<id>-<ts>.cosa-backup.tar.gz`: `backup-manifest.json`
  (schema version, workspace id, slug, bản sao `manifest.json` nguồn, checksum sha256 từng
  file, **wrapped DEK** — envelope-encrypt bởi master key, KHÔNG plaintext) + `data/…`
  (`vault/`, `knowledge/`, `sync/checkpoints/`; bỏ transient). `restore_workspace(mode="same"|"clone")`:
  same phát hiện collision (đã có dữ liệu vault) trừ khi `overwrite=True`; clone bắt buộc
  `new_workspace_id` khác ID gốc (Snowflake mới do caller cấp), rewrite `workspace_id` đích,
  import wrapped DEK. Giải nén thủ công (không `extractall`): sanitize từng member, chặn
  `..`/absolute/thoát khỏi `workspaces/<target_id>/`, verify sha256 vs manifest (lệch ⇒
  `VaultSecurityError`). `WorkspaceKeyManager.export_wrapped_dek()`/`import_wrapped_dek()` mới
  (import từ chối ghi đè DEK đang có + verify unwrap bằng master key hiện tại). Test
  `tests/agent_core/vault/test_workspace_backup.py` (8): clone round-trip, export A không chứa
  data/hash B, restore clone không mutate gốc, tampered archive fail checksum, path-traversal
  member bị chặn, same-id collision, clone cần ID khác.

- [x] **Per-workspace DEK + key rotation + destroy** (§6 phần key) —
  `packages/agent_core/vault/keys.py` (`WorkspaceKeyManager`, thuần, không import `services/*`).
  Master key từ `COSA_VAULT_MASTER_KEY` base64 32 byte (staging/prod fail-closed nếu thiếu;
  dev có seed cố định). Mỗi workspace 1 DEK 32 byte random, envelope-encrypt (AES-256-GCM,
  nonce 12 byte prepend) bằng master → `<data_root>/host/keys/<workspace_id>.dek` (không chứa
  plaintext DEK). `encrypt/decrypt` dùng DEK của đúng workspace, `workspace_id` làm AAD ⇒
  payload của A không giải mã bằng key B (InvalidTag → `WorkspaceKeyError`). `rotate()` giữ
  wrapped-DEK cũ trong `history` (rotation journal resumable) + bump version; `unload()/unload_all()`
  xoá cache RAM khi switch workspace; `destroy()` xoá key file ⇒ payload cũ không giải mã được
  (đúng ý khi xoá workspace). `workspace_id` qua `_check_segment` (chặn `../`). Test
  `tests/agent_core/vault/test_workspace_keys.py` (9): round-trip, cross-workspace fail,
  decrypt-trước-ensure raise, rotate+history+old-undecryptable, unload+reload, destroy,
  bad id, prod thiếu master key.

### Còn lại M3 (phiên riêng)

- §2 `S3WorkspaceStore` (MinIO/S3) + migrate key `quarantine/<workspace>/<ingestion>/...` sang layout mới.
- §4 phần còn (RLS policy + `current_setting('cosa.workspace_id')` + pool reset + pgvector filter-first);
  §5 Document/SOP lifecycle first-class;
  §6 phần còn: quota storage (`budget_gate.py` mở rộng) + wiring `WorkspaceKeyManager` vào
  object-store payload path (backup path đã dùng wrapped DEK); §8 workspace switcher invalidation.

## Exit gate

- [~] Hai workspace trên cùng local host không thể đọc/search/export/restore dữ liệu của nhau —
  object-store + key + backup/export layer xanh; còn RLS + vector search cross-workspace.
- [ ] Background run vẫn đúng workspace khi UI switch.
- [ ] RLS bật cho tenant-owned tables; pool context reset verified.
- [x] `brain_id` không còn trong `frontend/lib/` (grep sạch).
- [~] Negative test suite §6.9 — object-store (26) + key (9) + backup/export (8) xanh; còn RLS / vector search.

## Ngoài phạm vi M3

Encrypted **sync lên cloud** (M6 — M3 chỉ làm local backup/export + sync folder structure).
Cloud runtime allocation (M6). Full runtime stack per workspace (phương án C — optional
enterprise, ngoài phạm vi chương trình).
