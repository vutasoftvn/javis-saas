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

## Exit gate

- [ ] local-off continuation pass.
- [ ] stale-write rejection pass.
- [ ] split-brain chaos test pass.
- [ ] no-plaintext-sync verification pass.
- [ ] Conflict queue + human resolve flow hoạt động cho finance/legal.
- [ ] Runbook: node lost, key recovery, sync conflict, failed promotion.

## Ngoài phạm vi M6

Multi-region cloud runtime HA. Outcome pricing / autonomous org (tầm nhìn 2030). Generic
cross-workspace blob dedup.
