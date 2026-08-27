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
      workspaceId: user.workspaceId,
      authorization: `Bearer ${user.accessToken}`,
    });

    expect(ctx.workspaceId).toBe(user.workspaceId.toString());
    expect(ctx.userId).toBe(user.userId.toString());
  });

  it("rejects a request with no authorization header", async () => {
    await expect(
      resolveTenantContextEndpoint({
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
        workspaceId: "999999999999",
        authorization: `Bearer ${user.accessToken}`,
      })
    ).rejects.toThrow();
  });

  // Step 1: Verify endpoint response does not contain companyId
  it("returns response without companyId property", async () => {
    const user = await createTestSession({
      email: `tenant-endpoint-no-company-${Date.now()}@example.com`,
      displayName: "No Company Response Test",
    });

    const response = await resolveTenantContextEndpoint({
      workspaceId: user.workspaceId,
      authorization: `Bearer ${user.accessToken}`,
    });

    expect(response).toMatchObject({
      workspaceId: user.workspaceId.toString(),
      userId: user.userId.toString(),
    });
    expect(response).not.toHaveProperty("companyId");
  });

  it("requires workspaceId as mandatory parameter", async () => {
    const user = await createTestSession({
      email: `tenant-endpoint-required-${Date.now()}@example.com`,
      displayName: "Required Workspace Test",
    });

    await expect(
      resolveTenantContextEndpoint({
        authorization: `Bearer ${user.accessToken}`,
      } as any)
    ).rejects.toThrow();
  });
});
