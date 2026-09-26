import { describe, expect, it } from "vitest";
import { createTestWorkspaceWithMember } from "../../tests/_helpers";
import { mintCompanyDelegation } from "../../../shared/auth/cosa-delegation.service";
import {
  getVentureProfile,
  updateVentureProfile,
} from "../handlers/venture-profile.handler";

function delegation(userId: string, workspaceId: string, capabilityIds: string[]): string {
  return `Bearer ${mintCompanyDelegation({
    sub: `user:${userId}`,
    workspace_id: workspaceId,
    run_id: "run-venture-profile",
    capability_ids: capabilityIds,
  })}`;
}

describe("venture profile API", () => {
  it("returns an empty profile before anything is saved", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const res = await getVentureProfile({
      workspaceId: ws.workspaceId,
      authorization: ws.bearerToken,
    });
    expect(res.profile.workspaceId).toBe(ws.workspaceId);
    expect(res.profile.industry).toBeNull();
  });

  it("lets the founder update fields and keeps untouched ones", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    await updateVentureProfile({
      workspaceId: ws.workspaceId,
      authorization: ws.bearerToken,
      industry: " SaaS ",
      targetCustomer: "SME Việt Nam",
      initialRunwayMonths: 12,
    });
    const res = await updateVentureProfile({
      workspaceId: ws.workspaceId,
      authorization: ws.bearerToken,
      targetCustomer: "",
      geography: "VN",
    });
    expect(res.profile.industry).toBe("SaaS");
    expect(res.profile.targetCustomer).toBeNull();
    expect(res.profile.geography).toBe("VN");
    expect(res.profile.initialRunwayMonths).toBe(12);
  });

  it("serves the profile to an agent with venture.profile.read", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    await updateVentureProfile({
      workspaceId: ws.workspaceId,
      authorization: ws.bearerToken,
      industry: "Fintech",
    });
    const res = await getVentureProfile({
      workspaceId: ws.workspaceId,
      authorization: delegation(ws.userId, ws.workspaceId, ["venture.profile.read"]),
    });
    expect(res.profile.industry).toBe("Fintech");
  });

  it("does not let an agent write the profile", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    await expect(
      updateVentureProfile({
        workspaceId: ws.workspaceId,
        authorization: delegation(ws.userId, ws.workspaceId, [
          "venture.profile.read",
          "venture.profile.propose_update",
        ]),
        industry: "Other",
      })
    ).rejects.toMatchObject({ code: "unauthenticated" });
  });

  it("blocks read-only roles and invalid input", async () => {
    const auditor = await createTestWorkspaceWithMember({ role: "auditor" });
    await expect(
      updateVentureProfile({
        workspaceId: auditor.workspaceId,
        authorization: auditor.bearerToken,
        industry: "SaaS",
      })
    ).rejects.toMatchObject({ code: "permission_denied" });

    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    await expect(
      updateVentureProfile({
        workspaceId: ws.workspaceId,
        authorization: ws.bearerToken,
        initialRunwayMonths: -1,
      })
    ).rejects.toMatchObject({ code: "invalid_argument" });
    await expect(
      updateVentureProfile({ workspaceId: ws.workspaceId, authorization: ws.bearerToken })
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });
});
