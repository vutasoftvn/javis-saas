// services/company/identity/tests/sync.test.ts
import { describe, expect, it, vi, beforeEach } from "vitest";
import { db, schema } from "../models/db";

const { identityWorkspaceMemberships, identityUserProjections } = schema;

vi.mock("../services/platform.client", () => ({
  listPlatformWorkspaceMemberships: vi.fn().mockResolvedValue([]),
  validatePlatformWorkspaceMembership: vi.fn(),
  markPlatformWorkspaceSynced: vi.fn().mockResolvedValue(undefined),
  verifyPlatformToken: vi.fn().mockImplementation((token: string) => {
    if (token === "invalid") throw new Error("invalid token");
    return { sub: "u-mock", aud: "cosa" };
  }),
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
    // verifyPlatformToken mock (bên trên) luôn trả `sub: "u-mock"` bất kể
    // token truyền vào — userId ở đây phải khớp để qua được check
    // `verified.userId !== platformUserId` trong syncFromPlatformService.
    userId: "u-mock",
    email: `u-${id}@example.com`,
    displayName: "Test User",
    role: "founder",
    membershipId: `mem-${id}`,
    membershipUpdatedAt: new Date(2026, 0, 1).toISOString(),
    ...over,
  };
}

// Giúp mọi test resolve được response verify cho từng membership được request,
// không chỉ cái đầu tiên — vì syncFromPlatformService giờ verify TẤT CẢ
// membership trả về từ listPlatformWorkspaceMemberships (Promise.all), không
// chỉ membership đầu tiên như flow fast-path/fallback cũ.
function mockVerifiedMemberships(memberships: Array<ReturnType<typeof wm>>) {
  (validatePlatformWorkspaceMembership as any).mockImplementation(
    async ({ platformWorkspaceId }: { platformWorkspaceId: string }) => {
      const membership = memberships.find((item) => item.platformWorkspaceId === platformWorkspaceId);
      return membership ? { valid: true, ...membership } : { valid: false };
    },
  );
}

describe("syncFromPlatformService", () => {
  // Mock `verifyPlatformToken` (bên trên) luôn trả cùng một `sub: "u-mock"`
  // cho mọi token hợp lệ ⇒ toàn bộ test trong file này giờ verify membership
  // dưới CÙNG một platformUserId (đây chính là hành vi security fix mới —
  // membership phải khớp platformUserId của token, không còn suy ra userId
  // độc lập từ payload nữa). Vì vậy phải dọn sạch membership cũ của user mock
  // này trước mỗi test để giữ tính cô lập (trước đây mỗi test tự cô lập nhờ
  // userId ngẫu nhiên riêng — điều đó không còn khả thi với check mới).
  beforeEach(async () => {
    const [mockUser] = await db
      .select({ id: identityUserProjections.id })
      .from(identityUserProjections)
      .where(eq(identityUserProjections.platformUserId, "u-mock"))
      .limit(1);
    if (mockUser) {
      await db
        .delete(identityWorkspaceMemberships)
        .where(eq(identityWorkspaceMemberships.userId, mockUser.id));
    }
  });

  it("syncs multiple venture workspaces; WorkspaceSummary never exposes companyId", async () => {
    const a = wm({ workspaceName: "Workspace A", role: "founder" });
    const b = wm({ workspaceName: "Workspace B", role: "member" });

    (listPlatformWorkspaceMemberships as any).mockResolvedValueOnce([a, b]);
    mockVerifiedMemberships([a, b]);

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
    mockVerifiedMemberships([w]);
    const first = await syncFromPlatformService({ platform_access_token: "tok" });
    expect(first.workspaces[0].role).toBe("member");

    const w2 = { ...w, role: "founder", membershipUpdatedAt: new Date(2026, 0, 2).toISOString() };
    (listPlatformWorkspaceMemberships as any).mockResolvedValueOnce([w2]);
    mockVerifiedMemberships([w2]);
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
    mockVerifiedMemberships([w]);

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
    mockVerifiedMemberships([w]);

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

  it("does not trust client-sent workspaces or roles", async () => {
    const canonical = wm({ workspaceName: "Control Plane Workspace", role: "member" });
    (listPlatformWorkspaceMemberships as any).mockResolvedValueOnce([canonical]);
    mockVerifiedMemberships([canonical]);

    const result = await syncFromPlatformService({
      platform_access_token: "tok",
      workspaces: [{
        workspace_id: pwId(),
        workspace_name: "Injected Workspace",
        role_id: "founder",
      }],
    } as any);

    expect(listPlatformWorkspaceMemberships).toHaveBeenCalledWith({ platformToken: "tok" });
    expect(result.workspaces).toEqual([{ workspaceId: canonical.platformWorkspaceId, name: canonical.workspaceName, role: "member", status: "active" }]);
  });
});
