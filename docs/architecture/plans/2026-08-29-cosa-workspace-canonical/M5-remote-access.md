# M5 — Remote Access

**Audit:** §9.5, §5.1–§5.4, §5.7 · **Phụ thuộc:** M2, M4 · **Master:** [../2026-08-29-cosa-workspace-canonical-master-plan.md](../2026-08-29-cosa-workspace-canonical-master-plan.md)

## Context

`REMOTE_ACCESS` giải quyết **truy cập từ xa khi máy local đang chạy** — khác với
`CLOUD_CONTINUITY` (điều hành khi local tắt). Audit §5.3 nhấn: không dùng một cờ `online=true`
cho cả hai vì data-residency và failure semantics khác nhau.

Điểm tựa đã có trong code:
- [apps/cosa/config/planes.py](../../../../apps/cosa/config/planes.py) bắt execution plane chạy local trong production.
- [services/company/events/outbox-relay.service.ts](../../../../services/company/events/outbox-relay.service.ts) từ chối relay tới target không phải local.
- `services/cosa/services/control-plane-*.service.ts` (`lease`, `watch`, `worker`, `delivery`,
  `mission`, `scheduler`) — hạ tầng control-plane node presence + lease đã tồn tại, tái dùng.

Trong `REMOTE_ACCESS`, business data **vẫn ở local**; cloud chỉ route encrypted traffic
(audit §5.3 bảng). Guardrail 7: KHÔNG cloud-failover khi user chỉ bật Remote Access.

## Deliverables

### 1. Runtime node registration + device key + heartbeat (audit §9.5.1)
- Bảng `workspace_runtime_nodes` (control-plane, `services/cosa`): `node_id`(Snowflake),
  `workspace_id`, `device_key_fingerprint`, `runtime_role`, `last_heartbeat_at`, `presence_status`
  (ONLINE|OFFLINE|DEGRADED), `agent_version`, `registered_at`.
- Local node đăng ký lúc khởi động (device key từ OS Keychain — reuse cơ chế M3 §6), gửi heartbeat.
- Reuse [services/cosa/services/control-plane-lease.service.ts](../../../../services/cosa/services/control-plane-lease.service.ts),
  [control-plane-watch.service.ts](../../../../services/cosa/services/control-plane-watch.service.ts),
  [control-plane-worker.service.ts](../../../../services/cosa/services/control-plane-worker.service.ts).
- Node chưa đăng ký / device key không hợp lệ ⇒ không được nhận command.

### 2. Secure outbound tunnel/relay (audit §9.5.2)
- Local node mở **outbound** connection tới Platform Gateway / Runtime Router; KHÔNG mở raw
  local port ra internet.
- Relay chỉ chuyển tiếp encrypted command envelope; platform không giải mã business payload.
- Transport: WebSocket/gRPC-stream outbound + mTLS (device key ↔ platform cert).

### 3. Runtime Router (audit §5.4)
```
Web/Mobile/Desktop → Platform Gateway / Runtime Router
                       ├─ Secure relay → Local Workspace Runtime Node   (REMOTE_ACCESS)
                       └─ Isolated Cloud Workspace Runtime Node          (CLOUD_CONTINUITY — M6)
```
- Router resolve theo `workspace_id` + membership + `runtime_mode` + node presence + execution
  lease + sync freshness.
- Với `runtime_mode == REMOTE_ACCESS`: chỉ route tới local node; local offline ⇒ trả offline
  state, **không** thử cloud.

### 4. End-to-end authenticated command envelope (audit §9.5.4)
- Envelope: `workspace_id`, `principal` (user/workforce member), `command`, `nonce`,
  `issued_at`, `expires_at`, signature.
- Replay protection: nonce cache + `expires_at` window ở local node.
- Audit: mọi remote command ghi vào local audit log với `principal` + `source=remote_relay`.
- Principal/workspace trong envelope là nguồn sự thật — không suy từ transport.

### 5. Offline / stale UI semantics (audit §5.7)
- Local unavailable trong `REMOTE_ACCESS`: UI báo "node offline / read-only" rõ ràng; không âm
  thầm chạy cloud.
- Read-only stale view (nếu có cache) phải hiển thị `as_of` timestamp, không giả vờ live.
- Platform unavailable: local mode tiếp tục; platform actions queue hoặc báo unavailable,
  không fallback sang legacy Company (đã xóa ở M2).

### 6. Frontend
- API client resolve target: request business → local node qua relay URL (dùng
  `local_session_token` từ M1); request platform registry/entitlement → platform URL (dùng
  `platform_access_token`).
- Workspace picker/switcher hiển thị `runtime_mode`, `presence_status`, last heartbeat.

## Test plan (audit §10.5)

- Remote browser → relay → local runtime giữ đúng `workspace`/`principal`.
- Local offline trong `REMOTE_ACCESS` KHÔNG tự cloud execute; UI hiện offline state.
- Command envelope hết hạn / nonce lặp ⇒ reject (replay protection).
- Platform unavailable ⇒ local vẫn chạy; không Company fallback.
- Relay không mở raw local port (port scan test).
- Audit log ghi đủ remote command với principal.

## Tiến độ

