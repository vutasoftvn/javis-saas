# Kế hoạch quyền hạn và governance

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Đóng F01/F02 và phần authority của F16; founder quản lý quyền thống nhất cho người và agent, enforce tại service và gateway.

**Architecture:** Company sở hữu quyền nghiệp vụ; COSA giữ policy nền tảng riêng và bản tham chiếu có version. Gán role qua WorkforceMember; capability, permission, delegation và approval là các điều kiện đồng thời, không thay thế nhau.

**Tech Stack:** Encore.ts/Drizzle/Postgres, Python gateway, Flutter/GetX, Vitest/pytest.

**Spec:** [07](/Volumes/SSD/javis-saas/docs/architecture/overview/07-code-audit-business-agents-2026-09-05.md), [08](/Volumes/SSD/javis-saas/docs/architecture/overview/08-phan-tich-cycle-cas-permissions-2026-09-05.md), [plan tổng](/Volumes/SSD/javis-saas/docs/superpowers/plans/2026-09-05-business-agents-master.md).

## Global Constraints

- Áp dụng toàn bộ Global Constraints và quy ước DBTEST/PYTEST/FLUTTER trong plan tổng.
- “Một bảng permissions hoặc chỉ dẫn trong prompt riêng lẻ không đủ.”
- “Agent được cài tool không có nghĩa được dùng với mọi workspace/project hoặc mọi số tiền.”
- Human và AI dùng WorkforceMember; founder không được cho phép vượt tenant, sửa audit hoặc bỏ invariant sản phẩm.
- Policy migration không cấp quyền mới chỉ vì role cũ có write/*; quyền chuyển khoản ngân hàng không nằm trong catalog agent của phạm vi này.

## A1 — Chặn tenant/command bypass trước khi thay mô hình quyền

**Files sửa:** [weekly-review.service.ts](/Volumes/SSD/javis-saas/services/company/operations/strategy/services/weekly-review.service.ts), [next-best-action.service.ts](/Volumes/SSD/javis-saas/services/company/operations/strategy/services/next-best-action.service.ts), [next-best-action.handler.ts](/Volumes/SSD/javis-saas/services/company/operations/strategy/handlers/next-best-action.handler.ts), [execution-plan.service.ts](/Volumes/SSD/javis-saas/services/company/operations/services/execution-plan.service.ts), [execution-plan.handler.ts](/Volumes/SSD/javis-saas/services/company/operations/handlers/execution-plan.handler.ts), [ai-compliance-governance.service.ts](/Volumes/SSD/javis-saas/services/company/finance-legal/services/ai-compliance-governance.service.ts).

**Files tạo:** [command-authority.service.ts](/Volumes/SSD/javis-saas/services/company/identity/services/command-authority.service.ts), [business-command-authority.test.ts](/Volumes/SSD/javis-saas/services/company/identity/tests/business-command-authority.test.ts), [strategy-command-tenancy.test.ts](/Volumes/SSD/javis-saas/services/company/operations/strategy/tests/strategy-command-tenancy.test.ts).

**Interfaces:** đổi complete review/accept proposal thành nhận `ctx: TenantContext` bên cạnh id; tạo `requireFounderCommand(ctx, action): void` làm guard tạm cho policy/sweep/approval/deployment, được A2 thay nội bộ bằng evaluator. Chỉ founder/co-founder đã xác thực được qua; không dựa vào founderMemberId caller tự khai. Actor audit lấy từ ctx.

- [ ] Thêm test âm trực tiếp vào service và handler với fixture thật hai workspace. Code test guard tối thiểu:

```ts
import { expect, it } from "vitest";
import { requireFounderCommand } from "../services/command-authority.service";
it("auditor cannot manage agent policy", () => {
  expect(() => requireFounderCommand({
    workspaceId: "101", userId: "201", workforceMemberId: "301",
    membershipRole: "auditor", permissions: ["read"], correlationId: "audit-1",
  }, "agent.policy.manage")).toThrow();
});
```

- [ ] Chạy `DBTEST company identity/tests/business-command-authority.test.ts operations/strategy/tests/strategy-command-tenancy.test.ts`; FAIL phải do bypass/missing guard, không do auth fixture thiếu. Dùng createTestWorkspaceWithMember({role:"auditor"}) hiện có cho test DB.
- [ ] Guard tối thiểu và mọi mutation phải có điều kiện `id + workspace + trạng thái nguồn` trong cùng transaction:

```ts
if (!["founder", "co-founder"].includes(ctx.membershipRole)) {
  throw APIError.permissionDenied(`Missing authority for ${action}`);
}
// Trong service đang có tx/schema: chỉ update bản ghi thuộc workspace đã xác thực.
const targetWorkspaceId = BigInt(ctx.workspaceId);
```

Không trả nội dung tài nguyên chéo workspace; không phát event nếu update không thành công. Hoàn tất lại cùng phiên bản trả kết quả idempotent; state không hợp lệ trả failedPrecondition. Sweep/accept execution plan và create/approve AI deployment dùng command guard cùng đường.
- [ ] Test outsider biết id thật bị từ chối, row/outbox không đổi; replay chỉ một event; gọi service trực tiếp vẫn bị chặn. Typecheck Company, boundary gates. Commit `fix: enforce tenant and command authority at business boundaries`.

**Nghiệm thu:** F01/F02 đóng ở các đường đã chỉ ra; F16 được chặn tạm, chi tiết reviewer/risk hoàn thiện L2. Không chờ migration RBAC mới sửa lỗi này.

## A2 — Catalog, role assignment và evaluator có version

**Files sửa:** [identity.ts](/Volumes/SSD/javis-saas/services/company/shared/db/schema/identity.ts), [schema index](/Volumes/SSD/javis-saas/services/company/shared/db/schema/index.ts), [tenant-context.service.ts](/Volumes/SSD/javis-saas/services/company/identity/services/tenant-context.service.ts), [tenant_context.ts](/Volumes/SSD/javis-saas/services/company/shared/types/tenant_context.ts), command-authority.service.ts từ A1.

**Files tạo:** [permission-catalog.ts](/Volumes/SSD/javis-saas/services/company/identity/services/permission-catalog.ts), [permission-evaluator.ts](/Volumes/SSD/javis-saas/services/company/identity/services/permission-evaluator.ts), [business-authorization.service.ts](/Volumes/SSD/javis-saas/services/company/identity/services/business-authorization.service.ts), [8_business_permissions.up.sql](/Volumes/SSD/javis-saas/services/company/identity/migrations/8_business_permissions.up.sql), [permission-evaluator.test.ts](/Volumes/SSD/javis-saas/services/company/identity/tests/permission-evaluator.test.ts).

**Schema:** core.permission_definitions PK permission_key; workspace_roles PK UUID, unique(workspace_id,role_key); role_permissions PK(role_id,permission_key), effect, typed conditions; member_role_assignments PK UUID, workspace_id/workforce_member_id/role_id/project_id/legal_entity_id/valid_from/valid_until; workspace_policy_versions PK(workspace_id,version), hash, actor_member_id, reason, created_at. Dùng compound FK/workspace checks để role/member/scope không thuộc workspace khác. Thêm CHECK valid_until>valid_from; append-only version record. Không tự mint WorkforceMember để backfill.

Catalog ban đầu: `permissions.read/manage`, `agent.policy.manage`, `agent.sweep.manage`, `execution.plan.approve`, `strategy.read/write/target.manage/transition`, `finance.read/request.create/request.approve/reconcile/period.close/report.read`, `legal.read/obligation.manage`, `ai.deployment.create/review/approve`. Action rõ nhất thắng trong một role; giữa các rule áp dụng thì DENY thắng, REQUIRE_APPROVAL không bị ALLOW khác xóa. Không match/unknown action = DENY.

**Interfaces mới trong permission-evaluator.ts:**

```ts
export type PermissionEffect = "ALLOW" | "DENY" | "REQUIRE_APPROVAL";
export type PermissionRule = { id: string; effect: PermissionEffect };
export function combinePermissionRules(rules: readonly PermissionRule[]): PermissionEffect {
  if (!rules.length || rules.some(r => r.effect === "DENY")) return "DENY";
  return rules.some(r => r.effect === "REQUIRE_APPROVAL") ? "REQUIRE_APPROVAL" : "ALLOW";
}
```

`authorizeBusinessAction(ctx, action, scope, facts)` nhận ctx đã xác thực; facts từ DB của target, không tin project/amount caller tự khai. Trả RuleDecision của plan tổng. `requireBusinessAction` trả decision ALLOW; DENY thành permissionDenied; REQUIRE_APPROVAL chỉ qua khi proof đúng resource/version/run binding. Scope null nghĩa workspace scope, không có nghĩa mọi workspace.

- [ ] Viết test combine và DB assignment: deny thắng allow, hết hạn, scope khác project, unknown action. Test mẫu:

```ts
expect(combinePermissionRules([])).toBe("DENY");
expect(combinePermissionRules([
  {id:"r1",effect:"ALLOW"}, {id:"r2",effect:"REQUIRE_APPROVAL"},
])).toBe("REQUIRE_APPROVAL");
```

- [ ] Chạy `DBTEST company identity/tests/permission-evaluator.test.ts`; ghi RED trước implementation. Viết migration Expand và evaluator như contract; money conditions dùng minor string/currency, từ chối so hạn mức khác currency.
- [ ] Seed role mẫu founder, operator, finance, auditor và agent profile scopes. Backfill chỉ từ membership/workforce mapping đã chứng minh; member thiếu workforce ID giữ unassigned/cần provisioning. Founder bootstrap từ role membership đáng tin, không từ người tạo deployment; ngăn xóa/thu hồi founder quản trị cuối cùng trong transaction.
- [ ] Dry-run migration xuất số assignments/các record chưa map, không xuất token/PII. Test migration chạy lại không duplicate; version conflict không lost update; giữ event audit. Typecheck + migration gates; commit `feat: add scoped workforce permission catalog and evaluator`.

## A3 — Một nguồn quyền nghiệp vụ và enforcement xuyên runtime

**Files sửa:** [operations policy schema](/Volumes/SSD/javis-saas/services/company/shared/db/schema/operations.ts), [execution-plan.service.ts](/Volumes/SSD/javis-saas/services/company/operations/services/execution-plan.service.ts), [agent-policy.service.ts](/Volumes/SSD/javis-saas/services/cosa/services/agent-policy.service.ts), [COSA schema](/Volumes/SSD/javis-saas/services/cosa/storage/schema.ts), [evaluator.py](/Volumes/SSD/javis-saas/apps/cosa/policies/evaluator.py), [company_policy_client.py](/Volumes/SSD/javis-saas/apps/cosa/policies/company_policy_client.py), [gateway.py](/Volumes/SSD/javis-saas/packages/agent/capabilities/gateway.py), [delegation service](/Volumes/SSD/javis-saas/services/company/shared/auth/cosa-delegation.service.ts).

**Files tạo:** [business-policy.handler.ts](/Volumes/SSD/javis-saas/services/company/identity/handlers/business-policy.handler.ts), [policy-snapshot.test.ts](/Volumes/SSD/javis-saas/services/company/identity/tests/policy-snapshot.test.ts), [test_business_policy_revocation.py](/Volumes/SSD/javis-saas/tests/apps/cosa/policies/test_business_policy_revocation.py). Migration identity 9_business_policy_sources.up.sql và COSA 31_business_policy_references.up.sql chỉ thêm nguồn/version/hash và cutover marker; không copy raw business facts lên Control Plane.

**Interfaces:** nội bộ `POST /identity/business-policy/evaluate` với delegation đúng hướng; input action/resourceRef/version/runRef, server tự resolve facts. Response RuleDecision + resourceVersion + evaluatedAt + expiresAt. COSA snapshot chứa `platformRules` và `businessPolicyRef:{workspaceId,version,hash}` riêng; business decision resolve tại Company. Platform DENY vẫn chặn; Company ALLOW không vượt statutory floor/connector/task scope.

- [ ] Test hai policy cũ xung đột và event revoke trong lúc approval đang chờ. Fixture decision dùng các effect đã định nghĩa A2; integration phải gọi Company evaluator thật. Assertion cốt lõi:

```python
assert decision_before.effect == "REQUIRE_APPROVAL"
assert decision_after_revocation.effect == "DENY"
assert tool_side_effect_calls == 0
```

- [ ] Chạy `DBTEST company identity/tests/policy-snapshot.test.ts` và `PYTEST tests/apps/cosa/policies/test_business_policy_revocation.py`; kiểm RED do thiếu re-evaluation/cutover behavior.
- [ ] Import rules cũ thành Company policy có provenance; DENY > REQUIRE_APPROVAL > ALLOW khi cùng hành động/phạm vi. Legacy rule không map được capability→permission thì giữ chặn và báo needs_review, không tự ALLOW. Chỉ một writer thay đổi business policy; endpoint cũ gọi writer này và trả version mới. COSA chỉ cho sửa platform limits ở quyền platform riêng.
- [ ] Trước side effect hoặc resume, đọc quyền hiện tại và target version, giữ approval requirement lịch sử; reject snapshot không verify/không có mapping, không dùng default ALLOW. Cache read-only có thời hạn nhưng mutation phải kiểm version hiện tại. Company service recheck quyền + state trong transaction; không chỉ dựa snapshot gateway.
- [ ] Giữ replay protection delegation hiện hữu và idempotency command riêng để retry hợp lệ không thực thi đôi. Gateway generic chỉ nhận decision/proof, không import Company. Test run revoked, connector revoked, approval stale, unknown tool, workspace suspended. Chạy gateway grant/approval tests và cross-plane policy test; commit `feat: unify business policy enforcement across service and agent runtime`.

## A4 — Flutter quản trị quyền và giải thích quyết định

**Files sửa:** [settings_view.dart](/Volumes/SSD/javis-saas/frontend/lib/modules/settings/views/settings_view.dart), [settings_binding.dart](/Volumes/SSD/javis-saas/frontend/lib/modules/settings/bindings/settings_binding.dart), [mvp-surface.json](/Volumes/SSD/javis-saas/shared/contracts/mvp-surface.json), Company identity API barrel.

**Files tạo:** [permissions.handler.ts](/Volumes/SSD/javis-saas/services/company/identity/handlers/permissions.handler.ts), [permissions.service.ts](/Volumes/SSD/javis-saas/services/company/identity/services/permissions.service.ts), [permission_models.dart](/Volumes/SSD/javis-saas/frontend/lib/modules/settings/models/permission_models.dart), [permissions_service.dart](/Volumes/SSD/javis-saas/frontend/lib/modules/settings/services/permissions_service.dart), [permissions_controller.dart](/Volumes/SSD/javis-saas/frontend/lib/modules/settings/controllers/permissions_controller.dart), [permissions_panel.dart](/Volumes/SSD/javis-saas/frontend/lib/modules/settings/views/widgets/permissions_panel.dart), [permissions_panel_test.dart](/Volumes/SSD/javis-saas/frontend/test/modules/settings/permissions_panel_test.dart), [permissions-api.test.ts](/Volumes/SSD/javis-saas/services/company/identity/tests/permissions-api.test.ts).

**Contracts mới:** GET `/identity/permissions` trả catalog/roles/assignments/version/effectivePermissions; POST `/identity/permissions/simulate` trả RuleDecision và impact list; PUT `/identity/permissions` nhận expectedVersion, reason, mutations có discriminated union ASSIGN_ROLE/REVOKE_ROLE/SET_ROLE_PERMISSION. Service kiểm `permissions.manage`, giới hạn actor không tự cấp quyền vượt authority, chặn tự nâng quyền agent.

```json
{"expectedVersion":4,"reason":"Giao finance theo project",
 "mutations":[{"kind":"ASSIGN_ROLE","memberId":"301","roleId":"01991b7b-4e00-7000-8000-000000000001",
 "scope":{"workspaceId":"101","projectId":"401"},"validUntil":"2026-12-31T17:00:00Z"}]}
```

roleId trong ví dụ wire là UUID minh họa; runtime dùng role ID đã tồn tại từ GET, không cho caller tạo role ID tùy ý. UI chỉ các hành động catalog đã hỗ trợ.

- [ ] Backend test auditor PUT bị chặn; founder simulate không mutate DB; concurrent PUT expectedVersion cũ trả VERSION_CONFLICT. Flutter test chỉnh dropdown chưa save không đổi effective state, Save thất bại giữ form và hiện lỗi inline.
- [ ] Chạy `DBTEST company identity/tests/permissions-api.test.ts`, `FLUTTER test/modules/settings/permissions_panel_test.dart` để ghi RED.
- [ ] Triển khai DTO/action types và service theo A2/A3. UI ma trận người/agent × hành động, ba lựa chọn allow/approval/deny; scope/hạn mức/thời hạn trong panel chi tiết. Hiện giải thích “rule nào, scope nào, cần ai duyệt”; không lộ secret grant. Save dùng version và reload effective state.
- [ ] Test UI bằng widget key ổn định `permission-save`, `permission-conflict`, `permission-simulation`; assertion tối thiểu:

```dart
expect(find.byKey(const ValueKey('permission-conflict')), findsOneWidget);
expect(find.text('Đã lưu quyền'), findsNothing);
```

- [ ] Regenerate contracts, chạy frontend-api-contract-check, typecheck, Flutter analyze vùng sửa và relevant tests. Commit `feat: let founders manage and simulate scoped permissions`.

**Definition of done:** UI và direct API có cùng enforcement; role/scope/expiry/audit/version hoạt động; A1 regression còn pass; agent resume không dùng lại quyền đã thu hồi. Founder không bị khóa khỏi workspace do policy migration hoặc xóa assignment cuối cùng.
