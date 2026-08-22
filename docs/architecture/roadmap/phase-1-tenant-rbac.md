# Phase 1 — Platform, Identity, TenantContext, RBAC nền tảng

> Chi tiết thực thi cho Phase 1 của `docs/architecture/COSA_IMPLEMENTATION_ROADMAP_2026-08-22.md`. Viết mới hoàn toàn dựa trên codebase thật, không dựa vào các đề xuất ADR cũ trong `docs/architecture/adr/`.

## 1a. Unified TenantContext (§4.2)

**Task:**
1. Thêm `services/shared/types/tenant_context.ts`:
```ts
export interface TenantContext {
  companyId: string;
  workspaceId: string;
  userId: string;
  workforceMemberId?: string;
  membershipRole: string;
  permissions: string[];
  correlationId: string;
}
```
2. Viết resolver dùng chung, ví dụ `services/identity/services/tenant-context.service.ts`, nhận `Authorization` header + `workspaceId` (nếu có) → xác thực token qua control-plane → lấy membership/role từ identity → trả về `TenantContext` đã đóng gói. Sinh `correlationId` mới nếu request chưa có header tương ứng (ví dụ `X-Correlation-Id`), forward nếu đã có.
3. Cập nhật handler ở `services/operations/*`, `services/commercial/*`, `services/finance-legal/*` để lấy `TenantContext` qua resolver này thay vì tự parse token/param — làm dần theo domain đang đụng tới, không cần sửa toàn bộ codebase trong 1 PR (nhưng mọi handler MỚI từ Phase 1 trở đi bắt buộc dùng resolver này).
4. Đảm bảo `correlationId` được forward khi 1 service gọi service khác (RPC nội bộ Encore) — truyền qua header hoặc context param.

**Acceptance:**
- [ ] `TenantContext` type tồn tại tại `services/shared/types/tenant_context.ts`, immutable sau khi tạo (dùng `readonly` field).
- [ ] Test: user chuyển company/workspace → context mới phản ánh đúng company/workspace/role mới, không dính state cũ.
- [ ] Test: request không có correlation id → resolver tự sinh 1 cái mới, unique.
- [ ] Test: request có correlation id sẵn → giữ nguyên, forward xuyên suốt qua ít nhất 1 lần gọi RPC nội bộ.
- [ ] Không handler nào (trong code viết mới từ Phase 1) tự ý đoán company/workspace từ nguồn khác (ví dụ query param không qua resolver).

## 1b. WorkforceMember — chỉ verify

**Task:**
1. Chạy lại test hiện có cho `services/identity/services/organization.service.ts` (hire/get WorkforceMember).
2. Xác nhận AI agent có thể được gán 1 `WorkforceMember` id — nếu chưa có test case cho nhánh AI (`memberType='AI'`), bổ sung 1 test.
3. Không tạo bảng/model mới cho workforce — nếu phát sinh nhu cầu mới, mở rộng bảng `identityWorkforceMembers` hiện có.

**Acceptance:**
- [ ] Test tồn tại cho cả nhánh `human` và `AI` của WorkforceMember.
- [ ] Không có model/bảng "workforce" thứ hai được tạo ra ở đâu trong repo.

## 1c. RBAC decision kernel (§8.5, scope tối thiểu)

**Bối cảnh code thật hiện tại** (đã verify trực tiếp, không suy đoán):
- `agentos/core/policy.py::PolicyEngine.evaluate_for_agent()` hiện chỉ nhận `agent_permission_level`, `tool_risk_level`, `tool_permission` — **không có tham số role**. Risk `critical` bị hard-code luôn trả `REQUIRE_APPROVAL`.
- `services/control-plane` (migration đầu tiên) seed 3 role ở company scope: `founder`, `co-founder`, `user`. Chưa có `auditor`.
- `ToolSpec` hiện tại (registry tool trong `agentos/tools/`) chỉ có `name/description/handler/permission_class` — chưa có field `risk_level`/`tool_permission` tường minh.

**Task — làm theo đúng 3 bước tách bạch, không gộp:**

### Bước 1: Pure RBAC decision kernel + unit test

Thêm vào `agentos/core/policy.py`:
```python
class ToolRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ToolPermission(str, Enum):
    READ_ONLY = "read_only"
    SCOPED_WRITE = "scoped_write"
    ADMIN_WRITE = "admin_write"

def evaluate_access(
    *,
    role: str,
    agent_permission_level: PermissionLevel,
    tool_risk_level: ToolRiskLevel,
    tool_permission: ToolPermission,
) -> PolicyDecision:
    ...
```

