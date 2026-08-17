# COSA Agent Platform — Kế hoạch & Nhật ký Triển khai (v2 - Hoàn tất)

## Bối cảnh (Context)

`markdown/d1.md` yêu cầu điều chỉnh COSA thành "Local-first Agent Platform" theo 20 nguyên tắc tuyệt đối, và xác định rõ lộ trình các khối kiến trúc cốt lõi.

Toàn bộ các Phase từ 0 đến 6 đã được triển khai, kiểm thử tự động và xác minh thực tế trên mã nguồn:

| Hạng mục | Thực tế trong mã nguồn | Trạng thái |
|---|---|---|
| **Phase 0** (Audit Architecture Docs) | `CURRENT_ARCHITECTURE.md`, `GAP_ANALYSIS.md`, `MIGRATION_MAP.md` đồng bộ 100% | ✅ **Đã xong** |
| **Phase 1** (Budget / Stuck Detector Wiring) | `chief_of_staff.py:152-162` gọi `BudgetTracker.check()` + `StuckDetector.analyze_run()` tại các checkpoint; test tại `test_chief_of_staff_orchestration.py` | ✅ **Đã xong** |
| **Phase 2** (Vá 3 điểm bypass Gateway) | `chief_of_staff.py:210,263`, `company_tools.py:109`, và `agents/context/builder.py:76-102` đều gọi `GovernanceKernel.evaluate_and_audit_tool_call` | ✅ **Đã xong** |
| **Phase 3a** (Đổi tên & Tránh xung đột PolicyEngine) | Đổi tên class `PolicyEngine` trong `orchestrator/service.py` thành `OrchestratorPolicyEngine` (kèm alias tương thích ngược) | ✅ **Đã xong** |
| **Phase 3b** (Model Gateway & Profile Catalog) | `dspy_lm_factory.py` dùng chung catalog `ModelProfileRegistry`, `ModelGateway.invoke` bọc `trace_span` telemetry | ✅ **Đã xong** |
| **Phase 3c** (Chuẩn hóa `router_api.py`) | Docstring & scope chuẩn hóa: API Control Plane CRUD (Goals, Plans, Memories) phân định rõ với Chat Gate | ✅ **Đã xong** |
| **Phase 3d** (Prompt Registry) | `chief_of_staff.py:374` dùng `PromptRegistry.render_effective(domain="cosa", name="chief_of_staff_synthesis")` | ✅ **Đã xong** |
| **Phase 4** (Reality Verifier & Outreach Audit) | `SalesActionCapability.dispatch_outreach` fail-closed governance, `RealityVerifier` đầy đủ CRM/Email/Finance/Deploy checks | ✅ **Đã xong** |
| **Phase 5** (Google ADK Pilot & Parity Test) | `agents/adk_runtime/{adapter,sales_graph}.py` gateway-safe (`ModelGateway` + `GovernanceKernel`), test parity `test_adk_and_legacy_sales_parity` pass 100% | ✅ **Đã xong** |
| **Phase 6** (OpenTelemetry Observability) | `backend/requirements.txt` có `opentelemetry-api`/`sdk`, `trace_span()` wire vào `conversation_gate`, `ModelGateway`, `GovernanceKernel` | ✅ **Đã xong** |

---

## Chi tiết các Phase đã triển khai

