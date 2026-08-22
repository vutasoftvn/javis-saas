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

## ADR-014 — primitives đã port, cutover thật CHƯA làm

`docs/architecture/adr/ADR-014-permission-model-L0-L3-canonical.md` quyết định `PermissionLevel` (L0_READ/L1_SUGGEST/L2_DRAFT/L3A_EXECUTE_WITH_APPROVAL/L3_EXECUTE) là canonical. Đã port nguyên trạng vào `agentos/core/policy.py`:

| Thành phần | |
|---|---|
| `PermissionLevel`, `ExecutionMode`, `PROTECTED_CORE_RESOURCES` | Port nguyên trạng từ `legacy/agent_runtime/cosa_core/governance/policy_engine.py` |
| `PolicyEngine.evaluate_for_agent()` | Quyết định 2 chiều (agent permission level × tool risk) — method mới, song song với `evaluate(PermissionClass)` cũ |
| `evaluate_execution_mode()` | Hàm module-level, port đầy đủ AUTONOMOUS_SAFE/APPROVED_WORKFLOW/INTERACTIVE + core-resource immutability |
| `PERMISSION_CLASS_RISK_MAPPING` | Bảng khởi đầu suy từ `DEFAULT_POLICY_TABLE` đã duyệt, chưa phải kết luận cutover cuối cùng |

**Cutover thật (đổi `Executor`/`ApprovalGateStep` sang gọi `evaluate_for_agent()`, gán `risk_level` thật cho 17 tool trong `agentos/tools/clusters/*.py`, gán `PermissionLevel` cho từng Agent) CỐ TÌNH chưa làm** — đây là quyết định nghiệp vụ cho từng tool thật, không nên tự động hóa/bịa hàng loạt. Xem "Cập nhật thực thi" trong chính ADR-014.

## Đề xuất đang chờ quyết định (2026-08-22)

- `docs/architecture/adr/ADR-016-executor-permissionlevel-cutover-proposal.md` — cutover `Executor`/`ApprovalGateStep`/13 tool binding sang `evaluate_for_agent()`, phân tích phương án gán `risk_level` per-tool và `PermissionLevel` per-agent.
- `docs/architecture/adr/ADR-017-rbac-design-proposal.md` — thiết kế RBAC (chưa tồn tại ở đâu trong repo), phân tích quan hệ với `UnifiedPermission` (ABAC hiện có) và `WorkforceMember`.

## Còn thiếu

- RBAC — xem ADR-017 (proposal).
- Cutover Executor/ApprovalGateStep/13 tool binding sang `evaluate_for_agent()` — xem ADR-016 (proposal).
- Gán `PermissionLevel` cho từng Agent — hiện chưa có khái niệm "agent trust tier" nào ở `Executor` (xem ADR-016).
- Wire `evaluate_execution_mode()`/`ExecutionMode` vào tool-call loop thật.

Chi tiết đầy đủ: `docs/architecture/AI_AGENT_OS_GAP_ANALYSIS.md` Phần A8, `docs/architecture/adr/ADR-014-permission-model-L0-L3-canonical.md`.
