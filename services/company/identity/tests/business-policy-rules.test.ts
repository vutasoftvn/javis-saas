// IA02 phần 2 — GET /identity/business-policy/rules: route THUẦN delegation
// (không session fallback) để CapabilityGateway phía Python đọc raw
// business-policy rules, nhóm theo từng role assignment (không flatten) để
// bên gọi tái tạo đúng thuật toán combinePermissionRules gốc.
import { describe, expect, it } from "vitest";
import { randomUUID } from "node:crypto";
import { createTestWorkspaceWithMember } from "../../operations/tests/_helpers";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { mintCompanyDelegation } from "../../shared/auth/cosa-delegation.service";
import { CAP_BUSINESS_POLICY_RULES_READ } from "../../shared/auth/cosa-task-delegation";
import { getBusinessPolicyRules } from "../handlers/business-policy.handler";

const { identityWorkforceMembers, coreWorkspaceRoles, coreMemberRoleAssignments, coreRolePermissions } = schema;

describe("GET /identity/business-policy/rules (IA02 phần 2)", () => {
  it("rejects requests without a valid cosa delegation token", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });

    await expect(
      getBusinessPolicyRules({
        workspaceId: ws.workspaceId,
        authorization: undefined,
      })
    ).rejects.toThrow();
  });

  it("rejects a delegation token scoped to a different capability", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const token = mintCompanyDelegation({
      sub: "member-1",
      workspace_id: ws.workspaceId,
      run_id: "run-1",
      capability_ids: ["some.other.capability"],
    });

    await expect(
      getBusinessPolicyRules({
        workspaceId: ws.workspaceId,
        authorization: `Bearer ${token}`,
      })
    ).rejects.toThrow();
  });

  it("reports isFounder=true from real workspace membership, with no explicit rules when none assigned", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const wsId = BigInt(ws.workspaceId);
    const workforceMemberId = generateSnowflake();

    await db.insert(identityWorkforceMembers).values({
      id: workforceMemberId,
      workspaceId: wsId,
      memberType: "HUMAN",
      humanUserId: BigInt(ws.userId),
      roleTitle: "Founder",
      status: "active",
    });

    const token = mintCompanyDelegation({
      sub: "member-1",
      workspace_id: ws.workspaceId,
      run_id: "run-1",
      capability_ids: [CAP_BUSINESS_POLICY_RULES_READ],
    });

    const result = await getBusinessPolicyRules({
      workspaceId: ws.workspaceId,
      authorization: `Bearer ${token}`,
      workforceMemberId: String(workforceMemberId),
    });

    expect(result.isFounder).toBe(true);
    expect(result.ruleGroups).toEqual([]);
  });

  it("returns rules grouped per role assignment, respecting project/legal-entity scope", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "admin" });
    const wsId = BigInt(ws.workspaceId);
    const workforceMemberId = generateSnowflake();

    await db.insert(identityWorkforceMembers).values({
      id: workforceMemberId,
      workspaceId: wsId,
      memberType: "AI_AGENT",
      agentSpecId: "finance_agent",
      agentSpecVersion: "1.0.0",
      roleTitle: "Finance Agent",
      status: "active",
    });

    const roleId = randomUUID();
    await db.insert(coreWorkspaceRoles).values({
      id: roleId,
      workspaceId: wsId,
      roleKey: "finance_operator",
      name: "Finance Operator",
      isSystem: false,
    });

    // permission_key có FK tới permission_definitions (permission-catalog.ts)
    // — chỉ dùng key ĐÃ đăng ký thật (xác nhận qua lỗi FK khi thử key kiểu
    // capability_id chưa đăng ký: "Key (permission_key)=(...) is not present
    // in table permission_definitions"). Đây chính là bằng chứng cụ thể cho
    // câu hỏi vocabulary mismatch nêu ở business-authorization.service.ts:
    // muốn 1 rule áp dụng cho capability_id phía Python, permissionKey đó
    // phải được thêm vào catalog trước — không thể tự ý dùng string tuỳ ý.
    await db.insert(coreRolePermissions).values([
      {
        roleId,
        permissionKey: "finance.request.approve",
        effect: "ALLOW",
        conditions: { maxAmountMinor: "5000000", currency: "VND" },
      },
      {
        roleId,
        permissionKey: "finance.reconcile",
        effect: "REQUIRE_APPROVAL",
        conditions: {},
      },
    ]);

    // Assignment scoped to a specific project — chỉ áp dụng khi request đúng
    // projectId đó.
    await db.insert(coreMemberRoleAssignments).values({
      id: randomUUID(),
      workspaceId: wsId,
      workforceMemberId,
      roleId,
      projectId: 555n,
    });

    const token = mintCompanyDelegation({
      sub: "member-1",
      workspace_id: ws.workspaceId,
      run_id: "run-1",
      capability_ids: [CAP_BUSINESS_POLICY_RULES_READ],
    });

    // Không truyền projectId khớp -> assignment bị loại, ruleGroups rỗng.
    const noScope = await getBusinessPolicyRules({
      workspaceId: ws.workspaceId,
      authorization: `Bearer ${token}`,
      workforceMemberId: String(workforceMemberId),
    });
    expect(noScope.isFounder).toBe(false);
    expect(noScope.ruleGroups).toEqual([]);

    // Đúng projectId -> 1 group với đúng 2 rule đã cấu hình.
    const scoped = await getBusinessPolicyRules({
      workspaceId: ws.workspaceId,
      authorization: `Bearer ${token}`,
      workforceMemberId: String(workforceMemberId),
      projectId: "555",
    });
    expect(scoped.ruleGroups.length).toBe(1);
    const keys = scoped.ruleGroups[0].rules.map((r) => r.permissionKey).sort();
    expect(keys).toEqual(["finance.reconcile", "finance.request.approve"]);
  });
});
