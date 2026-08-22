# 07 — Governance & Permission Spec

**Blueprint gốc:** §48–§51, §85–§86, §96 của `markdown/AI_Agent_OS_Master_Architecture.md`.
**Áp dụng cho:** `agentos/core/policy.py` + `approval.py` (target theo ADR-013/014); `legacy/agent_runtime` `GovernanceKernel`/`PolicyEngine` vẫn canonical cho production hiện tại.

## Trạng thái hiện tại

| Thành phần | File |
|---|---|
| PolicyEngine (ALLOW/DENY/REQUIRE_APPROVAL) | `agentos/core/policy.py` |
| ApprovalService | `agentos/core/approval.py` |
| Audit log bền vững | `agentos/core/audit_sink.py` (`SqliteAuditSink`, Giai đoạn 3.4) |

`PolicyEngine`/`ApprovalService` giờ nhận `audit_sink` tùy chọn, ghi lại mọi quyết định `policy.evaluated`/`approval.requested`/`approval.decided` vào SQLite, truy vấn theo `run_id` qua `export_run()`. `Executor` (`agentos/core/executor.py`) thread `run_id` xuống cả `PolicyEngine.evaluate()` lẫn `ApprovalService.request_approval()` để lịch sử approval của 1 run cụ thể truy vấn được.

## ADR-014 — chưa thực hiện (breaking change lớn)

`docs/architecture/adr/ADR-014-permission-model-L0-L3-canonical.md` quyết định `PermissionLevel` (L0_READ/L1_SUGGEST/L2_DRAFT/L3A_EXECUTE_WITH_APPROVAL/L3_EXECUTE, từ `legacy/agent_runtime/cosa_core/governance/policy_engine.py`) là canonical, thay cho `PermissionClass` (11 tag phẳng, agentos hiện tại) làm cơ chế quyết định chính. Đây là migration lớn, đụng tới mọi tool definition (cần thêm `risk_level`/`permission_level` per tool) — **chưa thực hiện**, cần lên kế hoạch riêng trước khi làm (xem "Migration shape" trong chính ADR-014).

## Còn thiếu

- RBAC — cả blueprint (§48) lẫn cả 2 hệ thống đều chưa có, chỉ có trust-tier model (`PermissionLevel`), không phải role-based access control.
- Migration `PermissionClass` → `PermissionLevel` (ADR-014) — chưa bắt đầu.
- `ExecutionMode` (INTERACTIVE/APPROVED_WORKFLOW/AUTONOMOUS_SAFE) — khái niệm mới cho `agentos/`, đi kèm migration ADR-014.

Chi tiết đầy đủ: `docs/architecture/AI_AGENT_OS_GAP_ANALYSIS.md` Phần A8, `docs/architecture/adr/ADR-014-permission-model-L0-L3-canonical.md`.
