# M6 — Cloud Continuity

**Audit:** §9.6, §5.5–§5.7 · **Phụ thuộc:** M3, M5 · **Master:** [../2026-08-29-cosa-workspace-canonical-master-plan.md](../2026-08-29-cosa-workspace-canonical-master-plan.md)

## Context

`CLOUD_CONTINUITY` giải quyết **điều hành khi local node tắt**. Đây là subsystem greenfield
lớn: cloud runtime tách khỏi central control plane, execution lease + fencing chống split-brain,
encrypted selective sync theo aggregate, conflict recovery không last-write-wins cho dữ liệu
critical. Chỉ mở sau khi Workspace/lifecycle/identity/policy/audit là nguồn sự thật duy nhất
(M2+M4) và Vault + key isolation xong (M3) và relay + node registry xong (M5).

Guardrails liên quan: 7 (không cloud-failover khi chỉ Remote Access), 8 (không sync raw
credentials, không generic LWW cho critical data).

## Deliverables

### 1. Cloud Workspace Runtime deployment profile (audit §5.4, §9.6.1)
- Cùng runtime artifact/deployment contract với local, nhưng chạy trong **isolation scope một
  workspace** — không shared global AgentOS state.
- Tách khỏi central control plane (`services/cosa` vẫn là control-plane, không thành execution plane — guardrail 3).
- Allocation: platform cấp Cloud Workspace Runtime khi workspace bật `CLOUD_CONTINUITY`.

### 2. `WorkspaceExecutionLease` + fencing (audit §5.5)
```
WorkspaceExecutionLease {
  workspace_id, active_runtime_node_id, lease_epoch, fencing_token,
  lease_expires_at, last_heartbeat_at, last_sync_cursor
}
```
- Một workspace chỉ **một** write-authoritative runtime tại một thời điểm.
- Mọi durable write / run completion kèm `fencing_token`; store từ chối write với token cũ.
- Cloud chỉ promote nếu: local lease hết hạn **và** sync freshness đạt policy.
- Local quay lại phải acquire epoch mới — không tiếp tục ghi từ lease cũ.
- Finance/legal: `failover_policy = MANUAL` mặc định hoặc freshness threshold nghiêm ngặt.
- Read-only stale view hiển thị `as_of`, không giả vờ live.
- Reuse [services/cosa/services/control-plane-lease.service.ts](../../../../services/cosa/services/control-plane-lease.service.ts)
  + registry fencing từ M2 (Snowflake generator lease).

### 3. Encrypted selective sync theo aggregate (audit §5.6)
KHÔNG replicate DB row trực tiếp. Sync envelope:
```
workspace_id(Snowflake), entity_type, entity_id(SpineId Snowflake | LeafId UUIDv7 — string),
revision, base_revision, source_runtime_node_id, occurred_at, idempotency_key,
payload_hash, encryption_key_ref, encrypted_payload
```
Sync scopes:
| Scope | Chính sách |
|---|---|
| control metadata | sync khi workspace link platform |
| business modules | opt-in theo module + workspace |
| finance/legal | optimistic revision; conflict **cần human resolve** |
| credentials | KHÔNG sync raw secret; chỉ connector grant handle hoặc cấp cloud secret riêng |
| runs/memory/artifacts | local mặc định; optional encrypted backup/sync riêng |
| quarantine/temp/cache | KHÔNG sync |

- Tách ba pipeline: `agent_execution_outbox` ⊥ `cloud_sync_outbox` ⊥ `backup_outbox` —
  retry/dead-letter/retention riêng.
- Sync folder structure đã dựng ở M3 (`workspaces/<id>/sync/{outbox,inbox,conflicts,checkpoints}/`).
- Encryption dùng workspace DEK (M3 §6); platform không giữ plaintext key.

### 4. Local-preferred routing + promotion/demotion + split-brain recovery (audit §9.6.4)
- Runtime Router (M5) mở rộng: `CLOUD_CONTINUITY` mode ⇒ local preferred; local offline + lease
  hết + freshness pass ⇒ promote cloud; local reconnect ⇒ demote cloud, local acquire epoch mới.
