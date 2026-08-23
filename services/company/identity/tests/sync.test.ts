// services/company/identity/tests/sync.test.ts
import { describe, expect, it, vi } from "vitest";
import { db, schema } from "../models/db";

const { identityWorkspaceMemberships } = schema;

vi.mock("../services/platform.client", () => ({
  validatePlatformMembership: vi.fn(),
}));

import { validatePlatformMembership } from "../services/platform.client";
import { syncFromPlatformService } from "../services/sync.service";
import { eq } from "drizzle-orm";

describe("syncFromPlatformService", () => {
  it("updates the local membership role when the platform role changes on re-sync", async () => {
    const platformUserId = `plat-user-${Date.now()}`;
    const platformCompanyId = `plat-company-${Date.now()}`;

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
      company_id: platformCompanyId,
    });
    expect(first.access_token).toBeTruthy();

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

    await syncFromPlatformService({
      platform_access_token: "irrelevant-because-mocked",
      company_id: platformCompanyId,
    });

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
      syncFromPlatformService({ platform_access_token: "x", company_id: platformCompanyId }),
      syncFromPlatformService({ platform_access_token: "x", company_id: platformCompanyId }),
    ]);

    const rows = await db
      .select({ id: identityWorkspaceMemberships.id })
      .from(identityWorkspaceMemberships)
      .where(eq(identityWorkspaceMemberships.platformMembershipId, membershipId));
    expect(rows.length).toBe(1);
  });
});
