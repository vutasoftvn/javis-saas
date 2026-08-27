import { describe, it, expect } from "vitest";
import { createTestWorkspaceWithMember, createSecondWorkspace } from "./_helpers";
import { resolveTenantContext } from "../../identity/services/tenant-context.service";

describe("test helpers", () => {
  it("creates a workspace whose member resolves a tenant context", async () => {
    const { workspaceId, bearerToken } = await createTestWorkspaceWithMember();
    const ctx = await resolveTenantContext({ authorization: bearerToken, workspaceId });
    expect(ctx.workspaceId).toBe(workspaceId);
  });

  it("createSecondWorkspace produces a workspace the primary user is not in", async () => {
    const { bearerToken } = await createTestWorkspaceWithMember();
    const { workspaceId: otherWs } = await createSecondWorkspace();
    await expect(
      resolveTenantContext({ authorization: bearerToken, workspaceId: otherWs })
    ).rejects.toThrow(/không thuộc workspace/);
  });
});
