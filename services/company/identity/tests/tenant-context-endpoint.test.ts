import { describe, expect, it } from "vitest";
import { createTestSession } from "./helpers/test-session";
import { resolveTenantContextEndpoint } from "../handlers/tenant-context.handler";

describe("resolveTenantContextEndpoint", () => {
  it("returns the caller's authoritative workspaceId given a valid local token and workspaceId", async () => {
    const user = await createTestSession({
      email: `tenant-endpoint-${Date.now()}@example.com`,
      displayName: "Endpoint Test",
    });

    const ctx = await resolveTenantContextEndpoint({
      companyId: user.workspaceId,
      workspaceId: user.workspaceId,
      authorization: `Bearer ${user.accessToken}`,
    });

    expect(ctx.workspaceId).toBe(user.workspaceId.toString());
    expect(ctx.userId).toBe(user.userId.toString());
  });

  it("rejects a request with no authorization header", async () => {
    await expect(
      resolveTenantContextEndpoint({
        companyId: "1",
        workspaceId: "1",
        authorization: undefined,
      })
    ).rejects.toThrow();
  });

  it("rejects a workspaceId the caller is not a member of (local identity token path)", async () => {
    const user = await createTestSession({
      email: `tenant-endpoint-deny-${Date.now()}@example.com`,
      displayName: "Endpoint Deny Test",
    });

    await expect(
      resolveTenantContextEndpoint({
        companyId: "999999999999",
        workspaceId: "999999999999",
        authorization: `Bearer ${user.accessToken}`,
      })
    ).rejects.toThrow();
  });
});
