// services/company/identity/tests/helpers/test-session.test.ts
import { describe, expect, it } from "vitest";
import { createTestSession } from "./test-session";
import { resolveTenantContext } from "../../services/tenant-context.service";

describe("createTestSession", () => {
  it("creates a user+workspace+admin membership usable by resolveTenantContext", async () => {
    const session = await createTestSession({ displayName: "Helper Test" });
    expect(session.accessToken).toBeTruthy();
    expect(session.userId).toBeTruthy();
    expect(session.workspaceId).toBeTruthy();

    const ctx = await resolveTenantContext({
      authorization: `Bearer ${session.accessToken}`,
      workspaceId: session.workspaceId,
    });
    expect(ctx.userId).toBe(session.userId);
    expect(ctx.workspaceId).toBe(session.workspaceId);
    expect(ctx.membershipRole).toBe("admin");
  });

  it("honors a custom role", async () => {
    const session = await createTestSession({ displayName: "Viewer Test", role: "viewer" });
    const ctx = await resolveTenantContext({
      authorization: `Bearer ${session.accessToken}`,
      workspaceId: session.workspaceId,
    });
    expect(ctx.membershipRole).toBe("viewer");
  });
});
