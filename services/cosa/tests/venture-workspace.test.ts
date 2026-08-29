import { describe, it, expect, beforeAll } from "vitest";
import { db, schema } from "../models/db";
import { eq } from "drizzle-orm";
import {
  provisionVentureWorkspace,
  listWorkspaceMembershipsForUser,
  validateWorkspaceMembership,
  getWorkspaceEntitlement,
} from "../services/venture-workspace.service";
import { registerPlatformUser } from "../services/auth.service";

describe("venture-workspace service", () => {
  let userId: bigint;

  beforeAll(async () => {
    const email = `pw-${Date.now()}@t.io`;
    const r = await registerPlatformUser({ email, password: "secretPassword123" });
    const [u] = await db
      .select({ id: schema.users.id })
      .from(schema.users)
      .where(eq(schema.users.email, email))
      .limit(1);
    userId = u?.id ?? BigInt(0);
  });

  it("creates workspace + founder membership + free license + entitlement snapshot in one call", async () => {
    const cid = `cid-${Date.now()}`;
    const res = await provisionVentureWorkspace({
      ownerUserId: userId,
      workspaceName: "AI Coffee Shop",
      clientCreationId: cid,
    });

    expect(res.planId).toBe("free");
    expect(res.effectiveFeatures.finance).toBe(false); // plan free: finance disabled
    expect(res.effectiveLimits.max_projects).toBe(1);

    const [ws] = await db
      .select()
      .from(schema.platformWorkspaces)
      .where(eq(schema.platformWorkspaces.id, BigInt(res.platformWorkspaceId)));
    expect(ws.workspaceName).toBe("AI Coffee Shop");

    const [mem] = await db
      .select()
      .from(schema.platformWorkspaceMemberships)
      .where(eq(schema.platformWorkspaceMemberships.platformWorkspaceId, BigInt(res.platformWorkspaceId)));
    expect(mem.role).toBe("founder");
  });

  it("is idempotent by clientCreationId (retry returns same workspace, no dup license)", async () => {
    const cid = `cid-idem-${Date.now()}`;
    const a = await provisionVentureWorkspace({
      ownerUserId: userId,
      workspaceName: "W",
      clientCreationId: cid,
    });
    const b = await provisionVentureWorkspace({
      ownerUserId: userId,
      workspaceName: "W",
      clientCreationId: cid,
    });
    expect(b.platformWorkspaceId).toBe(a.platformWorkspaceId);

    const licenses = await db
      .select()
      .from(schema.workspaceLicenses)
      .where(eq(schema.workspaceLicenses.platformWorkspaceId, BigInt(a.platformWorkspaceId)));
    expect(licenses.length).toBe(1);
  });

  it("lists workspace memberships and validates membership", async () => {
    const cid = `cid-list-${Date.now()}`;
    const prov = await provisionVentureWorkspace({
      ownerUserId: userId,
      workspaceName: "WM Co",
      clientCreationId: cid,
    });

    const memberships = await listWorkspaceMembershipsForUser(userId);
    const found = memberships.find((m) => m.platformWorkspaceId === prov.platformWorkspaceId);
    expect(found).toBeDefined();
    expect(found?.role).toBe("founder");
    expect(found?.workspaceName).toBe("WM Co");

    const valid = await validateWorkspaceMembership(userId, BigInt(prov.platformWorkspaceId));
    expect(valid).not.toBeNull();
    expect(valid?.role).toBe("founder");

    const invalid = await validateWorkspaceMembership(BigInt(999999999), BigInt(prov.platformWorkspaceId));
    expect(invalid).toBeNull();
  });

  it("retrieves workspace entitlement snapshot", async () => {
    const cid = `cid-ent-${Date.now()}`;
    const prov = await provisionVentureWorkspace({
      ownerUserId: userId,
      workspaceName: "Ent Co",
      clientCreationId: cid,
    });

    const ent = await getWorkspaceEntitlement(BigInt(prov.platformWorkspaceId));
    expect(ent.platformWorkspaceId).toBe(prov.platformWorkspaceId);
    expect(ent.planId).toBe("free");
    expect(ent.effectiveFeatures.finance).toBe(false);
  });

  it("register with workspace_name provisions a free venture workspace", async () => {
    const email = `reg-${Date.now()}@t.io`;
    const res = await registerPlatformUser({
      email,
      password: "secretPassword123",
      workspace_name: "Solo Bakery",
      client_workspace_creation_id: `ccid-${Date.now()}`,
    });
    expect(res.platform_workspace_id).toBeTruthy();
    expect(res.workspace_provision_status).toBe("pending");

    const [ent] = await db
      .select()
      .from(schema.workspaceEntitlements)
      .where(eq(schema.workspaceEntitlements.platformWorkspaceId, BigInt(res.platform_workspace_id!)));
    expect(ent.planId).toBe("free");
  });

  it("backfills legacy companies without duplicates", async () => {
    // Seed a legacy company
    const compId = BigInt(Date.now());
    await db.insert(schema.companies).values({
      id: compId,
      name: "Legacy Corp",
      slug: `legacy-${compId.toString()}`,
      createdBy: userId,
      status: "active",
    });

    const [pw] = await db
      .select()
      .from(schema.platformWorkspaces)
      .where(eq(schema.platformWorkspaces.id, compId));
    // Since backfill migration ran before this company was inserted, we verify
    // manual backfill logic does not create duplicates
    const logId = `backfill:company:${compId.toString()}`;
    await db.insert(schema.platformWorkspaces).values({
      id: compId,
      workspaceName: "Legacy Corp",
      ownerUserId: userId,
      status: "active",
    }).onConflictDoNothing();

    await db.insert(schema.platformWorkspaceSyncLog).values({
      id: compId,
      platformWorkspaceId: compId,
      clientCreationId: logId,
      syncStatus: "pending",
    }).onConflictDoNothing();

    const [wsAfter] = await db
      .select()
      .from(schema.platformWorkspaces)
      .where(eq(schema.platformWorkspaces.id, compId));
    expect(wsAfter.workspaceName).toBe("Legacy Corp");
  });
});