- Split-brain: nếu cả hai từng ghi, chỉ writes có fencing token của epoch hiện tại được chấp
  nhận; writes epoch cũ bị reject + đưa vào conflict queue.

### 5. Conflict recovery (audit §5.7)
- Missing workspace key ⇒ fail-closed + hướng dẫn recovery; KHÔNG tạo vault rỗng mới cùng ID.
- Connector chỉ có local credential ⇒ cloud runtime đánh dấu capability `MISSING_CREDENTIAL`,
  không giả lập thành công.
- Conflict finance/legal/approval/lifecycle/policy: KHÔNG generic last-write-wins; đưa vào
  `sync/conflicts/` + human resolve; giữ đủ audit hai phía.

### 6. Cloud connector grants riêng (audit §9.6.6)
- Cloud runtime dùng cloud-scoped connector grant, không copy raw local credential.
- Grant handle sync được; secret material không.

## Test plan (audit §10.5)

- Local-off continuation: tắt local node, `CLOUD_CONTINUITY` workspace vẫn chạy task được.
- `CLOUD_CONTINUITY` chỉ promote khi lease hết **và** sync freshness pass.
- Local/cloud concurrent write: chỉ active fencing token thắng; local reconnect với stale
  epoch bị reject.
- Finance/legal stale cloud state ⇒ chuyển manual/read-only theo policy.
- Encrypted sync: không plaintext business payload trong sync store / control-plane logs.
- Conflict recovery giữ đủ audit; không generic LWW cho critical data.
- Missing workspace key ⇒ fail-closed, không tạo vault rỗng.
- Connector chỉ local credential ⇒ cloud báo `MISSING_CREDENTIAL`.
- Split-brain chaos test: partition local↔cloud, cả hai nhận write, reconcile đúng.
- Mỗi workspace trên cùng host có runtime/sync policy độc lập (A `LOCAL_ONLY`, B
  `REMOTE_ACCESS`, C `CLOUD_CONTINUITY`).

## Tiến độ

- [x] **§2 — `WorkspaceExecutionLease` + fencing** —
  Migration `cosa/23_workspace_execution_leases` (`control_plane.workspace_execution_leases`:
  `workspace_id` PK, `active_runtime_node_id`, `active_runtime_role`, `lease_epoch`,
  `fencing_token`, `lease_expires_at`, `last_sync_cursor`, `failover_policy` AUTO|MANUAL) +
  `workspace_execution_fencing_seq`. `workspace-execution-lease.service.ts`: `acquireWriteLease`
  (local — chưa có ⇒ epoch 1; cùng node còn hạn ⇒ renew; node khác còn hạn ⇒
  `failedPrecondition`; node khác hết hạn ⇒ takeover epoch+1 + fencing token mới),
  `promoteCloudRuntime` (CHỈ khi lease hết hạn + `failover_policy != MANUAL` +
  `syncFreshness === 'FRESH'`), `assertFencingTokenCurrent` (write mang token cũ ⇒
  `APIError.aborted` — split-brain protection), `heartbeatWriteLease`/`releaseWriteLease`/
  `setFailoverPolicy`. Test (10): takeover + stale-token-fenced, promote gates, local-reclaim
  fences cloud token. `encore test` 175/175.

- [x] **§3 — encrypted selective sync (scope + envelope + conflict)** —
  `packages/agent_core/sync/` (thuần). `scope_for(entity_type)` → policy table (control-metadata
  OPTIMISTIC / business OPTIMISTIC opt-in / **finance-legal + approval/lifecycle/policy
  HUMAN_RESOLVE** / credentials + runs + transient **NEVER**; entity lạ ⇒ fail-closed
  HUMAN_RESOLVE). `SyncEnvelope` + `build_sync_envelope` (mã hoá payload bằng workspace DEK
  M3 §6 — platform không thấy plaintext; refuse scope NEVER; `revision > base_revision`),
  `open_sync_envelope` (verify `payload_hash` + `key_ref` khớp workspace). `resolve_incoming_revision`
  (fast-forward / IGNORE_STALE / APPLY_WITH_AUDIT / **QUEUE_CONFLICT** — không LWW cho critical),
  `write_conflict_entry` (`sync/conflicts/` — chỉ hash + metadata, không plaintext). Test (22).