- [x] **§1 — Runtime node registration + device key + heartbeat + computed presence** —
  Migration `cosa/22_workspace_runtime_nodes` (`control_plane.workspace_runtime_nodes`:
  `node_id` Snowflake, `workspace_id`, `device_key_fingerprint`, `runtime_role`,
  `presence_status`, `last_heartbeat_at`, `revoked_at`; partial unique
  `(workspace_id, device_key_fingerprint) WHERE revoked_at IS NULL`).
  `runtime-node-registry.service.ts`: `registerRuntimeNode` (idempotent theo
  workspace+fingerprint, mint `node_id` Snowflake control-plane), `heartbeatRuntimeNode`
  (device key phải khớp; revoked ⇒ `permissionDenied`), `revokeRuntimeNode`,
  `computePresence` (ONLINE ≤45s / DEGRADED ≤120s / else OFFLINE — tính lại theo độ
  tươi heartbeat, không tin cột), `assertNodeMayReceiveCommand` (cổng §3/§4: node
  đăng ký + chưa revoke + device key khớp + presence != OFFLINE). Test (6). `encore test` 138/138.

- [x] **§4 — end-to-end authenticated command envelope** —
  `packages/agent_core/remote/command_envelope.py` (thuần stdlib, không import `services/*`).
  `CommandEnvelope` {workspace_id, principal, command, nonce, issued_at, expires_at,
  signature}. `CommandEnvelopeVerifier.verify()`: HMAC-SHA256 trên canonical bytes
  (constant-time compare) → `expires_at` + TTL trần 15m + `issued_at` không quá cửa sổ
  clock-skew 60s → `NonceReplayCache` bind `(workspace_id, nonce)` TTL theo `expires_at`.
  Trả `VerifiedCommand` — principal/workspace ĐÃ xác thực là nguồn sự thật, KHÔNG suy
  từ transport. Test (11): tampered, sai key, hết hạn, replay, nonce trùng khác workspace,
  cache evict. 565 passed agent_core sweep.

- [x] **§1/§3 HTTP surface** — `services/cosa/handlers/runtime-node.handler.ts`:
  `POST /cosa/runtime/nodes/{register,heartbeat,revoke}` + `GET /cosa/runtime/nodes` (auth
  worker-service token, `workspaceId` claim phải khớp request ⇒ `assertWorkspaceScopedWorker`);
  `POST /cosa/runtime/route` (§3 wiring — `runtimeMode` do caller truyền, resolve local/cloud
  node từ registry, node đăng ký + presence != OFFLINE ⇒ có runtime lease, gọi
  `resolveRuntimeRoute`). Route-inventory regenerated (5 route backend-implemented). Test (6).
  `encore test` 156/156.

- [x] **§4 — relay command gate (audit)** —
  `packages/agent_core/remote/relay_command_gate.py` `RelayCommandGate.accept()`: verify
  envelope → ghi audit local (ACCEPTED và REJECTED) với principal đã xác thực +
  `source="remote_relay"` → trả `VerifiedCommand` / re-raise. `RemoteCommandAuditSink` ABC +
  `InMemoryAuditSink`. Envelope hỏng ⇒ vẫn ghi dòng audit, không crash. Test (4).

- [x] **§3 — Runtime Router decision core** —
  `services/cosa/services/runtime-router.service.ts` `resolveRuntimeRoute(input)` (hàm thuần):
  `!membershipValid`⇒`DENIED`; `LOCAL_ONLY`+local up⇒`LOCAL_DIRECT`; `REMOTE_ACCESS`+local up
  ⇒`LOCAL_RELAY`, local offline/no node⇒`OFFLINE` với `cloudConsidered=false` (guardrail 7:
  KHÔNG cloud-failover); `CLOUD_CONTINUITY`(M6) ưu tiên `LOCAL_RELAY` khi local sống, else
  `CLOUD_ISOLATED` (degraded khi sync STALE), cả hai down⇒`OFFLINE`. presence `DEGRADED`⇒route
  + `degraded=true`; thiếu lease⇒coi offline. Adapter lấy runtime_mode (company) / presence
  (§1) / lease (control-plane-lease) chưa wire. Test (12). `encore test` 150/150.

### Còn lại M5 (phiên riêng)

- §2 secure outbound tunnel/relay (WebSocket/gRPC-stream + mTLS) — transport thật; local
  node giữ outbound connection tới Platform Gateway, KHÔNG mở raw inbound port.
- §3 adapter: `POST /cosa/runtime/route` hiện nhận `runtimeMode` từ caller — thêm adapter
  fetch trực tiếp từ `services/company` workspace record + wire lease thật.
- §5 offline/stale UI semantics (Flutter); §6 frontend API client target resolution +
  workspace picker hiển thị `runtime_mode`/`presence_status`/last heartbeat.

## Exit gate

- [ ] Truy cập web/mobile từ xa chạy task trên local node đúng workspace/principal.
- [ ] Tắt local node ⇒ trạng thái offline rõ ràng, không chạy nơi khác.
- [ ] Replay protection + envelope auth test xanh.
- [ ] Không raw inbound port; chỉ outbound tunnel.

## Ngoài phạm vi M5

Cloud runtime execution khi local tắt (M6). Execution lease promotion/demotion (M6). Encrypted
selective sync (M6). M5 chỉ làm relay tới local node đang chạy.
