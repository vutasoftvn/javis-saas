// services/company/identity/tests/sync.test.ts
import { describe, expect, it, vi } from "vitest";
import { db, schema } from "../models/db";

const { identityWorkspaceMemberships } = schema;

vi.mock("../services/platform.client", () => ({
  validatePlatformMembership: vi.fn(),
  listPlatformMemberships: vi.fn(),
  listPlatformWorkspaceMemberships: vi.fn().mockResolvedValue([]),
  validatePlatformWorkspaceMembership: vi.fn(),
  markPlatformWorkspaceSynced: vi.fn().mockResolvedValue(undefined),
}));

import {
  validatePlatformMembership,
  listPlatformMemberships,
  listPlatformWorkspaceMemberships,
  validatePlatformWorkspaceMembership,
  markPlatformWorkspaceSynced,
} from "../services/platform.client";
import { syncFromPlatformService } from "../services/sync.service";
import { eq } from "drizzle-orm";
import { ventureProfiles } from "../../shared/db/schema/strategy";

describe("syncFromPlatformService", () => {
  it("syncs multiple platform memberships and returns WorkspaceSummary list without exposing companyId", async () => {
    const platformUserId = `plat-user-${Date.now()}`;
    const platformCompanyId1 = `plat-co-1-${Date.now()}`;
    const platformCompanyId2 = `plat-co-2-${Date.now()}`;

    (listPlatformMemberships as any).mockResolvedValueOnce([
      { companyId: platformCompanyId1, name: "Company A", roleId: "founder" },
      { companyId: platformCompanyId2, name: "Company B", roleId: "member" },
    ]);

    // Mock validatePlatformMembership for both companies
    (validatePlatformMembership as any)
      .mockResolvedValueOnce({
        valid: true,
        userId: platformUserId,
        email: `sync-${Date.now()}@example.com`,
        phone: null,
        displayName: "Multi Test",
        companyId: platformCompanyId1,
        companyName: "Company A",
        roleId: "founder",
        membershipId: "mem-1",
        membershipUpdatedAt: new Date(2026, 0, 1).toISOString(),
      })
      .mockResolvedValueOnce({
        valid: true,
        userId: platformUserId,
        email: `sync-${Date.now()}@example.com`,
        phone: null,
        displayName: "Multi Test",
        companyId: platformCompanyId2,
        companyName: "Company B",
        roleId: "member",
        membershipId: "mem-2",
        membershipUpdatedAt: new Date(2026, 0, 1).toISOString(),
      });

    const result = await syncFromPlatformService({
      platform_access_token: "test-token",
    });

    // Assert result structure: access_token + workspaces list
    expect(result.access_token).toBeTruthy();
    expect(result.token_type).toBe("bearer");
    expect(result.workspaces).toBeDefined();
    expect(result.workspaces.length).toBe(2);

    // Assert WorkspaceSummary fields — NO companyId/platformCompanyId
    result.workspaces.forEach((ws) => {
      expect(ws).toHaveProperty("workspaceId");
      expect(ws).toHaveProperty("name");
      expect(ws).toHaveProperty("role");
      expect(ws).toHaveProperty("status");
      expect(ws).not.toHaveProperty("companyId");
      expect(ws).not.toHaveProperty("platformCompanyId");
    });

    // Verify both workspaces are included
    const names = result.workspaces.map((w) => w.name).sort();
    expect(names).toEqual(["Company A", "Company B"]);
  });

  it("updates the local membership role when the platform role changes on re-sync", async () => {
    const platformUserId = `plat-user-${Date.now()}`;
    const platformCompanyId = `plat-company-${Date.now()}`;

    (listPlatformMemberships as any).mockResolvedValueOnce([
      { companyId: platformCompanyId, name: "Test Co", roleId: "member" },
    ]);

    (validatePlatformMembership as any).mockResolvedValueOnce({
      valid: true,
      userId: platformUserId,
      email: `sync-${Date.now()}@example.com`,
      phone: null,
      displayName: "Sync Test",
      companyId: platformCompanyId,
      companyName: "Sync Test Co",
      roleId: "member",
      membershipId: "mem-1",
      membershipUpdatedAt: new Date(2026, 0, 1).toISOString(),
    });

    const first = await syncFromPlatformService({
      platform_access_token: "irrelevant-because-mocked",
    });
    expect(first.access_token).toBeTruthy();
    expect(first.workspaces.length).toBe(1);

    // Re-sync with role change
    (listPlatformMemberships as any).mockResolvedValueOnce([
      { companyId: platformCompanyId, name: "Test Co", roleId: "founder" },
    ]);

    (validatePlatformMembership as any).mockResolvedValueOnce({
      valid: true,
      userId: platformUserId,
      email: `sync-${Date.now()}@example.com`,
      phone: null,
      displayName: "Sync Test",
      companyId: platformCompanyId,
      companyName: "Sync Test Co",
      roleId: "founder",
      membershipId: "mem-1",
      membershipUpdatedAt: new Date(2026, 0, 2).toISOString(),
    });

    const second = await syncFromPlatformService({
      platform_access_token: "irrelevant-because-mocked",
    });
    expect(second.workspaces[0].role).toBe("founder");

    const rows = await db
      .select({ role: identityWorkspaceMemberships.role, platformMembershipId: identityWorkspaceMemberships.platformMembershipId })
      .from(identityWorkspaceMemberships);
    const match = rows.find((r) => r.platformMembershipId === "mem-1");
    expect(match?.role).toBe("founder");
  });

  it("does not create duplicate memberships on concurrent sync for the same user+workspace", async () => {
    const platformUserId = `plat-concurrent-${Date.now()}`;
    const platformCompanyId = `plat-concurrent-co-${Date.now()}`;
    const membershipId = `mem-concurrent-${Date.now()}`;

    const mockList = [
      { companyId: platformCompanyId, name: "Concurrent Co", roleId: "member" },
    ];

    (listPlatformMemberships as any).mockResolvedValue(mockList);

    (validatePlatformMembership as any).mockResolvedValue({
      valid: true,
      userId: platformUserId,
      email: `concurrent-${Date.now()}@example.com`,
      phone: null,
      displayName: "Concurrent Test",
      companyId: platformCompanyId,
      companyName: "Concurrent Co",
      roleId: "member",
      membershipId,
      membershipUpdatedAt: new Date().toISOString(),
    });

    await Promise.all([
      syncFromPlatformService({ platform_access_token: "x" }),
      syncFromPlatformService({ platform_access_token: "x" }),
    ]);

    const rows = await db
      .select({ id: identityWorkspaceMemberships.id })
      .from(identityWorkspaceMemberships)
      .where(eq(identityWorkspaceMemberships.platformMembershipId, membershipId));
    expect(rows.length).toBe(1);
  });

  it("syncs a platform workspace into core.workspaces keyed by platform_workspace_id + creates venture_profile", async () => {
    const testPwId = `pw-${Date.now()}`;
    const platformUserId = `u-${Date.now()}`;

    (listPlatformWorkspaceMemberships as any).mockResolvedValueOnce([
      {
        platformWorkspaceId: testPwId,
        workspaceName: "AI Bakery",
        userId: platformUserId,
        email: `bakery-${Date.now()}@example.com`,
        displayName: "Baker John",
        role: "founder",
        membershipId: `mem-${Date.now()}`,
        membershipUpdatedAt: new Date().toISOString(),
      },
    ]);

    (validatePlatformWorkspaceMembership as any).mockResolvedValueOnce({
      valid: true,
      platformWorkspaceId: testPwId,
      workspaceName: "AI Bakery",
      userId: platformUserId,
      email: `bakery-${Date.now()}@example.com`,
      displayName: "Baker John",
      role: "founder",
      membershipId: `mem-${Date.now()}`,
      membershipUpdatedAt: new Date().toISOString(),
    });

    const result = await syncFromPlatformService({
      platform_access_token: "test-workspace-token",
    });

    expect(result.access_token).toBeTruthy();
    expect(result.workspaces.length).toBe(1);
    expect(result.workspaces[0].name).toBe("AI Bakery");
    expect(result.workspaces[0].role).toBe("founder");

    const [ws] = await db
      .select()
      .from(schema.identityWorkspaces)
      .where(eq(schema.identityWorkspaces.platformWorkspaceId, testPwId));
    expect(ws).toBeDefined();
    expect(ws.companyStage).toBe("S0_GENESIS");

    const [vp] = await db
      .select()
      .from(ventureProfiles)
      .where(eq(ventureProfiles.workspaceId, ws.id));
    expect(vp).toBeDefined();
  });
});