- [x] **§4 — Cloud Continuity promotion/demotion advisor** —
  `services/cosa/services/cloud-continuity.service.ts` `resolveContinuityAction(input)` (thuần):
  non-`CLOUD_CONTINUITY` ⇒ `HOLD_LOCAL`/`NO_RUNTIME` (không failover cloud); local online + cloud
  giữ lease ⇒ `DEMOTE_CLOUD`; local offline + lease còn hạn ⇒ `HOLD_LOCAL_LEASE`; lease hết hạn ⇒
  `MANUAL_REQUIRED` (policy MANUAL) / `HOLD_STALE` (sync != FRESH) / `PROMOTE_CLOUD` / `NO_RUNTIME`.
  Enforcement thật là fencing token ở §2. Test (9). `encore test` 175/175.

- [x] **§5/§6 — cloud recovery guards** —
  `packages/agent_core/sync/cloud_recovery.py`: `assert_workspace_key_present` — thiếu DEK ở cloud
  host ⇒ `CloudRecoveryError` + hướng dẫn recovery, TUYỆT ĐỐI KHÔNG `ensure_dek` (không tạo vault
  rỗng mới cùng ID). `classify_connector_availability(ConnectorGrantView)` — `READY` chỉ khi có
  grant handle + `cloud_secret_provisioned`; thiếu cloud secret ⇒ `MISSING_CREDENTIAL` (không giả
  lập thành công; §6 grant handle sync được, secret material thì không). Test (6).

### Còn lại M6 (phiên riêng)

- §1 Cloud Workspace Runtime deployment profile — deployment/infra (Encore + isolation scope).
- §2/§4 wiring: adapter + endpoint gọi `promoteCloudRuntime`/`resolveContinuityAction` từ
  scheduler; 3 outbox pipeline riêng (`agent_execution_outbox` ⊥ `cloud_sync_outbox` ⊥
  `backup_outbox`) với retry/dead-letter riêng.
- §3 wiring: producer đọc business change → `build_sync_envelope` → `sync/outbox/`; consumer
  `sync/inbox/` → `resolve_incoming_revision` → apply / `write_conflict_entry`.
- Split-brain chaos test (partition local↔cloud, cả hai ghi, reconcile) — integration harness.
- Runbook: node lost, key recovery, sync conflict, failed promotion.

## Exit gate

- [~] local-off continuation pass — `promoteCloudRuntime` + advisor `PROMOTE_CLOUD` xanh;
  chạy task thật trên cloud runtime cần §1 deployment.
- [x] stale-write rejection pass — `assertFencingTokenCurrent` reject token epoch cũ
  (`APIError.aborted`); local-reclaim fences cloud token (test).
- [~] split-brain chaos test pass — fencing-token logic + advisor xanh (unit); chaos
  partition test thuộc integration harness.
- [x] no-plaintext-sync verification pass — `SyncEnvelope` mã hoá bằng workspace DEK;
  `write_conflict_entry` chỉ hash + metadata (test khẳng định không có plaintext).
- [x] Conflict queue + human resolve flow — `QUEUE_CONFLICT` cho finance/legal +
  `write_conflict_entry` → `sync/conflicts/*.json` status `AWAITING_HUMAN_RESOLVE`.
- [ ] Runbook: node lost, key recovery, sync conflict, failed promotion.

## Ngoài phạm vi M6

Multi-region cloud runtime HA. Outcome pricing / autonomous org (tầm nhìn 2030). Generic
cross-workspace blob dedup.
