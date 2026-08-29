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

## Exit gate

- [ ] Truy cập web/mobile từ xa chạy task trên local node đúng workspace/principal.
- [ ] Tắt local node ⇒ trạng thái offline rõ ràng, không chạy nơi khác.
- [ ] Replay protection + envelope auth test xanh.
- [ ] Không raw inbound port; chỉ outbound tunnel.

## Ngoài phạm vi M5

Cloud runtime execution khi local tắt (M6). Execution lease promotion/demotion (M6). Encrypted
selective sync (M6). M5 chỉ làm relay tới local node đang chạy.