Ma trận (role × risk trước, AgentPermissionLevel siết tiếp trong ceiling role cho phép):

| role | read | write low/medium | high | critical |
|---|---|---|---|---|
| founder | ALLOW | ALLOW | ALLOW nếu L3, else REQUIRE_APPROVAL | ALLOW nếu L3, else REQUIRE_APPROVAL |
| co-founder | ALLOW | ALLOW nếu agent level ≥ L2, else REQUIRE_APPROVAL | REQUIRE_APPROVAL | REQUIRE_APPROVAL |
| user | ALLOW | ALLOW nếu agent level ≥ L2, else REQUIRE_APPROVAL | REQUIRE_APPROVAL | REQUIRE_APPROVAL |
| auditor | ALLOW | DENY | DENY | DENY |

Unit test tối thiểu (`tests/agentos/core/test_policy_rbac.py`):
```python
assert evaluate_access(role="founder", tool_risk_level=CRITICAL, agent_permission_level=L3_EXECUTE, tool_permission=ADMIN_WRITE) == ALLOW
assert evaluate_access(role="user", tool_risk_level=CRITICAL, agent_permission_level=L2_DRAFT, tool_permission=ADMIN_WRITE) == REQUIRE_APPROVAL
assert evaluate_access(role="auditor", tool_risk_level=LOW, agent_permission_level=L3_EXECUTE, tool_permission=SCOPED_WRITE) == DENY
assert evaluate_access(role="auditor", tool_risk_level=LOW, agent_permission_level=L3_EXECUTE, tool_permission=READ_ONLY) == ALLOW
```
Bổ sung test cho `co-founder`/`user` ở mọi tổ hợp risk × permission_level còn lại trong ma trận (đủ 100% coverage của bảng, không chỉ 4 case mẫu).

### Bước 2: Mở rộng ToolSpec

Thêm `risk_level: ToolRiskLevel` và `tool_permission: ToolPermission` vào định nghĩa `ToolSpec` (`agentos/tools/registry.py` hoặc file tương đương). Gán giá trị cho từng tool cluster hiện có trong `agentos/tools/clusters/*.py` — đây là việc cần review thủ công từng tool (không tự động suy diễn hàng loạt), vì risk thật của mỗi tool là quyết định nghiệp vụ.

### Bước 3: Cutover Executor

`agentos/core/executor.py` gọi `evaluate_access()` thay vì đường hard-code `critical → REQUIRE_APPROVAL`. Chạy lại toàn bộ test tool binding hiện có, đối chiếu tường minh hành vi ALLOW/DENY/REQUIRE_APPROVAL trước/sau cutover cho từng tool — không suy đoán không có regression, phải chứng minh bằng test.

### Migration role `auditor`

Thêm migration mới trong `services/control-plane/migrations/` (số thứ tự tiếp theo sau `2_align_schema.up.sql`, ví dụ `3_add_auditor_role.up.sql`), **không sửa migration 1 đã phát hành**:
```sql
INSERT INTO cosa.roles (name, scope, priority, description)
VALUES ('auditor', 'company', 20, 'Read-only company auditor');
```
(điều chỉnh tên cột/bảng đúng theo schema thật hiện có ở `services/shared/db/schema/control-plane.ts` trước khi viết SQL).

Role vẫn thuộc `services/control-plane` — AgentOS **không** tự sở hữu danh sách role, chỉ nhận `role` đã normalize qua `TenantContext` (Phase 1a).

**Acceptance:**
- [ ] `evaluate_access()` tồn tại, pure function, đủ test coverage toàn bộ ma trận role×risk×permission ở trên.
- [ ] `ToolSpec` có `risk_level`/`tool_permission`; mọi tool cluster hiện có đã được gán giá trị tường minh (không còn field rỗng).
- [ ] `Executor` gọi `evaluate_access()` thật, không còn nhánh hard-code `critical→REQUIRE_APPROVAL`.
- [ ] Migration `auditor` role tồn tại, tách biệt migration 1.
- [ ] Test đối chiếu hành vi tool trước/sau cutover — không có tool nào đổi hành vi ngoài ý muốn.

## Dependency

1a chặn 1c (RBAC cần role đã normalize qua TenantContext). 1b độc lập, có thể làm song song. Phase 1 hoàn tất mới được bắt đầu Phase 2/3/4 theo roadmap tổng.
