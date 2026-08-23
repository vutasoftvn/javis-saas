import { describe, expect, it } from "vitest";
import { createTestSession } from "./helpers/test-session";
import { createWorkspaceRecord } from "../services/workspace.service";
import { resolveTenantContext } from "../services/tenant-context.service";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { identityWorkspaceMemberships } = schema;

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
        authorization: "",
      })
    ).rejects.toThrow();

    await expect(
      resolveTenantContext({
        authorization: "Bearer invalid.jwt.token",
      })
    ).rejects.toThrow();
  });

  it("throws instead of defaulting to workspace 1 when a local-token user has no membership and no workspaceId is given", async () => {
    const session = await createTestSession({ displayName: "No Membership Test", role: "admin" });
    // Xoá membership vừa tạo để mô phỏng user không thuộc workspace nào cả.
    const { db, schema } = await import("../models/db");
    const { eq } = await import("drizzle-orm");
    await db.delete(schema.identityWorkspaceMemberships).where(
      eq(schema.identityWorkspaceMemberships.userId, BigInt(session.userId))
    );

    await expect(
      resolveTenantContext({ authorization: `Bearer ${session.accessToken}` })
    ).rejects.toThrow();
  });
});
