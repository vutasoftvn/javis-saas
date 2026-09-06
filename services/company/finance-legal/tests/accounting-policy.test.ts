import { describe, expect, it } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { addMemberToWorkspace } from "../../operations/tests/_helpers";
import { createLegalEntityProfile } from "../services/legal-entity-profile.service";
import { resolveTenantContext } from "../../identity/services/tenant-context.service";
import {
  getAccountingPolicyService,
  setAccountingPolicyService,
} from "../services/accounting-policy.service";

async function foundersSetup(displayName: string) {
  const session = await createTestSession({ role: "founder", displayName });
  const authorization = `Bearer ${session.accessToken}`;
  const entity = await createLegalEntityProfile({
    workspaceId: BigInt(session.workspaceId),
    entityType: "MICRO_ENTERPRISE",
  });
  const ctx = await resolveTenantContext({ authorization, workspaceId: session.workspaceId });
  return { session, ctx, legalEntityId: entity.id };
}

describe("accounting-policy.service", () => {
  it("returns null when no policy has been set yet", async () => {
    const { ctx, legalEntityId } = await foundersSetup("Policy None Ws");
    const policy = await getAccountingPolicyService(ctx, legalEntityId);
    expect(policy).toBeNull();
  });

  it("founder sets a tax rate; a non-founder is rejected", async () => {
    const { ctx, legalEntityId } = await foundersSetup("Policy Set Ws");
    // `createTestSession` luôn tạo workspace MỚI của riêng nó — dùng nó ở đây
    // sẽ tạo ra một session thuộc workspace KHÁC ctx.workspaceId, khiến
    // resolveTenantContext fail sớm ở bước kiểm tra membership ("user không
    // thuộc workspace ...") thay vì test đúng nhánh requireFounderCommand.
    // Dùng addMemberToWorkspace (cùng pattern payment-request.test.ts) để
    // thêm 1 thành viên "member" thật vào CÙNG workspace của founder.
    const nonFounderMember = await addMemberToWorkspace(ctx.workspaceId, "member");
    const nonFounderCtx = await resolveTenantContext({
      authorization: nonFounderMember.bearerToken,
      workspaceId: ctx.workspaceId,
    });

    await expect(
      setAccountingPolicyService(nonFounderCtx, { legalEntityId, corporateIncomeTaxRateBps: 2000 })
    ).rejects.toThrow(/Missing authority/);

    const policy = await setAccountingPolicyService(ctx, { legalEntityId, corporateIncomeTaxRateBps: 2000 });
    expect(policy.corporateIncomeTaxRateBps).toBe(2000);
    expect(policy.inventoryValuationMethod).toBe("weighted_average");
    // foundersSetup không tạo hàng identityWorkforceMembers (chỉ createTestSession +
    // legal entity) nên ctx.workforceMemberId là undefined ở đây — đúng theo quy ước
    // "không fallback sang ctx.userId" (xem payment-request.test.ts dòng ~393-397,
    // ~433-434 cho cùng pattern với approvedByMemberId/budgetOverrideByMemberId),
    // cột phải là null, không phải rơi về userId.
    expect(policy.confirmedByMemberId).toBeNull();
    expect(policy.confirmedAt).not.toBeNull();

    const fetched = await getAccountingPolicyService(ctx, legalEntityId);
    expect(fetched?.corporateIncomeTaxRateBps).toBe(2000);
  });

  it("rejects a tax rate outside 0-10000 bps", async () => {
    const { ctx, legalEntityId } = await foundersSetup("Policy Range Ws");
    await expect(
      setAccountingPolicyService(ctx, { legalEntityId, corporateIncomeTaxRateBps: 10001 })
    ).rejects.toThrow(/corporateIncomeTaxRateBps/);
    await expect(
      setAccountingPolicyService(ctx, { legalEntityId, corporateIncomeTaxRateBps: -1 })
    ).rejects.toThrow(/corporateIncomeTaxRateBps/);
  });
});
