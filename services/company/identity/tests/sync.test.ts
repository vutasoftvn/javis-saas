// services/company/identity/tests/sync.test.ts
import { describe, expect, it, vi } from "vitest";
import { db, schema } from "../models/db";

const { identityWorkspaceMemberships } = schema;

vi.mock("../services/platform.client", () => ({
  listPlatformWorkspaceMemberships: vi.fn().mockResolvedValue([]),
  validatePlatformWorkspaceMembership: vi.fn(),
  markPlatformWorkspaceSynced: vi.fn().mockResolvedValue(undefined),
}));

import {
  listPlatformWorkspaceMemberships,
  validatePlatformWorkspaceMembership,
} from "../services/platform.client";
import { syncFromPlatformService } from "../services/sync.service";
import { eq } from "drizzle-orm";
import { ventureProfiles } from "../../shared/db/schema/strategy";

/** platformWorkspaceId là Snowflake decimal string do control-plane mint (C-6). */
function pwId(): string {
  return `7${Date.now()}${Math.floor(Math.random() * 100000)}`;
}

function wm(over: Partial<Record<string, unknown>> = {}) {
  const id = pwId();
  return {
    platformWorkspaceId: id,
    workspaceName: `WS ${id}`,
    userId: `u-${id}`,
    email: `u-${id}@example.com`,
    displayName: "Test User",
    role: "founder",
    membershipId: `mem-${id}`,
    membershipUpdatedAt: new Date(2026, 0, 1).toISOString(),
    ...over,
  };
}

describe("syncFromPlatformService", () => {
  it("syncs multiple venture workspaces; WorkspaceSummary never exposes companyId", async () => {
    const userId = `u-multi-${Date.now()}`;
    const a = wm({ userId, workspaceName: "Workspace A", role: "founder" });
    const b = wm({ userId, workspaceName: "Workspace B", role: "member" });

    (listPlatformWorkspaceMemberships as any).mockResolvedValueOnce([a, b]);
    (validatePlatformWorkspaceMembership as any).mockResolvedValueOnce({ valid: true, ...a });

    const result = await syncFromPlatformService({ platform_access_token: "tok" });

    expect(result.local_session_token).toBeTruthy();
    expect(result.token_type).toBe("bearer");
    expect(result.workspaces.length).toBe(2);
    result.workspaces.forEach((ws) => {
      expect(ws).toHaveProperty("workspaceId");
      expect(ws).toHaveProperty("role");
      expect(ws).not.toHaveProperty("companyId");
      expect(ws).not.toHaveProperty("platformCompanyId");
    });
    expect(result.workspaces.map((w) => w.name).sort()).toEqual([
      "Workspace A",
      "Workspace B",
    ]);
  });

  it("updates the local membership role when the platform role changes on re-sync", async () => {
    const w = wm({ workspaceName: "Role Change WS", role: "member" });

    (listPlatformWorkspaceMemberships as any).mockResolvedValueOnce([w]);
    (validatePlatformWorkspaceMembership as any).mockResolvedValueOnce({ valid: true, ...w });
    const first = await syncFromPlatformService({ platform_access_token: "tok" });
    expect(first.workspaces[0].role).toBe("member");

    const w2 = { ...w, role: "founder", membershipUpdatedAt: new Date(2026, 0, 2).toISOString() };
    (listPlatformWorkspaceMemberships as any).mockResolvedValueOnce([w2]);
    (validatePlatformWorkspaceMembership as any).mockResolvedValueOnce({ valid: true, ...w2 });
    const second = await syncFromPlatformService({ platform_access_token: "tok" });
    expect(second.workspaces[0].role).toBe("founder");

    const [row] = await db
      .select({ role: identityWorkspaceMemberships.role })
      .from(identityWorkspaceMemberships)
      .where(eq(identityWorkspaceMemberships.platformMembershipId, w.membershipId));
    expect(row.role).toBe("founder");
  });

  it("does not create duplicate memberships on concurrent sync for the same user+workspace", async () => {
    const w = wm({ workspaceName: "Concurrent WS" });
    (listPlatformWorkspaceMemberships as any).mockResolvedValue([w]);
    (validatePlatformWorkspaceMembership as any).mockResolvedValue({ valid: true, ...w });

    await Promise.all([
      syncFromPlatformService({ platform_access_token: "x" }),
      syncFromPlatformService({ platform_access_token: "x" }),
    ]);

    const rows = await db
      .select({ id: identityWorkspaceMemberships.id })
      .from(identityWorkspaceMemberships)
      .where(eq(identityWorkspaceMemberships.platformMembershipId, w.membershipId));
    expect(rows.length).toBe(1);
  });

  it("syncs a platform workspace using the platform-minted ID + creates venture_profile", async () => {
    const w = wm({ workspaceName: "AI Bakery" });
    (listPlatformWorkspaceMemberships as any).mockResolvedValueOnce([w]);
    (validatePlatformWorkspaceMembership as any).mockResolvedValueOnce({ valid: true, ...w });

    const result = await syncFromPlatformService({ platform_access_token: "tok" });
    expect(result.workspaces.length).toBe(1);
    expect(result.workspaces[0].name).toBe("AI Bakery");

    const [ws] = await db
      .select()
      .from(schema.identityWorkspaces)
      .where(eq(schema.identityWorkspaces.id, BigInt(w.platformWorkspaceId)));
    expect(ws.id.toString()).toBe(w.platformWorkspaceId);
    expect(ws.platformWorkspaceId).toBe(w.platformWorkspaceId);

    const [vp] = await db
      .select()
      .from(ventureProfiles)
      .where(eq(ventureProfiles.workspaceId, ws.id));
    expect(vp).toBeDefined();
  });

  it("M2 §4 — a control-plane failure surfaces as unavailable, not 'no workspace'", async () => {
    (listPlatformWorkspaceMemberships as any).mockRejectedValueOnce(new Error("ECONNREFUSED"));
    await expect(
      syncFromPlatformService({ platform_access_token: "tok" }),
    ).rejects.toMatchObject({ code: "unavailable" });
  });

  it("M2 §5 — zero venture workspace ⇒ failedPrecondition (no legacy company fallback)", async () => {
    (listPlatformWorkspaceMemberships as any).mockResolvedValueOnce([]);
    await expect(
      syncFromPlatformService({ platform_access_token: "tok" }),
    ).rejects.toMatchObject({ code: "failed_precondition" });
  });
});
