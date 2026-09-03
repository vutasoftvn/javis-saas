import { describe, expect, it } from "vitest";
import { createTestSession } from "./helpers/test-session";
import { createWorkspaceRecord } from "../services/workspace.service";
import { resolveTenantContext } from "../services/tenant-context.service";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { eq } from "drizzle-orm";

const { identityWorkspaceMemberships, identityWorkforceMembers, identityUserProjections } = schema;

describe("resolveTenantContext", () => {
  it("generates a new unique correlationId if none is provided", async () => {
    const user = await createTestSession({
      email: `tenant-corr-${Date.now()}@example.com`,
      displayName: "Correlation Test",
    });

    const ctx1 = await resolveTenantContext({
      authorization: `Bearer ${user.accessToken}`,
      workspaceId: user.workspaceId,
    });

    const ctx2 = await resolveTenantContext({
      authorization: `Bearer ${user.accessToken}`,
      workspaceId: user.workspaceId,
    });

    expect(ctx1.correlationId).toBeDefined();
    expect(ctx2.correlationId).toBeDefined();
    expect(ctx1.correlationId).not.toEqual(ctx2.correlationId);
  });

  it("forwards existing correlationId when provided", async () => {
    const user = await createTestSession({
      email: `tenant-fwd-${Date.now()}@example.com`,
      displayName: "Forward Test",
    });

    const customCorrelationId = "custom-corr-uuid-12345";
    const ctx = await resolveTenantContext({
      authorization: `Bearer ${user.accessToken}`,
      workspaceId: user.workspaceId,
      correlationId: customCorrelationId,
    });

    expect(ctx.correlationId).toBe(customCorrelationId);
  });

  it("returns immutable TenantContext object", async () => {
    const user = await createTestSession({
      email: `tenant-immut-${Date.now()}@example.com`,
      displayName: "Immutable Test",
    });

    const ctx = await resolveTenantContext({
      authorization: `Bearer ${user.accessToken}`,
      workspaceId: user.workspaceId,
    });

    expect(Object.isFrozen(ctx)).toBe(true);
    expect(ctx.userId).toBe(user.userId.toString());
    expect(ctx.workspaceId).toBe(user.workspaceId.toString());
  });

  it("reflects updated workspace/role when user switches workspace", async () => {
    const user = await createTestSession({
      email: `tenant-switch-${Date.now()}@example.com`,
      displayName: "Switch Test",
    });

    const ws2 = await createWorkspaceRecord({ name: "Second Workspace" });
    await db.insert(identityWorkspaceMemberships).values({
      id: generateSnowflake(),
      workspaceId: BigInt(ws2.id),
      userId: BigInt(user.userId),
      role: "viewer",
    });

    const ctx1 = await resolveTenantContext({
      authorization: `Bearer ${user.accessToken}`,
      workspaceId: user.workspaceId,
    });
    expect(ctx1.workspaceId).toBe(user.workspaceId.toString());
    expect(ctx1.membershipRole).toBe("admin");

    const ctx2 = await resolveTenantContext({
      authorization: `Bearer ${user.accessToken}`,
      workspaceId: ws2.id,
    });
    expect(ctx2.workspaceId).toBe(ws2.id.toString());
    expect(ctx2.membershipRole).toBe("viewer");
  });

  it("rejects invalid or missing authorization token", async () => {
    await expect(
      resolveTenantContext({
        workspaceId: "1",
        authorization: "",
      })
    ).rejects.toThrow();

    await expect(
      resolveTenantContext({
        workspaceId: "1",
        authorization: "Bearer invalid.jwt.token",
      })
    ).rejects.toThrow();
  });

  it("throws when workspaceId is missing (no default workspace)", async () => {
    const session = await createTestSession({ displayName: "No Workspace Test", role: "admin" });

    await expect(
      resolveTenantContext({ authorization: `Bearer ${session.accessToken}` } as any)
    ).rejects.toThrow();
  });

  it("throws when user is not a member of the requested workspace", async () => {
    const session = await createTestSession({ displayName: "No Membership Test", role: "admin" });
    const { db, schema } = await import("../models/db");
    const { eq } = await import("drizzle-orm");
    await db.delete(schema.identityWorkspaceMemberships).where(
      eq(schema.identityWorkspaceMemberships.userId, BigInt(session.userId))
    );

    await expect(
      resolveTenantContext({
        authorization: `Bearer ${session.accessToken}`,
        workspaceId: session.workspaceId,
      })
    ).rejects.toThrow();
  });

  // Step 1: Add failing tests for workspace-only tenancy
  it("resolves a user with multiple workspace memberships to the explicitly requested workspace", async () => {
    const user = await createTestSession({
      email: `multi-ws-${Date.now()}@example.com`,
      displayName: "Multi Workspace Test",
    });

    const ws2 = await createWorkspaceRecord({ name: "Second Workspace for Multi Test" });
    await db.insert(identityWorkspaceMemberships).values({
      id: generateSnowflake(),
      workspaceId: BigInt(ws2.id),
      userId: BigInt(user.userId),
      role: "member",
    });

    // Resolver should accept either workspace
    const ctx1 = await resolveTenantContext({
      authorization: `Bearer ${user.accessToken}`,
      workspaceId: user.workspaceId,
    });
    expect(ctx1.workspaceId).toBe(user.workspaceId.toString());
    expect(ctx1.membershipRole).toBe("admin");

    const ctx2 = await resolveTenantContext({
      authorization: `Bearer ${user.accessToken}`,
      workspaceId: ws2.id,
    });
    expect(ctx2.workspaceId).toBe(ws2.id.toString());
    expect(ctx2.membershipRole).toBe("member");
  });

  it("fails closed when user's membership is removed from a workspace", async () => {
    const user = await createTestSession({
      email: `membership-remove-${Date.now()}@example.com`,
      displayName: "Membership Removal Test",
    });

    const ws2 = await createWorkspaceRecord({ name: "Temporary Workspace" });
    const membershipId = generateSnowflake();
    await db.insert(identityWorkspaceMemberships).values({
      id: membershipId,
      workspaceId: BigInt(ws2.id),
      userId: BigInt(user.userId),
      role: "viewer",
    });

    // Should work initially
    const ctx = await resolveTenantContext({
      authorization: `Bearer ${user.accessToken}`,
      workspaceId: ws2.id,
    });
    expect(ctx.workspaceId).toBe(ws2.id.toString());

    // Remove membership
    await db.delete(identityWorkspaceMemberships).where(
      eq(identityWorkspaceMemberships.id, membershipId)
    );

    // Should fail after removal
    await expect(
      resolveTenantContext({
        authorization: `Bearer ${user.accessToken}`,
        workspaceId: ws2.id,
      })
    ).rejects.toThrow();
  });

  it("fails closed when no local projection exists for platform membership but workspace ID is supplied", async () => {
    const user = await createTestSession({
      email: `no-projection-${Date.now()}@example.com`,
      displayName: "No Projection Test",
    });

    // Even though user supplies a valid workspace ID, if it doesn't correspond to
    // their actual membership, resolution must fail (no fallback)
    const nonMemberWorkspaceId = "999999999999999999";

    await expect(
      resolveTenantContext({
        authorization: `Bearer ${user.accessToken}`,
        workspaceId: nonMemberWorkspaceId,
      })
    ).rejects.toThrow();
  });

  it("scopes workforceMemberId to the requested workspace when the same human user has workforce records in two workspaces", async () => {
    const user = await createTestSession({
      email: `wf-scope-${Date.now()}@example.com`,
      displayName: "Workforce Scope Test",
    });

    const workspaceA = BigInt(user.workspaceId);
    const workspaceB = await createWorkspaceRecord({ name: "Second Workspace for Workforce Scope Test" });
    await db.insert(identityWorkspaceMemberships).values({
      id: generateSnowflake(),
      workspaceId: BigInt(workspaceB.id),
      userId: BigInt(user.userId),
      role: "member",
    });

    const workforceA = generateSnowflake();
    const workforceB = generateSnowflake();
    await db.insert(identityWorkforceMembers).values([
      {
        id: workforceA,
        workspaceId: workspaceA,
        memberType: "HUMAN",
        humanUserId: BigInt(user.userId),
        roleTitle: "Founder",
      },
      {
        id: workforceB,
        workspaceId: BigInt(workspaceB.id),
        memberType: "HUMAN",
        humanUserId: BigInt(user.userId),
        roleTitle: "Member",
      },
    ]);

    const ctx = await resolveTenantContext({
      authorization: `Bearer ${user.accessToken}`,
      workspaceId: workspaceB.id,
    });

    expect(ctx.workforceMemberId).toBe(workforceB.toString());
    expect(ctx.workforceMemberId).not.toBe(workforceA.toString());
  });

  // B5 fix (2026-09-04) — apps/cosa cần platformUserId thật của local user để
  // mint control-plane delegation (services/cosa) — xem
  // apps/cosa/auth/jwt.py::mint_control_plane_delegation.
  it("trả platformUserId null khi local user chưa từng sync qua platform", async () => {
    const user = await createTestSession({
      email: `no-platform-link-${Date.now()}@example.com`,
      displayName: "No Platform Link Test",
    });

    const ctx = await resolveTenantContext({
      authorization: `Bearer ${user.accessToken}`,
      workspaceId: user.workspaceId,
    });

    expect(ctx.platformUserId).toBeNull();
  });

  it("trả đúng platformUserId khi local user đã link qua sync-from-platform", async () => {
    const user = await createTestSession({
      email: `platform-linked-${Date.now()}@example.com`,
      displayName: "Platform Linked Test",
    });

    // `platform_user_id` có UNIQUE constraint — dùng giá trị duy nhất mỗi lần
    // chạy test (không hardcode literal) để tránh đụng độ với lần chạy trước
    // trong cùng DB test.
    const platformUserId = `platform_user_${Date.now()}_${Math.random().toString(36).slice(2)}`;
    await db
      .update(identityUserProjections)
      .set({ platformUserId })
      .where(eq(identityUserProjections.id, BigInt(user.userId)));

    const ctx = await resolveTenantContext({
      authorization: `Bearer ${user.accessToken}`,
      workspaceId: user.workspaceId,
    });

    expect(ctx.platformUserId).toBe(platformUserId);
  });
});