### Phase 0 — Audit tài liệu kiến trúc ✅ HOÀN THÀNH
Toàn bộ tài liệu [CURRENT_ARCHITECTURE.md](file:///Volumes/SSD/javis-saas/docs/agent-platform/CURRENT_ARCHITECTURE.md), [GAP_ANALYSIS.md](file:///Volumes/SSD/javis-saas/docs/agent-platform/GAP_ANALYSIS.md), [MIGRATION_MAP.md](file:///Volumes/SSD/javis-saas/docs/agent-platform/MIGRATION_MAP.md) đã được đối chiếu trực tiếp với mã nguồn.

---

### Phase 1 — Vá gap an toàn Governance ✅ HOÀN THÀNH
`BudgetTracker`/`StuckDetector` đã được wire vào `chief_of_staff.py::check_governance()`, tự động dừng với status `failed` khi vượt quá ngân sách API hoặc lặp action vô tận.

---

### Phase 2 — Vá 3 điểm bypass gateway ✅ HOÀN THÀNH
Đã bảo vệ toàn bộ 3 điểm:
1. `chief_of_staff.py:210,263` — đánh giá và audit qua `GovernanceKernel` trước khi gọi summary.
2. `company_tools.py:109` — `execute_tool()` luôn gọi `GovernanceKernel.evaluate_and_audit_tool_call`.
3. `agents/context/builder.py:76-102` — `build_agent_context()` đánh giá và audit qua `GovernanceKernel` cho mọi truy vấn sales, finance, okrs, projects.

---

### Phase 3 — Hợp nhất hạ tầng & Loại bỏ xung đột ✅ HOÀN THÀNH
- **3a. Tránh xung đột tên**: `agents/orchestrator/service.py` đổi tên class thành `OrchestratorPolicyEngine` (giữ alias `PolicyEngine = OrchestratorPolicyEngine`).
- **3b. Model Gateway**: `dspy_lm_factory.py` dùng chung catalog `ModelProfileRegistry`, `ModelGateway.invoke` bọc `trace_span` telemetry.
- **3c. Control Plane Router API**: `agents/control_plane/router_api.py` được xác định rõ là API Control Plane CRUD (Goals, Plans, Memories) cho Agentic workflows, phân định độc lập với Conversation Gate của Chat.
- **3d. Prompt Sourcing**: `chief_of_staff.py` tải prompt qua `PromptRegistry.render_effective(domain="cosa", name="chief_of_staff_synthesis")`.

---

### Phase 4 — Reality Verifier & Outreach Audit ✅ HOÀN THÀNH
- `RealityVerifier` hỗ trợ xác minh thực tế PostgreSQL: `verify_crm_contact`, `verify_crm_lead`, `verify_email_approval_sent`, `verify_email_outbox`, `verify_deployment`, `verify_accounting_document`, `verify_financial_transaction`, và mint `Outcome Certificate`.
- `SalesActionCapability.dispatch_outreach` bắt buộc kiểm tra qua `GovernanceKernel` (fail-closed, `is_approved=False` mặc định).

---

### Phase 5 — Google ADK 2.0 Runtime Pilot & Parity Verification ✅ HOÀN THÀNH
- `agents/adk_runtime/adapter.py`: `AdkModelAdapter` → `ModelGateway`, `AdkToolAdapter` → `GovernanceKernel`.
- `agents/adk_runtime/sales_graph.py`: State graph workflow thực thi phân tích sales và diagnosis.
- `tests/agents/test_adk_runtime.py`: Bổ sung `test_adk_and_legacy_sales_parity` kiểm thử so sánh tương thích giữa ADK workflow và legacy execution.

---

### Phase 6 — OpenTelemetry Observability ✅ HOÀN THÀNH
- Bổ sung `opentelemetry-api>=1.20.0` và `opentelemetry-sdk>=1.20.0` vào `backend/requirements.txt`.
- `core/telemetry.py` cung cấp `trace_span()` an toàn (tự động loại bỏ khóa nhạy cảm: `api_key`, `token`, `password`, `chain_of_thought`).
- Wire `trace_span()` vào:
  1. `modules/chat/conversation_gate.py` (`conversation_gate.resolve`)
  2. `agents/reliability/model_gateway.py` (`model_gateway.invoke`)
  3. `agents/governance/kernel.py` (`governance_kernel.evaluate`)

---

## Ràng buộc Kiến trúc Đã Xác minh (Invariants)

1. **Snowflake ID**: Toàn bộ ID mới sử dụng 64-bit Snowflake ID (`generate_snowflake_id()` / `SnowflakeIDMixin`).
2. **Boundary**: Frontend `frontend/lib/` hoàn toàn không có tham chiếu cổng `8888`, `backend/server`, `javis/`, hay `web_socket_channel`.
3. **Fail-Closed Governance**: Mọi mutating/external action đều qua `GovernanceKernel`.
4. **Test Suite**: 100% test pass (189 passed, 3 skipped).

---

## Kiểm thử / Xác minh

```bash
# Chạy toàn bộ test suite
cd backend && PYTHONPATH=. ./.venv/bin/pytest app/tests/test_architectural_invariants.py app/tests/agents/ app/tests/test_telemetry.py app/tests/test_p2_revenue_engine.py -v

# Kiểm tra frontend runtime boundary
rg -n --glob '!build/**' '(:8888|backend/server|javis/|web_socket_channel)' frontend/lib
```
