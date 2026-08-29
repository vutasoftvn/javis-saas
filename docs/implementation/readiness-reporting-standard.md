# Development Readiness & Reporting Standard (2026-08-28)

## 1. Overview & Principles

This standard establishes mandatory development readiness, code quality, and verification gates for the `javis-saas` project across all engineering disciplines.

### Core Invariants:
1. **Single Source of Truth**: All architectural decisions must align with current schemas, ADRs, and implementation docs. Speculative or phantom contracts are strictly forbidden.
2. **Fail-Closed Security & Tenancy**:
   - Every single-record query and mutation must scope by `workspace_id`.
   - Missing configuration or secrets must immediately raise fatal runtime errors rather than falling back to insecure development defaults.
3. **Verified Reproducibility**: No feature or fix is complete without automated regression tests and local verification passing 100%.

---

## 2. Readiness Checklists by Layer

### 2.1. Backend Microservices (`services/company`, `services/cosa`)
- [ ] **Tenant Scoping**: All database queries (`select`, `update`, `delete`) must include `eq(table.workspaceId, ctx.workspaceId)` in their where clauses.
- [ ] **Header-First Context**: Endpoints must extract tenant context via `Header<"X-Workspace-Id">` instead of URL query parameters or request bodies.
- [ ] **Database Connection Security**: DB URL resolvers must strictly throw `Error("Missing required environment variable ...")` without hardcoded fallback credentials.
- [ ] **Container Image Pinning**: All images in Docker Compose and Kubernetes manifests must specify immutable semantic version tags (never `:latest`).
- [ ] **Durable Coordination**: Scheduled tasks, leases, and worker claims must use fencing tokens and atomic CAS operations (`FOR UPDATE SKIP LOCKED`).

### 2.2. Python Core & Agents (`packages/agent`, `apps/cosa`)
- [ ] **DAG Invariants**: Workflow specs must undergo schema validation ensuring non-empty step collections and preventing all-compensation DAG configurations.
- [ ] **Layer Boundaries**: `packages/agent` must never import from `services/` or `apps/`.
- [ ] **Subprocess Resilience**: Long-running background processes must support graceful SIGTERM and clean recovery from unexpected worker exits.

### 2.3. Flutter Frontend (`frontend/`)
- [ ] **Typed Error Handling**: HTTP client calls must catch status codes (401, 403, 404, 500) and throw structured typed exceptions.
- [ ] **Tenant Header Injection**: All API calls must utilize `ApiClient` which automatically injects `X-Workspace-Id` and Bearer authentication headers.
- [ ] **Optimistic UI Rollback**: Optimistic state updates must be enclosed in `try-catch` blocks that restore previous state upon network or server failures.
- [ ] **Zero Static Analysis Errors**: `flutter analyze` must report 0 issues before merging.

---

## 3. Mandatory CI / Local Verification Gates

Before submitting code reviews or deploying to staging/production, developers must execute and pass the standard verification targets:

```bash
# Gate 1: Fast Local Checks
make verify-local

# Gate 2: Full Integration & Service Verification
make verify
```

### Gate Pass Criteria:
- `boundary-check`: 0 illegal layer cross-dependencies.
- `tenancy-check`: 0 unsecured database queries.
- `check-docs`: 0 broken relative internal markdown links.
- `flutter analyze`: 0 analysis warnings or errors.
- `test suites`: 100% pass rate across Pytest, Vitest, and Flutter test suites.

---

## 4. Deferred — quyết định chính thức (không chặn go-live)

Mỗi hạng mục có ADR hoặc ticket + **điều kiện re-open** cụ thể. Không được tự
báo "Wave/Part hoàn thành" nếu bỏ qua bảng này (bài học CLAUDE.md §29.1).

| Hạng mục | Quyết định | Link | Điều kiện re-open |
|---|---|---|---|
| Conversation history (multi-turn context) | Launch single-turn; message vẫn lưu, không nạp lại vào prompt | [ADR-CONV-001](../architecture/adr/ADR-CONV-001-single-turn-launch.md) · [POST-LAUNCH-CONV-001](../tickets/POST-LAUNCH-CONV-001-multi-turn-context.md) | ≥ 3 báo cáo "agent quên context" hoặc 1 khách hàng chặn |
| Runtime agent registration API | Launch với 3 seed agent hard-code; thêm agent = code + redeploy | [ADR-AGENT-REG-001](../architecture/adr/ADR-AGENT-REG-001-seed-agents-for-launch.md) · [POST-LAUNCH-AGENT-REG-001](../tickets/POST-LAUNCH-AGENT-REG-001-registration-api.md) | > 5 agent, hoặc đổi spec > 1 lần/tuần, hoặc yêu cầu self-serve |
| Evidence-scoring weights | Dùng default; UI ghi chú "chưa hiệu chỉnh" | [POST-LAUNCH-OPS-001](../tickets/POST-LAUNCH-OPS-001-evidence-scoring-calibration.md) | Có ≥ 1 chu kỳ dữ liệu vận hành thật để calibrate |
| Manual tool loop kernel | Giữ làm fallback opt-in (`runtime="manual_tool_loop"`), không phải path chính | `ADR-RUNTIME-002` (xem CLAUDE.md "Runtime") · `docs/implementation/production-runtime-closure.md` | Chỉ khi OpenAI Agents SDK runtime lỗi nghiêm trọng cần fallback dài hạn |
| `list_approvals` join `company_id` (Part 2C.2) | **Đóng** — không thể thực hiện: migration `017_workspace_only_tenancy.sql` đã DROP `company_id` khỏi `agent.runs`; `workspace_id` là khóa tenant duy nhất. `list_pending_approvals` đã scope `workspace_id`; `get_scoped_approval` đã `JOIN runs ON r.workspace_id` | `packages/agent/migrations/017_workspace_only_tenancy.sql` | Chỉ nếu mô hình tenancy đổi lại (workspace trùng giữa company) — hiện không |

### Cách dùng bảng này

- Trước khi tuyên bố một Part "done": rà bảng, xác nhận mỗi mục liên quan có
  ADR/ticket hợp lệ + điều kiện re-open, không phải stub bị bỏ quên.
- Khi một điều kiện re-open được thỏa: mở lại ADR (thêm mục "Superseded by"
  hoặc "Revisited") + gán owner cho ticket.
